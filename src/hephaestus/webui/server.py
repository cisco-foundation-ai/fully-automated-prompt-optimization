# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Zero-dependency HTTP server for the local web UI.

Serves the Explorer at ``/``, the Evaluation Asset Studio at
``/evaluation-assets/``, and a small JSON API under ``/api/``. Built on
:mod:`http.server` so the UI requires no extra packages beyond the standard
library.

Routes:
    GET /                                          -> SPA shell (HTML)
    GET /evaluation-assets/                        -> asset studio (HTML)
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
    GET /api/tenants/<t>/evaluation-assets         -> asset pipeline summaries
    GET /api/tenants/<t>/evaluation-assets/<a>/stages/<s> -> stage details
    POST /api/evaluation-assets/start              -> create and run an asset
    POST /api/evaluation-assets/extend             -> create an incremental version
    POST /api/tenants/<t>/evaluation-assets/<a>/resume -> revise and resume an asset
"""

from __future__ import annotations

import ipaddress
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from src.hephaestus.evaluation_assets.input_contract import input_contract_document
from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig
from src.hephaestus.evaluation_assets.service import EvaluationAssetRunManager
from src.hephaestus.webui.data import TenantStore
from src.hephaestus.webui.evaluation_assets_frontend import EVALUATION_ASSET_HTML
from src.hephaestus.webui.frontend import INDEX_HTML

_LOGO_PATH = Path(__file__).with_name("assets") / "fapo-explorer-logo.webp"

RUBRIC_MODELS = {
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.2",
    "gpt-5.1",
    "gpt-5",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4o-mini",
    "o3",
    "o4-mini",
}
OPENAI_EMBEDDING_MODELS = {
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
}


class _ThreadingHTTPServerV6(ThreadingHTTPServer):
    address_family = socket.AF_INET6


class _Handler(BaseHTTPRequestHandler):
    store: TenantStore  # injected via factory below
    asset_manager: EvaluationAssetRunManager

    server_version = "HephaestusUI/0.1"

    # Silence the default noisy per-request logging.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        parsed = urlparse(self.path)
        path = parsed.path
        query = _parse_query(parsed.query)
        if _is_studio_path(path) and not self._authorize_studio_request():
            return

        if path in ("/", "/index.html"):
            self._send_html(INDEX_HTML)
            return

        if path in (
            "/evaluation-assets",
            "/evaluation-assets/",
            "/evaluation-assets/index.html",
        ):
            self._send_html(EVALUATION_ASSET_HTML)
            return

        if path == "/assets/fapo-explorer-logo.webp":
            self._send_file(_LOGO_PATH, "image/webp")
            return

        if path == "/api/overview":
            self._send_json(self.store.overview(_overview_tenant_ids(query)))
            return

        if path == "/api/evaluation-assets/input-contract":
            self._send_json(input_contract_document())
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

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        parsed = urlparse(self.path)
        if _is_studio_path(parsed.path) and not self._authorize_studio_request(
            mutation=True
        ):
            return
        if parsed.path == "/api/evaluation-assets/start":
            self._route_start_evaluation_asset()
            return
        if parsed.path == "/api/evaluation-assets/extend":
            self._route_extend_evaluation_asset()
            return
        params = _match(
            "/api/tenants/{tenant}/evaluation-assets/{asset}/resume",
            parsed.path,
        )
        if params is not None:
            self._route_resume_evaluation_asset(params)
            return
        self._send_json({"error": "not found", "path": parsed.path}, status=404)

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
            (
                "/api/tenants/{tenant}/evaluation-assets",
                _Handler._route_evaluation_assets,
            ),
            (
                "/api/tenants/{tenant}/evaluation-assets/{asset}/stages/{stage}",
                _Handler._route_evaluation_asset_stage,
            ),
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
        studio_data = self.store.run_uses_evaluation_asset_dataset(
            params["tenant"],
            run_rel,
        )
        if studio_data and not self._authorize_studio_request(no_store=True):
            return
        data = self.store.get_case(params["tenant"], run_rel, index)
        self._send_json_or_404(data, no_store=studio_data)

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
        studio_data = self.store.has_evaluation_asset_datasets(params["tenant"])
        if studio_data and not self._authorize_studio_request(no_store=True):
            return
        self._send_json(
            self.store.list_datasets(params["tenant"]),
            no_store=studio_data,
        )

    def _route_dataset(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        rel = (query.get("path") or [""])[0]
        if not rel:
            self._send_json({"error": "missing path"}, status=400)
            return
        dataset_rel = unquote(rel)
        studio_data = self.store.is_evaluation_asset_dataset(
            params["tenant"],
            dataset_rel,
        )
        if studio_data and not self._authorize_studio_request(no_store=True):
            return
        offset = _int_param(query, "offset", 0)
        limit = _int_param(query, "limit", 100)
        data = self.store.get_dataset(
            params["tenant"],
            dataset_rel,
            offset=offset,
            limit=limit,
        )
        self._send_json_or_404(data, no_store=studio_data)

    def _route_docs(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        self._send_json(self.store.list_docs(params["tenant"]))

    def _route_doc(self, params: Dict[str, str], query: Dict[str, List[str]]) -> None:
        rel = (query.get("path") or [""])[0]
        if not rel:
            self._send_json({"error": "missing path"}, status=400)
            return
        data = self.store.get_doc(params["tenant"], unquote(rel))
        self._send_json_or_404(data)

    def _route_evaluation_assets(
        self,
        params: Dict[str, str],
        query: Dict[str, List[str]],
    ) -> None:
        assets = self.store.list_evaluation_assets(params["tenant"])
        for asset in assets:
            asset["runner_active"] = self.asset_manager.is_running(
                params["tenant"],
                str(asset["asset_id"]),
            )
        self._send_json(assets)

    def _route_evaluation_asset_stage(
        self,
        params: Dict[str, str],
        query: Dict[str, List[str]],
    ) -> None:
        data = self.store.get_evaluation_asset_stage(
            params["tenant"],
            params["asset"],
            params["stage"],
        )
        self._send_json_or_404(data)

    def _route_start_evaluation_asset(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        try:
            cluster_count = int(payload.get("cluster_count") or 50)
            if not 1 <= cluster_count <= 1000:
                raise ValueError("cluster_count must be between 1 and 1000")
            raw_match_threshold = payload.get("match_threshold")
            match_threshold = (
                0.6
                if raw_match_threshold is None or raw_match_threshold == ""
                else float(raw_match_threshold)
            )
            if not 0.0 <= match_threshold <= 1.0:
                raise ValueError("match_threshold must be between 0 and 1")
            synthetic_coverage_enabled = str(
                payload.get("synthetic_coverage_enabled", "false")
            ).lower() in {"1", "true", "yes", "on"}
            synthetic_cases_per_cluster = int(
                payload.get("synthetic_cases_per_cluster") or 1
            )
            if not 1 <= synthetic_cases_per_cluster <= 100:
                raise ValueError(
                    "synthetic_cases_per_cluster must be between 1 and 100"
                )
            rubric_model = str(payload.get("rubric_model") or "gpt-5.5")
            embedding_model = str(
                payload.get("embedding_model") or "text-embedding-3-small"
            )
            if rubric_model not in RUBRIC_MODELS:
                raise ValueError("unsupported rubric_model")
            if (
                embedding_model not in OPENAI_EMBEDDING_MODELS
                and embedding_model != "tfidf"
            ):
                raise ValueError("unsupported embedding_model")
            embedding_provider = (
                "tfidf" if embedding_model == "tfidf" else "openai"
            )
            config = EvaluationAssetConfig(
                tenant_id=str(payload["tenant_id"]),
                asset_id=str(payload.get("asset_id") or "v1"),
                rubric_model=rubric_model,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                cluster_count=cluster_count,
                match_threshold=match_threshold,
                synthetic_coverage_enabled=synthetic_coverage_enabled,
                synthetic_cases_per_cluster=synthetic_cases_per_cluster,
            )
            state = self.asset_manager.start(
                config,
                Path(str(payload["feedback_path"])),
                Path(str(payload["unlabeled_path"])),
            )
        except FileExistsError as exc:
            self._send_json({"error": str(exc)}, status=409)
            return
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=409)
            return
        except (KeyError, TypeError, ValueError, OSError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        self._send_json(state, status=202)

    def _route_resume_evaluation_asset(self, params: Dict[str, str]) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        try:
            updates = _validated_resume_updates(payload)
            state = self.asset_manager.resume(
                params["tenant"],
                params["asset"],
                updates,
            )
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=409)
            return
        except (ValueError, OSError, KeyError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        self._send_json(state, status=202)

    def _route_extend_evaluation_asset(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        try:
            mode = str(payload.get("clustering_mode") or "keep")
            if mode not in {"keep", "refresh"}:
                raise ValueError("clustering_mode must be 'keep' or 'refresh'")
            updates: Dict[str, Any] = {}
            if payload.get("embedding_model"):
                embedding_model = str(payload["embedding_model"])
                if (
                    embedding_model not in OPENAI_EMBEDDING_MODELS
                    and embedding_model != "tfidf"
                ):
                    raise ValueError("unsupported embedding_model")
                updates["embedding_model"] = embedding_model
            if payload.get("cluster_count") not in {None, ""}:
                cluster_count = int(payload["cluster_count"])
                if not 1 <= cluster_count <= 1000:
                    raise ValueError("cluster_count must be between 1 and 1000")
                updates["cluster_count"] = cluster_count
            feedback_value = str(payload.get("additional_feedback_path") or "").strip()
            unlabeled_value = str(payload.get("additional_unlabeled_path") or "").strip()
            state = self.asset_manager.extend(
                str(payload["tenant_id"]),
                str(payload["parent_asset_id"]),
                str(payload["asset_id"]),
                additional_feedback=(
                    Path(feedback_value) if feedback_value else None
                ),
                additional_unlabeled=(
                    Path(unlabeled_value) if unlabeled_value else None
                ),
                clustering_mode=mode,
                config_updates=updates,
            )
        except FileExistsError as exc:
            self._send_json({"error": str(exc)}, status=409)
            return
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=409)
            return
        except (KeyError, TypeError, ValueError, OSError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return
        self._send_json(state, status=202)

    # -- response helpers ------------------------------------------------

    def _send_json_or_404(self, data: Any, *, no_store: bool = False) -> None:
        if data is None:
            self._send_json({"error": "not found"}, status=404, no_store=no_store)
        else:
            self._send_json(data, no_store=no_store)

    def _send_json(
        self,
        payload: Any,
        status: int = 200,
        *,
        no_store: bool = False,
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if no_store or _is_studio_path(urlparse(getattr(self, "path", "")).path):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self, max_bytes: int = 1024 * 1024) -> Dict[str, Any] | None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("application/json"):
            self._send_json({"error": "Content-Type must be application/json"}, status=415)
            return None
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "invalid Content-Length"}, status=400)
            return None
        if content_length < 1:
            self._send_json({"error": "request body is empty"}, status=400)
            return None
        if content_length > max_bytes:
            self._send_json({"error": "request body is too large"}, status=413)
            return None
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json({"error": "request body must be valid JSON"}, status=400)
            return None
        if not isinstance(payload, dict):
            self._send_json({"error": "request body must be a JSON object"}, status=400)
            return None
        return payload

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if _is_studio_path(urlparse(getattr(self, "path", "")).path):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorize_studio_request(
        self,
        *,
        mutation: bool = False,
        no_store: bool = False,
    ) -> bool:
        authority = self.headers.get("Host", "")
        if not _is_loopback_authority(authority):
            self._send_json(
                {"error": "Evaluation Asset Studio requires a loopback Host"},
                status=403,
                no_store=no_store,
            )
            return False
        origin = self.headers.get("Origin")
        if mutation and origin and not _is_same_http_origin(origin, authority):
            self._send_json(
                {"error": "Evaluation Asset Studio mutation Origin must match Host"},
                status=403,
                no_store=no_store,
            )
            return False
        return True

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


def _validated_resume_updates(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user-editable pipeline decisions accepted on resume."""
    allowed = {
        "rubric_model",
        "embedding_model",
        "cluster_count",
        "batch_size",
        "match_threshold",
        "min_trusted_examples",
        "min_trusted_groups",
        "max_unlabeled_to_trusted_ratio",
        "synthetic_coverage_enabled",
        "synthetic_cases_per_cluster",
        "split_seed",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(
            "unsupported resume fields: " + ", ".join(sorted(unknown))
        )
    updates: Dict[str, Any] = {}
    if "rubric_model" in payload:
        rubric_model = str(payload["rubric_model"])
        if rubric_model not in RUBRIC_MODELS:
            raise ValueError("unsupported rubric_model")
        updates["rubric_model"] = rubric_model
    if "embedding_model" in payload:
        embedding_model = str(payload["embedding_model"])
        if (
            embedding_model not in OPENAI_EMBEDDING_MODELS
            and embedding_model != "tfidf"
        ):
            raise ValueError("unsupported embedding_model")
        updates["embedding_model"] = embedding_model
    if "cluster_count" in payload:
        cluster_count = int(payload["cluster_count"])
        if not 1 <= cluster_count <= 1000:
            raise ValueError("cluster_count must be between 1 and 1000")
        updates["cluster_count"] = cluster_count
    if "batch_size" in payload:
        batch_size = int(payload["batch_size"])
        if not 1 <= batch_size <= 100:
            raise ValueError("batch_size must be between 1 and 100")
        updates["batch_size"] = batch_size
    if "match_threshold" in payload:
        match_threshold = float(payload["match_threshold"])
        if not 0.0 <= match_threshold <= 1.0:
            raise ValueError("match_threshold must be between 0 and 1")
        updates["match_threshold"] = match_threshold
    if "min_trusted_examples" in payload:
        min_trusted_examples = int(payload["min_trusted_examples"])
        if min_trusted_examples < 1:
            raise ValueError("min_trusted_examples must be at least 1")
        updates["min_trusted_examples"] = min_trusted_examples
    if "min_trusted_groups" in payload:
        min_trusted_groups = int(payload["min_trusted_groups"])
        if min_trusted_groups < 0:
            raise ValueError("min_trusted_groups must be at least 0")
        updates["min_trusted_groups"] = min_trusted_groups
    if "max_unlabeled_to_trusted_ratio" in payload:
        raw_ratio = payload["max_unlabeled_to_trusted_ratio"]
        ratio = None if raw_ratio is None or raw_ratio == "" else float(raw_ratio)
        if ratio is not None and ratio <= 0:
            raise ValueError(
                "max_unlabeled_to_trusted_ratio must be positive"
            )
        updates["max_unlabeled_to_trusted_ratio"] = ratio
    if "synthetic_coverage_enabled" in payload:
        raw_enabled = payload["synthetic_coverage_enabled"]
        updates["synthetic_coverage_enabled"] = (
            raw_enabled
            if isinstance(raw_enabled, bool)
            else str(raw_enabled).lower() in {"1", "true", "yes", "on"}
        )
    if "synthetic_cases_per_cluster" in payload:
        cases_per_cluster = int(payload["synthetic_cases_per_cluster"])
        if not 1 <= cases_per_cluster <= 100:
            raise ValueError(
                "synthetic_cases_per_cluster must be between 1 and 100"
            )
        updates["synthetic_cases_per_cluster"] = cases_per_cluster
    if "split_seed" in payload:
        updates["split_seed"] = int(payload["split_seed"])
    return updates


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


def _is_studio_path(path: str) -> bool:
    if path in {"/api/overview", "/api/tenants"}:
        return True
    if path == "/evaluation-assets" or path.startswith("/evaluation-assets/"):
        return True
    if path == "/api/evaluation-assets" or path.startswith(
        "/api/evaluation-assets/"
    ):
        return True
    parts = path.strip("/").split("/")
    return (
        len(parts) >= 4
        and parts[0] == "api"
        and parts[1] == "tenants"
        and parts[3] == "evaluation-assets"
    )


def _is_loopback_name(hostname: str) -> bool:
    candidate = hostname.strip().strip("[]")
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return candidate.rstrip(".").lower() == "localhost"


def _parsed_authority(authority: str) -> Tuple[str, int] | None:
    if not authority or any(character.isspace() for character in authority):
        return None
    parsed = urlparse(f"//{authority}")
    if parsed.username is not None or parsed.password is not None:
        return None
    try:
        port = parsed.port or 80
    except ValueError:
        return None
    if parsed.hostname is None or parsed.path:
        return None
    return _normalized_host(parsed.hostname), port


def _normalized_host(hostname: str) -> str:
    candidate = hostname.rstrip(".").lower()
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        return candidate


def _is_loopback_authority(authority: str) -> bool:
    parsed = _parsed_authority(authority)
    return parsed is not None and _is_loopback_name(parsed[0])


def _is_same_http_origin(origin: str, authority: str) -> bool:
    request_authority = _parsed_authority(authority)
    parsed = urlparse(origin)
    if (
        request_authority is None
        or parsed.scheme.lower() != "http"
        or not parsed.netloc
        or parsed.path
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False
    try:
        origin_port = parsed.port or 80
    except ValueError:
        return False
    if parsed.hostname is None:
        return False
    return request_authority == (_normalized_host(parsed.hostname), origin_port)


def serve(tenants_root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the UI server and block until interrupted."""
    if not _is_loopback_name(host):
        raise ValueError("Evaluation Asset Studio must bind to a loopback host")
    bind_host = host.strip().strip("[]")
    try:
        bind_address = ipaddress.ip_address(bind_host)
    except ValueError:
        bind_address = None
    server_type = (
        _ThreadingHTTPServerV6
        if isinstance(bind_address, ipaddress.IPv6Address)
        else ThreadingHTTPServer
    )
    store = TenantStore(tenants_root)
    asset_manager = EvaluationAssetRunManager(tenants_root)

    handler = type(
        "_BoundHandler",
        (_Handler,),
        {"store": store, "asset_manager": asset_manager},
    )
    httpd = server_type((bind_host, port), handler)

    url_host = f"[{bind_host}]" if isinstance(bind_address, ipaddress.IPv6Address) else bind_host
    url = f"http://{url_host}:{httpd.server_address[1]}/"
    print(f"Hephaestus UI serving {tenants_root} at {url}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()
