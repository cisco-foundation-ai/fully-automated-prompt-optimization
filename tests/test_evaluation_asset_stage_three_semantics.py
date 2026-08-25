# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from src.hephaestus.evaluation_assets.legacy_validation import (
    _validate_stage_three,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    compile_evaluation_guidelines,
    normalize_guideline_response,
    replay_native_stage_three,
    trusted_intent_from_guideline,
)


def test_native_trusted_intent_uses_all_prior_user_request_semantics() -> None:
    guideline = {
        "guideline_id": "guideline-task-route-1",
        "intent_label": "downstream label canary",
        "description": "normative description canary",
        "source_record_ids": ["feedback-1"],
        "route": "task_route",
        "criteria": [{"statement": "normative criterion canary"}],
    }
    normalized_by_id = {
        "feedback-1": {
            "group_id": "group-1",
            "user_input": "  source request semantics  ",
            "conversation_context": [
                {"role": "user", "content": "first user turn"},
                {"role": "assistant", "content": "latest context semantics"},
                {"role": "user", "content": "second user turn"},
            ],
            "tool_calls": [
                {"name": "lookup_tool", "arguments": {}},
                {"name": "archive", "arguments": {}},
                {"name": "lookup_tool", "arguments": {"query": "repeat"}},
            ],
            "feedback": {"polarity": "negative"},
        }
    }

    trusted_intent = trusted_intent_from_guideline(guideline, normalized_by_id)

    assert trusted_intent["label"] == "downstream label canary"
    assert trusted_intent["texts"] == [
        "source request semantics first user turn second user turn tools archive lookup_tool"
    ]


def test_historical_trusted_intent_profile_replays_normative_texts() -> None:
    guideline = {
        "guideline_id": "guideline-task-route-1",
        "intent_label": "complete task",
        "description": "Historical guideline description.",
        "source_record_ids": ["feedback-1"],
        "route": "task_route",
        "criteria": [{"statement": "Historical criterion statement."}],
    }
    normalized_by_id = {
        "feedback-1": {
            "group_id": "group-1",
            "user_input": "Historical source request.",
            "conversation_context": [],
            "tool_calls": [],
            "feedback": {"polarity": "positive"},
        }
    }

    trusted_intent = trusted_intent_from_guideline(
        guideline,
        normalized_by_id,
        text_profile="historical_v1",
    )

    assert trusted_intent["texts"] == [
        "Historical guideline description.",
        "Historical criterion statement.",
        "Historical source request.",
    ]


def test_trusted_intent_rejects_an_unknown_text_profile() -> None:
    guideline = {
        "guideline_id": "guideline-task-route-1",
        "intent_label": "complete task",
        "description": "Guideline description.",
        "source_record_ids": ["feedback-1"],
        "route": "task_route",
        "criteria": [{"statement": "Criterion statement."}],
    }
    normalized_by_id = {
        "feedback-1": {
            "group_id": "group-1",
            "user_input": "Source request.",
            "conversation_context": [],
            "tool_calls": [],
            "feedback": {"polarity": "positive"},
        }
    }

    with pytest.raises(ValueError, match="trusted-intent text profile"):
        trusted_intent_from_guideline(
            guideline,
            normalized_by_id,
            text_profile="legacy",
        )


def test_native_stage_three_replay_preserves_historical_trusted_intent_texts() -> None:
    """Native historical replay preserves both historical text and identities."""
    normalized = [
        {
            "record_id": "feedback-1",
            "group_id": "group-1",
            "route": "task_route",
            "task_type": "task_route",
            "request_id": "request-1",
            "user_input": "Historical source request.",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "feedback": {"polarity": "positive"},
        }
    ]
    evidence = [_evidence("feedback-1", "group-1")]
    candidates = [_candidate("feedback-1")]

    replayed = replay_native_stage_three(
        normalized,
        evidence,
        candidates,
        asset_id="asset-v1",
        identity_profile="historical_v1",
        text_profile="historical_v1",
    )

    assert replayed["trusted_intents"][0]["texts"] == [
        "Historical guideline description.",
        "Historical criterion statement.",
        "Historical source request.",
    ]
    assert replayed["guidelines"][0]["guideline_id"] == (
        "guideline-task-route-2db504df10"
    )
    assert replayed["guidelines"][0]["criteria"][0]["criterion_id"] == (
        "criterion-6c777f7e3e"
    )


def test_native_stage_three_replay_selects_current_identity_and_text_profiles() -> None:
    """Native v3 replay reproduces current identities and source-only text."""
    normalized = [
        {
            "record_id": "feedback-1",
            "group_id": "group-1",
            "route": "task_route",
            "task_type": "task_route",
            "request_id": "request-1",
            "user_input": "Current source request.",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "feedback": {"polarity": "positive"},
        }
    ]

    replayed = replay_native_stage_three(
        normalized,
        [_evidence("feedback-1", "group-1")],
        [_candidate("feedback-1")],
        asset_id="asset-v3",
        identity_profile="current_v2",
        text_profile="current",
    )

    assert replayed["trusted_intents"][0]["texts"] == [
        "Current source request."
    ]
    assert re.fullmatch(
        r"guideline-task-route-[0-9a-f]{64}",
        str(replayed["guidelines"][0]["guideline_id"]),
    )
    assert re.fullmatch(
        r"criterion-[0-9a-f]{64}",
        str(replayed["guidelines"][0]["criteria"][0]["criterion_id"]),
    )


@pytest.mark.parametrize(
    ("identity_profile", "text_profile"),
    [
        ("current_v2", "historical_v1"),
        ("historical_v1", "current"),
    ],
)
def test_native_stage_three_replay_rejects_mixed_generation_profiles(
    identity_profile: str,
    text_profile: str,
) -> None:
    """A replay cannot combine identities and text from different generations."""
    normalized = [
        {
            "record_id": "feedback-1",
            "group_id": "group-1",
            "route": "task_route",
            "task_type": "task_route",
            "request_id": "request-1",
            "user_input": "Source request.",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "feedback": {"polarity": "positive"},
        }
    ]

    with pytest.raises(ValueError, match="Stage 3 replay profiles"):
        replay_native_stage_three(
            normalized,
            [_evidence("feedback-1", "group-1")],
            [_candidate("feedback-1")],
            asset_id="asset-v3",
            identity_profile=identity_profile,  # type: ignore[arg-type]
            text_profile=text_profile,  # type: ignore[arg-type]
        )


def test_stage_three_semantic_validation_threads_current_replay_profiles(
    tmp_path: Path,
) -> None:
    """The v3 semantic validator replays the writer's current generation."""

    class Layout:
        asset_id = "asset-v3"
        manifest_path = tmp_path / "asset_manifest.json"

        @staticmethod
        def artifact_path(stage: Any, name: str) -> Path:
            value = str(getattr(stage, "value", stage))
            return tmp_path / value / name

    normalized = [
        {
            "record_id": "feedback-1",
            "group_id": "group-1",
            "route": "task_route",
            "task_type": "task_route",
            "request_id": "request-1",
            "user_input": "Current source request.",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "feedback": {"polarity": "positive"},
        }
    ]
    evidence = [_evidence("feedback-1", "group-1")]
    candidates = [_candidate("feedback-1")]
    replayed = replay_native_stage_three(
        normalized,
        evidence,
        candidates,
        asset_id=Layout.asset_id,
        identity_profile="current_v2",
        text_profile="current",
    )

    def jsonl(rows: list[dict[str, Any]]) -> bytes:
        return "".join(
            f"{json.dumps(row, sort_keys=True)}\n" for row in rows
        ).encode("utf-8")

    snapshot = {
        Layout.artifact_path("rubric_extraction", "trusted_intents.jsonl"): jsonl(
            replayed["trusted_intents"]
        ),
        Layout.artifact_path("rubric_extraction", "trusted_cases.jsonl"): jsonl(
            replayed["trusted_cases"]
        ),
        Layout.artifact_path("rubric_extraction", "feedback_evidence.jsonl"): jsonl(
            evidence
        ),
        Layout.artifact_path(
            "rubric_extraction", "candidate_guidelines.jsonl"
        ): jsonl(candidates),
        Layout.artifact_path(
            "rubric_extraction", "evaluation_guidelines.jsonl"
        ): jsonl(replayed["guidelines"]),
        Layout.manifest_path: json.dumps(
            {
                "providers": {
                    "rubric_provider": "test-provider",
                    "rubric_model": "test-model",
                }
            }
        ).encode("utf-8"),
    }

    trusted_intents, trusted_cases = _validate_stage_three(
        Layout(),
        "native",
        {"feedback-1": normalized[0]},
        snapshot,
        identity_profile="current_v2",
        text_profile="current",
    )

    assert trusted_intents[replayed["guidelines"][0]["guideline_id"]] == (
        replayed["trusted_intents"][0]
    )
    assert trusted_cases == replayed["trusted_cases"]


def test_current_v2_identities_distinguish_source_and_parent_semantics() -> None:
    """Current identities cover source provenance and complete parent semantics."""
    evidence = [
        _evidence("feedback-1", "group-1"),
        _evidence("feedback-2", "group-2"),
    ]
    changed_description = _candidate("feedback-1")
    changed_description["description"] = "A distinct persisted description."
    candidates = [
        _candidate("feedback-1"),
        _candidate("feedback-2"),
        changed_description,
    ]

    guidelines = compile_evaluation_guidelines(
        candidates,
        evidence,
        "test-provider",
        "test-model",
        identity_profile="current_v2",
    )

    guideline_ids = {str(row["guideline_id"]) for row in guidelines}
    criterion_ids = {
        str(criterion["criterion_id"])
        for guideline in guidelines
        for criterion in guideline["criteria"]
    }
    assert len(guideline_ids) == 3
    assert len(criterion_ids) == 3
    assert all(
        re.fullmatch(r"guideline-task-route-[0-9a-f]{64}", value)
        for value in guideline_ids
    )
    assert all(
        re.fullmatch(r"criterion-[0-9a-f]{64}", value)
        for value in criterion_ids
    )


def test_current_v2_criterion_identity_includes_order() -> None:
    """Repeated criterion semantics remain unique through persisted order."""
    candidate = _candidate("feedback-1")
    candidate["criteria"] = [
        candidate["criteria"][0],
        dict(candidate["criteria"][0]),
    ]

    guidelines = compile_evaluation_guidelines(
        [candidate],
        [_evidence("feedback-1", "group-1")],
        "test-provider",
        "test-model",
        identity_profile="current_v2",
    )

    criterion_ids = [
        str(row["criterion_id"]) for row in guidelines[0]["criteria"]
    ]
    assert len(set(criterion_ids)) == 2
    assert [row["order"] for row in guidelines[0]["criteria"]] == [1, 2]


def test_historical_v1_identity_preserves_exact_legacy_ids() -> None:
    """The historical identity profile reproduces exact legacy identifiers."""
    _, guidelines = normalize_guideline_response(
        {"guidelines": [_candidate("feedback-1")]},
        route="task_route",
        evidence=[_evidence("feedback-1", "group-1")],
        rubric_provider="test-provider",
        rubric_model="test-model",
        identity_profile="historical_v1",
    )

    assert guidelines[0]["guideline_id"] == "guideline-task-route-2db504df10"
    assert guidelines[0]["criteria"][0]["criterion_id"] == (
        "criterion-6c777f7e3e"
    )


def test_guideline_compilation_rejects_an_unknown_identity_profile() -> None:
    """Unknown identity profiles fail closed instead of selecting a fallback."""
    with pytest.raises(ValueError, match="guideline identity profile"):
        compile_evaluation_guidelines(
            [_candidate("feedback-1")],
            [_evidence("feedback-1", "group-1")],
            "test-provider",
            "test-model",
            identity_profile="future_v3",  # type: ignore[arg-type]
        )


def _evidence(record_id: str, group_id: str) -> dict[str, object]:
    return {
        "record_id": record_id,
        "group_id": group_id,
        "route": "task_route",
        "task_type": "task_route",
        "intent_label": "complete task",
        "confidence": 0.9,
        "observations": [],
        "requested_corrections": [],
        "uncertainties": [],
        "evidence_source": "trusted_feedback",
        "guideline_provider": "test-provider",
        "guideline_model": "test-model",
    }


def _candidate(record_id: str) -> dict[str, object]:
    return {
        "intent_label": "complete task",
        "description": "Historical guideline description.",
        "route": "task_route",
        "source_record_ids": [record_id],
        "confidence": 0.9,
        "criteria": [
            {
                "kind": "required",
                "statement": "Historical criterion statement.",
                "source_record_ids": [record_id],
                "dimension": "task_success",
                "severity": "critical",
                "applicability": "always",
                "scoring": "binary",
                "evidence_required": True,
                "evaluator": {
                    "type": "state_check",
                    "fallback": "human_review",
                },
            }
        ],
        "tool_expectations": {},
        "reference_output": None,
        "conflicts": [],
        "uncertainties": [],
    }
