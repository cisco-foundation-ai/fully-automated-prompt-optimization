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

_PUBLIC_REVIEW_ITEM_FIELDS = (
    "case_id",
    "fingerprint",
    "trust_tier",
    "status",
    "decision_id",
    "dependency_fingerprint",
    "context_fingerprint",
    "truth_fingerprint",
)
_PUBLIC_HELD_REVIEW_FIELDS = _PUBLIC_REVIEW_ITEM_FIELDS + (
    "case_content_sha256",
    "hold_reason",
)
_PUBLIC_REVIEW_COUNT_FIELDS = (
    "trusted",
    "approved",
    "pending",
    "rejected",
    "held",
    "total",
)
_PUBLIC_REVIEW_FINALIZATION_FIELDS = (
    "finalization_id",
    "review_set_fingerprint",
)


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

    def __init__(
        self,
        tenants_root: Path,
        *,
        repository_base: Path | None = None,
    ) -> None:
        effective_base = repository_base if repository_base is not None else Path.cwd()
        probe = EvaluationAssetLayout(
            tenants_root,
            "service",
            "layout",
            repository_base=effective_base,
        )
        self.tenants_root = probe.tenants_root
        self.repository_base = probe.repository_base
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
                repository_base=self.repository_base,
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
            layout = EvaluationAssetLayout(
                self.tenants_root,
                tenant_id,
                asset_id,
                repository_base=self.repository_base,
            )
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
                repository_base=self.repository_base,
            )
            layout = EvaluationAssetLayout(
                self.tenants_root,
                tenant_id,
                asset_id,
                repository_base=self.repository_base,
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
        layout = EvaluationAssetLayout(
            self.tenants_root,
            tenant_id,
            asset_id,
            repository_base=self.repository_base,
        )
        return layout.adopt_legacy().to_dict()

    def list_reviews(
        self,
        tenant_id: str,
        asset_id: str,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Return one verified page from the current review set."""
        layout = EvaluationAssetLayout(
            self.tenants_root,
            tenant_id,
            asset_id,
            repository_base=self.repository_base,
        )
        return public_review_page(
            layout.list_review_items(
                status=status,
                offset=offset,
                limit=limit,
            )
        )

    def decide_review(
        self,
        tenant_id: str,
        asset_id: str,
        case_id: str,
        fingerprint: str,
        decision: str,
        *,
        reviewer: str,
        note: str | None = None,
        expected_review_set_fingerprint: str,
    ) -> Dict[str, Any]:
        """Persist one exact, terminal decision through the locked core."""
        layout = EvaluationAssetLayout(
            self.tenants_root,
            tenant_id,
            asset_id,
            repository_base=self.repository_base,
        )
        return public_review_decision(
            layout.decide_review(
                case_id,
                fingerprint,
                decision,
                reviewer=reviewer,
                note=note,
                expected_review_set_fingerprint=(
                    expected_review_set_fingerprint
                ),
            )
        )

    def finalize_review(
        self,
        tenant_id: str,
        asset_id: str,
        *,
        reviewer: str,
        note: str | None = None,
        expected_review_set_fingerprint: str,
        expected_decision_set_fingerprint: str,
    ) -> Dict[str, Any]:
        """Admit explicit review finalization and return current safe state."""
        key = (tenant_id, asset_id)
        with self._lock:
            existing = self._threads.get(key)
            if existing is not None and existing.is_alive():
                raise RuntimeError("evaluation asset pipeline is already running")
            layout = EvaluationAssetLayout(
                self.tenants_root,
                tenant_id,
                asset_id,
                repository_base=self.repository_base,
            )
            pipeline = EvaluationAssetPipeline(layout)
            admission = _WorkerAdmission()
            thread = threading.Thread(
                target=self._run_review_finalization,
                args=(
                    key,
                    pipeline,
                    admission,
                    reviewer,
                    note,
                    expected_review_set_fingerprint,
                    expected_decision_set_fingerprint,
                ),
                name=f"evaluation-asset-review-{tenant_id}-{asset_id}",
                daemon=True,
            )
            self._threads[key] = thread
            thread.start()
        self._await_admission(admission)
        return public_review_state(layout.load_state().to_dict())

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

    def _run_review_finalization(
        self,
        key: Tuple[str, str],
        pipeline: EvaluationAssetPipeline,
        admission: _WorkerAdmission,
        reviewer: str,
        note: str | None,
        expected_review_set_fingerprint: str,
        expected_decision_set_fingerprint: str,
    ) -> None:
        def lock_acquired() -> None:
            admission.lock_acquired = True
            admission.lock_decided.set()

        def preflight_accepted() -> None:
            admission.preflight_accepted = True
            admission.preflight_decided.set()

        try:
            pipeline.finalize_review(
                reviewer=reviewer,
                note=note,
                expected_review_set_fingerprint=(
                    expected_review_set_fingerprint
                ),
                expected_decision_set_fingerprint=(
                    expected_decision_set_fingerprint
                ),
                _lock_acquired_callback=lock_acquired,
                _preflight_accepted_callback=preflight_accepted,
            )
        except EvaluationAssetBusyError as exc:
            admission.error = exc
        except Exception as exc:
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


def public_review_page(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the bounded queue projection shared by CLI and loopback HTTP."""
    page = _mapping_payload(payload, "review page")
    items = page.get("items", [])
    held = page.get("held", [])
    if not isinstance(items, list) or not isinstance(held, list):
        raise ValueError("review page items and held entries must be arrays")
    output = _project_fields(
        page,
        (
            "review_set_fingerprint",
            "decision_set_fingerprint",
            "review_authority_revision",
            "stage7_receipt_sha256",
            "offset",
            "limit",
            "total",
        ),
    )
    output["items"] = [
        _project_fields(
            _mapping_payload(item, "review item"),
            _PUBLIC_REVIEW_ITEM_FIELDS,
        )
        for item in items
    ]
    output["held"] = [
        _project_fields(
            _mapping_payload(item, "held review item"),
            _PUBLIC_HELD_REVIEW_FIELDS,
        )
        for item in held
    ]
    counts = _mapping_payload(page.get("counts", {}), "review counts")
    output["counts"] = _project_fields(counts, _PUBLIC_REVIEW_COUNT_FIELDS)
    raw_finalization = page.get("finalization")
    if raw_finalization is None:
        output["finalization"] = None
    else:
        finalization = _mapping_payload(
            raw_finalization,
            "review finalization",
        )
        public_finalization = _project_fields(
            finalization,
            _PUBLIC_REVIEW_FINALIZATION_FIELDS,
        )
        finalization_counts = _mapping_payload(
            finalization.get("counts", {}),
            "review finalization counts",
        )
        public_finalization["counts"] = _project_fields(
            finalization_counts,
            _PUBLIC_REVIEW_COUNT_FIELDS,
        )
        output["finalization"] = public_finalization
    return output


def public_review_decision(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Return identifiers and terminal status, never reviewer notes or case data."""
    return _project_fields(
        _mapping_payload(payload, "review decision"),
        (
            "decision_id",
            "case_id",
            "fingerprint",
            "status",
            "review_set_fingerprint",
        ),
    )


def public_review_state(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the safe state subset acknowledged by review finalization."""
    state = _mapping_payload(payload, "evaluation asset state")
    output = _project_fields(
        state,
        (
            "tenant_id",
            "asset_id",
            "status",
            "current_stage",
        ),
    )
    counts = _mapping_payload(state.get("counts", {}), "state counts")
    output["counts"] = _project_fields(counts, _PUBLIC_REVIEW_COUNT_FIELDS)
    return output


def _mapping_payload(payload: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must be an object")
    return payload


def _project_fields(
    payload: Mapping[str, Any],
    fields: tuple[str, ...],
) -> Dict[str, Any]:
    return {field: payload[field] for field in fields if field in payload}
