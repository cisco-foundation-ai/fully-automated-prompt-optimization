# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Filesystem layout and persistence for evaluation assets."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

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
    PipelineStage.RUBRIC_EXTRACTION.value: "03_rubric_extraction",
    PipelineStage.INTENT_CLUSTERING.value: "04_intent_clustering",
    PipelineStage.COVERAGE_DECISIONS.value: "05_coverage_decisions",
    PipelineStage.LABEL_INFERENCE.value: "06_label_inference",
    PipelineStage.SYNTHETIC_COVERAGE.value: "07_synthetic_coverage",
    PipelineStage.DATASET_SPLITS.value: "08_dataset_splits",
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
        "feedback_rubrics.jsonl",
        "trusted_intents.jsonl",
        "trusted_cases.jsonl",
    ),
    PipelineStage.INTENT_CLUSTERING: ("intent_inventory.jsonl",),
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
        return self.stages_root / directory

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
    def feedback_path(self) -> Path:
        return self.artifact_path(PipelineStage.RAW_INPUTS, "labeled_feedback.jsonl")

    @property
    def unlabeled_path(self) -> Path:
        return self.artifact_path(PipelineStage.RAW_INPUTS, "unlabeled.jsonl")

    def ensure(self) -> None:
        """Create the canonical directories without requiring other tenant files."""
        if self.uses_stage_layout:
            paths = [self.stage_directory(stage) for stage in PipelineStage]
        else:
            paths = [self.root / name for name in LEGACY_DIRECTORIES]
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)

    def initialize(
        self,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
    ) -> PipelineState:
        """Copy raw inputs into the asset and persist initial config/state."""
        self.ensure()
        if self.config_path.exists() or self.state_path.exists():
            raise FileExistsError(f"Evaluation asset already exists: {self.root}")
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
        parent = "decision_assets" if name == "feedback_rubrics.jsonl" else "prepared_inputs"
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
