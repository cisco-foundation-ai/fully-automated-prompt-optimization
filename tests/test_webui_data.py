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


def test_list_prompts_includes_skills_with_kind_and_group(tmp_path: Path) -> None:
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")

    prompt = tenant / "prompts" / "modules" / "agent" / "variant-001.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("System: hi\n", encoding="utf-8")

    skill = tenant / "skills" / "superlative-index-questions" / "variant-001.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("Drill in first.\n", encoding="utf-8")

    store = TenantStore(tenants)
    prompts = store.list_prompts("demo")

    # Both subtrees surface, each tagged by kind + group (parent dir name).
    by_path = {p["path"]: p for p in prompts}
    assert by_path["prompts/modules/agent/variant-001.md"]["kind"] == "prompt"
    assert by_path["prompts/modules/agent/variant-001.md"]["group"] == "agent"
    assert by_path["skills/superlative-index-questions/variant-001.md"]["kind"] == "skill"
    assert (
        by_path["skills/superlative-index-questions/variant-001.md"]["group"]
        == "superlative-index-questions"
    )


def test_get_prompt_serves_skill_subtree(tmp_path: Path) -> None:
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")

    skill = tenant / "skills" / "answer-formatting" / "variant-002.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("Be decisive.\n", encoding="utf-8")

    store = TenantStore(tenants)
    data = store.get_prompt("demo", "skills/answer-formatting/variant-002.md")
    assert data == {
        "path": "skills/answer-formatting/variant-002.md",
        "content": "Be decisive.\n",
        "kind": "skill",
        "group": "answer-formatting",
    }
    # Files outside the prompt/skill subtrees are still rejected.
    assert store.get_prompt("demo", "docs/tenant-profile.md") is None


def test_list_and_get_configs_support_config_and_configs_dirs(tmp_path: Path) -> None:
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    (tenant / "config" / "local.json").parent.mkdir()
    (tenant / "config" / "local.json").write_text('{"name":"local"}\n', encoding="utf-8")
    (tenant / "configs" / "nested").mkdir(parents=True)
    (tenant / "configs" / "nested" / "train.json").write_text('{"split":"train"}\n', encoding="utf-8")

    store = TenantStore(tenants)

    assert store.list_configs("demo") == [
        {"path": "config/local.json", "name": "local.json", "bytes": 17},
        {"path": "configs/nested/train.json", "name": "train.json", "bytes": 18},
    ]
    assert store.get_config("demo", "configs/nested/train.json") == {
        "path": "configs/nested/train.json",
        "content": '{"split":"train"}\n',
    }
    assert store.get_config("demo", "README.md") is None
