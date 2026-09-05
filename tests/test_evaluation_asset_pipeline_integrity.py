# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Focused integration contracts for trust/review pipeline hardening."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.hephaestus.evaluation_assets import pipeline as pipeline_module
from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig, PipelineStage
from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.split_isolation import (
    assign_split,
    derive_split_groups,
)
from src.hephaestus.webui.data import TenantStore


class _RecordingRubricProvider:
    provider_name = "recording"
    model = "recording-rubric"

    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []
        self.requests: list[dict[str, object]] = []

    def generate_json(self, system_prompt: str, payload: dict[str, object]):
        copied = json.loads(json.dumps(payload))
        self.payloads.append(copied)
        self.requests.append(
            {"system_prompt": system_prompt, "payload": copied}
        )
        if payload.get("mode") == "full_catalog_episode_rubric":
            guidelines = payload["evaluation_guidelines"]
            guideline_ids = [row["guideline_id"] for row in guidelines]
            episode = payload["episode"]
            return {
                "rubrics": [
                    {
                        "record_id": episode["record_id"],
                        "applicable_guideline_ids": guideline_ids,
                        "provenance": (
                            "guideline_grounded"
                            if guideline_ids
                            else "trace_inferred"
                        ),
                        "intent_label": "answer",
                        "confidence": 0.8,
                        "must": ["Answer the traffic request."],
                        "must_not": [],
                        "should": [],
                        "deterministic_checks": [],
                        "tool_expectations": {},
                        "reference_output": None,
                        "evidence_pointers": ["episode.user_messages[0]"],
                    }
                ]
            }
        if "records" in payload:
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "answer",
                        "confidence": 0.9,
                        "observations": [
                            {
                                "claim": row["feedback"]["rationale"],
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
        if "synthetic evaluation inputs" in system_prompt:
            return {
                "cases": [
                    {
                        "cluster_id": row["cluster_id"],
                        "task_type": row["route"],
                        "user_input": (
                            f"Synthetic coverage request for {row['cluster_id']}"
                        ),
                        "conversation_context": [],
                    }
                    for row in payload["clusters"]
                ]
            }
        if "clusters" in payload:
            return {
                "rubrics": [
                    {
                        "cluster_id": row["cluster_id"],
                        "intent_label": "answer",
                        "confidence": 0.8,
                        "must": ["Answer the traffic request."],
                        "must_not": [],
                        "should": [],
                        "deterministic_checks": [],
                        "tool_expectations": {},
                        "reference_output": None,
                    }
                    for row in payload["clusters"]
                ]
            }
        criterion = payload["evidence"][0]["observations"][0]["claim"]
        return {
            "guidelines": [
                {
                    "intent_label": "answer",
                    "description": "Answer the request.",
                    "route": payload["route"],
                    "source_record_ids": [
                        row["record_id"] for row in payload["evidence"]
                    ],
                    "confidence": 0.9,
                    "criteria": [
                        {
                            "kind": "required",
                            "statement": criterion,
                            "dimension": "task_success",
                            "severity": "critical",
                            "applicability": "always",
                            "scoring": "binary",
                            "evidence_required": False,
                            "evaluator": {
                                "type": "llm_judge",
                                "fallback": "human_review",
                            },
                        }
                    ],
                    "tool_expectations": {},
                    "reference_output": None,
                }
            ]
        }


class _RecordingEmbeddingProvider:
    provider_name = "recording"
    model = "recording-embedding"

    def __init__(self) -> None:
        self.payloads: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.payloads.append([str(text) for text in texts])
        return [[1.0, 0.0] for _ in texts]


def _feedback_row(record_id: str, group_id: str, *, rationale: str) -> dict:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": group_id,
        "request_id": record_id,
        "task_type": "answer",
        "route": "answer",
        "user_input": f"USER-CANARY-{record_id}",
        "assistant_output": f"OUTPUT-CANARY-{record_id}",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
        "feedback": {
            "polarity": "negative",
            "rationale": rationale,
        },
    }


def _row_for_split(record_id: str, split: str, *, rationale: str) -> dict:
    for ordinal in range(10_000):
        row = _feedback_row(
            record_id,
            f"group-{split}-{ordinal}",
            rationale=rationale,
        )
        split_group_id = derive_split_groups([row])[0].split_group_id
        if assign_split(split_group_id, split_seed=42) == split:
            return row
    raise AssertionError(f"could not construct a {split} fixture")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("array_key", "identity_key"),
    [
        ("evidence", "record_id"),
        ("rubrics", "cluster_id"),
    ],
)
def test_generated_model_response_rejects_duplicate_identity(
    array_key: str,
    identity_key: str,
) -> None:
    """A repeated model identity reports the value and both item positions."""
    response = {
        array_key: [
            {identity_key: "duplicate-id", "value": "first"},
            {identity_key: "duplicate-id", "value": "second"},
        ]
    }

    with pytest.raises(
        ValueError,
        match=(
            rf"duplicate {identity_key} 'duplicate-id'.*"
            rf"item 1.*item 2"
        ),
    ):
        pipeline_module._indexed_items(response, array_key, identity_key)


def test_stage_three_isolates_held_out_canaries_and_skips_ineligible_feedback(
    tmp_path: Path,
) -> None:
    feedback_rows = [
        _row_for_split("train", "train", rationale="RATIONALE-CANARY-train"),
        _row_for_split(
            "validation",
            "validation",
            rationale="RATIONALE-CANARY-validation",
        ),
        _row_for_split("test", "test", rationale="RATIONALE-CANARY-test"),
        _row_for_split(
            "regression",
            "regression",
            rationale="RATIONALE-CANARY-regression",
        ),
        _row_for_split("held", "train", rationale=""),
    ]
    tenants_root = tmp_path / "tenants"
    source_root = tenants_root / "tenant_a" / "source_artifacts"
    source_root.mkdir(parents=True)
    feedback = source_root / "feedback.jsonl"
    unlabeled = source_root / "unlabeled.jsonl"
    _write_jsonl(feedback, feedback_rows)
    _write_jsonl(
        unlabeled,
        [
            {
                key: value
                for key, value in _feedback_row(
                    "unlabeled",
                    "unlabeled-group",
                    rationale="unused",
                ).items()
                if key not in {"assistant_output", "feedback"}
            }
        ],
    )
    provider = _RecordingRubricProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id="v1",
            rubric_provider="recording",
            rubric_model="recording-rubric",
            embedding_provider="tfidf",
            embedding_model="tfidf-v1",
            cluster_count=1,
            batch_size=10,
        ),
        feedback,
        unlabeled,
        rubric_provider=provider,
        repository_base=tmp_path,
    )

    pipeline._validate_raw_inputs()
    pipeline._configure_providers()
    pipeline._prepare_inputs()
    pipeline._create_evaluation_guidelines()

    stage = PipelineStage.RUBRIC_EXTRACTION
    artifacts = {
        name: pipeline_module._load_jsonl(pipeline.layout.artifact_path(stage, name))
        for name in (
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "protected_feedback_evidence.jsonl",
            "protected_candidate_guidelines.jsonl",
            "protected_evaluation_guidelines.jsonl",
        )
    }
    reusable_text = json.dumps(
        {name: rows for name, rows in artifacts.items() if not name.startswith("protected_")},
        sort_keys=True,
    )
    assert "CANARY-validation" not in reusable_text
    assert "CANARY-test" not in reusable_text
    assert "CANARY-regression" not in reusable_text
    assert {row["record_id"] for row in artifacts["feedback_evidence.jsonl"]} == {
        "train"
    }
    assert {
        row["record_id"]
        for row in artifacts["protected_feedback_evidence.jsonl"]
    } == {"validation", "test", "regression"}
    assert {
        source_id
        for row in artifacts["protected_evaluation_guidelines.jsonl"]
        for source_id in row["source_record_ids"]
    } == {"validation", "test", "regression"}
    protected_text = json.dumps(
        {
            name: rows
            for name, rows in artifacts.items()
            if name.startswith("protected_")
        },
        sort_keys=True,
    )
    for split in ("validation", "test", "regression"):
        assert f"RATIONALE-CANARY-{split}" in protected_text

    payload_text = json.dumps(provider.payloads, sort_keys=True)
    assert "CANARY-held" not in payload_text
    for payload in provider.payloads:
        visible_ids = {
            str(row["record_id"])
            for key in ("records", "evidence")
            for row in payload.get(key, [])
        }
        assert not visible_ids or visible_ids in (
            {"train"},
            {"validation"},
            {"test"},
            {"regression"},
        ) or all(record_id.startswith("source-") for record_id in visible_ids)


def test_held_out_canaries_are_isolated_to_their_own_episode_rubrics(
    tmp_path: Path,
) -> None:
    """Protected criteria never enter clustering, unlabeled, or synthesis inputs."""
    feedback_rows = [
        _row_for_split("train", "train", rationale="RATIONALE-CANARY-train"),
        _row_for_split(
            "validation",
            "validation",
            rationale="RATIONALE-CANARY-validation",
        ),
        _row_for_split("test", "test", rationale="RATIONALE-CANARY-test"),
        _row_for_split(
            "regression",
            "regression",
            rationale="RATIONALE-CANARY-regression",
        ),
    ]
    tenants_root = tmp_path / "tenants"
    source_root = tenants_root / "tenant_a" / "source_artifacts"
    source_root.mkdir(parents=True)
    feedback = source_root / "feedback.jsonl"
    unlabeled = source_root / "unlabeled.jsonl"
    _write_jsonl(feedback, feedback_rows)
    unlabeled_row = {
        key: value
        for key, value in _feedback_row(
            "unlabeled",
            "unlabeled-group",
            rationale="unused",
        ).items()
        if key not in {"assistant_output", "feedback"}
    }
    unlabeled_row["user_input"] = "USER-CANARY-train followup traffic request"
    _write_jsonl(unlabeled, [unlabeled_row])
    provider = _RecordingRubricProvider()
    embedding_provider = _RecordingEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id="v1",
            rubric_provider="recording",
            rubric_model="recording-rubric",
            embedding_provider=embedding_provider.provider_name,
            embedding_model=embedding_provider.model,
            cluster_count=1,
            batch_size=10,
            match_threshold=0.0,
            synthetic_coverage_enabled=True,
            synthetic_cases_per_cluster=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=provider,
        embedding_provider=embedding_provider,
        repository_base=tmp_path,
    )

    paused = pipeline.run()

    assert paused.status == "awaiting_review"
    synthetic_requests = [
        row
        for row in provider.requests
        if "clusters" in row["payload"]
    ]
    assert len(synthetic_requests) == 1
    held_out_canaries = {
        f"{field}-CANARY-{split}"
        for split in ("validation", "test", "regression")
        for field in ("USER", "OUTPUT", "RATIONALE")
    }
    assert len(embedding_provider.payloads) == 1
    embedding_payloads = {
        PipelineStage.INTENT_CLUSTERING: embedding_provider.payloads[0],
    }
    for stage, payload in embedding_payloads.items():
        payload_text = json.dumps(payload, sort_keys=True)
        assert "USER-CANARY-train" in payload_text, stage.value
        assert all(
            canary not in payload_text
            for canary in held_out_canaries
        ), stage.value
    later_payload_text = json.dumps(synthetic_requests, sort_keys=True)
    assert all(canary not in later_payload_text for canary in held_out_canaries)

    rubric_requests = {
        row["payload"]["episode"]["record_id"]: row["payload"]
        for row in provider.requests
        if row["payload"].get("mode") == "full_catalog_episode_rubric"
    }
    assert set(rubric_requests) == {
        "train",
        "validation",
        "test",
        "regression",
        "unlabeled",
    }
    for record_id, payload in rubric_requests.items():
        payload_text = json.dumps(payload, sort_keys=True)
        permitted = (
            {f"{field}-CANARY-{record_id}" for field in ("USER", "OUTPUT", "RATIONALE")}
            if record_id in {"validation", "test", "regression"}
            else set()
        )
        assert all(
            canary in permitted or canary not in payload_text
            for canary in held_out_canaries
        )

    store = TenantStore(tenants_root, repository_base=tmp_path)
    ui_projection = json.dumps(
        [
            store.get_evaluation_asset_stage(
                "tenant_a",
                "v1",
                stage.value,
            )
            for stage in (
                PipelineStage.INTENT_CLUSTERING,
                PipelineStage.COVERAGE_DECISIONS,
                PipelineStage.SYNTHETIC_COVERAGE,
            )
        ],
        sort_keys=True,
    )
    assert all(canary not in ui_projection for canary in held_out_canaries)
    protected_stage = store.get_evaluation_asset_stage(
        "tenant_a",
        "v1",
        PipelineStage.RUBRIC_EXTRACTION.value,
    )
    assert protected_stage is not None
    assert all(
        artifact["preview_policy"] == "disabled"
        for artifact in protected_stage["artifacts"]
        if artifact["name"].startswith("protected_")
    )
