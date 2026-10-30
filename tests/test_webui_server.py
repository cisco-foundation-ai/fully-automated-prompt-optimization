# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAFO web UI HTTP routing helpers."""

from __future__ import annotations

import http.client
import json
import socket
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

import pytest

import src.hephaestus.webui.server as server_module
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
        {"store": TenantStore(tenants_root, repository_base=tmp_path)},
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


@contextmanager
def _running_server(store: TenantStore) -> Iterator[int]:
    handler = type("_TestHTTPHandler", (_Handler,), {"store": store})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


class TestEvaluationAssetHttpRoutes:
    """HTTP behavior for evaluation assets after the Studio API removal."""

    def test_asset_datasets_are_served_like_ordinary_datasets(self, tmp_path: Path) -> None:
        """Asset split files use the generic dataset routes; other asset files do not."""
        tenants_root = tmp_path / "tenants"
        asset = tenants_root / "tenant_a" / "evaluation_assets" / "v1"
        (asset / "datasets").mkdir(parents=True)
        (asset / "datasets" / "train.jsonl").write_text('{"case_id":"asset-case"}\n', encoding="utf-8")
        (asset / "lessons.jsonl").write_text('{"case_id":"lesson"}\n', encoding="utf-8")
        headers = {"Host": "example.com"}

        with _running_server(TenantStore(tenants_root, repository_base=tmp_path)) as port:
            listing = _http_json_request(port, "GET", "/api/tenants/tenant_a/datasets", headers=headers)
            page = _http_json_request(
                port,
                "GET",
                "/api/tenants/tenant_a/dataset?path=evaluation_assets/v1/datasets/train.jsonl",
                headers=headers,
            )
            lessons = _http_json_request(
                port,
                "GET",
                "/api/tenants/tenant_a/dataset?path=evaluation_assets/v1/lessons.jsonl",
                headers=headers,
            )

        assert listing[0] == 200
        assert "cache-control" not in listing[1]
        assert [row["path"] for row in listing[2]] == ["evaluation_assets/v1/datasets/train.jsonl"]
        assert page[0] == 200
        assert page[2]["rows"] == [{"case_id": "asset-case"}]
        assert lessons[0] == 404

    def test_removed_evaluation_asset_endpoints_are_not_served(self, tmp_path: Path) -> None:
        """The old evaluation-asset API is gone and tenant summaries omit its fields."""
        tenants_root = tmp_path / "tenants"
        tenant = tenants_root / "tenant_a"
        tenant.mkdir(parents=True)
        (tenant / "__init__.py").write_text("", encoding="utf-8")
        headers = {"Host": "127.0.0.1"}

        with _running_server(TenantStore(tenants_root, repository_base=tmp_path)) as port:
            statuses = [
                _http_request(port, "GET", path, headers=headers)[0]
                for path in (
                    "/api/evaluation-assets/input-contract",
                    "/api/tenants/tenant_a/evaluation-assets",
                    "/api/tenants/tenant_a/evaluation-assets/v1/stages/raw_inputs",
                    "/api/tenants/tenant_a/evaluation-assets/v1/reviews",
                )
            ]
            post_status, _ = _http_request(
                port,
                "POST",
                "/api/evaluation-assets/start",
                body="{}",
                headers={**headers, "Content-Type": "application/json"},
            )
            tenants_status, _, tenants = _http_json_request(port, "GET", "/api/tenants", headers=headers)

        assert statuses == [404, 404, 404, 404]
        assert post_status == 501
        assert tenants_status == 200
        assert [tenant["tenant_id"] for tenant in tenants] == ["tenant_a"]
        assert not [key for key in tenants[0] if key.startswith("evaluation_asset")]


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


def _http_json_request(
    port: int,
    method: str,
    path: str,
    *,
    body: str | None = None,
    headers: dict[str, str],
) -> tuple[int, dict[str, str], dict]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        return (
            response.status,
            {key.lower(): value for key, value in response.headers.items()},
            payload,
        )
    finally:
        connection.close()
