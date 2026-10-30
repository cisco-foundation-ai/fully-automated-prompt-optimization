# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""End-to-end chain integration tests.

Covers a 3-node chain (LLM -> Python function -> LLM), context threading,
score_pipeline_case dispatch, and output file verification.
"""

from __future__ import annotations

import gc
import json
import sys
from pathlib import Path

import pytest
from helpers import TrackingProvider, write_dataset, write_scorer

import src.hephaestus.runs.eval_runner as eval_runner
from src.hephaestus.runs.eval_runner import load_eval_config, run_evaluation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_pipeline_scorer(tmp_path: Path) -> Path:
    """Scorer that overrides score_pipeline_case to verify it was called."""
    scorer = tmp_path / "pipeline_scorer.py"
    scorer.write_text(
        """\
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        return None

    def score_case(self, case, output_text, scoring_profile):
        return {
            'composite_score': 50.0,
            'score_breakdown': {'quality': 50.0},
        }

    def score_pipeline_case(self, case, step_outputs, scoring_profile, output_text=''):
        # Return a distinct score so the test can distinguish pipeline vs single
        num_steps = len(step_outputs)
        return {
            'composite_score': 90.0,
            'score_breakdown': {'quality': 90.0, 'num_steps': float(num_steps)},
        }
""",
        encoding="utf-8",
    )
    return scorer


def _write_three_node_chain(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a 3-node chain: LLM (analyze) -> Python (transform) -> LLM (summarize).

    Returns (chain_file, analyze_template, summarize_template).
    """
    analyze_template = tmp_path / "analyze.md"
    analyze_template.write_text(
        "User: analyze ${inputs.Name}", encoding="utf-8"
    )

    summarize_template = tmp_path / "summarize.md"
    summarize_template.write_text(
        "User: summarize ${steps.transform.output}", encoding="utf-8"
    )

    chain_file = tmp_path / "three_node_chain.py"
    chain_file.write_text(
        """\
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.nodes import make_llm_node
from pathlib import Path
from typing import Any, Dict

def _transform_node(state: Dict[str, Any]) -> Dict[str, Any]:
    step_outputs = dict(state.get("step_outputs", {}))
    analyze_output = step_outputs.get("analyze", "")
    transformed = f"TRANSFORMED: {analyze_output.upper()}"
    step_outputs["transform"] = transformed
    return {"output_text": transformed, "step_outputs": step_outputs}

def build_chain(provider, config):
    analyze_path = Path(config["prompt_paths"]["analyze"])
    summarize_path = Path(config["prompt_paths"]["summarize"])
    graph = StateGraph(dict)
    graph.add_node(
        "analyze",
        make_llm_node(provider, analyze_path, output_key="analyze"),
    )
    graph.add_node("transform", _transform_node)
    graph.add_node(
        "summarize",
        make_llm_node(provider, summarize_path, output_key="summarize"),
    )
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "transform")
    graph.add_edge("transform", "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()
""",
        encoding="utf-8",
    )
    return chain_file, analyze_template, summarize_template


def _write_three_node_config(
    tmp_path: Path,
    chain_file: Path,
    analyze_template: Path,
    summarize_template: Path,
    scorer_path: Path,
    cases: int = 1,
) -> Path:
    dataset = write_dataset(tmp_path, cases=cases)
    config_path = tmp_path / "config.json"
    config = {
        "tenant_id": "integration_test",
        "provider": "baseten",
        "provider_settings": {},
        "dataset": {"path": str(dataset)},
        "chain": {
            "path": str(chain_file),
            "fn": "build_chain",
            "config": {
                "prompt_paths": {
                    "analyze": str(analyze_template),
                    "summarize": str(summarize_template),
                },
            },
        },
        "scoring_profile": {"scorer": {"module_path": str(scorer_path)}},
        "output_dir": str(tmp_path / "out"),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestThreeNodeChainIntegration:
    """End-to-end tests for a 3-node chain (LLM -> Python -> LLM)."""

    def test_context_threading_across_nodes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Node 3's prompt contains node 1 and node 2 outputs via context threading."""
        chain_file, analyze_t, summarize_t = _write_three_node_chain(tmp_path)
        scorer = write_scorer(tmp_path, composite_score=80.0)
        config_path = _write_three_node_config(
            tmp_path, chain_file, analyze_t, summarize_t, scorer, cases=2
        )

        # Provider returns distinct responses per call (2 cases x 2 LLM nodes):
        #   call 0 (analyze, case 1): "analysis of user1"
        #   call 1 (summarize, case 1): "summary result 1"
        #   call 2 (analyze, case 2): "analysis of user2"
        #   call 3 (summarize, case 2): "summary result 2"
        tracking = TrackingProvider(
            ["analysis of user1", "summary result 1", "analysis of user2", "summary result 2"]
        )
        monkeypatch.setattr(
            eval_runner, "build_provider_client", lambda _p, _s: tracking
        )

        loaded = load_eval_config(config_path)
        results = run_evaluation(loaded)

        assert len(results) == 2

        # 2 cases x 2 LLM calls each = 4 total provider calls
        assert len(tracking.calls) == 4

        # Verify context threading: the summarize node (call index 1) should
        # see the transform output which is based on the analyze output.
        # The transform node produces "TRANSFORMED: ANALYSIS OF USER1"
        summarize_call_1 = tracking.calls[1]
        summarize_text_1 = " ".join(msg["content"] for msg in summarize_call_1)
        assert "TRANSFORMED: ANALYSIS OF USER1" in summarize_text_1

        # Same for case 2
        summarize_call_2 = tracking.calls[3]
        summarize_text_2 = " ".join(msg["content"] for msg in summarize_call_2)
        assert "TRANSFORMED: ANALYSIS OF USER2" in summarize_text_2

    def test_score_pipeline_case_called_for_multi_step(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """score_pipeline_case is called with correct step_outputs for multi-step chain."""
        chain_file, analyze_t, summarize_t = _write_three_node_chain(tmp_path)
        scorer = _write_pipeline_scorer(tmp_path)
        config_path = _write_three_node_config(
            tmp_path, chain_file, analyze_t, summarize_t, scorer
        )

        tracking = TrackingProvider(["analysis output", "summary output"])
        monkeypatch.setattr(
            eval_runner, "build_provider_client", lambda _p, _s: tracking
        )

        loaded = load_eval_config(config_path)
        results = run_evaluation(loaded)

        # The pipeline scorer returns 90.0 composite and num_steps as a breakdown key
        for result in results:
            assert result["composite_score"] == 90.0
            assert result["score_breakdown"]["quality"] == 90.0
            # 3 steps: analyze, transform, summarize
            assert result["score_breakdown"]["num_steps"] == 3.0

    def test_step_outputs_in_results(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Multi-step chain includes step_outputs dict in results."""
        chain_file, analyze_t, summarize_t = _write_three_node_chain(tmp_path)
        scorer = write_scorer(tmp_path, composite_score=80.0)
        config_path = _write_three_node_config(
            tmp_path, chain_file, analyze_t, summarize_t, scorer
        )

        tracking = TrackingProvider(["analysis output", "summary output"])
        monkeypatch.setattr(
            eval_runner, "build_provider_client", lambda _p, _s: tracking
        )

        loaded = load_eval_config(config_path)
        results = run_evaluation(loaded)

        for result in results:
            assert "step_outputs" in result
            step_outputs = result["step_outputs"]
            assert "analyze" in step_outputs
            assert "transform" in step_outputs
            assert "summarize" in step_outputs
            assert step_outputs["analyze"] == "analysis output"
            assert step_outputs["transform"] == "TRANSFORMED: ANALYSIS OUTPUT"
            assert step_outputs["summarize"] == "summary output"

    def test_output_files_written(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verifies results.jsonl, run_config.json, and summary.md are written."""
        chain_file, analyze_t, summarize_t = _write_three_node_chain(tmp_path)
        scorer = write_scorer(tmp_path, composite_score=80.0)
        config_path = _write_three_node_config(
            tmp_path, chain_file, analyze_t, summarize_t, scorer, cases=2
        )

        tracking = TrackingProvider(
            ["analysis output", "summary output", "analysis output 2", "summary output 2"]
        )
        monkeypatch.setattr(
            eval_runner, "build_provider_client", lambda _p, _s: tracking
        )

        loaded = load_eval_config(config_path)
        run_evaluation(loaded)

        out_dir = tmp_path / "out"

        # results.jsonl
        results_path = out_dir / "results.jsonl"
        assert results_path.exists()
        result_lines = results_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(result_lines) == 2
        parsed = json.loads(result_lines[0])
        assert "step_outputs" in parsed
        assert parsed["step_outputs"]["analyze"] == "analysis output"

        # run_config.json with chain key
        run_config_path = out_dir / "run_config.json"
        assert run_config_path.exists()
        run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
        assert "chain" in run_config
        assert run_config["chain"]["path"] == str(chain_file)
        assert run_config["chain"]["fn"] == "build_chain"

        # summary.md
        summary_path = out_dir / "summary.md"
        assert summary_path.exists()
        summary_text = summary_path.read_text(encoding="utf-8")
        assert "Evaluation Summary" in summary_text
        assert "Total cases: 2" in summary_text


class TestEvalModuleRelease:
    """Evals release the tenant modules they load."""

    def test_repeated_evals_free_chain_module_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Module-level data in a chain does not survive its eval, so repeated evals do not accumulate it."""
        chain_file = tmp_path / "probe_chain.py"
        chain_file.write_text(
            """\
from langgraph.graph import StateGraph, END


class _LeakProbePayload:
    pass


PAYLOAD = _LeakProbePayload()


def _answer(state):
    return {"output_text": "ok", "step_outputs": {"answer": "ok"}}


def build_chain(provider, config):
    graph = StateGraph(dict)
    graph.add_node("answer", _answer)
    graph.set_entry_point("answer")
    graph.add_edge("answer", END)
    return graph.compile()
""",
            encoding="utf-8",
        )
        scorer = write_scorer(tmp_path)
        dataset = write_dataset(tmp_path)
        monkeypatch.setattr(eval_runner, "build_provider_client", lambda _p, _s: TrackingProvider([]))
        modules_before = set(sys.modules)

        for run in range(2):
            config_path = tmp_path / f"config-{run}.json"
            config = {
                "tenant_id": "integration_test",
                "provider": "baseten",
                "provider_settings": {},
                "dataset": {"path": str(dataset)},
                "chain": {"path": str(chain_file), "fn": "build_chain", "config": {}},
                "scoring_profile": {"scorer": {"module_path": str(scorer)}},
                "output_dir": str(tmp_path / f"out-{run}"),
            }
            config_path.write_text(json.dumps(config), encoding="utf-8")
            assert len(run_evaluation(load_eval_config(config_path))) == 1
        gc.collect()

        leftover = [name for name in set(sys.modules) - modules_before if "hephaestus_tenant" in name]
        assert leftover == []
        assert not [obj for obj in gc.get_objects() if type(obj).__name__ == "_LeakProbePayload"]
