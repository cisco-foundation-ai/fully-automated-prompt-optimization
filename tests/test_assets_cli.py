# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import sys
from pathlib import Path

import src.hephaestus.datasets.embedding_providers as embedding_providers
from src.hephaestus.cli import main


def test_assets_intent_inventory_cli_uses_openai_vectorizer(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """assets intent-inventory can use the OpenAI embedding vectorizer path."""
    records = tmp_path / "records.jsonl"
    trusted = tmp_path / "trusted_intents.jsonl"
    output_dir = tmp_path / "inventory"
    records.write_text(
        json.dumps(
            {
                "record_id": "r1",
                "canonical_intent_text": "category alpha request",
                "route": "route_a",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    trusted.write_text(
        json.dumps(
            {
                "intent_id": "trusted-alpha",
                "label": "category alpha",
                "texts": ["category alpha example"],
                "route": "route_a",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    class DummyEmbeddingProvider:
        created_with = None

        def __init__(self, **kwargs):
            DummyEmbeddingProvider.created_with = kwargs

        def embed_texts(self, texts):
            return [[1.0, 0.0] if "alpha" in text else [0.0, 1.0] for text in texts]

    monkeypatch.setattr(
        embedding_providers,
        "OpenAIEmbeddingProvider",
        DummyEmbeddingProvider,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "intent-inventory",
            "--records",
            str(records),
            "--trusted-intents",
            str(trusted),
            "--output-dir",
            str(output_dir),
            "--id-field",
            "record_id",
            "--text-field",
            "canonical_intent_text",
            "--route-field",
            "route",
            "--vectorizer",
            "openai",
            "--embedding-model",
            "test-embedding-model",
        ],
    )

    main()

    output = capsys.readouterr().out
    matches = [
        json.loads(line)
        for line in (output_dir / "intent_matches.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert "Wrote" in output
    assert DummyEmbeddingProvider.created_with["model"] == "test-embedding-model"
    assert matches[0]["status"] == "matched_trusted_intent"


def test_assets_intent_inventory_cli_uses_statistical_coverage_policy(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """assets intent-inventory writes under-covered matches when policy requires more examples."""
    records = tmp_path / "records.jsonl"
    trusted = tmp_path / "trusted_intents.jsonl"
    output_dir = tmp_path / "inventory"
    records.write_text(
        "\n".join(
            json.dumps(
                {
                    "record_id": f"r{index}",
                    "canonical_intent_text": "category alpha request",
                    "route": "route_a",
                }
            )
            for index in range(5)
        )
        + "\n",
        encoding="utf-8",
    )
    trusted.write_text(
        json.dumps(
            {
                "intent_id": "trusted-alpha",
                "label": "category alpha",
                "texts": ["category alpha request"],
                "route": "route_a",
                "metadata": {"trusted_example_count": 1},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "intent-inventory",
            "--records",
            str(records),
            "--trusted-intents",
            str(trusted),
            "--output-dir",
            str(output_dir),
            "--id-field",
            "record_id",
            "--text-field",
            "canonical_intent_text",
            "--route-field",
            "route",
            "--vectorizer",
            "tfidf",
            "--min-trusted-examples",
            "2",
            "--match-threshold",
            "0.1",
        ],
    )

    main()

    output = capsys.readouterr().out
    matches = [
        json.loads(line)
        for line in (output_dir / "intent_matches.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert "Wrote" in output
    assert matches[0]["status"] == "needs_more_trusted_examples"
    assert matches[0]["trusted_example_count"] == 1


def test_assets_assemble_cli_writes_bundle(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """assets assemble writes split files, manifest, and filter audit files."""
    trusted = tmp_path / "trusted.jsonl"
    synthetic = tmp_path / "synthetic.jsonl"
    output_dir = tmp_path / "out"
    trusted.write_text(
        json.dumps(_case("trusted-1", message="request alpha")) + "\n",
        encoding="utf-8",
    )
    synthetic.write_text(
        json.dumps(_case("synth-1", message="request beta", thread="s1")) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hephaestus",
            "assets",
            "assemble",
            "--trusted-cases",
            str(trusted),
            "--synthetic-cases",
            str(synthetic),
            "--output-dir",
            str(output_dir),
            "--dataset-version",
            "v1",
        ],
    )

    main()

    output = capsys.readouterr().out
    manifest = json.loads((output_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert "accepted synthetic=1" in output
    assert manifest["dataset_version"] == "v1"
    assert (output_dir / "synthetic_filter_issues.jsonl").exists()
    assert (output_dir / "train.jsonl").exists()


def test_assets_create_and_status_use_evaluation_assets_workspace(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    tenants_root = tmp_path / "tenants"
    feedback = tmp_path / "feedback.jsonl"
    unlabeled = tmp_path / "unlabeled.jsonl"
    feedback.write_text('{"id":"f1"}\n', encoding="utf-8")
    unlabeled.write_text('{"id":"u1"}\n', encoding="utf-8")
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

    assert '"status": "queued"' in capsys.readouterr().out


def _case(case_id: str, message: str, thread: str = "t1") -> dict:
    return {
        "case_id": case_id,
        "task_type": "generic",
        "context": {"messages_json": json.dumps([{"role": "user", "content": message}])},
        "expected": {"rubric": {"must": ["answer the request"]}},
        "metadata": {"group_id": thread},
    }
