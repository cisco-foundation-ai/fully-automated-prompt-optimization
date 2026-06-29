# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the deterministic TrajectoryScorer on Splunk MCP trajectories."""

from __future__ import annotations

import pytest

from src.hephaestus.types import EvalCase
from tenants.skill_example.code.scorers.trajectory_scorer import TrajectoryScorer


def _make_case(expected: dict, case_id: str = "t-001") -> EvalCase:
    return EvalCase(
        case_id=case_id,
        task_type="tool_use",
        context={"task": "What is most of my data stored in Splunk?"},
        expected=expected,
        metadata={},
    )


def _call(tool: str, arguments: dict, call_index: int, error: str | None = None) -> dict:
    return {
        "tool": tool,
        "arguments": arguments,
        "result": "",
        "result_length": 0,
        "error": error,
        "iteration": 1,
        "call_index": call_index,
        "node": "answer",
    }


@pytest.fixture()
def scorer() -> TrajectoryScorer:
    return TrajectoryScorer()


def test_index_inventory_full_marks(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [
            {"tool": "splunk_get_indexes"},
            {"tool": "splunk_get_index_info"},
        ]
    })
    history = [
        _call("splunk_get_indexes", {}, 0),
        _call("splunk_get_index_info", {"index_name": "main"}, 1),
    ]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="answer: ...", tool_call_history=history)
    assert result["score_breakdown"]["tool_selection"] == 100.0
    assert result["score_breakdown"]["call_ordering"] == 100.0


def test_search_pattern_tool_selection(scorer: TrajectoryScorer) -> None:
    # Search cases query directly via splunk_run_query (the saia_* AI Assistant
    # tools are unavailable on the target deployment).
    case = _make_case({"expected_trajectory": [{"tool": "splunk_run_query"}]})
    history = [_call("splunk_run_query", {"query": "index=_internal ...", "earliest_time": "-5h"}, 0)]
    result = scorer.score_pipeline_case(
        case, {}, {}, output_text="## Indexing Failures", tool_call_history=history
    )
    # No expected arguments -> argument scoring not applicable -> full marks.
    assert result["score_breakdown"]["argument_correctness"] == 100.0
    assert result["score_breakdown"]["tool_selection"] == 100.0


def test_named_index_argument_mismatch(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [{"tool": "splunk_get_index_info", "arguments": {"index_name": "main"}}]
    })
    history = [_call("splunk_get_index_info", {"index_name": "security"}, 0)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["argument_correctness"] == 0.0


def test_wrong_order_penalized(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [
            {"tool": "splunk_get_indexes"},
            {"tool": "splunk_get_index_info"},
        ]
    })
    # index_info before get_indexes -> only first expected element matched.
    history = [_call("splunk_get_index_info", {"index_name": "main"}, 0), _call("splunk_get_indexes", {}, 1)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["call_ordering"] == 50.0


def test_missing_tool_partial_credit(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": ["splunk_get_user_list", "splunk_get_user_info"]})
    history = [_call("splunk_get_user_list", {}, 0)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["tool_selection"] == pytest.approx(35.0)  # 1/2 * 70
