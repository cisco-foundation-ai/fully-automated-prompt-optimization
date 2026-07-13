#!/usr/bin/env python3
# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Local UI server for the standalone mini challenge."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from mini_eval import (
    DEFAULT_LEVEL,
    LABELS,
    LEVEL_CONFIG,
    build_starter_prompt,
    evaluate_prompt,
    get_level_config,
    load_fapo_results,
    load_jsonl,
    load_test_cases,
)

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
TRAIN_REFERENCE = BASE_DIR / "data" / "train_reference.jsonl"


def flatten_case(row: dict[str, Any], include_expected: bool = True) -> dict[str, Any]:
    metadata = row.get("metadata", {})
    flat = {
        "case_id": row.get("case_id", ""),
        "software_name": row.get("context", {}).get("software_name", ""),
        "difficulty": metadata.get("difficulty", ""),
        "ambiguity_type": metadata.get("ambiguity_type", ""),
    }
    if include_expected:
        flat["expected"] = row.get("expected", {}).get("category", "")
    return flat


def requested_level(query: str) -> str:
    params = parse_qs(query)
    return params.get("level", [DEFAULT_LEVEL])[0]


def level_payload(level: str) -> dict[str, Any]:
    config = get_level_config(level)
    cases = load_test_cases(config["test_data"])
    return {
        "id": level,
        "name": config["name"],
        "labels": config["labels"],
        "label_count": len(config["labels"]),
        "test_count": len(cases),
        "starter_prompt": build_starter_prompt(list(config["labels"])),
        "fapo_reference": load_fapo_results(config["fapo_results"]),
    }


class MiniChallengeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self.send_json(
                200,
                {
                    "labels": LABELS,
                    "default_level": DEFAULT_LEVEL,
                    "levels": [level_payload(level) for level in LEVEL_CONFIG],
                },
            )
            return
        if parsed.path == "/api/training":
            self.send_json(200, [flatten_case(row) for row in load_jsonl(TRAIN_REFERENCE)])
            return
        if parsed.path == "/api/mini-test":
            config = get_level_config(requested_level(parsed.query))
            rows = [flatten_case(row, include_expected=False) for row in load_jsonl(config["test_data"])]
            self.send_json(200, rows)
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/evaluate":
            self.send_json(404, {"error": "Not found"})
            return

        try:
            payload = self.read_json_body()
            prompt = str(payload.get("prompt", "")).strip()
            model = str(payload.get("model", "gpt-4o-mini")).strip() or "gpt-4o-mini"
            level = str(payload.get("level", DEFAULT_LEVEL)).strip() or DEFAULT_LEVEL
            config = get_level_config(level)
            if not prompt:
                self.send_json(400, {"error": "Prompt is required."})
                return
            result = evaluate_prompt(
                prompt=prompt,
                model=model,
                test_data=config["test_data"],
                fapo_results_path=config["fapo_results"],
                level=level,
                allowed_labels=list(config["labels"]),
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
            self.send_json(200, result)
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 200_000:
            raise ValueError("Request body is too large.")
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(body)

    def serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        target = (WEB_DIR / relative).resolve()
        if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
            self.send_json(403, {"error": "Forbidden"})
            return
        if not target.exists() or not target.is_file():
            self.send_json(404, {"error": "Not found"})
            return

        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the standalone mini challenge UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_test_cases(get_level_config(DEFAULT_LEVEL)["test_data"])
    address = (args.host, args.port)
    server = ThreadingHTTPServer(address, MiniChallengeHandler)
    print(f"Serving {len(cases)} mini challenge cases at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
