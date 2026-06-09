# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Task completion scorer for mcp_example tenant."""

from typing import Any, Dict, List, Optional

from src.hephaestus.scoring.scorer import Scorer as BaseScorer


class TaskScorer(BaseScorer):
    """Score agent task completion based on answer quality and tool usage.

    This scorer inspects the actual tool_call_history to verify correct tool usage.
    """

    def validate_case(self, case, scoring_profile):
        """Verify case has required fields."""
        assert "task" in case.context, f"Case {case.case_id}: missing 'task'"
        assert case.expected is not None, f"Case {case.case_id}: missing expected dict"

    def score_case(self, case, output_text, scoring_profile):
        """Default score_case - calls score_pipeline_case with no tool history."""
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
        """Score based on answer correctness and actual tool usage.

        Metrics:
        - answer_present (0-100): Did agent provide a clear answer?
        - answer_correct (0-100): Does answer contain expected content?
        - tool_usage (0-100): Did agent use the right tools?
        - tool_efficiency (0-100): Did agent use tools efficiently (not too many calls)?
        - composite_score: Weighted average of all metrics

        Args:
            case: Evaluation case
            step_outputs: Intermediate outputs (unused here)
            scoring_profile: Scoring configuration
            output_text: Final output from chain
            tool_call_history: List of tool calls made (if any)

        Returns:
            Dict with composite_score and score_breakdown
        """
        if output_text is None:
            output_text = ""

        expected = case.expected
        output_lower = output_text.lower()

        # 1. Check if answer is present (looks for "answer:" marker)
        answer_present = 100.0 if "answer:" in output_lower else 50.0

        # 2. Check if answer contains expected content
        answer_correct = 0.0
        if "answer_contains" in expected:
            expected_content = expected["answer_contains"].lower()
            if expected_content in output_lower:
                answer_correct = 100.0
            else:
                # Partial credit for having numbers/words from expected
                words = expected_content.split()
                matches = sum(1 for w in words if w in output_lower)
                answer_correct = (matches / len(words)) * 50.0 if words else 0.0

        # 3. Check tool usage based on actual tool_call_history
        tool_usage_score = 100.0
        expected_tools = expected.get("tools_used", [])

        if tool_call_history is not None:
            # Extract tool names from history (excluding failed calls)
            actual_tools = [
                tc.get("tool") for tc in tool_call_history if not tc.get("error")
            ]
            actual_tool_set = set(actual_tools)
            expected_tool_set = set(expected_tools)

            if len(expected_tools) == 0:
                # Should NOT use tools
                if len(actual_tools) == 0:
                    tool_usage_score = 100.0  # Correctly avoided tools
                else:
                    tool_usage_score = 30.0  # Used tools when shouldn't
            else:
                # Should use specific tools
                if expected_tool_set.issubset(actual_tool_set):
                    # Used all required tools
                    tool_usage_score = 100.0
                elif len(expected_tool_set & actual_tool_set) > 0:
                    # Used some required tools
                    overlap = len(expected_tool_set & actual_tool_set)
                    tool_usage_score = (overlap / len(expected_tool_set)) * 70.0
                else:
                    # Used wrong tools or no tools
                    tool_usage_score = 10.0 if len(actual_tools) > 0 else 0.0

        # 4. Check tool efficiency (penalize excessive tool calls)
        tool_efficiency = 100.0
        if tool_call_history is not None and len(tool_call_history) > 0:
            successful_calls = [tc for tc in tool_call_history if not tc.get("error")]
            failed_calls = [tc for tc in tool_call_history if tc.get("error")]

            # Penalize failed tool calls
            if failed_calls:
                tool_efficiency -= len(failed_calls) * 20.0

            # Penalize excessive calls (more than 2x expected)
            expected_call_count = len(expected_tools) if expected_tools else 0
            actual_call_count = len(successful_calls)

            if expected_call_count > 0:
                if actual_call_count > expected_call_count * 2:
                    tool_efficiency -= (actual_call_count - expected_call_count * 2) * 10.0

            tool_efficiency = max(0.0, tool_efficiency)  # Don't go below 0

        # Composite score: weighted average
        # Prioritize answer correctness, then tool usage, then efficiency
        composite = (
            0.15 * answer_present
            + 0.50 * answer_correct
            + 0.25 * tool_usage_score
            + 0.10 * tool_efficiency
        )

        return {
            "composite_score": composite,
            "score_breakdown": {
                "answer_present": answer_present,
                "answer_correct": answer_correct,
                "tool_usage": tool_usage_score,
                "tool_efficiency": tool_efficiency,
            },
        }
