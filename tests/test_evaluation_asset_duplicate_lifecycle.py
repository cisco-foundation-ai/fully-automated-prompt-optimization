# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""End-to-end contracts for exact-duplicate review and publication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from src.hephaestus.datasets.evaluation_assets import SyntheticFilterResult
from src.hephaestus.evaluation_assets import pipeline as pipeline_module
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
)
from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.review import case_content_fingerprint
from src.hephaestus.evaluation_assets.split_isolation import (
    assign_split,
    derive_split_groups,
)

_SHARED_REQUEST = "Return the canonical accepted answer."
_ACCEPTED_REFERENCE = "The canonical accepted answer."
_CONFLICTING_REFERENCE = "A contradictory scoring answer."


class _DuplicateLifecycleEmbeddingProvider:
    provider_name = "duplicate-lifecycle-test"
    model = "duplicate-lifecycle-embedding"

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class _DuplicateLifecycleRubricProvider:
    provider_name = "duplicate-lifecycle-test"
    model = "duplicate-lifecycle-rubric"

    def __init__(self, *, conflicting_truth: bool) -> None:
        self._inferred_reference = (
            _CONFLICTING_REFERENCE
            if conflicting_truth
            else None
        )

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if "records" in payload:
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "return the accepted answer",
                        "confidence": 0.9,
                        "observations": [
                            {
                                "claim": "Return the canonical accepted answer.",
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
            source_record_ids = [
                str(row["record_id"]) for row in payload["evidence"]
            ]
            return {
                "guidelines": [
                    {
                        "intent_label": "return the accepted answer",
                        "description": "Return the canonical accepted answer.",
                        "route": payload["route"],
                        "source_record_ids": source_record_ids,
                        "confidence": 0.9,
                        "criteria": [
                            {
                                "kind": "required",
                                "statement": "Return the canonical accepted answer.",
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
            return {
                "cases": [
                    {
                        "cluster_id": row["cluster_id"],
                        "task_type": "answer",
                        "user_input": _SHARED_REQUEST,
                        "conversation_context": [],
                    }
                    for row in payload["clusters"]
                ]
            }
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "return the accepted answer",
                    "confidence": 0.9,
                    "must": ["Return the canonical accepted answer."],
                    "must_not": [],
                    "should": [],
                    "deterministic_checks": [],
                    "tool_expectations": {"guidelines": []},
                    "reference_output": self._inferred_reference,
                }
                for row in payload["clusters"]
            ]
        }


def _feedback_row(group_id: str) -> dict[str, Any]:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "trusted-copy",
        "group_id": group_id,
        "request_id": "trusted-request",
        "task_type": "answer",
        "route": "answer",
        "user_input": _SHARED_REQUEST,
        "assistant_output": _ACCEPTED_REFERENCE,
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
        "feedback": {
            "polarity": "positive",
            "rationale": "The canonical answer satisfies the request.",
        },
    }


def _train_feedback() -> dict[str, Any]:
    for ordinal in range(10_000):
        row = _feedback_row(f"trusted-original-group-{ordinal}")
        split_group_id = derive_split_groups([row])[0].split_group_id
        if assign_split(split_group_id, split_seed=42) == "train":
            return row
    raise AssertionError("could not construct train feedback")


def _unlabeled_row(
    record_id: str,
    group_id: str,
    user_input: str,
) -> dict[str, Any]:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": group_id,
        "request_id": f"request-{record_id}",
        "task_type": "answer",
        "route": "answer",
        "user_input": user_input,
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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _accept_exact_synthetic_candidates(
    candidates: Sequence[dict[str, Any]],
    existing_cases: Sequence[dict[str, Any]] | None = None,
    duplicate_threshold: float = 0.95,
) -> SyntheticFilterResult:
    """Expose Stage 7 duplicate handling after the upstream filter boundary."""
    del existing_cases, duplicate_threshold
    return SyntheticFilterResult(
        accepted=[dict(candidate) for candidate in candidates],
        rejected=[],
        issues=[],
    )


def _new_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    conflicting_truth: bool,
) -> EvaluationAssetPipeline:
    tenants_root = tmp_path / "tenants"
    source_root = tenants_root / "tenant_a" / "source_artifacts"
    source_root.mkdir(parents=True)
    feedback_path = source_root / "feedback.jsonl"
    unlabeled_path = source_root / "unlabeled.jsonl"
    _write_jsonl(feedback_path, [_train_feedback()])
    _write_jsonl(
        unlabeled_path,
        [
            _unlabeled_row(
                "inferred-copy",
                "inferred-original-group",
                _SHARED_REQUEST,
            ),
            _unlabeled_row(
                "pending-only",
                "pending-original-group",
                "Return an independently pending answer.",
            ),
            _unlabeled_row(
                "rejected-only",
                "rejected-original-group",
                "Return an independently rejected answer.",
            ),
        ],
    )
    provider = _DuplicateLifecycleRubricProvider(
        conflicting_truth=conflicting_truth,
    )
    monkeypatch.setattr(
        pipeline_module,
        "filter_synthetic_cases",
        _accept_exact_synthetic_candidates,
    )
    return EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id="v1",
            cluster_count=1,
            rubric_provider=provider.provider_name,
            rubric_model=provider.model,
            embedding_provider=_DuplicateLifecycleEmbeddingProvider.provider_name,
            embedding_model=_DuplicateLifecycleEmbeddingProvider.model,
            synthetic_coverage_enabled=True,
            synthetic_cases_per_cluster=1,
        ),
        feedback_path,
        unlabeled_path,
        rubric_provider=provider,
        embedding_provider=_DuplicateLifecycleEmbeddingProvider(),
        repository_base=tmp_path,
    )


def _duplicate_family(
    pipeline: EvaluationAssetPipeline,
) -> dict[str, Any]:
    families = _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "duplicate_families.jsonl",
        )
    )
    synthetic_id = _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_cases.jsonl",
        )
    )[0]["case_id"]
    expected_ids = {
        "feedback-trusted-copy",
        "inferred-inferred-copy",
        synthetic_id,
    }
    matches = [
        family
        for family in families
        if {member["case_id"] for member in family["members"]} == expected_ids
    ]
    assert len(matches) == 1, "exact context copies did not form one family"
    return matches[0]


def _primary_split_rows(
    pipeline: EvaluationAssetPipeline,
) -> dict[str, list[dict[str, Any]]]:
    return {
        split: _read_jsonl(
            pipeline.layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
        )
        for split in ("train", "validation", "test", "regression_trusted")
    }


def _assert_review_manifests(
    pipeline: EvaluationAssetPipeline,
    *,
    review_page: Mapping[str, Any],
    expected_statuses: Mapping[str, str],
    expected_counts: Mapping[str, int],
) -> None:
    stage_manifest = _read_json(
        pipeline.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "dataset_manifest.json",
        )
    )
    root_manifest = _read_json(pipeline.layout.manifest_path)
    finalizations = _read_jsonl(pipeline.layout.review_finalizations_path)
    review_snapshot = _read_json(
        pipeline.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "review_snapshot.json",
        )
    )

    assert len(finalizations) == 1
    finalization = finalizations[0]
    assert review_snapshot == finalization
    assert root_manifest == stage_manifest
    assert finalization["counts"] == dict(expected_counts)
    assert {
        row["case_id"]: row["status"] for row in finalization["items"]
    } == dict(expected_statuses)

    fingerprints_by_case = {
        row["case_id"]: row["fingerprint"]
        for row in [*review_page["items"], *review_page["held"]]
    }
    trusted_cases = [
        *_read_jsonl(
            pipeline.layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "trusted_cases.jsonl",
            )
        ),
        *_read_jsonl(
            pipeline.layout.artifact_path(
                PipelineStage.RUBRIC_EXTRACTION,
                "protected_trusted_cases.jsonl",
            )
        ),
    ]
    held_ids = {row["case_id"] for row in review_page["held"]}
    expected_inventory = {
        "trusted": sorted(
            [
                {
                    "case_id": case["case_id"],
                    "fingerprint": case_content_fingerprint(case),
                }
                for case in trusted_cases
                if case["case_id"] not in held_ids
            ],
            key=lambda row: (row["case_id"], row["fingerprint"]),
        ),
        **{
            status: sorted(
                [
                    {
                        "case_id": case_id,
                        "fingerprint": fingerprints_by_case[case_id],
                    }
                    for case_id, case_status in expected_statuses.items()
                    if case_status == status
                ],
                key=lambda row: (row["case_id"], row["fingerprint"]),
            )
            for status in ("approved", "pending", "rejected")
        },
        "held": [
            {
                "case_id": row["case_id"],
                "fingerprint": row["fingerprint"],
                "reason": row["reason"],
            }
            for row in review_page["held"]
        ],
    }
    expected_review = {
        "review_set_fingerprint": review_page["review_set_fingerprint"],
        "finalization_id": finalization["finalization_id"],
        "stage7_receipt_sha256": review_page["stage7_receipt_sha256"],
        "counts": dict(expected_counts),
        "fingerprints": expected_inventory,
    }
    assert stage_manifest["review"] == expected_review


def test_exact_context_copies_share_one_approved_published_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch Stage 7 grouping that considers only original source groups."""
    pipeline = _new_pipeline(
        tmp_path,
        monkeypatch,
        conflicting_truth=False,
    )

    assert pipeline.run().status == "awaiting_review"
    review_page = pipeline.layout.list_review_items()
    family = _duplicate_family(pipeline)
    member_ids = {member["case_id"] for member in family["members"]}
    synthetic_id = next(
        case_id for case_id in member_ids if case_id.startswith("synthetic-")
    )

    assert family["hold_reasons"] == []
    assert family["assigned_early_split"] == "train"
    assert len(family["truth_fingerprints"]) == 1
    assert len({member["context_fingerprint"] for member in family["members"]}) == 1
    assert len({member["group_id"] for member in family["members"]}) == 3
    assert review_page["counts"] == {
        "trusted": 1,
        "approved": 0,
        "pending": 4,
        "rejected": 0,
        "held": 0,
        "total": 5,
    }
    items_by_id = {row["case_id"]: row for row in review_page["items"]}
    decisions: dict[str, dict[str, Any]] = {}
    for case_id in ("inferred-inferred-copy", synthetic_id):
        item = items_by_id[case_id]
        decisions[case_id] = pipeline.layout.decide_review(
            case_id,
            item["fingerprint"],
            "approved",
            reviewer="reviewer-a",
            expected_review_set_fingerprint=review_page[
                "review_set_fingerprint"
            ],
        )
    rejected = items_by_id["inferred-rejected-only"]
    pipeline.layout.decide_review(
        rejected["case_id"],
        rejected["fingerprint"],
        "rejected",
        reviewer="reviewer-a",
        expected_review_set_fingerprint=review_page[
            "review_set_fingerprint"
        ],
    )
    review_page = pipeline.layout.list_review_items()

    assert (
        pipeline.finalize_review(
            reviewer="reviewer-a",
            expected_review_set_fingerprint=review_page[
                "review_set_fingerprint"
            ],
            expected_decision_set_fingerprint=review_page[
                "decision_set_fingerprint"
            ],
        ).status
        == "released"
    )

    split_rows = _primary_split_rows(pipeline)
    published_locations = {
        split
        for split, rows in split_rows.items()
        if member_ids & {row["case_id"] for row in rows}
    }
    published_family = [
        row
        for rows in split_rows.values()
        for row in rows
        if row["case_id"] in member_ids
    ]
    assert published_locations == {"train"}
    assert {row["case_id"] for row in published_family} == member_ids
    assert {
        split for split, rows in split_rows.items() if rows
    } == {"train"}
    assert {
        row["case_id"] for rows in split_rows.values() for row in rows
    } == member_ids
    assert {row["metadata"]["split_group_id"] for row in published_family} == {
        family["split_group_id"]
    }
    assert {
        row["metadata"]["decision_id"]
        for row in published_family
        if row["case_id"] != "feedback-trusted-copy"
    } == {row["decision_id"] for row in decisions.values()}
    assert "inferred-pending-only" not in {
        row["case_id"] for rows in split_rows.values() for row in rows
    }
    assert "inferred-rejected-only" not in {
        row["case_id"] for rows in split_rows.values() for row in rows
    }
    _assert_review_manifests(
        pipeline,
        review_page=review_page,
        expected_statuses={
            "inferred-inferred-copy": "approved",
            "inferred-pending-only": "pending",
            "inferred-rejected-only": "rejected",
            synthetic_id: "approved",
        },
        expected_counts={
            "trusted": 1,
            "approved": 2,
            "pending": 1,
            "rejected": 1,
            "held": 0,
        },
    )


def test_conflicting_truth_holds_and_excludes_the_complete_exact_family(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch conflict handling that prefers one trust tier or one family member."""
    pipeline = _new_pipeline(
        tmp_path,
        monkeypatch,
        conflicting_truth=True,
    )

    assert pipeline.run().status == "awaiting_review"
    review_page = pipeline.layout.list_review_items()
    family = _duplicate_family(pipeline)
    member_ids = {member["case_id"] for member in family["members"]}

    assert family["hold_reasons"] == ["conflicting_expected_truth"]
    assert len(family["truth_fingerprints"]) == 2
    assert {row["case_id"] for row in review_page["held"]} == member_ids
    assert {row["hold_reason"] for row in review_page["held"]} == {
        "conflicting_expected_truth"
    }
    assert review_page["counts"] == {
        "trusted": 0,
        "approved": 0,
        "pending": 2,
        "rejected": 0,
        "held": 3,
        "total": 5,
    }
    items_by_id = {row["case_id"]: row for row in review_page["items"]}
    rejected = items_by_id["inferred-rejected-only"]
    pipeline.layout.decide_review(
        rejected["case_id"],
        rejected["fingerprint"],
        "rejected",
        reviewer="reviewer-a",
        expected_review_set_fingerprint=review_page[
            "review_set_fingerprint"
        ],
    )
    review_page = pipeline.layout.list_review_items()

    assert (
        pipeline.finalize_review(
            reviewer="reviewer-a",
            expected_review_set_fingerprint=review_page[
                "review_set_fingerprint"
            ],
            expected_decision_set_fingerprint=review_page[
                "decision_set_fingerprint"
            ],
        ).status
        == "released"
    )

    split_rows = _primary_split_rows(pipeline)
    assert member_ids.isdisjoint(
        row["case_id"] for rows in split_rows.values() for row in rows
    )
    triage_rows = _read_jsonl(
        pipeline.layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "triage_hold.jsonl",
        )
    )
    assert {row["case_id"] for row in triage_rows} == member_ids
    assert {row["metadata"]["hold_reason"] for row in triage_rows} == {
        "conflicting_expected_truth"
    }
    _assert_review_manifests(
        pipeline,
        review_page=review_page,
        expected_statuses={
            "inferred-pending-only": "pending",
            "inferred-rejected-only": "rejected",
        },
        expected_counts={
            "trusted": 0,
            "approved": 0,
            "pending": 1,
            "rejected": 1,
            "held": 3,
        },
    )
