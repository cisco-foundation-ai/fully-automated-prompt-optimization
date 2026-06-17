# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Trajectory scorer for mcp_example tenant.

A deterministic, LangSmith-style "trajectory" evaluator: instead of only
checking *which* tools were used (an order-insensitive set comparison), this
scorer inspects the ordered sequence of tool calls and their arguments to
verify the agent took a sensible path.

Expected-trajectory schema (all optional, read from ``case.expected``):

    "tools_used": ["add", "echo"]          # set of required tools (legacy)
    "expected_trajectory": [               # ordered, argument-aware (preferred)
        {"tool": "add",  "arguments": {"a": 100, "b": 234}},
        {"tool": "echo", "arguments": {"message": "334"}}
    ]

When ``expected_trajectory`` is present it drives ordering + argument scoring.
When only ``tools_used`` is present the scorer falls back to order-insensitive
set matching so existing datasets keep working.
"""

from typing import Any, Dict, List, Optional

from src.hephaestus.scoring.scorer import Scorer as BaseScorer


class TrajectoryScorer(BaseScorer):
    """Score the ordered tool-call trajectory of an agentic run.

    Metrics (each 0-100):
    - tool_selection: did the agent call the expected tools (set overlap)?
    - call_ordering: were ordered calls made in the expected order?
    - argument_correctness: did call arguments match expectations?
    - non_redundancy: penalizes duplicate (tool, arguments) calls and failures.
    """

    def validate_case(self, case, scoring_profile):
        assert "task" in case.context, f"Case {case.case_id}: missing 'task'"
        assert case.expected is not None, f"Case {case.case_id}: missing expected dict"

    def score_case(self, case, output_text, scoring_profile):
        return self.score_pipeline_case(
            case, {}, scoring_profile, output_text=output_text, tool_call_history=None
        )

    def score_pipeline_case(
        self,
        case,
        step_outputs: Dict[str, str],
        scoring_profile: Dict[str, Any],
        output_text: Optional[str] = None,
        tool_call_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        expected = case.expected or {}
        history = tool_call_history or []

        # Successful calls only, in execution order. Prefer the explicit
        # call_index (added by the enriched trace) and fall back to list order
        # so older traces without call_index still score.
        successful = [tc for tc in history if not tc.get("error")]
        successful.sort(key=lambda tc: tc.get("call_index", 0))

        expected_trajectory = expected.get("expected_trajectory")
        expected_tools = expected.get("tools_used", [])

        tool_selection = self._score_tool_selection(successful, expected_tools, expected_trajectory)
        call_ordering = self._score_ordering(successful, expected_trajectory)
        argument_correctness = self._score_arguments(successful, expected_trajectory)
        non_redundancy = self._score_redundancy(history, expected_trajectory, expected_tools)

        # Weighted composite. Selection and arguments matter most; ordering and
        # redundancy are secondary signals.
        composite = (
            0.35 * tool_selection
            + 0.20 * call_ordering
            + 0.30 * argument_correctness
            + 0.15 * non_redundancy
        )

        return {
            "composite_score": composite,
            "score_breakdown": {
                "tool_selection": tool_selection,
                "call_ordering": call_ordering,
                "argument_correctness": argument_correctness,
                "non_redundancy": non_redundancy,
            },
        }

    # --- sub-scorers ----------------------------------------------------

    @staticmethod
    def _expected_tool_names(expected_trajectory, expected_tools) -> List[str]:
        if expected_trajectory:
            return [step["tool"] for step in expected_trajectory]
        return list(expected_tools)

    def _score_tool_selection(self, successful, expected_tools, expected_trajectory) -> float:
        expected_names = set(self._expected_tool_names(expected_trajectory, expected_tools))
        actual_names = {tc.get("tool") for tc in successful}

        if not expected_names:
            # Reasoning case: should not call tools.
            return 100.0 if not actual_names else 30.0
        if expected_names.issubset(actual_names):
            return 100.0
        overlap = len(expected_names & actual_names)
        if overlap == 0:
            return 0.0
        return (overlap / len(expected_names)) * 70.0

    def _score_ordering(self, successful, expected_trajectory) -> float:
        # Ordering is only meaningful with an explicit expected_trajectory of
        # length >= 2. Otherwise it's not applicable -> full marks.
        if not expected_trajectory or len(expected_trajectory) < 2:
            return 100.0

        expected_seq = [step["tool"] for step in expected_trajectory]
        actual_seq = [tc.get("tool") for tc in successful]

        # Is expected_seq a subsequence of actual_seq (order preserved)?
        i = 0
        for tool in actual_seq:
            if i < len(expected_seq) and tool == expected_seq[i]:
                i += 1
        if i == len(expected_seq):
            return 100.0
        return (i / len(expected_seq)) * 100.0

    def _score_arguments(self, successful, expected_trajectory) -> float:
        # No argument expectations -> not applicable.
        if not expected_trajectory:
            return 100.0

        steps_with_args = [s for s in expected_trajectory if s.get("arguments") is not None]
        if not steps_with_args:
            return 100.0

        matched = 0
        for step in steps_with_args:
            if self._find_matching_call(successful, step["tool"], step["arguments"]):
                matched += 1
        return (matched / len(steps_with_args)) * 100.0

    @staticmethod
    def _find_matching_call(successful, tool_name, expected_args) -> bool:
        """True if some successful call to tool_name has matching arguments.

        Matching is subset-based and type-tolerant: every expected key must be
        present with an equal value (compared as strings to tolerate 59 vs
        "59"). Extra actual arguments are ignored.
        """
        for tc in successful:
            if tc.get("tool") != tool_name:
                continue
            actual_args = tc.get("arguments") or {}
            if all(
                key in actual_args and str(actual_args[key]) == str(val)
                for key, val in expected_args.items()
            ):
                return True
        return False

    def _score_redundancy(self, history, expected_trajectory, expected_tools) -> float:
        score = 100.0

        # Penalize failed calls.
        failed = [tc for tc in history if tc.get("error")]
        score -= len(failed) * 20.0

        # Penalize duplicate (tool, arguments) pairs among successful calls.
        successful = [tc for tc in history if not tc.get("error")]
        seen = set()
        duplicates = 0
        for tc in successful:
            key = (tc.get("tool"), _freeze(tc.get("arguments")))
            if key in seen:
                duplicates += 1
            seen.add(key)
        score -= duplicates * 15.0

        return max(0.0, score)


def _freeze(value: Any):
    """Make arguments hashable for duplicate detection."""
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value
