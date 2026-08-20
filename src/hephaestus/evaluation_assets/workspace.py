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
from src.hephaestus.evaluation_assets.control_jsonl import (
    read_strict_jsonl_objects,
)
from src.hephaestus.evaluation_assets.durability import (
    STAGE_SPECIFICATIONS,
    EvaluationAssetBusyError,
    EvaluationAssetImmutableError,
    EvaluationAssetIntegrityError,
    EvaluationAssetLegacyError,
    _replay_config_history,
    _verify_prospective_legacy_adoption_candidate,
    build_stage_receipt,
    file_sha256,
    persisted_json_sha256,
    released_parent_evidence,
    validate_legacy_release_candidate,
    verify_raw_snapshot_floor,
    verify_release_candidate,
    verify_released_asset,
)
from src.hephaestus.evaluation_assets.input_contract import validate_input_records
from src.hephaestus.evaluation_assets.journal_transitions import (
    JOURNAL_SCHEMA_VERSION,
    derive_adoption_plan,
    derive_audit_transition,
    derive_rebuild_plan,
    derive_release_publication_plan,
    derive_revision_plan,
)
from src.hephaestus.evaluation_assets.journal_validation import (
    validate_recovery_journal,
)
from src.hephaestus.evaluation_assets.lineage_validation import (
    LINEAGE_SCHEMA_VERSION,
    REUSE_SCHEMA_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
)
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.provenance import (
    build_legacy_provenance,
    build_legacy_stage_provenance,
)
from src.hephaestus.evaluation_assets.publication import (
    InstalledGeneration,
    build_generation_descriptor,
    build_release_pointer,
    generation_id_for_descriptor,
    install_generation,
    resolve_evaluation_asset_release,
    validate_historical_generation,
    write_release_pointer,
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
def utc_now() -> str:
    """Return a stable ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _persisted_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the exact bytes emitted by ``atomic_write_json``."""
    return (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _fault_point(name: str) -> None:
    """Provide a deterministic test seam between durable transaction phases."""


def _released_provider_decision(
    layout: "EvaluationAssetLayout",
    stage: PipelineStage,
    role: str,
) -> dict[str, str]:
    """Return verified producing identity or an explicit unavailable marker."""
    receipt = json.loads(layout.receipt_path(stage).read_text(encoding="utf-8"))
    provider_identity = receipt.get("provider_identity")
    if not isinstance(provider_identity, Mapping):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released provider identity is inconsistent",
        )
    if provider_identity.get("status") in {
        "unavailable",
        "historically_unavailable",
    }:
        return {"status": "unavailable"}
    identity = provider_identity.get(role)
    if not isinstance(identity, Mapping):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released provider identity is inconsistent",
        )
    provider = identity.get("provider")
    model = identity.get("model")
    if (
        identity.get("status") == "unavailable"
        or not isinstance(provider, str)
        or not provider.strip()
        or not isinstance(model, str)
        or not model.strip()
    ):
        return {"status": "unavailable"}
    return {
        "status": "available",
        "provider": provider.strip(),
        "model": model.strip(),
    }


def _required_extension_provider_identity(
    *,
    role: str,
    configured_provider: str,
    configured_model: str,
    decision: Mapping[str, str],
    updates: Mapping[str, Any],
    allow_replacement: bool = False,
) -> tuple[str, str]:
    """Require an explicit child choice when parent evidence cannot be inherited."""
    provider_field = f"{role}_provider"
    model_field = f"{role}_model"
    configured = (configured_provider, configured_model)
    if decision.get("status") == "unavailable":
        explicit_provider = updates.get(provider_field)
        explicit_model = updates.get(model_field)
        if (
            not isinstance(explicit_provider, str)
            or not explicit_provider.strip()
            or not isinstance(explicit_model, str)
            or not explicit_model.strip()
        ):
            raise ValueError(
                "extension requires an explicit provider identity because "
                f"the released parent {role} identity is unavailable"
            )
        return explicit_provider.strip(), explicit_model.strip()
    producing = (str(decision["provider"]), str(decision["model"]))
    if allow_replacement and producing != configured:
        explicit_provider = updates.get(provider_field)
        explicit_model = updates.get(model_field)
        if (
            not isinstance(explicit_provider, str)
            or not explicit_provider.strip()
            or not isinstance(explicit_model, str)
            or not explicit_model.strip()
        ):
            raise ValueError(
                "extension requires an explicit provider identity because "
                f"released parent {role} evidence differs from configuration"
            )
        return explicit_provider.strip(), explicit_model.strip()
    if producing != configured and (
        updates.get(provider_field),
        updates.get(model_field),
    ) != producing:
        raise ValueError(
            "extension requires an explicit provider identity matching "
            f"released parent {role} evidence"
        )
    return producing


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
        object.__setattr__(self, "tenants_root", self.tenants_root.resolve())

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

    def stage_provenance_path(self, stage: PipelineStage | str) -> Path:
        """Return a unique stage record path for canonical or historical layouts."""
        stage_name = stage.value if isinstance(stage, PipelineStage) else str(stage)
        stage_value = PipelineStage(stage_name)
        if self.uses_stage_layout:
            return self.artifact_path(stage_value, "provenance.json")
        index = list(PipelineStage).index(stage_value) + 1
        return self.root / "stage_provenance" / f"{index:02d}_{stage_name}.json"

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

    @property
    def generations_root(self) -> Path:
        """Return the immutable generation catalog for this asset."""
        return self.published_datasets / "generations"

    @property
    def release_pointer_path(self) -> Path:
        """Return the sole mutable catalog authority pointer."""
        return self.published_datasets / "release.json"

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
    def build_provenance_path(self) -> Path:
        return self.root / "build_provenance.json"

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
        initial_status: str = "draft",
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
                initial_status=initial_status,
            )

    def _initialize_extension_locked(
        self,
        parent: "EvaluationAssetLayout",
        *,
        additional_feedback: Optional[Path],
        additional_unlabeled: Optional[Path],
        clustering_mode: str,
        config_updates: Optional[Mapping[str, Any]],
        initial_status: str,
    ) -> PipelineState:
        """Initialize an extension while both parent and child locks are held."""
        if clustering_mode not in {"keep", "refresh"}:
            raise ValueError("clustering_mode must be 'keep' or 'refresh'")
        if initial_status not in {"draft", "queued"}:
            raise ValueError("initial_status must be draft or queued")
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
        updates = dict(config_updates or {})
        expected_rubric_identity = _required_extension_provider_identity(
            role="rubric",
            configured_provider=parent_config.rubric_provider,
            configured_model=parent_config.rubric_model,
            decision=_released_provider_decision(
                parent,
                PipelineStage.RUBRIC_EXTRACTION,
                "rubric",
            ),
            updates=updates,
        )
        expected_embedding_identity = _required_extension_provider_identity(
            role="embedding",
            configured_provider=parent_config.embedding_provider,
            configured_model=parent_config.embedding_model,
            decision=_released_provider_decision(
                parent,
                PipelineStage.INTENT_CLUSTERING,
                "embedding",
            ),
            updates=updates,
            allow_replacement=clustering_mode == "refresh",
        )
        merged_config = parent_config.to_dict()
        merged_config.update(updates)
        merged_config["tenant_id"] = self.tenant_id
        merged_config["asset_id"] = self.asset_id
        if "embedding_model" in updates and "embedding_provider" not in updates:
            merged_config["embedding_provider"] = (
                "tfidf"
                if updates["embedding_model"] == "tfidf"
                else "openai"
            )
        config = EvaluationAssetConfig.from_dict(merged_config)
        if (config.rubric_provider, config.rubric_model) != (
            expected_rubric_identity
        ):
            raise ValueError(
                "incremental extension must keep the parent's guideline model"
            )
        if clustering_mode == "keep" and (
            (config.embedding_provider, config.embedding_model)
            != expected_embedding_identity
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
            **{
                f"parent_{name}": parent.artifact_path(
                    PipelineStage.RUBRIC_EXTRACTION,
                    name,
                )
                for name in stage_three_artifacts
            },
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
                    "bytes": destination.stat().st_size,
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
        state.status = initial_status

        lineage = {
            "schema_version": LINEAGE_SCHEMA_VERSION,
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
            "schema_version": REUSE_SCHEMA_VERSION,
            "asset_id": self.asset_id,
            "parent_asset_id": parent.asset_id,
            "parent_release": parent_release,
            "parent_snapshot": {
                "schema_version": SNAPSHOT_SCHEMA_VERSION,
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
            if any(self.receipt_path(stage).exists() for stage in PipelineStage):
                raise EvaluationAssetLegacyError(
                    self.tenant_id,
                    self.asset_id,
                    "legacy receipt authority must be repaired before adoption",
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
                _replay_config_history(
                    self,
                    config,
                    state,
                    allow_pre_wal_history=True,
                )
                self._read_control_log(self.events_path)
                receipts: dict[PipelineStage, dict[str, Any]] = {}
                timestamp = utc_now()
                generation, target_manifests = self._prepare_legacy_release_artifacts(
                    config,
                    timestamp,
                )
                artifact_overrides = self._adoption_manifest_overrides(
                    target_manifests
                )
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
                        artifact_overrides=artifact_overrides,
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
            before_config = config.to_dict()
            before_state = read_json(self.state_path)
            target_receipts = {
                stage.value: receipts[stage] for stage in PipelineStage
            }
            stage_eight_receipt_sha256 = persisted_json_sha256(
                receipts[PipelineStage.DATASET_SPLITS]
            )
            pointer = build_release_pointer(
                tenant_id=self.tenant_id,
                asset_id=self.asset_id,
                generation=generation,
                stage_8_receipt_sha256=stage_eight_receipt_sha256,
                build_provenance_sha256=file_sha256(
                    self.build_provenance_path
                ),
                published_at=timestamp,
            )
            plan = derive_adoption_plan(
                before_config,
                before_state,
                target_receipts,
                pointer,
                operation_id=operation_id,
                prepared_at=timestamp,
            )
            target_state = PipelineState.from_dict(plan["target_state"])
            try:
                _verify_prospective_legacy_adoption_candidate(
                    self,
                    target_state,
                    receipts,
                    legacy_state=state,
                    artifact_overrides=artifact_overrides,
                )
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
                    "required release evidence failed verification",
                ) from exc
            prepared = {
                "schema_version": JOURNAL_SCHEMA_VERSION,
                "operation_id": operation_id,
                "kind": "legacy_adoption",
                "phase": "prepared",
                "prepared_at": timestamp,
                "request": {"release_pointer": pointer},
                "before_config": before_config,
                "before_state": before_state,
                "before": {
                    "config_sha256": file_sha256(self.config_path),
                    "state_sha256": file_sha256(self.state_path),
                    "release": _file_descriptor(self.release_pointer_path),
                },
                "target": {
                    "config_sha256": file_sha256(self.config_path),
                    "state_sha256": persisted_json_sha256(plan["target_state"]),
                    "receipt_sha256": plan["receipt_sha256"],
                    "release_sha256": persisted_json_sha256(pointer),
                    "stage_8_receipt_sha256": stage_eight_receipt_sha256,
                    "generation_manifest_sha256": (
                        generation.generation_manifest_sha256
                    ),
                    "build_provenance_sha256": file_sha256(
                        self.build_provenance_path
                    ),
                },
                "target_receipts": target_receipts,
                "before_manifests": {
                    "asset_manifest": _file_descriptor(self.manifest_path),
                    "dataset_manifest": _file_descriptor(
                        self.artifact_path(
                            PipelineStage.DATASET_SPLITS,
                            "dataset_manifest.json",
                        )
                    ),
                    "generation_manifest": _file_descriptor(
                        self.artifact_path(
                            PipelineStage.DATASET_SPLITS,
                            "generation_manifest.json",
                        )
                    ),
                },
                "target_manifests": target_manifests,
                "target_state": plan["target_state"],
                "event_entry": plan["event_entry"],
                "result": plan["result"],
                "audit": self._journal_audit_transitions(
                    history_entry=None,
                    event_entry=plan["event_entry"],
                ),
            }
            self._append_journal_once(prepared)
            _fault_point("after_prepared_journal")
            self._install_adoption_manifests(prepared)
            self._install_adoption_receipts(prepared)
            _fault_point("after_receipts_install")
            verify_release_candidate(
                self,
                target_state,
                release_pointer=pointer,
            )
            write_release_pointer(self.published_datasets, pointer)
            _fault_point("after_adoption_pointer_replace")
            resolved = resolve_evaluation_asset_release(
                self.published_datasets,
                expected_tenant_id=self.tenant_id,
                expected_asset_id=self.asset_id,
                expected_stage_8_receipt_sha256=stage_eight_receipt_sha256,
                trusted_root=self.tenant_root,
            )
            if resolved.pointer_sha256 != persisted_json_sha256(pointer):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "adoption release pointer does not match its WAL target",
                )
            verify_release_candidate(self, target_state)
            atomic_write_json(self.state_path, plan["target_state"])
            _fault_point("after_state_replace")
            verify_released_asset(self, target_state)
            self._append_jsonl_once(self.events_path, plan["event_entry"])
            _fault_point("after_event_append")
            self._commit_journal_operation(prepared)
            return target_state

    def _prepare_legacy_release_artifacts(
        self,
        config: EvaluationAssetConfig,
        timestamp: str,
    ) -> tuple[InstalledGeneration, dict[str, Any]]:
        """Convert verified pre-v2 outputs into historical provenance and a generation."""
        input_manifest = read_json(
            self.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json")
        )
        copied_inputs = {}
        for name, path in (
            ("labeled_feedback", self.feedback_path),
            ("unlabeled", self.unlabeled_path),
        ):
            details = input_manifest["inputs"][name]
            copied_inputs[name] = {
                "path": path.relative_to(self.root).as_posix(),
                "bytes": path.stat().st_size,
                "rows": details["rows"],
                "sha256": details["sha256"],
            }
        lineage = read_json(self.lineage_path) if self.lineage_path.is_file() else None
        provenance = build_legacy_provenance(
            resolved_configuration=config.to_dict(),
            copied_inputs=copied_inputs,
            lineage=lineage,
            split_seed=config.split_seed,
            created_at=timestamp,
        )
        split_paths = {
            split: self.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
            for split in ("train", "validation", "test", "regression_trusted")
        }
        descriptor = build_generation_descriptor(
            split_paths,
            provenance["identity_sha256"],
        )
        generation_id = generation_id_for_descriptor(descriptor)
        provenance_paths = [self.stage_provenance_path(stage) for stage in PipelineStage]
        _validate_asset_write_targets(
            self.root,
            [
                *provenance_paths,
                self.build_provenance_path,
                *(self.receipt_path(stage) for stage in PipelineStage),
                self.manifest_path,
                self.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "dataset_manifest.json",
                ),
                self.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "generation_manifest.json",
                ),
                self.state_path,
                self.events_path,
                self.recovery_journal_path,
            ],
        )
        _validate_asset_write_targets(
            self.tenant_root,
            [self.release_pointer_path],
        )
        _validate_asset_write_targets(
            self.tenant_root,
            [
                self.published_datasets,
                self.generations_root,
                self.generations_root / generation_id,
            ],
            target_kind="directory",
        )
        existing_generation = self.generations_root / generation_id
        if existing_generation.exists():
            installed = validate_historical_generation(
                existing_generation,
                expected_tenant_id=self.tenant_id,
                expected_asset_id=self.asset_id,
                trusted_root=self.tenant_root,
            )
            if dict(installed.descriptor) != descriptor:
                raise ValueError("legacy generation collision is inconsistent")
        for stage in PipelineStage:
            atomic_write_json(
                self.stage_provenance_path(stage),
                build_legacy_stage_provenance(stage.value),
            )
        atomic_write_json(self.build_provenance_path, provenance)
        generation = install_generation(
            self.published_datasets,
            tenant_id=self.tenant_id,
            asset_id=self.asset_id,
            split_paths=split_paths,
            build_fingerprint=provenance["identity_sha256"],
            fault_hook=_fault_point,
            trusted_root=self.tenant_root,
        )
        generation_manifest = read_json(
            generation.generation_dir / "generation_manifest.json"
        )
        manifest = read_json(self.manifest_path)
        generation_directory = generation.generation_dir.relative_to(
            self.tenants_root.parent
        ).as_posix()
        manifest["published_datasets"] = {
            "directory": self.published_datasets.relative_to(
                self.tenant_root
            ).as_posix(),
            "release_pointer": self.release_pointer_path.relative_to(
                self.tenant_root
            ).as_posix(),
            "generation_id": generation.generation_id,
            "generation_manifest_sha256": generation.generation_manifest_sha256,
            "build_provenance_sha256": file_sha256(self.build_provenance_path),
            "build_fingerprint": provenance["identity_sha256"],
            "files": {
                split: f"{generation_directory}/{split}.jsonl"
                for split in ("train", "validation", "test", "regression_trusted")
            },
        }
        return generation, {
            "asset_manifest": manifest,
            "dataset_manifest": manifest,
            "generation_manifest": generation_manifest,
        }

    def _adoption_manifest_overrides(
        self,
        manifests: Mapping[str, Any],
    ) -> dict[Path, bytes]:
        """Return exact prospective bytes for pre-WAL adoption verification."""
        return {
            self.manifest_path: _persisted_json_bytes(manifests["asset_manifest"]),
            self.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "dataset_manifest.json",
            ): _persisted_json_bytes(manifests["dataset_manifest"]),
            self.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "generation_manifest.json",
            ): _persisted_json_bytes(manifests["generation_manifest"]),
        }

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

    def _publish_release_locked(
        self,
        state: PipelineState,
        generation: InstalledGeneration,
    ) -> PipelineState:
        """Publish one complete generation through the authenticated v2 WAL."""
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        stage_eight_receipt_sha256 = file_sha256(
            self.receipt_path(PipelineStage.DATASET_SPLITS)
        )
        pointer = build_release_pointer(
            tenant_id=self.tenant_id,
            asset_id=self.asset_id,
            generation=generation,
            stage_8_receipt_sha256=stage_eight_receipt_sha256,
            build_provenance_sha256=file_sha256(self.build_provenance_path),
            published_at=timestamp,
        )
        before_config = self.load_config().to_dict()
        before_state = state.to_dict()
        plan = derive_release_publication_plan(
            before_config,
            before_state,
            pointer,
            operation_id=operation_id,
            prepared_at=timestamp,
        )
        release_before = _file_descriptor(self.release_pointer_path)
        prepared = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "operation_id": operation_id,
            "kind": "release_publication",
            "phase": "prepared",
            "prepared_at": timestamp,
            "request": {"release_pointer": pointer},
            "before_config": before_config,
            "before_state": before_state,
            "before": {
                "config_sha256": file_sha256(self.config_path),
                "state_sha256": file_sha256(self.state_path),
                "release": release_before,
            },
            "target": {
                "config_sha256": file_sha256(self.config_path),
                "state_sha256": persisted_json_sha256(plan["target_state"]),
                "release_sha256": persisted_json_sha256(pointer),
                "stage_8_receipt_sha256": stage_eight_receipt_sha256,
                "generation_manifest_sha256": (
                    generation.generation_manifest_sha256
                ),
                "build_provenance_sha256": file_sha256(
                    self.build_provenance_path
                ),
            },
            "target_state": plan["target_state"],
            "event_entry": plan["event_entry"],
            "result": plan["result"],
            "audit": self._journal_audit_transitions(
                history_entry=None,
                event_entry=plan["event_entry"],
            ),
        }
        self._append_journal_once(prepared)
        _fault_point("after_release_publication_prepared")
        target_state = PipelineState.from_dict(plan["target_state"])
        verify_release_candidate(
            self,
            target_state,
            release_pointer=pointer,
        )
        _fault_point("before_release_pointer_replace")
        write_release_pointer(self.published_datasets, pointer)
        _fault_point("after_release_pointer_replace")
        resolved = resolve_evaluation_asset_release(
            self.published_datasets,
            expected_tenant_id=self.tenant_id,
            expected_asset_id=self.asset_id,
            expected_stage_8_receipt_sha256=stage_eight_receipt_sha256,
            trusted_root=self.tenant_root,
        )
        if resolved.pointer_sha256 != prepared["target"]["release_sha256"]:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "installed release pointer does not match its WAL target",
            )
        _fault_point("after_release_pointer_verify")
        verify_release_candidate(self, target_state)
        atomic_write_json(self.state_path, plan["target_state"])
        _fault_point("after_released_state_replace")
        verify_released_asset(self, target_state)
        self._append_jsonl_once(self.events_path, plan["event_entry"])
        _fault_point("after_release_event_append")
        self._commit_journal_operation(prepared)
        _fault_point("after_release_publication_commit")
        verify_released_asset(self, target_state)
        return target_state

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
        verify_raw_snapshot_floor(self, state)
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

        revision = self._config_revision_count() + 1
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        before_config = current.to_dict()
        before_state = state.to_dict()
        plan = derive_revision_plan(
            before_config,
            before_state,
            updates,
            operation_id=operation_id,
            prepared_at=timestamp,
            revision=revision,
        )
        target_state = PipelineState.from_dict(plan["target_state"])
        result = dict(plan["result"])
        prepared = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "operation_id": operation_id,
            "kind": "configuration_revision",
            "phase": "prepared",
            "prepared_at": timestamp,
            "request": {"updates": dict(updates)},
            "before_config": before_config,
            "before_state": before_state,
            "before": {
                "config_sha256": file_sha256(self.config_path),
                "state_sha256": file_sha256(self.state_path),
            },
            "target": {
                "config_sha256": persisted_json_sha256(plan["target_config"]),
                "state_sha256": persisted_json_sha256(plan["target_state"]),
            },
            "target_config": plan["target_config"],
            "target_state": plan["target_state"],
            "history_entry": plan["history_entry"],
            "event_entry": plan["event_entry"],
            "invalidated_stages": plan["invalidated_stages"],
            "result": result,
            "audit": self._journal_audit_transitions(
                history_entry=plan["history_entry"],
                event_entry=plan["event_entry"],
            ),
        }
        self._append_journal_once(prepared)
        _fault_point("after_prepared_journal")
        atomic_write_json(self.config_path, plan["target_config"])
        _fault_point("after_config_replace")
        atomic_write_json(self.state_path, target_state.to_dict())
        _fault_point("after_state_replace")
        self._append_jsonl_once(self.config_history_path, plan["history_entry"])
        _fault_point("after_history_append")
        self._append_jsonl_once(self.events_path, plan["event_entry"])
        _fault_point("after_event_append")
        _fault_point("before_cleanup")
        self._clear_stage_outputs(
            [PipelineStage(value) for value in plan["invalidated_stages"]]
        )
        self._commit_journal_operation(prepared)
        return result

    def recover(self, *, lock_timeout: float = 0) -> list[str]:
        """Roll every prepared recovery operation forward exactly once."""
        with self.asset_lock(lock_timeout):
            return self._recover_locked()

    def _recover_locked(self) -> list[str]:
        """Recover prepared operations while the caller holds the asset lock."""
        entries = self._read_control_log(self.recovery_journal_path)
        try:
            journal = validate_recovery_journal(self, entries)
            outstanding = journal.outstanding
            if outstanding is not None and outstanding.get("kind") == "legacy_adoption":
                target_state = PipelineState.from_dict(outstanding["target_state"])
                before_state = PipelineState.from_dict(outstanding["before_state"])
                request = outstanding.get("request")
                prepared_release = (
                    request.get("release_pointer")
                    if isinstance(request, Mapping)
                    else None
                )
                if not isinstance(prepared_release, Mapping):
                    raise ValueError("adoption release target is invalid")
                _validate_source_rows(self.feedback_path, labeled=True)
                _validate_source_rows(self.unlabeled_path, labeled=False)
                target_receipts = outstanding.get("target_receipts")
                if not isinstance(target_receipts, Mapping):
                    raise ValueError("adoption receipt target is invalid")
                target_manifests = outstanding.get("target_manifests")
                if not isinstance(target_manifests, Mapping):
                    raise ValueError("adoption manifest target is invalid")
                target_asset_manifest = target_manifests.get("asset_manifest")
                if not isinstance(target_asset_manifest, Mapping):
                    raise ValueError("adoption manifest target is invalid")
                validate_legacy_release_candidate(
                    self,
                    before_state,
                    self.load_config(),
                    prepared_release=prepared_release,
                    manifest_payload=target_asset_manifest,
                )
                _verify_prospective_legacy_adoption_candidate(
                    self,
                    target_state,
                    {
                        stage: target_receipts[stage.value]
                        for stage in PipelineStage
                    },
                    legacy_state=before_state,
                    artifact_overrides=self._adoption_manifest_overrides(
                        target_manifests
                    ),
                )
        except (
            EvaluationAssetLegacyError,
            KeyError,
            OSError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "recovery journal authority is inconsistent",
            ) from exc
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
        current_state = self.load_state()
        if current_state.status == "released":
            verify_released_asset(self, current_state)
        return recovered

    def _roll_forward_prepared(self, entry: Mapping[str, Any]) -> None:
        kind = entry.get("kind")
        if kind == "release_publication":
            request = entry.get("request")
            pointer = (
                request.get("release_pointer")
                if isinstance(request, Mapping)
                else None
            )
            target_state = entry.get("target_state")
            if not isinstance(pointer, Mapping) or not isinstance(
                target_state, Mapping
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing release targets",
                )
            generation_id = str(pointer.get("generation_id") or "")
            generation = validate_historical_generation(
                self.generations_root / generation_id,
                expected_tenant_id=self.tenant_id,
                expected_asset_id=self.asset_id,
                trusted_root=self.tenant_root,
            )
            target = entry.get("target")
            if not isinstance(target, Mapping) or (
                generation.generation_manifest_sha256
                != target.get("generation_manifest_sha256")
            ):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery generation does not match its WAL target",
                )
            recovered_state = PipelineState.from_dict(target_state)
            verify_release_candidate(
                self,
                recovered_state,
                release_pointer=pointer,
            )
            write_release_pointer(self.published_datasets, pointer)
            resolved = resolve_evaluation_asset_release(
                self.published_datasets,
                expected_tenant_id=self.tenant_id,
                expected_asset_id=self.asset_id,
                expected_stage_8_receipt_sha256=str(
                    target.get("stage_8_receipt_sha256") or ""
                ),
                trusted_root=self.tenant_root,
            )
            if resolved.pointer_sha256 != target.get("release_sha256"):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovered release pointer does not match its WAL target",
                )
            verify_release_candidate(self, recovered_state)
            atomic_write_json(self.state_path, target_state)
            verify_released_asset(self, recovered_state)
            event_entry = entry.get("event_entry")
            if isinstance(event_entry, Mapping):
                self._append_jsonl_once(self.events_path, event_entry)
            self._commit_journal_operation(entry)
            verify_released_asset(self, recovered_state)
            return
        if kind == "legacy_adoption":
            self._install_adoption_manifests(entry)
            self._install_adoption_receipts(entry)
            request = entry.get("request")
            pointer = (
                request.get("release_pointer")
                if isinstance(request, Mapping)
                else None
            )
            if not isinstance(pointer, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing its adoption pointer",
                )
            target_state = entry.get("target_state")
            if not isinstance(target_state, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal is missing target state",
                )
            recovered_state = PipelineState.from_dict(target_state)
            verify_release_candidate(
                self,
                recovered_state,
                release_pointer=pointer,
            )
            write_release_pointer(self.published_datasets, pointer)
            resolve_evaluation_asset_release(
                self.published_datasets,
                expected_tenant_id=self.tenant_id,
                expected_asset_id=self.asset_id,
                expected_stage_8_receipt_sha256=str(
                    pointer.get("stage_8_receipt_sha256") or ""
                ),
                trusted_root=self.tenant_root,
            )
            verify_release_candidate(self, recovered_state)
            atomic_write_json(self.state_path, target_state)
            verify_released_asset(self, recovered_state)
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

    def _install_adoption_manifests(self, entry: Mapping[str, Any]) -> None:
        manifests = entry.get("target_manifests")
        if not isinstance(manifests, Mapping) or set(manifests) != {
            "asset_manifest",
            "dataset_manifest",
            "generation_manifest",
        }:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "the recovery journal has an incomplete adoption manifest set",
            )
        targets = (
            (self.manifest_path, manifests["asset_manifest"],
             "after_adoption_asset_manifest_replace"),
            (
                self.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "dataset_manifest.json",
                ),
                manifests["dataset_manifest"],
                "after_adoption_dataset_manifest_replace",
            ),
            (
                self.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "generation_manifest.json",
                ),
                manifests["generation_manifest"],
                "after_adoption_generation_manifest_replace",
            ),
        )
        for path, payload, fault_name in targets:
            if not isinstance(payload, Mapping):
                raise EvaluationAssetIntegrityError(
                    self.tenant_id,
                    self.asset_id,
                    "the recovery journal has an invalid adoption manifest",
                )
            target_bytes = _persisted_json_bytes(payload)
            if not path.is_file() or path.read_bytes() != target_bytes:
                atomic_write_json(path, payload)
            _fault_point(fault_name)

    def _commit_journal_operation(self, prepared: Mapping[str, Any]) -> None:
        self._append_journal_once(
            {
                "schema_version": JOURNAL_SCHEMA_VERSION,
                "operation_id": str(prepared["operation_id"]),
                "kind": str(prepared["kind"]),
                "phase": "committed",
                "committed_at": utc_now(),
            }
        )

    def _journal_audit_transitions(
        self,
        *,
        history_entry: Mapping[str, Any] | None,
        event_entry: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Authenticate both append-only prefixes before preparing a mutation."""
        self._read_control_log(self.config_history_path)
        self._read_control_log(self.events_path)
        history_present = self.config_history_path.is_file()
        history_bytes = (
            self.config_history_path.read_bytes() if history_present else b""
        )
        events_present = self.events_path.is_file()
        events_bytes = self.events_path.read_bytes() if events_present else b""
        return {
            "config_history": derive_audit_transition(
                history_bytes,
                present=history_present,
                appended_row=history_entry,
            ),
            "events": derive_audit_transition(
                events_bytes,
                present=events_present,
                appended_row=event_entry,
            ),
        }

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
        try:
            rows = read_strict_jsonl_objects(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise EvaluationAssetIntegrityError(
                self.tenant_id,
                self.asset_id,
                "a durable control log is malformed",
            ) from exc
        return rows

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
            self.receipt_path(stage).unlink(missing_ok=True)

    def _invalidate_checkpoints_locked(
        self,
        state: PipelineState,
        boundary: PipelineStage,
    ) -> PipelineState:
        """Make a stage suffix nonauthoritative before best-effort cleanup."""
        operation_id = uuid.uuid4().hex
        timestamp = utc_now()
        before_config = self.load_config().to_dict()
        before_state = state.to_dict()
        plan = derive_rebuild_plan(
            before_config,
            before_state,
            boundary,
            operation_id=operation_id,
            prepared_at=timestamp,
        )
        target_state = PipelineState.from_dict(plan["target_state"])
        prepared = {
            "schema_version": JOURNAL_SCHEMA_VERSION,
            "operation_id": operation_id,
            "kind": "checkpoint_rebuild",
            "phase": "prepared",
            "prepared_at": timestamp,
            "request": {"boundary": boundary.value},
            "before_config": before_config,
            "before_state": before_state,
            "before": {
                "config_sha256": file_sha256(self.config_path),
                "state_sha256": file_sha256(self.state_path),
            },
            "target": {
                "config_sha256": file_sha256(self.config_path),
                "state_sha256": persisted_json_sha256(plan["target_state"]),
            },
            "target_state": plan["target_state"],
            "event_entry": plan["event_entry"],
            "invalidated_stages": plan["invalidated_stages"],
            "result": plan["result"],
            "audit": self._journal_audit_transitions(
                history_entry=None,
                event_entry=plan["event_entry"],
            ),
        }
        self._append_journal_once(prepared)
        _fault_point("after_prepared_journal")
        atomic_write_json(self.state_path, target_state.to_dict())
        _fault_point("after_state_replace")
        self._append_jsonl_once(self.events_path, plan["event_entry"])
        _fault_point("after_event_append")
        _fault_point("before_cleanup")
        self._clear_stage_outputs(
            [PipelineStage(value) for value in plan["invalidated_stages"]]
        )
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


def _file_descriptor(path: Path) -> dict[str, Any]:
    """Describe one optional regular release pointer for the recovery WAL."""
    if path.is_symlink():
        raise ValueError("release pointer cannot be a symlink")
    if not path.exists():
        return {"present": False, "bytes": 0, "sha256": None}
    if not path.is_file():
        raise ValueError("release pointer must be a regular file")
    return {
        "present": True,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


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


def _validate_asset_write_targets(
    root: Path,
    targets: Sequence[Path],
    *,
    target_kind: str = "file",
) -> None:
    """Reject any prospective asset write whose path traverses a symlink."""
    if target_kind not in {"file", "directory"}:
        raise ValueError("evaluation asset write target kind is invalid")
    lexical_root = root.absolute()
    if lexical_root.is_symlink():
        raise ValueError("evaluation asset root cannot be a symlink")
    resolved_root = lexical_root.resolve(strict=True)
    for supplied in targets:
        target = supplied.absolute()
        if not _is_beneath(target, lexical_root):
            raise ValueError("evaluation asset write target escapes its root")
        relative = target.relative_to(lexical_root)
        current = lexical_root
        for component in relative.parts:
            current = current / component
            if current.is_symlink():
                raise ValueError("evaluation asset write target traverses a symlink")
            if current.exists() and current != target and not current.is_dir():
                raise ValueError("evaluation asset write target parent is not a directory")
        if target.exists() and (
            (target_kind == "file" and not target.is_file())
            or (target_kind == "directory" and not target.is_dir())
        ):
            raise ValueError("evaluation asset write target has the wrong file type")
        resolved_target = target.resolve(strict=False)
        if not _is_beneath(resolved_target, resolved_root):
            raise ValueError("evaluation asset write target escapes its root")


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
