# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Background service used by the CLI and Explorer UI."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from src.hephaestus.evaluation_assets.durability import EvaluationAssetBusyError
from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig
from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


@dataclass
class _WorkerAdmission:
    """Two-phase decision shared between a request and its background worker."""

    lock_decided: threading.Event = field(default_factory=threading.Event)
    preflight_decided: threading.Event = field(default_factory=threading.Event)
    lock_acquired: bool = False
    preflight_accepted: bool = False
    error: Optional[Exception] = None


class EvaluationAssetRunManager:
    """Start core pipeline runs while progress remains filesystem-backed."""

    def __init__(self, tenants_root: Path) -> None:
        self.tenants_root = tenants_root.resolve()
        self._threads: Dict[Tuple[str, str], threading.Thread] = {}
        self._lock = threading.Lock()

    def start(
        self,
        config: EvaluationAssetConfig,
        feedback_source: Path,
        unlabeled_source: Path,
    ) -> Dict[str, Any]:
        """Copy inputs, persist the job, and start it in a background thread."""
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
                initial_status="queued",
            )
            admission = _WorkerAdmission()
            thread = threading.Thread(
                target=self._run_pipeline,
                args=(key, pipeline, admission, None),
                name=f"evaluation-asset-{config.tenant_id}-{config.asset_id}",
                daemon=True,
            )
            self._threads[key] = thread
            thread.start()
        self._await_admission(admission)
        return pipeline.layout.load_state().to_dict()

    def resume(
        self,
        tenant_id: str,
        asset_id: str,
        config_updates: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Revise decisions when requested, then resume a persisted pipeline."""
        key = (tenant_id, asset_id)
        with self._lock:
            existing = self._threads.get(key)
            if existing is not None and existing.is_alive():
                raise RuntimeError("evaluation asset pipeline is already running")
            layout = EvaluationAssetLayout(self.tenants_root, tenant_id, asset_id)
            pipeline = EvaluationAssetPipeline(layout)
            admission = _WorkerAdmission()
            thread = threading.Thread(
                target=self._run_pipeline,
                args=(key, pipeline, admission, dict(config_updates or {})),
                name=f"evaluation-asset-{tenant_id}-{asset_id}",
                daemon=True,
            )
            self._threads[key] = thread
            thread.start()
        self._await_admission(admission)
        response = layout.load_state().to_dict()
        response["resume"] = pipeline.last_revision
        return response

    def extend(
        self,
        tenant_id: str,
        parent_asset_id: str,
        asset_id: str,
        *,
        additional_feedback: Optional[Path],
        additional_unlabeled: Optional[Path],
        clustering_mode: str,
        config_updates: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create and run a new asset version derived from a released parent."""
        key = (tenant_id, asset_id)
        with self._lock:
            for candidate in ((tenant_id, parent_asset_id), key):
                existing = self._threads.get(candidate)
                if existing is not None and existing.is_alive():
                    raise RuntimeError(
                        "parent or extended evaluation asset pipeline is already running"
                    )
            parent = EvaluationAssetLayout(
                self.tenants_root,
                tenant_id,
                parent_asset_id,
            )
            layout = EvaluationAssetLayout(
                self.tenants_root,
                tenant_id,
                asset_id,
            )
            layout.initialize_extension(
                parent,
                additional_feedback=additional_feedback,
                additional_unlabeled=additional_unlabeled,
                clustering_mode=clustering_mode,
                config_updates=config_updates,
                initial_status="queued",
            )
            pipeline = EvaluationAssetPipeline(layout)
            admission = _WorkerAdmission()
            thread = threading.Thread(
                target=self._run_pipeline,
                args=(key, pipeline, admission, None),
                name=f"evaluation-asset-{tenant_id}-{asset_id}",
                daemon=True,
            )
            self._threads[key] = thread
            thread.start()
        self._await_admission(admission)
        return layout.load_state().to_dict()

    def adopt(self, tenant_id: str, asset_id: str) -> Dict[str, Any]:
        """Verify and adopt a legacy completion through the locked core."""
        layout = EvaluationAssetLayout(self.tenants_root, tenant_id, asset_id)
        return layout.adopt_legacy().to_dict()

    def is_running(self, tenant_id: str, asset_id: str) -> bool:
        """Return whether this process currently owns a live pipeline thread."""
        with self._lock:
            thread = self._threads.get((tenant_id, asset_id))
            return bool(thread and thread.is_alive())

    def _run_pipeline(
        self,
        key: Tuple[str, str],
        pipeline: EvaluationAssetPipeline,
        admission: _WorkerAdmission,
        config_updates: Optional[Mapping[str, Any]],
    ) -> None:
        def lock_acquired() -> None:
            admission.lock_acquired = True
            admission.lock_decided.set()

        def preflight_accepted() -> None:
            admission.preflight_accepted = True
            admission.preflight_decided.set()

        try:
            pipeline.run(
                config_updates=config_updates,
                _lock_acquired_callback=lock_acquired,
                _preflight_accepted_callback=preflight_accepted,
            )
        except EvaluationAssetBusyError as exc:
            admission.error = exc
        except Exception as exc:
            # The pipeline persists the safe failed-stage/error-summary contract.
            admission.error = exc
            return
        finally:
            admission.lock_decided.set()
            admission.preflight_decided.set()
            with self._lock:
                current = self._threads.get(key)
                if current is threading.current_thread():
                    self._threads.pop(key, None)

    @staticmethod
    def _await_admission(admission: _WorkerAdmission) -> None:
        """Wait for a live worker's lock and preflight decisions without abandonment."""
        admission.lock_decided.wait()
        if not admission.lock_acquired:
            if admission.error is not None:
                raise admission.error
            raise RuntimeError("evaluation asset pipeline lock decision failed")
        admission.preflight_decided.wait()
        if not admission.preflight_accepted:
            if admission.error is not None:
                raise admission.error
            raise RuntimeError("evaluation asset pipeline preflight decision failed")
