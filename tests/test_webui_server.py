# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAPO web UI HTTP routing helpers."""

from __future__ import annotations

import json
from pathlib import Path

from src.hephaestus.webui.data import TenantStore
from src.hephaestus.webui.server import _Handler, _overview_tenant_ids, _parse_query


def test_overview_tenant_filter_distinguishes_missing_from_empty() -> None:
    assert _overview_tenant_ids(_parse_query("")) is None
    assert _overview_tenant_ids(_parse_query("tenants=")) == []


def test_overview_tenant_filter_parses_selected_tenants() -> None:
    assert _overview_tenant_ids(_parse_query("tenants=alpha,beta")) == ["alpha", "beta"]


def test_start_evaluation_asset_endpoint_returns_accepted(tmp_path: Path) -> None:
    class FakeManager:
        received = None

        def start(self, config, feedback_path, unlabeled_path):
            self.received = (config, feedback_path, unlabeled_path)
            return {
                "tenant_id": config.tenant_id,
                "asset_id": config.asset_id,
                "status": "queued",
            }

    manager = FakeManager()
    handler = type(
        "_TestHandler",
        (_Handler,),
        {"store": TenantStore(tmp_path / "tenants"), "asset_manager": manager},
    )
    instance = object.__new__(handler)
    payload = {
        "tenant_id": "new_tenant",
        "asset_id": "v1",
        "feedback_path": str(tmp_path / "feedback.jsonl"),
        "unlabeled_path": str(tmp_path / "unlabeled.jsonl"),
        "rubric_model": "gpt-5.5",
        "embedding_model": "text-embedding-3-small",
        "cluster_count": 12,
        "match_threshold": 0.73,
        "synthetic_coverage_enabled": True,
        "synthetic_cases_per_cluster": 4,
    }
    sent = {}
    instance._read_json_body = lambda: json.loads(json.dumps(payload))
    instance._send_json = lambda body, status=200: sent.update(
        {"body": body, "status": status}
    )

    instance._route_start_evaluation_asset()

    assert sent["status"] == 202
    body = sent["body"]
    assert body["status"] == "queued"
    assert manager.received[0].cluster_count == 12
    assert manager.received[0].match_threshold == 0.73
    assert manager.received[0].synthetic_coverage_enabled is True
    assert manager.received[0].synthetic_cases_per_cluster == 4


def test_start_evaluation_asset_accepts_tfidf_fallback(tmp_path: Path) -> None:
    class FakeManager:
        received = None

        def start(self, config, feedback_path, unlabeled_path):
            self.received = config
            return {"status": "queued"}

    manager = FakeManager()
    handler = type(
        "_TestHandler",
        (_Handler,),
        {"store": TenantStore(tmp_path / "tenants"), "asset_manager": manager},
    )
    instance = object.__new__(handler)
    instance._read_json_body = lambda: {
        "tenant_id": "new_tenant",
        "asset_id": "v1",
        "feedback_path": str(tmp_path / "feedback.jsonl"),
        "unlabeled_path": str(tmp_path / "unlabeled.jsonl"),
        "rubric_model": "gpt-4o-mini",
        "embedding_model": "tfidf",
        "cluster_count": 12,
    }
    sent = {}
    instance._send_json = lambda body, status=200: sent.update(
        {"body": body, "status": status}
    )

    instance._route_start_evaluation_asset()

    assert sent["status"] == 202
    assert manager.received.rubric_model == "gpt-4o-mini"
    assert manager.received.embedding_provider == "tfidf"
    assert manager.received.embedding_model == "tfidf"
    assert manager.received.match_threshold == 0.6
    assert manager.received.synthetic_coverage_enabled is False
    assert manager.received.synthetic_cases_per_cluster == 1


def test_resume_evaluation_asset_accepts_decision_updates(tmp_path: Path) -> None:
    class FakeManager:
        received = None

        def resume(self, tenant_id, asset_id, updates):
            self.received = (tenant_id, asset_id, updates)
            return {"status": "queued", "current_stage": "coverage_decisions"}

    manager = FakeManager()
    handler = type(
        "_TestHandler",
        (_Handler,),
        {"store": TenantStore(tmp_path / "tenants"), "asset_manager": manager},
    )
    instance = object.__new__(handler)
    instance._read_json_body = lambda: {
        "rubric_model": "gpt-5.5",
        "embedding_model": "tfidf",
        "cluster_count": 8,
        "batch_size": 5,
        "match_threshold": 0.25,
        "min_trusted_examples": 2,
        "min_trusted_groups": 1,
        "max_unlabeled_to_trusted_ratio": None,
        "synthetic_coverage_enabled": False,
        "synthetic_cases_per_cluster": 2,
        "split_seed": 73,
    }
    sent = {}
    instance._send_json = lambda body, status=200: sent.update(
        {"body": body, "status": status}
    )

    instance._route_resume_evaluation_asset(
        {"tenant": "tenant_a", "asset": "v1"}
    )

    assert sent["status"] == 202
    assert manager.received == (
        "tenant_a",
        "v1",
        {
            "rubric_model": "gpt-5.5",
            "embedding_model": "tfidf",
            "cluster_count": 8,
            "batch_size": 5,
            "match_threshold": 0.25,
            "min_trusted_examples": 2,
            "min_trusted_groups": 1,
            "max_unlabeled_to_trusted_ratio": None,
            "synthetic_coverage_enabled": False,
            "synthetic_cases_per_cluster": 2,
            "split_seed": 73,
        },
    )
