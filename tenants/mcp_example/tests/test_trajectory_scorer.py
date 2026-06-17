# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the deterministic TrajectoryScorer."""

from __future__ import annotations

import pytest

from src.hephaestus.types import EvalCase
from tenants.mcp_example.code.scorers.trajectory_scorer import TrajectoryScorer


def _make_case(expected: dict, case_id: str = "t-001") -> EvalCase:
    return EvalCase(
        case_id=case_id,
        task_type="tool_use",
        context={"task": "Add 100 and 234, then echo the result"},
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


# --- tool selection (legacy tools_used) ---


def test_all_expected_tools_used(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": ["add", "echo"]})
    history = [_call("add", {"a": 100, "b": 234}, 0), _call("echo", {"message": "334"}, 1)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="answer: 334", tool_call_history=history)
    assert result["score_breakdown"]["tool_selection"] == 100.0


def test_missing_tool_partial_credit(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": ["add", "echo"]})
    history = [_call("add", {"a": 100, "b": 234}, 0)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["tool_selection"] == pytest.approx(35.0)  # 1/2 * 70


def test_reasoning_case_uses_no_tools(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": []})
    result = scorer.score_pipeline_case(case, {}, {}, output_text="answer: Paris", tool_call_history=[])
    assert result["score_breakdown"]["tool_selection"] == 100.0


def test_reasoning_case_penalized_for_tool_use(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": []})
    history = [_call("add", {"a": 1, "b": 2}, 0)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["tool_selection"] == 30.0


# --- ordering ---


def test_correct_order_full_marks(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [
            {"tool": "add", "arguments": {"a": 100, "b": 234}},
            {"tool": "echo", "arguments": {"message": "334"}},
        ]
    })
    history = [_call("add", {"a": 100, "b": 234}, 0), _call("echo", {"message": "334"}, 1)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="answer: 334", tool_call_history=history)
    assert result["score_breakdown"]["call_ordering"] == 100.0


def test_wrong_order_penalized(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [
            {"tool": "add", "arguments": {}},
            {"tool": "echo", "arguments": {}},
        ]
    })
    # echo called before add -> only first expected element matched as subsequence
    history = [_call("echo", {"message": "x"}, 0), _call("add", {"a": 1, "b": 2}, 1)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["call_ordering"] == 50.0


# --- argument correctness ---


def test_argument_match(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [{"tool": "add", "arguments": {"a": 100, "b": 234}}]
    })
    history = [_call("add", {"a": 100, "b": 234}, 0)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["argument_correctness"] == 100.0


def test_argument_mismatch(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [{"tool": "add", "arguments": {"a": 100, "b": 234}}]
    })
    history = [_call("add", {"a": 1, "b": 2}, 0)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["argument_correctness"] == 0.0


def test_argument_match_is_type_tolerant(scorer: TrajectoryScorer) -> None:
    case = _make_case({
        "expected_trajectory": [{"tool": "add", "arguments": {"a": 100}}]
    })
    history = [_call("add", {"a": "100", "b": 234}, 0)]  # string vs int, extra arg
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["argument_correctness"] == 100.0


# --- redundancy ---


def test_failed_call_penalized(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": ["add"]})
    history = [_call("add", {"a": 1, "b": 2}, 0, error="boom"), _call("add", {"a": 1, "b": 2}, 1)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["non_redundancy"] == 80.0  # one failure -20


def test_duplicate_calls_penalized(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": ["echo"]})
    history = [_call("echo", {"message": "hi"}, 0), _call("echo", {"message": "hi"}, 1)]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=history)
    assert result["score_breakdown"]["non_redundancy"] == 85.0  # one duplicate -15


# --- backwards compat: no enriched fields (no call_index, no result) ---


def test_scores_legacy_trace_without_call_index(scorer: TrajectoryScorer) -> None:
    case = _make_case({"tools_used": ["add"]})
    legacy = [{"tool": "add", "arguments": {"a": 1, "b": 2}, "result_length": 1, "error": None}]
    result = scorer.score_pipeline_case(case, {}, {}, output_text="x", tool_call_history=legacy)
    assert result["score_breakdown"]["tool_selection"] == 100.0
    assert 0.0 <= result["composite_score"] <= 100.0
