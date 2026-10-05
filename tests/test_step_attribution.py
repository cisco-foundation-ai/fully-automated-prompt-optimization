# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for step_attribution module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.hephaestus.analysis.step_attribution import (
    attribute_failures,
    attribute_results,
    summarize,
)


class TestAttributeFailures:
    """Tests for attribute_failures()."""

    def test_all_pass_no_attribution(self, tmp_path: Path):
        """All cases pass — no failures attributed."""
        results = [
            {"case_id": "c1", "composite_score": 100.0, "step_outputs": {"answer": "yes"}},
            {"case_id": "c2", "composite_score": 100.0, "step_outputs": {"answer": "no"}},
        ]
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(
            "\n".join(json.dumps(r) for r in results), encoding="utf-8"
        )

        attribution = attribute_failures(results_path)
        assert attribution == {}

    def test_retrieval_failure_empty_output(self, tmp_path: Path):
        """Empty retrieval output attributed to retrieval step."""
        results = [
            {
                "case_id": "c1",
                "composite_score": 0.0,
                "context": {"question": "What is Python?"},
                "step_outputs": {"retrieve_docs": "", "answer": "I don't know"},
            },
        ]
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(json.dumps(results[0]), encoding="utf-8")

        attribution = attribute_failures(results_path)
        assert "retrieve_docs" in attribution
        assert attribution["retrieve_docs"]["count"] == 1
        assert "c1" in attribution["retrieve_docs"]["case_ids"]

    def test_retrieval_failure_low_overlap(self):
        """An in-memory case supplies retrieval context without persisting it."""
        results = [
            {
                "case_id": "c1",
                "composite_score": 50.0,
                "step_outputs": {
                    "search_passages": "banana smoothie recipe blender instructions",
                    "answer": "Unknown",
                },
            },
        ]
        cases = [
            {
                "case_id": "c1",
                "context": {"question": "capital France geography Europe"},
                "expected": {},
            }
        ]

        attribution = attribute_results(results, cases)
        assert "search_passages" in attribution

    def test_final_step_attribution(self, tmp_path: Path):
        """Good intermediates but wrong final answer attributed to final step."""
        results = [
            {
                "case_id": "c1",
                "composite_score": 0.0,
                "context": {"question": "Is 2+2=4?"},
                "step_outputs": {
                    "summarize": "Basic arithmetic: 2+2=4.",
                    "answer": "no",
                },
            },
        ]
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(json.dumps(results[0]), encoding="utf-8")

        attribution = attribute_failures(results_path)
        assert "answer" in attribution
        assert attribution["answer"]["count"] == 1

    def test_empty_intermediate_step_attribution(self, tmp_path: Path):
        """Empty intermediate step output attributed to that step."""
        results = [
            {
                "case_id": "c1",
                "composite_score": 0.0,
                "context": {"question": "test"},
                "step_outputs": {
                    "step_one": "",
                    "step_two": "some output",
                    "answer": "wrong",
                },
            },
        ]
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(json.dumps(results[0]), encoding="utf-8")

        attribution = attribute_failures(results_path)
        assert "step_one" in attribution

    def test_no_step_outputs(self, tmp_path: Path):
        """Case with no step_outputs attributed to __no_steps__."""
        results = [
            {"case_id": "c1", "composite_score": 0.0},
        ]
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(json.dumps(results[0]), encoding="utf-8")

        attribution = attribute_failures(results_path)
        assert "__no_steps__" in attribution

    def test_multiple_failed_cases(self, tmp_path: Path):
        """Multiple failures accumulate counts per step."""
        results = [
            {
                "case_id": "c1",
                "composite_score": 0.0,
                "context": {"question": "q1"},
                "step_outputs": {"summarize": "ok", "answer": "wrong"},
            },
            {
                "case_id": "c2",
                "composite_score": 0.0,
                "context": {"question": "q2"},
                "step_outputs": {"summarize": "ok", "answer": "also wrong"},
            },
            {
                "case_id": "c3",
                "composite_score": 100.0,
                "step_outputs": {"summarize": "ok", "answer": "correct"},
            },
        ]
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(
            "\n".join(json.dumps(r) for r in results), encoding="utf-8"
        )

        attribution = attribute_failures(results_path)
        assert "answer" in attribution
        assert attribution["answer"]["count"] == 2
        assert set(attribution["answer"]["case_ids"]) == {"c1", "c2"}

    def test_custom_threshold(self, tmp_path: Path):
        """Custom threshold changes which cases are considered failed."""
        results = [
            {
                "case_id": "c1",
                "composite_score": 80.0,
                "context": {"question": "test"},
                "step_outputs": {"answer": "partial"},
            },
        ]
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(json.dumps(results[0]), encoding="utf-8")

        # With default threshold (100), this is a failure
        attr_default = attribute_failures(results_path, threshold=100.0)
        assert "answer" in attr_default

        # With threshold 50, this passes
        attr_low = attribute_failures(results_path, threshold=50.0)
        assert attr_low == {}


class TestAttributeResults:
    """Tests for privacy-safe in-memory attribution."""

    def test_joins_expected_answer_in_memory_without_returning_protected_data(self):
        """In-memory expected data enables format analysis but is never returned."""
        results = [
            {
                "case_id": "c1",
                "composite_score": 0.0,
                "step_outputs": {
                    "answer": "private-gold-answer with a long explanation"
                },
            }
        ]
        cases = [
            {
                "case_id": "c1",
                "context": {"question": "private-question-canary"},
                "expected": {"answer": "private-gold-answer"},
            }
        ]

        attribution = attribute_results(results, cases)

        assert attribution["answer"]["heuristic"] == "format_failure"
        serialized = json.dumps(attribution, sort_keys=True)
        assert "private-question-canary" not in serialized
        assert "private-gold-answer" not in serialized

    def test_aggregates_every_heuristic_and_confidence_observation_per_step(self):
        """Later failure kinds cannot be hidden behind a step's first observation."""
        results = [
            {
                "case_id": "format",
                "composite_score": 0.0,
                "step_outputs": {"answer": "gold answer plus a long explanation"},
            },
            {
                "case_id": "reasoning",
                "composite_score": 0.0,
                "step_outputs": {"answer": "wrong"},
            },
        ]
        cases = [
            {
                "case_id": "format",
                "context": {},
                "expected": {"answer": "gold answer"},
            },
            {"case_id": "reasoning", "context": {}, "expected": {}},
        ]

        attribution = attribute_results(results, cases)

        assert attribution["answer"]["heuristic_counts"] == {
            "format_failure": 1,
            "final_step_fallback": 1,
        }
        assert attribution["answer"]["confidence_counts"] == {
            "medium": 1,
            "low": 1,
        }
        assert attribution["answer"]["heuristic"] == "format_failure"
        assert attribution["answer"]["confidence"] == "medium"

    def test_aggregates_retrieval_tiers_per_step(self):
        """A retrieval step retains both miss and partial observations."""
        results = [
            {
                "case_id": "miss",
                "composite_score": 0.0,
                "step_outputs": {"retrieve": "unrelated", "answer": "wrong"},
            },
            {
                "case_id": "partial",
                "composite_score": 0.0,
                "step_outputs": {"retrieve": "red", "answer": "wrong"},
            },
        ]
        cases = [
            {
                "case_id": "miss",
                "context": {"question": "red blue green yellow"},
                "expected": {},
            },
            {
                "case_id": "partial",
                "context": {"question": "red blue green yellow"},
                "expected": {},
            },
        ]

        attribution = attribute_results(results, cases)

        assert attribution["retrieve"]["retrieval_tier_counts"] == {
            "miss": 1,
            "partial": 1,
        }
        assert attribution["retrieve"]["retrieval_tier"] == "miss"

    def test_aggregates_tool_error_types_per_step(self):
        """A tool step retains every classified error observation."""
        results = [
            {
                "case_id": "timeout",
                "composite_score": 0.0,
                "step_outputs": {"answer": "wrong"},
                "tool_call_history": [
                    {"tool": "lookup", "error": "request timed out"}
                ],
            },
            {
                "case_id": "permission",
                "composite_score": 0.0,
                "step_outputs": {"answer": "wrong"},
                "tool_call_history": [
                    {"tool": "lookup", "error": "permission denied"}
                ],
            },
        ]
        cases = [
            {"case_id": "timeout", "context": {}, "expected": {}},
            {"case_id": "permission", "context": {}, "expected": {}},
        ]

        attribution = attribute_results(results, cases)

        assert attribution["tool_lookup"]["tool_error_type_counts"] == {
            "timeout": 1,
            "permission": 1,
        }
        assert attribution["tool_lookup"]["tool_error_type"] == "timeout"

    def test_reports_execution_failure_separately_from_scored_failures(self):
        """Infrastructure failures never masquerade as model-score attribution."""
        results = [
            {
                "case_id": "outage",
                "composite_score": 0.0,
                "step_outputs": {"answer": ""},
                "execution_status": "failed",
                "execution_error": {
                    "phase": "chain",
                    "category": "runtime",
                    "summary": "Chain execution failed.",
                },
                "evaluation_provenance": {},
            },
            {
                "case_id": "legitimate-zero",
                "composite_score": 0.0,
                "step_outputs": {"answer": "wrong"},
                "execution_status": "succeeded",
            },
        ]
        cases = [
            {"case_id": "outage", "context": {}, "expected": {}},
            {"case_id": "legitimate-zero", "context": {}, "expected": {}},
        ]

        attribution = attribute_results(results, cases)

        assert attribution["__infrastructure__"]["case_ids"] == ["outage"]
        assert attribution["__infrastructure__"]["failure_stage_counts"] == {
            "chain": 1
        }
        assert attribution["answer"]["case_ids"] == ["legitimate-zero"]
        assert "Chain execution failed." not in json.dumps(attribution)

    def test_requires_exact_ordered_case_join(self):
        """A reordered case collection cannot silently misjoin protected inputs."""
        results = [
            {"case_id": "c1", "composite_score": 0.0, "step_outputs": {}},
            {"case_id": "c2", "composite_score": 0.0, "step_outputs": {}},
        ]
        cases = [
            {"case_id": "c2", "context": {}, "expected": {}},
            {"case_id": "c1", "context": {}, "expected": {}},
        ]

        with pytest.raises(ValueError, match="ordered case IDs"):
            attribute_results(results, cases)

    def test_legacy_file_does_not_trust_embedded_protected_fields(
        self, tmp_path: Path
    ):
        """Legacy result files remain context-free without a verified dataset join."""
        result = {
            "case_id": "c1",
            "composite_score": 0.0,
            "context": {"question": "red blue green yellow"},
            "expected_answer": "private-gold-answer",
            "step_outputs": {
                "search_passages": "unrelated",
                "answer": "private-gold-answer with a long explanation",
            },
        }
        results_path = tmp_path / "results.jsonl"
        results_path.write_text(json.dumps(result), encoding="utf-8")

        attribution = attribute_failures(results_path)

        assert "search_passages" not in attribution
        assert attribution["answer"]["heuristic"] == "final_step_fallback"

    def test_summary_uses_observation_maps_and_separates_infrastructure(self):
        """Summary counts mixed observations without treating outages as prompts."""
        attribution = {
            "answer": {
                "count": 2,
                "case_ids": ["format", "reasoning"],
                "heuristic": "format_failure",
                "confidence": "medium",
                "heuristic_counts": {
                    "format_failure": 1,
                    "final_step_fallback": 1,
                },
                "confidence_counts": {"medium": 1, "low": 1},
            },
            "retrieve": {
                "count": 2,
                "case_ids": ["miss", "partial"],
                "heuristic": "retrieval_overlap",
                "confidence": "high",
                "heuristic_counts": {"retrieval_overlap": 2},
                "confidence_counts": {"high": 1, "medium": 1},
                "retrieval_tier": "miss",
                "retrieval_tier_counts": {"miss": 1, "partial": 1},
            },
            "__infrastructure__": {
                "count": 1,
                "case_ids": ["outage"],
                "heuristic": "execution_failure",
                "confidence": "high",
                "heuristic_counts": {"execution_failure": 1},
                "confidence_counts": {"high": 1},
                "infrastructure_failure": True,
                "failure_stage_counts": {"chain": 1},
            },
        }

        summary = summarize(attribution)

        assert summary["prompt_addressable"] == 2
        assert summary["structural_addressable"] == 2
        assert summary["infrastructure_failures"] == 1
        assert summary["total_failures"] == 5
        assert summary["by_confidence"] == {"high": 2, "medium": 2, "low": 1}
        assert summary["by_retrieval_tier"] == {
            "hit": 0,
            "partial": 1,
            "miss": 1,
        }
