# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Thin service contracts for evaluation-asset human review."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.service import EvaluationAssetRunManager
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


def test_review_service_lists_the_current_page_without_reimplementing_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch a service that drops the core status filter or pagination boundary."""
    received: list[tuple[str | None, int, int]] = []
    page = {
        "items": [
            {
                "case_id": "inferred-u1",
                "fingerprint": "sha256:" + "c" * 64,
                "trust_tier": "inferred_from_trusted_feedback",
                "status": "pending",
                "dependency_fingerprint": "sha256:" + "d" * 64,
                "context_fingerprint": "sha256:" + "e" * 64,
                "truth_fingerprint": "sha256:" + "f" * 64,
                "case": {"context": {"private": "must-not-leak"}},
                "provider_payload": "must-not-leak",
            }
        ],
        "held": [
            {
                "case_id": "synthetic-u2",
                "fingerprint": "sha256:" + "1" * 64,
                "trust_tier": "synthetic",
                "status": "held",
                "hold_reason": "conflicting_expected_truth",
                "case": {"context": {"private": "must-not-leak"}},
            }
        ],
        "counts": {"pending": 0, "approved": 0, "rejected": 0, "held": 0},
        "review_set_fingerprint": "sha256:" + "a" * 64,
        "decision_set_fingerprint": "sha256:" + "2" * 64,
        "review_authority_revision": "sha256:" + "3" * 64,
        "stage7_receipt_sha256": "sha256:" + "b" * 64,
        "finalization": {
            "finalization_id": "sha256:" + "4" * 64,
            "review_set_fingerprint": "sha256:" + "a" * 64,
            "counts": {"trusted": 1, "approved": 0, "pending": 1, "rejected": 0, "held": 1},
            "reviewer": "private-finalizer@example.com",
            "note": "private finalization note",
            "items": [{"case": "must-not-leak"}],
        },
        "offset": 4,
        "limit": 9,
        "total": 1,
        "workspace_path": "/private/tenant/path",
    }

    def list_review_items(
        layout: EvaluationAssetLayout,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> dict:
        assert (layout.tenant_id, layout.asset_id) == ("tenant_a", "v1")
        received.append((status, offset, limit))
        return page

    monkeypatch.setattr(
        EvaluationAssetLayout,
        "list_review_items",
        list_review_items,
        raising=False,
    )
    manager = EvaluationAssetRunManager(
        tmp_path / "tenants",
        repository_base=tmp_path,
    )

    assert manager.list_reviews(
        "tenant_a",
        "v1",
        status="approved",
        offset=4,
        limit=9,
    ) == {
        "items": [
            {
                "case_id": "inferred-u1",
                "fingerprint": "sha256:" + "c" * 64,
                "trust_tier": "inferred_from_trusted_feedback",
                "status": "pending",
                "dependency_fingerprint": "sha256:" + "d" * 64,
                "context_fingerprint": "sha256:" + "e" * 64,
                "truth_fingerprint": "sha256:" + "f" * 64,
            }
        ],
        "held": [
            {
                "case_id": "synthetic-u2",
                "fingerprint": "sha256:" + "1" * 64,
                "trust_tier": "synthetic",
                "status": "held",
                "hold_reason": "conflicting_expected_truth",
            }
        ],
        "counts": {"pending": 0, "approved": 0, "rejected": 0, "held": 0},
        "review_set_fingerprint": "sha256:" + "a" * 64,
        "decision_set_fingerprint": "sha256:" + "2" * 64,
        "review_authority_revision": "sha256:" + "3" * 64,
        "stage7_receipt_sha256": "sha256:" + "b" * 64,
        "finalization": {
            "finalization_id": "sha256:" + "4" * 64,
            "review_set_fingerprint": "sha256:" + "a" * 64,
            "counts": {"trusted": 1, "approved": 0, "pending": 1, "rejected": 0, "held": 1},
        },
        "offset": 4,
        "limit": 9,
        "total": 1,
    }
    assert received == [("approved", 4, 9)]


def test_review_service_binds_decision_to_case_fingerprint_and_current_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch any forwarding path that authorizes a case ID or hash in isolation."""
    received = []
    decision = {
        "decision_id": "sha256:" + "d" * 64,
        "case_id": "inferred-u1",
        "fingerprint": "sha256:" + "a" * 64,
        "status": "approved",
        "reviewer": "private-reviewer@example.com",
        "note": "private note",
    }

    def decide_review(
        layout: EvaluationAssetLayout,
        case_id: str,
        fingerprint: str,
        action: str,
        *,
        reviewer: str,
        note: str | None = None,
        expected_review_set_fingerprint: str | None = None,
        expected_decision_set_fingerprint: str | None = None,
    ) -> dict:
        assert (layout.tenant_id, layout.asset_id) == ("tenant_a", "v1")
        received.append(
            (
                case_id,
                fingerprint,
                action,
                reviewer,
                note,
                expected_review_set_fingerprint,
            )
        )
        return decision

    monkeypatch.setattr(
        EvaluationAssetLayout,
        "decide_review",
        decide_review,
        raising=False,
    )
    manager = EvaluationAssetRunManager(
        tmp_path / "tenants",
        repository_base=tmp_path,
    )

    assert manager.decide_review(
        "tenant_a",
        "v1",
        "inferred-u1",
        "sha256:" + "a" * 64,
        "approved",
        reviewer="reviewer@example.com",
        note="checked",
        expected_review_set_fingerprint="sha256:" + "b" * 64,
    ) == {
        "decision_id": "sha256:" + "d" * 64,
        "case_id": "inferred-u1",
        "fingerprint": "sha256:" + "a" * 64,
        "status": "approved",
    }
    assert received == [
        (
            "inferred-u1",
            "sha256:" + "a" * 64,
            "approved",
            "reviewer@example.com",
            "checked",
            "sha256:" + "b" * 64,
        )
    ]


def test_review_service_admits_exact_finalization_before_returning_current_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catch a worker acknowledgement before lock/preflight or without exact authority."""
    received = []

    class FinalState:
        def to_dict(self) -> dict:
            return {
                "tenant_id": "tenant_a",
                "asset_id": "v1",
                "status": "released",
                "current_stage": "dataset_splits",
                "counts": {"approved": 1, "pending": 2},
                "error": "/private/path must-not-leak",
            }

    def finalize_review(
        pipeline: EvaluationAssetPipeline,
        *,
        reviewer: str,
        note: str | None = None,
        expected_review_set_fingerprint: str | None = None,
        expected_decision_set_fingerprint: str | None = None,
        _lock_acquired_callback=None,
        _preflight_accepted_callback=None,
    ) -> FinalState:
        assert (pipeline.layout.tenant_id, pipeline.layout.asset_id) == (
            "tenant_a",
            "v1",
        )
        received.append(
            (
                reviewer,
                note,
                expected_review_set_fingerprint,
                expected_decision_set_fingerprint,
            )
        )
        _lock_acquired_callback()
        _preflight_accepted_callback()
        return FinalState()

    monkeypatch.setattr(
        EvaluationAssetPipeline,
        "finalize_review",
        finalize_review,
        raising=False,
    )
    monkeypatch.setattr(
        EvaluationAssetLayout,
        "load_state",
        lambda layout: FinalState(),
    )
    manager = EvaluationAssetRunManager(
        tmp_path / "tenants",
        repository_base=tmp_path,
    )

    assert manager.finalize_review(
        "tenant_a",
        "v1",
        reviewer="reviewer@example.com",
        note="release trusted and approved",
        expected_review_set_fingerprint="sha256:" + "b" * 64,
        expected_decision_set_fingerprint="sha256:" + "c" * 64,
    ) == {
        "tenant_id": "tenant_a",
        "asset_id": "v1",
        "status": "released",
        "current_stage": "dataset_splits",
        "counts": {"approved": 1, "pending": 2},
    }
    assert received == [
        (
            "reviewer@example.com",
            "release trusted and approved",
            "sha256:" + "b" * 64,
            "sha256:" + "c" * 64,
        )
    ]
