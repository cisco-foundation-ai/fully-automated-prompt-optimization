# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Characterize implementation-specific runtime capability boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from helpers import DummyClient, DummyCompletions

import src.hephaestus.runs.eval_runner as eval_runner
from src.hephaestus.chains.agentic_nodes import make_agentic_node
from src.hephaestus.chains.nodes import make_llm_node
from src.hephaestus.engine.skills import render_skills_block
from src.hephaestus.mcp.executor import MCPToolExecutor
from src.hephaestus.mcp.types import MCPConfig, MCPTool
from src.hephaestus.providers import build_provider_client, resolve_provider_settings
from src.hephaestus.providers.base import ProviderClient
from src.hephaestus.providers.baseten import BasetenClient
from src.hephaestus.providers.openai import OpenAIClient
from src.hephaestus.providers.sagemaker import SagemakerClient
from src.hephaestus.providers.tool_types import GenerateResponse, ToolCall
from src.hephaestus.types import ChainConfig, EvalConfig

_MESSAGES = [{"role": "user", "content": "Use the schema canary."}]
_SCHEMA_CANARY = [
    {
        "type": "function",
        "function": {
            "name": "schema_canary",
            "description": "A capability-contract canary.",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        },
    }
]


class _TextOnlyProvider(ProviderClient):
    """Base-provider probe that records only its text-generation input."""

    def __init__(self) -> None:
        self.messages: List[List[Dict[str, str]]] = []

    def generate(self, messages: List[Dict[str, str]]) -> str:
        self.messages.append(messages)
        return "base text"


class _RecordingProvider:
    """Minimal provider for testing node-level message construction."""

    def __init__(self) -> None:
        self.calls: List[List[Dict[str, str]]] = []

    def generate(self, messages: List[Dict[str, str]]) -> str:
        self.calls.append(messages)
        return "node text"


class _NoToolManager:
    """Real node/executor probe with one discoverable but unavailable tool."""

    def __init__(self) -> None:
        self.lookups: List[str] = []

    def list_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="schema_canary",
                description="Canary tool",
                input_schema={"type": "object", "properties": {}},
                server_name="test",
            )
        ]

    def get_tool(self, name: str) -> None:
        self.lookups.append(name)
        return None


class _TwoToolCallProvider:
    """Returns two calls, so the node's per-iteration ceiling is observable."""

    def __init__(self) -> None:
        self.calls: List[List[Dict[str, str]]] = []
        self.tool_schemas: List[Dict[str, Any]] | None = None

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
    ) -> GenerateResponse:
        self.calls.append(messages)
        self.tool_schemas = tools
        return GenerateResponse(
            content="inspect",
            tool_calls=[
                ToolCall(id="call-1", name="schema_canary", arguments={}),
                ToolCall(id="call-2", name="schema_canary", arguments={}),
            ],
            finish_reason="tool_calls",
        )


def _tool_call_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="call-1",
                            function=SimpleNamespace(
                                name="schema_canary",
                                arguments='{"value": "observed"}',
                            ),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ]
    )


def test_base_baseten_and_sagemaker_tool_requests_remain_text_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch a provider beginning to forward schemas without a tool implementation."""
    base = _TextOnlyProvider()
    base_response = base.generate_with_tools(_MESSAGES, tools=_SCHEMA_CANARY)

    baseten_completions = DummyCompletions()
    baseten_response = BasetenClient(client=DummyClient(baseten_completions)).generate_with_tools(
        _MESSAGES, tools=_SCHEMA_CANARY
    )

    monkeypatch.setenv("X_API_KEY", "test-key")
    sagemaker_payload: Dict[str, Any] = {}

    class _Response:
        def read(self) -> bytes:
            return b'{"content": "sagemaker text"}'

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
            return False

    def fake_urlopen(request: Any, timeout: int) -> _Response:
        sagemaker_payload.update(json.loads(request.data.decode("utf-8")))
        return _Response()

    sagemaker_response = SagemakerClient(
        api_url="https://example.invalid/invoke", urlopen_fn=fake_urlopen
    ).generate_with_tools(_MESSAGES, tools=_SCHEMA_CANARY)

    assert base_response.content == "base text"
    assert base_response.tool_calls is None
    assert base.messages == [_MESSAGES]
    assert baseten_response.content == "ok"
    assert baseten_response.tool_calls is None
    assert baseten_completions.called_with is not None
    assert "tools" not in baseten_completions.called_with
    assert sagemaker_response.content == "sagemaker text"
    assert sagemaker_response.tool_calls is None
    assert "tools" not in sagemaker_payload


def test_openai_non_reasoning_forwards_schemas_and_parses_tool_calls() -> None:
    """Catch a regression that silently turns supported OpenAI tool calls into text."""
    completions = DummyCompletions()
    captured: Dict[str, Any] = {}

    def record_create(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return _tool_call_response()

    completions.create = record_create  # type: ignore[method-assign]
    provider = OpenAIClient(model="gpt-4o", client=DummyClient(completions))

    response = provider.generate_with_tools(_MESSAGES, tools=_SCHEMA_CANARY)

    assert captured["tools"] == _SCHEMA_CANARY
    assert response.finish_reason == "tool_calls"
    assert response.tool_calls == [
        ToolCall(id="call-1", name="schema_canary", arguments={"value": "observed"})
    ]


@pytest.mark.parametrize(
    "model",
    ["o1-canary", "o3-canary", "o4-canary", "gpt-5-canary", "gpt5-canary"],
)
def test_openai_reasoning_prefixes_fall_back_without_forwarding_schemas(model: str) -> None:
    """Catch an unsupported current prefix starting a partial tool-call path."""
    completions = DummyCompletions()
    provider = OpenAIClient(model=model, client=DummyClient(completions))

    response = provider.generate_with_tools(_MESSAGES, tools=_SCHEMA_CANARY)

    assert response.content == "ok"
    assert response.tool_calls is None
    assert completions.called_with is not None
    assert "tools" not in completions.called_with


@pytest.mark.parametrize("supports_tools", [False, True])
def test_supports_tools_setting_cannot_change_resolved_openai_tool_capability(
    supports_tools: bool,
) -> None:
    """Catch a config-only capability override being accepted without implementation."""
    resolved = resolve_provider_settings(
        "openai", {"model": "gpt-4o", "supports_tools": supports_tools}
    )
    assert "supports_tools" not in resolved
    assert resolved == resolve_provider_settings("openai", {"model": "gpt-4o"})

    completions = DummyCompletions()
    captured: Dict[str, Any] = {}

    def record_create(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return _tool_call_response()

    completions.create = record_create  # type: ignore[method-assign]
    provider = build_provider_client(
        "openai", {"model": "gpt-4o", "supports_tools": supports_tools}
    )
    provider._client = DummyClient(completions)  # type: ignore[attr-defined]

    response = provider.generate_with_tools(_MESSAGES, tools=_SCHEMA_CANARY)

    assert captured["tools"] == _SCHEMA_CANARY
    assert response.tool_calls == [
        ToolCall(id="call-1", name="schema_canary", arguments={"value": "observed"})
    ]


def test_top_level_mcp_limits_are_not_injected_into_a_generic_tenant_factory(
    tmp_path: Path,
) -> None:
    """Catch an undocumented change that rewrites arbitrary tenant chain config."""
    factory = tmp_path / "generic_chain.py"
    factory.write_text(
        """
def build_chain(provider, config):
    def node(state):
        return {"output_text": str(config.get("max_iterations", "unset"))}
    return node
""",
        encoding="utf-8",
    )
    raw_config = {
        "tenant_id": "demo",
        "provider": "openai",
        "dataset": {"path": str(tmp_path / "cases.jsonl")},
        "chain": {"path": str(factory), "fn": "build_chain", "config": {}},
        "scoring_profile": {},
        "output_dir": str(tmp_path / "out"),
        "mcp": {
            "servers": [],
            "tool_execution": {
                "max_iterations": 1,
                "max_tool_calls_per_iteration": 1,
                "timeout_seconds": 1,
            },
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")

    config = eval_runner.load_eval_config(config_path)
    node = eval_runner._ensure_chain(config, _TextOnlyProvider())

    assert config.mcp == MCPConfig(
        servers=[], max_iterations=1, max_tool_calls_per_iteration=1, timeout_seconds=1
    )
    assert node({})["output_text"] == "unset"


def test_explicit_executor_and_node_limits_bound_tool_execution(tmp_path: Path) -> None:
    """Catch a node or executor ignoring the limits passed directly to it."""
    manager = _NoToolManager()
    executor = MCPToolExecutor(manager, max_tool_calls=1)

    first = executor.execute(ToolCall(id="one", name="schema_canary", arguments={}))
    second = executor.execute(ToolCall(id="two", name="schema_canary", arguments={}))

    template = tmp_path / "agent.md"
    template.write_text("System: tools\nUser: ${question}", encoding="utf-8")
    provider = _TwoToolCallProvider()
    node = make_agentic_node(
        provider=provider,
        prompt_template_path=template,
        mcp_manager=manager,
        max_iterations=1,
        max_tool_calls_per_iteration=1,
    )
    result = node({"context": {"question": "test"}, "step_outputs": {}})

    assert first.error == "Tool 'schema_canary' not found"
    assert second.error == "Exceeded max_tool_calls limit (1)"
    assert manager.lookups == ["schema_canary", "schema_canary"]
    assert provider.tool_schemas is not None
    assert len(provider.tool_schemas) == 1
    assert result["output_text"] == "inspect"
    assert len(result["tool_call_history"]) == 1
    assert result["tool_call_history"][0]["tool"] == "schema_canary"


def test_skill_paths_require_explicit_rendering_and_one_ordered_runtime_message(
    tmp_path: Path,
) -> None:
    """Catch generic chain loading inventing skills or explicit injection duplicating them."""
    template = tmp_path / "prompt.md"
    template.write_text("System: guardrails\nUser: ${question}", encoding="utf-8")
    first_skill = tmp_path / "first-skill" / "variant-001.md"
    second_skill = tmp_path / "second-skill" / "variant-001.md"
    first_skill.parent.mkdir()
    second_skill.parent.mkdir()
    first_skill.write_text("First skill canary.", encoding="utf-8")
    second_skill.write_text("Second skill canary.", encoding="utf-8")

    factory = tmp_path / "tenant_chain.py"
    factory.write_text(
        """
from pathlib import Path
from src.hephaestus.chains.nodes import make_llm_node

def build_chain(provider, config):
    return make_llm_node(provider, Path(config["prompt_path"]))
""",
        encoding="utf-8",
    )
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text('{"case_id": "1"}\n', encoding="utf-8")
    config = EvalConfig(
        tenant_id="demo",
        provider="openai",
        provider_settings={},
        dataset_path=str(dataset),
        scoring_profile={},
        output_dir=str(tmp_path / "out"),
        chain=ChainConfig(
            path=str(factory),
            fn="build_chain",
            config={
                "prompt_path": str(template),
                "skill_paths": [str(first_skill), str(second_skill)],
                "optimization_target": "prompt",
            },
        ),
    )
    eval_runner._validate_eval_paths(config)
    provider = _RecordingProvider()

    generic_node = eval_runner._ensure_chain(config, provider)
    generic_node({"context": {"question": "test"}, "step_outputs": {}})

    assert "First skill canary." not in "\n".join(
        message["content"] for message in provider.calls[0]
    )

    skills_text = render_skills_block([str(first_skill), str(second_skill)])
    explicit_node = make_llm_node(provider, template, skills_text=skills_text)
    explicit_node({"context": {"question": "test"}, "step_outputs": {}})

    messages = provider.calls[1]
    skills_messages = [
        message for message in messages if "<available_skills>" in message["content"]
    ]
    assert len(skills_messages) == 1
    assert messages[1] == skills_messages[0]
    skills_content = skills_messages[0]["content"]
    assert skills_content.index("### First Skill") < skills_content.index("### Second Skill")
    assert "First skill canary." in skills_content
    assert "Second skill canary." in skills_content
