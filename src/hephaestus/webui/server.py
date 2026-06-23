# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Zero-dependency HTTP server for the local web UI.

Serves a single-page app at ``/`` and a small read-only JSON API under
``/api/``. Built on :mod:`http.server` so the UI requires no extra packages
beyond the standard library.

Routes:
    GET /                                          -> SPA shell (HTML)
    GET /api/overview?tenants=<a,b>                -> dashboard aggregates (filtered)
    GET /api/tenants                               -> [tenant summaries]
    GET /api/tenants/<t>/runs                      -> [run summaries]
    GET /api/tenants/<t>/runs/<run>                -> run detail + case list
    GET /api/tenants/<t>/runs/<run>/cases/<i>      -> single case detail
    GET /api/tenants/<t>/iterations                -> iteration history
    GET /api/tenants/<t>/prompts                   -> [prompt files]
    GET /api/tenants/<t>/prompt?path=<rel>         -> prompt content
    GET /api/tenants/<t>/configs                   -> [config files]
    GET /api/tenants/<t>/config?path=<rel>         -> config content
    GET /api/tenants/<t>/datasets                  -> [dataset files]
    GET /api/tenants/<t>/dataset?path=<rel>&offset=&limit=  -> dataset rows
    GET /api/tenants/<t>/docs                       -> [doc files]
    GET /api/tenants/<t>/doc?path=<rel>            -> doc content (markdown)
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from src.hephaestus.webui.data import TenantStore
from src.hephaestus.webui.frontend import INDEX_HTML

_LOGO_PATH = Path(__file__).with_name("assets") / "fapo-explorer-logo.webp"


class _Handler(BaseHTTPRequestHandler):
    store: TenantStore  # injected via factory below

    server_version = "HephaestusUI/0.1"

    # Silence the default noisy per-request logging.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        parsed = urlparse(self.path)
        path = parsed.path
        query = _parse_query(parsed.query)

        if path in ("/", "/index.html"):
            self._send_html(INDEX_HTML)
            return

        if path == "/assets/fapo-explorer-logo.webp":
            self._send_file(_LOGO_PATH, "image/webp")
            return

        if path == "/api/overview":
            self._send_json(self.store.overview(_overview_tenant_ids(query)))
            return

        if path == "/api/tenants":
            self._send_json(self.store.list_tenants())
            return

        for pattern, handler in self._routes():
            params = _match(pattern, path)
            if params is not None:
                handler(self, params, query)
                return

        self._send_json({"error": "not found", "path": path}, status=404)

    # -- route table -----------------------------------------------------

    def _routes(
        self,
    ) -> List[Tuple[str, Callable[["_Handler", Dict[str, str], Dict[str, List[str]]], None]]]:
        return [
            ("/api/tenants/{tenant}/runs/{run}/cases/{index}", _Handler._route_case),
            ("/api/tenants/{tenant}/runs/{run}", _Handler._route_run),
            ("/api/tenants/{tenant}/runs", _Handler._route_runs),
            ("/api/tenants/{tenant}/iterations", _Handler._route_iterations),
            ("/api/tenants/{tenant}/prompts", _Handler._route_prompts),
            ("/api/tenants/{tenant}/prompt", _Handler._route_prompt),
            ("/api/tenants/{tenant}/configs", _Handler._route_configs),
            ("/api/tenants/{tenant}/config", _Handler._route_config),
            ("/api/tenants/{tenant}/datasets", _Handler._route_datasets),
            ("/api/tenants/{tenant}/dataset", _Handler._route_dataset),
            ("/api/tenants/{tenant}/docs", _Handler._route_docs),
            ("/api/tenants/{tenant}/doc", _Handler._route_doc),
        ]

    def _route_runs(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        self._send_json(self.store.list_runs(params["tenant"]))

    def _route_run(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        run_rel = unquote(params["run"])
        data = self.store.get_run(params["tenant"], run_rel)
        self._send_json_or_404(data)

    def _route_case(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        try:
            index = int(params["index"])
        except ValueError:
            self._send_json({"error": "bad index"}, status=400)
            return
        run_rel = unquote(params["run"])
        data = self.store.get_case(params["tenant"], run_rel, index)
        self._send_json_or_404(data)

    def _route_iterations(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        self._send_json(self.store.list_iterations(params["tenant"]))

    def _route_prompts(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        self._send_json(self.store.list_prompts(params["tenant"]))

    def _route_prompt(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        rel = (query.get("path") or [""])[0]
        if not rel:
            self._send_json({"error": "missing path"}, status=400)
            return
        data = self.store.get_prompt(params["tenant"], unquote(rel))
        self._send_json_or_404(data)

    def _route_configs(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        self._send_json(self.store.list_configs(params["tenant"]))

    def _route_config(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        rel = (query.get("path") or [""])[0]
        if not rel:
            self._send_json({"error": "missing path"}, status=400)
            return
        data = self.store.get_config(params["tenant"], unquote(rel))
        self._send_json_or_404(data)

    def _route_datasets(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        self._send_json(self.store.list_datasets(params["tenant"]))

    def _route_dataset(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        rel = (query.get("path") or [""])[0]
        if not rel:
            self._send_json({"error": "missing path"}, status=400)
            return
        offset = _int_param(query, "offset", 0)
        limit = _int_param(query, "limit", 100)
        data = self.store.get_dataset(params["tenant"], unquote(rel), offset=offset, limit=limit)
        self._send_json_or_404(data)

    def _route_docs(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        self._send_json(self.store.list_docs(params["tenant"]))

    def _route_doc(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        rel = (query.get("path") or [""])[0]
        if not rel:
            self._send_json({"error": "missing path"}, status=400)
            return
        data = self.store.get_doc(params["tenant"], unquote(rel))
        self._send_json_or_404(data)

    # -- response helpers ------------------------------------------------

    def _send_json_or_404(self, data: Any) -> None:
        if data is None:
            self._send_json({"error": "not found"}, status=404)
        else:
            self._send_json(data)

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self._send_json({"error": "not found"}, status=404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)


def _int_param(query: Dict[str, List[str]], name: str, default: int) -> int:
    raw = (query.get(name) or [None])[0]
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_query(raw_query: str) -> Dict[str, List[str]]:
    return parse_qs(raw_query, keep_blank_values=True)


def _overview_tenant_ids(query: Dict[str, List[str]]) -> List[str] | None:
    if "tenants" not in query:
        return None
    raw = query.get("tenants", [""])[0]
    return [tenant_id for tenant_id in raw.split(",") if tenant_id]


def _match(pattern: str, path: str) -> Dict[str, str] | None:
    """Match ``/api/.../{name}/...`` patterns; return captured params or None."""
    pat_parts = pattern.strip("/").split("/")
    path_parts = path.strip("/").split("/")
    if len(pat_parts) != len(path_parts):
        return None
    params: Dict[str, str] = {}
    for pat, actual in zip(pat_parts, path_parts):
        if pat.startswith("{") and pat.endswith("}"):
            params[pat[1:-1]] = unquote(actual)
        elif pat != actual:
            return None
    return params


def serve(tenants_root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the UI server and block until interrupted."""
    store = TenantStore(tenants_root)

    handler = type("_BoundHandler", (_Handler,), {"store": store})
    httpd = ThreadingHTTPServer((host, port), handler)

    url = f"http://{host}:{port}/"
    print(f"Hephaestus UI serving {tenants_root} at {url}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()
