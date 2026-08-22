# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Compatibility tests for evaluation-asset extension authority."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.hephaestus.evaluation_assets import lineage_validation
from src.hephaestus.evaluation_assets import workspace as workspace_module
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.split_isolation import (
    parent_assignments_by_group_id,
)
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

_PARENT_RELEASE = {
    "stage_8_receipt_sha256": "1" * 64,
    "released_state_sha256": "2" * 64,
    "source_lineage_sha256": "3" * 64,
    "release_pointer_sha256": "4" * 64,
    "generation_id": "sha256-" + "5" * 64,
    "generation_manifest_sha256": "6" * 64,
    "build_provenance_sha256": "7" * 64,
    "build_fingerprint": "8" * 64,
}


def _feedback_row(
    record_id: str,
    group_id: str,
    *,
    user_input: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": group_id,
        "task_type": "answer",
        "route": "support",
        "user_input": user_input or f"Request {record_id}",
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


def _unlabeled_row(record_id: str) -> dict[str, Any]:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": f"group-{record_id}",
        "task_type": "answer",
        "route": "support",
        "user_input": f"Request {record_id}",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }


def _trusted_case(record_id: str, group_id: str) -> dict[str, Any]:
    return {
        "case_id": f"feedback-{record_id}",
        "task_type": "answer",
        "context": {
            "messages_json": "[]",
            "tool_context_json": "[]",
            "runtime_json": "{}",
        },
        "expected": {"rubric": {"must": ["Answer the request."]}},
        "metadata": {
            "source": "feedback_trace",
            "group_id": group_id,
        },
    }


def _install_pre_v3_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    conflicting_context_assignments: bool = False,
) -> tuple[EvaluationAssetLayout, Path, dict[str, str]]:
    tenants_root = tmp_path / "tenants"
    parent = EvaluationAssetLayout(
        tenants_root,
        "tenant_a",
        "v1",
        repository_base=tmp_path,
    )
    parent.ensure()
    parent.published_datasets.mkdir(parents=True)
    shared_context = "Same model-visible request"
    feedback_rows = [
        _feedback_row(
            "f1",
            "group-f1",
            user_input=(shared_context if conflicting_context_assignments else None),
        ),
        _feedback_row(
            "f2",
            "group-f2",
            user_input=(shared_context if conflicting_context_assignments else None),
        ),
        _feedback_row("f3", "group-f3"),
        _feedback_row("f4", "group-f4"),
    ]
    parent._write_authority_jsonl(parent.historical_feedback_path, feedback_rows)
    parent._write_authority_jsonl(
        parent.historical_unlabeled_path,
        [_unlabeled_row("u1")],
    )
    config = EvaluationAssetConfig(
        tenant_id="tenant_a",
        asset_id="v1",
        rubric_provider="fake",
        rubric_model="fake-rubric",
        embedding_provider="fake",
        embedding_model="fake-embedding",
        cluster_count=1,
        split_seed=17,
    )
    state = PipelineState.new(config, "2026-08-21T12:00:00+00:00")
    state.status = "released"
    for stage in state.stages:
        stage.status = "completed"
        stage.started_at = "2026-08-21T12:00:00+00:00"
        stage.completed_at = "2026-08-21T12:01:00+00:00"
        stage.receipt_sha256 = "9" * 64
    parent._write_authority_json(parent.config_path, config.to_dict())
    parent._write_authority_json(parent.state_path, state.to_dict())
    parent._write_authority_json(
        parent.receipt_path(PipelineStage.PREPARED_INPUTS),
        {
            "schema_version": "fapo-stage-receipt-v2",
            "origin": "native",
        },
    )
    parent._write_authority_json(
        parent.receipt_path(PipelineStage.RUBRIC_EXTRACTION),
        {
            "schema_version": "fapo-stage-receipt-v2",
            "origin": "native",
            "provider_identity": {
                "rubric": {
                    "provider": "fake",
                    "model": "fake-rubric",
                }
            },
        },
    )
    parent._write_authority_json(
        parent.receipt_path(PipelineStage.INTENT_CLUSTERING),
        {
            "schema_version": "fapo-stage-receipt-v2",
            "origin": "native",
            "provider_identity": {
                "embedding": {
                    "provider": "fake",
                    "model": "fake-embedding",
                }
            },
        },
    )
    trusted_cases = {
        row["record_id"]: _trusted_case(row["record_id"], row["group_id"])
        for row in feedback_rows
    }
    parent._write_authority_jsonl(
        parent.artifact_path(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl"),
        trusted_cases.values(),
    )
    parent._write_authority_jsonl(
        parent.artifact_path(PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl"),
        [{"cluster_id": "cluster-1"}],
    )
    parent._write_authority_jsonl(
        parent.artifact_path(PipelineStage.COVERAGE_DECISIONS, "intent_matches.jsonl"),
        [],
    )
    parent._write_authority_jsonl(
        parent.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "inferred_unlabeled_cluster_rubrics.jsonl",
        ),
        [],
    )
    parent._write_authority_jsonl(
        parent.artifact_path(PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl"),
        [],
    )
    parent._write_authority_jsonl(
        parent.artifact_path(PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl"),
        [],
    )
    assignments = {
        "group-f1": "train",
        "group-f2": "test" if conflicting_context_assignments else "validation",
        "group-f3": "test",
        "group-f4": "regression",
    }
    for split in ("train", "validation", "test", "regression_trusted"):
        assignment = "regression" if split == "regression_trusted" else split
        parent._write_authority_jsonl(
            parent.artifact_path(PipelineStage.DATASET_SPLITS, f"{split}.jsonl"),
            [
                trusted_cases[record_id]
                for record_id, case in trusted_cases.items()
                if assignments[str(case["metadata"]["group_id"])] == assignment
            ],
        )

    source_root = tenants_root / "tenant_a" / "source_artifacts"
    source_root.mkdir(parents=True)
    additional = source_root / "additional.jsonl"
    additional.write_text(
        json.dumps(_feedback_row("f5", "group-f5")) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        workspace_module,
        "verify_released_asset",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        workspace_module,
        "released_parent_evidence",
        lambda *_args, **_kwargs: dict(_PARENT_RELEASE),
    )
    return parent, additional, assignments


def _install_unreceipted_current_profile_files(
    parent: EvaluationAssetLayout,
) -> None:
    """Place current-named files beside, but outside, v2 receipt authority."""
    for stage, name in (
        (PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl"),
        (PipelineStage.RUBRIC_EXTRACTION, "candidate_guidelines.jsonl"),
        (PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl"),
        (PipelineStage.RUBRIC_EXTRACTION, "trusted_intents.jsonl"),
    ):
        parent._write_authority_jsonl(parent.artifact_path(stage, name), [])
    extras = (
        (PipelineStage.PREPARED_INPUTS, "trusted_split_plan.jsonl"),
        (PipelineStage.RUBRIC_EXTRACTION, "protected_feedback_evidence.jsonl"),
        (PipelineStage.RUBRIC_EXTRACTION, "protected_candidate_guidelines.jsonl"),
        (PipelineStage.RUBRIC_EXTRACTION, "protected_evaluation_guidelines.jsonl"),
        (PipelineStage.RUBRIC_EXTRACTION, "protected_trusted_cases.jsonl"),
        (PipelineStage.LABEL_INFERENCE, "inference_dependencies.jsonl"),
        (PipelineStage.LABEL_INFERENCE, "held_inference_outputs.jsonl"),
        (PipelineStage.SYNTHETIC_COVERAGE, "synthetic_dependencies.jsonl"),
        (PipelineStage.SYNTHETIC_COVERAGE, "derived_review_items.jsonl"),
        (PipelineStage.SYNTHETIC_COVERAGE, "duplicate_families.jsonl"),
        (PipelineStage.SYNTHETIC_COVERAGE, "held_derived_cases.jsonl"),
    )
    for stage, name in extras:
        rows = [{"unreceipted": True}] if name == "trusted_split_plan.jsonl" else []
        parent._write_authority_jsonl(parent.artifact_path(stage, name), rows)
    parent._write_authority_jsonl(parent.review_decisions_path, [])
    parent._write_authority_jsonl(parent.review_finalizations_path, [])


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_pre_v3_extension_rebuilds_stage_three_and_inherits_parent_assignments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A v2 parent cannot seed globally authored evidence into current Stage 3."""
    parent, additional, assignments = _install_pre_v3_parent(
        tmp_path,
        monkeypatch,
    )
    child = EvaluationAssetLayout(
        parent.tenants_root,
        parent.tenant_id,
        "v2",
        repository_base=tmp_path,
    )

    child.initialize_extension(
        parent,
        additional_feedback=additional,
        additional_unlabeled=None,
        clustering_mode="keep",
    )

    reuse = json.loads(child.reuse_manifest_path.read_text(encoding="utf-8"))
    assert reuse["seeded_incremental_stage"] == {
        "stage": "rubric_extraction",
        "artifacts": [],
        "operation": "rebuild_guidelines_without_parent_seeds",
    }
    assert not any(
        child.artifact_path(PipelineStage.RUBRIC_EXTRACTION, name).exists()
        for name in (
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
            "protected_feedback_evidence.jsonl",
            "protected_candidate_guidelines.jsonl",
            "protected_evaluation_guidelines.jsonl",
            "protected_trusted_cases.jsonl",
        )
    )
    snapshot_names = {
        row["file"] for row in reuse["parent_snapshot"]["artifacts"]
    }
    assert not any(
        name.startswith("parent_feedback_")
        or name.startswith("parent_candidate_")
        or name.startswith("parent_evaluation_")
        or name.startswith("parent_protected_")
        or name.startswith("parent_review_")
        for name in snapshot_names
    )
    assert "parent_trusted_split_plan.jsonl" in snapshot_names
    inherited = parent_assignments_by_group_id(
        _read_jsonl(child.parent_snapshot / "parent_trusted_split_plan.jsonl")
    )
    assert inherited == assignments
    assert child.load_config().split_seed == 17
    evidence = lineage_validation.validate_extension_evidence(
        child,
        require_asset_manifest=False,
    )
    assert evidence.stage_three_seeds == ()


def test_pre_v3_extension_does_not_promote_unreceipted_current_profile_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Current-named files do not upgrade authenticated v2 parent authority."""
    parent, additional, _ = _install_pre_v3_parent(tmp_path, monkeypatch)
    _install_unreceipted_current_profile_files(parent)
    stage_two_receipt = json.loads(
        parent.receipt_path(PipelineStage.PREPARED_INPUTS).read_text(
            encoding="utf-8"
        )
    )
    assert (stage_two_receipt["schema_version"], stage_two_receipt["origin"]) == (
        "fapo-stage-receipt-v2",
        "native",
    )
    parent_before = _tree_bytes(parent.root)
    publication_before = _tree_bytes(parent.published_datasets)
    child = EvaluationAssetLayout(
        parent.tenants_root,
        parent.tenant_id,
        "v2",
        repository_base=tmp_path,
    )

    child.initialize_extension(
        parent,
        additional_feedback=additional,
        additional_unlabeled=None,
        clustering_mode="keep",
    )

    reuse = json.loads(child.reuse_manifest_path.read_text(encoding="utf-8"))
    assert reuse["seeded_incremental_stage"] == {
        "stage": "rubric_extraction",
        "artifacts": [],
        "operation": "rebuild_guidelines_without_parent_seeds",
    }
    assert not any(
        child.artifact_path(PipelineStage.RUBRIC_EXTRACTION, name).exists()
        for name in (
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
            "protected_feedback_evidence.jsonl",
            "protected_candidate_guidelines.jsonl",
            "protected_evaluation_guidelines.jsonl",
            "protected_trusted_cases.jsonl",
        )
    )
    snapshot_names = {
        row["file"] for row in reuse["parent_snapshot"]["artifacts"]
    }
    assert snapshot_names.isdisjoint(
        {
            "parent_protected_feedback_evidence.jsonl",
            "parent_protected_candidate_guidelines.jsonl",
            "parent_protected_evaluation_guidelines.jsonl",
            "parent_protected_trusted_cases.jsonl",
            "parent_inference_dependencies.jsonl",
            "parent_held_inference_outputs.jsonl",
            "parent_synthetic_dependencies.jsonl",
            "parent_derived_review_items.jsonl",
            "parent_duplicate_families.jsonl",
            "parent_held_derived_cases.jsonl",
            "parent_review_decisions.jsonl",
            "parent_review_finalizations.jsonl",
        }
    )
    assert _read_jsonl(
        child.parent_snapshot / "parent_trusted_split_plan.jsonl"
    ) != [{"unreceipted": True}]
    assert _read_jsonl(
        parent.artifact_path(
            PipelineStage.PREPARED_INPUTS,
            "trusted_split_plan.jsonl",
        )
    ) == [{"unreceipted": True}]
    assert _tree_bytes(parent.root) == parent_before
    assert _tree_bytes(parent.published_datasets) == publication_before
    assert parent.load_state().status == "released"


def test_pre_v3_extension_rejects_ambiguous_parent_split_assignments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connected contexts in different historical splits fail before child writes."""
    parent, additional, _ = _install_pre_v3_parent(
        tmp_path,
        monkeypatch,
        conflicting_context_assignments=True,
    )
    child = EvaluationAssetLayout(
        parent.tenants_root,
        parent.tenant_id,
        "v2",
        repository_base=tmp_path,
    )

    with pytest.raises(ValueError, match="parent_split_assignment_conflict"):
        child.initialize_extension(
            parent,
            additional_feedback=additional,
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()


def test_pre_v3_extension_rejects_split_seed_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A compatibility rebuild cannot silently repartition new trusted groups."""
    parent, additional, _ = _install_pre_v3_parent(tmp_path, monkeypatch)
    child = EvaluationAssetLayout(
        parent.tenants_root,
        parent.tenant_id,
        "v2",
        repository_base=tmp_path,
    )

    with pytest.raises(ValueError, match="keep the parent's early split seed"):
        child.initialize_extension(
            parent,
            additional_feedback=additional,
            additional_unlabeled=None,
            clustering_mode="keep",
            config_updates={"split_seed": 99},
        )

    assert not child.root.exists()
