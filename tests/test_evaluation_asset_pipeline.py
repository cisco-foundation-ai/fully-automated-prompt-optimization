# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.hephaestus import artifact_io
from src.hephaestus.datasets.intent_assets import IntentCluster
from src.hephaestus.datasets.jsonl_loader import load_cases
from src.hephaestus.evaluation_assets import pipeline as pipeline_module
from src.hephaestus.evaluation_assets.durability import (
    build_stage_receipt,
    file_sha256,
)
from src.hephaestus.evaluation_assets.models import (
    STAGE_COUNT_KEYS,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.pipeline import (
    EVIDENCE_EXTRACTION_PROMPT,
    FULL_CATALOG_RUBRIC_PROMPT,
    GUIDELINE_SYNTHESIS_PROMPT,
    EvaluationAssetPipeline,
    _compile_evaluation_guidelines,
    _compact_tool_result,
    _feedback_provider_record,
    _full_catalog_episode_payload,
    _guideline_provider_example,
    _normalize_aliased_guideline_response,
    _normalize_feedback_evidence,
    _normalize_feedback,
    _normalize_full_catalog_rubric_response,
    _normalize_intent,
    _normalize_rubric,
    _rubric_from_guidelines,
)
from src.hephaestus.evaluation_assets.publication import (
    resolve_evaluation_asset_release,
)
from src.hephaestus.evaluation_assets.review import case_content_fingerprint
from src.hephaestus.evaluation_assets.service import EvaluationAssetRunManager
from src.hephaestus.evaluation_assets.workspace import (
    EvaluationAssetLayout,
    utc_now,
)


def test_review_source_uses_episode_guideline_when_cluster_match_is_missing() -> None:
    """An episode-first decision can support a case from a weak cluster."""
    dependency = pipeline_module.build_stage_six_dependency(
        cluster={"cluster_id": "cluster-1"},
        match={"matched_intent_id": None},
        guideline={"guideline_ids": ["guideline-1"]},
        source_members=[
            {
                "identity": "unlabeled:u1",
                "content_sha256": "a" * 64,
            }
        ],
        provider={"provider": "fake", "model": "fake"},
        prompt={"revision": "episode-v1", "sha256": "b" * 64},
        algorithm_revision="episode-first-v1",
    )

    provenance = pipeline_module._review_source_provenance(
        {
            "case_id": "inferred-u1",
            "metadata": {
                "source_cluster": "cluster-1",
                "matched_intent_id": None,
                "applicable_guideline_ids": ["guideline-1"],
            },
        },
        dependency,
    )

    assert provenance == {
        "source_record_ids": ["u1"],
        "source_record_sha256s": ["sha256:" + "a" * 64],
        "source_cluster": "cluster-1",
        "matched_intent_id": "guideline-1",
    }


def test_full_catalog_episode_payload_contains_complete_trace_evidence() -> None:
    guideline = {"guideline_id": "guideline-1", "criteria": []}
    payload = _full_catalog_episode_payload(
        {
            "record_id": "episode-1",
            "group_id": "group-1",
            "request_id": "request-1",
            "task_type": "support",
            "route": "support",
            "user_input": "Please cancel the order.",
            "assistant_output": "The order was cancelled.",
            "conversation_context": [
                {"role": "user", "content": "I need help with an order."},
                {"role": "assistant", "content": "Which order?"},
            ],
            "tool_calls": [
                {
                    "name": "cancel_order",
                    "arguments": {"order_id": "order-1"},
                    "result": {"status": "cancelled"},
                }
            ],
            "runtime": {"channel": "chat"},
        },
        [guideline],
        trusted_feedback={"polarity": "positive", "rationale": "Correct."},
    )

    assert payload["mode"] == "full_catalog_episode_rubric"
    assert payload["evaluation_guidelines"] == [guideline]
    assert payload["episode"]["user_messages"] == [
        "I need help with an order.",
        "Please cancel the order.",
    ]
    assert payload["episode"]["assistant_messages"] == [
        {"pointer": "conversation_context[1]", "content": "Which order?"},
        {"pointer": "assistant_output", "content": "The order was cancelled."},
    ]
    assert payload["episode"]["tool_observations"][0]["outcome_status"] == (
        "result_returned"
    )
    assert payload["episode"]["tool_observations"][0]["result_state"] == {
        "status": "cancelled"
    }
    assert "tau" not in FULL_CATALOG_RUBRIC_PROMPT.lower()


def test_full_catalog_rubric_supports_guideline_and_trace_inferred_provenance() -> None:
    guideline = {"guideline_id": "guideline-1", "criteria": []}
    common = {
        "record_id": "episode-1",
        "intent_label": "cancel order",
        "confidence": 0.9,
        "must": ["Complete the requested action."],
        "must_not": [],
        "should": [],
        "deterministic_checks": [],
        "tool_expectations": {},
        "reference_output": None,
        "evidence_pointers": ["episode.user_messages[0]"],
    }
    grounded = _normalize_full_catalog_rubric_response(
        {
            "rubrics": [
                {
                    **common,
                    "applicable_guideline_ids": ["guideline-1"],
                    "provenance": "guideline_grounded",
                }
            ]
        },
        record_id="episode-1",
        guidelines=[guideline],
        rubric_provider="fake",
        rubric_model="fake",
        trusted=False,
    )
    inferred = _normalize_full_catalog_rubric_response(
        {
            "rubrics": [
                {
                    **common,
                    "applicable_guideline_ids": [],
                    "provenance": "trace_inferred",
                }
            ]
        },
        record_id="episode-1",
        guidelines=[guideline],
        rubric_provider="fake",
        rubric_model="fake",
        trusted=False,
    )

    assert grounded["label_source"] == "inferred_from_trusted_feedback"
    assert grounded["evaluation_guidelines"] == [guideline]
    assert inferred["label_source"] == "trace_inferred"
    assert inferred["evaluation_guidelines"] == []
    with pytest.raises(ValueError, match="provenance"):
        _normalize_full_catalog_rubric_response(
            {
                "rubrics": [
                    {
                        **common,
                        "applicable_guideline_ids": [],
                        "provenance": "guideline_grounded",
                    }
                ]
            },
            record_id="episode-1",
            guidelines=[guideline],
            rubric_provider="fake",
            rubric_model="fake",
            trusted=False,
        )


class FakeEmbeddingProvider:
    provider_name = "fake"
    model = "fake-embedding"

    def __init__(self):
        self.calls = 0

    def embed_texts(self, texts):
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


class MalformedEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self, malformed_call: int):
        super().__init__()
        self.malformed_call = malformed_call

    def embed_texts(self, texts):
        self.calls += 1
        if self.calls == self.malformed_call:
            return [[0.0, 0.0] for _ in texts]
        return [[1.0, 0.0] for _ in texts]


class SecretFailingEmbeddingProvider(FakeEmbeddingProvider):
    def embed_texts(self, texts):
        raise RuntimeError(
            'sk-live-secret-token raw_response={"email":"private@example.com"}'
        )


class FakeRubricProvider:
    provider_name = "fake"
    model = "fake-rubric"

    def __init__(self):
        self.synthetic_calls = 0
        self.episode_rubric_calls = 0
        self.feedback_record_ids = []
        self.calls = 0

    def generate_json(self, system_prompt, payload):
        self.calls += 1
        if payload.get("mode") == "full_catalog_episode_rubric":
            self.episode_rubric_calls += 1
            guideline_ids = [
                row["guideline_id"]
                for row in payload["evaluation_guidelines"]
            ]
            return {
                "rubrics": [
                    {
                        "record_id": payload["episode"]["record_id"],
                        "applicable_guideline_ids": guideline_ids,
                        "provenance": (
                            "guideline_grounded" if guideline_ids else "trace_inferred"
                        ),
                        "intent_label": "answer the request",
                        "confidence": 0.8,
                        "must": ["Answer the user's stated request."],
                        "must_not": ["Change the requested scope."],
                        "should": ["Be concise."],
                        "deterministic_checks": [],
                        "tool_expectations": {},
                        "reference_output": None,
                        "evidence_pointers": ["episode.user_messages[0]"],
                    }
                ]
            }
        if "records" in payload:
            self.feedback_record_ids.extend(
                row["record_id"] for row in payload["records"]
            )
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "answer the request",
                        "confidence": 0.9,
                        "observations": [
                            {
                                "claim": "Answer the user's stated request.",
                                "evidence_type": "explicit_feedback",
                                "evidence_pointer": "feedback.rationale",
                                "polarity": row["feedback"]["polarity"],
                            }
                        ],
                        "requested_corrections": [],
                        "uncertainties": [],
                    }
                    for row in payload["records"]
                ]
            }
        if "evidence" in payload:
            return {
                "guidelines": [
                    {
                        "intent_label": "answer the request",
                        "description": "Answer requests within their stated scope.",
                        "route": payload["route"],
                        "source_record_ids": [
                            row["record_id"] for row in payload["evidence"]
                        ],
                        "confidence": 0.9,
                        "criteria": [
                            {
                                "kind": "required",
                                "statement": "Answer the user's stated request.",
                                "dimension": "task_success",
                                "severity": "critical",
                                "applicability": "always",
                                "scoring": "binary",
                                "evidence_required": False,
                                "evaluator": {
                                    "type": "llm_judge",
                                    "fallback": "human_review",
                                },
                            },
                            {
                                "kind": "prohibited",
                                "statement": "Change the requested scope.",
                                "dimension": "instruction_following",
                                "severity": "major",
                                "applicability": "always",
                                "scoring": "binary",
                                "evidence_required": False,
                                "evaluator": {
                                    "type": "llm_judge",
                                    "fallback": "human_review",
                                },
                            },
                        ],
                        "tool_expectations": {},
                        "reference_output": None,
                    }
                ]
            }
        if "synthetic evaluation input" in system_prompt:
            self.synthetic_calls += 1
            return {
                "cases": [
                    {
                        "cluster_id": row["cluster_id"],
                        "task_type": row["route"],
                        "user_input": (
                            f"Variation-{case_index + 1} request for "
                            f"{row['cluster_id']}"
                        ),
                        "conversation_context": [],
                    }
                    for row in payload["clusters"]
                    for case_index in range(row["case_count"])
                ]
            }
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "answer the request",
                    "confidence": 0.8,
                    "must": ["Answer the user's stated request."],
                    "must_not": ["Change the requested scope."],
                    "should": ["Be concise."],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
                for row in payload["clusters"]
            ]
        }


def test_compact_tool_result_retains_item_identity_with_parent_state() -> None:
    """Compaction keeps entity identity needed to resolve mixed-state episodes."""
    compact = _compact_tool_result(
        {
            "resource_id": "resource-1",
            "status": "delivered",
            "items": [
                {
                    "item_id": "item-1",
                    "product_id": "product-1",
                    "name": "Requested Resource",
                    "options": {"large": "payload"},
                }
            ],
            "variants": {"large": "payload"},
        }
    )

    assert compact == {
        "resource_id": "resource-1",
        "status": "delivered",
        "items": [
            {
                "item_id": "item-1",
                "product_id": "product-1",
                "name": "Requested Resource",
            }
        ],
    }


class SecretFailingRubricProvider(FakeRubricProvider):
    def generate_json(self, system_prompt, payload):
        raise RuntimeError(
            'sk-live-secret-token raw_response={"email":"private@example.com"}'
        )


class SecretMalformedRubricProvider(FakeRubricProvider):
    def __init__(self, malformed_response: str):
        super().__init__()
        self.malformed_response = malformed_response

    def generate_json(self, system_prompt, payload):
        response = super().generate_json(system_prompt, payload)
        if self.malformed_response == "evidence" and "records" in payload:
            response["evidence"][0]["confidence"] = "sk-live-secret-token"
        elif self.malformed_response == "guideline" and "evidence" in payload:
            response["guidelines"][0]["confidence"] = "sk-live-secret-token"
        elif (
            self.malformed_response == "inferred"
            and payload.get("mode") == "full_catalog_episode_rubric"
        ):
            response["rubrics"][0]["confidence"] = "sk-live-secret-token"
        elif (
            self.malformed_response == "synthetic"
            and "synthetic evaluation input" in system_prompt
        ):
            response["cases"][0]["user_input"] = ""
            response["cases"][0]["note"] = "sk-live-secret-token"
        return response


def _approve_and_finalize(pipeline: EvaluationAssetPipeline) -> PipelineState:
    """Run through the explicit review boundary for release-oriented tests."""
    state = pipeline.run()
    assert state.status == "awaiting_review"
    page = pipeline.layout.list_review_items()
    for item in page["items"]:
        pipeline.layout.decide_review(
            item["case_id"],
            item["fingerprint"],
            "approved",
            reviewer="test-reviewer",
            expected_review_set_fingerprint=page["review_set_fingerprint"],
        )
    page = pipeline.layout.list_review_items()
    return pipeline.finalize_review(
        reviewer="test-reviewer",
        expected_review_set_fingerprint=page["review_set_fingerprint"],
        expected_decision_set_fingerprint=page["decision_set_fingerprint"],
    )


def test_normalization_preserves_structural_fields_and_redacts_content() -> None:
    """Schema structure survives while content-bearing PII is redacted."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": " record.owner@example.com ",
        "group_id": " group.owner@example.com ",
        "request_id": " request.owner@example.com ",
        "task_type": " task.owner@example.com ",
        "route": " route.owner@example.com ",
        "intent_label": " intent.owner@example.com ",
        "user_input": "Contact user@example.com from 192.0.2.1.",
        "assistant_output": "Reached assistant@example.com at 192.0.2.2.",
        "conversation_context": [
            {
                "role": " role.owner@example.com ",
                "content": "Earlier user@example.com at 192.0.2.3.",
                "metadata": {
                    "intent_label": "context.owner@example.com",
                    "note": "Escalate to context@example.com.",
                },
            }
        ],
        "tool_calls": [
            {
                "name": " lookup.owner@example.com ",
                "arguments": {
                    "address": "argument@example.com",
                    "nested": ["192.0.2.4"],
                },
                "result": {"owner": "result@example.com"},
                "error": "Tool error for error@example.com",
            }
        ],
        "runtime": {
            "model": " model.owner@example.com ",
            "unknown_leaf": "runtime-unknown@example.com",
            "request": {
                "content": "Runtime payload runtime@example.com",
                "model": " nested-model.owner@example.com ",
                "provider": " nested-provider.owner@example.com ",
                "route": " nested-route.owner@example.com ",
            },
            "nested_structures": {
                "messages": [
                    {
                        "role": " nested-role.owner@example.com ",
                        "content": "Nested message nested-message@example.com",
                        "metadata": {
                            "unknown_leaf": "nested-message-metadata@example.com"
                        },
                    }
                ],
                "tool_calls": [
                    {
                        "id": " nested-call.owner@example.com ",
                        "type": "function",
                        "function": {
                            "name": " nested-tool.owner@example.com ",
                            "arguments": {"email": "nested-argument@example.com"},
                        },
                        "metadata": {
                            "unknown_leaf": "nested-tool-metadata@example.com"
                        },
                    }
                ],
            },
        },
        "metadata": {
            "source_system": " source.owner@example.com ",
            "source_version": " source-version.owner@example.com ",
            "intent_label": " metadata.owner@example.com ",
            "unknown_leaf": "metadata-unknown@example.com",
            "nested": {"note": "Metadata metadata@example.com"},
        },
        "feedback": {
            "polarity": "negative",
            "source": "source.owner@example.com",
            "rationale": "Wrong for rationale@example.com",
            "correction": {"text": "Use correction@example.com"},
        },
    }

    feedback = _normalize_feedback(row)
    intent = _normalize_intent({key: value for key, value in row.items() if key != "feedback"})

    for normalized in (feedback, intent):
        assert normalized["schema_version"] == row["schema_version"]
        assert normalized["record_id"] == row["record_id"]
        assert normalized["group_id"] == row["group_id"]
        assert normalized["request_id"] == row["request_id"]
        assert normalized["task_type"] == row["task_type"]
        assert normalized["route"] == row["route"]
        assert normalized["intent_label"] == row["intent_label"]
        assert normalized["conversation_context"][0]["role"] == row[
            "conversation_context"
        ][0]["role"]
        assert normalized["tool_calls"][0]["name"] == row["tool_calls"][0]["name"]
        assert normalized["runtime"]["model"] == row["runtime"]["model"]
        assert normalized["runtime"]["request"]["model"] == " <email> "
        assert normalized["runtime"]["request"]["provider"] == " <email> "
        assert normalized["runtime"]["request"]["route"] == " <email> "
        assert normalized["metadata"]["source_system"] == row["metadata"][
            "source_system"
        ]

        assert normalized["metadata"]["source_version"] == row["metadata"][
            "source_version"
        ]
        assert normalized["metadata"]["intent_label"] == row["metadata"][
            "intent_label"
        ]
        assert normalized["runtime"]["nested_structures"]["messages"][0][
            "role"
        ] == row["runtime"]["nested_structures"]["messages"][0]["role"]
        assert normalized["runtime"]["nested_structures"]["tool_calls"][0][
            "id"
        ] == row["runtime"]["nested_structures"]["tool_calls"][0]["id"]
        assert normalized["runtime"]["nested_structures"]["tool_calls"][0][
            "function"
        ]["name"] == row["runtime"]["nested_structures"]["tool_calls"][0][
            "function"
        ]["name"]
        serialized = json.dumps(normalized, sort_keys=True)
        for secret in (
            "user@example.com",
            "assistant@example.com",
            "context@example.com",
            "argument@example.com",
            "result@example.com",
            "error@example.com",
            "runtime@example.com",
            "nested-model.owner@example.com",
            "nested-provider.owner@example.com",
            "nested-route.owner@example.com",
            "metadata@example.com",
            "runtime-unknown@example.com",
            "metadata-unknown@example.com",
            "nested-message@example.com",
            "nested-message-metadata@example.com",
            "nested-argument@example.com",
            "nested-tool-metadata@example.com",
            "192.0.2.1",
            "192.0.2.2",
            "192.0.2.3",
            "192.0.2.4",
        ):
            assert secret not in serialized
    feedback_serialized = json.dumps(feedback, sort_keys=True)
    assert "rationale@example.com" not in feedback_serialized
    assert "correction@example.com" not in feedback_serialized


def test_normalized_intent_includes_all_prior_user_messages() -> None:
    intent = _normalize_intent(
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": "record-1",
            "group_id": "group-1",
            "task_type": "answer",
            "user_input": "Current request",
            "conversation_context": [
                {"role": "user", "content": "First user request"},
                {"role": "assistant", "content": "Assistant response"},
                {"role": "user", "content": "Second user request"},
            ],
            "tool_calls": [{"name": "lookup", "arguments": {}}],
            "episode": {
                "events": [
                    {
                        "sequence": 0,
                        "type": "message",
                        "role": "user",
                        "content": "First user request",
                    },
                    {
                        "sequence": 1,
                        "type": "message",
                        "role": "assistant",
                        "content": "Assistant response",
                    },
                    {
                        "sequence": 2,
                        "type": "message",
                        "role": "user",
                        "content": "Second user request",
                    },
                    {
                        "sequence": 3,
                        "type": "message",
                        "role": "user",
                        "content": "Current request",
                    },
                    {
                        "sequence": 4,
                        "type": "message",
                        "role": "user",
                        "content": "Confirmed return",
                    },
                    {
                        "sequence": 5,
                        "type": "tool_call",
                        "call_id": "call-1",
                        "name": "submit_return",
                        "arguments": {},
                    },
                ]
            },
            "runtime": {},
            "metadata": {},
        }
    )

    assert intent["canonical_intent_text"] == (
        "First user request\nSecond user request\nCurrent request\n"
        "Confirmed return"
    )
    assert intent["tool_names"] == ["lookup", "submit_return"]
    assert "lookup" not in intent["canonical_intent_text"]
    assert "submit_return" not in intent["canonical_intent_text"]


def test_episode_redaction_preserves_structure_and_redacts_content() -> None:
    """Episode links remain usable without leaking content-bearing PII."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "record-1",
        "group_id": "group-1",
        "task_type": "answer",
        "user_input": "Request from user@example.com",
        "assistant_output": "Completed for user@example.com",
        "conversation_context": [],
        "tool_calls": [
            {
                "call_id": "call-1",
                "name": "lookup_order",
                "arguments": {"owner": "user@example.com"},
                "result": {"owner": "user@example.com"},
            }
        ],
        "episode": {
            "episode_id": "episode-1",
            "termination_reason": "Finished for user@example.com",
            "events": [
                {
                    "sequence": 0,
                    "type": "message",
                    "role": "user",
                    "content": "Request from user@example.com",
                },
                {
                    "sequence": 1,
                    "type": "tool_call",
                    "call_id": "call-1",
                    "name": "lookup_order",
                    "arguments": {"owner": "user@example.com"},
                },
                {
                    "sequence": 2,
                    "type": "tool_result",
                    "call_id": "call-1",
                    "result": {"owner": "user@example.com"},
                },
            ],
        },
        "runtime": {},
        "metadata": {},
        "feedback": {
            "polarity": "positive",
            "rationale": "Correct for user@example.com",
        },
    }

    normalized = _normalize_feedback(row)

    assert normalized["episode"]["episode_id"] == "episode-1"
    assert [event["sequence"] for event in normalized["episode"]["events"]] == [
        0,
        1,
        2,
    ]
    assert normalized["episode"]["events"][1]["call_id"] == "call-1"
    assert normalized["episode"]["events"][1]["name"] == "lookup_order"
    assert "user@example.com" not in json.dumps(normalized, sort_keys=True)

    provider_record = _feedback_provider_record(normalized)
    assert provider_record["conversation_context"] == []
    assert provider_record["tool_calls"] == normalized["tool_calls"]
    assert provider_record["tool_calls"][0]["result"] == {"owner": "<email>"}
    assert provider_record["episode"] == normalized["episode"]
    assert provider_record["trace_analysis"]["tool_observations"] == [
        {
            "pointer": "episode.events[1]",
            "name": "lookup_order",
            "arguments": {"owner": "<email>"},
            "outcome_status": "result_returned",
            "result_state": {},
        }
    ]
    assert "feedback_trace_mistake_pattern" in EVIDENCE_EXTRACTION_PROMPT
    assert "environment failures" in EVIDENCE_EXTRACTION_PROMPT


def test_guideline_synthesis_payload_includes_observed_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guideline creation receives tool arguments and explicit outcome status."""
    row = {
        "record_id": "feedback-1",
        "task_type": "answer",
        "user_input": "Complete the requested action.",
        "tool_calls": [
            {
                "call_id": "call-1",
                "name": "lookup_record",
                "arguments": {"record_id": "record-1"},
                "result": {"status": "ready", "large": "not duplicated"},
                "error": None,
            },
            {
                "call_id": "call-2",
                "name": "apply_change",
                "arguments": {"record_id": "record-1", "value": "new"},
                "error": "permission denied",
            },
            {
                "call_id": "call-3",
                "name": "audit_change",
                "arguments": {},
            },
        ],
        "feedback": {"polarity": "mixed"},
    }

    example = _guideline_provider_example(row)

    assert example == {
        "record_id": "feedback-1",
        "task_type": "answer",
        "user_input": "Complete the requested action.",
        "feedback": {"polarity": "mixed"},
        "trace_analysis": {
            "user_messages": ["Complete the requested action."],
            "assistant_messages": [],
            "tool_observations": [
                {
                    "pointer": "tool_calls[0]",
                    "name": "lookup_record",
                    "arguments": {"record_id": "record-1"},
                    "outcome_status": "result_returned",
                    "result_state": {"status": "ready"},
                },
                {
                    "pointer": "tool_calls[1]",
                    "name": "apply_change",
                    "arguments": {"record_id": "record-1", "value": "new"},
                    "outcome_status": "error_returned",
                    "error": "permission denied",
                },
                {
                    "pointer": "tool_calls[2]",
                    "name": "audit_change",
                    "arguments": {},
                    "outcome_status": "not_recorded",
                },
            ],
        },
        "runtime": {},
        "observed_tool_calls": [
            {
                "position": 1,
                "call_id": "call-1",
                "name": "lookup_record",
                "arguments": {"record_id": "record-1"},
                "outcome_status": "result_returned",
            },
            {
                "position": 2,
                "call_id": "call-2",
                "name": "apply_change",
                "arguments": {"record_id": "record-1", "value": "new"},
                "outcome_status": "error_returned",
                "error": "permission denied",
            },
            {
                "position": 3,
                "call_id": "call-3",
                "name": "audit_change",
                "arguments": {},
                "outcome_status": "not_recorded",
            },
        ],
    }
    assert "not duplicated" not in json.dumps(example, sort_keys=True)
    assert "observed_tool_calls" in GUIDELINE_SYNTHESIS_PROMPT
    assert "feedback_trace_mistake_pattern" in GUIDELINE_SYNTHESIS_PROMPT
    assert "trace_analysis" in GUIDELINE_SYNTHESIS_PROMPT
    assert "result_returned does not establish" in GUIDELINE_SYNTHESIS_PROMPT
    assert "evidence_required must be a" in GUIDELINE_SYNTHESIS_PROMPT
    assert "JSON boolean" in GUIDELINE_SYNTHESIS_PROMPT
    assert "never invent, transform, or copy an ID" in GUIDELINE_SYNTHESIS_PROMPT
    assert "short opaque" in GUIDELINE_SYNTHESIS_PROMPT
    assert "criteria" in GUIDELINE_SYNTHESIS_PROMPT
    assert "inherit the validated parent guideline" in GUIDELINE_SYNTHESIS_PROMPT
    assert "conflicts and uncertainties must be JSON arrays" in (
        GUIDELINE_SYNTHESIS_PROMPT
    )

    captured_payloads = []

    def capture_call(stage, prompt, payload, normalize):
        del stage, prompt, normalize
        captured_payloads.append(payload)
        return [], []

    pipeline = EvaluationAssetPipeline.__new__(EvaluationAssetPipeline)
    pipeline._provider_identities = {
        "rubric": {"provider": "fake", "model": "fake-rubric"}
    }
    monkeypatch.setattr(pipeline, "_call_rubric_provider", capture_call)

    evidence = [{"record_id": "feedback-1", "route": "answer"}]
    assert pipeline._synthesize_guidelines(
        evidence,
        {"feedback-1": row},
    ) == ([], [])
    assert captured_payloads == [
        {
            "route": "answer",
            "evidence": [{"record_id": "source-001", "route": "answer"}],
            "examples": [{**example, "record_id": "source-001"}],
        }
    ]
    assert "feedback-1" not in json.dumps(captured_payloads, sort_keys=True)


def test_feedback_trace_mistake_patterns_require_correlation_and_repair() -> None:
    """Mistake patterns are accepted only with feedback and trace evidence."""
    source = {
        "record_id": "feedback-1",
        "group_id": "group-1",
        "route": "answer",
        "task_type": "answer",
        "feedback": {"polarity": "negative"},
    }
    raw = {
        "intent_label": "complete the request",
        "confidence": 0.9,
        "observations": [
            {
                "claim": "The agent reported success after the tool returned an error.",
                "evidence_type": "feedback_trace_mistake_pattern",
                "evidence_pointer": "feedback.rationale; episode.events[4]",
                "polarity": "negative",
            }
        ],
        "requested_corrections": [
            "Acknowledge the failed tool outcome and do not claim completion."
        ],
        "uncertainties": [],
    }

    normalized = _normalize_feedback_evidence(raw, source, "fake", "fake-model")

    assert normalized["observations"][0]["evidence_type"] == (
        "feedback_trace_mistake_pattern"
    )
    assert normalized["requested_corrections"] == raw["requested_corrections"]

    missing_trace_pointer = {
        **raw,
        "observations": [
            {
                **raw["observations"][0],
                "evidence_pointer": "feedback.rationale",
            }
        ],
    }
    with pytest.raises(ValueError, match="both feedback and an observed trace"):
        _normalize_feedback_evidence(
            missing_trace_pointer,
            source,
            "fake",
            "fake-model",
        )

    with pytest.raises(ValueError, match="expected behavior or repair"):
        _normalize_feedback_evidence(
            {**raw, "requested_corrections": []},
            source,
            "fake",
            "fake-model",
        )

    with pytest.raises(ValueError, match="must agree with feedback"):
        _normalize_feedback_evidence(
            raw,
            {**source, "feedback": {"polarity": "positive"}},
            "fake",
            "fake-model",
        )


def test_feedback_trace_success_pattern_does_not_require_a_repair() -> None:
    """A positively endorsed behavior is itself the expected behavior."""
    source = {
        "record_id": "feedback-1",
        "group_id": "group-1",
        "route": "answer",
        "task_type": "answer",
        "feedback": {"polarity": "positive"},
    }
    raw = {
        "intent_label": "complete the request",
        "confidence": 0.9,
        "observations": [
            {
                "claim": "The agent confirmed the requested option before acting.",
                "evidence_type": "feedback_trace_success_pattern",
                "evidence_pointer": "feedback.rationale; episode.events[4]",
                "polarity": "positive",
            }
        ],
        "requested_corrections": [],
        "uncertainties": [],
    }

    normalized = _normalize_feedback_evidence(raw, source, "fake", "fake-model")

    assert normalized["observations"][0]["evidence_type"] == (
        "feedback_trace_success_pattern"
    )
    assert normalized["requested_corrections"] == []


def test_guideline_synthesis_restores_opaque_source_aliases() -> None:
    """Provider aliases map back exactly; unknown aliases remain invalid."""
    evidence = [
        {
            "record_id": "feedback-long-source-id",
            "route": "answer",
            "group_id": "group-1",
            "requested_corrections": [],
            "uncertainties": [],
        }
    ]
    response = {
        "guidelines": [
            {
                "intent_label": "complete the task",
                "description": "Complete the requested task.",
                "source_record_ids": ["source-001"],
                "confidence": 0.9,
                "criteria": [
                    {
                        "kind": "required",
                        "statement": "Complete the requested task.",
                        "source_record_ids": ["source-999"],
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
        ]
    }

    candidates, guidelines = _normalize_aliased_guideline_response(
        response,
        source_id_by_alias={"source-001": "feedback-long-source-id"},
        route="answer",
        evidence=evidence,
        rubric_provider="fake",
        rubric_model="fake-rubric",
        identity_profile="current_v2",
    )

    assert candidates[0]["source_record_ids"] == ["feedback-long-source-id"]
    assert candidates[0]["criteria"][0]["source_record_ids"] == [
        "feedback-long-source-id"
    ]
    assert guidelines[0]["source_record_ids"] == ["feedback-long-source-id"]

    response["guidelines"][0]["source_record_ids"] = ["source-999"]
    with pytest.raises(ValueError, match="incompatible evidence"):
        _normalize_aliased_guideline_response(
            response,
            source_id_by_alias={"source-001": "feedback-long-source-id"},
            route="answer",
            evidence=evidence,
            rubric_provider="fake",
            rubric_model="fake-rubric",
            identity_profile="current_v2",
        )


def test_normalization_defaults_preserve_exact_canonical_source_strings() -> None:
    """Omitted request and route fields inherit source strings without trimming."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": " exact-record-id ",
        "group_id": " exact-group-id ",
        "task_type": " exact-task-type ",
        "intent_label": " exact-intent-label ",
        "user_input": "Request",
        "assistant_output": "Response",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
        "feedback": {"polarity": "positive", "rationale": "Correct"},
    }

    feedback = _normalize_feedback(row)
    intent = _normalize_intent({key: value for key, value in row.items() if key != "feedback"})

    for normalized in (feedback, intent):
        assert normalized["request_id"] == " exact-record-id "
        assert normalized["route"] == " exact-task-type "


def test_normalization_recurses_through_composite_structural_fields() -> None:
    """Structural keys preserve scalars, never whole content-bearing subtrees."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "record-1",
        "group_id": "group-1",
        "task_type": "answer",
        "user_input": "Request",
        "assistant_output": "Response",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {
            "application": {
                "application_version": " app-version.owner@example.com ",
                "note": "application-secret@example.com",
                "messages": [
                    {
                        "role": " nested-runtime-role.owner@example.com ",
                        "content": "runtime-message-secret@example.com",
                        "source": {
                            "source_system": " message-source.owner@example.com ",
                            "note": "message-source-secret@example.com",
                        },
                    }
                ],
            },
            "deployment": [
                {
                    "deployment_id": " deployment.owner@example.com ",
                    "content": "deployment-secret@example.com",
                }
            ],
            "provider": {
                "provider_name": " provider.owner@example.com ",
                "metadata": {"unknown_leaf": "provider-secret@example.com"},
            },
            "tools_available": [
                {
                    "name": " lookup.owner@example.com ",
                    "description": "tool-description-secret@example.com",
                    "provider": {
                        "provider_name": " tool-provider.owner@example.com ",
                        "note": "tool-provider-secret@example.com",
                    },
                    "arguments": {"target": "tool-argument-secret@example.com"},
                    "result": {"owner": "tool-result-secret@example.com"},
                },
                {
                    "type": "function",
                    "function": {
                        "name": " nested-tool.owner@example.com ",
                        "description": "nested-tool-secret@example.com",
                        "arguments": {
                            "target": "nested-tool-argument-secret@example.com"
                        },
                    },
                },
            ],
        },
        "metadata": {
            "source": {
                "source_system": " source-system.owner@example.com ",
                "note": "source-secret@example.com",
                "history": [
                    {
                        "source_version": " source-version.owner@example.com ",
                        "content": "source-history-secret@example.com",
                    }
                ],
            }
        },
        "feedback": {"polarity": "positive", "rationale": "Correct"},
    }

    feedback = _normalize_feedback(row)
    intent = _normalize_intent({key: value for key, value in row.items() if key != "feedback"})

    for normalized in (feedback, intent):
        assert normalized["runtime"]["application"]["application_version"] == (
            " app-version.owner@example.com "
        )
        runtime_message = normalized["runtime"]["application"]["messages"][0]
        assert runtime_message["role"] == " nested-runtime-role.owner@example.com "
        assert runtime_message["source"]["source_system"] == (
            " message-source.owner@example.com "
        )
        assert normalized["runtime"]["deployment"][0]["deployment_id"] == (
            " deployment.owner@example.com "
        )
        assert normalized["runtime"]["provider"]["provider_name"] == (
            " provider.owner@example.com "
        )
        assert normalized["metadata"]["source"]["source_system"] == (
            " source-system.owner@example.com "
        )
        assert normalized["metadata"]["source"]["history"][0][
            "source_version"
        ] == " source-version.owner@example.com "
        tools = normalized["runtime"]["tools_available"]
        assert tools[0]["name"] == " lookup.owner@example.com "
        assert tools[0]["provider"]["provider_name"] == (
            " tool-provider.owner@example.com "
        )
        assert tools[1]["function"]["name"] == " nested-tool.owner@example.com "
        serialized = json.dumps(normalized, sort_keys=True)
        for secret in (
            "application-secret@example.com",
            "runtime-message-secret@example.com",
            "message-source-secret@example.com",
            "deployment-secret@example.com",
            "provider-secret@example.com",
            "source-secret@example.com",
            "source-history-secret@example.com",
            "tool-description-secret@example.com",
            "tool-provider-secret@example.com",
            "tool-argument-secret@example.com",
            "tool-result-secret@example.com",
            "nested-tool-secret@example.com",
            "nested-tool-argument-secret@example.com",
        ):
            assert secret not in serialized


def test_normalization_traverses_nested_tool_name_collections() -> None:
    """Tool collections keep names exact while redacting descriptive content."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "record-1",
        "group_id": "group-1",
        "task_type": "answer",
        "user_input": "Request",
        "assistant_output": "Response",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {
            "tools_available": [
                " scalar-tool.owner@example.com ",
                {
                    "name": " object-tool.owner@example.com ",
                    "description": "object-description-secret@example.com",
                },
                {
                    "type": "function",
                    "function": {
                        "name": " function-tool.owner@example.com ",
                        "arguments": {"email": "function-secret@example.com"},
                    },
                },
            ]
        },
        "metadata": {},
        "feedback": {"polarity": "positive", "rationale": "Correct"},
    }

    normalized = _normalize_feedback(row)

    tools = normalized["runtime"]["tools_available"]
    assert tools[0] == " scalar-tool.owner@example.com "
    assert tools[1]["name"] == " object-tool.owner@example.com "
    assert tools[2]["function"]["name"] == " function-tool.owner@example.com "
    serialized = json.dumps(normalized, sort_keys=True)
    assert "object-description-secret@example.com" not in serialized
    assert "function-secret@example.com" not in serialized


def test_normalization_preserves_name_only_in_structural_descriptor_context() -> None:
    """Descriptor-local names stay exact without globally exempting `name`."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "record-1",
        "group_id": "group-1",
        "task_type": "answer",
        "user_input": "Request",
        "assistant_output": "Response",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {
            "application": {
                "name": " application.owner@example.com ",
                "application_version": " application-version.owner@example.com ",
                "description": "application-description-secret@example.com",
                "details": {
                    "name": "arbitrary-nested-name@example.com",
                    "note": "application-details-secret@example.com",
                },
            },
            "deployment": [
                {
                    "name": " deployment.owner@example.com ",
                    "deployment_id": " deployment-id.owner@example.com ",
                    "payload": "deployment-payload-secret@example.com",
                }
            ],
            "provider": {
                "name": " provider.owner@example.com ",
                "provider_name": " provider-name.owner@example.com ",
                "note": "provider-note-secret@example.com",
            },
            "model": {
                "name": " model.owner@example.com ",
                "model_name": " model-name.owner@example.com ",
                "unknown_leaf": "model-secret@example.com",
            },
            "environment": {
                "name": " environment.owner@example.com ",
                "version": " environment-version.owner@example.com ",
                "note": "environment-secret@example.com",
            },
            "custom": {
                "name": "arbitrary-person@example.com",
                "note": "arbitrary-note@example.com",
            },
        },
        "metadata": {
            "source": {
                "name": " source.owner@example.com ",
                "source_system": " source-system.owner@example.com ",
                "description": "source-description-secret@example.com",
            }
        },
        "feedback": {"polarity": "positive", "rationale": "Correct"},
    }

    normalized = _normalize_feedback(row)

    assert normalized["runtime"]["application"]["name"] == (
        " application.owner@example.com "
    )
    assert normalized["runtime"]["deployment"][0]["name"] == (
        " deployment.owner@example.com "
    )
    assert normalized["runtime"]["provider"]["name"] == (
        " provider.owner@example.com "
    )
    assert normalized["runtime"]["model"]["name"] == " model.owner@example.com "
    assert normalized["runtime"]["environment"]["name"] == (
        " environment.owner@example.com "
    )
    assert normalized["metadata"]["source"]["name"] == " source.owner@example.com "
    assert normalized["runtime"]["application"]["application_version"] == (
        " application-version.owner@example.com "
    )
    assert normalized["runtime"]["deployment"][0]["deployment_id"] == (
        " deployment-id.owner@example.com "
    )
    assert normalized["runtime"]["provider"]["provider_name"] == (
        " provider-name.owner@example.com "
    )
    assert normalized["runtime"]["model"]["model_name"] == (
        " model-name.owner@example.com "
    )
    assert normalized["runtime"]["environment"]["version"] == (
        " environment-version.owner@example.com "
    )
    assert normalized["metadata"]["source"]["source_system"] == (
        " source-system.owner@example.com "
    )
    serialized = json.dumps(normalized, sort_keys=True)
    for secret in (
        "application-description-secret@example.com",
        "arbitrary-nested-name@example.com",
        "application-details-secret@example.com",
        "deployment-payload-secret@example.com",
        "provider-note-secret@example.com",
        "model-secret@example.com",
        "environment-secret@example.com",
        "source-description-secret@example.com",
        "arbitrary-person@example.com",
        "arbitrary-note@example.com",
    ):
        assert secret not in serialized


def test_normalization_routes_singular_tool_descriptor_by_context() -> None:
    """A singular tool descriptor preserves only its structural name fields."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "record-1",
        "group_id": "group-1",
        "task_type": "answer",
        "user_input": "Request",
        "assistant_output": "Response",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {
            "tool": {
                "name": " singular-tool.owner@example.com ",
                "tool_name": " tool-alias.owner@example.com ",
                "description": "tool-description-secret@example.com",
                "arguments": {"email": "tool-argument-secret@example.com"},
                "result": {"owner": "tool-result-secret@example.com"},
                "content": "tool-content-secret@example.com",
            }
        },
        "metadata": {},
        "feedback": {"polarity": "positive", "rationale": "Correct"},
    }

    normalized = _normalize_feedback(row)

    tool = normalized["runtime"]["tool"]
    assert tool["name"] == " singular-tool.owner@example.com "
    assert tool["tool_name"] == " tool-alias.owner@example.com "
    serialized = json.dumps(normalized, sort_keys=True)
    for secret in (
        "tool-description-secret@example.com",
        "tool-argument-secret@example.com",
        "tool-result-secret@example.com",
        "tool-content-secret@example.com",
    ):
        assert secret not in serialized


@pytest.mark.parametrize(
    ("field", "content"),
    [
        (
            "payload",
            {
                "id": "payload-id-secret@example.com",
                "source": "payload-source-secret@example.com",
                "nested": [{"role": "payload-role-secret@example.com"}],
            },
        ),
        (
            "content",
            [
                {
                    "record_id": "content-record-secret@example.com",
                    "tool_name": "content-tool-secret@example.com",
                }
            ],
        ),
        (
            "note",
            {
                "group_id": "note-group-secret@example.com",
                "source_system": "note-source-secret@example.com",
            },
        ),
        (
            "arguments",
            [
                {
                    "request_id": "arguments-request-secret@example.com",
                    "name": "arguments-name-secret@example.com",
                }
            ],
        ),
        (
            "results",
            {
                "id": "results-id-secret@example.com",
                "provider": "results-provider-secret@example.com",
            },
        ),
    ],
)
def test_normalization_redacts_every_descendant_of_explicit_content_fields(
    field: str,
    content: object,
) -> None:
    """Structural-looking descendants cannot escape explicit content context."""
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": " canonical-record.owner@example.com ",
        "group_id": " canonical-group.owner@example.com ",
        "task_type": " canonical-task.owner@example.com ",
        "route": " canonical-route.owner@example.com ",
        "user_input": "Request",
        "assistant_output": "Response",
        "conversation_context": [
            {
                "role": " canonical-role.owner@example.com ",
                "content": "Earlier request",
            }
        ],
        "tool_calls": [
            {
                "name": " canonical-tool.owner@example.com ",
                "arguments": {},
            }
        ],
        "runtime": {"wrapper": {field: content}},
        "metadata": {},
        "feedback": {"polarity": "positive", "rationale": "Correct"},
    }

    normalized = _normalize_feedback(row)

    assert normalized["record_id"] == row["record_id"]
    assert normalized["group_id"] == row["group_id"]
    assert normalized["task_type"] == row["task_type"]
    assert normalized["route"] == row["route"]
    assert normalized["conversation_context"][0]["role"] == row[
        "conversation_context"
    ][0]["role"]
    assert normalized["tool_calls"][0]["name"] == row["tool_calls"][0]["name"]
    serialized_content = json.dumps(normalized["runtime"]["wrapper"][field])
    for secret in (
        value
        for value in json.dumps(content).replace('"', " ").split()
        if "@example.com" in value
    ):
        assert secret.rstrip(",}] ") not in serialized_content
    assert "<email>" in serialized_content


def test_prepare_inputs_rejects_normalized_duplicate_with_both_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A faulty normalizer collision reports both originating rows and IDs."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    _write_extension_feedback(feedback, [" source-one ", " source-two "])
    feedback_lines = feedback.read_text(encoding="utf-8").splitlines()
    feedback.write_text(
        f"{feedback_lines[0]}\n\n{feedback_lines[1]}\n",
        encoding="utf-8",
    )
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    original = pipeline_module._normalize_feedback

    def collide(row):
        normalized = original(row)
        normalized["record_id"] = " canonical-collision "
        return normalized

    monkeypatch.setattr(pipeline_module, "_normalize_feedback", collide)

    with pytest.raises(
        ValueError,
        match=(
            r"normalized feedback.*' canonical-collision '.*"
            r"row 1.*' source-one '.*row 3.*' source-two '"
        ),
    ):
        pipeline._prepare_inputs()


@pytest.mark.parametrize(
    ("routes", "cluster_count", "message"),
    [
        (["route_a"], 2, "cannot exceed the number of unlabeled records"),
        (
            ["route_a", "route_b"],
            1,
            "must be at least the number of distinct effective routes",
        ),
    ],
)
def test_stage_one_rejects_infeasible_clustering_before_provider_calls(
    tmp_path: Path,
    routes: list[str],
    cluster_count: int,
    message: str,
) -> None:
    """Data-dependent clustering failures stop before paid provider work."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    _write_unlabeled_routes(unlabeled, routes)
    rubric_provider = FakeRubricProvider()
    embedding_provider = FakeEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=cluster_count,
        ),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )

    with pytest.raises(ValueError, match=message):
        pipeline.run()

    state = pipeline.layout.load_state()
    assert state.current_stage == PipelineStage.RAW_INPUTS.value
    assert rubric_provider.calls == 0
    assert embedding_provider.calls == 0


def test_stage_one_accepts_one_cluster_per_record_and_effective_route(
    tmp_path: Path,
) -> None:
    """The exact feasibility boundary remains accepted in Stage 1."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    _write_unlabeled_routes(unlabeled, ["route_a", "route_b"])
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=2),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )

    assert pipeline._validate_raw_inputs() == {
        "feedback_records": 1,
        "unlabeled_records": 2,
    }


def test_stage_one_treats_present_whitespace_routes_as_exact_bytes(
    tmp_path: Path,
) -> None:
    """Distinct present route bytes fail feasibility before provider work."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    _write_extension_unlabeled(unlabeled, ["u1", "u2"])
    rows = _read_test_jsonl(unlabeled)
    rows[0]["task_type"] = "shared-task"
    rows[0]["route"] = "route"
    rows[1]["task_type"] = "shared-task"
    rows[1]["route"] = " route "
    unlabeled.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    rubric_provider = FakeRubricProvider()
    embedding_provider = FakeEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )

    with pytest.raises(
        ValueError,
        match=r"number of distinct effective routes \(2\)",
    ):
        pipeline.run()

    state = pipeline.layout.load_state()
    assert state.current_stage == PipelineStage.RAW_INPUTS.value
    assert rubric_provider.calls == 0
    assert embedding_provider.calls == 0


@pytest.mark.parametrize(
    ("copied_input", "expected_detail"),
    [
        ("feedback", "missing required field 'group_id'"),
        ("unlabeled", "'conversation_context[0].content' is required"),
    ],
)
def test_stage_one_revalidates_each_copied_input_before_provider_calls(
    tmp_path: Path,
    copied_input: str,
    expected_detail: str,
) -> None:
    """A copied v1 contract violation fails Stage 1 with its exact location."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    rubric_provider = FakeRubricProvider()
    embedding_provider = FakeEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )
    copied_path = (
        pipeline.layout.feedback_path
        if copied_input == "feedback"
        else pipeline.layout.unlabeled_path
    )
    row = _read_test_jsonl(copied_path)[0]
    if copied_input == "feedback":
        del row["group_id"]
    else:
        row["conversation_context"] = [{"role": "user"}]
    copied_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    expected_error = f"{copied_path}:1: {expected_detail}"

    with pytest.raises(ValueError) as caught:
        pipeline.run()

    assert str(caught.value) == expected_error
    state = pipeline.layout.load_state()
    raw_stage = next(
        stage for stage in state.stages if stage.stage == PipelineStage.RAW_INPUTS.value
    )
    assert state.status == "failed"
    assert state.current_stage == PipelineStage.RAW_INPUTS.value
    assert state.error == expected_error
    assert raw_stage.status == "failed"
    assert raw_stage.message == expected_error
    assert rubric_provider.calls == 0
    assert embedding_provider.calls == 0


@pytest.mark.parametrize(
    ("malformed_call", "expected_stage"),
    [
        (1, PipelineStage.INTENT_CLUSTERING),
    ],
)
def test_pipeline_validates_injected_embedding_batches_at_every_stage(
    tmp_path: Path,
    malformed_call: int,
    expected_stage: PipelineStage,
) -> None:
    """Custom providers cannot bypass clustering vector validation."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    embedding_provider = MalformedEmbeddingProvider(malformed_call)
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=embedding_provider,
    )

    with pytest.raises(ValueError, match="embedding provider.*nonzero"):
        pipeline.run()

    state = pipeline.layout.load_state()
    assert state.current_stage == expected_stage.value
    assert embedding_provider.calls == malformed_call


@pytest.mark.parametrize(
    ("failure_kind", "expected_stage"),
    [
        ("rubric", PipelineStage.RUBRIC_EXTRACTION),
        ("embedding", PipelineStage.INTENT_CLUSTERING),
    ],
)
def test_provider_failure_persists_only_sanitized_causal_summary(
    tmp_path: Path,
    failure_kind: str,
    expected_stage: PipelineStage,
) -> None:
    """Provider payloads stay in the chained cause and out of artifacts."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    rubric_provider = (
        SecretFailingRubricProvider()
        if failure_kind == "rubric"
        else FakeRubricProvider()
    )
    embedding_provider = (
        SecretFailingEmbeddingProvider()
        if failure_kind == "embedding"
        else FakeEmbeddingProvider()
    )
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            rubric_model="safe-rubric-model",
            embedding_model="safe-embedding-model",
        ),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )

    with pytest.raises(Exception) as caught:
        pipeline.run()

    assert caught.value.__class__.__name__ == "ProviderCallError"
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert "sk-live-secret-token" in str(caught.value.__cause__)
    persisted = (
        pipeline.layout.state_path.read_text(encoding="utf-8")
        + pipeline.layout.events_path.read_text(encoding="utf-8")
    )
    assert expected_stage.value in persisted
    assert "provider=fake" in persisted
    assert "model=fake-" in persisted
    assert "cause=RuntimeError" in persisted
    assert "summary=provider operation failed" in persisted
    assert "sk-live-secret-token" not in persisted
    assert "raw_response" not in persisted
    assert "private@example.com" not in persisted


def test_rubric_provider_regenerates_once_after_schema_validation_error() -> None:
    """One malformed JSON shape gets one fresh, provenance-recorded attempt."""

    class RepairingProvider:
        provider_name = "fake"
        model = "fake-rubric"

        def __init__(self):
            self.calls = 0
            self.prompts = []

        def generate_json(self, system_prompt, payload):
            del payload
            self.calls += 1
            self.prompts.append(system_prompt)
            return {"valid": self.calls == 2}

    provider = RepairingProvider()
    pipeline = EvaluationAssetPipeline.__new__(EvaluationAssetPipeline)
    pipeline.rubric_provider = provider
    pipeline._provider_identities = {
        "rubric": {"provider": provider.provider_name, "model": provider.model}
    }
    pipeline._provider_settings = {
        "rubric": {"settings": {"response_format": "json_object"}}
    }
    pipeline._stage_call_rows = []

    def normalize(response):
        if response.get("valid") is not True:
            raise ValueError("invalid test response")
        return "normalized"

    assert pipeline._call_rubric_provider(
        PipelineStage.RUBRIC_EXTRACTION,
        "Return valid JSON.",
        {"records": []},
        normalize,
    ) == "normalized"
    assert provider.calls == 2
    assert provider.prompts[0] == "Return valid JSON."
    assert "previous response failed strict schema validation" in provider.prompts[1]
    assert [row["ordinal"] for row in pipeline._stage_call_rows] == [1, 2]


@pytest.mark.parametrize(
    ("malformed_response", "expected_stage"),
    [
        ("evidence", PipelineStage.RUBRIC_EXTRACTION),
        ("guideline", PipelineStage.RUBRIC_EXTRACTION),
        ("inferred", PipelineStage.LABEL_INFERENCE),
        ("synthetic", PipelineStage.SYNTHETIC_COVERAGE),
    ],
)
def test_malformed_rubric_responses_never_persist_provider_content(
    tmp_path: Path,
    malformed_response: str,
    expected_stage: PipelineStage,
) -> None:
    """Semantic response failures cross the same sanitized provider boundary."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            rubric_model="safe-rubric-model",
            synthetic_coverage_enabled=malformed_response == "synthetic",
            split_seed=0,
        ),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=SecretMalformedRubricProvider(malformed_response),
        embedding_provider=FakeEmbeddingProvider(),
    )

    with pytest.raises(Exception) as caught:
        pipeline.run()

    assert caught.value.__class__.__name__ == "ProviderCallError"
    assert isinstance(caught.value.__cause__, ValueError)
    persisted = b"\n".join(
        path.read_bytes()
        for path in pipeline.layout.root.rglob("*")
        if path.is_file()
    )
    assert expected_stage.value.encode() in persisted
    assert b"cause=ValueError" in persisted
    assert b"summary=provider returned an invalid response" in persisted
    assert b"sk-live-secret-token" not in persisted


def test_provider_failure_never_persists_dynamic_exception_class_name(
    tmp_path: Path,
) -> None:
    """Only fixed exception categories cross the persistence boundary."""
    secret_class_name = "SecretCredentialClass_A1B2C3"
    secret_exception = type(secret_class_name, (Exception,), {})

    class DynamicFailureProvider(FakeRubricProvider):
        def generate_json(self, system_prompt, payload):
            raise secret_exception("raw-secret-value")

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=DynamicFailureProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )

    with pytest.raises(Exception) as caught:
        pipeline.run()

    assert caught.value.__cause__.__class__.__name__ == secret_class_name
    assert "raw-secret-value" in str(caught.value.__cause__)
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in pipeline.layout.root.rglob("*")
        if path.is_file()
    )
    assert "cause=ProviderError" in persisted
    assert secret_class_name not in persisted
    assert "raw-secret-value" not in persisted


def test_rubric_normalization_accepts_list_form_tool_expectations() -> None:
    expectation = "Use the required search tool before answering." + ("x" * 80)

    rubric = _normalize_rubric(
        {
            "intent_label": "answer the request",
            "confidence": 0.9,
            "must": ["Answer the request."],
            "must_not": [],
            "should": [],
            "deterministic_checks": [],
            "tool_expectations": [expectation],
            "reference_output": None,
        },
        "record_id",
        "feedback-1",
        "human_feedback",
        "fake",
        "gpt-5.5",
    )

    assert rubric["tool_expectations"] == {"requirements": [expectation]}
    assert "tool_expectations" in GUIDELINE_SYNTHESIS_PROMPT


def test_guideline_compilation_preserves_provenance_and_evaluator_plan() -> None:
    evidence = [
        {
            "record_id": "feedback-1",
            "group_id": "group-1",
            "route": "task_route",
            "requested_corrections": [],
            "uncertainties": ["The required ordering is not established."],
        }
    ]
    candidates = [
        {
            "route": "task_route",
            "intent_label": "complete the task",
            "description": "Complete the requested task safely.",
            "source_record_ids": ["feedback-1"],
            "confidence": 0.9,
            "criteria": [
                {
                    "kind": "required",
                    "statement": "The requested state change is present.",
                    "source_record_ids": ["feedback-1"],
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
    ]

    guidelines = _compile_evaluation_guidelines(
        candidates,
        evidence,
        "fake",
        "gpt-5.5",
    )
    rubric = _rubric_from_guidelines(
        "feedback-1",
        guidelines,
        "fake",
        "gpt-5.5",
    )

    assert guidelines[0]["criteria"][0]["source_record_ids"] == ["feedback-1"]
    assert guidelines[0]["criteria"][0]["evaluator"]["type"] == "state_check"
    assert guidelines[0]["uncertainties"] == [
        "The required ordering is not established."
    ]
    assert rubric["deterministic_checks"][0]["criterion_id"].startswith(
        "criterion-"
    )


def test_evaluation_asset_optional_settings_have_safe_defaults() -> None:
    config = EvaluationAssetConfig(tenant_id="new_tenant")

    assert config.match_threshold == 0.6
    assert config.synthetic_coverage_enabled is False
    assert config.synthetic_cases_per_cluster == 1

    loaded = EvaluationAssetConfig.from_dict({"tenant_id": "new_tenant"})
    assert loaded.match_threshold == 0.6
    assert loaded.synthetic_coverage_enabled is False
    assert loaded.synthetic_cases_per_cluster == 1


def test_config_round_trip_distinguishes_missing_ratio_from_explicit_null() -> None:
    """A missing coverage ratio defaults while explicit null stays disabled."""
    missing = EvaluationAssetConfig.from_dict({"tenant_id": "new_tenant"})
    disabled = EvaluationAssetConfig.from_dict(
        {
            "tenant_id": "new_tenant",
            "max_unlabeled_to_trusted_ratio": None,
        }
    )

    assert missing.max_unlabeled_to_trusted_ratio == 20.0
    assert EvaluationAssetConfig.from_dict(
        missing.to_dict()
    ).max_unlabeled_to_trusted_ratio == 20.0
    assert disabled.max_unlabeled_to_trusted_ratio is None
    assert EvaluationAssetConfig.from_dict(
        disabled.to_dict()
    ).max_unlabeled_to_trusted_ratio is None


def test_layout_accepts_only_selected_tenant_source_jsonl(tmp_path: Path) -> None:
    """Create accepts ordinary selected-tenant source and dataset JSONL files."""
    tenants_root = tmp_path / "tenants"
    feedback = (
        tenants_root / "tenant_a" / "source_artifacts" / "feedback.jsonl"
    )
    unlabeled = tenants_root / "tenant_a" / "datasets" / "unlabeled.jsonl"
    feedback.parent.mkdir(parents=True)
    unlabeled.parent.mkdir(parents=True)
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )

    assert layout.feedback_path.read_bytes() == feedback.read_bytes()
    assert layout.unlabeled_path.read_bytes() == unlabeled.read_bytes()


@pytest.mark.parametrize(
    "source_kind",
    [
        "workspace_external",
        "other_tenant",
        "generated_dataset",
        "directory",
        "wrong_suffix",
        "symlink_escape",
    ],
)
def test_layout_rejects_unauthorized_sources_before_initializing(
    tmp_path: Path,
    source_kind: str,
) -> None:
    """Create rejects every source outside the selected tenant input boundary."""
    tenants_root = tmp_path / "workspace" / "tenants"
    selected_sources = tenants_root / "tenant_a" / "source_artifacts"
    selected_sources.mkdir(parents=True)
    unlabeled = selected_sources / "unlabeled.jsonl"
    _write_extension_unlabeled(unlabeled, ["u1"])
    outside = tmp_path / "outside.jsonl"
    _write_extension_feedback(outside, ["f1"])

    if source_kind == "workspace_external":
        feedback = outside
    elif source_kind == "other_tenant":
        feedback = (
            tenants_root / "tenant_b" / "source_artifacts" / "feedback.jsonl"
        )
        feedback.parent.mkdir(parents=True)
        _write_extension_feedback(feedback, ["f1"])
    elif source_kind == "generated_dataset":
        feedback = (
            tenants_root
            / "tenant_a"
            / "datasets"
            / "evaluation_assets"
            / "v0"
            / "train.jsonl"
        )
        feedback.parent.mkdir(parents=True)
        _write_extension_feedback(feedback, ["f1"])
    elif source_kind == "directory":
        feedback = selected_sources / "directory.jsonl"
        feedback.mkdir()
    elif source_kind == "wrong_suffix":
        feedback = selected_sources / "feedback.json"
        _write_extension_feedback(feedback, ["f1"])
    else:
        feedback = selected_sources / "feedback.jsonl"
        feedback.symlink_to(outside)

    layout = EvaluationAssetLayout(tenants_root, "tenant_a", source_kind)

    with pytest.raises((OSError, ValueError)):
        layout.initialize(
            EvaluationAssetConfig(
                tenant_id="tenant_a",
                asset_id=source_kind,
            ),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_initialize_reports_source_file_and_row_before_creating_asset(
    tmp_path: Path,
) -> None:
    """Contract failures identify the original source row without side effects."""
    tenants_root = tmp_path / "tenants"
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    feedback.write_text('{"record_id":"f1"}\n', encoding="utf-8")
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    with pytest.raises(
        ValueError,
        match=r"feedback\.jsonl:1: missing required field 'schema_version'",
    ):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_initialize_contract_error_uses_physical_row_after_leading_blanks(
    tmp_path: Path,
) -> None:
    """Initialization diagnostics count skipped blank lines physically."""
    tenants_root = tmp_path / "tenants"
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    feedback.write_text('\n\n{"record_id":"f1"}\n', encoding="utf-8")
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    with pytest.raises(
        ValueError,
        match=r"feedback\.jsonl:3: missing required field 'schema_version'",
    ):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_stage_one_contract_error_uses_copied_input_physical_row(
    tmp_path: Path,
) -> None:
    """Stage-one diagnostics retain interior blank lines in copied inputs."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    rubric_provider = FakeRubricProvider()
    embedding_provider = FakeEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
    )
    valid_row = pipeline.layout.feedback_path.read_text(
        encoding="utf-8"
    ).splitlines()[0]
    pipeline.layout.feedback_path.write_text(
        f'{valid_row}\n\n{{"record_id":"f2"}}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"labeled_feedback\.jsonl:3: missing required field 'schema_version'",
    ):
        pipeline.run()

    assert rubric_provider.calls == 0
    assert embedding_provider.calls == 0


def test_layout_rejects_symlinked_tenant_source_root_escape(
    tmp_path: Path,
) -> None:
    """A source_artifacts directory symlink cannot authorize external files."""
    tenants_root = tmp_path / "workspace" / "tenants"
    tenant_root = tenants_root / "tenant_a"
    external = tmp_path / "external"
    tenant_root.mkdir(parents=True)
    external.mkdir()
    (tenant_root / "source_artifacts").symlink_to(external, target_is_directory=True)
    feedback = external / "feedback.jsonl"
    unlabeled = external / "unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    with pytest.raises(ValueError, match="selected tenant"):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_initialize_reports_source_file_and_row_for_malformed_json(
    tmp_path: Path,
) -> None:
    """Malformed source JSON identifies its original file and physical row."""
    tenants_root = tmp_path / "tenants"
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    feedback.write_text('{"record_id":\n', encoding="utf-8")
    _write_extension_unlabeled(unlabeled, ["u1"])
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")

    with pytest.raises(ValueError, match=r"feedback\.jsonl:1: invalid JSON"):
        layout.initialize(
            EvaluationAssetConfig(tenant_id="tenant_a"),
            feedback,
            unlabeled,
        )

    assert not layout.root.exists()


def test_extension_rejects_unauthorized_addition_before_initializing_child(
    tmp_path: Path,
) -> None:
    """Extension applies the same tenant source boundary before child writes."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    parent = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    parent.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    other_feedback = (
        tenants_root / "tenant_b" / "source_artifacts" / "feedback.jsonl"
    )
    other_feedback.parent.mkdir(parents=True)
    _write_extension_feedback(other_feedback, ["f2"])
    child = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")

    with pytest.raises(ValueError):
        child.initialize_extension(
            parent,
            additional_feedback=other_feedback,
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()


def test_service_create_and_extend_share_tenant_source_boundary(
    tmp_path: Path,
) -> None:
    """The service delegates create and extend authorization to core layout."""
    workspace = tmp_path / "workspace"
    tenants_root = workspace / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    other_source = (
        tenants_root / "tenant_b" / "source_artifacts" / "other.jsonl"
    )
    other_source.parent.mkdir(parents=True)
    other_source.write_text('{"record_id":"other"}\n', encoding="utf-8")
    manager = EvaluationAssetRunManager(
        tenants_root,
        repository_base=workspace,
    )

    with pytest.raises(ValueError, match="selected tenant"):
        manager.start(
            EvaluationAssetConfig(
                tenant_id="tenant_a",
                asset_id="service-create",
                embedding_provider="tfidf",
                embedding_model="tfidf",
            ),
            other_source,
            unlabeled,
        )
    assert not (
        tenants_root / "tenant_a" / "evaluation_assets" / "service-create"
    ).exists()

    parent = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    parent.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    with pytest.raises(ValueError, match="selected tenant"):
        manager.extend(
            "tenant_a",
            "v1",
            "service-extend",
            additional_feedback=other_source,
            additional_unlabeled=None,
            clustering_mode="keep",
        )
    assert not (
        tenants_root / "tenant_a" / "evaluation_assets" / "service-extend"
    ).exists()


def test_layout_resolves_existing_legacy_artifact_paths(tmp_path: Path) -> None:
    layout = EvaluationAssetLayout(tmp_path / "tenants", "legacy_tenant", "v1")
    for name in (
        "raw_inputs",
        "prepared_inputs",
        "decision_assets",
        "review_queues",
        "dataset_splits",
    ):
        (layout.root / name).mkdir(parents=True, exist_ok=True)

    assert layout.uses_stage_layout is False
    assert layout.artifact_path(
        "rubric_extraction",
        "feedback_rubrics.jsonl",
    ) == (layout.root / "decision_assets" / "feedback_rubrics.jsonl")
    assert layout.artifact_path(
        "rubric_extraction",
        "trusted_cases.jsonl",
    ) == (layout.root / "prepared_inputs" / "trusted_cases.jsonl")
    assert layout.artifact_path(
        "coverage_decisions",
        "review_queue/labeling_queue.jsonl",
    ) == (layout.root / "review_queues" / "labeling_queue.jsonl")


def test_layout_resolves_previous_stage_three_directory(tmp_path: Path) -> None:
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    previous = layout.stages_root / "03_rubric_extraction"
    previous.mkdir(parents=True)

    assert layout.stage_directory(PipelineStage.RUBRIC_EXTRACTION) == previous
    assert layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "feedback_rubrics.jsonl",
    ) == previous / "feedback_rubrics.jsonl"


def _add_genuine_stage_one_receipt(
    layout: EvaluationAssetLayout,
    state: PipelineState,
) -> None:
    pipeline = EvaluationAssetPipeline(
        layout,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    counts = pipeline._validate_raw_inputs()
    pipeline._finalize_stage_outputs(PipelineStage.RAW_INPUTS)
    completed_at = utc_now()
    receipt = build_stage_receipt(
        layout,
        PipelineStage.RAW_INPUTS,
        layout.load_config(),
        counts,
        completed_at=completed_at,
        prompt_values={},
    )
    receipt_path = layout.receipt_path(PipelineStage.RAW_INPUTS)
    artifact_io.atomic_write_json(receipt_path, receipt)
    stage_one = state.stages[0]
    stage_one.status = "completed"
    stage_one.started_at = stage_one.started_at or completed_at
    stage_one.completed_at = completed_at
    stage_one.receipt_sha256 = file_sha256(receipt_path)
    state.counts.update(counts)


def test_revise_config_invalidates_only_dependent_stages(tmp_path: Path) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            match_threshold=0.6,
        ),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages:
        stage_state.status = "completed"
        stage_state.message = "done"
        stage_state.started_at = "2026-08-20T00:00:00+00:00"
        stage_state.completed_at = "2026-08-20T00:00:01+00:00"
    state.status = "failed"
    state.error = "stopped"
    state.counts = {
        key: 1 for keys in STAGE_COUNT_KEYS.values() for key in keys
    }
    _add_genuine_stage_one_receipt(layout, state)
    layout.save_state(state)
    stage_four_artifact = layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    )
    stage_five_artifact = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "cluster_sampling_metadata.jsonl",
    )
    stage_four_artifact.write_text("{}\n", encoding="utf-8")
    stage_five_artifact.write_text("{}\n", encoding="utf-8")
    layout.manifest_path.write_text("{}\n", encoding="utf-8")
    release_pointer = layout.release_pointer_path
    generation_split = (
        layout.generations_root / f"sha256-{'0' * 64}" / "train.jsonl"
    )
    generation_split.parent.mkdir(parents=True)
    release_pointer.write_text("{}\n", encoding="utf-8")
    generation_split.write_text("{}\n", encoding="utf-8")

    revision = layout.revise_config({"match_threshold": 0.2})

    revised_state = layout.load_state()
    assert revision["resume_from_stage"] == "coverage_decisions"
    assert revision["invalidated_from_stage"] == "coverage_decisions"
    assert revision["changed_fields"] == {
        "match_threshold": {"previous": 0.6, "new": 0.2}
    }
    assert layout.load_config().match_threshold == 0.2
    assert stage_four_artifact.exists()
    assert not stage_five_artifact.exists()
    assert not layout.manifest_path.exists()
    assert release_pointer.read_text(encoding="utf-8") == "{}\n"
    assert generation_split.read_text(encoding="utf-8") == "{}\n"
    assert [
        item.status for item in revised_state.stages[:4]
    ] == ["completed"] * 4
    assert [
        item.status for item in revised_state.stages[4:]
    ] == ["pending"] * 4
    assert "intent_clusters" in revised_state.counts
    assert "matched_clusters" not in revised_state.counts
    assert revised_state.status == "queued"
    assert revised_state.current_stage == "coverage_decisions"
    history = [
        json.loads(line)
        for line in layout.config_history_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert [entry["event"] for entry in history] == [
        "configuration_created",
        "configuration_updated",
    ]


def test_revise_config_derives_embedding_provider_and_restarts_stage_four(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages[:3]:
        stage_state.status = "completed"
    _add_genuine_stage_one_receipt(layout, state)
    layout.save_state(state)

    revision = layout.revise_config({"embedding_model": "tfidf"})

    config = layout.load_config()
    assert config.embedding_model == "tfidf"
    assert config.embedding_provider == "tfidf"
    assert revision["resume_from_stage"] == "intent_clustering"
    assert revision["invalidated_from_stage"] == "intent_clustering"


def test_revise_config_with_unchanged_values_preserves_checkpoints(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
    )
    _add_genuine_stage_one_receipt(layout, state)
    layout.save_state(state)

    revision = layout.revise_config({"match_threshold": 0.6})

    assert revision == {
        "changed_fields": {},
        "invalidated_from_stage": None,
        "resume_from_stage": None,
    }
    assert layout.load_state().stages[0].status == "completed"
    assert layout.config_revision_summary()["count"] == 1


def test_revise_config_resumes_an_earlier_incomplete_stage(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_minimal_input_pair(tenants_root, "tenant_a")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages:
        stage_state.status = "completed"
    state.stages[4].status = "failed"
    state.status = "failed"
    state.current_stage = "coverage_decisions"
    _add_genuine_stage_one_receipt(layout, state)
    layout.save_state(state)

    revision = layout.revise_config({"synthetic_coverage_enabled": True})

    assert revision["invalidated_from_stage"] == "synthetic_coverage"
    assert revision["resume_from_stage"] == "coverage_decisions"
    assert layout.load_state().current_stage == "coverage_decisions"


def test_extend_asset_keeps_clustering_and_extracts_only_new_rubrics(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tenants_root / "tenant_a" / "source_artifacts"
    inputs.mkdir(parents=True)
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_feedback = inputs / "added-feedback.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1", "u2"])
    _write_extension_feedback(added_feedback, ["u1"])
    parent_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    parent_pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            synthetic_coverage_enabled=False,
            rubric_provider="fake",
            rubric_model="fake-rubric",
            embedding_provider="fake",
            embedding_model="fake-embedding",
        ),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    _approve_and_finalize(parent_pipeline)
    parent_inventory = parent_layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    ).read_text(encoding="utf-8")
    parent_locations = _split_case_locations(parent_layout)

    child_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")
    child_layout.initialize_extension(
        parent_layout,
        additional_feedback=added_feedback,
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    parent_layout.root.rename(tmp_path / "archived-parent")
    child_provider = FakeRubricProvider()
    child_pipeline = EvaluationAssetPipeline(
        child_layout,
        rubric_provider=child_provider,
        embedding_provider=FakeEmbeddingProvider(),
    )
    child_state = _approve_and_finalize(child_pipeline)

    assert child_state.status == "released"
    assert set(child_provider.feedback_record_ids) == {"f1", "u1"}
    assert child_layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    ).read_text(encoding="utf-8") == parent_inventory
    guidelines = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        )
    )
    assert {
        record_id
        for row in guidelines
        for record_id in row["source_record_ids"]
    } == {
        row["record_id"]
        for row in _read_test_jsonl(
            child_layout.artifact_path(
                PipelineStage.PREPARED_INPUTS,
                "normalized_feedback.jsonl",
            )
        )
        if row["trusted_split"] == "train" and row["evidence_eligible"]
    }
    inferred = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "inferred_cases.jsonl",
        )
    )
    assert "inferred-u1" not in {row["case_id"] for row in inferred}
    child_locations = _split_case_locations(child_layout)
    assert parent_locations
    for case_id, parent_split in parent_locations.items():
        if case_id == "inferred-u1":
            continue
        assert child_locations[case_id] == parent_split
    lineage = json.loads(child_layout.lineage_path.read_text(encoding="utf-8"))
    assert lineage["parent_asset_id"] == "v1"
    assert lineage["clustering_mode"] == "keep"


def test_extend_asset_refreshes_clustering_for_new_unlabeled_records(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tenants_root / "tenant_a" / "source_artifacts"
    inputs.mkdir(parents=True)
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_unlabeled = inputs / "added-unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1", "u2"])
    _write_extension_unlabeled(added_unlabeled, ["u3"])
    parent = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            rubric_provider="fake",
            rubric_model="fake-rubric",
            embedding_provider="fake",
            embedding_model="fake-embedding",
        ),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    _approve_and_finalize(parent)
    parent_layout = parent.layout

    child_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")
    child_layout.initialize_extension(
        parent_layout,
        additional_feedback=None,
        additional_unlabeled=added_unlabeled,
        clustering_mode="refresh",
        config_updates={"cluster_count": 2},
    )
    child_provider = FakeRubricProvider()
    child_pipeline = EvaluationAssetPipeline(
        child_layout,
        rubric_provider=child_provider,
        embedding_provider=FakeEmbeddingProvider(),
    )
    state = _approve_and_finalize(child_pipeline)

    assert state.status == "released"
    assert child_provider.feedback_record_ids == ["f1"]
    assert state.counts["unlabeled_records"] == 3
    assert state.counts["intent_clusters"] == 2
    lineage_rows = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.INTENT_CLUSTERING,
            "cluster_lineage.jsonl",
        )
    )
    assert lineage_rows
    assert {
        row["relationship"] for row in lineage_rows
    } <= {"continued", "split", "merged", "new", "retired"}


def test_extend_asset_rejects_unlabeled_additions_when_clustering_is_kept(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tenants_root / "tenant_a" / "source_artifacts"
    inputs.mkdir(parents=True)
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_unlabeled = inputs / "added-unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    _write_extension_unlabeled(added_unlabeled, ["u2"])
    parent = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            rubric_provider="fake",
            rubric_model="fake-rubric",
            embedding_provider="fake",
            embedding_model="fake-embedding",
        ),
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    parent.run()

    with pytest.raises(ValueError, match="use refresh"):
        EvaluationAssetLayout(tenants_root, "tenant_a", "v2").initialize_extension(
            parent.layout,
            additional_feedback=None,
            additional_unlabeled=added_unlabeled,
            clustering_mode="keep",
        )


@pytest.mark.parametrize(
    (
        "synthetic_coverage_enabled",
        "synthetic_cases_per_cluster",
        "expected_synthetic_cases",
    ),
    [(False, 1, 0), (True, 2, 2)],
)
def test_pipeline_is_self_contained_and_writes_canonical_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    synthetic_coverage_enabled: bool,
    synthetic_cases_per_cluster: int,
    expected_synthetic_cases: int,
) -> None:
    tenants_root = tmp_path / "tenants"
    imports = tenants_root / "new_tenant" / "source_artifacts"
    imports.mkdir(parents=True)
    feedback = imports / "feedback.jsonl"
    unlabeled = imports / "unlabeled.jsonl"
    feedback.write_text(
        "\n".join(
            json.dumps(
                {
                    "schema_version": "fapo-evaluation-input-v1",
                    "record_id": f"f{index}",
                    "group_id": (
                        "feedback-thread"
                        if index == 1
                        else f"feedback-thread-{index}"
                    ),
                    "task_type": "answer",
                    "user_input": f"Apply requirement {index}",
                    "assistant_output": "Applied an alternative condition",
                    "conversation_context": [],
                    "tool_calls": [],
                    "runtime": {},
                    "metadata": {},
                    "feedback": {
                        "polarity": "negative",
                        "rationale": "The required condition was not satisfied",
                    },
                }
            )
            for index in range(1, 11)
        )
        + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        "\n".join(
            json.dumps(
                {
                    "schema_version": "fapo-evaluation-input-v1",
                    "record_id": f"u{index}",
                    "group_id": (
                        "feedback-thread"
                        if index == 1
                        else f"feedback-thread-{index}"
                    ),
                    "task_type": "answer",
                    "user_input": f"Answer request {index}",
                    "conversation_context": [],
                    "tool_calls": [],
                    "runtime": {},
                    "metadata": {},
                }
            )
            for index in range(1, 4)
        )
        + "\n",
        encoding="utf-8",
    )
    config = EvaluationAssetConfig(
        tenant_id="new_tenant",
        asset_id="v1",
        cluster_count=1,
        rubric_provider="fake",
        rubric_model="fake-rubric",
        embedding_provider="fake",
        embedding_model="fake-embedding",
        synthetic_coverage_enabled=synthetic_coverage_enabled,
        synthetic_cases_per_cluster=synthetic_cases_per_cluster,
    )
    rubric_provider = FakeRubricProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        config,
        feedback,
        unlabeled,
        repository_base=tmp_path,
        rubric_provider=rubric_provider,
        embedding_provider=FakeEmbeddingProvider(),
    )

    feedback.unlink()
    unlabeled.unlink()
    state = pipeline.run()
    layout = pipeline.layout

    assert state.status == "awaiting_review"
    review_page = layout.list_review_items()
    for item in review_page["items"]:
        layout.decide_review(
            item["case_id"],
            item["fingerprint"],
            "approved",
            reviewer="test-reviewer",
            expected_review_set_fingerprint=review_page[
                "review_set_fingerprint"
            ],
        )
    review_page = layout.list_review_items()
    state = pipeline.finalize_review(
        reviewer="test-reviewer",
        expected_review_set_fingerprint=review_page[
            "review_set_fingerprint"
        ],
        expected_decision_set_fingerprint=review_page[
            "decision_set_fingerprint"
        ],
    )
    assert state.status == "released"
    assert all(stage.status == "completed" for stage in state.stages)
    assert layout.feedback_path.exists()
    assert layout.unlabeled_path.exists()
    assert layout.artifact_path(
        "prepared_inputs",
        "normalized_feedback.jsonl",
    ).exists()
    assert layout.artifact_path(
        "coverage_decisions",
        "cluster_sampling_metadata.jsonl",
    ).exists()
    for stale_path in (
        layout.artifact_path("coverage_decisions", "intent_matches.jsonl"),
        layout.artifact_path(
            "coverage_decisions", "review_queue/labeling_queue.jsonl"
        ),
        layout.artifact_path(
            "label_inference", "episode_guideline_candidates.jsonl"
        ),
        layout.artifact_path(
            "label_inference", "episode_guideline_applicability.jsonl"
        ),
        layout.artifact_path(
            "label_inference", "inferred_unlabeled_cluster_rubrics.jsonl"
        ),
        layout.artifact_path("label_inference", "inference_dependencies.jsonl"),
    ):
        assert not stale_path.exists()
    for name in (
        "episode_rubrics.jsonl",
        "trusted_cases.jsonl",
        "inferred_cases.jsonl",
        "case_dependencies.jsonl",
        "held_rubric_outputs.jsonl",
    ):
        assert layout.artifact_path("label_inference", name).exists()
    assert layout.artifact_path("dataset_splits", "train.jsonl").exists()
    assert layout.manifest_path.exists()
    release = resolve_evaluation_asset_release(layout.published_datasets)
    for split_name in (
        "train",
        "validation",
        "test",
        "regression_trusted",
    ):
        stage_split = layout.artifact_path(
            "dataset_splits",
            f"{split_name}.jsonl",
        )
        published_split = release.files[split_name]
        assert published_split.read_bytes() == stage_split.read_bytes()
        assert not (layout.published_datasets / f"{split_name}.jsonl").exists()
    assert (layout.root / "stages" / "01_raw_inputs").is_dir()
    assert (layout.root / "stages" / "03_evaluation_guidelines").is_dir()
    assert not (layout.root / "stages" / "03_rubric_extraction").exists()
    assert not (layout.root / "raw_inputs").exists()

    prepared_feedback = json.loads(
        layout.artifact_path(
            "prepared_inputs",
            "normalized_feedback.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    prepared_intent = json.loads(
        layout.artifact_path(
            "prepared_inputs",
            "intent_records.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    feedback_evidence = json.loads(
        layout.artifact_path(
            "rubric_extraction",
            "feedback_evidence.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    evaluation_guideline = json.loads(
        layout.artifact_path(
            "rubric_extraction",
            "evaluation_guidelines.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    trusted_case = json.loads(
        layout.artifact_path(
            "label_inference",
            "trusted_cases.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    inferred_rubric = next(
        row
        for row in _read_test_jsonl(
            layout.artifact_path("label_inference", "episode_rubrics.jsonl")
        )
        if row["record_id"] == "u1"
    )
    dataset_manifest = json.loads(
        layout.artifact_path(
            "dataset_splits",
            "dataset_manifest.json",
        ).read_text(encoding="utf-8")
    )

    assert prepared_feedback["record_id"] == "f1"
    assert prepared_feedback["group_id"] == "feedback-thread"
    assert prepared_feedback["schema_version"] == "fapo-evaluation-input-v1"
    assert "feedback_id" not in prepared_feedback
    assert "thread_id" not in prepared_feedback
    assert prepared_intent["record_id"] == "u1"
    assert prepared_intent["group_id"] == "feedback-thread"
    assert prepared_intent["schema_version"] == "fapo-evaluation-input-v1"
    assert "feedback_id" not in prepared_intent
    assert "thread_id" not in prepared_intent
    assert feedback_evidence["record_id"] == "f1"
    assert "feedback_id" not in feedback_evidence
    normalized_feedback = _read_test_jsonl(
        layout.artifact_path("prepared_inputs", "normalized_feedback.jsonl")
    )
    assert set(evaluation_guideline["source_record_ids"]) == {
        row["record_id"]
        for row in normalized_feedback
        if row["trusted_split"] == "train" and row["evidence_eligible"]
    }
    assert evaluation_guideline["calibration_status"] == "uncalibrated"
    assert evaluation_guideline["criteria"][0]["evaluator"]["type"] == "llm_judge"
    assert trusted_case["metadata"]["group_id"] == "feedback-thread"
    assert trusted_case["metadata"]["request_id"] == "f1"
    assert "review_status" not in trusted_case["metadata"]
    assert "thread_group" not in trusted_case["metadata"]
    assert "request_group" not in trusted_case["metadata"]
    assert evaluation_guideline["guideline_id"] in (
        trusted_case["expected"]["evaluation_guideline_ids"]
    )
    assert inferred_rubric["review_status"] == "review_required"
    assert inferred_rubric["rubric_provenance"] == "guideline_grounded"
    assert (
        dataset_manifest["review_policy"]["evaluation_guidelines"]
        == "active_from_trusted_evidence"
    )
    assert dataset_manifest["review_policy"]["guideline_calibration"] == "uncalibrated"
    assert dataset_manifest["clustering"]["purpose"] == (
        "batch_sampling_and_analysis"
    )
    assert dataset_manifest["clustering"]["correctness_role"] == "none"
    assert dataset_manifest["evaluation_guidelines"] == {
        "schema_version": "fapo-evaluation-guideline-v1",
        "count": 1,
        "activation_status": "active_from_trusted_evidence",
        "calibration_status": "uncalibrated",
    }
    assert dataset_manifest["episode_rubric_generation"] == {
        "method": "full_catalog_single_call_per_episode_v1",
        "guideline_selection": "inside_rubric_generation_call",
        "guideline_catalog": "all_split_permitted_guidelines",
        "no_applicable_guideline_fallback": "trace_inferred",
        "trace_evidence": [
            "user_messages",
            "assistant_messages",
            "tool_calls",
            "tool_results",
            "runtime",
            "trusted_feedback_when_present",
        ],
    }
    assert dataset_manifest["synthetic_coverage"] == {
        "enabled": synthetic_coverage_enabled,
        "cases_per_cluster": synthetic_cases_per_cluster,
    }
    assert dataset_manifest["regression_gate"] == {
        "source": "trusted_feedback",
        "fraction": 0.2,
        "selection": "deterministic_early_connected_group_hash",
        "seed": 42,
    }
    generation_directory = release.generation_dir.relative_to(
        layout.tenants_root.parent
    ).as_posix()
    assert dataset_manifest["published_datasets"] == {
        "directory": "datasets/evaluation_assets/v1",
        "release_pointer": "datasets/evaluation_assets/v1/release.json",
        "generation_id": release.generation_id,
        "generation_manifest_sha256": release.generation_manifest_sha256,
        "build_provenance_sha256": release.build_provenance_sha256,
        "build_fingerprint": release.build_fingerprint,
        "files": {
            split: f"{generation_directory}/{split}.jsonl"
            for split in ("train", "validation", "test", "regression_trusted")
        },
    }
    assert dataset_manifest["review_policy"]["derived_cases"] == "approved_only"
    assert dataset_manifest["review_policy"]["episode_rubrics"] == (
        "case_specific_with_explicit_provenance"
    )
    review_snapshot_path = layout.artifact_path(
        PipelineStage.DATASET_SPLITS,
        "review_snapshot.json",
    )
    review_snapshot = json.loads(review_snapshot_path.read_text(encoding="utf-8"))
    fingerprint_inventory = dataset_manifest["review"]["fingerprints"]
    assert set(fingerprint_inventory) == {
        "trusted",
        "approved",
        "pending",
        "rejected",
        "held",
    }
    assert {
        status: len(rows) for status, rows in fingerprint_inventory.items()
    } == dataset_manifest["review"]["counts"]
    held_ids = {row["case_id"] for row in review_snapshot["held"]}
    trusted_review_cases = _read_test_jsonl(
        layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "trusted_cases.jsonl",
        )
    )
    assert fingerprint_inventory["trusted"] == sorted(
        (
            {
                "case_id": row["case_id"],
                "fingerprint": case_content_fingerprint(row),
            }
            for row in trusted_review_cases
            if row["case_id"] not in held_ids
        ),
        key=lambda row: (row["case_id"], row["fingerprint"]),
    )
    assert fingerprint_inventory["held"] == review_snapshot["held"]
    for status in ("approved", "pending", "rejected"):
        assert fingerprint_inventory[status] == [
            {"case_id": row["case_id"], "fingerprint": row["fingerprint"]}
            for row in review_snapshot["items"]
            if row["status"] == status
        ]
    build_provenance = json.loads(
        layout.build_provenance_path.read_text(encoding="utf-8")
    )
    review_input = build_provenance["identity"]["inputs"]["review_snapshot"]
    review_bytes = review_snapshot_path.read_bytes()
    assert review_input == {
        "path": review_snapshot_path.relative_to(layout.root).as_posix(),
        "bytes": len(review_bytes),
        "rows": 1,
        "sha256": hashlib.sha256(review_bytes).hexdigest(),
    }

    synthetic_candidates = [
        json.loads(line)
        for line in layout.artifact_path(
            "synthetic_coverage",
            "synthetic_candidates.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    synthetic_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            "synthetic_coverage",
            "synthetic_cases.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert len(synthetic_candidates) == expected_synthetic_cases
    assert len(synthetic_cases) == expected_synthetic_cases
    assert len({row["case_id"] for row in synthetic_candidates}) == len(
        synthetic_candidates
    )
    assert rubric_provider.synthetic_calls == (
        1 if synthetic_coverage_enabled else 0
    )
    assert rubric_provider.episode_rubric_calls == 13

    regression_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            "dataset_splits",
            "regression_trusted.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    standard_trusted_cases = [
        json.loads(line)
        for name in ("train_trusted", "validation_trusted", "test_trusted")
        for line in layout.artifact_path(
            "dataset_splits",
            f"{name}.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert len(regression_cases) == 2
    assert len(standard_trusted_cases) == 8
    assert {
        row["case_id"] for row in regression_cases
    }.isdisjoint(row["case_id"] for row in standard_trusted_cases)
    assert {
        row["metadata"]["group_id"] for row in regression_cases
    }.isdisjoint(
        row["metadata"]["group_id"] for row in standard_trusted_cases
    )
    assert state.counts["regression_trusted_cases"] == 2

    combined_splits = {
        name: [
            json.loads(line)
            for line in layout.artifact_path(
                "dataset_splits",
                f"{name}.jsonl",
            ).read_text(encoding="utf-8").splitlines()
        ]
        for name in ("train", "validation", "test")
    }
    split_groups = {
        name: {row["metadata"]["group_id"] for row in rows}
        for name, rows in combined_splits.items()
    }
    assert split_groups["train"].isdisjoint(split_groups["validation"])
    assert split_groups["train"].isdisjoint(split_groups["test"])
    assert split_groups["validation"].isdisjoint(split_groups["test"])
    regression_groups = {
        row["metadata"]["group_id"] for row in regression_cases
    }
    assert all(
        regression_groups.isdisjoint(groups)
        for groups in split_groups.values()
    )

    triage_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            "dataset_splits",
            "triage_hold.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert all(
        row["metadata"]["group_id"] in regression_groups
        and row["metadata"]["hold_reason"]
        == "group_id_reserved_for_regression"
        for row in triage_cases
    )
    case_locations = {
        row["case_id"]: split
        for split, rows in {
            **combined_splits,
            "regression": regression_cases,
            "triage": triage_cases,
        }.items()
        for row in rows
    }
    for index in range(1, 4):
        trusted_location = case_locations[f"feedback-f{index}"]
        inferred_location = case_locations[f"inferred-u{index}"]
        if trusted_location == "regression":
            assert inferred_location == "triage"
        else:
            assert inferred_location == trusted_location
    assert state.counts["triage_hold_cases"] == len(triage_cases)
    monkeypatch.chdir(layout.tenants_root.parent)
    assert load_cases(
        Path(dataset_manifest["published_datasets"]["files"]["train"])
    )


def test_layout_rejects_unsafe_tenant_and_asset_names(tmp_path: Path) -> None:
    for tenant_id, asset_id in (("../escape", "v1"), ("tenant", "../../asset")):
        try:
            EvaluationAssetLayout(tmp_path / "tenants", tenant_id, asset_id)
        except ValueError:
            continue
        raise AssertionError("unsafe evaluation asset path was accepted")


def _write_extension_feedback(path: Path, record_ids: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": record_id,
            "group_id": f"group-{record_id}",
            "task_type": "answer",
            "route": "route_a",
            "user_input": f"Request {record_id}",
            "assistant_output": "Previous response",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
            "feedback": {
                "polarity": "positive",
                "rationale": "The response satisfied the request.",
            },
        }
        for record_id in record_ids
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_extension_unlabeled(path: Path, record_ids: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": record_id,
            "group_id": f"group-{record_id}",
            "task_type": "answer",
            "route": "route_a",
            "user_input": f"Request {record_id}",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
        }
        for record_id in record_ids
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_unlabeled_routes(path: Path, routes: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": f"u{index}",
            "group_id": f"group-u{index}",
            "task_type": route,
            "route": route if index % 2 else None,
            "user_input": f"Request u{index}",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
        }
        for index, route in enumerate(routes, start=1)
    ]
    for row in rows:
        if row["route"] is None:
            del row["route"]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_minimal_input_pair(
    tenants_root: Path,
    tenant_id: str,
) -> tuple[Path, Path]:
    source_root = tenants_root / tenant_id / "source_artifacts"
    source_root.mkdir(parents=True, exist_ok=True)
    feedback = source_root / "feedback.jsonl"
    unlabeled = source_root / "unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    return feedback, unlabeled


def _read_test_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _split_case_locations(layout: EvaluationAssetLayout) -> dict[str, str]:
    locations = {}
    for split in ("train", "validation", "test", "regression_trusted"):
        for row in _read_test_jsonl(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
        ):
            locations[row["case_id"]] = split
    return locations
