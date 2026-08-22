# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAPO web UI filesystem store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.hephaestus.evaluation_assets.publication import (
    LOGICAL_SPLITS,
    build_release_pointer,
    install_generation,
    write_release_pointer,
)
from src.hephaestus.webui import data as webui_data_module
from src.hephaestus.webui.data import TenantStore


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _publish_generation(
    tenant: Path,
    *,
    asset_id: str,
    suffix: str,
    fingerprint: str,
):
    sources: dict[str, Path] = {}
    for split in LOGICAL_SPLITS:
        path = tenant / "workspace" / suffix / f"{split}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"case_id": f"{suffix}-{split}"}) + "\n",
            encoding="utf-8",
        )
        sources[split] = path
    catalog = tenant / "datasets" / "evaluation_assets" / asset_id
    generation = install_generation(
        catalog,
        tenant_id=tenant.name,
        asset_id=asset_id,
        split_paths=sources,
        build_fingerprint=fingerprint,
    )
    pointer = build_release_pointer(
        tenant_id=tenant.name,
        asset_id=asset_id,
        generation=generation,
        stage_8_receipt_sha256="a" * 64,
        build_provenance_sha256="b" * 64,
        published_at="2026-08-20T00:00:00+00:00",
    )
    write_release_pointer(catalog, pointer)
    return generation


def test_dataset_catalog_lists_only_pointer_current_studio_splits(
    tmp_path: Path,
) -> None:
    """Studio discovery omits generations, temps, and legacy catalog copies."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    ordinary = tenant / "datasets" / "ordinary.jsonl"
    ordinary.parent.mkdir(parents=True)
    ordinary.write_text('{"case_id":"ordinary"}\n', encoding="utf-8")
    historical = _publish_generation(
        tenant,
        asset_id="asset",
        suffix="historical",
        fingerprint="c" * 64,
    )
    current = _publish_generation(
        tenant,
        asset_id="asset",
        suffix="current",
        fingerprint="d" * 64,
    )
    catalog = tenant / "datasets" / "evaluation_assets" / "asset"
    (catalog / "train.jsonl").write_text("legacy\n", encoding="utf-8")
    temporary = catalog / "generations" / ".unfinished.tmp"
    temporary.mkdir()
    (temporary / "train.jsonl").write_text("partial\n", encoding="utf-8")

    store = TenantStore(tenants, repository_base=tmp_path)
    listed = store.list_datasets("demo")
    listed_paths = {row["path"] for row in listed}

    expected_current = {
        path.relative_to(tenant).as_posix() for path in current.files.values()
    }
    assert listed_paths == {"datasets/ordinary.jsonl", *expected_current}
    assert store.has_evaluation_asset_datasets("demo") is True
    current_train = current.files["train"].relative_to(tenant).as_posix()
    assert store.get_dataset("demo", current_train)["rows"] == [
        {"case_id": "current-train"}
    ]
    historical_train = historical.files["train"].relative_to(tenant).as_posix()
    assert store.get_dataset("demo", historical_train)["rows"] == [
        {"case_id": "historical-train"}
    ]
    assert store.get_dataset(
        "demo", "datasets/evaluation_assets/asset/train.jsonl"
    ) is None

    (historical.generation_dir / "generation_manifest.json").write_text(
        "{}\n", encoding="utf-8"
    )
    assert store.get_dataset("demo", historical_train) is None


def test_corrupt_studio_pointer_fails_closed_without_hiding_ordinary_data(
    tmp_path: Path,
) -> None:
    """A corrupt release pointer never causes raw generation recursion."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    ordinary = tenant / "datasets" / "ordinary.jsonl"
    ordinary.parent.mkdir(parents=True)
    ordinary.write_text('{"case_id":"ordinary"}\n', encoding="utf-8")
    _publish_generation(
        tenant,
        asset_id="asset",
        suffix="current",
        fingerprint="e" * 64,
    )
    pointer = tenant / "datasets" / "evaluation_assets" / "asset" / "release.json"
    pointer.write_text("{}\n", encoding="utf-8")

    store = TenantStore(tenants, repository_base=tmp_path)

    assert [row["path"] for row in store.list_datasets("demo")] == [
        "datasets/ordinary.jsonl"
    ]
    assert store.has_evaluation_asset_datasets("demo") is False


def test_ordinary_symlink_alias_into_studio_is_protected_and_unreadable(
    tmp_path: Path,
) -> None:
    """An ordinary-looking alias cannot bypass immutable Studio validation."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    current = _publish_generation(
        tenant,
        asset_id="asset",
        suffix="current",
        fingerprint="f" * 64,
    )
    alias = tenant / "datasets" / "alias.jsonl"
    alias.symlink_to(current.files["train"])
    store = TenantStore(tenants, repository_base=tmp_path)

    assert "datasets/alias.jsonl" not in {
        row["path"] for row in store.list_datasets("demo")
    }
    assert store.is_evaluation_asset_dataset("demo", "datasets/alias.jsonl")
    assert store.get_dataset("demo", "datasets/alias.jsonl") is None


def test_prepared_ordinary_snapshot_rejects_swap_to_studio_before_read(
    tmp_path: Path,
) -> None:
    """A path swap after classification cannot expose Studio row bytes."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    ordinary = tenant / "datasets" / "ordinary.jsonl"
    ordinary.parent.mkdir(parents=True)
    ordinary.write_text('{"case_id":"ordinary"}\n', encoding="utf-8")
    current = _publish_generation(
        tenant,
        asset_id="asset",
        suffix="current",
        fingerprint="e" * 64,
    )
    store = TenantStore(tenants, repository_base=tmp_path)
    snapshot, studio_data = store.prepare_dataset(
        "demo",
        "datasets/ordinary.jsonl",
    )
    assert studio_data is False
    ordinary.unlink()
    ordinary.symlink_to(current.files["train"])

    assert store.materialize_dataset(snapshot) is None


def test_studio_listing_defers_release_validation_until_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-authorization listing preparation never hashes Studio split bytes."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    _publish_generation(
        tenant,
        asset_id="asset",
        suffix="current",
        fingerprint="9" * 64,
    )
    store = TenantStore(tenants, repository_base=tmp_path)
    real_resolve = webui_data_module.resolve_evaluation_asset_release
    calls: list[Path] = []

    def tracked_resolve(catalog: Path, **kwargs):
        calls.append(catalog)
        return real_resolve(catalog, **kwargs)

    monkeypatch.setattr(
        webui_data_module,
        "resolve_evaluation_asset_release",
        tracked_resolve,
    )

    prepared, studio_data = store.prepare_dataset_listing("demo")

    assert studio_data is True
    assert calls == []
    assert len(store.materialize_dataset_listing(prepared)) == 4
    assert calls


def test_historical_studio_read_defers_generation_hashes_until_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Historical Studio files are classified cheaply before authorization."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    generation = _publish_generation(
        tenant,
        asset_id="asset",
        suffix="historical",
        fingerprint="8" * 64,
    )
    relative = generation.files["train"].relative_to(tenant).as_posix()
    store = TenantStore(tenants, repository_base=tmp_path)
    real_validate = webui_data_module.validate_historical_generation
    calls: list[Path] = []

    def tracked_validate(directory: Path, **kwargs):
        calls.append(directory)
        return real_validate(directory, **kwargs)

    monkeypatch.setattr(
        webui_data_module,
        "validate_historical_generation",
        tracked_validate,
    )

    prepared, studio_data = store.prepare_dataset("demo", relative)

    assert studio_data is True
    assert calls == []
    assert store.materialize_dataset(prepared)["rows"] == [
        {"case_id": "historical-train"}
    ]
    assert calls


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

    runs = TenantStore(tenants, repository_base=tmp_path).list_runs("demo")

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

    run = TenantStore(tenants, repository_base=tmp_path).get_run(
        "demo",
        "evals/tmp/chain-variant002-val",
    )

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

    store = TenantStore(tenants, repository_base=tmp_path)
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

    store = TenantStore(tenants, repository_base=tmp_path)
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

    store = TenantStore(tenants, repository_base=tmp_path)

    assert store.list_configs("demo") == [
        {"path": "config/local.json", "name": "local.json", "bytes": 17},
        {"path": "configs/nested/train.json", "name": "train.json", "bytes": 18},
    ]
    assert store.get_config("demo", "configs/nested/train.json") == {
        "path": "configs/nested/train.json",
        "content": '{"split":"train"}\n',
    }
    assert store.get_config("demo", "README.md") is None


def test_evaluation_asset_only_directory_is_a_tenant(tmp_path: Path) -> None:
    tenant = tmp_path / "bootstrap_tenant"
    asset = tenant / "evaluation_assets" / "v1"
    for name in (
        "raw_inputs",
        "prepared_inputs",
        "decision_assets",
        "review_queues",
        "dataset_splits",
    ):
        (asset / name).mkdir(parents=True, exist_ok=True)
    (asset / "config.json").write_text(
        json.dumps(
            {
                "tenant_id": "bootstrap_tenant",
                "asset_id": "v1",
                "cluster_count": 10,
            }
        ),
        encoding="utf-8",
    )
    (asset / "pipeline_state.json").write_text(
        json.dumps(
            {
                "tenant_id": "bootstrap_tenant",
                "asset_id": "v1",
                "status": "running",
                "current_stage": "rubric_extraction",
                "stages": [],
            }
        ),
        encoding="utf-8",
    )

    store = TenantStore(tmp_path, repository_base=tmp_path.parent)
    listed = store.list_tenants()

    assert [row["tenant_id"] for row in listed] == ["bootstrap_tenant"]
    assert listed[0]["evaluation_asset_count"] == 1
    assert listed[0]["evaluation_asset"]["state"]["current_stage"] == "rubric_extraction"


def test_evaluation_asset_stage_returns_bounded_artifact_previews(
    tmp_path: Path,
) -> None:
    tenant = tmp_path / "bootstrap_tenant"
    asset = tenant / "evaluation_assets" / "v1"
    for name in ("raw_inputs", "prepared_inputs", "decision_assets", "dataset_splits"):
        (asset / name).mkdir(parents=True, exist_ok=True)
    _write_json(
        asset / "config.json",
        {
            "tenant_id": "bootstrap_tenant",
            "asset_id": "v1",
            "cluster_count": 10,
        },
    )
    _write_json(
        asset / "pipeline_state.json",
        {
            "tenant_id": "bootstrap_tenant",
            "asset_id": "v1",
            "status": "completed",
            "counts": {"intent_clusters": 82},
            "stages": [
                {
                    "stage": "intent_clustering",
                    "label": "Mine intent clusters",
                    "status": "completed",
                    "message": "82 clusters created",
                }
            ],
        },
    )
    inventory = asset / "decision_assets" / "intent_inventory.jsonl"
    inventory.write_text(
        "\n".join(
            json.dumps(
                {
                    "cluster_id": f"route-{index:03d}",
                    "route": "route",
                    "size": index + 1,
                }
            )
            for index in range(82)
        )
        + "\n",
        encoding="utf-8",
    )

    store = TenantStore(tmp_path, repository_base=tmp_path.parent)
    detail = store.get_evaluation_asset_stage(
        "bootstrap_tenant",
        "v1",
        "intent_clustering",
    )

    assert detail is not None
    assert detail["status"] == "completed"
    assert detail["counts"]["intent_clusters"] == 82
    assert detail["artifacts"][0]["row_count"] == 82
    assert len(detail["artifacts"][0]["preview"]) == 1
    assert len(detail["clusters"]) == 82
    assert (
        store.get_evaluation_asset_stage("bootstrap_tenant", "v1", "unknown")
        is None
    )


def test_evaluation_asset_stage_reads_stage_oriented_layout(
    tmp_path: Path,
) -> None:
    tenant = tmp_path / "bootstrap_tenant"
    asset = tenant / "evaluation_assets" / "v1"
    prepared = asset / "stages" / "02_prepared_inputs"
    guidelines = asset / "stages" / "03_evaluation_guidelines"
    clustering = asset / "stages" / "04_intent_clustering"
    prepared.mkdir(parents=True)
    guidelines.mkdir(parents=True)
    clustering.mkdir(parents=True)
    _write_json(
        asset / "config.json",
        {"tenant_id": "bootstrap_tenant", "asset_id": "v1"},
    )
    _write_json(
        asset / "pipeline_state.json",
        {
            "tenant_id": "bootstrap_tenant",
            "asset_id": "v1",
            "status": "completed",
            "stages": [],
        },
    )
    (prepared / "intent_records.jsonl").write_text(
        '{"record_id":"r1","user_input":"request alpha"}\n',
        encoding="utf-8",
    )
    (guidelines / "feedback_evidence.jsonl").write_text(
        '{"record_id":"f1","observations":[]}\n',
        encoding="utf-8",
    )
    (guidelines / "candidate_guidelines.jsonl").write_text(
        '{"intent_label":"answer"}\n',
        encoding="utf-8",
    )
    (guidelines / "evaluation_guidelines.jsonl").write_text(
        '{"guideline_id":"guideline-answer"}\n',
        encoding="utf-8",
    )
    (clustering / "intent_inventory.jsonl").write_text(
        json.dumps(
            {
                "cluster_id": "route-001",
                "route": "route",
                "size": 1,
                "record_ids": ["r1"],
                "representative_ids": ["r1"],
                "top_terms": ["alpha"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    detail = TenantStore(
        tmp_path,
        repository_base=tmp_path.parent,
    ).get_evaluation_asset_stage(
        "bootstrap_tenant",
        "v1",
        "intent_clustering",
    )

    assert detail is not None
    assert detail["artifacts"][0]["path"].endswith(
        "stages/04_intent_clustering/intent_inventory.jsonl"
    )
    assert detail["clusters"][0]["representatives"] == ["request alpha"]
    guideline_detail = TenantStore(
        tmp_path,
        repository_base=tmp_path.parent,
    ).get_evaluation_asset_stage(
        "bootstrap_tenant",
        "v1",
        "rubric_extraction",
    )
    assert guideline_detail is not None
    artifacts = {item["name"]: item for item in guideline_detail["artifacts"]}
    assert artifacts["evaluation_guidelines.jsonl"]["display_name"] == (
        "Evaluation guidelines"
    )
    assert artifacts["evaluation_guidelines.jsonl"]["group"] == "Key outputs"


def test_missing_label_artifacts_belong_to_label_inference(
    tmp_path: Path,
) -> None:
    tenant = tmp_path / "bootstrap_tenant"
    asset = tenant / "evaluation_assets" / "v1"
    for name in (
        "raw_inputs",
        "prepared_inputs",
        "decision_assets",
        "review_queues",
        "dataset_splits",
    ):
        (asset / name).mkdir(parents=True, exist_ok=True)
    _write_json(
        asset / "config.json",
        {"tenant_id": "bootstrap_tenant", "asset_id": "v1"},
    )
    _write_json(
        asset / "pipeline_state.json",
        {
            "tenant_id": "bootstrap_tenant",
            "asset_id": "v1",
            "status": "completed",
            "stages": [],
        },
    )
    (asset / "decision_assets" / "intent_matches.jsonl").write_text(
        '{"cluster_id":"cluster-1"}\n',
        encoding="utf-8",
    )
    (asset / "decision_assets" / "coverage_report.md").write_text(
        "# Coverage\n",
        encoding="utf-8",
    )
    (asset / "review_queues" / "labeling_queue.jsonl").write_text(
        '{"queue_id":"cluster-1:record-1"}\n',
        encoding="utf-8",
    )
    (
        asset
        / "decision_assets"
        / "missing_labeled_feedback_clusters.jsonl"
    ).write_text('{"cluster_id":"cluster-2"}\n', encoding="utf-8")
    (
        asset
        / "decision_assets"
        / "missing_labeled_feedback_report.md"
    ).write_text("# Missing\n", encoding="utf-8")

    store = TenantStore(tmp_path, repository_base=tmp_path.parent)
    coverage = store.get_evaluation_asset_stage(
        "bootstrap_tenant",
        "v1",
        "coverage_decisions",
    )
    inference = store.get_evaluation_asset_stage(
        "bootstrap_tenant",
        "v1",
        "label_inference",
    )

    assert coverage is not None
    assert inference is not None
    assert {item["name"] for item in coverage["artifacts"]} == {
        "intent_matches.jsonl",
        "coverage_report.md",
        "labeling_queue.jsonl",
    }
    labeling_queue = next(
        item
        for item in coverage["artifacts"]
        if item["name"] == "labeling_queue.jsonl"
    )
    assert labeling_queue["display_name"] == "Traces to label"
    assert labeling_queue["group"] == "Needs attention"
    coverage_report = next(
        item
        for item in coverage["artifacts"]
        if item["name"] == "coverage_report.md"
    )
    assert coverage_report["content"] == "# Coverage\n"
    assert coverage_report["content_truncated"] is False
    assert {
        "missing_labeled_feedback_clusters.jsonl",
        "missing_labeled_feedback_report.md",
    }.issubset(item["name"] for item in inference["artifacts"])
