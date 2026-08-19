# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Filesystem layout and persistence for evaluation assets."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Sequence

from filelock import FileLock, Timeout

from src.hephaestus.artifact_io import (
    atomic_append_jsonl,
    atomic_copy_file,
    atomic_write_json,
    atomic_write_jsonl,
)
from src.hephaestus.artifact_io import (
    atomic_write_text as atomic_write_text,
)
from src.hephaestus.evaluation_assets.durability import (
    STAGE_SPECIFICATIONS,
    EvaluationAssetBusyError,
    EvaluationAssetImmutableError,
    EvaluationAssetIntegrityError,
    EvaluationAssetLegacyError,
    build_stage_receipt,
    file_sha256,
    persisted_json_sha256,
    released_parent_evidence,
    validate_legacy_release_candidate,
    verify_receipt_chain,
    verify_released_asset,
)
from src.hephaestus.evaluation_assets.input_contract import validate_input_records
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)

SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")
STAGE_DIRECTORIES = {
    PipelineStage.RAW_INPUTS.value: "01_raw_inputs",
    PipelineStage.PREPARED_INPUTS.value: "02_prepared_inputs",
    PipelineStage.RUBRIC_EXTRACTION.value: "03_evaluation_guidelines",
    PipelineStage.INTENT_CLUSTERING.value: "04_intent_clustering",
    PipelineStage.COVERAGE_DECISIONS.value: "05_coverage_decisions",
    PipelineStage.LABEL_INFERENCE.value: "06_label_inference",
    PipelineStage.SYNTHETIC_COVERAGE.value: "07_synthetic_coverage",
    PipelineStage.DATASET_SPLITS.value: "08_dataset_splits",
}
PREVIOUS_STAGE_DIRECTORIES = {
    PipelineStage.RUBRIC_EXTRACTION.value: "03_rubric_extraction",
}
LEGACY_DIRECTORIES = (
    "raw_inputs",
    "prepared_inputs",
    "decision_assets",
    "review_queues",
    "dataset_splits",
)
STAGE_ARTIFACTS = {
    PipelineStage.RUBRIC_EXTRACTION: (
        "feedback_evidence.jsonl",
        "candidate_guidelines.jsonl",
        "evaluation_guidelines.jsonl",
        "feedback_rubrics.jsonl",
        "trusted_intents.jsonl",
        "trusted_cases.jsonl",
    ),
    PipelineStage.INTENT_CLUSTERING: (
        "intent_inventory.jsonl",
        "cluster_lineage.jsonl",
    ),
    PipelineStage.COVERAGE_DECISIONS: (
        "intent_matches.jsonl",
        "coverage_report.md",
        "review_queue/labeling_queue.jsonl",
    ),
    PipelineStage.LABEL_INFERENCE: (
        "inferred_unlabeled_cluster_rubrics.jsonl",
        "inferred_unlabeled_labels.jsonl",
        "missing_labeled_feedback_clusters.jsonl",
        "missing_labeled_feedback_report.md",
        "inferred_cases.jsonl",
    ),
    PipelineStage.SYNTHETIC_COVERAGE: (
        "synthetic_candidates.jsonl",
        "rejected_synthetic.jsonl",
        "synthetic_filter_issues.jsonl",
        "synthetic_cases.jsonl",
    ),
}


def utc_now() -> str:
    """Return a stable ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _fault_point(name: str) -> None:
    """Provide a deterministic test seam between durable transaction phases."""


@contextmanager
def _ordered_asset_locks(
    layouts: Sequence["EvaluationAssetLayout"],
    timeout: float,
) -> Iterator[None]:
    """Acquire unique asset locks by sorted absolute path and release in reverse."""
    ordered = sorted(
        {str(layout.lock_path.absolute()): layout for layout in layouts}.items()
    )
    acquired: list[FileLock] = []
    current: Optional[EvaluationAssetLayout] = None
    try:
        for lock_name, current in ordered:
            current.lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock = FileLock(lock_name, timeout=timeout)
            try:
                lock.acquire()
            except Timeout as exc:
                raise EvaluationAssetBusyError(
                    current.tenant_id,
                    current.asset_id,
                ) from exc
            acquired.append(lock)
        yield
    finally:
        for lock in reversed(acquired):
            lock.release()


@dataclass(frozen=True)
class EvaluationAssetLayout:
    """Canonical self-contained layout for one tenant asset version."""

    tenants_root: Path
    tenant_id: str
    asset_id: str

    def __post_init__(self) -> None:
        if not SAFE_NAME.fullmatch(self.tenant_id):
            raise ValueError("tenant_id must contain only letters, digits, '-' or '_'")
        if not SAFE_NAME.fullmatch(self.asset_id):
            raise ValueError("asset_id must contain only letters, digits, '-' or '_'")

    @property
    def tenant_root(self) -> Path:
        return self.tenants_root.resolve() / self.tenant_id

    @property
    def assets_root(self) -> Path:
        return self.tenant_root / "evaluation_assets"

    @property
    def root(self) -> Path:
        return self.assets_root / self.asset_id

    @property
    def lock_path(self) -> Path:
        """Return the deterministic collection-level lock for this asset."""
        return self.assets_root / ".locks" / f"{self.asset_id}.lock"

    @contextmanager
    def asset_lock(self, timeout: float = 0) -> Iterator[None]:
        """Hold the cross-process mutation lock for this asset."""
        with _ordered_asset_locks((self,), timeout):
            yield

    @property
    def stages_root(self) -> Path:
        return self.root / "stages"

    @property
    def receipts_root(self) -> Path:
        return self.root / "receipts"

    def receipt_path(self, stage: PipelineStage | str) -> Path:
        """Return the commit-marker path for one ordered stage."""
        stage_name = stage.value if isinstance(stage, PipelineStage) else str(stage)
        try:
            stage_value = PipelineStage(stage_name)
        except ValueError as exc:
            raise ValueError(f"Unknown evaluation asset stage: {stage_name}") from exc
        index = list(PipelineStage).index(stage_value) + 1
        return self.receipts_root / f"{index:02d}_{stage_name}.json"

    @property
    def uses_stage_layout(self) -> bool:
        """Return whether this asset uses the canonical stage-oriented layout."""
        if self.stages_root.is_dir():
            return True
        return not any((self.root / name).exists() for name in LEGACY_DIRECTORIES)

    def stage_directory(self, stage: PipelineStage | str) -> Path:
        """Return the canonical output directory for one pipeline stage."""
        stage_name = stage.value if isinstance(stage, PipelineStage) else str(stage)
        try:
            directory = STAGE_DIRECTORIES[stage_name]
        except KeyError as exc:
            raise ValueError(f"Unknown evaluation asset stage: {stage_name}") from exc
        canonical = self.stages_root / directory
        previous_name = PREVIOUS_STAGE_DIRECTORIES.get(stage_name)
        previous = self.stages_root / previous_name if previous_name else None
        if previous is not None and previous.is_dir() and not canonical.exists():
            return previous
        return canonical

    def artifact_path(
        self,
        stage: PipelineStage | str,
        relative_name: str,
    ) -> Path:
        """Resolve a stage artifact in either the canonical or legacy layout."""
        stage_name = stage.value if isinstance(stage, PipelineStage) else str(stage)
        if self.uses_stage_layout:
            return self.stage_directory(stage_name) / relative_name
        return self.root / _legacy_artifact_path(stage_name, relative_name)

    @property
    def raw_inputs(self) -> Path:
        """Compatibility alias for Stage 1 or the legacy raw-input directory."""
        if self.uses_stage_layout:
            return self.stage_directory(PipelineStage.RAW_INPUTS)
        return self.root / "raw_inputs"

    @property
    def prepared_inputs(self) -> Path:
        """Compatibility alias for Stage 2 or the legacy prepared directory."""
        if self.uses_stage_layout:
            return self.stage_directory(PipelineStage.PREPARED_INPUTS)
        return self.root / "prepared_inputs"

    @property
    def decision_assets(self) -> Path:
        """Return the legacy decision directory for compatibility callers."""
        return self.root / "decision_assets"

    @property
    def review_queues(self) -> Path:
        """Compatibility alias for the Stage 5 review queue directory."""
        if self.uses_stage_layout:
            return self.stage_directory(PipelineStage.COVERAGE_DECISIONS) / "review_queue"
        return self.root / "review_queues"

    @property
    def dataset_splits(self) -> Path:
        """Compatibility alias for Stage 8 or the legacy split directory."""
        if self.uses_stage_layout:
            return self.stage_directory(PipelineStage.DATASET_SPLITS)
        return self.root / "dataset_splits"

    @property
    def published_datasets(self) -> Path:
        """Return the versioned tenant dataset directory published by Stage 8."""
        return self.tenant_root / "datasets" / "evaluation_assets" / self.asset_id

    def publish_dataset_splits(
        self,
        split_names: Sequence[str],
    ) -> Dict[str, str]:
        """Copy selected Stage 8 splits into the tenant's dataset catalog."""
        published: Dict[str, str] = {}
        for split_name in split_names:
            source = self.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split_name}.jsonl",
            )
            destination = self.published_datasets / f"{split_name}.jsonl"
            _copy_jsonl(source, destination)
            published[split_name] = destination.relative_to(
                self.tenant_root
            ).as_posix()
        return published

    @property
    def config_path(self) -> Path:
        return self.root / "config.json"

    @property
    def state_path(self) -> Path:
        return self.root / "pipeline_state.json"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    @property
    def manifest_path(self) -> Path:
        return self.root / "asset_manifest.json"

    @property
    def config_history_path(self) -> Path:
        return self.root / "config_history.jsonl"

    @property
    def recovery_journal_path(self) -> Path:
        return self.root / "recovery_journal.jsonl"

    @property
    def lineage_path(self) -> Path:
        return self.root / "lineage.json"

    @property
    def reuse_manifest_path(self) -> Path:
        return self.root / "reuse_manifest.json"

    @property
    def feedback_path(self) -> Path:
        return self.artifact_path(PipelineStage.RAW_INPUTS, "labeled_feedback.jsonl")

    @property
    def unlabeled_path(self) -> Path:
        return self.artifact_path(PipelineStage.RAW_INPUTS, "unlabeled.jsonl")

    @property
    def parent_snapshot(self) -> Path:
        return self.artifact_path(
            PipelineStage.RAW_INPUTS,
            "parent_snapshot",
        )

    def ensure(self) -> None:
        """Create the canonical directories without requiring other tenant files."""
        if self.uses_stage_layout:
            paths = [self.stage_directory(stage) for stage in PipelineStage]
        else:
            paths = [self.root / name for name in LEGACY_DIRECTORIES]
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)

    def resolve_input_source(self, path: Path) -> Path:
        """Resolve one authorized JSONL source for this selected tenant."""
        requested = path.expanduser().absolute()
        try:
            resolved = requested.resolve(strict=True)
        except FileNotFoundError as exc:
            raise FileNotFoundError(requested) from exc
        if not resolved.is_file():
            raise ValueError(
                f"Evaluation asset input must be a regular file: {requested}"
            )
        if requested.suffix != ".jsonl" or resolved.suffix != ".jsonl":
            raise ValueError(f"Evaluation asset inputs must use .jsonl: {requested}")

        source_root = (self.tenant_root / "source_artifacts").resolve()
        datasets_root = (self.tenant_root / "datasets").resolve()
        generated_root = (datasets_root / "evaluation_assets").resolve()
        if not _is_beneath(resolved, self.tenant_root):
            raise ValueError(
                "Evaluation asset input must remain inside the selected tenant "
                f"after symlink resolution: {requested}"
            )
        if _is_beneath(requested, generated_root) or _is_beneath(
            resolved,
            generated_root,
        ):
            raise ValueError(
                "Evaluation asset inputs cannot use generated "
                f"datasets/evaluation_assets files: {requested}"
            )
        if not (
            _is_beneath(resolved, source_root)
            or _is_beneath(resolved, datasets_root)
        ):
            raise ValueError(
                "Evaluation asset input must be a regular .jsonl file under "
                "the selected tenant's source_artifacts/ or datasets/: "
                f"{requested}"
            )
        return resolved

    def initialize(
        self,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
        *,
        initial_status: str = "draft",
        lock_timeout: float = 0,
    ) -> PipelineState:
        """Copy raw inputs into the asset and persist initial config/state."""
        with self.asset_lock(lock_timeout):
            return self._initialize_locked(
                config,
                feedback_source,
                unlabeled_source,
                initial_status=initial_status,
            )

    def _initialize_locked(
        self,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
        *,
        initial_status: str,
    ) -> PipelineState:
        """Initialize while the caller holds :attr:`lock_path`."""
        if initial_status not in {"draft", "queued"}:
            raise ValueError("initial_status must be draft or queued")
        if self.config_path.exists() or self.state_path.exists():
            raise FileExistsError(f"Evaluation asset already exists: {self.root}")
        feedback_source = self.resolve_input_source(feedback_source)
        unlabeled_source = self.resolve_input_source(unlabeled_source)
        _validate_source_rows(feedback_source, labeled=True)
        _validate_source_rows(unlabeled_source, labeled=False)
        self.ensure()
        _copy_jsonl(feedback_source, self.feedback_path)
        _copy_jsonl(unlabeled_source, self.unlabeled_path)
        timestamp = utc_now()
        state = PipelineState.new(config, timestamp)
        state.status = initial_status
        atomic_write_json(self.config_path, config.to_dict())
        atomic_write_json(self.state_path, state.to_dict())
        self._append_config_revision(
            {
                "timestamp": timestamp,
                "revision": 1,
                "event": "configuration_created",
                "configuration": config.to_dict(),
            }
        )
        self.append_event("pipeline_created", {"status": state.status})
        return state

    def initialize_extension(
        self,
        parent: "EvaluationAssetLayout",
        *,
        additional_feedback: Optional[Path],
        additional_unlabeled: Optional[Path],
        clustering_mode: str,
        config_updates: Optional[Mapping[str, Any]] = None,
        lock_timeout: float = 0,
    ) -> PipelineState:
        """Create a child only after verifying its immutable released parent."""
        with _ordered_asset_locks((parent, self), lock_timeout):
            parent._recover_locked()
            return self._initialize_extension_locked(
                parent,
                additional_feedback=additional_feedback,
                additional_unlabeled=additional_unlabeled,
                clustering_mode=clustering_mode,
                config_updates=config_updates,
            )

    def _initialize_extension_locked(
        self,
        parent: "EvaluationAssetLayout",
        *,
        additional_feedback: Optional[Path],
        additional_unlabeled: Optional[Path],
        clustering_mode: str,
        config_updates: Optional[Mapping[str, Any]],
    ) -> PipelineState:
        """Initialize an extension while both parent and child locks are held."""
        if clustering_mode not in {"keep", "refresh"}:
            raise ValueError("clustering_mode must be 'keep' or 'refresh'")
        if parent.tenant_id != self.tenant_id:
            raise ValueError("parent and child assets must belong to the same tenant")
        if parent.asset_id == self.asset_id:
            raise ValueError("extended asset must use a new asset_id")
        if self.config_path.exists() or self.state_path.exists():
            raise FileExistsError(f"Evaluation asset already exists: {self.root}")
        resolved_feedback = (
            self.resolve_input_source(additional_feedback)
            if additional_feedback is not None
            else None
        )
        resolved_unlabeled = (
            self.resolve_input_source(additional_unlabeled)
            if additional_unlabeled is not None
            else None
        )
        extra_feedback = (
            _validate_source_rows(resolved_feedback, labeled=True)
            if resolved_feedback is not None
            else []
        )
        extra_unlabeled = (
            _validate_source_rows(resolved_unlabeled, labeled=False)
            if resolved_unlabeled is not None
            else []
        )
        if not extra_feedback and not extra_unlabeled:
            raise ValueError(
                "extension requires additional labeled or unlabeled records"
            )
        if clustering_mode == "keep" and extra_unlabeled:
            raise ValueError(
                "keep clustering accepts labeled additions only; "
                "use refresh when adding unlabeled records"
            )

        parent_state = parent.load_state()
        if parent_state.legacy_completed:
            raise EvaluationAssetLegacyError(
                parent.tenant_id,
                parent.asset_id,
                "explicit verification and adoption are required before extension",
            )
        if parent_state.status != "released":
            raise ValueError("parent evaluation asset must be released")
        parent_release = released_parent_evidence(parent, parent_state)

        parent_config = parent.load_config()
        merged_config = parent_config.to_dict()
        merged_config.update(dict(config_updates or {}))
        merged_config["tenant_id"] = self.tenant_id
        merged_config["asset_id"] = self.asset_id
        if "embedding_model" in (config_updates or {}):
            merged_config["embedding_provider"] = (
                "tfidf"
                if config_updates["embedding_model"] == "tfidf"
                else "openai"
            )
        config = EvaluationAssetConfig.from_dict(merged_config)
        if config.rubric_provider != parent_config.rubric_provider or (
            config.rubric_model != parent_config.rubric_model
        ):
            raise ValueError(
                "incremental extension must keep the parent's guideline model"
            )
        if clustering_mode == "keep" and (
            config.embedding_provider != parent_config.embedding_provider
            or config.embedding_model != parent_config.embedding_model
            or config.cluster_count != parent_config.cluster_count
        ):
            raise ValueError(
                "keep clustering requires the parent's embedding model "
                "and cluster count"
            )

        feedback_rows = _merge_jsonl_rows(
            _read_jsonl_rows(parent.feedback_path),
            extra_feedback,
            source="labeled feedback",
        )
        unlabeled_rows = _merge_jsonl_rows(
            _read_jsonl_rows(parent.unlabeled_path),
            extra_unlabeled,
            source="unlabeled input",
        )
        self.ensure()
        atomic_write_jsonl(self.feedback_path, feedback_rows)
        atomic_write_jsonl(self.unlabeled_path, unlabeled_rows)

        guideline_artifacts = (
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
        )
        compatibility_artifacts = ("feedback_rubrics.jsonl",)
        shared_artifacts = ("trusted_intents.jsonl", "trusted_cases.jsonl")
        if parent.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        ).is_file():
            stage_three_artifacts = guideline_artifacts + shared_artifacts
        else:
            stage_three_artifacts = compatibility_artifacts + shared_artifacts
        seeded_artifacts = []
        for name in stage_three_artifacts:
            source = parent.artifact_path(PipelineStage.RUBRIC_EXTRACTION, name)
            if not source.is_file():
                raise FileNotFoundError(source)
            destination = self.artifact_path(PipelineStage.RUBRIC_EXTRACTION, name)
            atomic_copy_file(source, destination)
            seeded_artifacts.append(name)

        snapshot_sources = {
            "parent_intent_inventory.jsonl": parent.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            ),
            "parent_intent_matches.jsonl": parent.artifact_path(
                PipelineStage.COVERAGE_DECISIONS,
                "intent_matches.jsonl",
            ),
            "parent_inferred_cluster_rubrics.jsonl": parent.artifact_path(
                PipelineStage.LABEL_INFERENCE,
                "inferred_unlabeled_cluster_rubrics.jsonl",
            ),
            "parent_synthetic_cases.jsonl": parent.artifact_path(
                PipelineStage.SYNTHETIC_COVERAGE,
                "synthetic_cases.jsonl",
            ),
            **{
                f"parent_{split}.jsonl": parent.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    f"{split}.jsonl",
                )
                for split in (
                    "train",
                    "validation",
                    "test",
                    "regression_trusted",
                )
            },
        }
        snapshot_artifacts = []
        for name, source in snapshot_sources.items():
            if not source.is_file():
                raise FileNotFoundError(source)
            destination = self.parent_snapshot / name
            atomic_copy_file(source, destination)
            snapshot_artifacts.append(
                {
                    "file": name,
                    "sha256": _sha256_path(destination),
                }
            )

        reused_artifacts = []
        if clustering_mode == "keep":
            source = parent.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            )
            if not source.is_file():
                raise FileNotFoundError(source)
            destination = self.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            )
            atomic_copy_file(source, destination)
            reused_artifacts.append("intent_inventory.jsonl")
            clusters = _read_jsonl_rows(destination)
            lineage_rows = [
                {
                    "previous_cluster_id": row["cluster_id"],
                    "new_cluster_id": row["cluster_id"],
                    "member_overlap": 1.0,
                    "relationship": "reused",
                }
                for row in clusters
            ]
            atomic_write_jsonl(
                self.artifact_path(
                    PipelineStage.INTENT_CLUSTERING,
                    "cluster_lineage.jsonl",
                ),
                lineage_rows,
            )
            reused_artifacts.append("cluster_lineage.jsonl")

        timestamp = utc_now()
        state = PipelineState.new(config, timestamp)

        lineage = {
            "asset_id": self.asset_id,
            "parent_asset_id": parent.asset_id,
            "creation_mode": "incremental_feedback",
            "clustering_mode": clustering_mode,
            "created_at": timestamp,
            "parent_release": parent_release,
            "added_labeled_record_ids": [
                str(row["record_id"]) for row in extra_feedback
            ],
            "added_unlabeled_record_ids": [
                str(row["record_id"]) for row in extra_unlabeled
            ],
            "parent_input_counts": {
                "labeled": len(feedback_rows) - len(extra_feedback),
                "unlabeled": len(unlabeled_rows) - len(extra_unlabeled),
            },
            "extended_input_counts": {
                "labeled": len(feedback_rows),
                "unlabeled": len(unlabeled_rows),
            },
        }
        reuse_manifest = {
            "parent_asset_id": parent.asset_id,
            "parent_release": parent_release,
            "parent_snapshot": {
                "path": self.parent_snapshot.relative_to(self.root).as_posix(),
                "artifacts": snapshot_artifacts,
            },
            "seeded_incremental_stage": {
                "stage": PipelineStage.RUBRIC_EXTRACTION.value,
                "artifacts": seeded_artifacts,
                "operation": "append_evidence_and_rebuild_guidelines",
            },
            "reused_stages": (
                [
                    {
                        "stage": PipelineStage.INTENT_CLUSTERING.value,
                        "artifacts": reused_artifacts,
                        "reason": "no unlabeled records or clustering settings changed",
                    }
                ]
                if clustering_mode == "keep"
                else []
            ),
        }
        atomic_write_json(self.config_path, config.to_dict())
        atomic_write_json(self.state_path, state.to_dict())
        atomic_write_json(self.lineage_path, lineage)
        atomic_write_json(self.reuse_manifest_path, reuse_manifest)
        self._append_config_revision(
            {
                "timestamp": timestamp,
                "revision": 1,
                "event": "configuration_inherited",
                "parent_asset_id": parent.asset_id,
                "configuration": config.to_dict(),
            }
        )
        self.append_event(
            "pipeline_extended",
            {
                "parent_asset_id": parent.asset_id,
                "clustering_mode": clustering_mode,
                "added_labeled_records": len(extra_feedback),
                "added_unlabeled_records": len(extra_unlabeled),
            },
        )
        return state

    def adopt_legacy(self, *, lock_timeout: float = 0) -> PipelineState:
        """Verify and explicitly adopt one pre-v2 completed asset."""
        with self.asset_lock(lock_timeout):
            recovered = self._recover_locked()
            state = self.load_state()
            if state.status == "released":
                verify_released_asset(self, state)
                if recovered:
                    return state
                raise EvaluationAssetImmutableError(self.tenant_id, self.asset_id)
            if not state.legacy_completed:
                raise EvaluationAssetLegacyError(
                    self.tenant_id,
                    self.asset_id,
                    "only a pre-v2 completed state can be adopted",
                )
            try:
                _validate_source_rows(self.feedback_path, labeled=True)
                _validate_source_rows(self.unlabeled_path, labeled=False)
                config = self.load_config()
                counts = validate_legacy_release_candidate(
                    self,
                    state,
                    config,
                )
                receipts: dict[PipelineStage, dict[str, Any]] = {}
                timestamp = utc_now()
                for stage in PipelineStage:
                    stage_state = next(
                        item for item in state.stages if item.stage == stage.value
                    )
                    completed_at = (
                        stage_state.completed_at or state.updated_at or timestamp
                    )
                    stage_counts = {
                        key: counts[key] for key in STAGE_COUNT_KEYS[stage]
                    }
                    receipts[stage] = build_stage_receipt(
                        self,
                        stage,
                        config,
                        stage_counts,
                        completed_at=completed_at,
                        prompt_values={},
                        origin="legacy_adoption",
                        historical_unavailable=True,
                        upstream_receipts=receipts,
                    )
            except EvaluationAssetLegacyError:
                raise
            except (
                EvaluationAssetIntegrityError,
                KeyError,
                OSError,
                TypeError,
                UnicodeError,
                ValueError,
            ) as exc:
                raise EvaluationAssetLegacyError(
                    self.tenant_id,
                    self.asset_id,
                    "required stage artifacts or manifests failed verification",
                ) from exc

            operation_id = uuid.uuid4().hex
            target_state = PipelineState.from_dict(state.to_dict())
            target_state.schema_version = STATE_SCHEMA_VERSION
            target_state.status = "released"
            target_state.current_stage = None
            target_state.error = None
            target_state.counts = counts
            target_state.updated_at = timestamp
            target_state.mutation_sequence = state.mutation_sequence + 1
            target_state.last_operation_id = operation_id
            for stage in PipelineStage:
                stage_state = next(
                    item
                    for item in target_state.stages
                    if item.stage == stage.value
                )
                stage_state.receipt_sha256 = persisted_json_sha256(
                    receipts[stage]
                )
            event_entry = {
                "timestamp": timestamp,
                "event": "legacy_asset_adopted",
                "tenant_id": self.tenant_id,
                "asset_id": self.asset_id,
                "operation_id": operation_id,
                "details": {"previous_status": "completed"},
            }
            prepared = {
                "schema_version": "fapo-recovery-journal-v1",
                "operation_id": operation_id,
                "kind": "legacy_adoption",
                "phase": "prepared",
                "prepared_at": timestamp,
                "before": {
                    "config_sha256": file_sha256(self.config_path),
                    "state_sha256": file_sha256(self.state_path),
                },
                "target_receipts": {
                    stage.value: receipts[stage] for stage in PipelineStage
                },
                "target_state": target_state.to_dict(),
                "event_entry": event_entry,
                "result": {"status": "released"},
            }
            self._append_journal_once(prepared)
            _fault_point("after_prepared_journal")
            self._install_adoption_receipts(prepared)
            _fault_point("after_receipts_install")
            verify_receipt_chain(self, target_state)
            atomic_write_json(self.state_path, target_state.to_dict())
            _fault_point("after_state_replace")
            self._append_jsonl_once(self.events_path, event_entry)
            _fault_point("after_event_append")
            self._commit_journal_operation(prepared)
            return target_state

    def load_config(self) -> EvaluationAssetConfig:
        """Load this asset's persisted configuration."""
        return EvaluationAssetConfig.from_dict(read_json(self.config_path))

    def load_state(self) -> PipelineState:
        """Load this asset's persisted run state."""
        return PipelineState.from_dict(read_json(self.state_path))

    def save_state(self, state: PipelineState) -> None:
        """Atomically persist run state."""
        state.updated_at = utc_now()
        atomic_write_json(self.state_path, state.to_dict())

    def revise_config(
        self,
        updates: Mapping[str, Any],
        *,
        lock_timeout: float = 0,
    ) -> Dict[str, Any]:
        """Persist decision changes and invalidate their dependent stages."""
        with self.asset_lock(lock_timeout):
            self._recover_locked()
            return self._revise_config_locked(updates)

    def _revise_config_locked(self, updates: Mapping[str, Any]) -> Dict[str, Any]:
        """Revise configuration while the caller holds the asset lock."""
        state = self.load_state()
        if state.status == "released":
            verify_released_asset(self, state)
            raise EvaluationAssetImmutableError(self.tenant_id, self.asset_id)
        if state.legacy_completed:
            raise EvaluationAssetLegacyError(
                self.tenant_id,
                self.asset_id,
                "explicit verification and adoption are required before revision",
            )
        current = self.load_config()
        unknown = set(updates) - set(CONFIG_STAGE_DEPENDENCIES)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unsupported pipeline decision fields: {names}")

        merged = current.to_dict()
        merged.update(dict(updates))
        if "embedding_model" in updates:
            merged["embedding_provider"] = (
                "tfidf" if updates["embedding_model"] == "tfidf" else "openai"
            )
        revised = EvaluationAssetConfig.from_dict(merged)
        changes = {
            key: {"previous": current.to_dict()[key], "new": revised.to_dict()[key]}
            for key in CONFIG_STAGE_DEPENDENCIES
            if current.to_dict()[key] != revised.to_dict()[key]
        }
        if not changes:
            return {
                "changed_fields": {},
                "invalidated_from_stage": None,
                "resume_from_stage": None,
            }

        ordered_stages = list(PipelineStage)
        earliest = min(
            (CONFIG_STAGE_DEPENDENCIES[key] for key in changes),
            key=ordered_stages.index,
        )
        invalidated = ordered_stages[ordered_stages.index(earliest) :]
        resume_stage = next(
            (
                stage
                for stage in ordered_stages
                if next(
                    item for item in state.stages if item.stage == stage.value
                ).status
                != "completed"
            ),
            earliest,
        )
        revision = self._config_revision_count() + 1
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        target_state = self._target_invalidated_state(
            state,
            invalidated,
            resume_stage=resume_stage,
            operation_id=operation_id,
            timestamp=timestamp,
        )
        history_entry = {
            "timestamp": timestamp,
            "revision": revision,
            "event": "configuration_updated",
            "operation_id": operation_id,
            "changed_fields": changes,
            "invalidated_from_stage": earliest.value,
            "resume_from_stage": resume_stage.value,
        }
        event_entry = {
            "timestamp": timestamp,
            "event": "configuration_updated",
            "tenant_id": self.tenant_id,
            "asset_id": self.asset_id,
            "operation_id": operation_id,
            "details": {
                "revision": revision,
                "changed_fields": changes,
                "invalidated_from_stage": earliest.value,
                "resume_from_stage": resume_stage.value,
            },
        }
        result = {
            "changed_fields": changes,
            "invalidated_from_stage": earliest.value,
            "resume_from_stage": resume_stage.value,
            "revision": revision,
        }
        prepared = {
            "schema_version": "fapo-recovery-journal-v1",
            "operation_id": operation_id,
            "kind": "configuration_revision",
            "phase": "prepared",
            "prepared_at": timestamp,
            "before": {
                "config_sha256": file_sha256(self.config_path),
                "state_sha256": file_sha256(self.state_path),
            },
            "target_config": revised.to_dict(),
            "target_state": target_state.to_dict(),
            "history_entry": history_entry,
            "event_entry": event_entry,
            "invalidated_stages": [stage.value for stage in invalidated],
            "result": result,
        }
        self._append_journal_once(prepared)
        _fault_point("after_prepared_journal")
        atomic_write_json(self.config_path, revised.to_dict())
        _fault_point("after_config_replace")
        atomic_write_json(self.state_path, target_state.to_dict())
        _fault_point("after_state_replace")
        self._append_jsonl_once(self.config_history_path, history_entry)
        _fault_point("after_history_append")
        self._append_jsonl_once(self.events_path, event_entry)
        _fault_point("after_event_append")
        _fault_point("before_cleanup")
        self._clear_stage_outputs(invalidated)
        self._commit_journal_operation(prepared)
        return result

    def recover(self, *, lock_timeout: float = 0) -> list[str]:
        """Roll every prepared recovery operation forward exactly once."""
        with self.asset_lock(lock_timeout):
            return self._recover_locked()

    def _recover_locked(self) -> list[str]:
        """Recover prepared operations while the caller holds the asset lock."""
        entries = self._read_control_log(self.recovery_journal_path)
        committed = {
            str(row.get("operation_id"))
            for row in entries
            if row.get("phase") == "committed"
        }
        recovered: list[str] = []
        for entry in entries:
            operation_id = str(entry.get("operation_id") or "")
            if entry.get("phase") != "prepared" or operation_id in committed:
                continue
            self._roll_forward_prepared(entry)
            recovered.append(operation_id)
            committed.add(operation_id)
        return recovered

    def _roll_forward_prepared(self, entry: Mapping[str, Any]) -> None:
        kind = entry.get("kind")
        if kind == "legacy_adoption":
            self._install_adoption_receipts(entry)
            target_state = entry.get("target_state")
            if not isinstance(target_state, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing target state",
                )
            recovered_state = PipelineState.from_dict(target_state)
            verify_receipt_chain(self, recovered_state)
            atomic_write_json(self.state_path, target_state)
            event_entry = entry.get("event_entry")
            if isinstance(event_entry, Mapping):
                self._append_jsonl_once(self.events_path, event_entry)
            self._commit_journal_operation(entry)
            return
        if kind not in {"configuration_revision", "checkpoint_rebuild"}:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal contains an unsupported operation",
            )
        target_config = entry.get("target_config")
        if isinstance(target_config, Mapping):
            atomic_write_json(self.config_path, target_config)
        target_state = entry.get("target_state")
        if not isinstance(target_state, Mapping):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal is missing target state",
            )
        atomic_write_json(self.state_path, target_state)
        history_entry = entry.get("history_entry")
        if isinstance(history_entry, Mapping):
            self._append_jsonl_once(self.config_history_path, history_entry)
        event_entry = entry.get("event_entry")
        if isinstance(event_entry, Mapping):
            self._append_jsonl_once(self.events_path, event_entry)
        invalidated = entry.get("invalidated_stages")
        if not isinstance(invalidated, list):
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal is missing its cleanup boundary",
            )
        try:
            stages = [PipelineStage(str(stage)) for stage in invalidated]
        except ValueError as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an invalid cleanup boundary",
            ) from exc
        self._clear_stage_outputs(stages)
        self._commit_journal_operation(entry)

    def _install_adoption_receipts(self, entry: Mapping[str, Any]) -> None:
        receipts = entry.get("target_receipts")
        if not isinstance(receipts, Mapping) or set(receipts) != {
            stage.value for stage in PipelineStage
        }:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an incomplete receipt set",
            )
        for stage in PipelineStage:
            receipt = receipts.get(stage.value)
            if not isinstance(receipt, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal has an invalid receipt",
                )
            atomic_write_json(self.receipt_path(stage), receipt)

    def _commit_journal_operation(self, prepared: Mapping[str, Any]) -> None:
        self._append_journal_once(
            {
                "schema_version": "fapo-recovery-journal-v1",
                "operation_id": str(prepared["operation_id"]),
                "kind": str(prepared["kind"]),
                "phase": "committed",
                "committed_at": utc_now(),
            }
        )

    def _append_journal_once(self, payload: Mapping[str, Any]) -> None:
        self._append_jsonl_once(
            self.recovery_journal_path,
            payload,
            identity_fields=("operation_id", "phase"),
        )

    def _append_jsonl_once(
        self,
        path: Path,
        payload: Mapping[str, Any],
        *,
        identity_fields: Sequence[str] = ("operation_id",),
    ) -> None:
        identity = tuple(payload.get(field) for field in identity_fields)
        if any(
            tuple(row.get(field) for field in identity_fields) == identity
            for row in self._read_control_log(path)
        ):
            return
        atomic_append_jsonl(path, payload)

    def _read_control_log(self, path: Path) -> list[Dict[str, Any]]:
        if not path.is_file():
            return []
        rows: list[Dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("control row is not an object")
                rows.append(row)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "a durable control log is malformed",
            ) from exc
        return rows

    def _target_invalidated_state(
        self,
        state: PipelineState,
        invalidated: Sequence[PipelineStage],
        *,
        resume_stage: PipelineStage,
        operation_id: str,
        timestamp: str,
    ) -> PipelineState:
        target = PipelineState.from_dict(state.to_dict())
        invalidated_names = {stage.value for stage in invalidated}
        invalidated_count_keys = {
            key for stage in invalidated for key in STAGE_COUNT_KEYS[stage]
        }
        target.counts = {
            key: value
            for key, value in target.counts.items()
            if key not in invalidated_count_keys
        }
        for stage_state in target.stages:
            if stage_state.stage not in invalidated_names:
                continue
            stage_state.status = "pending"
            stage_state.message = ""
            stage_state.started_at = None
            stage_state.completed_at = None
            stage_state.receipt_sha256 = None
        target.status = "queued"
        target.current_stage = resume_stage.value
        target.error = None
        target.updated_at = timestamp
        target.mutation_sequence += 1
        target.last_operation_id = operation_id
        return target

    def config_revision_summary(self) -> Dict[str, Any]:
        """Return bounded configuration revision metadata for the Studio."""
        if not self.config_history_path.is_file():
            return {"count": 0, "latest": None}
        latest = None
        count = 0
        for line in self.config_history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            count += 1
            latest = json.loads(line)
        return {"count": count, "latest": latest}

    def append_event(self, event: str, details: Optional[Mapping[str, Any]] = None) -> None:
        """Append an audit event after state has been safely persisted."""
        payload = {
            "timestamp": utc_now(),
            "event": event,
            "tenant_id": self.tenant_id,
            "asset_id": self.asset_id,
            "details": dict(details or {}),
        }
        atomic_append_jsonl(self.events_path, payload)

    def _config_revision_count(self) -> int:
        if not self.config_history_path.is_file():
            return 0
        return sum(
            1
            for line in self.config_history_path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        )

    def _append_config_revision(self, payload: Mapping[str, Any]) -> None:
        atomic_append_jsonl(self.config_history_path, payload)

    def _clear_stage_outputs(self, stages: Iterable[PipelineStage]) -> None:
        stages = tuple(stages)
        for stage in stages:
            specification = STAGE_SPECIFICATIONS[stage]
            relative_names = list(specification.required_outputs)
            relative_names.extend(specification.legacy_required_outputs)
            if stage == PipelineStage.INTENT_CLUSTERING:
                relative_names.append("cluster_lineage.jsonl")
            for relative_name in relative_names:
                path = self.artifact_path(stage, relative_name)
                if path.is_file():
                    path.unlink()
            for relative_name in specification.required_asset_outputs:
                path = self.root / relative_name
                if path.is_file():
                    path.unlink()
            for relative_name in specification.required_catalog_outputs:
                path = self.published_datasets / relative_name
                if path.is_file():
                    path.unlink()
            self.receipt_path(stage).unlink(missing_ok=True)
        try:
            self.published_datasets.rmdir()
        except OSError:
            pass

    def _invalidate_checkpoints_locked(
        self,
        state: PipelineState,
        boundary: PipelineStage,
    ) -> PipelineState:
        """Make a stage suffix nonauthoritative before best-effort cleanup."""
        ordered_stages = list(PipelineStage)
        invalidated = ordered_stages[ordered_stages.index(boundary) :]
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        target_state = self._target_invalidated_state(
            state,
            invalidated,
            resume_stage=boundary,
            operation_id=operation_id,
            timestamp=timestamp,
        )
        event_entry = {
            "timestamp": timestamp,
            "event": "checkpoint_rebuild_started",
            "tenant_id": self.tenant_id,
            "asset_id": self.asset_id,
            "operation_id": operation_id,
            "details": {"stage": boundary.value},
        }
        prepared = {
            "schema_version": "fapo-recovery-journal-v1",
            "operation_id": operation_id,
            "kind": "checkpoint_rebuild",
            "phase": "prepared",
            "prepared_at": timestamp,
            "before": {"state_sha256": file_sha256(self.state_path)},
            "target_state": target_state.to_dict(),
            "event_entry": event_entry,
            "invalidated_stages": [stage.value for stage in invalidated],
            "result": {"resume_from_stage": boundary.value},
        }
        self._append_journal_once(prepared)
        _fault_point("after_prepared_journal")
        atomic_write_json(self.state_path, target_state.to_dict())
        _fault_point("after_state_replace")
        self._append_jsonl_once(self.events_path, event_entry)
        _fault_point("after_event_append")
        _fault_point("before_cleanup")
        self._clear_stage_outputs(invalidated)
        self._commit_journal_operation(prepared)
        return target_state

    def artifact_summary(self) -> Dict[str, Any]:
        """Return API-safe paths and file counts for the canonical directories."""
        if self.uses_stage_layout:
            directories = [
                (STAGE_DIRECTORIES[stage.value], self.stage_directory(stage))
                for stage in PipelineStage
            ]
        else:
            directories = [
                (name, self.root / name)
                for name in LEGACY_DIRECTORIES
                if (self.root / name).is_dir()
            ]
        return {
            "asset_id": self.asset_id,
            "path": self.root.relative_to(self.tenant_root).as_posix(),
            "lineage": (
                read_json(self.lineage_path)
                if self.lineage_path.is_file()
                else None
            ),
            "directories": {
                name: {
                    "path": path.relative_to(self.tenant_root).as_posix(),
                    "file_count": sum(1 for item in path.rglob("*") if item.is_file()),
                }
                for name, path in directories
            },
            "config_revisions": self.config_revision_summary(),
        }


def _legacy_artifact_path(stage: str, relative_name: str) -> Path:
    """Map a canonical stage artifact back to its pre-stage-layout location."""
    name = Path(relative_name).name
    if stage == PipelineStage.RAW_INPUTS.value:
        return Path("raw_inputs") / name
    if stage == PipelineStage.PREPARED_INPUTS.value:
        return Path("prepared_inputs") / name
    if stage == PipelineStage.RUBRIC_EXTRACTION.value:
        parent = (
            "decision_assets"
            if name
            in {
                "feedback_evidence.jsonl",
                "candidate_guidelines.jsonl",
                "evaluation_guidelines.jsonl",
                "feedback_rubrics.jsonl",
            }
            else "prepared_inputs"
        )
        return Path(parent) / name
    if stage == PipelineStage.INTENT_CLUSTERING.value:
        return Path("decision_assets") / name
    if stage == PipelineStage.COVERAGE_DECISIONS.value:
        parent = "review_queues" if name == "labeling_queue.jsonl" else "decision_assets"
        return Path(parent) / name
    if stage == PipelineStage.LABEL_INFERENCE.value:
        parent = "prepared_inputs" if name == "inferred_cases.jsonl" else "decision_assets"
        return Path(parent) / name
    if stage == PipelineStage.SYNTHETIC_COVERAGE.value:
        parent = "prepared_inputs" if name == "synthetic_cases.jsonl" else "decision_assets"
        return Path(parent) / name
    if stage == PipelineStage.DATASET_SPLITS.value:
        return Path("dataset_splits") / name
    raise ValueError(f"Unknown evaluation asset stage: {stage}")


def list_asset_layouts(tenants_root: Path, tenant_id: str) -> Iterable[EvaluationAssetLayout]:
    """List safe asset workspaces newest-first by directory modification time."""
    if not SAFE_NAME.fullmatch(tenant_id):
        return []
    assets_root = tenants_root.resolve() / tenant_id / "evaluation_assets"
    if not assets_root.is_dir():
        return []
    layouts = [
        EvaluationAssetLayout(tenants_root, tenant_id, child.name)
        for child in assets_root.iterdir()
        if child.is_dir() and SAFE_NAME.fullmatch(child.name)
    ]
    return sorted(layouts, key=lambda item: item.root.stat().st_mtime, reverse=True)


def read_json(path: Path) -> Dict[str, Any]:
    """Read a JSON object or raise a clear error."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return raw


def _copy_jsonl(source: Path, destination: Path) -> None:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() != ".jsonl":
        raise ValueError(f"Evaluation asset inputs must be JSONL: {source}")
    atomic_copy_file(source, destination)


def _read_jsonl_rows(path: Optional[Path]) -> list[Dict[str, Any]]:
    rows, _ = _read_jsonl_rows_with_line_numbers(path)
    return rows


def _read_jsonl_rows_with_line_numbers(
    path: Optional[Path],
) -> tuple[list[Dict[str, Any]], list[int]]:
    if path is None:
        return [], []
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    if resolved.suffix.lower() != ".jsonl":
        raise ValueError(f"Evaluation asset inputs must be JSONL: {resolved}")
    rows: list[Dict[str, Any]] = []
    row_numbers: list[int] = []
    for line_number, line in enumerate(
        resolved.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{resolved}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object at {resolved}:{line_number}")
        rows.append(row)
        row_numbers.append(line_number)
    return rows, row_numbers


def _validate_source_rows(path: Path, *, labeled: bool) -> list[Dict[str, Any]]:
    rows, row_numbers = _read_jsonl_rows_with_line_numbers(path)
    if not rows:
        kind = "labeled feedback" if labeled else "unlabeled"
        raise ValueError(f"{path}: {kind} input is empty")
    validate_input_records(
        rows,
        labeled=labeled,
        path=path,
        row_numbers=row_numbers,
    )
    return rows


def _is_beneath(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _merge_jsonl_rows(
    parent_rows: Sequence[Mapping[str, Any]],
    added_rows: Sequence[Mapping[str, Any]],
    *,
    source: str,
) -> list[Dict[str, Any]]:
    merged: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in [*parent_rows, *added_rows]:
        record_id = str(row.get("record_id") or "").strip()
        if not record_id:
            raise ValueError(f"{source} record is missing record_id")
        if record_id in seen:
            raise ValueError(f"duplicate {source} record_id: {record_id}")
        seen.add(record_id)
        merged.append(dict(row))
    return merged


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
