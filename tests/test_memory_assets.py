# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from data_pipeline_fakes import ScriptedModel, make_record, write_jsonl

from src.hephaestus.cli import build_parser
from src.hephaestus.data_pipeline.build import build_asset
from src.hephaestus.data_pipeline.config import AssetConfig
from src.hephaestus.memory_assets import (
    MEMORY_ASSET_SCHEMA_VERSION,
    MEMORY_CARD_SCHEMA_VERSION,
    build_memory_asset,
)
from src.hephaestus.memory_evidence import build_additive_memory_asset

CRITERION_ID = "G001.c1"


class FakeMemoryProvider:
    provider_name = "fake"
    model = "fake-memory"

    def __init__(self, *, criterion_id: str = CRITERION_ID) -> None:
        self.criterion_id = criterion_id
        self.payloads: List[Dict[str, Any]] = []

    def generate_json(self, system_prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        del system_prompt
        self.payloads.append(json.loads(json.dumps(payload)))
        traces = payload["supporting_traces"]
        return {
            "memory_card": {
                "title": "Confirm before changing an order",
                "summary": "Confirm the order, act, and verify the result.",
                "when_to_use": ["The user asks to change an order."],
                "when_not_to_use": [],
                "instructions": [
                    {
                        "text": "Confirm the order before changing it.",
                        "source_criterion_ids": [self.criterion_id],
                    }
                ],
                "avoid": [],
                "tool_guidance": [],
                "example_steps": [
                    {
                        "text": "Confirm, apply the change, then verify.",
                        "source_trace_ids": [traces[0]["trace_id"]],
                    }
                ],
            }
        }

    def drain_call_metadata(self) -> List[Dict[str, Any]]:
        return [{"request_id": "request-1"}]


class FakeAdditiveProvider:
    provider_name = "fake"
    model = "fake-additive-memory"

    def __init__(self) -> None:
        self.payloads: List[Dict[str, Any]] = []

    def generate_json(self, system_prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        del system_prompt
        self.payloads.append(json.loads(json.dumps(payload)))
        if payload["mode"] == "runtime_memory_evidence_mining":
            pattern = {
                "guideline_id": "G001",
                "kind": "procedure",
                "text": "Verify the order state after the change.",
                "source_criterion_ids": [CRITERION_ID],
                "source_trace_ids": [payload["episodes"][0]["trace_id"]],
                "confidence": 0.9,
            }
            return {"patterns": [pattern]}
        pattern = payload["candidate_patterns"][0]
        addition = {
            "kind": "procedure",
            "text": "After changing an order, check the returned state.",
            "source_criterion_ids": pattern["source_criterion_ids"],
            "source_trace_ids": pattern["source_trace_ids"],
            "source_pattern_ids": [pattern["pattern_id"]],
        }
        return {"additions": [addition]}

    def drain_call_metadata(self) -> List[Dict[str, Any]]:
        return []


def _asset(tmp_path: Path, model: ScriptedModel | None = None) -> Path:
    """Build a small finished asset with the pipeline and return its directory."""
    feedback = [
        make_record(
            f"f{i:02d}", labeled=True, rationale=f"Changed order {i} without confirming; mail a{i}@b.com."
        )
        for i in range(10)
    ]
    for row in feedback[::2]:
        row["feedback"]["polarity"] = "positive"
    write_jsonl(tmp_path / "feedback.jsonl", feedback)
    write_jsonl(tmp_path / "unlabeled.jsonl", [make_record(f"u{i:02d}", labeled=False) for i in range(10)])
    config = AssetConfig.from_dict(
        {
            "tenant_id": "tenant-a",
            "asset_id": "asset-v1",
            "feedback": "feedback.jsonl",
            "unlabeled": "unlabeled.jsonl",
            "model": "source-model",
            "workers": 1,
        }
    )
    scripted = model or ScriptedModel()
    build_asset(config, repository_root=tmp_path, provider_factory=lambda: scripted)
    return config.asset_root(tmp_path)


def _build(tmp_path: Path, provider: FakeMemoryProvider, **overrides: Any) -> Dict[str, Any]:
    return build_memory_asset(
        tenants_root=tmp_path / "tenants",
        tenant_id="tenant-a",
        source_asset_id="asset-v1",
        memory_asset_id=overrides.pop("memory_asset_id", "memory-v1"),
        provider=provider,
        **overrides,
    )


def _memory_root(tmp_path: Path, memory_id: str) -> Path:
    return tmp_path / "tenants" / "tenant-a" / "memory_assets" / memory_id


class TestBuildMemoryAsset:
    def test_creates_one_grounded_card_per_guideline(self, tmp_path: Path) -> None:
        """Each catalog guideline becomes one card built from its train feedback traces."""
        _asset(tmp_path)
        provider = FakeMemoryProvider()

        manifest = _build(tmp_path, provider, max_source_traces=2)

        output = _memory_root(tmp_path, "memory-v1")
        [card] = [json.loads(line) for line in (output / "memory_cards.jsonl").read_text().splitlines()]
        assert manifest["card_count"] == 1
        assert manifest["schema_version"] == MEMORY_ASSET_SCHEMA_VERSION
        assert manifest["evidence_mode"] == "trusted_only"
        assert manifest["include_inferred"] is False
        assert {"manifest.json", "catalog.json", "lessons.jsonl", "inputs/feedback.jsonl"} <= set(
            manifest["source_artifacts"]
        )
        assert "datasets/train.jsonl" not in manifest["source_artifacts"]
        assert card["schema_version"] == MEMORY_CARD_SCHEMA_VERSION
        assert (card["source_guideline_id"], card["trust_tier"], card["confidence"]) == (
            "G001",
            "trusted_feedback",
            0.9,
        )
        assert len(card["selected_source_record_ids"]) == 2
        assert "Procedure:" in card["injection_text"]

    def test_traces_are_redacted_aliased_and_mix_polarities(self, tmp_path: Path) -> None:
        """Supporting traces follow the asset's redaction, hide record IDs, and lead with both polarities."""
        _asset(tmp_path)
        provider = FakeMemoryProvider()

        _build(tmp_path, provider, max_source_traces=2)

        payload = provider.payloads[0]
        traces = payload["supporting_traces"]
        assert [trace["trusted_feedback"]["polarity"] for trace in traces] == ["positive", "negative"]
        assert all("record_id" not in trace["trace"] for trace in traces)
        assert "<email>" in json.dumps(traces) and "@b.com" not in json.dumps(traces)
        assert payload["guideline"]["criteria"][0]["criterion_id"] == CRITERION_ID
        assert "lesson_ids" not in payload["guideline"]

    def test_uses_the_assets_model_by_default(self, tmp_path: Path) -> None:
        """Without --model, the card model defaults to the model the asset was built with."""
        _asset(tmp_path)

        with pytest.raises(ValueError, match="injected provider model"):
            _build(tmp_path, FakeMemoryProvider(), model="other-model")

    def test_rejects_unknown_criterion_citations(self, tmp_path: Path) -> None:
        """An instruction citing an invented criterion fails and writes nothing."""
        _asset(tmp_path)

        with pytest.raises(ValueError, match="unknown IDs"):
            _build(tmp_path, FakeMemoryProvider(criterion_id="invented"))
        assert not _memory_root(tmp_path, "memory-v1").exists()

    def test_rejects_non_train_feedback(self, tmp_path: Path) -> None:
        """A guideline whose feedback record is not in train fails the build."""
        root = _asset(tmp_path)
        rows = [json.loads(line) for line in (root / "splits.jsonl").read_text().splitlines()]
        lesson = json.loads((root / "lessons.jsonl").read_text().splitlines()[0])
        for row in rows:
            if row["record_id"] == lesson["record_id"]:
                row["split"] = "test"
        write_jsonl(root / "splits.jsonl", rows)

        with pytest.raises(ValueError, match="non-train feedback"):
            _build(tmp_path, FakeMemoryProvider())

    def test_requires_a_finished_asset(self, tmp_path: Path) -> None:
        """An asset without manifest.json is not a valid source."""
        root = _asset(tmp_path)
        (root / "manifest.json").unlink()

        with pytest.raises(ValueError, match="not finished"):
            _build(tmp_path, FakeMemoryProvider())


class TestBuildAdditiveMemoryAsset:
    def test_mines_inferred_train_cases_that_apply_a_guideline(self, tmp_path: Path) -> None:
        """Inferred train cases that applied a guideline are mined once; trace-inferred ones are skipped."""
        model = ScriptedModel()
        model.trace_inferred_for = {"u06", "u07", "u08", "u09"}
        root = _asset(tmp_path, model)
        _build(tmp_path, FakeMemoryProvider())
        base_card = json.loads((_memory_root(tmp_path, "memory-v1") / "memory_cards.jsonl").read_text())
        train_cases = [
            json.loads(line) for line in (root / "datasets" / "train.jsonl").read_text().splitlines()
        ]
        expected = sorted(
            case["case_id"]
            for case in train_cases
            if case["metadata"]["trust_tier"] == "inferred_from_trusted_feedback"
            and case["expected"]["evaluation_guideline_ids"]
        )
        trace_inferred = [
            case
            for case in train_cases
            if case["metadata"]["trust_tier"] == "inferred_from_trusted_feedback"
            and not case["expected"]["evaluation_guideline_ids"]
        ]
        assert trace_inferred, "fixture must put a trace-inferred case in train"
        provider = FakeAdditiveProvider()

        manifest = build_additive_memory_asset(
            tenants_root=tmp_path / "tenants",
            tenant_id="tenant-a",
            source_asset_id="asset-v1",
            base_memory_asset_id="memory-v1",
            memory_asset_id="memory-additive-v1",
            batch_size=2,
            max_additions_per_card=1,
            provider=provider,
        )

        mined = [
            episode["inferred_case_id"]
            for payload in provider.payloads
            if payload["mode"] == "runtime_memory_evidence_mining"
            for episode in payload["episodes"]
        ]
        [card] = [
            json.loads(line)
            for line in (_memory_root(tmp_path, "memory-additive-v1") / "memory_cards.jsonl")
            .read_text()
            .splitlines()
        ]
        assert expected and sorted(mined) == expected
        assert manifest["inferred_candidate_pool"] == len(expected)
        assert manifest["evidence_mode"] == "trusted_plus_inferred"
        assert manifest["addition_count"] == 1
        assert card["instructions"][:-1] == base_card["instructions"]
        assert card["trusted_spine_preserved"] is True
        assert card["trust_tier"] == "trusted_memory_with_inferred_addendum"


class TestMemoryCli:
    def test_build_arguments(self) -> None:
        """`memory build` takes the source asset and trace limit."""
        args = build_parser().parse_args(
            [
                "memory",
                "build",
                "--tenant",
                "t",
                "--asset-id",
                "a",
                "--memory-id",
                "m",
                "--max-source-traces",
                "3",
            ]
        )

        assert (args.memory_command, args.max_source_traces) == ("build", 3)

    def test_additive_requires_explicit_consent(self) -> None:
        """`memory build-additive` requires --include-inferred."""
        base = ["memory", "build-additive", "--tenant", "t", "--asset-id", "a", "--base-memory-id", "m"]
        with pytest.raises(SystemExit):
            build_parser().parse_args([*base, "--memory-id", "m2"])

        args = build_parser().parse_args(
            [*base, "--memory-id", "m2", "--include-inferred", "--batch-size", "12"]
        )

        assert (args.include_inferred, args.batch_size, args.max_additions_per_card) == (True, 12, 3)
