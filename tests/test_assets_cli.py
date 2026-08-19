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
    for command in ("create", "run", "extend", "adopt", "status"):
        assert command in help_text
    with pytest.raises(SystemExit):
        parser.parse_args(["assets", "intent-inventory"])
    with pytest.raises(SystemExit):
        parser.parse_args(["assets", "assemble"])


def test_assets_create_and_status_use_evaluation_assets_workspace(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
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
