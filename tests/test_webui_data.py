# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the FAFO web UI filesystem store."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.hephaestus.runs.bundle import RunBundleWriter
from src.hephaestus.runs.identity import build_run_identity
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
    dataset_rel: str = "datasets/cases.jsonl",
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
    dataset_path = tenant / dataset_rel
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    content = _dataset_bytes(rows)
    dataset_path.write_bytes(content)
    dataset_literal = f"tenants/{tenant.name}/{dataset_rel}"
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


def _write_asset(
    tenant: Path,
    asset_id: str,
    splits: dict[str, list[dict[str, object]]],
) -> Path:
    """Write a built evaluation asset with dataset splits and non-dataset files."""
    asset = tenant / "evaluation_assets" / asset_id
    for split, rows in splits.items():
        path = asset / "datasets" / f"{split}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_dataset_bytes(rows))
    for relative in (
        "inputs/feedback.jsonl",
        "cache/rubric.jsonl",
        "lessons.jsonl",
        "rubrics.jsonl",
        "splits.jsonl",
    ):
        path = asset / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"case_id":"not-a-dataset"}\n', encoding="utf-8")
    _write_json(asset / "catalog.json", {"guidelines": []})
    _write_json(asset / "manifest.json", {"asset_id": asset_id})
    (asset / "review.md").write_text("# Review\n", encoding="utf-8")
    return asset


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
    assert run["run_manifest"]["schema_version"] == "fafo-run-bundle-manifest-v1"
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

    assert store.list_runs("demo") == []
    assert store.get_run("demo", "evals/authenticated-run") is None
    assert store.list_tenants()[0]["run_count"] == 0
    assert store.get_case("demo", "evals/authenticated-run", 0) is None


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
    """A directory holding only built evaluation assets is listed as a tenant."""
    _write_asset(tmp_path / "bootstrap_tenant", "v1", {"train": [{"case_id": "case-1"}]})

    listed = TenantStore(tmp_path, repository_base=tmp_path.parent).list_tenants()

    assert [row["tenant_id"] for row in listed] == ["bootstrap_tenant"]
    assert listed[0]["dataset_count"] == 1
    assert "evaluation_asset_count" not in listed[0]


class TestEvaluationAssetDatasets:
    """Datasets built by ``assets build`` under ``evaluation_assets/<asset_id>/``."""

    @staticmethod
    def _tenant(tmp_path: Path) -> Path:
        tenant = tmp_path / "tenants" / "demo"
        tenant.mkdir(parents=True)
        (tenant / "__init__.py").write_text("", encoding="utf-8")
        return tenant

    def test_lists_split_files_and_hides_other_asset_files(self, tmp_path: Path) -> None:
        """Only an asset's ``datasets/*.jsonl`` files join the dataset listing."""
        tenant = self._tenant(tmp_path)
        (tenant / "datasets").mkdir()
        (tenant / "datasets" / "ordinary.jsonl").write_text('{"case_id":"ordinary"}\n', encoding="utf-8")
        _write_asset(
            tenant,
            "v1",
            {
                "train": [{"case_id": "t1"}, {"case_id": "t2"}],
                "train_trusted": [{"case_id": "t1"}],
            },
        )
        store = TenantStore(tmp_path / "tenants", repository_base=tmp_path)

        listed = store.list_datasets("demo")

        assert [(row["path"], row["row_count"]) for row in listed] == [
            ("datasets/ordinary.jsonl", 1),
            ("evaluation_assets/v1/datasets/train.jsonl", 2),
            ("evaluation_assets/v1/datasets/train_trusted.jsonl", 1),
        ]
        assert store.list_tenants()[0]["dataset_count"] == 3

    def test_reads_split_files_but_no_other_asset_file(self, tmp_path: Path) -> None:
        """The dataset reader pages asset splits and rejects every other asset path."""
        tenant = self._tenant(tmp_path)
        _write_asset(tenant, "v1", {"validation": [{"case_id": "v-1"}, {"case_id": "v-2"}]})
        store = TenantStore(tmp_path / "tenants", repository_base=tmp_path)

        page = store.get_dataset(
            "demo",
            "evaluation_assets/v1/datasets/validation.jsonl",
            offset=1,
            limit=5,
        )

        assert page == {
            "path": "evaluation_assets/v1/datasets/validation.jsonl",
            "total": 2,
            "offset": 1,
            "limit": 5,
            "rows": [{"case_id": "v-2"}],
        }
        for rel in (
            "evaluation_assets/v1/inputs/feedback.jsonl",
            "evaluation_assets/v1/cache/rubric.jsonl",
            "evaluation_assets/v1/lessons.jsonl",
            "evaluation_assets/v1/catalog.json",
            "evaluation_assets/v1/datasets",
            "evaluation_assets/v1/datasets/../inputs/feedback.jsonl",
            "evaluation_assets/datasets/validation.jsonl",
        ):
            assert store.get_dataset("demo", rel) is None

    def test_rejects_aliased_asset_directories(self, tmp_path: Path) -> None:
        """Symlinked asset and asset-dataset directories are neither listed nor read."""
        tenant = self._tenant(tmp_path)
        asset = _write_asset(tenant, "v1", {"train": [{"case_id": "t1"}]})
        (tenant / "evaluation_assets" / "alias").symlink_to(asset, target_is_directory=True)
        linked = tenant / "evaluation_assets" / "linked"
        linked.mkdir()
        (linked / "datasets").symlink_to(asset / "inputs", target_is_directory=True)
        store = TenantStore(tmp_path / "tenants", repository_base=tmp_path)

        assert [row["path"] for row in store.list_datasets("demo")] == [
            "evaluation_assets/v1/datasets/train.jsonl"
        ]
        assert store.get_dataset("demo", "evaluation_assets/alias/datasets/train.jsonl") is None
        assert store.get_dataset("demo", "evaluation_assets/linked/datasets/feedback.jsonl") is None

    def test_authenticated_run_joins_asset_split(self, tmp_path: Path) -> None:
        """A bundle recorded against an asset split joins that split's ground truth."""
        tenant = self._tenant(tmp_path)
        _publish_authenticated_run(tenant, dataset_rel="evaluation_assets/v1/datasets/train.jsonl")
        store = TenantStore(tmp_path / "tenants", repository_base=tmp_path)

        case = store.get_case("demo", "evals/authenticated-run", 0)

        assert case is not None
        assert case["authority"] == "authoritative"
        assert case["ground_truth"] == {
            "dataset": "evaluation_assets/v1/datasets/train.jsonl",
            "expected": {"answer": "protected-answer"},
            "context": {"question": "protected-question"},
            "metadata": {"source": "protected"},
        }

    def test_authenticated_run_cannot_join_non_dataset_asset_file(self, tmp_path: Path) -> None:
        """A bundle recorded against an asset input file gets no ground truth."""
        tenant = self._tenant(tmp_path)
        _publish_authenticated_run(tenant, dataset_rel="evaluation_assets/v1/inputs/feedback.jsonl")
        store = TenantStore(tmp_path / "tenants", repository_base=tmp_path)

        case = store.get_case("demo", "evals/authenticated-run", 0)

        assert case is not None
        assert case["case"]["case_id"] == "case-1"
        assert case["ground_truth"] is None

    def test_legacy_run_joins_asset_split(self, tmp_path: Path) -> None:
        """A loose run whose config names an asset split joins it best-effort."""
        tenant = self._tenant(tmp_path)
        _write_asset(
            tenant,
            "v1",
            {
                "train": [{"case_id": "train-case"}],
                "test": [{"case_id": "test-case", "expected": {"answer": "test-answer"}}],
            },
        )
        _write_loose_run(
            tenant,
            run_name="legacy",
            status="completed",
            dataset_path="tenants/demo/evaluation_assets/v1/datasets/test.jsonl",
            case_id="test-case",
        )

        case = TenantStore(tmp_path / "tenants", repository_base=tmp_path).get_case(
            "demo",
            "evals/legacy",
            0,
        )

        assert case is not None
        assert case["ground_truth"] == {
            "dataset": "evaluation_assets/v1/datasets/test.jsonl",
            "expected": {"answer": "test-answer"},
            "context": None,
            "metadata": None,
        }
