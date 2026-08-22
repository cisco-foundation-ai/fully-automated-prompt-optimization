# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAPO web UI filesystem store."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.hephaestus.evaluation_assets.publication import (
    LOGICAL_SPLITS,
    build_release_pointer,
    install_generation,
    write_release_pointer,
)
from src.hephaestus.runs.bundle import RunBundleWriter
from src.hephaestus.runs.identity import build_run_identity
from src.hephaestus.webui import data as webui_data_module
from src.hephaestus.webui.data import TenantStore
from src.hephaestus.webui.frontend import INDEX_HTML

_DEFAULT_TENANT_ID = object()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _dataset_bytes(rows: list[dict[str, object]]) -> bytes:
    return b"".join(
        (
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        for row in rows
    )


def _publish_authenticated_run(
    tenant: Path,
    *,
    run_name: str = "authenticated-run",
    dataset_rows: list[dict[str, object]] | None = None,
    identity_case_ids: list[str] | None = None,
    progress_overrides: dict[str, object] | None = None,
    run_config_tenant_id: object = _DEFAULT_TENANT_ID,
) -> tuple[Path, Path]:
    rows = dataset_rows or [
        {
            "case_id": "case-1",
            "task_type": "demo",
            "context": {"question": "protected-question"},
            "expected": {"answer": "protected-answer"},
            "metadata": {"source": "protected"},
        }
    ]
    dataset_path = tenant / "datasets" / "cases.jsonl"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    content = _dataset_bytes(rows)
    dataset_path.write_bytes(content)
    dataset_literal = f"tenants/{tenant.name}/datasets/cases.jsonl"
    case_ids = [str(row["case_id"]) for row in rows]
    recorded_case_ids = identity_case_ids or case_ids
    identity = build_run_identity(
        ordered_case_ids=recorded_case_ids,
        dataset_path=dataset_literal,
        dataset_fingerprint="sha256:" + hashlib.sha256(content).hexdigest(),
        split_fingerprint=None,
        scorer_fingerprint=None,
        metric_fingerprint=None,
    ).to_dict()
    run_dir = tenant / "evals" / run_name
    writer = RunBundleWriter.reserve(run_dir, run_id="run-authenticated")
    progress: dict[str, object] = {
        "run_id": "run-authenticated",
        "status": "completed",
        "total_cases": len(recorded_case_ids),
        "completed_cases": len(recorded_case_ids),
        "successful_cases": len(recorded_case_ids),
        "attempted_case_ids": recorded_case_ids,
        "successful_case_ids": recorded_case_ids,
        "failed_case_ids": [],
        "in_flight_case_ids": [],
        "trust_tier_summaries": {},
    }
    progress.update(progress_overrides or {})
    effective_tenant_id = (
        tenant.name
        if run_config_tenant_id is _DEFAULT_TENANT_ID
        else run_config_tenant_id
    )
    writer.publish(
        run_config={
            "run_id": "run-authenticated",
            "tenant_id": effective_tenant_id,
            "dataset_path": dataset_literal,
            "provider": "example-provider",
        },
        run_identity=identity,
        results=[
            {"case_id": case_id, "execution_status": "succeeded"}
            for case_id in recorded_case_ids
        ],
        summary="# Safe summary\n",
        progress=progress,
    )
    return run_dir, dataset_path


def _write_loose_run(
    tenant: Path,
    *,
    run_name: str,
    status: str,
    dataset_path: str,
    case_id: str,
) -> Path:
    run_dir = tenant / "evals" / run_name
    _write_json(
        run_dir / "run_config.json",
        {"run_id": run_name, "dataset_path": dataset_path},
    )
    _write_json(
        run_dir / "progress.json",
        {"run_id": run_name, "status": status},
    )
    (run_dir / "results.jsonl").write_text(
        json.dumps({"case_id": case_id}) + "\n",
        encoding="utf-8",
    )
    return run_dir


def _publish_generation(
    tenant: Path,
    *,
    asset_id: str,
    suffix: str,
    fingerprint: str,
    split_rows: dict[str, dict[str, object]] | None = None,
):
    sources: dict[str, Path] = {}
    for split in LOGICAL_SPLITS:
        path = tenant / "workspace" / suffix / f"{split}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                (split_rows or {}).get(
                    split,
                    {"case_id": f"{suffix}-{split}"},
                )
            )
            + "\n",
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


def test_authenticated_terminal_run_uses_manifest_validated_facts(tmp_path: Path) -> None:
    """Only a validated bundle is marked authoritative and supplies terminal data."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    _publish_authenticated_run(tenant)

    store = TenantStore(tenants, repository_base=tmp_path)
    listed = store.list_runs("demo")
    run = store.get_run("demo", "evals/authenticated-run")

    assert listed[0]["authority"] == "authoritative"
    assert listed[0]["run_id"] == "run-authenticated"
    assert run is not None
    assert run["authority"] == "authoritative"
    assert run["run_manifest"]["schema_version"] == "fapo-run-bundle-manifest-v1"
    assert run["run_manifest"]["hash_algorithm"] == "sha256"
    assert run["run_manifest"]["run_id"] == "run-authenticated"
    assert run["run_manifest"]["status"] == "completed"
    assert run["run_manifest"]["result_count"] == 1
    assert run["run_manifest"]["successful_result_count"] == 1
    assert run["run_manifest"]["failed_result_count"] == 0
    assert run["run_manifest"]["run_identity_fingerprint"] == (
        run["run_identity"]["identity_fingerprint"]
    )
    assert run["run_manifest"]["ordered_case_ids_fingerprint"] == (
        run["run_identity"]["always_controls"]["ordered_case_ids_fingerprint"]
    )
    assert run["run_identity"]["always_controls"]["dataset_path"] == (
        "tenants/demo/datasets/cases.jsonl"
    )
    assert run["cases"][0]["case_id"] == "case-1"


def test_manifest_valid_bundle_for_another_tenant_is_omitted(tmp_path: Path) -> None:
    """A valid manifest cannot authorize a bundle transplanted across tenants."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    _publish_authenticated_run(tenant, run_config_tenant_id="other-tenant")
    store = TenantStore(tenants, repository_base=tmp_path)

    snapshot, studio_data = store.prepare_case(
        "demo",
        "evals/authenticated-run",
        0,
    )

    assert store.list_runs("demo") == []
    assert store.get_run("demo", "evals/authenticated-run") is None
    assert store.list_tenants()[0]["run_count"] == 0
    assert snapshot is None
    assert studio_data is False


def test_symlinked_tenant_alias_is_not_a_tenant_identity(tmp_path: Path) -> None:
    """A lexical tenant name cannot alias another tenant directory."""
    tenants = tmp_path / "tenants"
    real = tenants / "real"
    real.mkdir(parents=True)
    (real / "__init__.py").write_text("", encoding="utf-8")
    _publish_authenticated_run(real)
    (tenants / "alias").symlink_to(real, target_is_directory=True)
    store = TenantStore(tenants, repository_base=tmp_path)

    assert "alias" not in {item["tenant_id"] for item in store.list_tenants()}
    assert store.list_runs("alias") == []
    assert store.get_run("alias", "evals/authenticated-run") is None


def test_symlinked_eval_parent_cannot_import_another_tenants_runs(
    tmp_path: Path,
) -> None:
    """Run discovery and direct reads reject a foreign eval parent alias."""
    tenants = tmp_path / "tenants"
    requested = tenants / "requested"
    foreign = tenants / "foreign"
    for tenant in (requested, foreign):
        tenant.mkdir(parents=True)
        (tenant / "__init__.py").write_text("", encoding="utf-8")
    _publish_authenticated_run(
        foreign,
        run_config_tenant_id="requested",
    )
    (requested / "evals").symlink_to(
        foreign / "evals",
        target_is_directory=True,
    )
    store = TenantStore(tenants, repository_base=tmp_path)

    assert store.list_runs("requested") == []
    assert store.get_run("requested", "evals/authenticated-run") is None


@pytest.mark.parametrize("alias_kind", ("ancestor", "run"))
def test_symlinked_run_path_components_are_rejected(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    """Neither an intermediate directory nor the run directory may be an alias."""
    tenants = tmp_path / "tenants"
    requested = tenants / "requested"
    foreign = tenants / "foreign"
    for tenant in (requested, foreign):
        tenant.mkdir(parents=True)
        (tenant / "__init__.py").write_text("", encoding="utf-8")
    foreign_run, _ = _publish_authenticated_run(
        foreign,
        run_config_tenant_id="requested",
    )
    evals = requested / "evals"
    evals.mkdir()
    if alias_kind == "ancestor":
        (evals / "linked-parent").symlink_to(
            foreign_run.parent,
            target_is_directory=True,
        )
        run_rel = "evals/linked-parent/authenticated-run"
    else:
        (evals / "linked-run").symlink_to(
            foreign_run,
            target_is_directory=True,
        )
        run_rel = "evals/linked-run"
    store = TenantStore(tenants, repository_base=tmp_path)

    assert store.list_runs("requested") == []
    assert store.get_run("requested", run_rel) is None


@pytest.mark.parametrize(
    ("artifact", "outside_content", "missing_field"),
    [
        ("results.jsonl", '{"case_id":"outside-canary"}\n', "cases"),
        ("run_config.json", '{"secret":"outside-canary"}\n', "run_config"),
        ("progress.json", '{"secret":"outside-canary"}\n', "progress"),
        ("summary.md", "outside-canary\n", "summary_md"),
    ],
)
def test_loose_run_readers_never_follow_artifact_symlinks(
    tmp_path: Path,
    artifact: str,
    outside_content: str,
    missing_field: str,
) -> None:
    """Every legacy artifact reader fails closed on an out-of-tenant alias."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    run_dir = _write_loose_run(
        tenant,
        run_name="legacy",
        status="completed",
        dataset_path="tenants/demo/datasets/cases.jsonl",
        case_id="safe-case",
    )
    outside = tmp_path / f"outside-{artifact}"
    outside.write_text(outside_content, encoding="utf-8")
    target = run_dir / artifact
    target.unlink(missing_ok=True)
    target.symlink_to(outside)
    store = TenantStore(tenants, repository_base=tmp_path)

    run = store.get_run("demo", "evals/legacy")

    assert run is not None
    assert "outside-canary" not in json.dumps(run)
    if missing_field == "cases":
        assert run[missing_field] == []
        assert store.get_case("demo", "evals/legacy", 0) is None
    else:
        assert run[missing_field] is None


def test_tenant_readable_subtrees_cannot_alias_a_sibling_tenant(
    tmp_path: Path,
) -> None:
    """Dataset, prompt, config, and docs roots retain lexical tenant ownership."""
    tenants = tmp_path / "tenants"
    requested = tenants / "requested"
    foreign = tenants / "foreign"
    for tenant in (requested, foreign):
        tenant.mkdir(parents=True)
        (tenant / "__init__.py").write_text("", encoding="utf-8")
    (foreign / "datasets").mkdir()
    (foreign / "datasets" / "secret.jsonl").write_text(
        '{"case_id":"outside-canary"}\n',
        encoding="utf-8",
    )
    (foreign / "prompts").mkdir()
    (foreign / "prompts" / "secret.md").write_text(
        "outside-canary\n",
        encoding="utf-8",
    )
    (foreign / "configs").mkdir()
    (foreign / "configs" / "secret.json").write_text(
        '{"secret":"outside-canary"}\n',
        encoding="utf-8",
    )
    (foreign / "docs").mkdir()
    (foreign / "docs" / "secret.md").write_text(
        "outside-canary\n",
        encoding="utf-8",
    )
    (foreign / "docs" / "iteration-memory.jsonl").write_text(
        '{"variants_tried":99,"secret":"outside-canary"}\n',
        encoding="utf-8",
    )
    for dirname in ("datasets", "prompts", "configs", "docs"):
        (requested / dirname).symlink_to(
            foreign / dirname,
            target_is_directory=True,
        )
    store = TenantStore(tenants, repository_base=tmp_path)

    assert store.list_datasets("requested") == []
    assert store.get_dataset("requested", "datasets/secret.jsonl") is None
    assert store.list_prompts("requested") == []
    assert store.get_prompt("requested", "prompts/secret.md") is None
    assert store.list_configs("requested") == []
    assert store.get_config("requested", "configs/secret.json") is None
    assert store.list_docs("requested") == []
    assert store.get_doc("requested", "docs/secret.md") is None
    assert store.list_iterations("requested") == []
    assert store.overview(["requested"])["totals"]["variants"] == 0


def test_tenant_readers_reject_final_file_symlinks(tmp_path: Path) -> None:
    """Exact tenant subtrees still cannot expose an aliased leaf file."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    fixtures = {
        "datasets/secret.jsonl": '{"case_id":"outside-canary"}\n',
        "prompts/secret.md": "outside-canary\n",
        "configs/secret.json": '{"secret":"outside-canary"}\n',
        "docs/secret.md": "outside-canary\n",
        "docs/iteration-memory.jsonl": (
            '{"variants_tried":99,"secret":"outside-canary"}\n'
        ),
    }
    for relative, content in fixtures.items():
        source = outside / Path(relative).name
        source.write_text(content, encoding="utf-8")
        target = tenant / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
    store = TenantStore(tenants, repository_base=tmp_path)

    assert store.list_datasets("demo") == []
    assert store.get_dataset("demo", "datasets/secret.jsonl") is None
    assert store.list_prompts("demo") == []
    assert store.get_prompt("demo", "prompts/secret.md") is None
    assert store.list_configs("demo") == []
    assert store.get_config("demo", "configs/secret.json") is None
    assert store.list_docs("demo") == []
    assert store.get_doc("demo", "docs/secret.md") is None
    assert store.list_iterations("demo") == []


def test_authenticated_case_rejects_symlinked_datasets_root(tmp_path: Path) -> None:
    """An authenticated run cannot join rows through a sibling datasets alias."""
    tenants = tmp_path / "tenants"
    requested = tenants / "requested"
    foreign = tenants / "foreign"
    for tenant in (requested, foreign):
        tenant.mkdir(parents=True)
        (tenant / "__init__.py").write_text("", encoding="utf-8")
    (foreign / "datasets").mkdir()
    (requested / "datasets").symlink_to(
        foreign / "datasets",
        target_is_directory=True,
    )
    _publish_authenticated_run(requested)
    store = TenantStore(tenants, repository_base=tmp_path)

    case = store.get_case("requested", "evals/authenticated-run", 0)

    assert case is not None
    assert case["case"]["case_id"] == "case-1"
    assert case["ground_truth"] is None


def test_unmanifested_terminal_and_live_runs_remain_visibly_unverified(
    tmp_path: Path,
) -> None:
    """Loose legacy output and active progress cannot be presented as verified."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    for run_name, status in (("old-run", "completed"), ("live-run", "running")):
        _write_json(
            tenant / "evals" / run_name / "progress.json",
            {"run_id": run_name, "status": status},
        )

    runs = TenantStore(tenants, repository_base=tmp_path).list_runs("demo")

    states = {run["name"]: run["authority"] for run in runs}
    assert states == {
        "old-run": "legacy_unverified",
        "live-run": "live_unverified",
    }


def test_overview_headlines_use_latest_authoritative_completed_run(
    tmp_path: Path,
) -> None:
    """A newer loose score cannot become dashboard headline evidence."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    _publish_authenticated_run(
        tenant,
        run_name="verified-run",
        progress_overrides={
            "avg_composite_score": 42.0,
            "updated_at": "2026-08-20T00:00:00+00:00",
        },
    )
    loose = _write_loose_run(
        tenant,
        run_name="forged-newer-run",
        status="completed",
        dataset_path="datasets/cases.jsonl",
        case_id="case-1",
    )
    _write_json(
        loose / "progress.json",
        {
            "run_id": "forged-newer-run",
            "status": "completed",
            "avg_composite_score": 99.0,
            "updated_at": "2026-08-21T00:00:00+00:00",
        },
    )

    overview = TenantStore(tenants, repository_base=tmp_path).overview()

    assert overview["totals"]["avg_latest_score"] == 42.0
    assert overview["tenants"][0]["latest_run"]["name"] == "verified-run"
    assert overview["tenants"][0]["latest_run"]["authority"] == "authoritative"
    assert overview["recent_runs"][0]["name"] == "forged-newer-run"
    assert overview["recent_runs"][0]["authority"] == "legacy_unverified"


def test_explorer_marks_authority_and_hides_unverified_scores() -> None:
    """Every run surface labels authority and gates displayed score evidence."""
    assert "function authorityLabel(authority)" in INDEX_HTML
    assert "function authoritativeCompletedScore(run)" in INDEX_HTML
    assert "authoritativeCompletedScore(r) != null" in INDEX_HTML
    assert "<th>Authority</th>" in INDEX_HTML
    assert "<b>Run authority:</b>" in INDEX_HTML
    assert "Unverified artifacts are diagnostic only" in INDEX_HTML


def test_tampered_manifest_run_is_not_authoritative(tmp_path: Path) -> None:
    """A manifest file alone cannot turn a terminal run into trusted UI data."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    run_dir, _ = _publish_authenticated_run(tenant)
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    manifest["status"] = "failed"
    _write_json(run_dir / "run_manifest.json", manifest)

    listed = TenantStore(tenants, repository_base=tmp_path).list_runs("demo")

    assert listed[0]["authority"] == "invalid_unverified"


def test_manifest_only_corrupt_run_remains_visibly_invalid(tmp_path: Path) -> None:
    """A corrupt authority marker remains discoverable without loose artifacts."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    _write_json(
        tenant / "evals" / "manifest-only" / "run_manifest.json",
        {"schema_version": "corrupt"},
    )

    listed = TenantStore(tenants, repository_base=tmp_path).list_runs("demo")

    assert [(run["name"], run["authority"]) for run in listed] == [
        ("manifest-only", "invalid_unverified")
    ]


def test_case_payload_exposes_manifest_authority(tmp_path: Path) -> None:
    """Case consumers can distinguish authenticated and corrupt loose results."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    run_dir, _ = _publish_authenticated_run(tenant)
    store = TenantStore(tenants, repository_base=tmp_path)

    authenticated = store.get_case("demo", "evals/authenticated-run", 0)
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    manifest["status"] = "failed"
    _write_json(run_dir / "run_manifest.json", manifest)
    corrupt = store.get_case("demo", "evals/authenticated-run", 0)

    assert authenticated is not None
    assert authenticated["authority"] == "authoritative"
    assert corrupt is not None
    assert corrupt["authority"] == "invalid_unverified"


@pytest.mark.parametrize(
    "status",
    ("completed", "running"),
)
def test_unverified_run_never_joins_protected_studio_ground_truth(
    tmp_path: Path,
    status: str,
) -> None:
    """A release manifest cannot replace an authenticated run-to-dataset binding."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    generation = _publish_generation(
        tenant,
        asset_id="asset",
        suffix="protected",
        fingerprint="7" * 64,
        split_rows={
            "train": {
                "case_id": "protected-train",
                "context": {"secret": "protected-context"},
                "expected": {"secret": "protected-expected"},
                "metadata": {"secret": "protected-metadata"},
            }
        },
    )
    dataset_path = generation.files["train"].relative_to(tmp_path).as_posix()
    _write_loose_run(
        tenant,
        run_name=status,
        status=status,
        dataset_path=dataset_path,
        case_id="protected-train",
    )
    store = TenantStore(tenants, repository_base=tmp_path)

    snapshot, studio_data = store.prepare_case("demo", f"evals/{status}", 0)
    case = store.materialize_case(snapshot)

    assert studio_data is True
    assert case is not None
    assert case["case"]["case_id"] == "protected-train"
    assert case["ground_truth"] is None


def test_legacy_run_still_joins_ordinary_dataset_ground_truth(tmp_path: Path) -> None:
    """The authenticated-join requirement does not break ordinary legacy data."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    dataset = tenant / "datasets" / "ordinary.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(
        json.dumps(
            {
                "case_id": "ordinary-case",
                "context": {"question": "ordinary-question"},
                "expected": {"answer": "ordinary-answer"},
                "metadata": {"source": "ordinary"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_loose_run(
        tenant,
        run_name="legacy",
        status="completed",
        dataset_path=dataset.relative_to(tmp_path).as_posix(),
        case_id="ordinary-case",
    )

    case = TenantStore(tenants, repository_base=tmp_path).get_case(
        "demo",
        "evals/legacy",
        0,
    )

    assert case is not None
    assert case["ground_truth"] == {
        "dataset": "datasets/ordinary.jsonl",
        "expected": {"answer": "ordinary-answer"},
        "context": {"question": "ordinary-question"},
        "metadata": {"source": "ordinary"},
    }


def test_authenticated_case_join_requires_unchanged_dataset_bytes(tmp_path: Path) -> None:
    """Changed dataset bytes cannot disclose context or expected data through a run."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    _, dataset_path = _publish_authenticated_run(tenant)
    store = TenantStore(tenants, repository_base=tmp_path)

    valid_case = store.get_case("demo", "evals/authenticated-run", 0)
    dataset_path.write_bytes(
        _dataset_bytes(
            [
                {
                    "case_id": "case-1",
                    "task_type": "demo",
                    "context": {"question": "changed-protected-question"},
                    "expected": {"answer": "changed-protected-answer"},
                    "metadata": {},
                }
            ]
        )
    )
    changed_case = store.get_case("demo", "evals/authenticated-run", 0)

    assert valid_case is not None
    assert valid_case["ground_truth"]["context"] == {"question": "protected-question"}
    assert changed_case is not None
    assert changed_case["case"]["case_id"] == "case-1"
    assert changed_case["ground_truth"] is None


def test_authenticated_case_join_requires_dataset_order_to_match_identity(
    tmp_path: Path,
) -> None:
    """Matching rows cannot be joined if their order differs from the run identity."""
    tenants = tmp_path / "tenants"
    tenant = tenants / "demo"
    tenant.mkdir(parents=True)
    (tenant / "__init__.py").write_text("", encoding="utf-8")
    _publish_authenticated_run(
        tenant,
        dataset_rows=[
            {
                "case_id": "case-2",
                "task_type": "demo",
                "context": {"question": "two"},
                "expected": {"answer": "two"},
                "metadata": {},
            },
            {
                "case_id": "case-1",
                "task_type": "demo",
                "context": {"question": "one"},
                "expected": {"answer": "one"},
                "metadata": {},
            },
        ],
        identity_case_ids=["case-1", "case-2"],
    )

    case = TenantStore(tenants, repository_base=tmp_path).get_case(
        "demo",
        "evals/authenticated-run",
        0,
    )

    assert case is not None
    assert case["ground_truth"] is None


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
    assert listed[0]["evaluation_asset"]["review_authority_revision"] is None


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
    assert detail["clusters"][0]["representative_ids"] == ["r1"]
    assert "request alpha" not in json.dumps(detail)
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


def test_evaluation_asset_stage_disables_protected_content_previews(
    tmp_path: Path,
) -> None:
    tenant = tmp_path / "bootstrap_tenant"
    asset = tenant / "evaluation_assets" / "v1"
    _write_json(
        asset / "config.json",
        {"tenant_id": "bootstrap_tenant", "asset_id": "v1"},
    )
    _write_json(
        asset / "pipeline_state.json",
        {
            "tenant_id": "bootstrap_tenant",
            "asset_id": "v1",
            "status": "awaiting_review",
            "stages": [],
        },
    )
    protected_rows = {
        "stages/01_raw_inputs/labeled_feedback.jsonl": "RAW-FEEDBACK-CANARY",
        "stages/01_raw_inputs/unlabeled.jsonl": "RAW-UNLABELED-CANARY",
        "stages/02_prepared_inputs/normalized_feedback.jsonl": (
            "NORMALIZED-FEEDBACK-CANARY"
        ),
        "stages/02_prepared_inputs/intent_records.jsonl": "INTENT-SOURCE-CANARY",
        "stages/03_evaluation_guidelines/protected_feedback_evidence.jsonl": (
            "PROTECTED-EVIDENCE-CANARY"
        ),
        "stages/03_evaluation_guidelines/protected_candidate_guidelines.jsonl": (
            "PROTECTED-CANDIDATE-CANARY"
        ),
        "stages/03_evaluation_guidelines/protected_evaluation_guidelines.jsonl": (
            "PROTECTED-GUIDELINE-CANARY"
        ),
        "stages/03_evaluation_guidelines/protected_trusted_cases.jsonl": (
            "PROTECTED-CASE-CANARY"
        ),
        "stages/06_label_inference/inferred_unlabeled_cluster_rubrics.jsonl": (
            "INFERRED-RUBRIC-CANARY"
        ),
        "stages/06_label_inference/inferred_unlabeled_labels.jsonl": (
            "INFERRED-LABEL-CANARY"
        ),
        "stages/06_label_inference/inferred_cases.jsonl": "INFERRED-CASE-CANARY",
        "stages/06_label_inference/inference_dependencies.jsonl": (
            "INFERENCE-DEPENDENCY-CANARY"
        ),
        "stages/06_label_inference/held_inference_outputs.jsonl": (
            "HELD-INFERENCE-CANARY"
        ),
        "stages/07_synthetic_coverage/synthetic_candidates.jsonl": (
            "SYNTHETIC-CANDIDATE-CANARY"
        ),
        "stages/07_synthetic_coverage/synthetic_cases.jsonl": (
            "SYNTHETIC-CASE-CANARY"
        ),
        "stages/07_synthetic_coverage/rejected_synthetic.jsonl": (
            "REJECTED-SYNTHETIC-CANARY"
        ),
        "stages/07_synthetic_coverage/synthetic_dependencies.jsonl": (
            "SYNTHETIC-DEPENDENCY-CANARY"
        ),
        "stages/08_dataset_splits/validation.jsonl": "VALIDATION-CANARY",
        "stages/08_dataset_splits/test.jsonl": "TEST-CANARY",
        "stages/08_dataset_splits/regression_trusted.jsonl": (
            "REGRESSION-CANARY"
        ),
        "stages/08_dataset_splits/validation_inferred.jsonl": (
            "VALIDATION-INFERRED-CANARY"
        ),
        "stages/08_dataset_splits/test_synthetic.jsonl": (
            "TEST-SYNTHETIC-CANARY"
        ),
        "stages/08_dataset_splits/triage_hold.jsonl": "TRIAGE-HOLD-CANARY",
    }
    for relative_path, canary in protected_rows.items():
        path = asset / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "record_id": "record-1",
                    "user_input": canary,
                    "assistant_output": canary,
                    "feedback": {"rationale": canary, "correction": canary},
                    "criteria": [canary],
                    "provider_payload": canary,
                }
            )
            + "\n",
            encoding="utf-8",
        )

    store = TenantStore(tmp_path, repository_base=tmp_path.parent)
    details = [
        store.get_evaluation_asset_stage("bootstrap_tenant", "v1", stage)
        for stage in (
            "raw_inputs",
            "prepared_inputs",
            "rubric_extraction",
            "label_inference",
            "synthetic_coverage",
            "dataset_splits",
        )
    ]

    assert all(detail is not None for detail in details)
    artifacts = [
        artifact
        for detail in details
        if detail is not None
        for artifact in detail["artifacts"]
    ]
    assert {artifact["name"] for artifact in artifacts} == {
        Path(relative_path).name for relative_path in protected_rows
    }
    for artifact in artifacts:
        assert artifact["preview_policy"] == "disabled"
        assert artifact["preview"] == []
        assert "content" not in artifact
        assert artifact["row_count"] == 1
    serialized = json.dumps(details)
    for canary in protected_rows.values():
        assert canary not in serialized


def test_evaluation_asset_stage_projects_split_and_review_metadata_only(
    tmp_path: Path,
) -> None:
    tenant = tmp_path / "bootstrap_tenant"
    asset = tenant / "evaluation_assets" / "v1"
    _write_json(
        asset / "config.json",
        {"tenant_id": "bootstrap_tenant", "asset_id": "v1"},
    )
    _write_json(
        asset / "pipeline_state.json",
        {
            "tenant_id": "bootstrap_tenant",
            "asset_id": "v1",
            "status": "awaiting_review",
            "stages": [],
        },
    )
    metadata_files = {
        "stages/02_prepared_inputs/trusted_split_plan.jsonl": {
            "schema_version": "fapo-trusted-split-assignment-v1",
            "record_id": "record-1",
            "group_id": "group-1",
            "split_group_id": "split-group-1",
            "context_fingerprint": "sha256:" + "1" * 64,
            "split": "validation",
            "assignment_source": "seeded",
            "evidence_eligible": False,
            "hold_reason": "insufficient_correctness_evidence",
        },
        "stages/02_prepared_inputs/feedback_eligibility.jsonl": {
            "record_id": "record-1",
            "split": "validation",
            "evidence_eligible": False,
            "hold_reason": "insufficient_correctness_evidence",
        },
        "stages/07_synthetic_coverage/derived_review_items.jsonl": {
            "review_item_id": "review-1",
            "case_id": "case-1",
            "fingerprint": "sha256:" + "2" * 64,
            "status": "pending",
        },
        "stages/07_synthetic_coverage/duplicate_families.jsonl": {
            "family_id": "family-1",
            "member_case_ids": ["case-1", "case-2"],
            "status": "held",
            "hold_reason": "conflicting_expected_truth",
        },
        "stages/07_synthetic_coverage/held_derived_cases.jsonl": {
            "case_id": "case-3",
            "fingerprint": "sha256:" + "3" * 64,
            "status": "held",
            "hold_reason": "empty_rubric",
        },
        "reviews/decisions.jsonl": {
            "decision_id": "decision-1",
            "fingerprint": "sha256:" + "2" * 64,
            "decision": "approved",
            "reviewer": "REVIEWER-METADATA-CANARY",
            "timestamp": "TIMESTAMP-METADATA-CANARY",
        },
        "reviews/finalizations.jsonl": {
            "finalization_id": "finalization-1",
            "review_set_fingerprint": "sha256:" + "4" * 64,
            "status": "finalized",
            "reviewer": "FINALIZER-METADATA-CANARY",
            "timestamp": "FINALIZATION-TIME-CANARY",
        },
    }
    canaries: list[str] = []
    for index, (relative_path, safe_metadata) in enumerate(metadata_files.items()):
        canary = f"METADATA-BODY-CANARY-{index}"
        canaries.append(canary)
        path = asset / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    **safe_metadata,
                    "user_input": canary,
                    "assistant_output": canary,
                    "rationale": canary,
                    "correction": canary,
                    "criteria": [canary],
                    "provider_payload": {"body": canary},
                    "case": {"input": canary, "expected": canary},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    _write_json(
        asset / "stages/08_dataset_splits/review_snapshot.json",
        {
            "finalization_id": "finalization-1",
            "review_set_fingerprint": "sha256:" + "4" * 64,
            "approved_fingerprints": ["sha256:" + "2" * 64],
            "provider_payload": {"body": "REVIEW-SNAPSHOT-CANARY"},
        },
    )
    canaries.append("REVIEW-SNAPSHOT-CANARY")
    canaries.extend(
        (
            "REVIEWER-METADATA-CANARY",
            "TIMESTAMP-METADATA-CANARY",
            "FINALIZER-METADATA-CANARY",
            "FINALIZATION-TIME-CANARY",
        )
    )

    store = TenantStore(tmp_path, repository_base=tmp_path.parent)
    details = [
        store.get_evaluation_asset_stage("bootstrap_tenant", "v1", stage)
        for stage in ("prepared_inputs", "synthetic_coverage", "dataset_splits")
    ]

    assert all(detail is not None for detail in details)
    artifacts = {
        artifact["name"]: artifact
        for detail in details
        if detail is not None
        for artifact in detail["artifacts"]
    }
    assert set(metadata_files).issubset(
        artifact["path"].split("evaluation_assets/v1/", 1)[-1]
        for artifact in artifacts.values()
    )
    for name in (
        "trusted_split_plan.jsonl",
        "feedback_eligibility.jsonl",
        "derived_review_items.jsonl",
        "duplicate_families.jsonl",
        "held_derived_cases.jsonl",
        "decisions.jsonl",
        "finalizations.jsonl",
        "review_snapshot.json",
    ):
        assert artifacts[name]["preview_policy"] == "metadata_only"
        assert artifacts[name]["preview"]
    serialized = json.dumps(details)
    for canary in canaries:
        assert canary not in serialized
    assert "record-1" in serialized
    assert "review-1" in serialized
    assert "decision-1" in serialized
    assert "finalization-1" in serialized
