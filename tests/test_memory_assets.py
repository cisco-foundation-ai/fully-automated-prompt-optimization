# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.hephaestus.cli import build_parser
from src.hephaestus.memory_evidence import build_additive_memory_asset
from src.hephaestus.memory_assets import (
    MEMORY_ASSET_SCHEMA_VERSION,
    MEMORY_CARD_SCHEMA_VERSION,
    build_memory_asset,
)


class FakeMemoryProvider:
    provider_name = "fake"
    model = "fake-memory"

    def __init__(self, *, criterion_id: str = "criterion-required") -> None:
        self.criterion_id = criterion_id
        self.payloads: list[dict] = []

    def generate_json(self, system_prompt, payload):
        del system_prompt
        self.payloads.append(dict(payload))
        traces = payload["supporting_traces"]
        return {
            "memory_card": {
                "title": "Complete a supported account action",
                "summary": "Inspect state, confirm eligibility, act, and verify the result.",
                "when_to_use": ["The user requests this account action."],
                "when_not_to_use": [],
                "instructions": [
                    {
                        "text": "Confirm the current state before changing it.",
                        "source_criterion_ids": [self.criterion_id],
                    }
                ],
                "avoid": [
                    {
                        "text": "Do not report success before observing the resulting state.",
                        "source_criterion_ids": ["criterion-prohibited"],
                    }
                ],
                "tool_guidance": [],
                "example_steps": [
                    {
                        "text": "Inspect the resource, apply the allowed action, then verify.",
                        "source_trace_ids": [traces[0]["trace_id"]],
                    }
                ],
            }
        }

    def drain_call_metadata(self):
        return [{"request_id": "request-1"}]


class FakeAdditiveProvider:
    provider_name = "fake"
    model = "fake-additive-memory"

    def __init__(self) -> None:
        self.payloads: list[dict] = []
        self.call_count = 0

    def generate_json(self, system_prompt, payload):
        del system_prompt
        self.call_count += 1
        self.payloads.append(dict(payload))
        if payload["mode"] == "runtime_memory_evidence_mining":
            trace_id = payload["episodes"][0]["trace_id"]
            return {
                "patterns": [
                    {
                        "guideline_id": "guideline-account-action",
                        "kind": "procedure",
                        "text": "Verify the resulting resource state after the update.",
                        "source_criterion_ids": ["criterion-required"],
                        "source_trace_ids": [trace_id],
                        "confidence": 0.95,
                    }
                ]
            }
        pattern = payload["candidate_patterns"][0]
        return {
            "additions": [
                {
                    "kind": "procedure",
                    "text": "After updating, inspect the returned resource state.",
                    "source_criterion_ids": pattern["source_criterion_ids"],
                    "source_trace_ids": pattern["source_trace_ids"],
                    "source_pattern_ids": [pattern["pattern_id"]],
                }
            ]
        }

    def drain_call_metadata(self):
        return [{"request_id": f"request-{self.call_count}"}]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _feedback_row(record_id: str, polarity: str, *, split: str = "train") -> dict:
    return {
        "record_id": record_id,
        "task_type": "account_action",
        "route": "account_action",
        "user_input": "Please perform the requested action.",
        "assistant_output": "The action is complete.",
        "conversation_context": [],
        "tool_calls": [
            {
                "name": "update_resource",
                "arguments": {"resource_id": "resource-1"},
                "result": {"status": "updated"},
            }
        ],
        "runtime": {},
        "feedback": {
            "polarity": polarity,
            "rationale": "The observed behavior was reviewed.",
        },
        "trusted_split": split,
        "evidence_eligible": True,
    }


def _source_asset(tmp_path: Path) -> Path:
    root = tmp_path / "tenants" / "tenant-a" / "evaluation_assets" / "asset-v1"
    _write_json(root / "pipeline_state.json", {"status": "released"})
    _write_json(root / "asset_manifest.json", {"asset_id": "asset-v1"})
    _write_json(root / "config.json", {"rubric_model": "source-model"})
    _write_jsonl(
        root
        / "stages"
        / "03_evaluation_guidelines"
        / "evaluation_guidelines.jsonl",
        [
            {
                "guideline_id": "guideline-account-action",
                "route": "account_action",
                "intent_label": "perform an account action",
                "description": "Perform only supported account actions.",
                "confidence": 0.9,
                "source_record_ids": ["record-negative", "record-positive", "record-extra"],
                "criteria": [
                    {
                        "criterion_id": "criterion-required",
                        "kind": "required",
                        "statement": "Confirm the current state before acting.",
                    },
                    {
                        "criterion_id": "criterion-prohibited",
                        "kind": "prohibited",
                        "statement": "Do not claim an unobserved successful state change.",
                    },
                ],
                "tool_expectations": {},
                "conflicts": [],
                "uncertainties": [],
            }
        ],
    )
    _write_jsonl(
        root / "stages" / "02_prepared_inputs" / "normalized_feedback.jsonl",
        [
            _feedback_row("record-negative", "negative"),
            _feedback_row("record-positive", "positive"),
            _feedback_row("record-extra", "positive"),
        ],
    )
    return root


def _add_inferred_training_sources(root: Path) -> None:
    guideline_id = "guideline-account-action"
    raw_rows = []
    inferred_rows = []
    for index, cluster in enumerate(("cluster-a", "cluster-b", "cluster-c"), start=1):
        record_id = f"inferred-record-{index}"
        raw = _feedback_row(record_id, "positive")
        raw.pop("feedback")
        raw_rows.append(raw)
        inferred_rows.append(
            {
                "case_id": f"inferred-{record_id}",
                "task_type": "account_action",
                "context": {},
                "expected": {
                    "evaluation_guideline_ids": [guideline_id],
                    "rubric": {
                        "must": ["Confirm the current state before acting."],
                        "must_not": [],
                        "should": [],
                    },
                },
                "metadata": {
                    "applicable_guideline_ids": [guideline_id],
                    "request_id": record_id,
                    "review_status": "approved",
                    "split": "train",
                    "trust_tier": "inferred_from_trusted_feedback",
                    "source_cluster": cluster,
                    "rubric_confidence": 0.99,
                    "rubric_evidence_pointers": ["tool_calls[0]"],
                },
            }
        )
    _write_jsonl(root / "stages" / "01_raw_inputs" / "unlabeled.jsonl", raw_rows)
    _write_jsonl(
        root / "stages" / "08_dataset_splits" / "train_inferred.jsonl",
        inferred_rows,
    )


def test_build_memory_asset_creates_one_grounded_card_per_guideline(tmp_path: Path) -> None:
    _source_asset(tmp_path)
    provider = FakeMemoryProvider()

    manifest = build_memory_asset(
        tenants_root=tmp_path / "tenants",
        tenant_id="tenant-a",
        source_asset_id="asset-v1",
        memory_asset_id="memory-v1",
        max_source_traces=2,
        provider=provider,
    )

    output = tmp_path / "tenants" / "tenant-a" / "memory_assets" / "memory-v1"
    card = json.loads((output / "memory_cards.jsonl").read_text().splitlines()[0])
    saved_manifest = json.loads((output / "manifest.json").read_text())

    assert manifest["card_count"] == 1
    assert saved_manifest["schema_version"] == MEMORY_ASSET_SCHEMA_VERSION
    assert saved_manifest["evidence_mode"] == "trusted_only"
    assert saved_manifest["include_approved_inferred"] is False
    assert "train_inferred.jsonl" not in saved_manifest["source_artifacts"]
    assert card["schema_version"] == MEMORY_CARD_SCHEMA_VERSION
    assert card["source_guideline_id"] == "guideline-account-action"
    assert card["trust_tier"] == "trusted_feedback"
    assert card["selected_source_record_ids"] == ["record-extra", "record-negative"]
    assert card["example_steps"][0]["source_record_ids"] == ["record-extra"]
    assert "Procedure:" in card["injection_text"]
    assert [row["trusted_feedback"]["polarity"] for row in provider.payloads[0]["supporting_traces"]] == [
        "positive",
        "negative",
    ]


def test_build_memory_asset_rejects_unknown_criterion_citations(tmp_path: Path) -> None:
    _source_asset(tmp_path)

    with pytest.raises(ValueError, match="unknown IDs"):
        build_memory_asset(
            tenants_root=tmp_path / "tenants",
            tenant_id="tenant-a",
            source_asset_id="asset-v1",
            memory_asset_id="memory-v1",
            provider=FakeMemoryProvider(criterion_id="invented-criterion"),
        )

    assert not (
        tmp_path / "tenants" / "tenant-a" / "memory_assets" / "memory-v1"
    ).exists()


def test_build_memory_asset_rejects_protected_feedback(tmp_path: Path) -> None:
    root = _source_asset(tmp_path)
    feedback_path = (
        root / "stages" / "02_prepared_inputs" / "normalized_feedback.jsonl"
    )
    rows = [json.loads(line) for line in feedback_path.read_text().splitlines()]
    rows[0]["trusted_split"] = "test"
    _write_jsonl(feedback_path, rows)

    with pytest.raises(ValueError, match="non-reusable feedback"):
        build_memory_asset(
            tenants_root=tmp_path / "tenants",
            tenant_id="tenant-a",
            source_asset_id="asset-v1",
            memory_asset_id="memory-v1",
            provider=FakeMemoryProvider(),
        )


def test_build_additive_memory_asset_processes_every_inferred_case_once(
    tmp_path: Path,
) -> None:
    root = _source_asset(tmp_path)
    _add_inferred_training_sources(root)
    build_memory_asset(
        tenants_root=tmp_path / "tenants",
        tenant_id="tenant-a",
        source_asset_id="asset-v1",
        memory_asset_id="memory-v1",
        provider=FakeMemoryProvider(),
    )
    base_path = (
        tmp_path / "tenants" / "tenant-a" / "memory_assets" / "memory-v1"
    )
    base_card = json.loads((base_path / "memory_cards.jsonl").read_text().splitlines()[0])
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

    output = (
        tmp_path
        / "tenants"
        / "tenant-a"
        / "memory_assets"
        / "memory-additive-v1"
    )
    card = json.loads((output / "memory_cards.jsonl").read_text().splitlines()[0])
    trace_index = [
        json.loads(line) for line in (output / "trace_index.jsonl").read_text().splitlines()
    ]
    mined_case_ids = [
        episode["inferred_case_id"]
        for payload in provider.payloads
        if payload["mode"] == "runtime_memory_evidence_mining"
        for episode in payload["episodes"]
    ]

    assert manifest["inferred_candidate_pool"] == 3
    assert manifest["evidence_mode"] == "trusted_plus_approved_inferred"
    assert manifest["include_approved_inferred"] is True
    assert manifest["inferred_cases_processed"] == 3
    assert manifest["batch_count"] == 2
    assert manifest["addition_count"] == 1
    assert len(trace_index) == 3
    assert len(mined_case_ids) == len(set(mined_case_ids)) == 3
    assert card["title"] == base_card["title"]
    assert card["summary"] == base_card["summary"]
    assert card["when_to_use"] == base_card["when_to_use"]
    assert card["instructions"][:-1] == base_card["instructions"]
    assert card["addition_count"] == 1
    assert card["trusted_spine_preserved"] is True
    assert card["trust_tier"] == "trusted_memory_with_approved_inferred_addendum"


def test_memory_build_cli_contract() -> None:
    args = build_parser().parse_args(
        [
            "memory",
            "build",
            "--tenant",
            "tenant-a",
            "--asset-id",
            "asset-v1",
            "--memory-id",
            "memory-v1",
            "--max-source-traces",
            "3",
        ]
    )

    assert args.command == "memory"
    assert args.memory_command == "build"
    assert args.max_source_traces == 3

    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "memory",
                "build",
                "--tenant",
                "tenant-a",
                "--asset-id",
                "asset-v1",
                "--memory-id",
                "memory-v1",
                "--include-approved-inferred",
            ]
        )

    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "memory",
                "build-additive",
                "--tenant",
                "tenant-a",
                "--asset-id",
                "asset-v1",
                "--base-memory-id",
                "memory-v1",
                "--memory-id",
                "memory-additive-v1",
            ]
        )

    additive_args = build_parser().parse_args(
        [
            "memory",
            "build-additive",
            "--tenant",
            "tenant-a",
            "--asset-id",
            "asset-v1",
            "--base-memory-id",
            "memory-v1",
            "--memory-id",
            "memory-additive-v1",
            "--include-approved-inferred",
            "--batch-size",
            "12",
        ]
    )
    assert additive_args.memory_command == "build-additive"
    assert additive_args.include_approved_inferred is True
    assert additive_args.batch_size == 12
    assert additive_args.max_additions_per_card == 3
