# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import multiprocessing
import shutil
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from src.hephaestus import artifact_io
from src.hephaestus.evaluation_assets import durability as durability_module
from src.hephaestus.evaluation_assets import workspace as workspace_module
from src.hephaestus.evaluation_assets.durability import (
    LEGACY_UNAVAILABLE_PROVENANCE,
    STAGE_SPECIFICATIONS,
    EvaluationAssetBusyError,
    EvaluationAssetImmutableError,
    EvaluationAssetIntegrityError,
    EvaluationAssetLegacyError,
    canonical_sha256,
    file_sha256,
    released_parent_evidence,
    verify_released_asset,
)
from src.hephaestus.evaluation_assets.models import (
    STATE_SCHEMA_VERSION,
    TOP_LEVEL_STATUSES,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.service import EvaluationAssetRunManager
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


class _NeverCalledRubricProvider:
    model = "never-called-rubric"

    def __init__(self) -> None:
        self.calls = 0

    def generate_json(self, system_prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        raise AssertionError("busy pipeline reached the rubric provider")


class _NeverCalledEmbeddingProvider:
    model = "never-called-embedding"

    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        raise AssertionError("busy pipeline reached the embedding provider")


class _SuccessfulEmbeddingProvider:
    model = "fake-embedding"

    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[1.0, 0.0] for _ in texts]


class _SuccessfulRubricProvider:
    model = "fake-rubric"

    def __init__(self) -> None:
        self.calls = 0

    def generate_json(
        self,
        system_prompt: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls += 1
        if "records" in payload:
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "answer request",
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
            return {
                "guidelines": [
                    {
                        "intent_label": "answer request",
                        "description": "Answer requests within their stated scope.",
                        "route": payload["route"],
                        "source_record_ids": [
                            row["record_id"] for row in payload["evidence"]
                        ],
                        "confidence": 0.9,
                        "criteria": [
                            {
                                "kind": "required",
                                "statement": "Answer the stated request.",
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
        if "synthetic evaluation input" in system_prompt:
            return {"cases": []}
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "answer request",
                    "confidence": 0.8,
                    "must": ["Answer the stated request."],
                    "must_not": [],
                    "should": [],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
                for row in payload["clusters"]
            ]
        }


def _hold_asset_lock(
    tenants_root: str,
    tenant_id: str,
    asset_id: str,
    ready: Any,
    release: Any,
) -> None:
    layout = EvaluationAssetLayout(Path(tenants_root), tenant_id, asset_id)
    with layout.asset_lock():
        ready.set()
        if not release.wait(10):
            raise RuntimeError("test lock holder timed out")


def test_state_round_trips_all_v2_lifecycle_statuses() -> None:
    """V2 accepts exactly the six lifecycle states and rejects completed."""
    timestamp = "2026-08-19T00:00:00+00:00"
    config = EvaluationAssetConfig(tenant_id="tenant_a")

    assert TOP_LEVEL_STATUSES == (
        "draft",
        "queued",
        "running",
        "awaiting_review",
        "released",
        "failed",
    )
    for status in TOP_LEVEL_STATUSES:
        state = PipelineState.new(config, timestamp)
        state.status = status
        restored = PipelineState.from_dict(state.to_dict())
        assert restored.schema_version == STATE_SCHEMA_VERSION
        assert restored.status == status

    invalid = PipelineState.new(config, timestamp).to_dict()
    invalid["status"] = "completed"
    with pytest.raises(ValueError, match="Unsupported evaluation asset status"):
        PipelineState.from_dict(invalid)


def test_pre_v2_completed_remains_an_explicit_legacy_sentinel() -> None:
    """Loading legacy completed never silently maps it to released."""
    raw = {
        "tenant_id": "tenant_a",
        "asset_id": "v1",
        "status": "completed",
        "created_at": "2026-08-19T00:00:00+00:00",
        "updated_at": "2026-08-19T01:00:00+00:00",
        "stages": [],
    }

    state = PipelineState.from_dict(raw)

    assert state.schema_version != STATE_SCHEMA_VERSION
    assert state.status == "completed"
    assert state.legacy_completed is True
    assert state.to_dict()["status"] == "completed"


def test_completed_is_rejected_for_an_explicit_future_state_schema() -> None:
    """Only the known pre-v2 representation may carry the legacy sentinel."""
    raw = {
        "schema_version": "fapo-evaluation-asset-state-v3",
        "tenant_id": "tenant_a",
        "asset_id": "v1",
        "status": "completed",
        "stages": [],
    }

    with pytest.raises(ValueError, match="Unsupported evaluation asset status"):
        PipelineState.from_dict(raw)


def test_new_pipeline_state_starts_draft() -> None:
    """Library and CLI initialization persist an inert draft workspace."""
    state = PipelineState.new(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        "2026-08-19T00:00:00+00:00",
    )

    assert state.status == "draft"
    assert state.schema_version == STATE_SCHEMA_VERSION
    assert state.mutation_sequence == 0


def test_filelock_is_a_bounded_core_dependency() -> None:
    """Every installed core caller receives the cross-process lock library."""
    pyproject = Path(__file__).parents[1] / "pyproject.toml"

    assert '"filelock>=3.13,<4"' in pyproject.read_text(encoding="utf-8")


def test_atomic_control_write_syncs_file_and_parent_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prepared journal rename is durable in file and directory metadata."""
    if artifact_io.os.name == "nt":
        pytest.skip("directory fsync is a POSIX durability primitive")
    synced: list[int] = []
    real_fsync = artifact_io.os.fsync

    def record_fsync(file_descriptor: int) -> None:
        synced.append(file_descriptor)
        real_fsync(file_descriptor)

    monkeypatch.setattr(artifact_io.os, "fsync", record_fsync)

    artifact_io.atomic_append_jsonl(
        tmp_path / "recovery_journal.jsonl",
        {"phase": "prepared"},
    )

    assert len(synced) >= 2


def test_spawned_process_holds_same_deterministic_asset_lock(tmp_path: Path) -> None:
    """A spawn-context holder excludes a direct library run without mutations."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            embedding_provider="tfidf",
            embedding_model="tfidf",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
    )
    rubric = _NeverCalledRubricProvider()
    embedding = _NeverCalledEmbeddingProvider()
    pipeline = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    before = _tree_bytes(layout.root)
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        with pytest.raises(
            EvaluationAssetBusyError,
            match="tenant_a/v1.*already being modified",
        ) as exc_info:
            pipeline.run()
        assert str(tmp_path) not in str(exc_info.value)
        assert layout.lock_path == (
            tenants_root.resolve()
            / "tenant_a"
            / "evaluation_assets"
            / ".locks"
            / "v1.lock"
        )
        assert rubric.calls == 0
        assert embedding.calls == 0
        assert _tree_bytes(layout.root) == before
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_spawned_lock_excludes_initialization_before_child_root_exists(
    tmp_path: Path,
) -> None:
    """Creation races use the collection-level lock before creating the asset root."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        with pytest.raises(EvaluationAssetBusyError):
            layout.initialize(
                EvaluationAssetConfig(tenant_id="tenant_a"),
                feedback,
                unlabeled,
            )
        assert not layout.root.exists()
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_revision_uses_same_asset_lock_and_preserves_bytes_when_busy(
    tmp_path: Path,
) -> None:
    """Direct config revision cannot bypass a lock owned by another process."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
    )
    before = _tree_bytes(layout.root)
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        with pytest.raises(EvaluationAssetBusyError):
            layout.revise_config({"cluster_count": 2})
        assert _tree_bytes(layout.root) == before
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_cli_and_service_resume_surface_library_lock_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI and service callers expose the core busy error without audit writes."""
    from src.hephaestus.cli import main

    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            embedding_provider="tfidf",
            embedding_model="tfidf",
            cluster_count=1,
        ),
        feedback,
        unlabeled,
    )
    before = _tree_bytes(layout.root)
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    process = context.Process(
        target=_hold_asset_lock,
        args=(str(tenants_root), "tenant_a", "v1", ready, release),
    )
    process.start()
    try:
        assert ready.wait(5)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "hephaestus",
                "assets",
                "run",
                "--tenant",
                "tenant_a",
                "--asset-id",
                "v1",
                "--tenants-root",
                str(tenants_root),
            ],
        )
        with pytest.raises(EvaluationAssetBusyError):
            main()
        assert _tree_bytes(layout.root) == before

        manager = EvaluationAssetRunManager(tenants_root)
        with pytest.raises(EvaluationAssetBusyError):
            manager.resume("tenant_a", "v1")
        assert _tree_bytes(layout.root) == before
    finally:
        release.set()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    assert process.exitcode == 0


def test_service_start_persists_queued_before_returning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service never returns a newly accepted job in draft state."""
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    entered = threading.Event()
    release = threading.Event()

    def pause_first_stage(
        pipeline: EvaluationAssetPipeline,
        stage: Any,
    ) -> dict[str, int]:
        entered.set()
        if not release.wait(5):
            raise RuntimeError("test stage timed out")
        raise RuntimeError("stop after service lifecycle assertion")

    monkeypatch.setattr(EvaluationAssetPipeline, "_run_stage", pause_first_stage)
    manager = EvaluationAssetRunManager(tenants_root)
    try:
        response = manager.start(
            EvaluationAssetConfig(
                tenant_id="tenant_a",
                embedding_provider="tfidf",
                embedding_model="tfidf",
                cluster_count=1,
            ),
            feedback,
            unlabeled,
        )
        assert entered.wait(5)
        assert response["status"] in {"queued", "running"}
        assert response["status"] != "draft"
        persisted = EvaluationAssetLayout(
            tenants_root,
            "tenant_a",
            "v1",
        ).load_state()
        assert persisted.status in {"queued", "running"}
    finally:
        release.set()


def test_stage_specification_exhaustively_declares_required_artifacts() -> None:
    """One declarative map covers every current stage-owned release artifact."""
    expected = {
        PipelineStage.RAW_INPUTS: {"input_manifest.json"},
        PipelineStage.PREPARED_INPUTS: {
            "normalized_feedback.jsonl",
            "intent_records.jsonl",
        },
        PipelineStage.RUBRIC_EXTRACTION: {
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
        },
        PipelineStage.INTENT_CLUSTERING: {"intent_inventory.jsonl"},
        PipelineStage.COVERAGE_DECISIONS: {
            "intent_matches.jsonl",
            "coverage_report.md",
            "review_queue/labeling_queue.jsonl",
        },
        PipelineStage.LABEL_INFERENCE: {
            "inferred_unlabeled_cluster_rubrics.jsonl",
            "inferred_unlabeled_labels.jsonl",
            "missing_labeled_feedback_clusters.jsonl",
            "missing_labeled_feedback_report.md",
            "inferred_cases.jsonl",
        },
        PipelineStage.SYNTHETIC_COVERAGE: {
            "synthetic_candidates.jsonl",
            "rejected_synthetic.jsonl",
            "synthetic_filter_issues.jsonl",
            "synthetic_cases.jsonl",
        },
        PipelineStage.DATASET_SPLITS: {
            "train_trusted.jsonl",
            "train_inferred.jsonl",
            "train_synthetic.jsonl",
            "train.jsonl",
            "validation_trusted.jsonl",
            "validation_inferred.jsonl",
            "validation_synthetic.jsonl",
            "validation.jsonl",
            "test_trusted.jsonl",
            "test_inferred.jsonl",
            "test_synthetic.jsonl",
            "test.jsonl",
            "regression_trusted.jsonl",
            "triage_hold.jsonl",
            "dataset_manifest.json",
        },
    }

    assert set(STAGE_SPECIFICATIONS) == set(PipelineStage)
    for stage, required_outputs in expected.items():
        assert set(STAGE_SPECIFICATIONS[stage].required_outputs) == required_outputs
    assert STAGE_SPECIFICATIONS[PipelineStage.DATASET_SPLITS].required_asset_outputs == (
        "asset_manifest.json",
    )
    assert STAGE_SPECIFICATIONS[PipelineStage.DATASET_SPLITS].required_catalog_outputs == (
        "train.jsonl",
        "validation.jsonl",
        "test.jsonl",
        "regression_trusted.jsonl",
    )


def test_pipeline_writes_receipt_commit_markers_and_releases(tmp_path: Path) -> None:
    """A new build releases only after all stage receipts exist and are referenced."""
    pipeline, rubric, embedding = _create_pipeline(tmp_path)

    state = pipeline.run()

    assert state.status == "released"
    assert state.schema_version == STATE_SCHEMA_VERSION
    assert all(stage.status == "completed" for stage in state.stages)
    assert rubric.calls > 0
    assert embedding.calls > 0
    for index, stage in enumerate(PipelineStage, start=1):
        stage_state = next(item for item in state.stages if item.stage == stage.value)
        receipt_path = pipeline.layout.receipt_path(stage)
        assert receipt_path.name == f"{index:02d}_{stage.value}.json"
        assert receipt_path.is_file()
        assert stage_state.receipt_sha256 == file_sha256(receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["schema_version"] == "fapo-stage-receipt-v1"
        assert receipt["stage"] == stage.value
        assert receipt["stage_index"] == index
        assert receipt["resolved_config_sha256"]
        assert receipt["dependency_config_sha256"]
        assert receipt["prompt_set_sha256"]
        assert receipt["provider_identity_sha256"]
        assert receipt["provider_calls_sha256"]
        assert receipt["code_sha256"]
        assert {item["path"] for item in receipt["outputs"]} >= {
            pipeline.layout.artifact_path(stage, name)
            .relative_to(pipeline.layout.root)
            .as_posix()
            for name in STAGE_SPECIFICATIONS[stage].required_outputs
        }


_STAGE_MUTATION_TARGETS = {
    PipelineStage.RAW_INPUTS: "input_manifest.json",
    PipelineStage.PREPARED_INPUTS: "normalized_feedback.jsonl",
    PipelineStage.RUBRIC_EXTRACTION: "feedback_evidence.jsonl",
    PipelineStage.INTENT_CLUSTERING: "intent_inventory.jsonl",
    PipelineStage.COVERAGE_DECISIONS: "coverage_report.md",
    PipelineStage.LABEL_INFERENCE: "inferred_cases.jsonl",
    PipelineStage.SYNTHETIC_COVERAGE: "synthetic_cases.jsonl",
    PipelineStage.DATASET_SPLITS: "train.jsonl",
}


@pytest.mark.parametrize("stage", list(PipelineStage))
def test_mutable_resume_rebuilds_from_first_missing_output(
    tmp_path: Path,
    stage: PipelineStage,
) -> None:
    """A missing committed output invalidates that mutable stage and its suffix."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    state.status = "failed"
    layout.save_state(state)
    boundary = list(PipelineStage).index(stage)
    prefix_receipts = {
        prior: layout.receipt_path(prior).read_bytes()
        for prior in list(PipelineStage)[:boundary]
    }
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    target.unlink()
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()

    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    ).run()

    assert resumed.status == "released"
    assert target.is_file()
    assert all(
        layout.receipt_path(prior).read_bytes() == receipt_bytes
        for prior, receipt_bytes in prefix_receipts.items()
    )


@pytest.mark.parametrize("stage", list(PipelineStage))
def test_mutable_resume_rebuilds_from_first_corrupt_output(
    tmp_path: Path,
    stage: PipelineStage,
) -> None:
    """A parseable byte change still invalidates a mutable receipt boundary."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    state.status = "failed"
    layout.save_state(state)
    boundary = list(PipelineStage).index(stage)
    prefix_receipts = {
        prior: layout.receipt_path(prior).read_bytes()
        for prior in list(PipelineStage)[:boundary]
    }
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    corrupt_bytes = target.read_bytes() + b" \n"
    target.write_bytes(corrupt_bytes)

    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    assert resumed.status == "released"
    assert target.read_bytes() != corrupt_bytes
    assert all(
        layout.receipt_path(prior).read_bytes() == receipt_bytes
        for prior, receipt_bytes in prefix_receipts.items()
    )


@pytest.mark.parametrize("stage", list(PipelineStage))
@pytest.mark.parametrize("mutation", ["missing", "corrupt"])
def test_released_asset_fails_closed_for_stage_output_damage(
    tmp_path: Path,
    stage: PipelineStage,
    mutation: str,
) -> None:
    """Released verification detects every stage boundary without repair."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    if mutation == "missing":
        target.unlink()
    else:
        target.write_bytes(target.read_bytes() + b" \n")
    before = _authority_bytes(layout)
    rubric = _NeverCalledRubricProvider()
    embedding = _NeverCalledEmbeddingProvider()

    with pytest.raises(EvaluationAssetIntegrityError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()

    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


def test_released_revision_and_run_fail_before_any_mutation(tmp_path: Path) -> None:
    """Changed, unchanged, and run requests cannot write a released asset."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    before = _authority_bytes(layout)

    for updates in ({}, {"match_threshold": 0.2}):
        with pytest.raises(
            EvaluationAssetImmutableError,
            match=r"assets extend --parent-asset-id v1 --asset-id <new-id>",
        ):
            layout.revise_config(updates)
        assert _authority_bytes(layout) == before

    rubric = _NeverCalledRubricProvider()
    embedding = _NeverCalledEmbeddingProvider()
    with pytest.raises(EvaluationAssetImmutableError):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=rubric,
            embedding_provider=embedding,
        ).run()
    assert _authority_bytes(layout) == before
    assert rubric.calls == 0
    assert embedding.calls == 0


def test_legacy_completed_rejects_revision_before_any_mutation(tmp_path: Path) -> None:
    """Adoption is the legacy completion's only permitted mutation path."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    before = _authority_bytes(layout)

    for updates in ({}, {"match_threshold": 0.2}):
        with pytest.raises(EvaluationAssetLegacyError, match="Run assets adopt"):
            layout.revise_config(updates)
        assert _authority_bytes(layout) == before


def test_downstream_revision_keeps_projected_receipt_prefix_valid(
    tmp_path: Path,
) -> None:
    """Audit-only full config changes do not invalidate unrelated stages."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    state.status = "failed"
    layout.save_state(state)
    prefix = {
        stage: layout.receipt_path(stage).read_bytes()
        for stage in list(PipelineStage)[:7]
    }

    revision = layout.revise_config({"split_seed": 73})
    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=_NeverCalledRubricProvider(),
        embedding_provider=_NeverCalledEmbeddingProvider(),
    ).run()

    assert revision["invalidated_from_stage"] == "dataset_splits"
    assert resumed.status == "released"
    assert all(
        layout.receipt_path(stage).read_bytes() == receipt
        for stage, receipt in prefix.items()
    )


def test_released_verification_does_not_require_current_code_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Historical code hashes remain evidence after the checkout changes."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    released = pipeline.run()
    monkeypatch.setattr(
        durability_module,
        "_code_identity",
        lambda: {"fingerprint": "new-code", "members": []},
    )

    verify_released_asset(pipeline.layout, released)
    with pytest.raises(EvaluationAssetImmutableError):
        EvaluationAssetPipeline(
            pipeline.layout,
            rubric_provider=_NeverCalledRubricProvider(),
            embedding_provider=_NeverCalledEmbeddingProvider(),
        ).run()


def test_missing_raw_snapshot_is_not_rebuildable(tmp_path: Path) -> None:
    """Mutable recovery never fabricates a missing immutable raw snapshot."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    state.status = "failed"
    layout.save_state(state)
    layout.feedback_path.unlink()
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetIntegrityError, match="raw input snapshot"):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_NeverCalledRubricProvider(),
            embedding_provider=_NeverCalledEmbeddingProvider(),
        ).run()

    assert _authority_bytes(layout) == before


@pytest.mark.parametrize(
    "fault_name",
    [
        "after_prepared_journal",
        "after_config_replace",
        "after_state_replace",
        "after_history_append",
        "after_event_append",
        "before_cleanup",
    ],
)
def test_revision_recovery_rolls_forward_after_each_interruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Every interrupted revision recovers one target state and one audit row."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    state.status = "failed"
    layout.save_state(state)
    prefix_receipts = {
        stage: layout.receipt_path(stage).read_bytes()
        for stage in list(PipelineStage)[:4]
    }
    stale_stage_five = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )

    def inject_fault(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault, match=fault_name):
        layout.revise_config({"match_threshold": 0.2})

    journal_after_fault = _read_jsonl(layout.recovery_journal_path)
    prepared = [row for row in journal_after_fault if row["phase"] == "prepared"]
    assert len(prepared) == 1
    operation_id = prepared[0]["operation_id"]
    if fault_name == "before_cleanup":
        interrupted_state = layout.load_state()
        assert interrupted_state.stages[4].status == "pending"
        assert interrupted_state.stages[4].receipt_sha256 is None
        assert stale_stage_five.is_file()

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    recovered = layout.recover()

    assert recovered == [operation_id]
    assert layout.load_config().match_threshold == 0.2
    recovered_state = layout.load_state()
    assert recovered_state.status == "queued"
    assert recovered_state.current_stage == PipelineStage.COVERAGE_DECISIONS.value
    assert recovered_state.mutation_sequence == state.mutation_sequence + 1
    assert recovered_state.last_operation_id == operation_id
    assert [item.status for item in recovered_state.stages[:4]] == [
        "completed"
    ] * 4
    assert [item.status for item in recovered_state.stages[4:]] == ["pending"] * 4
    assert all(
        layout.receipt_path(stage).read_bytes() == receipt_bytes
        for stage, receipt_bytes in prefix_receipts.items()
    )
    assert not stale_stage_five.exists()
    history = [
        row
        for row in _read_jsonl(layout.config_history_path)
        if row.get("operation_id") == operation_id
    ]
    events = [
        row
        for row in _read_jsonl(layout.events_path)
        if row.get("operation_id") == operation_id
    ]
    assert len(history) == 1
    assert len(events) == 1
    phases = [
        row["phase"]
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["operation_id"] == operation_id
    ]
    assert phases == ["prepared", "committed"]


def test_revision_prepares_journal_before_changing_control_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The prepared WAL record is durable while prior control bytes remain exact."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    state.status = "failed"
    layout.save_state(state)
    before = {
        path.name: path.read_bytes()
        for path in (
            layout.config_path,
            layout.state_path,
            layout.config_history_path,
            layout.events_path,
        )
    }

    def inject_fault(name: str) -> None:
        if name == "after_prepared_journal":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault):
        layout.revise_config({"match_threshold": 0.2})

    assert {
        path.name: path.read_bytes()
        for path in (
            layout.config_path,
            layout.state_path,
            layout.config_history_path,
            layout.events_path,
        )
    } == before
    journal = _read_jsonl(layout.recovery_journal_path)
    assert len(journal) == 1
    assert journal[0]["kind"] == "configuration_revision"
    assert journal[0]["phase"] == "prepared"


@pytest.mark.parametrize(
    "fault_name",
    [
        "after_prepared_journal",
        "after_state_replace",
        "after_event_append",
        "before_cleanup",
    ],
)
def test_checkpoint_rebuild_recovery_marks_stale_suffix_nonauthoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_name: str,
) -> None:
    """Interrupted receipt repair rolls forward before a resumed stage runs."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    state = layout.load_state()
    state.status = "failed"
    layout.save_state(state)
    target = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )
    target.write_bytes(target.read_bytes() + b" \n")
    prior_state = layout.state_path.read_bytes()

    def inject_fault(name: str) -> None:
        if name == fault_name:
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault, match=fault_name):
        EvaluationAssetPipeline(
            layout,
            rubric_provider=_SuccessfulRubricProvider(),
            embedding_provider=_SuccessfulEmbeddingProvider(),
        ).run()

    journal = _read_jsonl(layout.recovery_journal_path)
    prepared = [
        row
        for row in journal
        if row.get("kind") == "checkpoint_rebuild" and row["phase"] == "prepared"
    ]
    assert len(prepared) == 1
    operation_id = prepared[0]["operation_id"]
    if fault_name == "after_prepared_journal":
        assert layout.state_path.read_bytes() == prior_state
    else:
        interrupted = layout.load_state()
        assert interrupted.status == "queued"
        assert interrupted.stages[4].status == "pending"
        assert interrupted.stages[4].receipt_sha256 is None
    if fault_name == "before_cleanup":
        assert target.is_file()

    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)
    resumed = EvaluationAssetPipeline(
        layout,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    assert resumed.status == "released"
    phases = [
        row["phase"]
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["operation_id"] == operation_id
    ]
    assert phases == ["prepared", "committed"]
    rebuild_events = [
        row
        for row in _read_jsonl(layout.events_path)
        if row.get("operation_id") == operation_id
    ]
    assert len(rebuild_events) == 1
    assert rebuild_events[0]["event"] == "checkpoint_rebuild_started"


def test_legacy_adoption_builds_honest_receipts_then_releases(tmp_path: Path) -> None:
    """Explicit adoption converts only a fully validated legacy completion."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    adopted = layout.adopt_legacy()

    assert adopted.status == "released"
    assert adopted.schema_version == STATE_SCHEMA_VERSION
    assert adopted.current_stage is None
    unavailable_hash = canonical_sha256(LEGACY_UNAVAILABLE_PROVENANCE)
    for stage in PipelineStage:
        stage_state = next(item for item in adopted.stages if item.stage == stage.value)
        receipt_path = layout.receipt_path(stage)
        assert stage_state.receipt_sha256 == file_sha256(receipt_path)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["origin"] == "legacy_adoption"
        assert receipt["code"] == LEGACY_UNAVAILABLE_PROVENANCE
        assert receipt["code_sha256"] == unavailable_hash
        assert receipt["provider_calls_sha256"] == unavailable_hash
    verify_released_asset(layout, adopted)
    adoption_rows = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row.get("kind") == "legacy_adoption"
    ]
    assert [row["phase"] for row in adoption_rows] == ["prepared", "committed"]


def test_legacy_adoption_accepts_declared_rubric_compatibility_profile(
    tmp_path: Path,
) -> None:
    """Pre-guideline artifacts are adopted without inventing native provenance."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    legacy_rubric = layout.artifact_path(
        PipelineStage.RUBRIC_EXTRACTION,
        "feedback_rubrics.jsonl",
    )
    workspace_module.atomic_write_jsonl(
        legacy_rubric,
        [{"record_id": "feedback-1", "must": ["Answer the request."]}],
    )
    for name in (
        "feedback_evidence.jsonl",
        "candidate_guidelines.jsonl",
        "evaluation_guidelines.jsonl",
    ):
        layout.artifact_path(PipelineStage.RUBRIC_EXTRACTION, name).unlink()
    manifest = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    manifest["evaluation_guidelines"] = {
        "schema_version": "legacy-feedback-rubric-v1",
        "count": 0,
        "activation_status": "legacy_compatibility",
        "calibration_status": "unavailable",
    }
    workspace_module.atomic_write_json(layout.manifest_path, manifest)
    workspace_module.atomic_write_json(
        layout.artifact_path(PipelineStage.DATASET_SPLITS, "dataset_manifest.json"),
        manifest,
    )
    _downgrade_to_legacy_completed(layout)

    adopted = layout.adopt_legacy()

    stage_three = json.loads(
        layout.receipt_path(PipelineStage.RUBRIC_EXTRACTION).read_text(
            encoding="utf-8"
        )
    )
    stage_six = json.loads(
        layout.receipt_path(PipelineStage.LABEL_INFERENCE).read_text(
            encoding="utf-8"
        )
    )
    assert adopted.status == "released"
    assert stage_three["artifact_profile"] == "legacy"
    assert stage_six["artifact_profile"] == "legacy"
    assert any(
        item["path"].endswith("feedback_rubrics.jsonl")
        for item in stage_three["outputs"]
    )
    verify_released_asset(layout, adopted)


@pytest.mark.parametrize("manifest_name", ["input", "asset"])
def test_legacy_adoption_rejects_inconsistent_manifest_without_writes(
    tmp_path: Path,
    manifest_name: str,
) -> None:
    """Source and asset manifest claims must agree with the persisted files."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    if manifest_name == "input":
        path = layout.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["inputs"]["labeled_feedback"]["sha256"] = "0" * 64
    else:
        path = layout.manifest_path
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["asset_id"] = "wrong"
    workspace_module.atomic_write_json(path, manifest)
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert not layout.recovery_journal_path.exists()


@pytest.mark.parametrize("stage", list(PipelineStage))
@pytest.mark.parametrize("mutation", ["missing", "corrupt"])
def test_legacy_adoption_rejects_invalid_required_artifact_without_authority_change(
    tmp_path: Path,
    stage: PipelineStage,
    mutation: str,
) -> None:
    """Every stage must validate before adoption writes receipts or a journal."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    target = layout.artifact_path(stage, _STAGE_MUTATION_TARGETS[stage])
    if mutation == "missing":
        target.unlink()
    elif target.suffix == ".md":
        target.write_text("", encoding="utf-8")
    else:
        target.write_text("{not-json\n", encoding="utf-8")
    before = _authority_bytes(layout)

    with pytest.raises(
        EvaluationAssetLegacyError,
        match=r"Run assets adopt after repair, or create a new asset version",
    ):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


@pytest.mark.parametrize(
    "catalog_name",
    ["train.jsonl", "validation.jsonl", "test.jsonl", "regression_trusted.jsonl"],
)
def test_legacy_adoption_rejects_catalog_copy_mismatch_without_authority_change(
    tmp_path: Path,
    catalog_name: str,
) -> None:
    """The four current catalog copies must match the legacy Stage 8 outputs."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)
    catalog_path = layout.published_datasets / catalog_name
    catalog_path.write_bytes(catalog_path.read_bytes() + b" \n")
    before = _authority_bytes(layout)

    with pytest.raises(EvaluationAssetLegacyError):
        layout.adopt_legacy()

    assert _authority_bytes(layout) == before
    assert layout.load_state().legacy_completed
    assert not layout.recovery_journal_path.exists()
    assert not any(layout.receipts_root.glob("*.json"))


def test_legacy_adoption_recovers_installed_nonauthoritative_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery completes adoption without rerunning any pipeline stage."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    def inject_fault(name: str) -> None:
        if name == "after_receipts_install":
            raise _InjectedFault(name)

    monkeypatch.setattr(workspace_module, "_fault_point", inject_fault)
    with pytest.raises(_InjectedFault, match="after_receipts_install"):
        layout.adopt_legacy()

    assert layout.load_state().legacy_completed
    assert len(list(layout.receipts_root.glob("*.json"))) == len(PipelineStage)
    prepared = [
        row
        for row in _read_jsonl(layout.recovery_journal_path)
        if row.get("kind") == "legacy_adoption" and row["phase"] == "prepared"
    ]
    assert len(prepared) == 1
    monkeypatch.setattr(workspace_module, "_fault_point", lambda name: None)

    assert layout.recover() == [prepared[0]["operation_id"]]
    adopted = layout.load_state()
    assert adopted.status == "released"
    verify_released_asset(layout, adopted)
    phases = [
        row["phase"]
        for row in _read_jsonl(layout.recovery_journal_path)
        if row["operation_id"] == prepared[0]["operation_id"]
    ]
    assert phases == ["prepared", "committed"]


def test_service_adopt_is_a_thin_locked_core_api(tmp_path: Path) -> None:
    """Service callers use the same adoption transaction as library callers."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    layout = pipeline.layout
    _downgrade_to_legacy_completed(layout)

    response = EvaluationAssetRunManager(layout.tenants_root).adopt(
        layout.tenant_id,
        layout.asset_id,
    )

    assert response["status"] == "released"
    verify_released_asset(layout, layout.load_state())


@pytest.mark.parametrize(
    "damage",
    ["receipt", "source", "manifest", "catalog"],
)
def test_extension_rejects_corrupt_parent_before_child_creation(
    tmp_path: Path,
    damage: str,
) -> None:
    """A child root stays absent unless the released parent verifies fully."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    if damage == "receipt":
        target = parent.receipt_path(PipelineStage.DATASET_SPLITS)
    elif damage == "source":
        target = parent.feedback_path
    elif damage == "manifest":
        target = parent.manifest_path
    else:
        target = parent.published_datasets / "train.jsonl"
    target.write_bytes(target.read_bytes() + b" \n")
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    additional = _write_additional_feedback(parent.tenants_root)

    with pytest.raises(EvaluationAssetIntegrityError):
        child.initialize_extension(
            parent,
            additional_feedback=additional,
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()


def test_extension_points_legacy_parent_to_adoption_without_child_creation(
    tmp_path: Path,
) -> None:
    """Legacy completed is never accepted as a released parent alias."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    _downgrade_to_legacy_completed(parent)
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")

    with pytest.raises(EvaluationAssetLegacyError, match="Run assets adopt"):
        child.initialize_extension(
            parent,
            additional_feedback=_write_additional_feedback(parent.tenants_root),
            additional_unlabeled=None,
            clustering_mode="keep",
        )

    assert not child.root.exists()


def test_extension_records_verified_parent_evidence_and_is_self_contained(
    tmp_path: Path,
) -> None:
    """Verified release/source identities are copied into a runnable child."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    parent_state = pipeline.run()
    parent = pipeline.layout
    expected_evidence = released_parent_evidence(parent, parent_state)
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")

    state = child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )

    assert state.status == "draft"
    assert all(stage.status == "pending" for stage in state.stages)
    lineage = json.loads(child.lineage_path.read_text(encoding="utf-8"))
    assert lineage["parent_release"] == expected_evidence
    assert json.loads(child.reuse_manifest_path.read_text(encoding="utf-8"))[
        "parent_release"
    ] == expected_evidence
    shutil.rmtree(parent.root)

    released = EvaluationAssetPipeline(
        child,
        rubric_provider=_SuccessfulRubricProvider(),
        embedding_provider=_SuccessfulEmbeddingProvider(),
    ).run()

    assert released.status == "released"
    verify_released_asset(child, released)


def test_extension_acquires_parent_and_child_locks_in_absolute_sorted_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock ordering is independent of caller parent/child argument order."""
    pipeline, _, _ = _create_pipeline(tmp_path)
    pipeline.run()
    parent = pipeline.layout
    child = EvaluationAssetLayout(parent.tenants_root, parent.tenant_id, "v2")
    acquired: list[str] = []

    class RecordingLock:
        def __init__(self, path: str, timeout: float) -> None:
            self.path = path

        def acquire(self) -> None:
            acquired.append(self.path)

        def release(self) -> None:
            pass

    monkeypatch.setattr(workspace_module, "FileLock", RecordingLock)

    child.initialize_extension(
        parent,
        additional_feedback=_write_additional_feedback(parent.tenants_root),
        additional_unlabeled=None,
        clustering_mode="keep",
    )

    expected = sorted(
        [str(parent.lock_path.absolute()), str(child.lock_path.absolute())]
    )
    assert acquired == expected


class _InjectedFault(RuntimeError):
    pass


def _create_pipeline(
    tmp_path: Path,
    *,
    asset_id: str = "v1",
) -> tuple[
    EvaluationAssetPipeline,
    _SuccessfulRubricProvider,
    _SuccessfulEmbeddingProvider,
]:
    tenants_root = tmp_path / "tenants"
    feedback, unlabeled = _write_input_pair(tenants_root)
    rubric = _SuccessfulRubricProvider()
    embedding = _SuccessfulEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id=asset_id,
            rubric_provider="fake",
            rubric_model=rubric.model,
            embedding_provider="fake",
            embedding_model=embedding.model,
            cluster_count=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    return pipeline, rubric, embedding


def _write_input_pair(tenants_root: Path) -> tuple[Path, Path]:
    sources = tenants_root / "tenant_a" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    common = {
        "schema_version": "fapo-evaluation-input-v1",
        "group_id": "group-1",
        "task_type": "generic",
        "user_input": "Process the supplied input.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }
    feedback.write_text(
        json.dumps(
            {
                **common,
                "record_id": "feedback-1",
                "assistant_output": "A previous response.",
                "feedback": {
                    "polarity": "positive",
                    "rationale": "The response satisfied the request.",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        json.dumps({**common, "record_id": "unlabeled-1"}) + "\n",
        encoding="utf-8",
    )
    return feedback, unlabeled


def _write_additional_feedback(tenants_root: Path) -> Path:
    path = tenants_root / "tenant_a" / "source_artifacts" / "additional.jsonl"
    payload = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": "feedback-2",
        "group_id": "group-2",
        "task_type": "generic",
        "user_input": "Process another supplied input.",
        "assistant_output": "Another previous response.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "feedback": {
            "polarity": "positive",
            "rationale": "The other response satisfied the request.",
        },
        "metadata": {},
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _authority_bytes(layout: EvaluationAssetLayout) -> dict[str, bytes]:
    authority = {
        f"asset/{name}": contents
        for name, contents in _tree_bytes(layout.root).items()
    }
    if layout.published_datasets.is_dir():
        authority.update(
            {
                f"catalog/{name}": contents
                for name, contents in _tree_bytes(layout.published_datasets).items()
            }
        )
    return authority


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _downgrade_to_legacy_completed(layout: EvaluationAssetLayout) -> None:
    state = layout.load_state().to_dict()
    state.pop("schema_version", None)
    state.pop("mutation_sequence", None)
    state.pop("last_operation_id", None)
    state["status"] = "completed"
    for stage_state in state["stages"]:
        stage_state.pop("receipt_sha256", None)
    workspace_module.atomic_write_json(layout.state_path, state)
    for stage in PipelineStage:
        layout.receipt_path(stage).unlink()
