# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Background service used by the CLI and Explorer UI."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Tuple

from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig
from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


class EvaluationAssetRunManager:
    """Start core pipeline runs while progress remains filesystem-backed."""

    def __init__(self, tenants_root: Path) -> None:
        self.tenants_root = tenants_root.resolve()
        self.workspace_root = self.tenants_root.parent
        self._threads: Dict[Tuple[str, str], threading.Thread] = {}
        self._lock = threading.Lock()

    def start(
        self,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
    ) -> Dict[str, Any]:
        """Copy inputs, persist the job, and start it in a background thread."""
        feedback_source = self._allowed_input(feedback_source)
        unlabeled_source = self._allowed_input(unlabeled_source)
        key = (config.tenant_id, config.asset_id)
        with self._lock:
            existing = self._threads.get(key)
            if existing is not None and existing.is_alive():
                raise RuntimeError("evaluation asset pipeline is already running")
            pipeline = EvaluationAssetPipeline.create(
                self.tenants_root,
                config,
                feedback_source,
                unlabeled_source,
            )
            thread = threading.Thread(
                target=self._run_pipeline,
                args=(key, pipeline),
                name=f"evaluation-asset-{config.tenant_id}-{config.asset_id}",
                daemon=True,
            )
            self._threads[key] = thread
            thread.start()
        return pipeline.layout.load_state().to_dict()

    def resume(self, tenant_id: str, asset_id: str) -> Dict[str, Any]:
        """Resume a failed or interrupted persisted pipeline."""
        key = (tenant_id, asset_id)
        with self._lock:
            existing = self._threads.get(key)
            if existing is not None and existing.is_alive():
                raise RuntimeError("evaluation asset pipeline is already running")
            layout = EvaluationAssetLayout(self.tenants_root, tenant_id, asset_id)
            pipeline = EvaluationAssetPipeline(layout)
            thread = threading.Thread(
                target=self._run_pipeline,
                args=(key, pipeline),
                name=f"evaluation-asset-{tenant_id}-{asset_id}",
                daemon=True,
            )
            self._threads[key] = thread
            thread.start()
        return layout.load_state().to_dict()

    def is_running(self, tenant_id: str, asset_id: str) -> bool:
        """Return whether this process currently owns a live pipeline thread."""
        with self._lock:
            thread = self._threads.get((tenant_id, asset_id))
            return bool(thread and thread.is_alive())

    def _allowed_input(self, path: Path) -> Path:
        resolved = path.expanduser().resolve()
        if self.workspace_root not in resolved.parents:
            raise ValueError(
                f"input path must be inside the FAPO workspace: {self.workspace_root}"
            )
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        return resolved

    def _run_pipeline(
        self,
        key: Tuple[str, str],
        pipeline: EvaluationAssetPipeline,
    ) -> None:
        try:
            pipeline.run()
        except Exception:
            # The pipeline persists the full error and failed stage before raising.
            return
        finally:
            with self._lock:
                current = self._threads.get(key)
                if current is threading.current_thread():
                    self._threads.pop(key, None)
