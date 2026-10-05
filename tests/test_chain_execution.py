# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for chain execution in eval_runner.

Covers _ensure_chain and run_evaluation with chain-based execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from helpers import TrackingProvider, write_dataset, write_scorer

import src.hephaestus.runs.eval_runner as eval_runner
from src.hephaestus.runs.eval_runner import run_evaluation
from src.hephaestus.types import ChainConfig, EvalConfig


class _ErrorProvider:
    """Mock provider that raises on generate()."""

    def generate(self, messages: List[Dict[str, str]]) -> str:
        raise RuntimeError("Provider error: model unavailable")


def _write_llm_chain(tmp_path: Path, template_path: Path) -> Path:
    """Create a 1-node chain wrapping make_llm_node for the given template."""
    chain_file = tmp_path / "chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.nodes import make_llm_node
from pathlib import Path

def build_chain(provider, config):
    p = Path(config['prompt_path'])
    graph = StateGraph(dict)
    graph.add_node('llm', make_llm_node(provider, p))
    graph.set_entry_point('llm')
    graph.add_edge('llm', END)
    return graph.compile()
""",
        encoding="utf-8",
    )
    return chain_file


def test_ensure_chain_loads_factory(tmp_path: Path) -> None:
    """Chain config loads and invokes factory."""
    template = tmp_path / "variant.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")

    chain_file = tmp_path / "my_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.nodes import make_llm_node
from pathlib import Path

def build_chain(provider, config):
    prompt_path = Path(config['prompt_path'])
    graph = StateGraph(dict)
    graph.add_node('classify', make_llm_node(provider, prompt_path))
    graph.set_entry_point('classify')
    graph.add_edge('classify', END)
    return graph.compile()
""",
        encoding="utf-8",
    )

    provider = TrackingProvider(["factory chain response"])
    config = EvalConfig(
        tenant_id="demo",
        provider="baseten",
        provider_settings={},
        dataset_path="",
        scoring_profile={},
        output_dir="",
        chain=ChainConfig(
            path=str(chain_file),
            fn="build_chain",
            config={"prompt_path": str(template)},
        ),
    )

    from src.hephaestus.runs.eval_runner import _ensure_chain

    chain = _ensure_chain(config, provider)
    state: Dict[str, Any] = {
        "context": {"inputs.Name": "Bob"},
        "output_text": "",
        "step_outputs": {},
    }
    result = chain.invoke(state)

    assert result["output_text"] == "factory chain response"
    assert len(provider.calls) == 1


def test_chain_execution_single_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mock provider, verify single LLM call per case."""
    dataset = write_dataset(tmp_path, cases=2)
    template = tmp_path / "variant.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    scorer = write_scorer(tmp_path)
    chain_file = _write_llm_chain(tmp_path, template)

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {"prompt_path": str(template)},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    tracking = TrackingProvider(["response1", "response2"])
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: tracking,
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 2
    assert len(tracking.calls) == 2
    assert results[0]["output_text"] == "response1"
    assert results[1]["output_text"] == "response2"


def _write_multi_node_chain(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a 2-node chain with prompt templates."""
    template1 = tmp_path / "step1.md"
    template1.write_text("User: analyze ${inputs.Name}", encoding="utf-8")
    template2 = tmp_path / "step2.md"
    template2.write_text("User: summarize ${steps.step1.output}", encoding="utf-8")

    chain_file = tmp_path / "multi_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.nodes import make_llm_node
from pathlib import Path

def build_chain(provider, config):
    p1 = Path(config['prompt_paths']['step1'])
    p2 = Path(config['prompt_paths']['step2'])
    graph = StateGraph(dict)
    graph.add_node('step1', make_llm_node(provider, p1, output_key='step1'))
    graph.add_node('step2', make_llm_node(provider, p2, output_key='step2'))
    graph.set_entry_point('step1')
    graph.add_edge('step1', 'step2')
    graph.add_edge('step2', END)
    return graph.compile()
""",
        encoding="utf-8",
    )
    return chain_file, template1, template2


def _write_multi_node_config(
    tmp_path: Path,
    chain_file: Path,
    template1: Path,
    template2: Path,
) -> Path:
    """Create a config file for a multi-node chain."""
    dataset = write_dataset(tmp_path, cases=1)
    scorer = write_scorer(tmp_path)

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {
                "prompt_paths": {
                    "step1": str(template1),
                    "step2": str(template2),
                },
            },
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_chain_execution_multi_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify context threading across nodes in multi-node chain."""
    chain_file, template1, template2 = _write_multi_node_chain(tmp_path)
    config_path = _write_multi_node_config(tmp_path, chain_file, template1, template2)

    tracking = TrackingProvider(["step1 output", "step2 final"])
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: tracking,
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 1
    assert results[0]["output_text"] == "step2 final"
    # Verify context threading: step2 prompt should contain step1's output
    assert len(tracking.calls) == 2
    step2_messages = tracking.calls[1]
    step2_text = " ".join(msg["content"] for msg in step2_messages)
    assert "step1 output" in step2_text


def test_chain_execution_step_outputs_in_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multi-step chain includes step_outputs in results."""
    chain_file, template1, template2 = _write_multi_node_chain(tmp_path)
    config_path = _write_multi_node_config(tmp_path, chain_file, template1, template2)

    tracking = TrackingProvider(["step1 result", "step2 result"])
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: tracking,
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert "step_outputs" in results[0]
    assert results[0]["step_outputs"]["step1"] == "step1 result"
    assert results[0]["step_outputs"]["step2"] == "step2 result"

    # Verify run_config.json includes chain config
    run_config = json.loads((tmp_path / "out" / "run_config.json").read_text())
    assert "chain" in run_config
    assert run_config["chain"]["path"] == str(chain_file)


def test_chain_execution_error_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Provider errors become sanitized failed case outcomes."""
    dataset = write_dataset(tmp_path, cases=1)
    template = tmp_path / "variant.md"
    template.write_text("User: hello ${inputs.Name}", encoding="utf-8")
    scorer = write_scorer(tmp_path)
    chain_file = _write_llm_chain(tmp_path, template)

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {"prompt_path": str(template)},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: _ErrorProvider(),
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 1
    assert results[0]["output_text"] == ""
    assert results[0]["execution_status"] == "failed"
    assert results[0]["execution_error"] == {
        "phase": "chain",
        "category": "runtime",
        "summary": "Chain execution failed.",
    }


def test_chain_with_custom_state_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chain with domain-specific state fields beyond standard protocol still works."""
    dataset = write_dataset(tmp_path, cases=1)
    scorer = write_scorer(tmp_path)

    chain_file = tmp_path / "custom_state_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from typing import Any, Dict

def _custom_node(state: Dict[str, Any]) -> Dict[str, Any]:
    step_outputs = dict(state.get('step_outputs', {}))
    step_outputs['custom'] = 'result'
    return {
        'output_text': 'custom output',
        'step_outputs': step_outputs,
        'confidence': 0.95,
        'domain_tags': ['security'],
    }

def build_chain(provider, config):
    graph = StateGraph(dict)
    graph.add_node('custom', _custom_node)
    graph.set_entry_point('custom')
    graph.add_edge('custom', END)
    return graph.compile()
""",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: None,
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 1
    assert results[0]["output_text"] == "custom output"
    assert results[0]["composite_score"] == 100.0


def test_chain_missing_output_text_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Eval runner warns when chain returns state without output_text."""
    dataset = write_dataset(tmp_path, cases=1)
    scorer = write_scorer(tmp_path)
    chain_source = tmp_path / "chain.py"
    chain_source.write_text(
        """\
def build_chain(provider, config):
    raise AssertionError("the test replaces chain construction")
""",
        encoding="utf-8",
    )

    config = EvalConfig(
        tenant_id="demo",
        provider="baseten",
        provider_settings={},
        dataset_path=str(dataset),
        scoring_profile={"scorer": {"module_path": str(scorer)}},
        output_dir=str(tmp_path / "out"),
        chain=ChainConfig(path=str(chain_source), fn="build_chain", config={}),
    )

    class BadChain:
        def stream(self, state: Dict[str, Any]) -> list:
            return [{"bad_node": {"context": state["context"], "step_outputs": {}}}]

    monkeypatch.setattr(eval_runner, "_validate_eval_paths", lambda _c: None)
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda _c, _p: BadChain())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda _p, _s: None)

    with caplog.at_level("WARNING", logger="src.hephaestus.runs.eval_runner"):
        results = run_evaluation(config)

    assert any("output_text" in r.message for r in caplog.records)
    assert results[0]["output_text"] == ""


def test_chain_node_error_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chain-node exceptions become sanitized failed case outcomes."""
    dataset = write_dataset(tmp_path, cases=1)
    scorer = write_scorer(tmp_path)

    chain_file = tmp_path / "error_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from typing import Any, Dict

def _failing_node(state: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError('Node computation failed')

def build_chain(provider, config):
    graph = StateGraph(dict)
    graph.add_node('failing', _failing_node)
    graph.set_entry_point('failing')
    graph.add_edge('failing', END)
    return graph.compile()
""",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: None,
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 1
    assert results[0]["output_text"] == ""
    assert results[0]["execution_status"] == "failed"
    assert results[0]["execution_error"] == {
        "phase": "chain",
        "category": "runtime",
        "summary": "Chain execution failed.",
    }


def test_diagnostics_populated_for_unresolved_placeholders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unresolved template placeholders appear in results.diagnostics."""
    dataset = write_dataset(tmp_path, cases=1)
    # Template references ${inputs.Name} (provided) and ${inputs.Age} (NOT provided)
    template = tmp_path / "variant.md"
    template.write_text("User: hello ${inputs.Name}, age ${inputs.Age}", encoding="utf-8")
    scorer = write_scorer(tmp_path)
    chain_file = _write_llm_chain(tmp_path, template)

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {"prompt_path": str(template)},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    tracking = TrackingProvider(["response"])
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: tracking,
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 1
    assert "inputs.Age" in results[0]["diagnostics"]


def _write_single_node_chain(tmp_path: Path) -> tuple[Path, Path]:
    """Create a 1-node explicit chain with a prompt template."""
    template = tmp_path / "step1.md"
    template.write_text("User: analyze ${inputs.Name}", encoding="utf-8")

    chain_file = tmp_path / "single_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.nodes import make_llm_node
from pathlib import Path

def build_chain(provider, config):
    p = Path(config['prompt_path'])
    graph = StateGraph(dict)
    graph.add_node('only_step', make_llm_node(provider, p, output_key='only_step'))
    graph.set_entry_point('only_step')
    graph.add_edge('only_step', END)
    return graph.compile()
""",
        encoding="utf-8",
    )
    return chain_file, template


def test_single_step_explicit_chain_uses_score_pipeline_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 1-step explicit chain config routes through score_pipeline_case, not score_case."""
    chain_file, template = _write_single_node_chain(tmp_path)
    dataset = write_dataset(tmp_path, cases=1)

    scorer_file = tmp_path / "scorer.py"
    scorer_file.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {'composite_score': 50.0, 'score_breakdown': {'via': 50.0}}

    def score_pipeline_case(self, case, step_outputs, scoring_profile, output_text=''):
        return {'composite_score': 99.0, 'score_breakdown': {'via': 99.0}}
""",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {"prompt_path": str(template)},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer_file)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    tracking = TrackingProvider(["single step output"])
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: tracking,
    )

    loaded = eval_runner.load_eval_config(config_path)
    results = run_evaluation(loaded)

    assert len(results) == 1
    # 99.0 proves score_pipeline_case was called, not score_case (which returns 50.0)
    assert results[0]["composite_score"] == 99.0
    assert "step_outputs" in results[0]


def test_chain_does_not_mutate_case_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chain nodes that mutate state['context'] must not affect the original EvalCase."""
    dataset = write_dataset(tmp_path, cases=1)
    scorer = write_scorer(tmp_path)

    chain_file = tmp_path / "mutating_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from typing import Any, Dict

def _mutating_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state['context']['injected'] = 'MUTATED'
    return {'output_text': 'done', 'step_outputs': {'only': 'done'}}

def build_chain(provider, config):
    graph = StateGraph(dict)
    graph.add_node('mutate', _mutating_node)
    graph.set_entry_point('mutate')
    graph.add_edge('mutate', END)
    return graph.compile()
""",
        encoding="utf-8",
    )

    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "demo",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {},
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _p, _s: None,
    )

    loaded = eval_runner.load_eval_config(config_path)
    cases = __import__("src.hephaestus.datasets.jsonl_loader", fromlist=["load_cases"]).load_cases(
        Path(loaded.dataset_path)
    )
    original_context = dict(cases[0].context)

    run_evaluation(loaded)

    # The original EvalCase context must be unchanged
    assert cases[0].context == original_context
    assert "injected" not in cases[0].context
