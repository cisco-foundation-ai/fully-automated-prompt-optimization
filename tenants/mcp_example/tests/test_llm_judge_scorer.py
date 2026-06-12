# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the LLM-as-judge scorer and the composite scorer.

The judge provider is mocked so no live API calls are made.
"""

from __future__ import annotations

import pytest

from src.hephaestus.types import EvalCase
from tenants.mcp_example.code.scorers import llm_judge_scorer
from tenants.mcp_example.code.scorers.composite_scorer import CompositeScorer
from tenants.mcp_example.code.scorers.llm_judge_scorer import LLMJudgeScorer


class _FakeProvider:
    """Returns a canned judge response (or raises) for generate()."""

    def __init__(self, response: str | None = None, raises: Exception | None = None):
        self._response = response
        self._raises = raises
        self.calls: list = []

    def generate(self, messages):
        self.calls.append(messages)
        if self._raises is not None:
            raise self._raises
        return self._response


def _make_case(expected: dict, case_id: str = "j-001") -> EvalCase:
    return EvalCase(
        case_id=case_id,
        task_type="tool_use",
        context={"task": "What is 42 plus 17?"},
        expected=expected,
        metadata={},
    )


# --- LLMJudgeScorer ---


def test_judge_parses_clean_json(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider('{"score": 100, "reason": "correct"}')
    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", lambda *_: fake)

    scorer = LLMJudgeScorer()
    case = _make_case({"answer_contains": "59"})
    result = scorer.score_pipeline_case(case, {}, {"judge": {}}, output_text="answer: 59")

    assert result["composite_score"] == 100.0
    assert result["score_breakdown"]["answer_correct"] == 100.0
    assert len(fake.calls) == 1


def test_judge_parses_json_in_code_fence(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider('```json\n{"score": 30, "reason": "wrong number"}\n```')
    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", lambda *_: fake)

    scorer = LLMJudgeScorer()
    result = scorer.score_pipeline_case(
        _make_case({"answer_contains": "59"}), {}, {"judge": {}}, output_text="answer: 12"
    )
    assert result["composite_score"] == 30.0


def test_judge_clamps_out_of_range_score(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider('{"score": 250, "reason": "x"}')
    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", lambda *_: fake)

    scorer = LLMJudgeScorer()
    result = scorer.score_pipeline_case(
        _make_case({"answer_contains": "59"}), {}, {"judge": {}}, output_text="x"
    )
    assert result["composite_score"] == 100.0


def test_judge_failure_degrades_to_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider(raises=RuntimeError("provider down"))
    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", lambda *_: fake)

    scorer = LLMJudgeScorer()
    result = scorer.score_pipeline_case(
        _make_case({"answer_contains": "59"}), {},
        {"judge": {"fallback_score": 42.0}}, output_text="x",
    )
    assert result["composite_score"] == 42.0


def test_judge_unparseable_response_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider("I cannot produce JSON today.")
    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", lambda *_: fake)

    scorer = LLMJudgeScorer()
    result = scorer.score_pipeline_case(
        _make_case({"answer_contains": "59"}), {},
        {"judge": {"fallback_score": 50.0}}, output_text="x",
    )
    assert result["composite_score"] == 50.0


def test_judge_provider_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    builds = {"count": 0}

    def _build(*_):
        builds["count"] += 1
        return _FakeProvider('{"score": 100, "reason": "ok"}')

    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", _build)
    scorer = LLMJudgeScorer()
    case = _make_case({"answer_contains": "59"})
    scorer.score_pipeline_case(case, {}, {"judge": {}}, output_text="answer: 59")
    scorer.score_pipeline_case(case, {}, {"judge": {}}, output_text="answer: 59")
    assert builds["count"] == 1  # same config -> one build


# --- CompositeScorer ---


def test_composite_combines_trajectory_and_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider('{"score": 100, "reason": "correct"}')
    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", lambda *_: fake)

    scorer = CompositeScorer()
    case = _make_case({"answer_contains": "59", "tools_used": ["add"]})
    history = [{
        "tool": "add", "arguments": {"a": 42, "b": 17}, "result": "59",
        "result_length": 2, "error": None, "iteration": 1, "call_index": 0, "node": "answer",
    }]
    result = scorer.score_pipeline_case(
        case, {}, {"judge": {}}, output_text="answer: 59", tool_call_history=history
    )

    bd = result["score_breakdown"]
    assert bd["answer_correct"] == 100.0      # judge
    assert bd["trajectory"] == 100.0          # right tool used
    assert "answer_present" not in bd         # removed component
    # child sub-metrics flattened with prefixes
    assert "traj_tool_selection" in bd
    assert "judge_answer_correct" in bd
    assert result["composite_score"] == pytest.approx(100.0)


def test_composite_respects_custom_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeProvider('{"score": 0, "reason": "wrong"}')
    monkeypatch.setattr(llm_judge_scorer, "build_provider_client", lambda *_: fake)

    scorer = CompositeScorer()
    case = _make_case({"answer_contains": "59", "tools_used": ["add"]})
    history = [{
        "tool": "add", "arguments": {"a": 42, "b": 17}, "result": "59",
        "result_length": 2, "error": None, "iteration": 1, "call_index": 0, "node": "answer",
    }]
    # All weight on trajectory -> judge's 0 shouldn't matter.
    profile = {
        "judge": {},
        "composite_weights": {"answer_correct": 0.0, "trajectory": 1.0},
    }
    result = scorer.score_pipeline_case(
        case, {}, profile, output_text="answer: 59", tool_call_history=history
    )
    assert result["composite_score"] == pytest.approx(result["score_breakdown"]["trajectory"])
