# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Runtime-integrity regressions at the evaluation-runner boundary."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import src.hephaestus.runs.eval_runner as eval_runner
from src.hephaestus.datasets.jsonl_loader import load_cases_with_identity
from src.hephaestus.mcp.types import MCPConfig, MCPServerConfig, MCPTool
from src.hephaestus.runs.compare import (
    RunComparisonIncompatibilityError,
    compare_runs,
)
from src.hephaestus.runs.mcp_facts import safe_mcp_facts
from src.hephaestus.runs.progress import read_progress
from src.hephaestus.types import ChainConfig, EvalCase, EvalConfig


class _Scorer:
    def __init__(self, *, score: float = 100.0, error: BaseException | None = None) -> None:
        self.score = score
        self.error = error
        self.calls = 0

    def validate_case(self, case: EvalCase, scoring_profile: dict[str, Any]) -> None:
        del case, scoring_profile

    def score_pipeline_case(
        self,
        case: EvalCase,
        step_outputs: dict[str, Any],
        scoring_profile: dict[str, Any],
        *,
        output_text: str,
    ) -> dict[str, Any]:
        del case, step_outputs, scoring_profile, output_text
        self.calls += 1
        if self.error is not None:
            raise self.error
        return {
            "composite_score": self.score,
            "score_breakdown": {"quality": self.score},
        }


class _Chain:
    def __init__(self, error: BaseException | None = None) -> None:
        self.error = error

    def stream(self, state: dict[str, Any]):
        if self.error is not None:
            raise self.error
        name = str(state["context"].get("name", "ok"))
        if name.startswith("fail"):
            raise ConnectionError("case-secret-connection-detail")
        yield {
            "answer": {
                "output_text": name,
                "step_outputs": {"answer": name},
            }
        }


def _case(*, metadata: dict[str, Any] | None = None) -> EvalCase:
    return EvalCase(
        case_id="case-1",
        task_type="demo",
        context={"name": "ok"},
        expected={"answer": "protected"},
        metadata=metadata or {},
    )


def _config(tmp_path: Path, *, rows: list[dict[str, Any]] | None = None) -> EvalConfig:
    dataset = tmp_path / "cases.jsonl"
    if rows is None:
        rows = [
            {
                "case_id": "case-1",
                "task_type": "demo",
                "context": {"name": "ok"},
                "expected": {"answer": "protected"},
                "metadata": {},
            }
        ]
    dataset.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    chain_path = tmp_path / "chain.py"
    chain_path.write_text("def build_chain(provider, config): ...\n", encoding="utf-8")
    scorer_path = tmp_path / "scorer.py"
    scorer_path.write_text("# inert test scorer source\n", encoding="utf-8")
    return EvalConfig(
        tenant_id="demo",
        provider="baseten",
        provider_settings={},
        dataset_path=str(dataset),
        scoring_profile={"scorer": {"module_path": str(scorer_path)}},
        output_dir=str(tmp_path / "out"),
        chain=ChainConfig(path=str(chain_path)),
    )


def test_chain_failure_is_sanitized_and_never_scored() -> None:
    secret = "api-key-super-secret"
    scorer = _Scorer()

    result = eval_runner._evaluate_single_case(
        _case(
            metadata={
                "trust_tier": "inferred_from_trusted_feedback",
                "private": secret,
            }
        ),
        _Chain(RuntimeError(secret)),
        scorer,
        {},
    )

    payload = json.dumps(result.__dict__, sort_keys=True)
    assert result.execution_status == "failed"
    assert result.execution_error is not None
    assert result.execution_error["phase"] == "chain"
    assert result.evaluation_provenance == {
        "trust_tier": "inferred_from_trusted_feedback"
    }
    assert scorer.calls == 0
    assert secret not in payload
    assert "private" not in payload


def test_chain_failure_sanitizes_malformed_partial_state() -> None:
    """Malformed tenant state cannot replace the fixed chain failure result."""

    class MalformedChain:
        def stream(self, _state: dict[str, Any]):
            yield {
                "partial": {
                    "diagnostics": object(),
                    "output_text": object(),
                    "step_outputs": object(),
                    "tool_call_history": ["malformed"],
                }
            }
            raise RuntimeError("protected-chain-detail")

    scorer = _Scorer()
    result = eval_runner._evaluate_single_case(
        _case(),
        MalformedChain(),
        scorer,
        {},
    )

    assert result.execution_status == "failed"
    assert result.execution_error == {
        "phase": "chain",
        "category": "runtime",
        "summary": "Chain execution failed.",
    }
    assert result.diagnostics == ["Chain execution failed."]
    assert result.output_text == ""
    assert result.step_outputs == {}
    assert result.tool_call_history is None
    assert result.total_tool_calls == 0
    assert result.failed_tool_calls == 0
    assert scorer.calls == 0


def test_scorer_failure_is_sanitized_and_preserves_chain_output() -> None:
    secret = "scorer-secret-payload"
    result = eval_runner._evaluate_single_case(
        _case(metadata={"trust_tier": "trusted_feedback"}),
        _Chain(),
        _Scorer(error=ValueError(secret)),
        {},
    )

    payload = json.dumps(result.__dict__, sort_keys=True)
    assert result.execution_status == "failed"
    assert result.execution_error is not None
    assert result.execution_error["phase"] == "scorer"
    assert result.output_text == "ok"
    assert result.step_outputs == {"answer": "ok"}
    assert secret not in payload


def test_malformed_scorer_diagnostics_are_a_sanitized_scorer_failure() -> None:
    """Diagnostics validation belongs to the scorer execution boundary."""

    class MalformedDiagnosticsScorer(_Scorer):
        def score_pipeline_case(
            self,
            case: EvalCase,
            step_outputs: dict[str, Any],
            scoring_profile: dict[str, Any],
            *,
            output_text: str,
        ) -> dict[str, Any]:
            del case, step_outputs, scoring_profile, output_text
            return {
                "composite_score": 100.0,
                "score_breakdown": {"quality": 100.0},
                "diagnostics": object(),
            }

    result = eval_runner._evaluate_single_case(
        _case(),
        _Chain(),
        MalformedDiagnosticsScorer(),
        {},
    )

    assert result.execution_status == "failed"
    assert result.execution_error == {
        "phase": "scorer",
        "category": "runtime",
        "summary": "Scorer execution failed.",
    }
    assert result.diagnostics == ["Scorer execution failed."]
    assert result.output_text == "ok"
    assert result.step_outputs == {"answer": "ok"}


@pytest.mark.parametrize("startup_phase", ["scorer", "mcp", "provider", "chain"])
def test_startup_failure_preserves_exact_exception_and_failed_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    startup_phase: str,
) -> None:
    config = _config(tmp_path)
    sentinel = RuntimeError(f"{startup_phase}-startup-sentinel")
    scorer = _Scorer()

    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: scorer)
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda _name, _settings: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    if startup_phase == "scorer":
        monkeypatch.setattr(
            eval_runner,
            "load_tenant_scorer",
            lambda _profile: (_ for _ in ()).throw(sentinel),
        )
    elif startup_phase == "mcp":
        config.mcp = object()

        class _Manager:
            def __init__(self, *_args: Any, **_kwargs: Any) -> None:
                pass

            def start_servers(self) -> None:
                raise sentinel

            def stop_servers(self) -> None:
                pass

        monkeypatch.setattr(eval_runner, "MCPServerManager", _Manager)
    elif startup_phase == "provider":
        monkeypatch.setattr(
            eval_runner,
            "build_provider_client",
            lambda _name, _settings: (_ for _ in ()).throw(sentinel),
        )
    else:
        monkeypatch.setattr(
            eval_runner,
            "_ensure_chain",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(sentinel),
        )

    with pytest.raises(RuntimeError) as caught:
        eval_runner.run_evaluation(config)

    assert caught.value is sentinel
    progress = read_progress(Path(config.output_dir))
    assert progress is not None
    assert progress.status == "failed"


def test_secondary_progress_failure_never_replaces_startup_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    sentinel = RuntimeError("provider-startup-sentinel")
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda _name, _settings: (_ for _ in ()).throw(sentinel),
    )
    monkeypatch.setattr(
        eval_runner.ProgressTracker,
        "mark_failed",
        lambda _self: (_ for _ in ()).throw(OSError("secondary-progress-error")),
    )

    with pytest.raises(RuntimeError) as caught:
        eval_runner.run_evaluation(config)

    assert caught.value is sentinel


def test_mixed_execution_is_degraded_and_aggregates_successes_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {
            "case_id": "ok-1",
            "task_type": "demo",
            "context": {"name": "ok-1"},
            "expected": {},
            "metadata": {"trust_tier": "trusted_feedback"},
        },
        {
            "case_id": "failed-1",
            "task_type": "demo",
            "context": {"name": "fail-1"},
            "expected": {},
            "metadata": {"trust_tier": "synthetic_from_trusted_rubric"},
        },
        {
            "case_id": "ok-2",
            "task_type": "demo",
            "context": {"name": "ok-2"},
            "expected": {},
            "metadata": {"trust_tier": "inferred_from_trusted_feedback"},
        },
    ]
    config = _config(tmp_path, rows=rows)
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer(score=80.0))
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    results = eval_runner.run_evaluation(config)

    assert [result["execution_status"] for result in results] == [
        "succeeded",
        "failed",
        "succeeded",
    ]
    progress = read_progress(Path(config.output_dir))
    assert progress is not None
    assert progress.status == "degraded"
    assert progress.failed_case_ids == ["failed-1"]
    assert progress.avg_composite_score == 80.0


def test_callback_mutation_cannot_rewrite_provenance_or_attribution_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate/scorer callbacks receive copies, never publication evidence."""
    config = _config(
        tmp_path,
        rows=[
            {
                "case_id": "case-1",
                "task_type": "demo",
                "context": {"name": "original-context-canary"},
                "expected": {"answer": "original-expected-canary"},
                "metadata": {
                    "trust_tier": "synthetic_from_trusted_rubric",
                    "private": "original-metadata-canary",
                },
            }
        ],
    )
    observed_summary_cases: list[dict[str, Any]] = []
    real_render_summary = eval_runner.render_summary

    class MutatingScorer(_Scorer):
        def validate_case(
            self,
            case: EvalCase,
            scoring_profile: dict[str, Any],
        ) -> None:
            del scoring_profile
            case.metadata["trust_tier"] = "inferred_from_trusted_feedback"
            case.context["name"] = "validate-mutated-context"
            case.expected["answer"] = "validate-mutated-expected"

        def score_pipeline_case(
            self,
            case: EvalCase,
            step_outputs: dict[str, Any],
            scoring_profile: dict[str, Any],
            *,
            output_text: str,
        ) -> dict[str, Any]:
            del step_outputs, scoring_profile, output_text
            case.metadata["trust_tier"] = "trusted_feedback"
            case.context["name"] = "score-mutated-context"
            case.expected["answer"] = "score-mutated-expected"
            return {
                "composite_score": 50.0,
                "score_breakdown": {"quality": 50.0},
            }

    def capture_summary(
        results: Any,
        *,
        cases: Any,
    ) -> str:
        observed_summary_cases.extend(
            {
                "context": copy.deepcopy(case.context),
                "expected": copy.deepcopy(case.expected),
                "metadata": copy.deepcopy(case.metadata),
            }
            for case in cases
        )
        return real_render_summary(results, cases=cases)

    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda _profile: MutatingScorer(),
    )
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())
    monkeypatch.setattr(eval_runner, "render_summary", capture_summary)

    results = eval_runner.run_evaluation(config)

    assert results[0]["evaluation_provenance"] == {
        "trust_tier": "synthetic_from_trusted_rubric"
    }
    assert observed_summary_cases == [
        {
            "context": {"name": "original-context-canary"},
            "expected": {"answer": "original-expected-canary"},
            "metadata": {
                "trust_tier": "synthetic_from_trusted_rubric",
                "private": "original-metadata-canary",
            },
        }
    ]
    progress = read_progress(Path(config.output_dir))
    assert progress is not None
    assert set(progress.trust_tier_summaries) == {
        "synthetic_from_trusted_rubric"
    }
    summary = (Path(config.output_dir) / "summary.md").read_text(encoding="utf-8")
    assert "| synthetic_from_trusted_rubric |" in summary
    assert "| trusted_feedback |" not in summary


def test_successful_zero_score_is_completed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer(score=0.0))
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    results = eval_runner.run_evaluation(config)

    assert results[0]["execution_status"] == "succeeded"
    progress = read_progress(Path(config.output_dir))
    assert progress is not None
    assert progress.status == "completed"
    assert progress.avg_composite_score == 0.0


def test_duplicate_case_ids_report_physical_rows_before_any_runtime_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate input identity is rejected before any runtime side effect."""
    config = _config(
        tmp_path,
        rows=[
            {
                "case_id": "duplicate",
                "task_type": "demo",
                "context": {},
                "expected": {},
                "metadata": {},
            },
            {
                "case_id": "duplicate",
                "task_type": "demo",
                "context": {},
                "expected": {},
                "metadata": {},
            },
        ],
    )
    Path(config.dataset_path).write_text(
        """\
{"case_id": "duplicate", "task_type": "demo", "context": {}, "expected": {}, "metadata": {}}

{"case_id": "duplicate", "task_type": "demo", "context": {}, "expected": {}, "metadata": {}}
""",
        encoding="utf-8",
    )
    calls = {"scorer": 0, "mcp": 0, "provider": 0, "chain": 0}

    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda _profile: calls.__setitem__("scorer", calls["scorer"] + 1),
    )
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda *_args: calls.__setitem__("provider", calls["provider"] + 1),
    )
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: calls.__setitem__("chain", calls["chain"] + 1),
    )

    class _Manager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            calls["mcp"] += 1

    config.mcp = object()
    monkeypatch.setattr(eval_runner, "MCPServerManager", _Manager)

    with pytest.raises(ValueError, match=r"rows 1 and 3"):
        eval_runner.run_evaluation(config)

    assert calls == {"scorer": 0, "mcp": 0, "provider": 0, "chain": 0}


@pytest.mark.parametrize("symlink", [False, True])
def test_output_collision_preserves_existing_bytes_before_runtime_factories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    symlink: bool,
) -> None:
    """No factory may run when the output location is already occupied."""
    config = _config(tmp_path)
    output_dir = Path(config.output_dir)
    preserved = tmp_path / "preserved"
    preserved.mkdir()
    preserved_file = preserved / "sentinel.bin"
    preserved_file.write_bytes(b"collision-bytes")
    if symlink:
        try:
            output_dir.symlink_to(preserved, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"symlinks are unavailable: {exc}")
    else:
        output_dir.mkdir()
        (output_dir / "sentinel.bin").write_bytes(preserved_file.read_bytes())
        preserved_file = output_dir / "sentinel.bin"

    calls = {"scorer": 0, "mcp": 0, "provider": 0, "chain": 0}
    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda _profile: calls.__setitem__("scorer", calls["scorer"] + 1),
    )
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda *_args: calls.__setitem__("provider", calls["provider"] + 1),
    )
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: calls.__setitem__("chain", calls["chain"] + 1),
    )

    class _Manager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            calls["mcp"] += 1

    config.mcp = object()
    monkeypatch.setattr(eval_runner, "MCPServerManager", _Manager)

    with pytest.raises(FileExistsError, match="run output already exists"):
        eval_runner.run_evaluation(config)

    assert preserved_file.read_bytes() == b"collision-bytes"
    assert calls == {"scorer": 0, "mcp": 0, "provider": 0, "chain": 0}


def test_runner_routes_all_live_progress_through_reserved_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runner progress persistence retains the writer's directory authority."""
    config = _config(tmp_path)
    payloads: list[dict[str, Any]] = []
    real_write_progress = eval_runner.RunBundleWriter.write_progress

    def capture_write_progress(writer: Any, payload: Any) -> None:
        payloads.append(copy.deepcopy(dict(payload)))
        real_write_progress(writer, payload)

    monkeypatch.setattr(
        eval_runner.RunBundleWriter,
        "write_progress",
        capture_write_progress,
    )
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    eval_runner.run_evaluation(config)

    assert payloads[0]["status"] == "running"
    assert payloads[-1]["status"] == "completed"
    assert payloads[-1]["attempted_case_ids"] == ["case-1"]


def test_runner_publishes_tracker_snapshot_without_rereading_progress_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The authenticated terminal payload comes from tracker-owned memory."""
    config = _config(tmp_path)
    progress_path = Path(config.output_dir) / "progress.json"
    real_read_text = Path.read_text

    def reject_progress_reread(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if path == progress_path:
            raise AssertionError("runner reopened live progress by path")
        return real_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", reject_progress_reread)
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    results = eval_runner.run_evaluation(config)

    assert results[0]["execution_status"] == "succeeded"
    assert (Path(config.output_dir) / "run_manifest.json").is_file()


def test_published_bundle_never_contains_runtime_canaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Protected inputs and exception text remain outside output artifacts and logs."""
    canaries = {
        "context": "context-canary",
        "expected": "expected-canary",
        "metadata": "metadata-canary",
        "endpoint": "endpoint-canary",
        "mcp_argument": "mcp-argument-canary",
        "mcp_environment": "mcp-environment-canary",
        "credential": "credential-canary",
        "exception": "exception-canary",
    }
    config = _config(
        tmp_path,
        rows=[
            {
                "case_id": "case-1",
                "task_type": "demo",
                "context": {"name": canaries["context"]},
                "expected": {"answer": canaries["expected"]},
                "metadata": {
                    "trust_tier": "trusted_feedback",
                    "private": canaries["metadata"],
                },
            }
        ],
    )
    config.provider_settings = {
        "base_url": f"https://{canaries['endpoint']}.example",
        "api_key": canaries["credential"],
    }
    config.mcp = MCPConfig(
        servers=[
            MCPServerConfig(
                name="retrieval",
                command=r"C:\\private\\mcp-server.exe",
                args=["--token", canaries["mcp_argument"]],
                env={"MCP_TOKEN": canaries["mcp_environment"]},
            )
        ]
    )

    class _Manager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.tools: dict[str, Any] = {}

        def start_servers(self) -> None:
            pass

        def stop_servers(self) -> None:
            pass

    monkeypatch.setattr(eval_runner, "MCPServerManager", _Manager)
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: _Chain(RuntimeError(canaries["exception"])),
    )

    eval_runner.run_evaluation(config)

    output_bytes = b"".join(
        artifact.read_bytes()
        for artifact in Path(config.output_dir).rglob("*")
        if artifact.is_file()
    )
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    for canary in canaries.values():
        assert canary.encode("utf-8") not in output_bytes
        assert canary not in log_text


def test_run_uses_pre_callback_artifact_and_config_snapshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Callbacks and concurrent edits cannot move execution or publication authority."""
    chain_package = tmp_path / "chain_package"
    chain_package.mkdir()
    chain_init = chain_package / "__init__.py"
    chain_helper = chain_package / "helper.py"
    chain_module = chain_package / "chain.py"
    chain_init.write_text("", encoding="utf-8")
    chain_helper.write_text('LABEL = "original-helper"\n', encoding="utf-8")
    chain_module.write_text(
        """\
from pathlib import Path

from .helper import LABEL


class Chain:
    def __init__(self, config):
        self.config = config

    def stream(self, state):
        del state
        prompt = Path(self.config["prompt_paths"]["answer"]).read_text(encoding="utf-8")
        skill = Path(self.config["skill_paths"][0]).read_text(encoding="utf-8")
        output = "|".join((LABEL, prompt, skill, self.config["marker"]))
        yield {"answer": {"output_text": output, "step_outputs": {"answer": output}}}


def build_chain(provider, config):
    del provider
    return Chain(config)
""",
        encoding="utf-8",
    )

    scorer_package = tmp_path / "scorer_package"
    scorer_package.mkdir()
    scorer_init = scorer_package / "__init__.py"
    scorer_helper = scorer_package / "helper.py"
    scorer_module = scorer_package / "scorer.py"
    scorer_init.write_text("", encoding="utf-8")
    scorer_helper.write_text("SCORE = 91.0\n", encoding="utf-8")
    scorer_module.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

from .helper import SCORE


class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        del case, scoring_profile

    def score_case(self, case, output_text, scoring_profile):
        del case, output_text
        value = SCORE * float(scoring_profile["scale"])
        return {"composite_score": value, "score_breakdown": {"quality": value}}
""",
        encoding="utf-8",
    )

    prompt = tmp_path / "prompt.md"
    skill = tmp_path / "skill.md"
    prompt.write_text("original-prompt", encoding="utf-8")
    skill.write_text("original-skill", encoding="utf-8")
    config = _config(tmp_path)
    config.chain = ChainConfig(
        path=str(chain_module),
        config={
            "prompt_paths": {"answer": str(prompt)},
            "skill_paths": [str(skill)],
            "optimization_target": "both",
            "marker": "original-marker",
        },
    )
    config.scoring_profile = {
        "scorer": {"module_path": str(scorer_module)},
        "scale": 1,
    }
    config.provider_settings = {"model": "original-model"}
    config.mcp = MCPConfig(
        servers=[MCPServerConfig(name="snapshot-server", command="snapshot-command")]
    )

    snapshotted_bytes = {
        path: path.read_bytes()
        for path in (
            chain_init,
            chain_helper,
            chain_module,
            scorer_init,
            scorer_helper,
            scorer_module,
            prompt,
            skill,
        )
    }
    execution_paths: list[Path] = []
    snapshot_alive_at_stop: list[bool] = []
    real_resolve = eval_runner.resolve_provider_settings
    real_load_scorer = eval_runner.load_tenant_scorer
    real_ensure_chain = eval_runner._ensure_chain

    def mutate_after_snapshot(
        provider_name: str,
        settings: dict[str, object],
    ) -> dict[str, object]:
        config.provider_settings["model"] = "post-start-model"
        config.chain.config["marker"] = "post-start-marker"
        config.scoring_profile["scale"] = 0
        chain_helper.write_text('LABEL = "post-start-helper"\n', encoding="utf-8")
        chain_module.write_text(
            chain_module.read_text(encoding="utf-8") + "\n# post-start edit\n",
            encoding="utf-8",
        )
        scorer_helper.write_text("SCORE = 5.0\n", encoding="utf-8")
        scorer_module.write_text(
            scorer_module.read_text(encoding="utf-8") + "\n# post-start edit\n",
            encoding="utf-8",
        )
        prompt.write_text("post-start-prompt", encoding="utf-8")
        skill.write_text("post-start-skill", encoding="utf-8")
        return real_resolve(provider_name, settings)

    def capture_scorer_path(profile: dict[str, Any]) -> Any:
        execution_paths.append(Path(profile["scorer"]["module_path"]))
        return real_load_scorer(profile)

    def capture_chain_paths(
        execution_config: EvalConfig,
        provider: Any,
        mcp_manager: Any = None,
    ) -> Any:
        execution_paths.extend(
            [
                Path(execution_config.chain.path),
                Path(execution_config.chain.config["prompt_paths"]["answer"]),
                Path(execution_config.chain.config["skill_paths"][0]),
            ]
        )
        return real_ensure_chain(execution_config, provider, mcp_manager=mcp_manager)

    class _Manager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.tools: dict[str, Any] = {}

        def start_servers(self) -> None:
            pass

        def stop_servers(self) -> None:
            snapshot_alive_at_stop.append(all(path.is_file() for path in execution_paths))

    monkeypatch.setattr(eval_runner, "resolve_provider_settings", mutate_after_snapshot)
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", capture_scorer_path)
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", capture_chain_paths)
    monkeypatch.setattr(eval_runner, "MCPServerManager", _Manager)

    results = eval_runner.run_evaluation(config)

    assert results[0]["output_text"] == (
        "original-helper|original-prompt|original-skill|original-marker"
    )
    assert results[0]["composite_score"] == 91.0
    assert execution_paths
    assert all(path not in snapshotted_bytes for path in execution_paths)
    assert snapshot_alive_at_stop == [True]
    assert all(not path.exists() for path in execution_paths)

    run_config = json.loads(
        (Path(config.output_dir) / "run_config.json").read_text(encoding="utf-8")
    )
    assert run_config["chain"]["path"] == str(chain_module)
    assert run_config["scoring_profile"]["scorer_module_path"] == str(scorer_module)
    assert run_config["provider_settings"]["model"] == "original-model"
    assert run_config["chain"]["prompt_artifacts"] == [
        {
            "name": "answer",
            "path": str(prompt),
            "sha256": "sha256:" + hashlib.sha256(snapshotted_bytes[prompt]).hexdigest(),
        }
    ]
    assert run_config["chain"]["skill_artifacts"] == [
        {
            "ordinal": 0,
            "path": str(skill),
            "sha256": "sha256:" + hashlib.sha256(snapshotted_bytes[skill]).hexdigest(),
        }
    ]
    chain_sources = {
        row["path"]: row["sha256"] for row in run_config["chain"]["source_artifacts"]
    }
    scorer_sources = {
        row["path"]: row["sha256"]
        for row in run_config["scoring_profile"]["scorer_source_artifacts"]
    }
    for path in (chain_init, chain_helper, chain_module):
        assert chain_sources[str(path)] == (
            "sha256:" + hashlib.sha256(snapshotted_bytes[path]).hexdigest()
        )
    for path in (scorer_init, scorer_helper, scorer_module):
        assert scorer_sources[str(path)] == (
            "sha256:" + hashlib.sha256(snapshotted_bytes[path]).hexdigest()
        )


def test_same_package_chain_and_scorer_share_one_frozen_module_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Snapshotting preserves shared module state within one tenant package."""
    package = tmp_path / "tenant_package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "shared.py").write_text("CHAIN_EXECUTED = False\n", encoding="utf-8")
    chain_module = package / "chain.py"
    chain_module.write_text(
        """\
from . import shared


class Chain:
    def stream(self, state):
        del state
        shared.CHAIN_EXECUTED = True
        yield {"answer": {"output_text": "shared", "step_outputs": {}}}


def build_chain(provider, config):
    del provider, config
    return Chain()
""",
        encoding="utf-8",
    )
    scorer_module = package / "scorer.py"
    scorer_module.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

from . import shared


class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        del case, scoring_profile

    def score_case(self, case, output_text, scoring_profile):
        del case, output_text, scoring_profile
        if not shared.CHAIN_EXECUTED:
            raise RuntimeError("chain and scorer loaded separate shared modules")
        return {"composite_score": 100.0, "score_breakdown": {"shared": 100.0}}
""",
        encoding="utf-8",
    )
    config = _config(tmp_path)
    config.chain = ChainConfig(path=str(chain_module))
    config.scoring_profile = {"scorer": {"module_path": str(scorer_module)}}

    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())

    results = eval_runner.run_evaluation(config)

    assert results[0]["execution_status"] == "succeeded"
    assert results[0]["composite_score"] == 100.0
    run_config = json.loads(
        (Path(config.output_dir) / "run_config.json").read_text(encoding="utf-8")
    )
    assert (
        run_config["chain"]["source_artifacts"]
        == run_config["scoring_profile"]["scorer_source_artifacts"]
    )


def test_skill_snapshot_preserves_distinct_runtime_headings_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Frozen skill paths preserve the configured skill display identities."""
    research_skill = tmp_path / "skills" / "deep-research" / "variant.md"
    review_skill = tmp_path / "skills" / "code_review" / "variant.md"
    research_skill.parent.mkdir(parents=True)
    review_skill.parent.mkdir(parents=True)
    research_skill.write_text("Research procedure", encoding="utf-8")
    review_skill.write_text("Review procedure", encoding="utf-8")
    chain_module = tmp_path / "skill_chain.py"
    chain_module.write_text(
        """\
from src.hephaestus.engine.skills import render_skills_block


class Chain:
    def __init__(self, skill_paths):
        self.skill_paths = skill_paths

    def stream(self, state):
        del state
        rendered = render_skills_block(self.skill_paths)
        yield {"answer": {"output_text": rendered, "step_outputs": {}}}


def build_chain(provider, config):
    del provider
    return Chain(config["skill_paths"])
""",
        encoding="utf-8",
    )
    config = _config(tmp_path)
    config.chain = ChainConfig(
        path=str(chain_module),
        config={
            "skill_paths": [str(research_skill), str(review_skill)],
            "optimization_target": "prompt",
        },
    )
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())

    results = eval_runner.run_evaluation(config)

    assert results[0]["output_text"] == (
        "### Deep Research\n\nResearch procedure\n\n"
        "### Code Review\n\nReview procedure"
    )


def test_tenant_snapshot_excludes_sibling_sources_and_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sibling tenant is neither read nor allowed to perturb run identity."""
    repository_root = tmp_path / "repository"
    tenants_root = repository_root / "tenants"
    owner_root = tenants_root / "snapshot_owner"
    sibling_root = tenants_root / "sibling_private"
    owner_root.mkdir(parents=True)
    sibling_root.mkdir(parents=True)
    (tenants_root / "__init__.py").write_text("", encoding="utf-8")
    (owner_root / "__init__.py").write_text("", encoding="utf-8")
    (owner_root / "shared.py").write_text('VALUE = "owner"\n', encoding="utf-8")
    chain_module = owner_root / "chain.py"
    chain_module.write_text(
        """\
from tenants.snapshot_owner.shared import VALUE


class Chain:
    def stream(self, state):
        del state
        yield {"answer": {"output_text": VALUE, "step_outputs": {}}}


def build_chain(provider, config):
    del provider, config
    return Chain()
""",
        encoding="utf-8",
    )
    scorer_module = owner_root / "scorer.py"
    scorer_module.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer


class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        del case, scoring_profile

    def score_case(self, case, output_text, scoring_profile):
        del case, output_text, scoring_profile
        return {"composite_score": 100.0, "score_breakdown": {"quality": 100.0}}
""",
        encoding="utf-8",
    )
    sibling_source = sibling_root / "canary.py"
    sibling_source.write_text('SECRET = "sibling-tenant-canary-v1"\n', encoding="utf-8")
    sibling_v1_hash = "sha256:" + hashlib.sha256(sibling_source.read_bytes()).hexdigest()

    stable_runtime = {
        "source_members": [],
        "source_fingerprint": eval_runner.fingerprint_value([]),
        "git": {"status": "unavailable"},
        "python": {"implementation": "CPython", "version": "test"},
        "packages": {},
    }
    monkeypatch.setattr(eval_runner, "_repository_root", lambda: repository_root)
    monkeypatch.setattr(eval_runner, "_runtime_facts", lambda: stable_runtime)
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())

    config = _config(tmp_path)
    config.tenant_id = "snapshot_owner"
    config.chain = ChainConfig(path=str(chain_module))
    config.scoring_profile = {"scorer": {"module_path": str(scorer_module)}}
    eval_runner.run_evaluation(config)
    first_config = json.loads(
        (Path(config.output_dir) / "run_config.json").read_text(encoding="utf-8")
    )
    first_identity = json.loads(
        (Path(config.output_dir) / "run_identity.json").read_text(encoding="utf-8")
    )

    serialized_sources = json.dumps(
        {
            "chain": first_config["chain"]["source_artifacts"],
            "scorer": first_config["scoring_profile"]["scorer_source_artifacts"],
        }
    )
    assert str(sibling_source) not in serialized_sources
    assert sibling_v1_hash not in serialized_sources

    sibling_source.write_text('SECRET = "sibling-tenant-canary-v2"\n', encoding="utf-8")
    second_config = copy.deepcopy(config)
    second_config.output_dir = str(tmp_path / "out-second")
    eval_runner.run_evaluation(second_config)
    second_identity = json.loads(
        (Path(second_config.output_dir) / "run_identity.json").read_text(
            encoding="utf-8"
        )
    )

    assert first_identity["identity_fingerprint"] == second_identity[
        "identity_fingerprint"
    ]


@pytest.mark.parametrize("symlink_scope", ["tenant_root", "nested_directory"])
def test_tenant_snapshot_rejects_ancestor_directory_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    symlink_scope: str,
) -> None:
    """Lexical tenant containment cannot disguise a sibling tenant target."""
    repository_root = tmp_path / "repository"
    tenants_root = repository_root / "tenants"
    owner_root = tenants_root / "owner"
    sibling_root = tenants_root / "sibling"
    sibling_root.mkdir(parents=True)
    (tenants_root / "__init__.py").write_text("", encoding="utf-8")
    (sibling_root / "__init__.py").write_text("", encoding="utf-8")
    (sibling_root / "chain.py").write_text(
        "def build_chain(provider, config): ...\n",
        encoding="utf-8",
    )
    if symlink_scope == "tenant_root":
        link = owner_root
        chain_path = link / "chain.py"
    else:
        owner_root.mkdir()
        (owner_root / "__init__.py").write_text("", encoding="utf-8")
        link = owner_root / "foreign"
        chain_path = link / "chain.py"
    try:
        link.symlink_to(sibling_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    stable_runtime = {
        "source_members": [],
        "source_fingerprint": eval_runner.fingerprint_value([]),
        "git": {"status": "unavailable"},
        "python": {"implementation": "CPython", "version": "test"},
        "packages": {},
    }
    calls = {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}
    monkeypatch.setattr(eval_runner, "_repository_root", lambda: repository_root)
    monkeypatch.setattr(eval_runner, "_runtime_facts", lambda: stable_runtime)
    monkeypatch.setattr(
        eval_runner,
        "resolve_provider_settings",
        lambda *_args: calls.__setitem__("resolver", calls["resolver"] + 1) or {},
    )
    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda *_args: calls.__setitem__("scorer", calls["scorer"] + 1) or _Scorer(),
    )
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda *_args: calls.__setitem__("provider", calls["provider"] + 1) or object(),
    )
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: calls.__setitem__("chain", calls["chain"] + 1)
        or _Chain(),
    )

    config = _config(tmp_path)
    config.tenant_id = "owner"
    config.chain = ChainConfig(path=str(chain_path))
    with pytest.raises(ValueError, match="chain.*ancestor.*symlink"):
        eval_runner.run_evaluation(config)

    assert calls == {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}


@pytest.mark.parametrize(
    "artifact",
    ["dataset", "prompt", "skill", "case prompt"],
)
@pytest.mark.parametrize("escape_kind", ["cross_tenant", "ancestor_symlink"])
def test_tenant_data_and_text_artifacts_reject_scope_escapes_before_callbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
    escape_kind: str,
) -> None:
    """Tenant data and text artifacts cannot read across tenant boundaries."""
    repository_root = tmp_path / "repository"
    tenants_root = repository_root / "tenants"
    owner_root = tenants_root / "owner"
    sibling_root = tenants_root / "sibling"
    owner_root.mkdir(parents=True)
    sibling_root.mkdir(parents=True)

    filename = "cases.jsonl" if artifact == "dataset" else "protected.md"
    sibling_target = sibling_root / filename
    if artifact == "dataset":
        sibling_target.write_text(
            json.dumps(
                {
                    "case_id": "foreign-case",
                    "task_type": "demo",
                    "context": {"name": "foreign"},
                    "expected": {},
                    "metadata": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        sibling_target.write_text("sibling-tenant-canary", encoding="utf-8")

    if escape_kind == "cross_tenant":
        escaped_path = sibling_target
    else:
        foreign_link = owner_root / "foreign"
        try:
            foreign_link.symlink_to(sibling_root, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"symlinks are unavailable: {exc}")
        escaped_path = foreign_link / filename

    rows = None
    if artifact == "case prompt":
        rows = [
            {
                "case_id": "case-1",
                "task_type": "demo",
                "context": {"name": "ok"},
                "expected": {},
                "metadata": {},
                "prompt_template_path": str(escaped_path),
            }
        ]
    config = _config(tmp_path, rows=rows)
    config.tenant_id = "owner"
    if artifact == "dataset":
        config.dataset_path = str(escaped_path)
    elif artifact == "prompt":
        config.chain.config = {
            "prompt_paths": {"answer": str(escaped_path)},
            "optimization_target": "prompt",
        }
    elif artifact == "skill":
        config.chain.config = {
            "skill_paths": [str(escaped_path)],
            "optimization_target": "prompt",
        }

    calls = {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}
    stable_runtime = {
        "source_members": [],
        "source_fingerprint": eval_runner.fingerprint_value([]),
        "git": {"status": "unavailable"},
        "python": {"implementation": "CPython", "version": "test"},
        "packages": {},
    }
    monkeypatch.setattr(eval_runner, "_repository_root", lambda: repository_root)
    monkeypatch.setattr(eval_runner, "_runtime_facts", lambda: stable_runtime)
    monkeypatch.setattr(
        eval_runner,
        "resolve_provider_settings",
        lambda *_args: calls.__setitem__("resolver", calls["resolver"] + 1) or {},
    )
    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda *_args: calls.__setitem__("scorer", calls["scorer"] + 1)
        or _Scorer(),
    )
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda *_args: calls.__setitem__("provider", calls["provider"] + 1)
        or object(),
    )
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: calls.__setitem__("chain", calls["chain"] + 1)
        or _Chain(),
    )
    real_read_bytes = Path.read_bytes
    escaped_lexical = eval_runner._lexical_absolute(escaped_path)

    def reject_foreign_read(path: Path) -> bytes:
        if eval_runner._lexical_absolute(path) == escaped_lexical:
            raise AssertionError("foreign tenant artifact was read")
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", reject_foreign_read)

    with pytest.raises(
        ValueError,
        match=rf"{artifact}.*(crosses|ancestor|resolves).*tenant|"
        rf"{artifact}.*tenant.*(crosses|ancestor|resolves)",
    ):
        eval_runner.run_evaluation(config)

    assert calls == {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}


def test_python_scope_ignores_unrelated_data_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only executable Python members are subject to package symlink rejection."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    chain_module = package / "chain.py"
    chain_module.write_text("def build_chain(provider, config): ...\n", encoding="utf-8")
    data_target = tmp_path / "dataset-target.jsonl"
    data_target.write_text('{"protected": true}\n', encoding="utf-8")
    data_link = package / "dataset.jsonl"
    try:
        data_link.symlink_to(data_target)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    config = _config(tmp_path)
    config.chain = ChainConfig(path=str(chain_module))
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    results = eval_runner.run_evaluation(config)

    assert results[0]["execution_status"] == "succeeded"
    run_config = json.loads(
        (Path(config.output_dir) / "run_config.json").read_text(encoding="utf-8")
    )
    assert str(data_link) not in json.dumps(run_config["chain"]["source_artifacts"])


@pytest.mark.parametrize("artifact", ["chain", "prompt", "skill", "scorer"])
def test_executable_artifact_symlinks_fail_before_callbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact: str,
) -> None:
    """Executable indirection cannot evade a byte-bound run identity."""
    config = _config(tmp_path)
    prompt = tmp_path / "prompt.md"
    skill = tmp_path / "skill.md"
    scorer = tmp_path / "scorer.py"
    prompt.write_text("prompt", encoding="utf-8")
    skill.write_text("skill", encoding="utf-8")
    scorer.write_text("# scorer\n", encoding="utf-8")
    config.chain.config = {
        "prompt_paths": {"answer": str(prompt)},
        "skill_paths": [str(skill)],
        "optimization_target": "prompt",
    }
    config.scoring_profile = {"scorer": {"module_path": str(scorer)}}

    target = {
        "chain": Path(config.chain.path),
        "prompt": prompt,
        "skill": skill,
        "scorer": scorer,
    }[artifact]
    real_target = target.with_name(f"{target.stem}-real{target.suffix}")
    target.replace(real_target)
    try:
        target.symlink_to(real_target)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    calls = {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}

    def resolver(*_args: Any) -> dict[str, object]:
        calls["resolver"] += 1
        return {}

    monkeypatch.setattr(eval_runner, "resolve_provider_settings", resolver)
    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda *_args: calls.__setitem__("scorer", calls["scorer"] + 1) or _Scorer(),
    )
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda *_args: calls.__setitem__("provider", calls["provider"] + 1) or object(),
    )
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: calls.__setitem__("chain", calls["chain"] + 1) or _Chain(),
    )

    with pytest.raises(ValueError, match=rf"{artifact}.*symlink|symlink.*{artifact}"):
        eval_runner.run_evaluation(config)

    assert calls == {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}


def test_declared_missing_scorer_cannot_appear_after_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A resolver callback cannot create an unbound scorer after preflight."""
    config = _config(tmp_path)
    scorer_path = Path(config.scoring_profile["scorer"]["module_path"])
    scorer_path.unlink()
    calls = {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}

    def create_scorer(*_args: Any) -> dict[str, object]:
        calls["resolver"] += 1
        scorer_path.write_text("# appeared after snapshot\n", encoding="utf-8")
        return {}

    monkeypatch.setattr(eval_runner, "resolve_provider_settings", create_scorer)
    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda *_args: calls.__setitem__("scorer", calls["scorer"] + 1) or _Scorer(),
    )
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda *_args: calls.__setitem__("provider", calls["provider"] + 1) or object(),
    )
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: calls.__setitem__("chain", calls["chain"] + 1) or _Chain(),
    )

    with pytest.raises(FileNotFoundError, match="scorer executable artifact not found"):
        eval_runner.run_evaluation(config)

    assert calls == {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}
    assert not scorer_path.exists()


def test_runtime_facts_cover_every_core_execution_layer() -> None:
    """The runtime source fingerprint covers every core layer invoked by evals."""
    facts = eval_runner._runtime_facts()
    paths = {row["path"] for row in facts["source_members"]}

    assert {
        "src/hephaestus/analysis/step_attribution.py",
        "src/hephaestus/artifact_io.py",
        "src/hephaestus/chains/agentic_nodes.py",
        "src/hephaestus/chains/loader.py",
        "src/hephaestus/chains/nodes.py",
        "src/hephaestus/chains/types.py",
        "src/hephaestus/datasets/jsonl_loader.py",
        "src/hephaestus/engine/prompt_renderer.py",
        "src/hephaestus/engine/skills.py",
        "src/hephaestus/evaluation_assets/provenance.py",
        "src/hephaestus/evaluation_assets/trust_tiers.py",
        "src/hephaestus/loader.py",
        "src/hephaestus/local_authority_io.py",
        "src/hephaestus/mcp/executor.py",
        "src/hephaestus/mcp/manager.py",
        "src/hephaestus/mcp/schema_converter.py",
        "src/hephaestus/mcp/types.py",
        "src/hephaestus/providers/base.py",
        "src/hephaestus/providers/openai.py",
        "src/hephaestus/runs/bundle.py",
        "src/hephaestus/runs/eval_runner.py",
        "src/hephaestus/runs/identity.py",
        "src/hephaestus/runs/progress.py",
        "src/hephaestus/scoring/runtime.py",
        "src/hephaestus/scoring/scorer.py",
        "src/hephaestus/types.py",
    } <= paths


def test_runtime_source_symlink_fails_before_callbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symlinked core source cannot become an omitted identity dimension."""
    repository_root = tmp_path / "repository"
    runtime_dir = repository_root / "runtime"
    runtime_dir.mkdir(parents=True)
    fixed_source = repository_root / "fixed.py"
    fixed_source.write_text("# fixed runtime source\n", encoding="utf-8")
    target = runtime_dir / "target.py"
    target.write_text("# target runtime source\n", encoding="utf-8")
    runtime_source = runtime_dir / "core.py"
    try:
        runtime_source.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    calls = {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}
    monkeypatch.setattr(eval_runner, "_repository_root", lambda: repository_root)
    monkeypatch.setattr(eval_runner, "_RUNTIME_SOURCE_GLOBS", ("runtime/*.py",))
    monkeypatch.setattr(eval_runner, "_RUNTIME_SOURCE_FILES", ("fixed.py",))
    monkeypatch.setattr(
        eval_runner,
        "resolve_provider_settings",
        lambda *_args: calls.__setitem__("resolver", calls["resolver"] + 1) or {},
    )
    monkeypatch.setattr(
        eval_runner,
        "load_tenant_scorer",
        lambda *_args: calls.__setitem__("scorer", calls["scorer"] + 1) or _Scorer(),
    )
    monkeypatch.setattr(
        eval_runner,
        "build_provider_client",
        lambda *_args: calls.__setitem__("provider", calls["provider"] + 1) or object(),
    )
    monkeypatch.setattr(
        eval_runner,
        "_ensure_chain",
        lambda *_args, **_kwargs: calls.__setitem__("chain", calls["chain"] + 1)
        or _Chain(),
    )

    with pytest.raises(ValueError, match="runtime source.*symlink"):
        eval_runner.run_evaluation(_config(tmp_path))

    assert calls == {"resolver": 0, "scorer": 0, "provider": 0, "chain": 0}


def test_full_runtime_facts_are_bound_into_chain_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Python, package, and Git drift changes identity even with stable source bytes."""
    config = _config(tmp_path)
    loaded = load_cases_with_identity(Path(config.dataset_path))
    resolved = eval_runner.resolve_provider_settings("baseten", {})
    provider_facts = eval_runner.safe_provider_facts("baseten", resolved)
    mcp_facts = safe_mcp_facts(None, None)
    source_fingerprint = "sha256:" + "a" * 64
    runtime_one = {
        "source_members": [],
        "source_fingerprint": source_fingerprint,
        "git": {"commit": "first"},
        "python": {"implementation": "CPython", "version": "3.10.0"},
        "packages": {"hephaestus": {"status": "available", "version": "1"}},
    }
    runtime_two = {
        **runtime_one,
        "git": {"commit": "second"},
        "python": {"implementation": "CPython", "version": "3.11.0"},
        "packages": {"hephaestus": {"status": "available", "version": "2"}},
    }

    monkeypatch.setattr(eval_runner, "_runtime_facts", lambda: runtime_one)
    first, first_config = eval_runner._build_identity_and_config(
        config,
        loaded,
        run_id="first",
        resolved_provider_settings=resolved,
        provider_facts=provider_facts,
        mcp_facts=mcp_facts,
    )
    monkeypatch.setattr(eval_runner, "_runtime_facts", lambda: runtime_two)
    second, second_config = eval_runner._build_identity_and_config(
        config,
        loaded,
        run_id="second",
        resolved_provider_settings=resolved,
        provider_facts=provider_facts,
        mcp_facts=mcp_facts,
    )

    assert first_config["runtime"] == runtime_one
    assert second_config["runtime"] == runtime_two
    assert (
        first.control_dimensions["chain_structure"]["fingerprint"]
        != second.control_dimensions["chain_structure"]["fingerprint"]
    )


def test_mcp_capabilities_are_snapshotted_before_chain_callbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tenant chain mutation cannot rewrite the capabilities bound to the run."""
    config = _config(tmp_path)
    config.mcp = MCPConfig(
        servers=[MCPServerConfig(name="tools", command="tool-server")]
    )
    original_schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
    }
    expected_facts = safe_mcp_facts(
        config.mcp,
        {
            "original": MCPTool(
                name="original",
                description="Original",
                input_schema=copy.deepcopy(original_schema),
                server_name="tools",
            )
        },
    )

    class _Manager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.tools = {
                "original": MCPTool(
                    name="original",
                    description="Original",
                    input_schema=copy.deepcopy(original_schema),
                    server_name="tools",
                )
            }

        def start_servers(self) -> None:
            pass

        def stop_servers(self) -> None:
            pass

    def mutate_capabilities(
        _config: EvalConfig,
        _provider: Any,
        *,
        mcp_manager: Any,
    ) -> _Chain:
        mcp_manager.tools["original"].input_schema["properties"]["value"][
            "type"
        ] = "number"
        mcp_manager.tools.clear()
        mcp_manager.tools["post-start"] = MCPTool(
            name="post-start",
            description="Post start",
            input_schema={"type": "array"},
            server_name="tools",
        )
        return _Chain()

    monkeypatch.setattr(eval_runner, "MCPServerManager", _Manager)
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", mutate_capabilities)

    eval_runner.run_evaluation(config)

    run_config = json.loads(
        (Path(config.output_dir) / "run_config.json").read_text(encoding="utf-8")
    )
    assert run_config["mcp"]["discovered_capabilities"] == expected_facts[
        "discovered_capabilities"
    ]
    identity = json.loads(
        (Path(config.output_dir) / "run_identity.json").read_text(encoding="utf-8")
    )
    resolved = identity["control_dimensions"]["mcp_capabilities"]["resolved"]
    assert resolved["tool_names"] == ["original"]


def test_snapshot_cleanup_failure_precedes_authoritative_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No manifest is installed until fallible execution-snapshot cleanup succeeds."""
    config = _config(tmp_path)
    sentinel = OSError("snapshot-cleanup-sentinel")
    original_cleanup = eval_runner.tempfile.TemporaryDirectory.cleanup

    def cleanup_then_fail(directory: Any) -> None:
        original_cleanup(directory)
        raise sentinel

    monkeypatch.setattr(
        eval_runner.tempfile.TemporaryDirectory,
        "cleanup",
        cleanup_then_fail,
    )
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    with pytest.raises(OSError) as caught:
        eval_runner.run_evaluation(config)

    assert caught.value is sentinel
    output_dir = Path(config.output_dir)
    assert not (output_dir / "run_manifest.json").exists()
    progress = read_progress(output_dir)
    assert progress is not None
    assert progress.status == "failed"


@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        ("baseten", "any-model", False),
        ("sagemaker", "any-model", False),
        ("openai", "o3-mini", False),
        ("openai", "gpt-5-mini", False),
        ("openai", "gpt-4o", True),
    ],
)
def test_run_identity_reports_resolved_provider_tool_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    model: str,
    expected: bool,
) -> None:
    """Discovered MCP tools do not imply that the resolved model can call them."""
    config = _config(tmp_path)
    config.provider = provider
    config.provider_settings = {"model": model}
    config.mcp = MCPConfig(
        servers=[MCPServerConfig(name="tools", command="tool-server")]
    )

    class _Manager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.tools = {
                "lookup": MCPTool(
                    name="lookup",
                    description="Lookup",
                    input_schema={"type": "object"},
                    server_name="tools",
                )
            }

        def start_servers(self) -> None:
            pass

        def stop_servers(self) -> None:
            pass

    monkeypatch.setattr(eval_runner, "MCPServerManager", _Manager)
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    eval_runner.run_evaluation(config)

    identity = json.loads(
        (Path(config.output_dir) / "run_identity.json").read_text(encoding="utf-8")
    )
    resolved = identity["control_dimensions"]["mcp_capabilities"]["resolved"]
    assert resolved["tool_names"] == ["lookup"]
    assert resolved["supports_tool_calling"] is expected


def test_sagemaker_runs_cannot_claim_controlled_model_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable SageMaker model remains unavailable end to end."""
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    baseline = _config(tmp_path)
    baseline.provider = "sagemaker"
    baseline.provider_settings = {"api_url": "https://example.invalid/invoke"}
    baseline.output_dir = str(tmp_path / "baseline")
    candidate = copy.deepcopy(baseline)
    candidate.output_dir = str(tmp_path / "candidate")

    eval_runner.run_evaluation(baseline)
    eval_runner.run_evaluation(candidate)

    identity = json.loads(
        (Path(baseline.output_dir) / "run_identity.json").read_text(
            encoding="utf-8"
        )
    )
    assert identity["control_dimensions"]["model"] == {
        "status": "unavailable",
        "resolved": {"status": "unavailable"},
    }
    with pytest.raises(RunComparisonIncompatibilityError) as caught:
        compare_runs(Path(baseline.output_dir), Path(candidate.output_dir))

    assert any(
        issue.code == "control_dimensions.model.unavailable"
        for issue in caught.value.issues
    )
    exploratory = compare_runs(
        Path(baseline.output_dir),
        Path(candidate.output_dir),
        exploratory=True,
    )
    assert exploratory["compatibility"]["controlled"] is False
    assert exploratory["compatibility"]["exploratory"] is True


@pytest.mark.parametrize(
    ("dimension", "baseline_settings", "candidate_settings"),
    [
        (
            "model",
            {"model": "gpt-4o", "temperature": 0.0},
            {"model": "gpt-4.1", "temperature": 0.0},
        ),
        (
            "sampling",
            {"model": "gpt-4o", "temperature": 0.0},
            {"model": "gpt-4o", "temperature": 0.7},
        ),
    ],
)
def test_provider_model_and_sampling_dimensions_are_orthogonal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dimension: str,
    baseline_settings: dict[str, object],
    candidate_settings: dict[str, object],
) -> None:
    """Declaring one provider-related variant does not vary provider identity."""
    monkeypatch.setattr(eval_runner, "load_tenant_scorer", lambda _profile: _Scorer())
    monkeypatch.setattr(eval_runner, "build_provider_client", lambda *_args: object())
    monkeypatch.setattr(eval_runner, "_ensure_chain", lambda *_args, **_kwargs: _Chain())

    baseline = _config(tmp_path)
    baseline.provider = "openai"
    baseline.provider_settings = baseline_settings
    baseline.comparison_variant_dimensions = [dimension]
    baseline.output_dir = str(tmp_path / f"baseline-{dimension}")
    candidate = copy.deepcopy(baseline)
    candidate.provider_settings = candidate_settings
    candidate.output_dir = str(tmp_path / f"candidate-{dimension}")

    eval_runner.run_evaluation(baseline)
    eval_runner.run_evaluation(candidate)

    comparison = compare_runs(
        Path(baseline.output_dir),
        Path(candidate.output_dir),
    )
    assert comparison["compatibility"]["controlled"] is True
    assert [
        row["dimension"]
        for row in comparison["compatibility"]["variant_differences"]
    ] == [dimension]
