# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.hephaestus.datasets.intent_assets import IntentCluster, IntentMatch
from src.hephaestus.evaluation_assets.models import (
    STAGE_COUNT_KEYS,
    EvaluationAssetConfig,
    PipelineStage,
)
from src.hephaestus.evaluation_assets.pipeline import (
    FEEDBACK_PROMPT,
    EvaluationAssetPipeline,
    _build_labeling_queue,
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
        self.feedback_record_ids = []

    def generate_json(self, system_prompt, payload):
        if "records" in payload:
            self.feedback_record_ids.extend(
                row["record_id"] for row in payload["records"]
            )
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


def test_layout_resolves_existing_legacy_artifact_paths(tmp_path: Path) -> None:
    layout = EvaluationAssetLayout(tmp_path / "tenants", "legacy_tenant", "v1")
    for name in (
        "raw_inputs",
        "prepared_inputs",
        "decision_assets",
        "review_queues",
        "dataset_splits",
    ):
        (layout.root / name).mkdir(parents=True, exist_ok=True)

    assert layout.uses_stage_layout is False
    assert layout.artifact_path(
        "rubric_extraction",
        "feedback_rubrics.jsonl",
    ) == (layout.root / "decision_assets" / "feedback_rubrics.jsonl")
    assert layout.artifact_path(
        "rubric_extraction",
        "trusted_cases.jsonl",
    ) == (layout.root / "prepared_inputs" / "trusted_cases.jsonl")
    assert layout.artifact_path(
        "coverage_decisions",
        "review_queue/labeling_queue.jsonl",
    ) == (layout.root / "review_queues" / "labeling_queue.jsonl")


def test_revise_config_invalidates_only_dependent_stages(tmp_path: Path) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    feedback.write_text("{}\n", encoding="utf-8")
    unlabeled.write_text("{}\n", encoding="utf-8")
    layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=5,
            match_threshold=0.6,
        ),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages:
        stage_state.status = "completed"
        stage_state.message = "done"
        stage_state.started_at = "start"
        stage_state.completed_at = "end"
    state.status = "failed"
    state.error = "stopped"
    state.counts = {
        key: 1 for keys in STAGE_COUNT_KEYS.values() for key in keys
    }
    layout.save_state(state)
    stage_four_artifact = layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    )
    stage_five_artifact = layout.artifact_path(
        PipelineStage.COVERAGE_DECISIONS,
        "intent_matches.jsonl",
    )
    stage_four_artifact.write_text("{}\n", encoding="utf-8")
    stage_five_artifact.write_text("{}\n", encoding="utf-8")
    layout.manifest_path.write_text("{}\n", encoding="utf-8")

    revision = layout.revise_config({"match_threshold": 0.2})

    revised_state = layout.load_state()
    assert revision["resume_from_stage"] == "coverage_decisions"
    assert revision["invalidated_from_stage"] == "coverage_decisions"
    assert revision["changed_fields"] == {
        "match_threshold": {"previous": 0.6, "new": 0.2}
    }
    assert layout.load_config().match_threshold == 0.2
    assert stage_four_artifact.exists()
    assert not stage_five_artifact.exists()
    assert not layout.manifest_path.exists()
    assert [
        item.status for item in revised_state.stages[:4]
    ] == ["completed"] * 4
    assert [
        item.status for item in revised_state.stages[4:]
    ] == ["pending"] * 4
    assert "intent_clusters" in revised_state.counts
    assert "matched_clusters" not in revised_state.counts
    assert revised_state.status == "queued"
    assert revised_state.current_stage == "coverage_decisions"
    history = [
        json.loads(line)
        for line in layout.config_history_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert [entry["event"] for entry in history] == [
        "configuration_created",
        "configuration_updated",
    ]


def test_revise_config_derives_embedding_provider_and_restarts_stage_four(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    feedback.write_text("{}\n", encoding="utf-8")
    unlabeled.write_text("{}\n", encoding="utf-8")
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages[:3]:
        stage_state.status = "completed"
    layout.save_state(state)

    revision = layout.revise_config({"embedding_model": "tfidf"})

    config = layout.load_config()
    assert config.embedding_model == "tfidf"
    assert config.embedding_provider == "tfidf"
    assert revision["resume_from_stage"] == "intent_clustering"
    assert revision["invalidated_from_stage"] == "intent_clustering"


def test_revise_config_with_unchanged_values_preserves_checkpoints(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    feedback.write_text("{}\n", encoding="utf-8")
    unlabeled.write_text("{}\n", encoding="utf-8")
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    state.stages[0].status = "completed"
    layout.save_state(state)

    revision = layout.revise_config({"match_threshold": 0.6})

    assert revision == {
        "changed_fields": {},
        "invalidated_from_stage": None,
        "resume_from_stage": None,
    }
    assert layout.load_state().stages[0].status == "completed"
    assert layout.config_revision_summary()["count"] == 1


def test_revise_config_resumes_an_earlier_incomplete_stage(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    feedback.write_text("{}\n", encoding="utf-8")
    unlabeled.write_text("{}\n", encoding="utf-8")
    layout = EvaluationAssetLayout(tmp_path / "tenants", "tenant_a", "v1")
    state = layout.initialize(
        EvaluationAssetConfig(tenant_id="tenant_a"),
        feedback,
        unlabeled,
    )
    for stage_state in state.stages:
        stage_state.status = "completed"
    state.stages[4].status = "failed"
    state.status = "failed"
    state.current_stage = "coverage_decisions"
    layout.save_state(state)

    revision = layout.revise_config({"synthetic_coverage_enabled": True})

    assert revision["invalidated_from_stage"] == "synthetic_coverage"
    assert revision["resume_from_stage"] == "coverage_decisions"
    assert layout.load_state().current_stage == "coverage_decisions"


def test_extend_asset_keeps_clustering_and_extracts_only_new_rubrics(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_feedback = inputs / "added-feedback.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1", "u2"])
    _write_extension_feedback(added_feedback, ["u1"])
    parent_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v1")
    parent_pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            cluster_count=1,
            synthetic_coverage_enabled=False,
        ),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    parent_pipeline.run()
    parent_inventory = parent_layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    ).read_text(encoding="utf-8")
    parent_locations = _split_case_locations(parent_layout)

    child_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")
    child_layout.initialize_extension(
        parent_layout,
        additional_feedback=added_feedback,
        additional_unlabeled=None,
        clustering_mode="keep",
    )
    parent_layout.root.rename(tmp_path / "archived-parent")
    child_provider = FakeRubricProvider()
    child_state = EvaluationAssetPipeline(
        child_layout,
        rubric_provider=child_provider,
        embedding_provider=FakeEmbeddingProvider(),
    ).run()

    assert child_state.status == "completed"
    assert child_provider.feedback_record_ids == ["u1"]
    assert child_layout.artifact_path(
        PipelineStage.INTENT_CLUSTERING,
        "intent_inventory.jsonl",
    ).read_text(encoding="utf-8") == parent_inventory
    rubrics = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "feedback_rubrics.jsonl",
        )
    )
    assert {row["record_id"] for row in rubrics} == {"f1", "u1"}
    inferred = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.LABEL_INFERENCE,
            "inferred_cases.jsonl",
        )
    )
    assert "inferred-u1" not in {row["case_id"] for row in inferred}
    child_locations = _split_case_locations(child_layout)
    for case_id in ("feedback-f1", "inferred-u2"):
        assert child_locations[case_id] == parent_locations[case_id]
    lineage = json.loads(child_layout.lineage_path.read_text(encoding="utf-8"))
    assert lineage["parent_asset_id"] == "v1"
    assert lineage["clustering_mode"] == "keep"


def test_extend_asset_refreshes_clustering_for_new_unlabeled_records(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_unlabeled = inputs / "added-unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1", "u2"])
    _write_extension_unlabeled(added_unlabeled, ["u3"])
    parent = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    parent.run()
    parent_layout = parent.layout

    child_layout = EvaluationAssetLayout(tenants_root, "tenant_a", "v2")
    child_layout.initialize_extension(
        parent_layout,
        additional_feedback=None,
        additional_unlabeled=added_unlabeled,
        clustering_mode="refresh",
        config_updates={"cluster_count": 2},
    )
    child_provider = FakeRubricProvider()
    state = EvaluationAssetPipeline(
        child_layout,
        rubric_provider=child_provider,
        embedding_provider=FakeEmbeddingProvider(),
    ).run()

    assert state.status == "completed"
    assert child_provider.feedback_record_ids == []
    assert state.counts["unlabeled_records"] == 3
    assert state.counts["intent_clusters"] == 2
    lineage_rows = _read_test_jsonl(
        child_layout.artifact_path(
            PipelineStage.INTENT_CLUSTERING,
            "cluster_lineage.jsonl",
        )
    )
    assert lineage_rows
    assert {
        row["relationship"] for row in lineage_rows
    } <= {"continued", "split", "merged", "new", "retired"}


def test_extend_asset_rejects_unlabeled_additions_when_clustering_is_kept(
    tmp_path: Path,
) -> None:
    tenants_root = tmp_path / "tenants"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    feedback = inputs / "feedback.jsonl"
    unlabeled = inputs / "unlabeled.jsonl"
    added_unlabeled = inputs / "added-unlabeled.jsonl"
    _write_extension_feedback(feedback, ["f1"])
    _write_extension_unlabeled(unlabeled, ["u1"])
    _write_extension_unlabeled(added_unlabeled, ["u2"])
    parent = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(tenant_id="tenant_a", cluster_count=1),
        feedback,
        unlabeled,
        rubric_provider=FakeRubricProvider(),
        embedding_provider=FakeEmbeddingProvider(),
    )
    parent.run()

    with pytest.raises(ValueError, match="use refresh"):
        EvaluationAssetLayout(tenants_root, "tenant_a", "v2").initialize_extension(
            parent.layout,
            additional_feedback=None,
            additional_unlabeled=added_unlabeled,
            clustering_mode="keep",
        )


def test_labeling_queue_samples_only_clusters_needing_trusted_labels() -> None:
    clusters = [
        IntentCluster(
            cluster_id="route-a-001",
            route="route_a",
            record_ids=[f"u{index}" for index in range(1, 25)],
            representative_ids=["u1", "u2", "u3"],
            top_terms=["category", "alpha"],
        ),
        IntentCluster(
            cluster_id="route-b-001",
            route="route_b",
            record_ids=["u25"],
            representative_ids=["u25"],
            top_terms=["category", "beta"],
        ),
    ]
    matches = [
        IntentMatch(
            cluster_id="route-a-001",
            status="missing_or_weak_labels",
            score=0.2,
            reason="below threshold",
        ),
        IntentMatch(
            cluster_id="route-b-001",
            status="matched_trusted_intent",
            score=0.9,
        ),
    ]
    intent_rows = [
        {
            "record_id": f"u{index}",
            "user_input": f"request {index}",
            "route": "route_a" if index < 25 else "route_b",
        }
        for index in range(1, 26)
    ]

    queue = _build_labeling_queue(
        clusters,
        matches,
        intent_rows,
        sample_ratio=0.1,
        max_per_cluster=3,
    )

    assert [row["trace"]["record_id"] for row in queue] == ["u1", "u2", "u3"]
    assert {row["cluster_id"] for row in queue} == {"route-a-001"}
    assert {row["annotation_status"] for row in queue} == {"pending"}
    assert {row["samples_from_cluster"] for row in queue} == {3}


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
    assert layout.artifact_path(
        "prepared_inputs",
        "normalized_feedback.jsonl",
    ).exists()
    assert layout.artifact_path(
        "coverage_decisions",
        "intent_matches.jsonl",
    ).exists()
    assert layout.artifact_path(
        "coverage_decisions",
        "review_queue/labeling_queue.jsonl",
    ).exists()
    assert layout.artifact_path("dataset_splits", "train.jsonl").exists()
    assert layout.manifest_path.exists()
    assert not (layout.tenant_root / "datasets").exists()
    assert (layout.root / "stages" / "01_raw_inputs").is_dir()
    assert not (layout.root / "raw_inputs").exists()

    prepared_feedback = json.loads(
        layout.artifact_path(
            "prepared_inputs",
            "normalized_feedback.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    prepared_intent = json.loads(
        layout.artifact_path(
            "prepared_inputs",
            "intent_records.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    feedback_rubric = json.loads(
        layout.artifact_path(
            "rubric_extraction",
            "feedback_rubrics.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    trusted_case = json.loads(
        layout.artifact_path(
            "rubric_extraction",
            "trusted_cases.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    inferred_rubric = json.loads(
        layout.artifact_path(
            "label_inference",
            "inferred_unlabeled_cluster_rubrics.jsonl",
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    dataset_manifest = json.loads(
        layout.artifact_path(
            "dataset_splits",
            "dataset_manifest.json",
        ).read_text(encoding="utf-8")
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
    assert dataset_manifest["coverage"]["labeling_queue"] == {
        "statuses": [
            "needs_more_trusted_examples",
            "missing_or_weak_labels",
        ],
        "sample_ratio": 0.1,
        "minimum_per_cluster": 1,
        "maximum_per_cluster": 3,
        "selection": "deterministic_centroid_nearest",
    }
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
    assert (
        dataset_manifest["review_policy"]["coverage_labeling_queue"]
        == "human_label_required"
    )

    synthetic_candidates = [
        json.loads(line)
        for line in layout.artifact_path(
            "synthetic_coverage",
            "synthetic_candidates.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    synthetic_cases = [
        json.loads(line)
        for line in layout.artifact_path(
            "synthetic_coverage",
            "synthetic_cases.jsonl",
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
        for line in layout.artifact_path(
            "dataset_splits",
            "regression_trusted.jsonl",
        ).read_text(encoding="utf-8").splitlines()
    ]
    standard_trusted_cases = [
        json.loads(line)
        for name in ("train_trusted", "validation_trusted", "test_trusted")
        for line in layout.artifact_path(
            "dataset_splits",
            f"{name}.jsonl",
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
            for line in layout.artifact_path(
                "dataset_splits",
                f"{name}.jsonl",
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
        for line in layout.artifact_path(
            "dataset_splits",
            "triage_hold.jsonl",
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


def _write_extension_feedback(path: Path, record_ids: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": record_id,
            "group_id": f"group-{record_id}",
            "task_type": "answer",
            "route": "route_a",
            "user_input": f"Request {record_id}",
            "assistant_output": "Previous response",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
            "feedback": {
                "polarity": "positive",
                "rationale": "The response satisfied the request.",
            },
        }
        for record_id in record_ids
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_extension_unlabeled(path: Path, record_ids: list[str]) -> None:
    rows = [
        {
            "schema_version": "fapo-evaluation-input-v1",
            "record_id": record_id,
            "group_id": f"group-{record_id}",
            "task_type": "answer",
            "route": "route_a",
            "user_input": f"Request {record_id}",
            "conversation_context": [],
            "tool_calls": [],
            "runtime": {},
            "metadata": {},
        }
        for record_id in record_ids
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_test_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _split_case_locations(layout: EvaluationAssetLayout) -> dict[str, str]:
    locations = {}
    for split in ("train", "validation", "test", "regression_trusted"):
        for row in _read_test_jsonl(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                f"{split}.jsonl",
            )
        ):
            locations[row["case_id"]] = split
    return locations
