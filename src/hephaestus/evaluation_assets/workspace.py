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

from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig, PipelineState

SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")


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
    def raw_inputs(self) -> Path:
        return self.root / "raw_inputs"

    @property
    def prepared_inputs(self) -> Path:
        return self.root / "prepared_inputs"

    @property
    def decision_assets(self) -> Path:
        return self.root / "decision_assets"

    @property
    def dataset_splits(self) -> Path:
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
    def feedback_path(self) -> Path:
        return self.raw_inputs / "labeled_feedback.jsonl"

    @property
    def unlabeled_path(self) -> Path:
        return self.raw_inputs / "unlabeled.jsonl"

    def ensure(self) -> None:
        """Create the canonical directories without requiring other tenant files."""
        for path in (
            self.raw_inputs,
            self.prepared_inputs,
            self.decision_assets,
            self.dataset_splits,
        ):
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

    def artifact_summary(self) -> Dict[str, Any]:
        """Return API-safe paths and file counts for the canonical directories."""
        return {
            "asset_id": self.asset_id,
            "path": self.root.relative_to(self.tenant_root).as_posix(),
            "directories": {
                name: {
                    "path": path.relative_to(self.tenant_root).as_posix(),
                    "file_count": sum(1 for item in path.rglob("*") if item.is_file()),
                }
                for name, path in (
                    ("raw_inputs", self.raw_inputs),
                    ("prepared_inputs", self.prepared_inputs),
                    ("decision_assets", self.decision_assets),
                    ("dataset_splits", self.dataset_splits),
                )
            },
        }


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
