# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Regression checks for documentation that describes the runtime boundary."""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from types import SimpleNamespace

from src.hephaestus.chains.agentic_nodes import make_agentic_node
from src.hephaestus.mcp.types import MCPConfig, MCPServerConfig
from src.hephaestus.runs.io_utils import render_summary
from src.hephaestus.runs.mcp_facts import safe_mcp_facts

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _compact(text: str) -> str:
    """Normalize Markdown wrapping while preserving the asserted wording."""
    return " ".join(text.split())


def _fenced_blocks(text: str, language: str) -> list[str]:
    """Return Markdown fence bodies for one exact language tag."""
    return re.findall(rf"```{re.escape(language)}\n(.*?)```", text, re.DOTALL)


def test_prompt_iteration_loop_is_the_canonical_exact_enforcement_table() -> None:
    loop = _compact(_read("docs/processes/prompt-iteration-loop.md"))
    readme = _compact(_read("README.md"))

    expected_rows = (
        "| **Runtime-enforced** | config/schema validation; duplicate physical "
        "`case_id` rejection; exclusive output reservation; per-case execution "
        "status; successful-only aggregates; manifest authentication; and "
        "run-identity comparison controls. |",
        "| **Agent-enforced / bypassable** | tenant playbook and scope; "
        "training-only authoring; independent variant review; clone-new-variant; "
        "fixed scorer; validation-only selection; and iteration memory. |",
        "| **Recommended conventions** | one focused edit; smallest useful/prompt-first "
        "escalation; repeated trials; scorer/judge calibration; and untouched future "
        "validation. |",
    )
    for row in expected_rows:
        assert row in loop

    assert (
        "[canonical enforcement boundary]"
        "(docs/processes/prompt-iteration-loop.md#enforcement-boundary)" in readme
    )
    assert "not an operating-system sandbox" in readme
    for row in expected_rows:
        assert row not in readme


def test_run_bundle_and_privacy_docs_match_authoritative_runtime() -> None:
    readme = _compact(_read("README.md"))
    paths = _compact(_read("docs/references/eval_paths.md"))

    for required in (
        "`run_manifest.json`",
        "`completed`, `degraded`, or `failed`",
        "not a privacy boundary",
        "does not persist raw dataset `context` or `expected` fields by default",
        "tool arguments, and tool results can repeat tenant data",
        "fatal setup or runtime failure can leave only an unverified `progress.json`",
        "installs `run_manifest.json` last",
        "safe, resolved projection",
        "does not serialize credentials, raw `chain.config`, full MCP command "
        "paths, argument values, or environment values",
        "does record each command basename, argument count, and environment variable names",
    ):
        assert required in readme + paths
    for artifact in (
        "`progress.json`",
        "`results.jsonl`",
        "`run_config.json`",
        "`run_identity.json`",
        "`summary.md`",
        "`run_manifest.json`",
    ):
        assert artifact in paths


def test_architecture_lifecycle_matches_the_snapshot_before_callback_runtime() -> None:
    architecture = _compact(_read("docs/architecture.md"))
    lifecycle = " ".join(architecture.replace("│", "").split())

    assert "chain.invoke" not in architecture
    assert architecture.count("run_evaluation(config)") == 2
    assert architecture.count("chain.stream") == 2
    for required in (
        "Deep-copy caller config and validate the copied paths",
        "Single complete-dataset byte snapshot and duplicate physical `case_id` rejection",
        "Reserve an absent output directory and initialize progress",
        "Before callbacks, snapshot copied execution config; chain/scorer package "
        "`.py` files; declared prompts, skills, and case prompts; and runtime facts",
        "Resolve provider settings/facts → load and validate scorer → start MCP "
        "and discover tools → build provider → load chain factory",
        "Stream each case with `chain.stream` → score → record per-case outcome",
        "Tear down MCP while the input snapshot remains live",
        "Build safe identity/config, results, successful-only aggregates, summary, "
        "and in-memory attribution",
        "Exit and clean up the temporary snapshot",
        "Publish terminal artifacts, with `run_manifest.json` installed last, then "
        "return immediately",
    ):
        assert required in lifecycle


def test_runtime_behavior_docs_cover_attribution_provider_and_mcp_limits() -> None:
    readme = _compact(_read("README.md"))
    config = _compact(_read("docs/config-schema.md"))
    mcp = _compact(_read("docs/mcp-quick-start.md"))

    for required in (
        "deterministic, rule-based runtime attribution",
        "later agent semantic analysis",
        "OpenAI non-reasoning models forward tool schemas",
        "`o1`, `o3`, `o4`, `gpt-5`, and `gpt5` are text-only",
        "Baseten and SageMaker are text-only",
        "does not automatically wire `mcp.tool_execution` into a generic tenant factory",
        "explicit `make_agentic_node` arguments control the ReAct limits",
        "top-level `max_tool_calls` is not wired into the MCP executor",
        "one aggregate startup-ready wait ceiling",
        "does not enforce a per-server connection deadline",
        "standard `make_agentic_node` always uses the executor's 30-second default",
    ):
        assert required in readme + config + mcp


def test_runtime_docs_qualify_agent_conventions_and_mcp_limit_wiring() -> None:
    readme = _compact(_read("README.md"))
    config = _compact(_read("docs/config-schema.md"))
    mcp = _compact(_read("docs/mcp-quick-start.md"))

    for required in (
        "**All four are agent-enforced / bypassable**",
        "organizational only, not a runtime-enforced isolation boundary",
        "**prompt-first convention is recommended, not runtime-enforced**",
        "provider/model tool-calling capability",
        "**Do not change top-level `mcp.tool_execution` to alter a node or executor**",
        "Changing the executor timeout requires a custom agentic node",
        "when `run_evaluation` calls its path/preflight validation, not by `load_eval_config`",
    ):
        assert required in readme + config + mcp


def test_mcp_example_scores_and_diagnostics_match_runtime() -> None:
    example = _read("docs/examples/mcp-react-example.md")
    output = json.loads(_fenced_blocks(example, "json")[-1])
    assert output["output_text"] == output["step_outputs"]["answer"]
    assert output["diagnostics"] == [
        "Agentic node 'answer': 2 iterations, 1 tool calls total"
    ]

    scorer_source = next(
        block
        for block in _fenced_blocks(example, "python")
        if "class TaskScorer" in block
    )
    namespace: dict[str, object] = {}
    exec(compile(scorer_source, "<documented-task-scorer>", "exec"), namespace)
    scorer = namespace["TaskScorer"]()
    case = SimpleNamespace(
        case_id="1",
        context={"task": "What is the current population of Tokyo?"},
        expected={
            "answer": "approximately 14 million",
            "tools_used": ["brave_web_search"],
        },
    )
    scorer.validate_case(case, {})
    score = scorer.score_pipeline_case(
        case,
        output["step_outputs"],
        {},
        output_text=output["output_text"],
        tool_call_history=output["tool_call_history"],
    )
    assert score == {
        "composite_score": 100.0,
        "score_breakdown": {
            "answer_present": 100.0,
            "answer_quality": 100.0,
            "tool_usage": 100.0,
            "efficiency": 100.0,
        },
    }
    assert output["composite_score"] == score["composite_score"]
    assert output["score_breakdown"] == score["score_breakdown"]


def test_comparison_identity_and_provenance_docs_are_bounded() -> None:
    config = _compact(_read("docs/config-schema.md"))

    expected_dimensions = (
        "prompts",
        "skills",
        "chain_parameters",
        "chain_structure",
        "provider",
        "model",
        "sampling",
        "mcp_capabilities",
    )
    for dimension in expected_dimensions:
        assert f"`{dimension}`" in config
    for required in (
        "dataset, split, scorer, and metric are permanent controls",
        "`provider`, `model`, and `sampling` are independent dimensions",
        "does not require also declaring `provider`",
        "does not guarantee that a rerun reproduces the same output",
        "`provider_revision`",
        "`model_revision`",
        "`api_revision`",
        "`provider_request_id`",
        "`provider_response_id`",
        "`implementation_revision`",
        '`{"status": "unavailable"}`',
    ):
        assert required in config


def test_mcp_example_uses_supported_fields_and_real_trajectory_scoring() -> None:
    example = _read("docs/examples/mcp-react-example.md")

    assert '"supports_tools"' not in example
    assert '"config_path"' not in example
    assert "allowed_tools=" not in example
    assert "mcp_server_brave_search" not in example
    assert '"command": "npx"' in example
    assert '"args": ["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"]' in example
    assert "https://github.com/brave/brave-search-mcp-server" in example
    assert "brave_web_search" in example
    assert "tool_call_history" in example
    assert "score_pipeline_case" in example
    assert "does not assume tool usage from answer quality" in example
    assert '"tools_used": ["brave_web_search"]' in example
    assert "limits = config[\"agent_limits\"]" in example
    assert "max_iterations=limits[\"max_iterations\"]" in example
    assert 'assert "answer" in case.expected or "answer_contains" in case.expected' in example
    assert "from pathlib import Path" in example
    assert "from langgraph.graph import END, StateGraph" in example
    assert "\n        }\n        }\n```" not in example


def test_skill_paths_are_explicit_tenant_chain_work() -> None:
    readme = _compact(_read("README.md"))
    architecture = _compact(_read("docs/architecture.md"))
    config = _compact(_read("docs/config-schema.md"))

    for required in (
        "does not itself inject a skill into a tenant chain",
        "render_skills_block",
        "skills_text",
        "preserves each configured skill-directory name as a distinct heading after snapshotting",
        "preserves configured order",
    ):
        assert required in readme + architecture + config


def test_architecture_documents_the_actual_pipeline_scorer_arguments() -> None:
    architecture = _compact(_read("docs/architecture.md"))

    assert "always passes final `output_text`" in architecture
    assert (
        "passes `tool_call_history` only when the scorer signature accepts it"
        in architecture
    )
    assert (
        "the default implementation forwards final `output_text` to `score_case`"
        in architecture
    )


def test_mcp_quick_start_qualifies_the_unbundled_dataset_and_parses_one_jsonl_row() -> None:
    quick_start = _compact(_read("docs/mcp-quick-start.md"))
    config = json.loads(_read("tenants/mcp_example/configs/eval.json"))
    dataset_path = REPO_ROOT / config["dataset"]["path"]

    assert dataset_path.exists() or (
        "does not include `tenants/mcp_example/datasets/tool_tasks.jsonl`"
        in quick_start
    )
    assert "complete, runnable example" not in quick_start
    assert "The dataset has 30 cases" not in quick_start
    assert (
        "head -n 1 tenants/mcp_example/evals/run-001/results.jsonl | "
        "python3 -m json.tool" in quick_start
    )
    assert (
        "cat tenants/mcp_example/evals/run-001/results.jsonl | "
        "python3 -m json.tool" not in quick_start
    )


def test_mcp_timeout_docs_match_the_standard_node_and_manager_boundary() -> None:
    quick_start = _compact(_read("docs/mcp-quick-start.md"))

    assert "timeout_seconds" not in inspect.signature(make_agentic_node).parameters
    for required in (
        "one aggregate startup-ready wait ceiling",
        "does not enforce a per-server connection deadline",
        "maximum enabled-server value plus 30 seconds",
        "standard `make_agentic_node` always uses the executor's 30-second default",
        "Changing the executor timeout requires a custom agentic node",
    ):
        assert required in quick_start


def test_mcp_privacy_docs_name_the_metadata_that_is_actually_persisted() -> None:
    paths = _compact(_read("docs/references/eval_paths.md"))
    secret = "secret-value-canary"
    facts = safe_mcp_facts(
        MCPConfig(
            servers=[
                MCPServerConfig(
                    name="search",
                    command="/private/bin/server",
                    args=["--token", secret],
                    env={"MCP_TOKEN": secret},
                )
            ]
        ),
        {},
    )

    assert facts["servers"] == [
        {
            "name": "search",
            "enabled": True,
            "timeout_seconds": 30,
            "command_name": "server",
            "argument_count": 2,
            "environment_variable_names": ["MCP_TOKEN"],
        }
    ]
    assert secret not in json.dumps(facts)
    assert "full MCP command paths, argument values, or environment values" in paths
    assert "does record each command basename, argument count, and environment variable names" in paths


def test_readme_describes_final_step_fallback_and_conditional_summary_output() -> None:
    readme = _compact(_read("README.md"))
    perfect_summary = render_summary(
        [
            {
                "case_id": "perfect",
                "execution_status": "succeeded",
                "composite_score": 100.0,
                "step_outputs": {"answer": "correct"},
            }
        ]
    )
    failed_summary = render_summary(
        [
            {
                "case_id": "failed",
                "execution_status": "succeeded",
                "composite_score": 50.0,
                "step_outputs": {"answer": "wrong"},
            }
        ]
    )

    assert "## Step Attribution" not in perfect_summary
    assert "## Step Attribution" in failed_summary
    assert "caller-supplied in-memory case context and expected-answer evidence" in readme
    assert "does not persist that joined protected evidence" in readme
    assert "low-confidence final-step fallback" in readme
    assert "Format failures and low-confidence final-step fallbacks" in readme
    assert "does not prove that the inputs were good or that reasoning was the cause" in readme
    assert "only when the run has step outputs and at least one failure" in readme
    assert "Reasoning failures — all inputs were good" not in readme
    assert "appears automatically in each run's `summary.md`" not in readme


def test_web_ui_labels_run_authority_and_authenticates_studio_ground_truth() -> None:
    web_ui = _compact(_read("docs/web-ui.md"))

    for required in (
        "`authoritative`",
        "`invalid_unverified`",
        "`legacy_unverified`",
        "`live_unverified`",
        "validated `run_manifest.json`",
        "authenticated only when the bundle's dataset path agrees with its run identity",
        "dataset bytes match the recorded fingerprint",
        "Studio dataset ground truth is not joined from a fallback path",
        "`results.jsonl`, `run_config.json`, `summary.md`, `progress.json`, or `run_manifest.json`",
    ):
        assert required in web_ui


def test_iteration_doc_keeps_generic_synthetic_agents_separate_from_studio_stage_7() -> None:
    loop = _compact(_read("docs/processes/prompt-iteration-loop.md"))

    assert "generic tenant-level synthetic-data helpers" in loop
    assert "not Evaluation Asset Studio Stage 7" in loop


def test_feedback_flow_retains_narrow_stage_3_and_stage_7_guarantees() -> None:
    flow = _compact(_read("docs/processes/feedback-dataset-flow.md"))

    for required in (
        "eligible training feedback only",
        "never expose protected criteria to Stages 5–7, later provider payloads, or UI previews",
        "Synthetic proposals are requested only for clusters with a scoreable inferred rubric",
        "They do not define new trusted intents or correctness criteria.",
        "Mechanically accepted synthetic cases remain pending until an "
        "exact-fingerprint review approves them.",
        "derived cases never enter `regression_trusted`",
    ):
        assert required in flow
