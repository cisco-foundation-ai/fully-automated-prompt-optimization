# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Filesystem layout and persistence for evaluation assets."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

from src.hephaestus.evaluation_assets.input_contract import validate_input_records
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
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
    def stages_root(self) -> Path:
        return self.root / "stages"

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
    ) -> PipelineState:
        """Copy raw inputs into the asset and persist initial config/state."""
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
    ) -> PipelineState:
        """Create a new immutable asset version from a completed parent."""
        if clustering_mode not in {"keep", "refresh"}:
            raise ValueError("clustering_mode must be 'keep' or 'refresh'")
        if parent.tenant_id != self.tenant_id:
            raise ValueError("parent and child assets must belong to the same tenant")
        if parent.asset_id == self.asset_id:
            raise ValueError("extended asset must use a new asset_id")
        if parent.load_state().status != "completed":
            raise ValueError("parent evaluation asset must be completed")
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
        _atomic_write_jsonl(self.feedback_path, feedback_rows)
        _atomic_write_jsonl(self.unlabeled_path, unlabeled_rows)

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
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
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
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
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
            shutil.copy2(source, destination)
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
            _atomic_write_jsonl(
                self.artifact_path(
                    PipelineStage.INTENT_CLUSTERING,
                    "cluster_lineage.jsonl",
                ),
                lineage_rows,
            )
            reused_artifacts.append("cluster_lineage.jsonl")

        timestamp = utc_now()
        state = PipelineState.new(config, timestamp)
        if clustering_mode == "keep":
            stage_state = next(
                item
                for item in state.stages
                if item.stage == PipelineStage.INTENT_CLUSTERING.value
            )
            stage_state.status = "completed"
            stage_state.started_at = timestamp
            stage_state.completed_at = timestamp
            stage_state.message = (
                f"Reused from parent asset {parent.asset_id}"
            )
            state.counts["intent_clusters"] = len(
                _read_jsonl_rows(
                    self.artifact_path(
                        PipelineStage.INTENT_CLUSTERING,
                        "intent_inventory.jsonl",
                    )
                )
            )

        lineage = {
            "asset_id": self.asset_id,
            "parent_asset_id": parent.asset_id,
            "creation_mode": "incremental_feedback",
            "clustering_mode": clustering_mode,
            "created_at": timestamp,
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

    def revise_config(self, updates: Mapping[str, Any]) -> Dict[str, Any]:
        """Persist decision changes and invalidate their dependent stages."""
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
        self._clear_stage_outputs(invalidated)

        state = self.load_state()
        invalidated_names = {stage.value for stage in invalidated}
        invalidated_count_keys = {
            key for stage in invalidated for key in STAGE_COUNT_KEYS[stage]
        }
        state.counts = {
            key: value
            for key, value in state.counts.items()
            if key not in invalidated_count_keys
        }
        for stage_state in state.stages:
            if stage_state.stage not in invalidated_names:
                continue
            stage_state.status = "pending"
            stage_state.message = ""
            stage_state.started_at = None
            stage_state.completed_at = None
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
        state.status = "queued"
        state.current_stage = resume_stage.value
        state.error = None

        atomic_write_json(self.config_path, revised.to_dict())
        self.save_state(state)
        revision = self._config_revision_count() + 1
        entry = {
            "timestamp": utc_now(),
            "revision": revision,
            "event": "configuration_updated",
            "changed_fields": changes,
            "invalidated_from_stage": earliest.value,
            "resume_from_stage": resume_stage.value,
        }
        self._append_config_revision(entry)
        self.append_event(
            "configuration_updated",
            {
                "revision": revision,
                "changed_fields": changes,
                "invalidated_from_stage": earliest.value,
                "resume_from_stage": resume_stage.value,
            },
        )
        return {
            "changed_fields": changes,
            "invalidated_from_stage": earliest.value,
            "resume_from_stage": resume_stage.value,
            "revision": revision,
        }

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
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

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
        self.config_history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True) + "\n")

    def _clear_stage_outputs(self, stages: Iterable[PipelineStage]) -> None:
        stages = tuple(stages)
        for stage in stages:
            if self.uses_stage_layout:
                directory = self.stage_directory(stage)
                if directory.exists():
                    shutil.rmtree(directory)
                directory.mkdir(parents=True, exist_ok=True)
                continue
            if stage == PipelineStage.DATASET_SPLITS:
                directory = self.root / "dataset_splits"
                if directory.exists():
                    shutil.rmtree(directory)
                directory.mkdir(parents=True, exist_ok=True)
                continue
            for relative_name in STAGE_ARTIFACTS.get(stage, ()):
                path = self.artifact_path(stage, relative_name)
                if path.is_file():
                    path.unlink()
        if PipelineStage.DATASET_SPLITS in stages and self.manifest_path.is_file():
            self.manifest_path.unlink()
        if (
            PipelineStage.DATASET_SPLITS in stages
            and self.published_datasets.is_dir()
        ):
            shutil.rmtree(self.published_datasets)

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


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write JSON using an atomic same-directory replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(dict(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def _copy_jsonl(source: Path, destination: Path) -> None:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() != ".jsonl":
        raise ValueError(f"Evaluation asset inputs must be JSONL: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "wb",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        with source.open("rb") as source_handle:
            shutil.copyfileobj(source_handle, handle)
        temporary_path = Path(handle.name)
    temporary_path.replace(destination)


def _read_jsonl_rows(path: Optional[Path]) -> list[Dict[str, Any]]:
    if path is None:
        return []
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    if resolved.suffix.lower() != ".jsonl":
        raise ValueError(f"Evaluation asset inputs must be JSONL: {resolved}")
    rows: list[Dict[str, Any]] = []
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
    return rows


def _validate_source_rows(path: Path, *, labeled: bool) -> list[Dict[str, Any]]:
    rows = _read_jsonl_rows(path)
    if not rows:
        kind = "labeled feedback" if labeled else "unlabeled"
        raise ValueError(f"{path}: {kind} input is empty")
    validate_input_records(rows, labeled=labeled, path=path)
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


def _atomic_write_jsonl(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
