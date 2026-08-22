# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAPO web UI HTTP routing helpers."""

from __future__ import annotations

import http.client
import json
import socket
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import src.hephaestus.webui.server as server_module
from src.hephaestus.evaluation_assets.publication import (
    LOGICAL_SPLITS,
    build_release_pointer,
    install_generation,
    write_release_pointer,
)
from src.hephaestus.webui.data import TenantStore
from src.hephaestus.webui.server import (
    _Handler,
    _overview_tenant_ids,
    _parse_query,
    serve,
)


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
        {
            "store": TenantStore(
                tmp_path / "tenants",
                repository_base=tmp_path,
            ),
            "asset_manager": manager,
        },
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
        {
            "store": TenantStore(
                tmp_path / "tenants",
                repository_base=tmp_path,
            ),
            "asset_manager": manager,
        },
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
        {
            "store": TenantStore(
                tmp_path / "tenants",
                repository_base=tmp_path,
            ),
            "asset_manager": manager,
        },
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


def test_extend_evaluation_asset_endpoint_accepts_refresh_plan(
    tmp_path: Path,
) -> None:
    class FakeManager:
        received = None

        def extend(self, tenant_id, parent_asset_id, asset_id, **kwargs):
            self.received = (tenant_id, parent_asset_id, asset_id, kwargs)
            return {"status": "queued", "asset_id": asset_id}

    manager = FakeManager()
    handler = type(
        "_TestHandler",
        (_Handler,),
        {
            "store": TenantStore(
                tmp_path / "tenants",
                repository_base=tmp_path,
            ),
            "asset_manager": manager,
        },
    )
    instance = object.__new__(handler)
    instance._read_json_body = lambda: {
        "tenant_id": "tenant_a",
        "parent_asset_id": "v1",
        "asset_id": "v2",
        "additional_feedback_path": str(tmp_path / "feedback.jsonl"),
        "additional_unlabeled_path": str(tmp_path / "unlabeled.jsonl"),
        "clustering_mode": "refresh",
        "embedding_model": "tfidf",
        "cluster_count": 12,
    }
    sent = {}
    instance._send_json = lambda body, status=200: sent.update(
        {"body": body, "status": status}
    )

    instance._route_extend_evaluation_asset()

    assert sent["status"] == 202
    assert manager.received == (
        "tenant_a",
        "v1",
        "v2",
        {
            "additional_feedback": tmp_path / "feedback.jsonl",
            "additional_unlabeled": tmp_path / "unlabeled.jsonl",
            "clustering_mode": "refresh",
            "config_updates": {
                "embedding_model": "tfidf",
                "cluster_count": 12,
            },
        },
    )


def test_adopt_evaluation_asset_endpoint_uses_thin_service_api(
    tmp_path: Path,
) -> None:
    class FakeManager:
        received = None

        def adopt(self, tenant_id, asset_id):
            self.received = (tenant_id, asset_id)
            return {"status": "released", "asset_id": asset_id}

    manager = FakeManager()
    handler = type(
        "_TestHandler",
        (_Handler,),
        {
            "store": TenantStore(
                tmp_path / "tenants",
                repository_base=tmp_path,
            ),
            "asset_manager": manager,
        },
    )
    instance = object.__new__(handler)
    sent = {}
    instance._send_json = lambda body, status=200: sent.update(
        {"body": body, "status": status}
    )

    instance._route_adopt_evaluation_asset(
        {"tenant": "tenant_a", "asset": "legacy-v1"}
    )

    assert manager.received == ("tenant_a", "legacy-v1")
    assert sent == {
        "body": {"status": "released", "asset_id": "legacy-v1"},
        "status": 202,
    }


def test_serve_rejects_non_loopback_bind_before_server_start(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The combined UI cannot be bound to a non-loopback interface."""
    class NoOpServer:
        def __init__(self, *args, **kwargs):
            pass

        def serve_forever(self):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(server_module, "ThreadingHTTPServer", NoOpServer)

    with pytest.raises(ValueError, match="loopback"):
        serve(
            tmp_path / "tenants",
            host="0.0.0.0",
            port=8765,
            repository_base=tmp_path,
        )


def test_serve_binds_ipv6_loopback_and_prints_bracketed_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if not socket.has_ipv6:
        pytest.skip("IPv6 is unavailable")

    probe = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        probe.bind(("::1", 0))
    except OSError as exc:
        pytest.skip(f"IPv6 loopback is unavailable: {exc}")
    finally:
        probe.close()

    address_families: list[socket.AddressFamily] = []

    def serve_once(server: ThreadingHTTPServer) -> None:
        address_families.append(server.address_family)

    monkeypatch.setattr(ThreadingHTTPServer, "serve_forever", serve_once)

    serve(
        tmp_path / "tenants",
        host="::1",
        port=0,
        repository_base=tmp_path,
    )

    assert address_families == [socket.AF_INET6]
    assert "http://[::1]:" in capsys.readouterr().out


def test_studio_http_policy_and_cache_headers(tmp_path: Path) -> None:
    """Studio routes enforce local authority, same origin, and no-store."""
    class FakeManager:
        def is_running(self, tenant_id, asset_id):
            return False

        def start(self, config, feedback_path, unlabeled_path):
            return {
                "tenant_id": config.tenant_id,
                "asset_id": config.asset_id,
                "status": "queued",
            }

    handler = type(
        "_TestHTTPHandler",
        (_Handler,),
        {
            "store": TenantStore(
                tmp_path / "tenants",
                repository_base=tmp_path,
            ),
            "asset_manager": FakeManager(),
        },
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    local_host = f"127.0.0.1:{port}"
    payload = json.dumps(
        {
            "tenant_id": "tenant_a",
            "asset_id": "v1",
            "feedback_path": "feedback.jsonl",
            "unlabeled_path": "unlabeled.jsonl",
            "cluster_count": 1,
        }
    )

    try:
        status, headers = _http_request(
            port,
            "GET",
            "/evaluation-assets/",
            headers={"Host": "example.com"},
        )
        assert status == 403
        assert headers["cache-control"] == "no-store"

        status, headers = _http_request(
            port,
            "GET",
            "/",
            headers={"Host": "example.com"},
        )
        assert status == 200
        assert "cache-control" not in headers

        status, headers = _http_request(
            port,
            "GET",
            "/evaluation-assets/",
            headers={"Host": local_host},
        )
        assert status == 200
        assert headers["cache-control"] == "no-store"

        status, headers = _http_request(
            port,
            "GET",
            "/api/evaluation-assets/input-contract",
            headers={"Host": local_host},
        )
        assert status == 200
        assert headers["cache-control"] == "no-store"

        status, headers = _http_request(
            port,
            "GET",
            "/api/tenants",
            headers={"Host": local_host},
        )
        assert status == 200
        assert headers["cache-control"] == "no-store"

        status, headers = _http_request(
            port,
            "GET",
            "/api/overview",
            headers={"Host": "example.com"},
        )
        assert status == 403
        assert headers["cache-control"] == "no-store"

        mutation_headers = {
            "Host": local_host,
            "Content-Type": "application/json",
            "Origin": "http://example.com",
        }
        status, headers = _http_request(
            port,
            "POST",
            "/api/evaluation-assets/start",
            body=payload,
            headers=mutation_headers,
        )
        assert status == 403
        assert headers["cache-control"] == "no-store"

        mutation_headers["Origin"] = f"http://{local_host}"
        status, headers = _http_request(
            port,
            "POST",
            "/api/evaluation-assets/start",
            body=payload,
            headers=mutation_headers,
        )
        assert status == 202
        assert headers["cache-control"] == "no-store"

        mutation_headers.pop("Origin")
        status, _ = _http_request(
            port,
            "POST",
            "/api/evaluation-assets/start",
            body=payload,
            headers=mutation_headers,
        )
        assert status == 202
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_published_studio_datasets_inherit_studio_http_boundary(
    tmp_path: Path,
) -> None:
    """Generic dataset and joined-case reads cannot bypass Studio policy."""
    tenants_root = tmp_path / "tenants"
    tenant = tenants_root / "tenant_a"
    ordinary = tenant / "datasets" / "ordinary.jsonl"
    run_dir = tenant / "evals" / "run-1"
    ordinary.parent.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    ordinary.write_text('{"case_id":"ordinary"}\n', encoding="utf-8")
    split_sources = {}
    for split in LOGICAL_SPLITS:
        source = tenant / "workspace" / f"{split}.jsonl"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            (
                '{"case_id":"studio-case","context":{"input":"private"},'
                '"expected":{"answer":"protected"}}\n'
            ),
            encoding="utf-8",
        )
        split_sources[split] = source
    catalog = tenant / "datasets" / "evaluation_assets" / "v1"
    generation = install_generation(
        catalog,
        tenant_id="tenant_a",
        asset_id="v1",
        split_paths=split_sources,
        build_fingerprint="a" * 64,
    )
    write_release_pointer(
        catalog,
        build_release_pointer(
            tenant_id="tenant_a",
            asset_id="v1",
            generation=generation,
            stage_8_receipt_sha256="b" * 64,
            build_provenance_sha256="c" * 64,
            published_at="2026-08-20T00:00:00+00:00",
        ),
    )
    published_rel = generation.files["train"].relative_to(tenant).as_posix()
    (run_dir / "results.jsonl").write_text(
        '{"case_id":"studio-case","composite_score":1.0}\n',
        encoding="utf-8",
    )
    (run_dir / "run_config.json").write_text(
        json.dumps(
            {
                    "dataset_path": (
                        f"tenants/tenant_a/{published_rel}"
                    )
            }
        )
        + "\n",
        encoding="utf-8",
    )

    handler = type(
        "_TestPublishedDatasetHTTPHandler",
        (_Handler,),
        {
            "store": TenantStore(tenants_root, repository_base=tmp_path),
            "asset_manager": object(),
        },
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    local_host = f"127.0.0.1:{port}"

    try:
        for path in (
            "/api/tenants/tenant_a/datasets",
            (
                    "/api/tenants/tenant_a/dataset?path="
                    f"{published_rel}"
                ),
            "/api/tenants/tenant_a/runs/evals%2Frun-1/cases/0",
        ):
            status, headers = _http_request(
                port,
                "GET",
                path,
                headers={"Host": "example.com"},
            )
            assert status == 403
            assert headers["cache-control"] == "no-store"

            status, headers = _http_request(
                port,
                "GET",
                path,
                headers={"Host": local_host},
            )
            assert status == 200
            assert headers["cache-control"] == "no-store"

        status, headers = _http_request(
            port,
            "GET",
            "/api/tenants/tenant_a/dataset?path=datasets/ordinary.jsonl",
            headers={"Host": "example.com"},
        )
        assert status == 200
        assert "cache-control" not in headers
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_dataset_routes_use_one_data_and_policy_snapshot() -> None:
    """A pointer appearing between policy and data reads cannot bypass auth."""
    order = []

    class FakeStore:
        def prepare_dataset_listing(self, tenant_id):
            assert tenant_id == "tenant_a"
            order.append("prepare-list")
            return (("list-snapshot",), True)

        def materialize_dataset_listing(self, snapshot):
            assert snapshot == ("list-snapshot",)
            order.append("read-list")
            return [{"path": "studio.jsonl"}]

        def prepare_dataset(self, tenant_id, dataset_rel):
            assert (tenant_id, dataset_rel) == (
                "tenant_a",
                "studio.jsonl",
            )
            order.append("prepare-dataset")
            return ("dataset-snapshot", True)

        def materialize_dataset(self, snapshot, offset, limit):
            assert (snapshot, offset, limit) == ("dataset-snapshot", 0, 100)
            order.append("read-dataset")
            return {"rows": [{"case_id": "private"}]}

    handler = type("_SnapshotHandler", (_Handler,), {"store": FakeStore()})
    instance = object.__new__(handler)
    authorized = []
    sent = []
    instance._authorize_studio_request = lambda no_store: authorized.append(
        no_store
    ) or order.append("authorize") or True
    instance._send_json = lambda body, no_store=False: sent.append(
        (body, no_store)
    )
    instance._send_json_or_404 = lambda body, no_store=False: sent.append(
        (body, no_store)
    )

    instance._route_datasets({"tenant": "tenant_a"}, {})
    instance._route_dataset(
        {"tenant": "tenant_a"},
        {"path": ["studio.jsonl"]},
    )

    assert authorized == [True, True]
    assert order == [
        "prepare-list",
        "authorize",
        "read-list",
        "prepare-dataset",
        "authorize",
        "read-dataset",
    ]
    assert sent == [
        ([{"path": "studio.jsonl"}], True),
        ({"rows": [{"case_id": "private"}]}, True),
    ]


def test_case_route_uses_one_joined_data_and_policy_snapshot() -> None:
    """Joined case details and their Studio classification share one read."""
    order = []

    class FakeStore:
        def prepare_case(self, tenant_id, run_rel, index):
            assert (tenant_id, run_rel, index) == ("tenant_a", "evals/run", 0)
            order.append("prepare")
            return ("case-snapshot", True)

        def materialize_case(self, snapshot):
            assert snapshot == "case-snapshot"
            order.append("read")
            return {"ground_truth": {"expected": "private"}}

    handler = type("_CaseSnapshotHandler", (_Handler,), {"store": FakeStore()})
    instance = object.__new__(handler)
    authorized = []
    sent = []
    instance._authorize_studio_request = lambda no_store: authorized.append(
        no_store
    ) or order.append("authorize") or True
    instance._send_json_or_404 = lambda body, no_store=False: sent.append(
        (body, no_store)
    )

    instance._route_case(
        {"tenant": "tenant_a", "run": "evals%2Frun", "index": "0"},
        {},
    )

    assert authorized == [True]
    assert order == ["prepare", "authorize", "read"]
    assert sent == [({"ground_truth": {"expected": "private"}}, True)]


def test_ordinary_dataset_catalog_remains_available_to_explorer_hosts(
    tmp_path: Path,
) -> None:
    """An ordinary-only dataset catalog keeps the Explorer's existing policy."""
    tenants_root = tmp_path / "tenants"
    tenant = tenants_root / "tenant_a"
    dataset = tenant / "datasets" / "ordinary.jsonl"
    dataset.parent.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    dataset.write_text('{"case_id":"ordinary"}\n', encoding="utf-8")

    handler = type(
        "_TestOrdinaryDatasetHTTPHandler",
        (_Handler,),
        {
            "store": TenantStore(tenants_root, repository_base=tmp_path),
            "asset_manager": object(),
        },
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]

    try:
        for path in (
            "/api/tenants/tenant_a/datasets",
            "/api/tenants/tenant_a/dataset?path=datasets/ordinary.jsonl",
        ):
            status, headers = _http_request(
                port,
                "GET",
                path,
                headers={"Host": "example.com"},
            )
            assert status == 200
            assert "cache-control" not in headers
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def _http_request(
    port: int,
    method: str,
    path: str,
    *,
    body: str | None = None,
    headers: dict[str, str],
) -> tuple[int, dict[str, str]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response.read()
        return response.status, {key.lower(): value for key, value in response.headers.items()}
    finally:
        connection.close()
