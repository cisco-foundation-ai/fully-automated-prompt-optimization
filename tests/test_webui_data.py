# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAPO web UI filesystem store."""

from __future__ import annotations

import json
from pathlib import Path

from src.hephaestus.webui.data import TenantStore


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_list_runs_recurses_under_evals_tmp(tmp_path: Path) -> None:
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")

    run_dir = tenant / "evals" / "tmp" / "chain-variant002-val"
    _write_json(
        run_dir / "progress.json",
        {
            "run_id": "run-123",
            "status": "completed",
            "total_cases": 2,
            "completed_cases": 2,
            "avg_composite_score": 75.0,
            "updated_at": "2026-06-18T10:00:00",
        },
    )
    _write_json(
        run_dir / "run_config.json",
        {"provider": "openai", "provider_settings": {"model": "gpt-4.1-mini"}},
    )
    (run_dir / "summary.md").write_text("# Summary\n", encoding="utf-8")
    (run_dir / "results.jsonl").write_text('{"case_id":"a","composite_score":100}\n', encoding="utf-8")

    runs = TenantStore(tenants).list_runs("demo")

    assert len(runs) == 1
    assert runs[0]["run_dir"] == "evals/tmp/chain-variant002-val"
    assert runs[0]["name"] == "chain-variant002-val"
    assert runs[0]["run_id"] == "run-123"
    assert runs[0]["avg_composite_score"] == 75.0
    assert runs[0]["has_results"] is True


def test_get_run_supports_nested_run_dir(tmp_path: Path) -> None:
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")

    run_dir = tenant / "evals" / "tmp" / "chain-variant002-val"
    _write_json(run_dir / "progress.json", {"run_id": "run-123", "status": "completed"})
    _write_json(run_dir / "run_config.json", {"provider": "openai"})
    (run_dir / "summary.md").write_text("# Summary\n", encoding="utf-8")
    (run_dir / "results.jsonl").write_text('{"case_id":"a","composite_score":100}\n', encoding="utf-8")

    run = TenantStore(tenants).get_run("demo", "evals/tmp/chain-variant002-val")

    assert run is not None
    assert run["run_dir"] == "evals/tmp/chain-variant002-val"
    assert run["summary_md"] == "# Summary\n"
    assert run["cases"] == [
        {
            "index": 0,
            "case_id": "a",
            "task_type": None,
            "composite_score": 100,
            "total_tool_calls": None,
            "failed_tool_calls": None,
            "score_breakdown": {},
        }
    ]
