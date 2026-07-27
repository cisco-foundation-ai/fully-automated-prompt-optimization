# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from src.hephaestus.datasets.intent_assets import (
    CoveragePolicy,
    IntentCluster,
    IntentRecord,
    TrustedIntent,
    build_intent_inventory,
    build_intent_match_texts,
    canonical_intent_text,
    cluster_records,
    cluster_records_fixed_count,
    dense_vectors_to_sparse,
    load_intent_records_from_jsonl,
    load_trusted_intents_from_jsonl,
    match_clusters_to_trusted_intents,
)


def test_fixed_count_clustering_is_exact_and_deterministic() -> None:
    records = [
        IntentRecord(record_id=f"r{index}", text=f"request {index}", route="route")
        for index in range(6)
    ]
    vectors = {
        f"r{index}": {
            "x": 1.0 if index < 3 else 0.0,
            "y": 0.0 if index < 3 else 1.0,
        }
        for index in range(6)
    }

    first = cluster_records_fixed_count(records, 2, vectors=vectors)
    second = cluster_records_fixed_count(records, 2, vectors=vectors)

    assert len(first) == 2
    assert [cluster.record_ids for cluster in first] == [
        cluster.record_ids for cluster in second
    ]
    assert sorted(record_id for cluster in first for record_id in cluster.record_ids) == [
        f"r{index}" for index in range(6)
    ]


def test_canonical_intent_text_extracts_nested_fields():
    raw = {
        "inputs": {"latest_user": "Process category alpha"},
        "metadata": {"tool": "tool_a", "route": "route_a"},
    }

    text = canonical_intent_text(raw, ["inputs.latest_user", "metadata.tool"])

    assert text == "Process category alpha tool_a"


def test_load_intent_records_from_jsonl_uses_selected_fields(tmp_path: Path):
    path = tmp_path / "records.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "r1",
                "inputs": {"latest_user": "Process category beta"},
                "metadata": {"route": "route_b", "thread": "t1"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = load_intent_records_from_jsonl(
        path,
        id_field="id",
        text_fields=["inputs.latest_user"],
        route_field="metadata.route",
        group_field="metadata.thread",
    )

    assert records == [
        IntentRecord(
            record_id="r1",
            text="Process category beta",
            route="route_b",
            group_id="t1",
        )
    ]


def test_load_trusted_intents_from_jsonl(tmp_path: Path):
    path = tmp_path / "trusted.jsonl"
    path.write_text(
        json.dumps(
            {
                "intent_id": "intent-1",
                "label": "category beta",
                "texts": ["category beta request"],
                "route": "route_b",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    intents = load_trusted_intents_from_jsonl(path)

    assert intents == [
        TrustedIntent(
            intent_id="intent-1",
            label="category beta",
            texts=["category beta request"],
            route="route_b",
        )
    ]


def test_dense_vectors_to_sparse_adapts_embeddings_for_clustering():
    vectors = dense_vectors_to_sparse(["a", "b"], [[3.0, 4.0], [0.0, 2.0]])

    assert round(vectors["a"]["dim_0"], 3) == 0.6
    assert round(vectors["a"]["dim_1"], 3) == 0.8
    assert vectors["b"]["dim_0"] == 0.0
    assert vectors["b"]["dim_1"] == 1.0


def test_cluster_records_groups_similar_intents_by_route():
    records = [
        IntentRecord("alpha-1", "category alpha request variant one", route="route_a"),
        IntentRecord("alpha-2", "category alpha request variant two", route="route_a"),
        IntentRecord("beta-1", "category beta request variant one", route="route_b"),
    ]

    clusters = cluster_records(records, similarity_threshold=0.12)

    cluster_sets = {tuple(cluster.record_ids) for cluster in clusters}
    assert ("alpha-1", "alpha-2") in cluster_sets
    assert ("beta-1",) in cluster_sets
    assert {cluster.route for cluster in clusters} == {"route_a", "route_b"}


def test_match_clusters_to_trusted_intents_routes_unknown_clusters_to_feedback():
    records = [
        IntentRecord("alpha-1", "category alpha request variant one", route="route_a"),
        IntentRecord("alpha-2", "category alpha request variant two", route="route_a"),
        IntentRecord("beta-1", "category beta request variant one", route="route_b"),
    ]
    clusters = cluster_records(records, similarity_threshold=0.12)
    trusted = [
        TrustedIntent(
            intent_id="trusted-alpha",
            label="category alpha",
            texts=["category alpha request"],
            route="route_a",
        )
    ]

    matches = match_clusters_to_trusted_intents(clusters, records, trusted, match_threshold=0.12)

    statuses = {match.cluster_id: match.status for match in matches}
    matched = [match for match in matches if match.status == "matched_trusted_intent"]
    missing = [match for match in matches if match.status == "missing_or_weak_labels"]

    assert len(matched) == 1
    assert matched[0].matched_intent_id == "trusted-alpha"
    assert len(missing) == 1
    assert statuses[missing[0].cluster_id] == "missing_or_weak_labels"


def test_coverage_policy_requests_more_examples_for_under_supported_match():
    records = [
        IntentRecord(f"alpha-{index}", "category alpha request", route="route_a")
        for index in range(5)
    ]
    clusters = [
        IntentCluster(
            cluster_id="route-a-001",
            route="route_a",
            record_ids=[record.record_id for record in records],
            representative_ids=["alpha-0"],
            top_terms=["category", "alpha"],
        )
    ]
    trusted = [
        TrustedIntent(
            intent_id="trusted-alpha",
            label="category alpha",
            texts=["category alpha request"],
            route="route_a",
            metadata={"trusted_example_count": 1, "trusted_group_count": 1},
        )
    ]

    matches = match_clusters_to_trusted_intents(
        clusters,
        records,
        trusted,
        coverage_policy=CoveragePolicy(
            min_match_score=0.1,
            min_trusted_examples=2,
            min_trusted_groups=1,
        ),
    )

    assert matches[0].status == "needs_more_trusted_examples"
    assert matches[0].trusted_example_count == 1
    assert matches[0].unlabeled_to_trusted_ratio == 5.0
    assert "below minimum" in matches[0].reason


def test_coverage_policy_uses_unlabeled_to_trusted_ratio():
    records = [
        IntentRecord(f"alpha-{index}", "category alpha request", route="route_a")
        for index in range(6)
    ]
    clusters = [
        IntentCluster(
            cluster_id="route-a-001",
            route="route_a",
            record_ids=[record.record_id for record in records],
            representative_ids=["alpha-0"],
            top_terms=["category", "alpha"],
        )
    ]
    trusted = [
        TrustedIntent(
            intent_id="trusted-alpha",
            label="category alpha",
            texts=["category alpha request"],
            route="route_a",
            metadata={"trusted_example_count": 2},
        )
    ]

    matches = match_clusters_to_trusted_intents(
        clusters,
        records,
        trusted,
        coverage_policy=CoveragePolicy(
            min_match_score=0.1,
            min_trusted_examples=1,
            max_unlabeled_to_trusted_ratio=2.0,
        ),
    )

    assert matches[0].status == "needs_more_trusted_examples"
    assert matches[0].unlabeled_to_trusted_ratio == 3.0
    assert "ratio" in matches[0].reason


def test_match_clusters_accepts_external_vectors():
    records = [
        IntentRecord("r1", "lexically unrelated text", route="generic"),
    ]
    clusters = [
        IntentCluster(
            cluster_id="generic-001",
            route="generic",
            record_ids=["r1"],
            representative_ids=["r1"],
            top_terms=[],
        )
    ]
    trusted = [
        TrustedIntent(
            intent_id="intent-1",
            label="different words",
            texts=["also different words"],
            route="generic",
        )
    ]
    match_texts = build_intent_match_texts(clusters, records, trusted)
    vectors = {
        key: {"same_dimension": 1.0}
        for key in match_texts
    }

    matches = match_clusters_to_trusted_intents(
        clusters,
        records,
        trusted,
        coverage_policy=CoveragePolicy(min_match_score=0.9),
        vectors=vectors,
    )

    assert matches[0].status == "matched_trusted_intent"
    assert matches[0].score == 1.0


def test_build_intent_inventory_returns_clusters_and_matches():
    records = [
        IntentRecord("r1", "category alpha request variant one", route="route_a"),
        IntentRecord("r2", "category alpha request variant two", route="route_a"),
    ]
    trusted = [
        TrustedIntent(
            intent_id="trusted-alpha",
            label="category alpha",
            texts=["category alpha request"],
            route="route_a",
        )
    ]

    inventory = build_intent_inventory(
        records,
        trusted,
        similarity_threshold=0.1,
        match_threshold=0.1,
    )

    assert len(inventory.clusters) == 1
    assert inventory.matches[0].status == "matched_trusted_intent"
