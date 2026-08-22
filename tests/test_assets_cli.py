# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.hephaestus.cli import build_parser, main


def test_assets_help_exposes_only_canonical_pipeline_commands() -> None:
    """Legacy assembly commands are absent from public parser help and choices."""
    parser = build_parser()
    command_action = next(
        action for action in parser._actions if action.dest == "command"
    )
    assets_parser = command_action.choices["assets"]
    help_text = assets_parser.format_help()

    assert "intent-inventory" not in help_text
    assert "assemble" not in help_text
    for command in ("create", "run", "extend", "adopt", "status", "reviews"):
        assert command in help_text
    with pytest.raises(SystemExit):
        parser.parse_args(["assets", "intent-inventory"])
    with pytest.raises(SystemExit):
        parser.parse_args(["assets", "assemble"])


def test_assets_reviews_parser_requires_exact_review_authority() -> None:
    """Decision and finalization commands cannot omit their stale-set guards."""
    parser = build_parser()

    list_args = parser.parse_args(
        [
            "assets",
            "reviews",
            "list",
            "--tenant",
            "tenant_a",
            "--asset-id",
            "v1",
            "--status",
            "pending",
            "--offset",
            "10",
            "--limit",
            "20",
        ]
    )
    assert list_args.reviews_command == "list"
    assert list_args.status == "pending"
    assert list_args.offset == 10
    assert list_args.limit == 20

    held_args = parser.parse_args(
        ["assets", "reviews", "list", "--tenant", "tenant_a", "--status", "held"]
    )
    assert held_args.status == "held"

    approve_args = parser.parse_args(
        [
            "assets",
            "reviews",
            "approve",
            "--tenant",
            "tenant_a",
            "--case-id",
            "inferred-u1",
            "--fingerprint",
            "sha256:" + "a" * 64,
            "--reviewer",
            "reviewer@example.com",
            "--review-set",
            "sha256:" + "b" * 64,
        ]
    )
    assert approve_args.reviews_command == "approve"
    assert approve_args.case_id == "inferred-u1"
    assert approve_args.expected_review_set_fingerprint == "sha256:" + "b" * 64

    for command in ("approve", "reject"):
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "assets",
                    "reviews",
                    command,
                    "--tenant",
                    "tenant_a",
                    "--fingerprint",
                    "sha256:" + "a" * 64,
                    "--reviewer",
                    "reviewer@example.com",
                    "--review-set",
                    "sha256:" + "b" * 64,
                ]
            )

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "assets",
                "reviews",
                "finalize",
                "--tenant",
                "tenant_a",
                "--reviewer",
                "reviewer@example.com",
                "--review-set",
                "sha256:" + "b" * 64,
            ]
        )

    for option, value in (
        ("--case-id", " "),
        ("--fingerprint", "sha256:not-canonical"),
        ("--reviewer", " "),
        ("--review-set", "sha256:not-canonical"),
    ):
        arguments = [
            "assets",
            "reviews",
            "approve",
            "--tenant",
            "tenant_a",
            "--case-id",
            "inferred-u1",
            "--fingerprint",
            "sha256:" + "a" * 64,
            "--reviewer",
            "reviewer@example.com",
            "--review-set",
            "sha256:" + "b" * 64,
        ]
        arguments[arguments.index(option) + 1] = value
        with pytest.raises(SystemExit):
            parser.parse_args(arguments)

    for option, value in (("--offset", "-1"), ("--limit", "0"), ("--limit", "101")):
        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "assets",
                    "reviews",
                    "list",
                    "--tenant",
                    "tenant_a",
                    option,
                    value,
                ]
            )


def test_assets_reviews_cli_lists_one_bounded_safe_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Catch a list command that drops pagination or prints protected case content."""
    from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

    received = []

    def list_review_items(
        layout: EvaluationAssetLayout,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> dict:
        received.append((layout.tenant_id, layout.asset_id, status, offset, limit))
        return {
            "items": [
                {
                    "case_id": "inferred-u1",
                    "fingerprint": "sha256:" + "a" * 64,
                    "trust_tier": "inferred_from_trusted_feedback",
                    "status": "pending",
                    "case": {"context": {"private": "must-not-leak"}},
                }
            ],
            "held": [],
            "counts": {"pending": 1, "approved": 0, "rejected": 0, "held": 0},
            "review_set_fingerprint": "sha256:" + "b" * 64,
            "stage7_receipt_sha256": "sha256:" + "c" * 64,
            "offset": offset,
            "limit": limit,
            "total": 1,
        }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        EvaluationAssetLayout,
        "list_review_items",
        list_review_items,
        raising=False,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "reviews",
            "list",
            "--tenant",
            "tenant_a",
            "--asset-id",
            "v1",
            "--tenants-root",
            "tenants",
            "--status",
            "pending",
            "--offset",
            "3",
            "--limit",
            "8",
        ],
    )

    main()

    assert received == [("tenant_a", "v1", "pending", 3, 8)]
    output = json.loads(capsys.readouterr().out)
    assert output["items"] == [
        {
            "case_id": "inferred-u1",
            "fingerprint": "sha256:" + "a" * 64,
            "trust_tier": "inferred_from_trusted_feedback",
            "status": "pending",
        }
    ]
    assert "private" not in json.dumps(output)


@pytest.mark.parametrize(
    ("command", "expected_decision"),
    (("approve", "approved"), ("reject", "rejected")),
)
def test_assets_reviews_cli_binds_one_exact_decision(
    command: str,
    expected_decision: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Catch a CLI decision that omits case identity or current-set authority."""
    from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

    received = []

    def decide_review(
        layout: EvaluationAssetLayout,
        case_id: str,
        fingerprint: str,
        decision: str,
        *,
        reviewer: str,
        note: str | None = None,
        expected_review_set_fingerprint: str | None = None,
    ) -> dict:
        received.append(
            (
                layout.tenant_id,
                layout.asset_id,
                case_id,
                fingerprint,
                decision,
                reviewer,
                note,
                expected_review_set_fingerprint,
            )
        )
        return {
            "decision_id": "sha256:" + "c" * 64,
            "case_id": case_id,
            "fingerprint": fingerprint,
            "status": decision,
            "note": "must-not-leak",
        }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        EvaluationAssetLayout,
        "decide_review",
        decide_review,
        raising=False,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "reviews",
            command,
            "--tenant",
            "tenant_a",
            "--asset-id",
            "v1",
            "--tenants-root",
            "tenants",
            "--case-id",
            "inferred-u1",
            "--fingerprint",
            "sha256:" + "a" * 64,
            "--reviewer",
            "reviewer@example.com",
            "--note",
            "checked",
            "--review-set",
            "sha256:" + "b" * 64,
        ],
    )

    main()

    assert received == [
        (
            "tenant_a",
            "v1",
            "inferred-u1",
            "sha256:" + "a" * 64,
            expected_decision,
            "reviewer@example.com",
            "checked",
            "sha256:" + "b" * 64,
        )
    ]
    assert json.loads(capsys.readouterr().out) == {
        "case_id": "inferred-u1",
        "decision_id": "sha256:" + "c" * 64,
        "fingerprint": "sha256:" + "a" * 64,
        "status": expected_decision,
    }


def test_assets_reviews_cli_finalizes_current_set_synchronously(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Catch a CLI finalization that queues work without executing Stage 8."""
    from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline

    received = []

    class FinalState:
        def to_dict(self) -> dict:
            return {
                "tenant_id": "tenant_a",
                "asset_id": "v1",
                "status": "released",
                "current_stage": "dataset_splits",
                "counts": {"approved": 1, "pending": 0},
                "error": "must-not-leak",
            }

    def finalize_review(
        pipeline: EvaluationAssetPipeline,
        *,
        reviewer: str,
        note: str | None = None,
        expected_review_set_fingerprint: str | None = None,
        expected_decision_set_fingerprint: str | None = None,
        **kwargs,
    ) -> FinalState:
        received.append(
            (
                pipeline.layout.tenant_id,
                pipeline.layout.asset_id,
                reviewer,
                note,
                expected_review_set_fingerprint,
                expected_decision_set_fingerprint,
                kwargs,
            )
        )
        return FinalState()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        EvaluationAssetPipeline,
        "finalize_review",
        finalize_review,
        raising=False,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "reviews",
            "finalize",
            "--tenant",
            "tenant_a",
            "--asset-id",
            "v1",
            "--tenants-root",
            "tenants",
            "--reviewer",
            "reviewer@example.com",
            "--note",
            "release approved cases",
            "--review-set",
            "sha256:" + "b" * 64,
            "--decision-set",
            "sha256:" + "c" * 64,
        ],
    )

    main()

    assert received == [
        (
            "tenant_a",
            "v1",
            "reviewer@example.com",
            "release approved cases",
            "sha256:" + "b" * 64,
            "sha256:" + "c" * 64,
            {},
        )
    ]
    assert json.loads(capsys.readouterr().out) == {
        "tenant_id": "tenant_a",
        "asset_id": "v1",
        "status": "released",
        "current_stage": "dataset_splits",
        "counts": {"approved": 1, "pending": 0},
    }


def test_assets_create_and_status_use_evaluation_assets_workspace(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    tenants_root = tmp_path / "tenants"
    sources = tenants_root / "bootstrap" / "source_artifacts"
    sources.mkdir(parents=True)
    feedback = sources / "feedback.jsonl"
    unlabeled = sources / "unlabeled.jsonl"
    feedback.write_text(
        json.dumps(_evaluation_input("f1", labeled=True)) + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        json.dumps(_evaluation_input("u1", labeled=False)) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "create",
            "--tenant",
            "bootstrap",
            "--asset-id",
            "v2",
            "--feedback",
            str(feedback),
            "--unlabeled",
            str(unlabeled),
            "--tenants-root",
            str(tenants_root),
            "--clusters",
            "1",
            "--embedding-model",
            "tfidf",
            "--enable-synthetic-coverage",
            "--synthetic-cases-per-cluster",
            "3",
        ],
    )

    main()

    asset_root = tenants_root / "bootstrap" / "evaluation_assets" / "v2"
    assert (
        asset_root
        / "stages"
        / "01_raw_inputs"
        / "labeled_feedback.jsonl"
    ).exists()
    assert (
        asset_root
        / "stages"
        / "01_raw_inputs"
        / "unlabeled.jsonl"
    ).exists()
    assert (asset_root / "stages" / "08_dataset_splits").is_dir()
    assert not (asset_root / "raw_inputs").exists()
    config = json.loads((asset_root / "config.json").read_text(encoding="utf-8"))
    assert config["embedding_provider"] == "tfidf"
    assert config["embedding_model"] == "tfidf"
    assert config["synthetic_coverage_enabled"] is True
    assert config["synthetic_cases_per_cluster"] == 3
    assert not (tenants_root / "bootstrap" / "datasets").exists()
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "status",
            "--tenant",
            "bootstrap",
            "--asset-id",
            "v2",
            "--tenants-root",
            str(tenants_root),
        ],
    )
    main()

    assert '"status": "draft"' in capsys.readouterr().out


def test_assets_create_cli_rejects_other_tenant_source_before_writes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The CLI create path enforces the same selected-tenant source boundary."""
    monkeypatch.chdir(tmp_path)
    tenants_root = tmp_path / "tenants"
    other_sources = tenants_root / "tenant_b" / "source_artifacts"
    selected_sources = tenants_root / "tenant_a" / "source_artifacts"
    other_sources.mkdir(parents=True)
    selected_sources.mkdir(parents=True)
    feedback = other_sources / "feedback.jsonl"
    unlabeled = selected_sources / "unlabeled.jsonl"
    feedback.write_text(
        json.dumps(_evaluation_input("f1", labeled=True)) + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        json.dumps(_evaluation_input("u1", labeled=False)) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "create",
            "--tenant",
            "tenant_a",
            "--feedback",
            str(feedback),
            "--unlabeled",
            str(unlabeled),
            "--tenants-root",
            str(tenants_root),
        ],
    )

    with pytest.raises(ValueError, match="selected tenant"):
        main()

    assert not (
        tenants_root / "tenant_a" / "evaluation_assets" / "v1"
    ).exists()


def test_assets_extend_cli_rejects_other_tenant_source_before_writes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The CLI extend path enforces the selected-tenant source boundary."""
    from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig
    from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

    monkeypatch.chdir(tmp_path)
    tenants_root = tmp_path / "tenants"
    selected_sources = tenants_root / "tenant_a" / "source_artifacts"
    other_sources = tenants_root / "tenant_b" / "source_artifacts"
    selected_sources.mkdir(parents=True)
    other_sources.mkdir(parents=True)
    feedback = selected_sources / "feedback.jsonl"
    unlabeled = selected_sources / "unlabeled.jsonl"
    addition = other_sources / "additional.jsonl"
    feedback.write_text(
        json.dumps(_evaluation_input("f1", labeled=True)) + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        json.dumps(_evaluation_input("u1", labeled=False)) + "\n",
        encoding="utf-8",
    )
    addition.write_text(
        json.dumps(_evaluation_input("f2", labeled=True)) + "\n",
        encoding="utf-8",
    )
    parent = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    parent.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "extend",
            "--tenant",
            "tenant_a",
            "--parent-asset-id",
            "v1",
            "--asset-id",
            "v2",
            "--additional-feedback",
            str(addition),
            "--tenants-root",
            str(tenants_root),
        ],
    )

    with pytest.raises(ValueError, match="selected tenant"):
        main()

    assert not (
        tenants_root / "tenant_a" / "evaluation_assets" / "v2"
    ).exists()


def test_assets_extend_cli_parses_incremental_clustering_options() -> None:
    args = build_parser().parse_args(
        [
            "assets",
            "extend",
            "--tenant",
            "tenant_a",
            "--parent-asset-id",
            "v1",
            "--asset-id",
            "v2",
            "--additional-unlabeled",
            "new.jsonl",
            "--clustering-mode",
            "refresh",
            "--embedding-model",
            "tfidf",
            "--clusters",
            "12",
        ]
    )

    assert args.assets_command == "extend"
    assert args.parent_asset_id == "v1"
    assert args.clustering_mode == "refresh"
    assert args.embedding_model == "tfidf"
    assert args.clusters == 12


def test_assets_adopt_cli_exposes_explicit_legacy_transition(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from src.hephaestus.evaluation_assets.models import (
        EvaluationAssetConfig,
        PipelineState,
    )
    from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

    monkeypatch.chdir(tmp_path)
    state = PipelineState.new(
        EvaluationAssetConfig(tenant_id="tenant_a", asset_id="legacy-v1"),
        "2026-08-19T00:00:00+00:00",
    )
    state.status = "released"
    received = []

    def adopt(layout: EvaluationAssetLayout, *, lock_timeout: float = 0) -> PipelineState:
        received.append((layout.tenant_id, layout.asset_id, lock_timeout))
        return state

    monkeypatch.setattr(EvaluationAssetLayout, "adopt_legacy", adopt)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "adopt",
            "--tenant",
            "tenant_a",
            "--asset-id",
            "legacy-v1",
            "--tenants-root",
            str(tmp_path / "tenants"),
        ],
    )

    main()

    assert received == [("tenant_a", "legacy-v1", 0)]
    assert '"status": "released"' in capsys.readouterr().out


def test_assets_cli_rejects_absolute_root_outside_invocation_before_writes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """CLI repository-relative paths never infer an outside absolute base."""
    repository_base = tmp_path / "repository"
    repository_base.mkdir()
    outside_root = tmp_path / "outside" / "tenants"
    monkeypatch.chdir(repository_base)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "create",
            "--tenant",
            "tenant_a",
            "--feedback",
            "feedback.jsonl",
            "--unlabeled",
            "unlabeled.jsonl",
            "--tenants-root",
            str(outside_root),
        ],
    )

    with pytest.raises(ValueError, match="repository base"):
        main()

    assert not outside_root.exists()


def test_assets_cli_rejects_symlinked_tenants_ancestor_before_writes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """CLI startup rejects an in-base path that traverses an external symlink."""
    repository_base = tmp_path / "repository"
    repository_base.mkdir()
    outside = tmp_path / "outside"
    tenants_root = outside / "tenants"
    tenants_root.mkdir(parents=True)
    sentinel = outside / "KEEP"
    sentinel.write_bytes(b"KEEP")
    try:
        (repository_base / "escape").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")
    monkeypatch.chdir(repository_base)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "create",
            "--tenant",
            "tenant_a",
            "--feedback",
            "feedback.jsonl",
            "--unlabeled",
            "unlabeled.jsonl",
            "--tenants-root",
            "escape/tenants",
        ],
    )

    with pytest.raises(ValueError, match="exact repository base"):
        main()

    assert sentinel.read_bytes() == b"KEEP"
    assert not (tenants_root / "tenant_a").exists()


def _evaluation_input(record_id: str, *, labeled: bool) -> dict:
    row = {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": f"group-{record_id}",
        "task_type": "generic",
        "user_input": "Process the supplied input.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }
    if labeled:
        row.update(
            {
                "assistant_output": "A previous response.",
                "feedback": {
                    "polarity": "positive",
                    "rationale": "The response satisfied the request.",
                },
            }
        )
    return row
