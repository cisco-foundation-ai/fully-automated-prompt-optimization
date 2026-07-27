# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.hephaestus.evaluation_assets.models import EvaluationAssetConfig
from src.hephaestus.evaluation_assets.pipeline import (
    FEEDBACK_PROMPT,
    EvaluationAssetPipeline,
    _normalize_rubric,
)
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout


class FakeEmbeddingProvider:
    model = "fake-embedding"

    def embed_texts(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeRubricProvider:
    model = "fake-rubric"

    def __init__(self):
        self.synthetic_calls = 0

    def generate_json(self, system_prompt, payload):
        if "records" in payload:
            return {
                "rubrics": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": "answer the request",
                        "confidence": 0.9,
                        "must": ["Answer the user's stated request."],
                        "must_not": ["Change the requested scope."],
                        "should": ["Be concise."],
                        "deterministic_checks": [],
                        "tool_expectations": {},
                        "reference_output": None,
                    }
                    for row in payload["records"]
                ]
            }
        if "synthetic evaluation input" in system_prompt:
            self.synthetic_calls += 1
            return {
                "cases": [
                    {
                        "cluster_id": row["cluster_id"],
                        "task_type": row["route"],
                        "user_input": (
                            f"Variation-{case_index + 1} request for "
                            f"{row['cluster_id']}"
                        ),
                        "conversation_context": [],
                    }
                    for row in payload["clusters"]
                    for case_index in range(row["case_count"])
                ]
            }
        return {
            "rubrics": [
                {
                    "cluster_id": row["cluster_id"],
                    "intent_label": "answer the request",
                    "confidence": 0.8,
                    "must": ["Answer the user's stated request."],
                    "must_not": ["Change the requested scope."],
                    "should": ["Be concise."],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
                for row in payload["clusters"]
            ]
        }


def test_rubric_normalization_accepts_list_form_tool_expectations() -> None:
    expectation = "Use the required search tool before answering." + ("x" * 80)

    rubric = _normalize_rubric(
        {
            "intent_label": "answer the request",
            "confidence": 0.9,
            "must": ["Answer the request."],
            "must_not": [],
            "should": [],
            "deterministic_checks": [],
            "tool_expectations": [expectation],
            "reference_output": None,
        },
        "record_id",
        "feedback-1",
        "human_feedback",
        "gpt-5.5",
    )

    assert rubric["tool_expectations"] == {"requirements": [expectation]}
    assert "tool_expectations must be a JSON object" in FEEDBACK_PROMPT


def test_evaluation_asset_optional_settings_have_safe_defaults() -> None:
    config = EvaluationAssetConfig(tenant_id="new_tenant")

    assert config.match_threshold == 0.6
    assert config.synthetic_coverage_enabled is False
    assert config.synthetic_cases_per_cluster == 1

    loaded = EvaluationAssetConfig.from_dict({"tenant_id": "new_tenant"})
    assert loaded.match_threshold == 0.6
    assert loaded.synthetic_coverage_enabled is False
    assert loaded.synthetic_cases_per_cluster == 1


@pytest.mark.parametrize(
    (
        "synthetic_coverage_enabled",
        "synthetic_cases_per_cluster",
        "expected_synthetic_cases",
    ),
    [(False, 1, 0), (True, 2, 2)],
)
def test_pipeline_is_self_contained_and_writes_canonical_layout(
    tmp_path: Path,
    synthetic_coverage_enabled: bool,
    synthetic_cases_per_cluster: int,
    expected_synthetic_cases: int,
) -> None:
    tenants_root = tmp_path / "tenants"
    imports = tmp_path / "imports"
    imports.mkdir()
    feedback = imports / "feedback.jsonl"
    unlabeled = imports / "unlabeled.jsonl"
    feedback.write_text(
        "\n".join(
            json.dumps(
                {
                    "schema_version": "fapo-evaluation-input-v1",
                    "record_id": f"f{index}",
                    "group_id": (
                        "feedback-thread"
                        if index == 1
                        else f"feedback-thread-{index}"
                    ),
                    "task_type": "answer",
                    "user_input": f"Apply requirement {index}",
                    "assistant_output": "Applied an alternative condition",
                    "conversation_context": [],
                    "tool_calls": [],
                    "runtime": {},
                    "metadata": {},
                    "feedback": {
                        "polarity": "negative",
                        "rationale": "The required condition was not satisfied",
                    },
                }
            )
            for index in range(1, 11)
        )
        + "\n",
        encoding="utf-8",
    )
    unlabeled.write_text(
        "\n".join(
            json.dumps(
                {
                    "schema_version": "fapo-evaluation-input-v1",
                    "record_id": f"u{index}",
                    "group_id": (
                        "feedback-thread"
                        if index == 1
                        else f"feedback-thread-{index}"
                    ),
                    "task_type": "answer",
                    "user_input": f"Answer request {index}",
                    "conversation_context": [],
                    "tool_calls": [],
                    "runtime": {},
                    "metadata": {},
                }
            )
            for index in range(1, 4)
        )
        + "\n",
        encoding="utf-8",
    )
    config = EvaluationAssetConfig(
        tenant_id="new_tenant",
        asset_id="v1",
        cluster_count=1,
        rubric_model="fake-rubric",
        embedding_model="fake-embedding",
        synthetic_coverage_enabled=synthetic_coverage_enabled,
        synthetic_cases_per_cluster=synthetic_cases_per_cluster,
    )
    rubric_provider = FakeRubricProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        config,
        feedback,
        unlabeled,
        rubric_provider=rubric_provider,
        embedding_provider=FakeEmbeddingProvider(),
    )

    feedback.unlink()
    unlabeled.unlink()
    state = pipeline.run()
    layout = pipeline.layout

    assert state.status == "completed"
    assert all(stage.status == "completed" for stage in state.stages)
    assert layout.feedback_path.exists()
    assert layout.unlabeled_path.exists()
    assert (layout.prepared_inputs / "normalized_feedback.jsonl").exists()
    assert (layout.decision_assets / "intent_matches.jsonl").exists()
    assert (layout.dataset_splits / "train.jsonl").exists()
    assert layout.manifest_path.exists()
    assert not (layout.tenant_root / "datasets").exists()

    prepared_feedback = json.loads(
        (layout.prepared_inputs / "normalized_feedback.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    prepared_intent = json.loads(
        (layout.prepared_inputs / "intent_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    feedback_rubric = json.loads(
        (layout.decision_assets / "feedback_rubrics.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    trusted_case = json.loads(
        (layout.prepared_inputs / "trusted_cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    inferred_rubric = json.loads(
        (
            layout.decision_assets
            / "inferred_unlabeled_cluster_rubrics.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    dataset_manifest = json.loads(
        (layout.dataset_splits / "dataset_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert prepared_feedback["record_id"] == "f1"
    assert prepared_feedback["group_id"] == "feedback-thread"
    assert prepared_feedback["schema_version"] == "fapo-evaluation-input-v1"
    assert "feedback_id" not in prepared_feedback
    assert "thread_id" not in prepared_feedback
    assert prepared_intent["record_id"] == "u1"
    assert prepared_intent["group_id"] == "feedback-thread"
    assert prepared_intent["schema_version"] == "fapo-evaluation-input-v1"
    assert "feedback_id" not in prepared_intent
    assert "thread_id" not in prepared_intent
    assert feedback_rubric["record_id"] == "f1"
    assert "feedback_id" not in feedback_rubric
    assert "review_status" not in feedback_rubric
    assert trusted_case["metadata"]["group_id"] == "feedback-thread"
    assert trusted_case["metadata"]["request_id"] == "f1"
    assert "review_status" not in trusted_case["metadata"]
    assert "thread_group" not in trusted_case["metadata"]
    assert "request_group" not in trusted_case["metadata"]
    assert inferred_rubric["review_status"] == "review_required"
    assert (
        dataset_manifest["review_policy"]["feedback_rubrics"]
        == "accepted_without_review"
    )
    assert dataset_manifest["coverage"]["match_threshold"] == 0.6
    assert dataset_manifest["synthetic_coverage"] == {
        "enabled": synthetic_coverage_enabled,
        "cases_per_cluster": synthetic_cases_per_cluster,
    }
    assert dataset_manifest["regression_gate"] == {
        "source": "trusted_feedback",
        "fraction": 0.2,
        "selection": "deterministic_group_safe_random",
        "seed": 42,
    }
    assert (
        dataset_manifest["review_policy"]["regression_gate"]
        == "automatic_trusted_feedback_holdout"
    )

    synthetic_candidates = [
        json.loads(line)
        for line in (
            layout.decision_assets / "synthetic_candidates.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    synthetic_cases = [
        json.loads(line)
        for line in (
            layout.prepared_inputs / "synthetic_cases.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert len(synthetic_candidates) == expected_synthetic_cases
    assert len(synthetic_cases) == expected_synthetic_cases
    assert len({row["case_id"] for row in synthetic_candidates}) == len(
        synthetic_candidates
    )
    assert rubric_provider.synthetic_calls == (
        1 if synthetic_coverage_enabled else 0
    )

    regression_cases = [
        json.loads(line)
        for line in (
            layout.dataset_splits / "regression_trusted.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    standard_trusted_cases = [
        json.loads(line)
        for name in ("train_trusted", "validation_trusted", "test_trusted")
        for line in (
            layout.dataset_splits / f"{name}.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert len(regression_cases) == 2
    assert len(standard_trusted_cases) == 8
    assert {
        row["case_id"] for row in regression_cases
    }.isdisjoint(row["case_id"] for row in standard_trusted_cases)
    assert {
        row["metadata"]["group_id"] for row in regression_cases
    }.isdisjoint(
        row["metadata"]["group_id"] for row in standard_trusted_cases
    )
    assert state.counts["regression_trusted_cases"] == 2

    combined_splits = {
        name: [
            json.loads(line)
            for line in (
                layout.dataset_splits / f"{name}.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        ]
        for name in ("train", "validation", "test")
    }
    split_groups = {
        name: {row["metadata"]["group_id"] for row in rows}
        for name, rows in combined_splits.items()
    }
    assert split_groups["train"].isdisjoint(split_groups["validation"])
    assert split_groups["train"].isdisjoint(split_groups["test"])
    assert split_groups["validation"].isdisjoint(split_groups["test"])
    regression_groups = {
        row["metadata"]["group_id"] for row in regression_cases
    }
    assert all(
        regression_groups.isdisjoint(groups)
        for groups in split_groups.values()
    )

    triage_cases = [
        json.loads(line)
        for line in (
            layout.dataset_splits / "triage_hold.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert all(
        row["metadata"]["group_id"] in regression_groups
        and row["metadata"]["hold_reason"]
        == "group_id_reserved_for_regression"
        for row in triage_cases
    )
    case_locations = {
        row["case_id"]: split
        for split, rows in {
            **combined_splits,
            "regression": regression_cases,
            "triage": triage_cases,
        }.items()
        for row in rows
    }
    for index in range(1, 4):
        trusted_location = case_locations[f"feedback-f{index}"]
        inferred_location = case_locations[f"inferred-u{index}"]
        if trusted_location == "regression":
            assert inferred_location == "triage"
        else:
            assert inferred_location == trusted_location
    assert state.counts["triage_hold_cases"] == len(triage_cases)


def test_layout_rejects_unsafe_tenant_and_asset_names(tmp_path: Path) -> None:
    for tenant_id, asset_id in (("../escape", "v1"), ("tenant", "../../asset")):
        try:
            EvaluationAssetLayout(tmp_path / "tenants", tenant_id, asset_id)
        except ValueError:
            continue
        raise AssertionError("unsafe evaluation asset path was accepted")
