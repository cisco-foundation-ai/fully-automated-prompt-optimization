# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""End-to-end contracts for the evaluation-asset review lifecycle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from src.hephaestus.evaluation_assets import workspace as workspace_module
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
)
from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.split_isolation import (
    assign_split,
    derive_split_groups,
)
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


class _DeterministicEmbeddingProvider:
    provider_name = "review-lifecycle-test"
    model = "review-lifecycle-embedding"

    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


class _DeterministicRubricProvider:
    provider_name = "review-lifecycle-test"
    model = "review-lifecycle-rubric"

    def __init__(self) -> None:
        self.calls = 0

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        self.calls += 1
        if "records" in payload:
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "answer the request",
                        "confidence": 0.9,
                        "observations": [
                            {
                                "claim": "Answer the stated request.",
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
            source_record_ids = [row["record_id"] for row in payload["evidence"]]
            return {
                "guidelines": [
                    {
                        "intent_label": "answer the request",
                        "description": "Answer requests within their stated scope.",
                        "route": payload["route"],
                        "source_record_ids": source_record_ids,
                        "confidence": 0.9,
                        "criteria": [
                            {
                                "kind": "required",
                                "statement": "Answer the stated request.",
                                "source_record_ids": source_record_ids,
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
                        "conflicts": [],
                        "uncertainties": [],
                    }
                ]
            }
        if "synthetic evaluation inputs" in system_prompt:
            raise AssertionError("synthetic generation is disabled in this test")
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "answer the request",
                    "confidence": 0.8,
                    "must": ["Answer the stated request."],
                    "must_not": ["Change the requested scope."],
                    "should": [],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
                for row in payload["clusters"]
            ]
        }


def _feedback_row(record_id: str, group_id: str) -> dict[str, Any]:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": group_id,
        "request_id": record_id,
        "task_type": "answer",
        "route": "answer",
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


def _feedback_for_split(record_id: str, split: str) -> dict[str, Any]:
    for ordinal in range(10_000):
        row = _feedback_row(record_id, f"group-{split}-{ordinal}")
        split_group_id = derive_split_groups([row])[0].split_group_id
        if assign_split(split_group_id, split_seed=42) == split:
            return row
    raise AssertionError(f"could not construct feedback for the {split} split")


def _unlabeled_row(record_id: str) -> dict[str, Any]:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": f"group-{record_id}",
        "request_id": record_id,
        "task_type": "answer",
        "route": "answer",
        "user_input": f"Request {record_id}",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _new_pipeline(
    tmp_path: Path,
    *,
    asset_id: str = "v1",
) -> tuple[
    EvaluationAssetPipeline,
    _DeterministicRubricProvider,
    _DeterministicEmbeddingProvider,
]:
    tenants_root = tmp_path / "tenants"
    source_root = tenants_root / "tenant_a" / "source_artifacts"
    source_root.mkdir(parents=True, exist_ok=True)
    feedback = source_root / f"feedback-{asset_id}.jsonl"
    unlabeled = source_root / f"unlabeled-{asset_id}.jsonl"
    _write_jsonl(feedback, [_feedback_for_split("f1", "train")])
    _write_jsonl(unlabeled, [_unlabeled_row("u1"), _unlabeled_row("u2")])
    rubric_provider = _DeterministicRubricProvider()
    embedding_provider = _DeterministicEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id=asset_id,
            cluster_count=1,
            rubric_provider=rubric_provider.provider_name,
            rubric_model=rubric_provider.model,
            embedding_provider=embedding_provider.provider_name,
            embedding_model=embedding_provider.model,
            synthetic_coverage_enabled=False,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
        repository_base=tmp_path,
    )
    return pipeline, rubric_provider, embedding_provider


def _published_cases(layout: EvaluationAssetLayout) -> list[dict[str, Any]]:
    return [
        row
        for split in ("train", "validation", "test", "regression_trusted")
        for row in _read_jsonl(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
        )
    ]


def _review_statuses(page: Mapping[str, Any]) -> dict[str, str]:
    return {str(item["case_id"]): str(item["status"]) for item in page["items"]}


def test_pending_only_finalization_publishes_no_derived_cases(
    tmp_path: Path,
) -> None:
    pipeline, _, _ = _new_pipeline(tmp_path)

    paused = pipeline.run()
    page = pipeline.layout.list_review_items()

    assert paused.status == "awaiting_review"
    assert page["counts"] == {
        "trusted": 1,
        "approved": 0,
        "pending": 2,
        "rejected": 0,
        "held": 0,
        "total": 3,
    }
    derived_ids = {str(item["case_id"]) for item in page["items"]}

    released = pipeline.finalize_review(
        reviewer="reviewer-a",
        expected_review_set_fingerprint=page["review_set_fingerprint"],
        expected_decision_set_fingerprint=page["decision_set_fingerprint"],
    )

    published = _published_cases(pipeline.layout)
    assert released.status == "released"
    assert derived_ids.isdisjoint(str(case["case_id"]) for case in published)
    assert {case["metadata"]["trust_tier"] for case in published} == {"trusted_feedback"}
    snapshot = json.loads(
        pipeline.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "review_snapshot.json",
        ).read_text(encoding="utf-8")
    )
    assert snapshot["counts"] == {
        "trusted": 1,
        "approved": 0,
        "pending": 2,
        "rejected": 0,
        "held": 0,
    }


def test_finalization_rejects_a_stale_decision_snapshot_and_replays_release(
    tmp_path: Path,
) -> None:
    """Catch decision races hidden by a stable item/dependency review set."""
    pipeline, _, _ = _new_pipeline(tmp_path)
    assert pipeline.run().status == "awaiting_review"
    stale_page = pipeline.layout.list_review_items()
    item = stale_page["items"][0]
    pipeline.layout.decide_review(
        item["case_id"],
        item["fingerprint"],
        "approved",
        reviewer="reviewer-a",
        expected_review_set_fingerprint=stale_page["review_set_fingerprint"],
    )

    with pytest.raises(ValueError, match="decision set changed"):
        pipeline.finalize_review(
            reviewer="reviewer-a",
            expected_review_set_fingerprint=stale_page["review_set_fingerprint"],
            expected_decision_set_fingerprint=stale_page["decision_set_fingerprint"],
        )

    current_page = pipeline.layout.list_review_items()
    assert (
        pipeline.finalize_review(
            reviewer="reviewer-a",
            expected_review_set_fingerprint=current_page["review_set_fingerprint"],
            expected_decision_set_fingerprint=current_page["decision_set_fingerprint"],
        ).status
        == "released"
    )
    released_page = pipeline.layout.list_review_items()
    assert released_page["finalization"] is not None
    assert (
        pipeline.finalize_review(
            reviewer="different-replay-reviewer",
            expected_review_set_fingerprint=released_page["review_set_fingerprint"],
            expected_decision_set_fingerprint=released_page["decision_set_fingerprint"],
        ).status
        == "released"
    )


def test_exact_approve_and_reject_control_release_inclusion(
    tmp_path: Path,
) -> None:
    pipeline, _, _ = _new_pipeline(tmp_path)
    assert pipeline.run().status == "awaiting_review"
    page = pipeline.layout.list_review_items()
    approved_item, rejected_item = page["items"]

    approved = pipeline.layout.decide_review(
        approved_item["case_id"],
        approved_item["fingerprint"],
        "approved",
        reviewer="reviewer-a",
        expected_review_set_fingerprint=page["review_set_fingerprint"],
    )
    pipeline.layout.decide_review(
        rejected_item["case_id"],
        rejected_item["fingerprint"],
        "rejected",
        reviewer="reviewer-a",
        expected_review_set_fingerprint=page["review_set_fingerprint"],
    )
    page = pipeline.layout.list_review_items()

    released = pipeline.finalize_review(
        reviewer="reviewer-a",
        expected_review_set_fingerprint=page["review_set_fingerprint"],
        expected_decision_set_fingerprint=page["decision_set_fingerprint"],
    )

    published_by_id = {str(case["case_id"]): case for case in _published_cases(pipeline.layout)}
    assert released.status == "released"
    assert approved_item["case_id"] in published_by_id
    assert rejected_item["case_id"] not in published_by_id
    approved_case = published_by_id[approved_item["case_id"]]
    assert approved_case["metadata"]["review_status"] == "approved"
    assert approved_case["metadata"]["decision_id"] == approved["decision_id"]
    snapshot = json.loads(
        pipeline.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "review_snapshot.json",
        ).read_text(encoding="utf-8")
    )
    assert {item["case_id"]: item["status"] for item in snapshot["items"]} == {
        approved_item["case_id"]: "approved",
        rejected_item["case_id"]: "rejected",
    }


def test_child_inherits_identical_fingerprint_decisions(
    tmp_path: Path,
) -> None:
    parent, _, _ = _new_pipeline(tmp_path)
    assert parent.run().status == "awaiting_review"
    parent_page = parent.layout.list_review_items()
    parent_decisions: dict[str, dict[str, Any]] = {}
    for item, status in zip(parent_page["items"], ("approved", "rejected")):
        parent_decisions[item["case_id"]] = parent.layout.decide_review(
            item["case_id"],
            item["fingerprint"],
            status,
            reviewer="reviewer-a",
            expected_review_set_fingerprint=parent_page["review_set_fingerprint"],
        )
    parent_page = parent.layout.list_review_items()
    assert (
        parent.finalize_review(
            reviewer="reviewer-a",
            expected_review_set_fingerprint=parent_page["review_set_fingerprint"],
            expected_decision_set_fingerprint=parent_page[
                "decision_set_fingerprint"
            ],
        ).status
        == "released"
    )

    added_feedback = tmp_path / "tenants" / "tenant_a" / "source_artifacts" / "additional-feedback.jsonl"
    _write_jsonl(added_feedback, [_feedback_for_split("f2", "validation")])
    child_layout = EvaluationAssetLayout(
        tmp_path / "tenants",
        "tenant_a",
        "v2",
        repository_base=tmp_path,
    )
    child_layout.initialize_extension(
        parent.layout,
        additional_feedback=added_feedback,
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    child = EvaluationAssetPipeline(
        child_layout,
        rubric_provider=_DeterministicRubricProvider(),
        embedding_provider=_DeterministicEmbeddingProvider(),
    )

    assert child.run().status == "awaiting_review"
    child_page = child.layout.list_review_items()

    assert _review_statuses(child_page) == _review_statuses(parent.layout.list_review_items())
    parent_fingerprints = {item["case_id"]: item["fingerprint"] for item in parent_page["items"]}
    assert {item["case_id"]: item["fingerprint"] for item in child_page["items"]} == parent_fingerprints
    for item in child_page["items"]:
        inherited = item["inherited_from"]
        assert inherited == {
            "parent_asset_id": "v1",
            "parent_decision_id": parent_decisions[item["case_id"]]["decision_id"],
            "parent_fingerprint": parent_fingerprints[item["case_id"]],
        }
    assert (
        child.finalize_review(
            reviewer="reviewer-b",
            expected_review_set_fingerprint=child_page["review_set_fingerprint"],
            expected_decision_set_fingerprint=child_page[
                "decision_set_fingerprint"
            ],
        ).status
        == "released"
    )


def test_failed_stage_eight_resumes_from_frozen_finalization_without_provider_rerun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline, rubric_provider, embedding_provider = _new_pipeline(tmp_path)
    assert pipeline.run().status == "awaiting_review"
    page = pipeline.layout.list_review_items()
    provider_calls_at_review = (rubric_provider.calls, embedding_provider.calls)
    original_run_stage = pipeline._run_stage
    failed_once = False

    def fail_stage_eight(stage: PipelineStage) -> dict[str, int]:
        nonlocal failed_once
        if stage is PipelineStage.DATASET_SPLITS and not failed_once:
            failed_once = True
            raise RuntimeError("injected Stage 8 failure")
        return original_run_stage(stage)

    monkeypatch.setattr(pipeline, "_run_stage", fail_stage_eight)
    with pytest.raises(RuntimeError, match="injected Stage 8 failure"):
        pipeline.finalize_review(
            reviewer="reviewer-a",
            expected_review_set_fingerprint=page["review_set_fingerprint"],
            expected_decision_set_fingerprint=page["decision_set_fingerprint"],
        )

    failed_state = pipeline.layout.load_state()
    frozen_finalization = pipeline.layout.review_finalizations_path.read_bytes()
    assert failed_state.status == "failed"
    assert failed_state.current_stage == PipelineStage.DATASET_SPLITS.value
    assert len(_read_jsonl(pipeline.layout.review_finalizations_path)) == 1
    assert (rubric_provider.calls, embedding_provider.calls) == provider_calls_at_review

    monkeypatch.setattr(pipeline, "_run_stage", original_run_stage)
    resumed = pipeline.run()

    assert resumed.status == "released"
    assert pipeline.layout.review_finalizations_path.read_bytes() == frozen_finalization
    assert (rubric_provider.calls, embedding_provider.calls) == provider_calls_at_review


def test_stage_seven_completed_state_crash_resumes_to_review_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crash after the Stage 7 receipt cannot enter Stage 8 unreviewed."""
    pipeline, rubric_provider, embedding_provider = _new_pipeline(tmp_path)

    def fail_after_stage_seven(name: str) -> None:
        if name == "after_stage_7_receipt_state_complete":
            raise RuntimeError("injected Stage 7 pause crash")

    monkeypatch.setattr(workspace_module, "_fault_point", fail_after_stage_seven)
    with pytest.raises(RuntimeError, match="injected Stage 7 pause crash"):
        pipeline.run()

    interrupted = pipeline.layout.load_state()
    stage_seven = next(
        item
        for item in interrupted.stages
        if item.stage == PipelineStage.SYNTHETIC_COVERAGE.value
    )
    provider_calls = (rubric_provider.calls, embedding_provider.calls)
    assert interrupted.status == "running"
    assert stage_seven.status == "completed"
    assert stage_seven.receipt_sha256 is not None

    monkeypatch.setattr(workspace_module, "_fault_point", lambda _name: None)
    resumed = pipeline.run()

    assert resumed.status == "awaiting_review"
    assert resumed.current_stage is None
    assert next(
        item
        for item in resumed.stages
        if item.stage == PipelineStage.DATASET_SPLITS.value
    ).status == "pending"
    assert not pipeline.layout.receipt_path(PipelineStage.DATASET_SPLITS).exists()
    assert not pipeline.layout.artifact_path(
        PipelineStage.DATASET_SPLITS,
        "train.jsonl",
    ).exists()
    assert (rubric_provider.calls, embedding_provider.calls) == provider_calls
    assert not pipeline.layout.review_finalizations_path.read_text(
        encoding="utf-8"
    ).strip()


def test_unscoreable_inferred_rubric_counts_one_review_cluster(
    tmp_path: Path,
) -> None:
    """A held rubric contributes once to the Stage 6 review count."""
    pipeline, rubric_provider, _ = _new_pipeline(tmp_path)
    original_generate = rubric_provider.generate_json

    def generate_unscoreable(
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if "clusters" not in payload or "evidence" in payload:
            return original_generate(system_prompt, payload)
        rubric_provider.calls += 1
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "answer the request",
                    "confidence": 0.8,
                    "must": [],
                    "must_not": [],
                    "should": [],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
                for row in payload["clusters"]
            ]
        }

    rubric_provider.generate_json = generate_unscoreable  # type: ignore[method-assign]

    paused = pipeline.run()
    receipt = json.loads(
        pipeline.layout.receipt_path(PipelineStage.LABEL_INFERENCE).read_text(
            encoding="utf-8"
        )
    )

    assert paused.status == "awaiting_review"
    assert receipt["counts"]["review_clusters"] == 1
    assert paused.counts["review_clusters"] == 1
    assert len(
        _read_jsonl(
            pipeline.layout.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "held_inference_outputs.jsonl",
            )
        )
    ) == 1
