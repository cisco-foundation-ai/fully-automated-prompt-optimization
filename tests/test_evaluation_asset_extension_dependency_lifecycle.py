# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Pipeline-level extension dependency invalidation contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

from src.hephaestus.evaluation_assets import pipeline as pipeline_module
from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
)
from src.hephaestus.evaluation_assets.pipeline import EvaluationAssetPipeline
from src.hephaestus.evaluation_assets.split_isolation import (
    assign_split,
    derive_split_groups,
)
from src.hephaestus.evaluation_assets.trust_tiers import (
    INFERRED_FROM_TRUSTED_FEEDBACK,
    SYNTHETIC_FROM_TRUSTED_RUBRIC,
)
from src.hephaestus.evaluation_assets.workspace import EvaluationAssetLayout

ROUTE_A = "route_a"
ROUTE_B = "route_b"


class _LifecycleEmbeddingProvider:
    provider_name = "extension-lifecycle"
    model = "extension-lifecycle-embedding"

    def __init__(self, *, drift_route_a_match: bool = False) -> None:
        self.drift_route_a_match = drift_route_a_match
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors: list[list[float]] = []
        for text in texts:
            if "ROUTE_A" in text:
                if self.drift_route_a_match and "trusted request" in text:
                    vectors.append([0.8, 0.6])
                else:
                    vectors.append([1.0, 0.0])
            elif "ROUTE_B" in text:
                vectors.append([0.0, 1.0])
            else:
                raise AssertionError(f"unrecognized embedding text: {text!r}")
        return vectors


class _LifecycleRubricProvider:
    def __init__(
        self,
        *,
        provider_name: str = "extension-lifecycle",
        model: str = "extension-lifecycle-rubric",
        temperature: float = 0.0,
        guideline_suffix_by_route: Mapping[str, str] | None = None,
        inferred_suffix_by_route: Mapping[str, str] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self.temperature = temperature
        self.guideline_suffix_by_route = dict(guideline_suffix_by_route or {})
        self.inferred_suffix_by_route = dict(inferred_suffix_by_route or {})
        self.stage_six_clusters: list[str] = []
        self.stage_seven_clusters: list[str] = []

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if "records" in payload:
            return {
                "evidence": [
                    {
                        "record_id": row["record_id"],
                        "intent_label": f"handle {row['task_type']} request",
                        "confidence": 0.95,
                        "observations": [
                            {
                                "claim": f"Satisfy the {row['task_type']} request.",
                                "evidence_type": "explicit_feedback",
                                "evidence_pointer": "feedback.rationale",
                                "polarity": row["feedback"]["polarity"],
                            }
                        ],
                        "requested_corrections": [],
                        "uncertainties": [],
                    }
                    for row in payload["records"]
                ]
            }
        if "evidence" in payload:
            route = str(payload["route"])
            source_record_ids = [str(row["record_id"]) for row in payload["evidence"]]
            suffix = self.guideline_suffix_by_route.get(route, "")
            return {
                "guidelines": [
                    {
                        "intent_label": f"handle {route} request",
                        "description": f"Handle {route} requests.{suffix}",
                        "route": route,
                        "source_record_ids": source_record_ids,
                        "confidence": 0.95,
                        "criteria": [
                            {
                                "kind": "required",
                                "statement": f"Satisfy the {route} request.{suffix}",
                                "source_record_ids": source_record_ids,
                                "dimension": "task_success",
                                "severity": "critical",
                                "applicability": "always",
                                "scoring": "binary",
                                "evidence_required": False,
                                "evaluator": {
                                    "type": "llm_judge",
                                    "fallback": "human_review",
                                },
                            }
                        ],
                        "tool_expectations": {},
                        "reference_output": None,
                        "conflicts": [],
                        "uncertainties": [],
                    }
                ]
            }
        if "synthetic evaluation inputs" in system_prompt:
            scenario_texts = {
                ROUTE_A: (
                    "Astronomy telescope orbital calibration request",
                    "Volcanic seismology sensor interpretation request",
                ),
                ROUTE_B: (
                    "Culinary souffle kitchen timing request",
                    "Textile weaving loom pattern request",
                ),
            }
            cases: list[dict[str, Any]] = []
            for cluster in payload["clusters"]:
                cluster_id = str(cluster["cluster_id"])
                route = str(cluster["route"])
                self.stage_seven_clusters.append(cluster_id)
                for index in range(1, int(cluster["case_count"]) + 1):
                    cases.append(
                        {
                            "cluster_id": cluster_id,
                            "task_type": route,
                            "user_input": scenario_texts[route][index - 1],
                            "conversation_context": [],
                        }
                    )
            return {"cases": cases}

        rubrics: list[dict[str, Any]] = []
        for cluster in payload["clusters"]:
            cluster_id = str(cluster["cluster_id"])
            route = str(cluster["route"])
            self.stage_six_clusters.append(cluster_id)
            suffix = self.inferred_suffix_by_route.get(route, "")
            rubrics.append(
                {
                    "cluster_id": cluster_id,
                    "intent_label": f"handle {route} request",
                    "confidence": 0.9,
                    "must": [f"Satisfy the {route} request.{suffix}"],
                    "must_not": [f"Substitute another route for {route}."],
                    "should": [],
                    "deterministic_checks": [],
                    "tool_expectations": {},
                    "reference_output": None,
                }
            )
        return {"rubrics": rubrics}


class _RejectingRouteAParentProvider(_LifecycleRubricProvider):
    """Make the parent's Route A candidate duplicate its inferred case."""

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if "synthetic evaluation inputs" not in system_prompt:
            return super().generate_json(system_prompt, payload)
        cases: list[dict[str, Any]] = []
        for cluster in payload["clusters"]:
            cluster_id = str(cluster["cluster_id"])
            route = str(cluster["route"])
            self.stage_seven_clusters.append(cluster_id)
            user_input = (
                str(cluster["representatives"][0])
                if route == ROUTE_A
                else "Culinary souffle kitchen timing request"
            )
            cases.append(
                {
                    "cluster_id": cluster_id,
                    "task_type": route,
                    "user_input": user_input,
                    "conversation_context": [],
                }
            )
        return {"cases": cases}


class _CrossClusterDuplicateProvider(_LifecycleRubricProvider):
    """Make canonical cluster order decide which duplicate candidate survives."""

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if "synthetic evaluation inputs" not in system_prompt:
            return super().generate_json(system_prompt, payload)
        cases: list[dict[str, Any]] = []
        for cluster in payload["clusters"]:
            cluster_id = str(cluster["cluster_id"])
            route = str(cluster["route"])
            self.stage_seven_clusters.append(cluster_id)
            cases.append(
                {
                    "cluster_id": cluster_id,
                    "task_type": route,
                    "user_input": "Culinary souffle kitchen timing request",
                    "conversation_context": [],
                }
            )
        return {"cases": cases}


@dataclass(frozen=True)
class _ReleasedParent:
    pipeline: EvaluationAssetPipeline
    review_items: dict[tuple[str, str, str], dict[str, Any]]
    inference_dependencies: dict[str, dict[str, Any]]
    synthetic_dependencies: dict[str, dict[str, Any]]
    clusters_by_route: dict[str, str]


def _feedback_row(
    record_id: str,
    group_id: str,
    route: str,
) -> dict[str, Any]:
    marker = route.upper()
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": group_id,
        "request_id": record_id,
        "task_type": route,
        "route": route,
        "user_input": f"{marker} trusted request {record_id}",
        "assistant_output": f"Previous {route} response",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
        "feedback": {
            "polarity": "positive",
            "rationale": f"The response satisfied the {route} request.",
        },
    }


def _feedback_for_split(
    record_id: str,
    route: str,
    split: str,
) -> dict[str, Any]:
    for ordinal in range(20_000):
        row = _feedback_row(
            record_id,
            f"group-{route}-{split}-{ordinal}",
            route,
        )
        split_group_id = derive_split_groups([row])[0].split_group_id
        if assign_split(split_group_id, split_seed=42) == split:
            return row
    raise AssertionError(f"could not construct {route} feedback for {split}")


def _unlabeled_row(record_id: str, route: str) -> dict[str, Any]:
    return {
        "schema_version": "fapo-evaluation-input-v1",
        "record_id": record_id,
        "group_id": f"group-{record_id}",
        "request_id": record_id,
        "task_type": route,
        "route": route,
        "user_input": f"{route.upper()} unlabeled request {record_id}",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _dependencies(
    layout: EvaluationAssetLayout,
    stage: PipelineStage,
    filename: str,
) -> dict[str, dict[str, Any]]:
    return {
        str(row["cluster_id"]): dict(row["dependency"])
        for row in _read_jsonl(layout.artifact_path(stage, filename))
    }


def _clusters_by_route(layout: EvaluationAssetLayout) -> dict[str, str]:
    return {
        str(row["route"]): str(row["cluster_id"])
        for row in _read_jsonl(
            layout.artifact_path(
                PipelineStage.INTENT_CLUSTERING,
                "intent_inventory.jsonl",
            )
        )
    }


def _review_key(item: Mapping[str, Any]) -> tuple[str, str, str]:
    case = item["case"]
    metadata = case["metadata"]
    return (
        str(metadata["trust_tier"]),
        str(metadata["source_cluster"]),
        str(item["case_id"]),
    )


def _review_items(layout: EvaluationAssetLayout) -> dict[tuple[str, str, str], dict[str, Any]]:
    page = layout.list_review_items(limit=100)
    return {_review_key(item): dict(item) for item in page["items"]}


def _raw_review_items(
    layout: EvaluationAssetLayout,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Project persisted decisions without historical receipt revalidation."""
    decisions = {
        (str(row["case_id"]), str(row["fingerprint"])): row
        for row in _read_jsonl(layout.review_decisions_path)
    }
    projected: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in _read_jsonl(
        layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "derived_review_items.jsonl",
        )
    ):
        item = dict(row)
        decision = decisions.get((str(item["case_id"]), str(item["fingerprint"])))
        item["status"] = str(decision["status"]) if decision is not None else "pending"
        item["inherited_from"] = decision.get("inherited_from") if decision is not None else None
        projected[_review_key(item)] = item
    return projected


def _tier_cluster_items(
    items: Mapping[tuple[str, str, str], Mapping[str, Any]],
    tier: str,
    cluster_id: str,
) -> list[Mapping[str, Any]]:
    return [
        item
        for (item_tier, item_cluster, _case_id), item in items.items()
        if item_tier == tier and item_cluster == cluster_id
    ]


def _build_released_parent(
    tmp_path: Path,
    *,
    rubric_provider: _LifecycleRubricProvider | None = None,
    expected_pending: int = 4,
) -> _ReleasedParent:
    tenants_root = tmp_path / "tenants"
    source_root = tenants_root / "tenant_a" / "source_artifacts"
    source_root.mkdir(parents=True)
    feedback = source_root / "feedback-v1.jsonl"
    unlabeled = source_root / "unlabeled-v1.jsonl"
    _write_jsonl(
        feedback,
        [
            _feedback_for_split("fa1", ROUTE_A, "train"),
            _feedback_for_split("fb1", ROUTE_B, "train"),
        ],
    )
    _write_jsonl(
        unlabeled,
        [
            _unlabeled_row("ua1", ROUTE_A),
            _unlabeled_row("ub1", ROUTE_B),
        ],
    )
    rubric_provider = rubric_provider or _LifecycleRubricProvider()
    embedding_provider = _LifecycleEmbeddingProvider()
    pipeline = EvaluationAssetPipeline.create(
        tenants_root,
        EvaluationAssetConfig(
            tenant_id="tenant_a",
            asset_id="v1",
            cluster_count=2,
            batch_size=1,
            match_threshold=0.5,
            rubric_provider=rubric_provider.provider_name,
            rubric_model=rubric_provider.model,
            embedding_provider=embedding_provider.provider_name,
            embedding_model=embedding_provider.model,
            synthetic_coverage_enabled=True,
            synthetic_cases_per_cluster=1,
        ),
        feedback,
        unlabeled,
        rubric_provider=rubric_provider,
        embedding_provider=embedding_provider,
        repository_base=tmp_path,
    )
    assert pipeline.run().status == "awaiting_review"
    page = pipeline.layout.list_review_items(limit=100)
    assert page["counts"] == {
        "trusted": 2,
        "approved": 0,
        "pending": expected_pending,
        "rejected": 0,
        "held": 0,
        "total": 2 + expected_pending,
    }
    for item in page["items"]:
        pipeline.layout.decide_review(
            str(item["case_id"]),
            str(item["fingerprint"]),
            "approved",
            reviewer="parent-reviewer",
            expected_review_set_fingerprint=str(page["review_set_fingerprint"]),
        )
    page = pipeline.layout.list_review_items(limit=100)
    assert (
        pipeline.finalize_review(
            reviewer="parent-reviewer",
            expected_review_set_fingerprint=str(page["review_set_fingerprint"]),
            expected_decision_set_fingerprint=str(
                page["decision_set_fingerprint"]
            ),
        ).status
        == "released"
    )
    return _ReleasedParent(
        pipeline=pipeline,
        review_items=_review_items(pipeline.layout),
        inference_dependencies=_dependencies(
            pipeline.layout,
            PipelineStage.LABEL_INFERENCE,
            "inference_dependencies.jsonl",
        ),
        synthetic_dependencies=_dependencies(
            pipeline.layout,
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_dependencies.jsonl",
        ),
        clusters_by_route=_clusters_by_route(pipeline.layout),
    )


def _initialize_child(
    tmp_path: Path,
    parent: _ReleasedParent,
    *,
    additional_feedback: Sequence[Mapping[str, Any]] | None = None,
    additional_unlabeled: Sequence[Mapping[str, Any]] | None = None,
    clustering_mode: str = "keep",
    config_updates: Mapping[str, Any] | None = None,
) -> EvaluationAssetLayout:
    source_root = tmp_path / "tenants" / "tenant_a" / "source_artifacts"
    feedback_path: Path | None = None
    unlabeled_path: Path | None = None
    if additional_feedback is not None:
        feedback_path = source_root / "feedback-v2.jsonl"
        _write_jsonl(feedback_path, additional_feedback)
    if additional_unlabeled is not None:
        unlabeled_path = source_root / "unlabeled-v2.jsonl"
        _write_jsonl(unlabeled_path, additional_unlabeled)
    child = EvaluationAssetLayout(
        tmp_path / "tenants",
        "tenant_a",
        "v2",
        repository_base=tmp_path,
    )
    child.initialize_extension(
        parent.pipeline.layout,
        additional_feedback=feedback_path,
        additional_unlabeled=unlabeled_path,
        clustering_mode=clustering_mode,
        config_updates=config_updates,
    )
    return child


def _baseline_child_layout(tmp_path: Path, parent: _ReleasedParent) -> EvaluationAssetLayout:
    return _initialize_child(
        tmp_path,
        parent,
        additional_feedback=[_feedback_for_split("fa-held", ROUTE_A, "validation")],
    )


def _run_child(
    layout: EvaluationAssetLayout,
    *,
    rubric_provider: _LifecycleRubricProvider | None = None,
    embedding_provider: _LifecycleEmbeddingProvider | None = None,
    verify_review_page: bool = True,
) -> tuple[
    EvaluationAssetPipeline,
    _LifecycleRubricProvider,
    _LifecycleEmbeddingProvider,
    dict[tuple[str, str, str], dict[str, Any]],
]:
    rubric = rubric_provider or _LifecycleRubricProvider()
    embedding = embedding_provider or _LifecycleEmbeddingProvider()
    pipeline = EvaluationAssetPipeline(
        layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    assert pipeline.run().status == "awaiting_review"
    items = _review_items(layout) if verify_review_page else _raw_review_items(layout)
    return pipeline, rubric, embedding, items


def _assert_inferred_review_change_is_cluster_local(
    parent: _ReleasedParent,
    child_items: Mapping[tuple[str, str, str], Mapping[str, Any]],
    *,
    changed_cluster_id: str,
    reusable_cluster_id: str,
) -> None:
    changed = _tier_cluster_items(
        child_items,
        INFERRED_FROM_TRUSTED_FEEDBACK,
        changed_cluster_id,
    )
    reusable = _tier_cluster_items(
        child_items,
        INFERRED_FROM_TRUSTED_FEEDBACK,
        reusable_cluster_id,
    )
    assert len(changed) == 1
    assert len(reusable) == 1
    assert changed[0]["status"] == "pending"
    assert changed[0]["inherited_from"] is None
    assert reusable[0]["status"] == "approved"
    assert reusable[0]["inherited_from"]["parent_asset_id"] == "v1"
    parent_changed = parent.review_items[_review_key(changed[0])]
    parent_reusable = parent.review_items[_review_key(reusable[0])]
    assert changed[0]["fingerprint"] != parent_changed["fingerprint"]
    assert reusable[0]["fingerprint"] == parent_reusable["fingerprint"]


def _assert_synthetic_reviews_are_newly_pending(
    parent: _ReleasedParent,
    child_items: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> None:
    child_synthetic = {
        key: item for key, item in child_items.items() if key[0] == SYNTHETIC_FROM_TRUSTED_RUBRIC
    }
    parent_synthetic = {
        key: item for key, item in parent.review_items.items() if key[0] == SYNTHETIC_FROM_TRUSTED_RUBRIC
    }
    assert set(child_synthetic) == set(parent_synthetic)
    assert all(item["status"] == "pending" for item in child_synthetic.values())
    assert all(item["inherited_from"] is None for item in child_synthetic.values())
    assert all(
        child_synthetic[key]["fingerprint"] != parent_synthetic[key]["fingerprint"] for key in child_synthetic
    )


def test_identical_child_reuses_both_derived_stages_and_inherits_reviews(
    tmp_path: Path,
) -> None:
    """Removing extension reuse would make both provider-call assertions fail."""
    parent = _build_released_parent(tmp_path)
    child_layout = _baseline_child_layout(tmp_path, parent)

    _, rubric, _, child_items = _run_child(child_layout)

    assert _clusters_by_route(child_layout) == parent.clusters_by_route
    assert rubric.stage_six_clusters == []
    assert rubric.stage_seven_clusters == []
    assert (
        _dependencies(
            child_layout,
            PipelineStage.LABEL_INFERENCE,
            "inference_dependencies.jsonl",
        )
        == parent.inference_dependencies
    )
    assert (
        _dependencies(
            child_layout,
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_dependencies.jsonl",
        )
        == parent.synthetic_dependencies
    )
    assert set(child_items) == set(parent.review_items)
    assert all(item["status"] == "approved" for item in child_items.values())
    assert all(item["inherited_from"]["parent_asset_id"] == "v1" for item in child_items.values())


def test_stage_seven_reuse_reaches_a_stable_dependency_fixed_point(
    tmp_path: Path,
) -> None:
    """A new accepted cluster case invalidates every affected tentative reuse."""
    parent = _build_released_parent(
        tmp_path,
        rubric_provider=_RejectingRouteAParentProvider(),
        expected_pending=3,
    )
    cluster_a = parent.clusters_by_route[ROUTE_A]
    cluster_b = parent.clusters_by_route[ROUTE_B]
    parent_synthetic = _read_jsonl(
        parent.pipeline.layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_cases.jsonl",
        )
    )
    assert [
        str((case.get("metadata") or {}).get("source_cluster"))
        for case in parent_synthetic
    ] == [cluster_b]

    child_layout = _baseline_child_layout(tmp_path, parent)
    _, rubric, _, child_items = _run_child(child_layout)
    child_dependencies = _dependencies(
        child_layout,
        PipelineStage.SYNTHETIC_COVERAGE,
        "synthetic_dependencies.jsonl",
    )

    assert rubric.stage_six_clusters == []
    assert rubric.stage_seven_clusters == [cluster_a, cluster_b]
    assert child_dependencies[cluster_b] != parent.synthetic_dependencies[cluster_b]
    child_b_reviews = _tier_cluster_items(
        child_items,
        SYNTHETIC_FROM_TRUSTED_RUBRIC,
        cluster_b,
    )
    assert len(child_b_reviews) == 1
    assert child_b_reviews[0]["status"] == "pending"
    assert child_b_reviews[0]["inherited_from"] is None


def test_stage_seven_reuse_preserves_canonical_cross_cluster_filter_order(
    tmp_path: Path,
) -> None:
    """Tentative reuse cannot give a later cluster priority over a fresh candidate."""
    extension_root = tmp_path / "extension"
    parent = _build_released_parent(
        extension_root,
        rubric_provider=_RejectingRouteAParentProvider(),
        expected_pending=3,
    )
    cluster_a = parent.clusters_by_route[ROUTE_A]
    cluster_b = parent.clusters_by_route[ROUTE_B]
    child_layout = _baseline_child_layout(extension_root, parent)
    child_provider = _CrossClusterDuplicateProvider()

    _, child_provider, _, child_items = _run_child(
        child_layout,
        rubric_provider=child_provider,
    )
    child_accepted = _read_jsonl(
        child_layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_cases.jsonl",
        )
    )
    child_rejected = _read_jsonl(
        child_layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "rejected_synthetic.jsonl",
        )
    )
    child_dependencies = _dependencies(
        child_layout,
        PipelineStage.SYNTHETIC_COVERAGE,
        "synthetic_dependencies.jsonl",
    )

    fresh_provider = _CrossClusterDuplicateProvider()
    fresh = _build_released_parent(
        tmp_path / "fresh",
        rubric_provider=fresh_provider,
        expected_pending=3,
    )
    fresh_accepted = _read_jsonl(
        fresh.pipeline.layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_cases.jsonl",
        )
    )
    fresh_rejected = _read_jsonl(
        fresh.pipeline.layout.artifact_path(
            PipelineStage.SYNTHETIC_COVERAGE,
            "rejected_synthetic.jsonl",
        )
    )

    def source_clusters(rows: Sequence[Mapping[str, Any]]) -> list[str]:
        return [
            str((case.get("metadata") or {}).get("source_cluster"))
            for case in rows
        ]

    assert child_provider.stage_seven_clusters == [cluster_a, cluster_b]
    assert fresh_provider.stage_seven_clusters == [cluster_a, cluster_b]
    assert source_clusters(child_accepted) == source_clusters(fresh_accepted) == [
        cluster_a
    ]
    assert source_clusters(child_rejected) == source_clusters(fresh_rejected) == [
        cluster_b
    ]
    assert child_dependencies[cluster_b] != parent.synthetic_dependencies[cluster_b]
    assert child_accepted[0]["metadata"]["dependency_sha256"] == (
        child_dependencies[cluster_a]["dependency_sha256"]
    )
    assert not _tier_cluster_items(
        child_items,
        SYNTHETIC_FROM_TRUSTED_RUBRIC,
        cluster_b,
    )


@pytest.mark.parametrize(
    "mutation",
    ["guideline_and_rubric_content", "guideline_support_and_source_membership", "match"],
)
def test_cluster_local_stage_six_dependency_mutation_regenerates_only_that_cluster(
    tmp_path: Path,
    mutation: str,
) -> None:
    """Stable cluster IDs cannot authorize reuse after Stage 6 evidence changes."""
    parent = _build_released_parent(tmp_path)
    cluster_a = parent.clusters_by_route[ROUTE_A]
    cluster_b = parent.clusters_by_route[ROUTE_B]
    if mutation == "guideline_support_and_source_membership":
        child_layout = _initialize_child(
            tmp_path,
            parent,
            additional_feedback=[_feedback_for_split("fa2", ROUTE_A, "train")],
        )
        rubric = _LifecycleRubricProvider()
        embedding = _LifecycleEmbeddingProvider()
    else:
        child_layout = _baseline_child_layout(tmp_path, parent)
        rubric = _LifecycleRubricProvider(
            guideline_suffix_by_route=(
                {ROUTE_A: " Require the revised complete criterion."}
                if mutation == "guideline_and_rubric_content"
                else None
            ),
            inferred_suffix_by_route=(
                {ROUTE_A: " Apply the revised complete rubric."}
                if mutation == "guideline_and_rubric_content"
                else None
            ),
        )
        embedding = _LifecycleEmbeddingProvider(
            drift_route_a_match=mutation == "match",
        )

    _, rubric, _, child_items = _run_child(
        child_layout,
        rubric_provider=rubric,
        embedding_provider=embedding,
    )
    child_inference = _dependencies(
        child_layout,
        PipelineStage.LABEL_INFERENCE,
        "inference_dependencies.jsonl",
    )
    child_synthetic = _dependencies(
        child_layout,
        PipelineStage.SYNTHETIC_COVERAGE,
        "synthetic_dependencies.jsonl",
    )

    assert _clusters_by_route(child_layout) == parent.clusters_by_route
    assert rubric.stage_six_clusters == [cluster_a]
    assert child_inference[cluster_a] != parent.inference_dependencies[cluster_a]
    assert child_inference[cluster_b] == parent.inference_dependencies[cluster_b]
    assert set(rubric.stage_seven_clusters) == {cluster_a, cluster_b}
    assert child_synthetic[cluster_a] != parent.synthetic_dependencies[cluster_a]
    assert child_synthetic[cluster_b] != parent.synthetic_dependencies[cluster_b]
    _assert_inferred_review_change_is_cluster_local(
        parent,
        child_items,
        changed_cluster_id=cluster_a,
        reusable_cluster_id=cluster_b,
    )
    _assert_synthetic_reviews_are_newly_pending(parent, child_items)

    parent_descriptor = parent.inference_dependencies[cluster_a]["descriptor"]
    child_descriptor = child_inference[cluster_a]["descriptor"]
    if mutation == "guideline_and_rubric_content":
        assert child_descriptor["guideline"] != parent_descriptor["guideline"]
        child_rubric = _dependencies(
            child_layout,
            PipelineStage.SYNTHETIC_COVERAGE,
            "synthetic_dependencies.jsonl",
        )[cluster_a]["descriptor"]["rubric"]
        parent_rubric = parent.synthetic_dependencies[cluster_a]["descriptor"]["rubric"]
        assert child_rubric != parent_rubric
        assert "revised complete rubric" in child_rubric["must"][0]
    elif mutation == "guideline_support_and_source_membership":
        assert child_descriptor["guideline"]["source_record_ids"] == ["fa1", "fa2"]
        assert child_descriptor["source_members"] != parent_descriptor["source_members"]
        assert child_descriptor["match"]["trusted_example_count"] == 2
    else:
        assert child_descriptor["cluster"] == parent_descriptor["cluster"]
        assert child_descriptor["guideline"] == parent_descriptor["guideline"]
        assert child_descriptor["source_members"] == parent_descriptor["source_members"]
        assert child_descriptor["match"]["score"] == 0.8
        assert parent_descriptor["match"]["score"] == 1.0


def test_refreshed_cluster_membership_regenerates_stable_cluster_ids(
    tmp_path: Path,
) -> None:
    """Keeping a cluster ID cannot hide changed record and source membership."""
    parent = _build_released_parent(tmp_path)
    cluster_a = parent.clusters_by_route[ROUTE_A]
    cluster_b = parent.clusters_by_route[ROUTE_B]
    child_layout = _initialize_child(
        tmp_path,
        parent,
        additional_unlabeled=[_unlabeled_row("ua2", ROUTE_A)],
        clustering_mode="refresh",
        config_updates={"cluster_count": 2},
    )

    _, rubric, _, child_items = _run_child(child_layout)
    child_inference = _dependencies(
        child_layout,
        PipelineStage.LABEL_INFERENCE,
        "inference_dependencies.jsonl",
    )

    assert _clusters_by_route(child_layout) == parent.clusters_by_route
    assert set(rubric.stage_six_clusters) == {cluster_a, cluster_b}
    assert set(rubric.stage_seven_clusters) == {cluster_a, cluster_b}
    assert child_inference[cluster_a]["descriptor"]["cluster"]["record_ids"] == [
        "ua1",
        "ua2",
    ]
    assert (
        child_inference[cluster_a]["descriptor"]["source_members"]
        != parent.inference_dependencies[cluster_a]["descriptor"]["source_members"]
    )
    assert child_inference[cluster_b]["descriptor"] == parent.inference_dependencies[cluster_b]["descriptor"]
    changed = _tier_cluster_items(
        child_items,
        INFERRED_FROM_TRUSTED_FEEDBACK,
        cluster_a,
    )
    reusable = _tier_cluster_items(
        child_items,
        INFERRED_FROM_TRUSTED_FEEDBACK,
        cluster_b,
    )
    assert {str(item["case_id"]) for item in changed} == {
        "inferred-ua1",
        "inferred-ua2",
    }
    assert all(item["status"] == "pending" for item in changed)
    assert all(item["inherited_from"] is None for item in changed)
    assert len(reusable) == 1
    assert reusable[0]["status"] == "approved"
    assert reusable[0]["inherited_from"]["parent_asset_id"] == "v1"
    parent_ua1 = next(
        item for (_tier, _cluster, case_id), item in parent.review_items.items() if case_id == "inferred-ua1"
    )
    child_ua1 = next(item for item in changed if item["case_id"] == "inferred-ua1")
    assert child_ua1["fingerprint"] != parent_ua1["fingerprint"]
    _assert_synthetic_reviews_are_newly_pending(parent, child_items)


@pytest.mark.parametrize("mutation", ["provider_model", "provider_settings", "stage_six_prompt"])
def test_global_stage_six_dependency_mutation_regenerates_all_clusters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """Provider identity/settings and prompt revisions bind Stage 6 reuse."""
    parent = _build_released_parent(tmp_path)
    child_layout = _baseline_child_layout(tmp_path, parent)
    provider = _LifecycleRubricProvider()
    if mutation == "provider_model":
        child_layout.revise_config(
            {
                "rubric_provider": "extension-lifecycle-v2",
                "rubric_model": "extension-lifecycle-rubric-v2",
            }
        )
        provider = _LifecycleRubricProvider(
            provider_name="extension-lifecycle-v2",
            model="extension-lifecycle-rubric-v2",
        )
    elif mutation == "provider_settings":
        provider = _LifecycleRubricProvider(temperature=0.25)
    else:
        monkeypatch.setitem(
            pipeline_module.PROMPT_REVISIONS,
            "label_inference",
            "label-inference-extension-lifecycle-v2",
        )

    _, provider, _, child_items = _run_child(
        child_layout,
        rubric_provider=provider,
    )
    child_inference = _dependencies(
        child_layout,
        PipelineStage.LABEL_INFERENCE,
        "inference_dependencies.jsonl",
    )
    child_synthetic = _dependencies(
        child_layout,
        PipelineStage.SYNTHETIC_COVERAGE,
        "synthetic_dependencies.jsonl",
    )
    clusters = set(parent.clusters_by_route.values())

    assert set(provider.stage_six_clusters) == clusters
    assert set(provider.stage_seven_clusters) == clusters
    assert all(child_inference[item] != parent.inference_dependencies[item] for item in clusters)
    assert all(child_synthetic[item] != parent.synthetic_dependencies[item] for item in clusters)
    assert all(item["status"] == "pending" for item in child_items.values())
    for cluster_id in clusters:
        parent_descriptor = parent.inference_dependencies[cluster_id]["descriptor"]
        child_descriptor = child_inference[cluster_id]["descriptor"]
        if mutation == "provider_model":
            assert child_descriptor["provider"]["provider"] == "extension-lifecycle-v2"
            assert child_descriptor["provider"]["model"] == "extension-lifecycle-rubric-v2"
        elif mutation == "provider_settings":
            assert parent_descriptor["provider"]["settings"]["temperature"] == 0.0
            assert child_descriptor["provider"]["settings"]["temperature"] == 0.25
        else:
            assert child_descriptor["prompt"]["revision"] == "label-inference-extension-lifecycle-v2"


@pytest.mark.parametrize("mutation", ["stage_seven_prompt", "candidate_count"])
def test_stage_seven_only_mutation_reuses_inference_and_invalidates_synthetic_reviews(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """Stage 7 prompt/settings changes retain Stage 6 but not synthetic approval."""
    parent = _build_released_parent(tmp_path)
    config_updates = {"synthetic_cases_per_cluster": 2} if mutation == "candidate_count" else None
    child_layout = _initialize_child(
        tmp_path,
        parent,
        additional_feedback=[_feedback_for_split("fa-held", ROUTE_A, "validation")],
        config_updates=config_updates,
    )
    if mutation == "stage_seven_prompt":
        monkeypatch.setitem(
            pipeline_module.PROMPT_REVISIONS,
            "synthetic_coverage",
            "synthetic-coverage-extension-lifecycle-v2",
        )

    _, rubric, _, child_items = _run_child(
        child_layout,
        verify_review_page=mutation != "stage_seven_prompt",
    )
    child_inference = _dependencies(
        child_layout,
        PipelineStage.LABEL_INFERENCE,
        "inference_dependencies.jsonl",
    )
    child_synthetic = _dependencies(
        child_layout,
        PipelineStage.SYNTHETIC_COVERAGE,
        "synthetic_dependencies.jsonl",
    )
    clusters = set(parent.clusters_by_route.values())

    assert rubric.stage_six_clusters == []
    assert set(rubric.stage_seven_clusters) == clusters
    assert child_inference == parent.inference_dependencies
    assert all(child_synthetic[item] != parent.synthetic_dependencies[item] for item in clusters)
    inferred = [
        item
        for (tier, _cluster_id, _case_id), item in child_items.items()
        if tier == INFERRED_FROM_TRUSTED_FEEDBACK
    ]
    synthetic = [
        item
        for (tier, _cluster_id, _case_id), item in child_items.items()
        if tier == SYNTHETIC_FROM_TRUSTED_RUBRIC
    ]
    assert len(inferred) == 2
    assert all(item["status"] == "approved" for item in inferred)
    assert all(item["inherited_from"]["parent_asset_id"] == "v1" for item in inferred)
    assert synthetic
    assert all(item["status"] == "pending" for item in synthetic)
    assert all(item["inherited_from"] is None for item in synthetic)
    for cluster_id in clusters:
        descriptor = child_synthetic[cluster_id]["descriptor"]
        if mutation == "stage_seven_prompt":
            assert descriptor["prompt"]["revision"] == "synthetic-coverage-extension-lifecycle-v2"
        else:
            assert descriptor["settings"]["candidate_count"] == 2
