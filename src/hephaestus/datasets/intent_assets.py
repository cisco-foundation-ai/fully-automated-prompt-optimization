# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Utilities for creating intent inventories from feedback and trace data."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

TOKEN_RE = re.compile(r"[a-z0-9_]+")
STOPWORDS = {
    "a",
    "about",
    "all",
    "also",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "show",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "with",
    "would",
    "you",
}


@dataclass(frozen=True)
class IntentRecord:
    """Canonical text and metadata for one trace or feedback example."""

    record_id: str
    text: str
    route: str = "default"
    group_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrustedIntent:
    """Trusted labeled evidence for an intent family."""

    intent_id: str
    label: str
    texts: List[str]
    route: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IntentCluster:
    """A cluster of unlabeled records that appear to share an intent."""

    cluster_id: str
    route: str
    record_ids: List[str]
    representative_ids: List[str]
    top_terms: List[str]

    @property
    def size(self) -> int:
        """Return the number of records assigned to the cluster."""
        return len(self.record_ids)


@dataclass(frozen=True)
class IntentMatch:
    """Coverage decision for one cluster against the trusted labeled pool."""

    cluster_id: str
    status: str
    score: float
    matched_intent_id: Optional[str] = None
    matched_label: Optional[str] = None
    cluster_size: int = 0
    trusted_example_count: int = 0
    trusted_group_count: int = 0
    unlabeled_to_trusted_ratio: Optional[float] = None
    reason: str = ""


@dataclass(frozen=True)
class CoveragePolicy:
    """Statistical thresholds for trusted-intent coverage decisions."""

    min_match_score: float = 0.35
    min_trusted_examples: int = 1
    min_trusted_groups: int = 0
    large_cluster_size: int = 0
    min_trusted_examples_for_large_cluster: int = 0
    max_unlabeled_to_trusted_ratio: Optional[float] = None


@dataclass(frozen=True)
class IntentInventory:
    """Cluster and coverage outputs for downstream dataset creation."""

    clusters: List[IntentCluster]
    matches: List[IntentMatch]


SparseVector = Dict[str, float]


def normalize_text(text: str) -> str:
    """Normalize whitespace for canonical intent text."""
    return " ".join(str(text).split())


def tokenize(text: str) -> List[str]:
    """Tokenize text for lightweight lexical clustering."""
    tokens = TOKEN_RE.findall(text.lower())
    return [token for token in tokens if len(token) > 1 and token not in STOPWORDS]


def canonical_intent_text(raw: Mapping[str, Any], field_paths: Sequence[str]) -> str:
    """Build canonical intent text from selected fields in a raw record.

    Args:
        raw: Source record.
        field_paths: Dot-separated paths to include, such as
            ``["inputs.messages", "metadata.tool_names"]``.

    Returns:
        Whitespace-normalized text joined from non-empty field values.
    """
    parts: List[str] = []
    for path in field_paths:
        value = _get_path(raw, path)
        text = _stringify_value(value)
        if text:
            parts.append(text)
    return normalize_text(" ".join(parts))


def load_intent_records_from_jsonl(
    path: Path,
    id_field: str,
    text_fields: Sequence[str],
    route_field: Optional[str] = None,
    group_field: Optional[str] = None,
) -> List[IntentRecord]:
    """Load generic intent records from a JSONL file.

    Tenant adapters should choose fields that describe user intent and avoid
    high-cardinality runtime noise such as timestamps or request UUIDs.
    """
    records: List[IntentRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        raw = json.loads(text)
        record_id = _stringify_value(_get_path(raw, id_field))
        if not record_id:
            raise ValueError(f"Missing intent record id at line {line_number}: {id_field}")

        intent_text = canonical_intent_text(raw, text_fields)
        if not intent_text:
            raise ValueError(f"Missing intent text at line {line_number}: {text_fields}")

        route = _stringify_value(_get_path(raw, route_field)) if route_field else "default"
        group_id = _stringify_value(_get_path(raw, group_field)) if group_field else None
        records.append(
            IntentRecord(
                record_id=record_id,
                text=intent_text,
                route=route or "default",
                group_id=group_id or None,
            )
        )
    return records


def load_trusted_intents_from_jsonl(path: Path) -> List[TrustedIntent]:
    """Load trusted intent evidence from JSONL.

    Each row must contain ``intent_id``, ``label``, and ``texts``. ``route`` and
    ``metadata`` are optional.
    """
    intents: List[TrustedIntent] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        raw = json.loads(text)
        intent_id = _stringify_value(raw.get("intent_id"))
        label = _stringify_value(raw.get("label"))
        texts = raw.get("texts")
        if not intent_id:
            raise ValueError(f"Missing intent_id at {path}:{line_number}")
        if not label:
            raise ValueError(f"Missing label at {path}:{line_number}")
        if not isinstance(texts, list) or not all(isinstance(item, str) for item in texts):
            raise ValueError(f"Invalid texts at {path}:{line_number}: expected list of strings")
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid metadata at {path}:{line_number}: expected object")
        intents.append(
            TrustedIntent(
                intent_id=intent_id,
                label=label,
                texts=list(texts),
                route=_stringify_value(raw.get("route")) or None,
                metadata=metadata,
            )
        )
    return intents


def build_tfidf_vectors(text_by_id: Mapping[str, str]) -> Dict[str, SparseVector]:
    """Build normalized sparse TF-IDF vectors for a small or medium corpus."""
    token_counts: Dict[str, Counter[str]] = {
        item_id: Counter(tokenize(text)) for item_id, text in text_by_id.items()
    }
    doc_freq: Counter[str] = Counter()
    for counts in token_counts.values():
        doc_freq.update(counts.keys())

    total_docs = max(1, len(text_by_id))
    vectors: Dict[str, SparseVector] = {}
    for item_id, counts in token_counts.items():
        total_tokens = sum(counts.values())
        if total_tokens == 0:
            vectors[item_id] = {}
            continue
        weighted: SparseVector = {}
        for token, count in counts.items():
            tf = count / total_tokens
            idf = math.log((1 + total_docs) / (1 + doc_freq[token])) + 1
            weighted[token] = tf * idf
        vectors[item_id] = _normalize_vector(weighted)
    return vectors


def dense_vectors_to_sparse(
    item_ids: Sequence[str],
    embeddings: Sequence[Sequence[float]],
) -> Dict[str, SparseVector]:
    """Adapt dense embedding vectors to the sparse-vector clustering API."""
    if len(item_ids) != len(embeddings):
        raise ValueError("item_ids and embeddings must have the same length")
    vectors: Dict[str, SparseVector] = {}
    for item_id, embedding in zip(item_ids, embeddings):
        vectors[item_id] = _normalize_vector(
            {f"dim_{index}": float(value) for index, value in enumerate(embedding)}
        )
    return vectors


def cosine_similarity(left: SparseVector, right: SparseVector) -> float:
    """Return cosine similarity for normalized sparse vectors."""
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


def cluster_records(
    records: Sequence[IntentRecord],
    similarity_threshold: float = 0.35,
    max_representatives: int = 3,
    vectors: Optional[Mapping[str, SparseVector]] = None,
) -> List[IntentCluster]:
    """Cluster records by route using greedy sparse-vector similarity.

    The implementation is intentionally dependency-light. For high-volume
    production clustering, tenant code can provide external embedding vectors
    through ``vectors`` and still reuse the same cluster and match structures.
    """
    if not records:
        return []

    vector_by_id = dict(vectors) if vectors is not None else build_tfidf_vectors(
        {record.record_id: record.text for record in records}
    )
    records_by_route: Dict[str, List[IntentRecord]] = defaultdict(list)
    for record in records:
        records_by_route[record.route].append(record)
    cluster_prefix_by_route = _cluster_prefixes_by_route(records_by_route)

    clusters: List[IntentCluster] = []
    for route in sorted(records_by_route):
        route_records = sorted(records_by_route[route], key=lambda item: item.record_id)
        route_clusters: List[List[str]] = []
        centroids: List[SparseVector] = []

        for record in route_records:
            vector = vector_by_id.get(record.record_id, {})
            best_index, best_score = _best_centroid(vector, centroids)
            if best_index is not None and best_score >= similarity_threshold:
                route_clusters[best_index].append(record.record_id)
                centroids[best_index] = _average_vectors(route_clusters[best_index], vector_by_id)
            else:
                route_clusters.append([record.record_id])
                centroids.append(vector)

        for index, record_ids in enumerate(route_clusters, start=1):
            cluster_id = f"{cluster_prefix_by_route[route]}-{index:03d}"
            representatives = _representative_ids(record_ids, vector_by_id, max_representatives)
            top_terms = _top_terms(_average_vectors(record_ids, vector_by_id), limit=8)
            clusters.append(
                IntentCluster(
                    cluster_id=cluster_id,
                    route=route,
                    record_ids=record_ids,
                    representative_ids=representatives,
                    top_terms=top_terms,
                )
            )
    assert_unique_cluster_ids(clusters)
    return clusters


def cluster_records_fixed_count(
    records: Sequence[IntentRecord],
    cluster_count: int,
    max_representatives: int = 3,
    vectors: Optional[Mapping[str, SparseVector]] = None,
    max_iterations: int = 50,
) -> List[IntentCluster]:
    """Cluster records into an exact, deterministic number of route-local groups.

    Cluster capacity is allocated proportionally across routes, with at least
    one cluster per route. Within each route, deterministic cosine k-means uses
    farthest-first initialization and stable record-id tie breaking.
    """
    if not records:
        return []
    if cluster_count < 1:
        raise ValueError("cluster_count must be at least 1")
    if cluster_count > len(records):
        raise ValueError("cluster_count cannot exceed the number of records")

    records_by_route: Dict[str, List[IntentRecord]] = defaultdict(list)
    for record in records:
        records_by_route[record.route].append(record)
    if cluster_count < len(records_by_route):
        raise ValueError(
            "cluster_count must be at least the number of distinct routes "
            f"({len(records_by_route)})"
        )

    vector_by_id = dict(vectors) if vectors is not None else build_tfidf_vectors(
        {record.record_id: record.text for record in records}
    )
    allocation = _allocate_cluster_counts(records_by_route, cluster_count)
    cluster_prefix_by_route = _cluster_prefixes_by_route(records_by_route)
    output: List[IntentCluster] = []

    for route in sorted(records_by_route):
        route_records = sorted(records_by_route[route], key=lambda item: item.record_id)
        member_ids = _fixed_count_memberships(
            route_records,
            allocation[route],
            vector_by_id,
            max_iterations=max_iterations,
        )
        for index, record_ids in enumerate(member_ids, start=1):
            cluster_id = f"{cluster_prefix_by_route[route]}-{index:03d}"
            output.append(
                IntentCluster(
                    cluster_id=cluster_id,
                    route=route,
                    record_ids=record_ids,
                    representative_ids=_representative_ids(
                        record_ids,
                        vector_by_id,
                        max_representatives,
                    ),
                    top_terms=_top_terms(
                        _average_vectors(record_ids, vector_by_id),
                        limit=8,
                    ),
                )
            )
    assert_unique_cluster_ids(output)
    return output


def match_clusters_to_trusted_intents(
    clusters: Sequence[IntentCluster],
    records: Sequence[IntentRecord],
    trusted_intents: Sequence[TrustedIntent],
    match_threshold: float = 0.35,
    coverage_policy: Optional[CoveragePolicy] = None,
    vectors: Optional[Mapping[str, SparseVector]] = None,
) -> List[IntentMatch]:
    """Match intent clusters to trusted labeled intent evidence."""
    assert_unique_cluster_ids(clusters)
    policy = coverage_policy or CoveragePolicy(min_match_score=match_threshold)
    if not clusters:
        return []
    if not trusted_intents:
        return [
            IntentMatch(
                cluster_id=cluster.cluster_id,
                status="missing_or_weak_labels",
                score=0.0,
                cluster_size=cluster.size,
                reason="no trusted intents available",
            )
            for cluster in clusters
        ]

    match_texts = build_intent_match_texts(clusters, records, trusted_intents)
    vector_by_key = dict(vectors) if vectors is not None else build_tfidf_vectors(match_texts)
    trusted_by_key = {f"trusted:{intent.intent_id}": intent for intent in trusted_intents}

    matches: List[IntentMatch] = []
    for cluster in clusters:
        cluster_key = f"cluster:{cluster.cluster_id}"
        best_key = None
        best_score = 0.0
        for trusted_key, trusted_intent in trusted_by_key.items():
            if trusted_intent.route is not None and trusted_intent.route != cluster.route:
                continue
            score = cosine_similarity(
                vector_by_key.get(cluster_key, {}),
                vector_by_key.get(trusted_key, {}),
            )
            if score > best_score:
                best_key = trusted_key
                best_score = score

        if best_key is None or best_score < policy.min_match_score:
            matches.append(
                IntentMatch(
                    cluster_id=cluster.cluster_id,
                    status="missing_or_weak_labels",
                    score=round(best_score, 4),
                    cluster_size=cluster.size,
                    reason=(
                        f"best match score {best_score:.4f} is below "
                        f"threshold {policy.min_match_score:.4f}"
                    ),
                )
            )
        else:
            trusted = trusted_by_key[best_key]
            status, reason = _coverage_decision(cluster, trusted, best_score, policy)
            trusted_example_count = _trusted_example_count(trusted)
            trusted_group_count = _trusted_group_count(trusted)
            matches.append(
                IntentMatch(
                    cluster_id=cluster.cluster_id,
                    status=status,
                    score=round(best_score, 4),
                    matched_intent_id=trusted.intent_id,
                    matched_label=trusted.label,
                    cluster_size=cluster.size,
                    trusted_example_count=trusted_example_count,
                    trusted_group_count=trusted_group_count,
                    unlabeled_to_trusted_ratio=_safe_ratio(cluster.size, trusted_example_count),
                    reason=reason,
                )
            )
    return matches


def _allocate_cluster_counts(
    records_by_route: Mapping[str, Sequence[IntentRecord]],
    total_clusters: int,
) -> Dict[str, int]:
    routes = sorted(records_by_route)
    allocation = {route: 1 for route in routes}
    remaining = total_clusters - len(routes)
    while remaining > 0:
        candidates = [
            route
            for route in routes
            if allocation[route] < len(records_by_route[route])
        ]
        if not candidates:
            break
        route = max(
            candidates,
            key=lambda item: (
                len(records_by_route[item]) / allocation[item],
                len(records_by_route[item]),
                item,
            ),
        )
        allocation[route] += 1
        remaining -= 1
    return allocation


def _fixed_count_memberships(
    records: Sequence[IntentRecord],
    cluster_count: int,
    vectors: Mapping[str, SparseVector],
    max_iterations: int,
) -> List[List[str]]:
    record_ids = [record.record_id for record in records]
    centroid_ids = [record_ids[0]]
    while len(centroid_ids) < cluster_count:
        candidate = min(
            (record_id for record_id in record_ids if record_id not in centroid_ids),
            key=lambda record_id: (
                max(
                    cosine_similarity(vectors.get(record_id, {}), vectors.get(existing, {}))
                    for existing in centroid_ids
                ),
                record_id,
            ),
        )
        centroid_ids.append(candidate)

    centroids = [vectors.get(record_id, {}) for record_id in centroid_ids]
    assignments: Optional[List[int]] = None
    for _ in range(max_iterations):
        next_assignments = [
            max(
                range(cluster_count),
                key=lambda index: (
                    cosine_similarity(vectors.get(record_id, {}), centroids[index]),
                    -index,
                ),
            )
            for record_id in record_ids
        ]
        _fill_empty_clusters(next_assignments, record_ids, centroids, vectors)
        if next_assignments == assignments:
            break
        assignments = next_assignments
        centroids = [
            _average_vectors(
                [
                    record_id
                    for record_id, assignment in zip(record_ids, assignments)
                    if assignment == index
                ],
                vectors,
            )
            for index in range(cluster_count)
        ]

    assert assignments is not None
    memberships = [
        sorted(
            record_id
            for record_id, assignment in zip(record_ids, assignments)
            if assignment == index
        )
        for index in range(cluster_count)
    ]
    memberships.sort(key=lambda members: members[0])
    return memberships


def _fill_empty_clusters(
    assignments: List[int],
    record_ids: Sequence[str],
    centroids: Sequence[SparseVector],
    vectors: Mapping[str, SparseVector],
) -> None:
    counts = Counter(assignments)
    for empty_index in (index for index in range(len(centroids)) if counts[index] == 0):
        donor_position = min(
            (
                position
                for position, assignment in enumerate(assignments)
                if counts[assignment] > 1
            ),
            key=lambda position: (
                cosine_similarity(
                    vectors.get(record_ids[position], {}),
                    centroids[assignments[position]],
                ),
                record_ids[position],
            ),
        )
        donor_index = assignments[donor_position]
        assignments[donor_position] = empty_index
        counts[donor_index] -= 1
        counts[empty_index] += 1


def build_intent_inventory(
    records: Sequence[IntentRecord],
    trusted_intents: Sequence[TrustedIntent],
    similarity_threshold: float = 0.35,
    match_threshold: float = 0.35,
    coverage_policy: Optional[CoveragePolicy] = None,
    cluster_vectors: Optional[Mapping[str, SparseVector]] = None,
    match_vectors: Optional[Mapping[str, SparseVector]] = None,
) -> IntentInventory:
    """Build clusters and trusted-intent match decisions for trace records."""
    clusters = cluster_records(
        records,
        similarity_threshold=similarity_threshold,
        vectors=cluster_vectors,
    )
    matches = match_clusters_to_trusted_intents(
        clusters,
        records,
        trusted_intents,
        match_threshold=match_threshold,
        coverage_policy=coverage_policy,
        vectors=match_vectors,
    )
    return IntentInventory(clusters=clusters, matches=matches)


def build_intent_match_texts(
    clusters: Sequence[IntentCluster],
    records: Sequence[IntentRecord],
    trusted_intents: Sequence[TrustedIntent],
) -> Dict[str, str]:
    """Build comparable cluster and trusted-intent texts for matching."""
    assert_unique_cluster_ids(clusters)
    record_by_id = {record.record_id: record for record in records}
    match_texts = {
        f"cluster:{cluster.cluster_id}": " ".join(
            record_by_id[record_id].text for record_id in cluster.record_ids if record_id in record_by_id
        )
        for cluster in clusters
    }
    match_texts.update(
        {
            f"trusted:{intent.intent_id}": " ".join([intent.label] + list(intent.texts))
            for intent in trusted_intents
        }
    )
    return match_texts


def cluster_to_dict(cluster: IntentCluster) -> Dict[str, Any]:
    """Serialize an intent cluster for JSONL reports."""
    return {
        "cluster_id": cluster.cluster_id,
        "route": cluster.route,
        "size": cluster.size,
        "record_ids": list(cluster.record_ids),
        "representative_ids": list(cluster.representative_ids),
        "top_terms": list(cluster.top_terms),
    }


def match_to_dict(match: IntentMatch) -> Dict[str, Any]:
    """Serialize an intent match for JSONL reports."""
    return {
        "cluster_id": match.cluster_id,
        "status": match.status,
        "score": match.score,
        "matched_intent_id": match.matched_intent_id,
        "matched_label": match.matched_label,
        "cluster_size": match.cluster_size,
        "trusted_example_count": match.trusted_example_count,
        "trusted_group_count": match.trusted_group_count,
        "unlabeled_to_trusted_ratio": match.unlabeled_to_trusted_ratio,
        "reason": match.reason,
    }


def _coverage_decision(
    cluster: IntentCluster,
    trusted: TrustedIntent,
    score: float,
    policy: CoveragePolicy,
) -> Tuple[str, str]:
    trusted_examples = _trusted_example_count(trusted)
    trusted_groups = _trusted_group_count(trusted)
    ratio = _safe_ratio(cluster.size, trusted_examples)

    if trusted_examples < policy.min_trusted_examples:
        return (
            "needs_more_trusted_examples",
            f"trusted examples {trusted_examples} below minimum {policy.min_trusted_examples}",
        )
    if trusted_groups < policy.min_trusted_groups:
        return (
            "needs_more_trusted_examples",
            f"trusted groups {trusted_groups} below minimum {policy.min_trusted_groups}",
        )
    if (
        policy.large_cluster_size > 0
        and cluster.size >= policy.large_cluster_size
        and trusted_examples < policy.min_trusted_examples_for_large_cluster
    ):
        return (
            "needs_more_trusted_examples",
            "large cluster has insufficient trusted examples: "
            f"{trusted_examples} below {policy.min_trusted_examples_for_large_cluster}",
        )
    if (
        policy.max_unlabeled_to_trusted_ratio is not None
        and ratio is not None
        and ratio > policy.max_unlabeled_to_trusted_ratio
    ):
        return (
            "needs_more_trusted_examples",
            "unlabeled-to-trusted ratio "
            f"{ratio:.2f} exceeds {policy.max_unlabeled_to_trusted_ratio:.2f}",
        )
    return ("matched_trusted_intent", f"coverage thresholds satisfied at score {score:.4f}")


def _trusted_example_count(intent: TrustedIntent) -> int:
    for key in ("trusted_example_count", "example_count", "case_count"):
        value = _coerce_int(intent.metadata.get(key))
        if value is not None:
            return value
    return len(intent.texts)


def _trusted_group_count(intent: TrustedIntent) -> int:
    for key in ("trusted_group_count", "group_count", "thread_count"):
        value = _coerce_int(intent.metadata.get(key))
        if value is not None:
            return value
    for key in ("trusted_group_ids", "group_ids", "thread_ids"):
        value = intent.metadata.get(key)
        if isinstance(value, list):
            return len({str(item) for item in value})
    return 0


def _safe_ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _get_path(raw: Any, path: Optional[str]) -> Any:
    if not path:
        return None
    value = raw
    for part in path.split("."):
        if isinstance(value, Mapping):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            index = int(part)
            value = value[index] if index < len(value) else None
        else:
            return None
    return value


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return normalize_text(" ".join(_stringify_value(item) for item in value))
    if isinstance(value, Mapping):
        return normalize_text(json.dumps(value, sort_keys=True))
    return normalize_text(str(value))


def _normalize_vector(vector: SparseVector) -> SparseVector:
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm == 0:
        return {}
    return {token: value / norm for token, value in vector.items()}


def _average_vectors(record_ids: Iterable[str], vector_by_id: Mapping[str, SparseVector]) -> SparseVector:
    accumulator: Counter[str] = Counter()
    count = 0
    for record_id in record_ids:
        count += 1
        accumulator.update(vector_by_id.get(record_id, {}))
    if count == 0:
        return {}
    return _normalize_vector({token: value / count for token, value in accumulator.items()})


def _best_centroid(vector: SparseVector, centroids: Sequence[SparseVector]) -> Tuple[Optional[int], float]:
    best_index = None
    best_score = 0.0
    for index, centroid in enumerate(centroids):
        score = cosine_similarity(vector, centroid)
        if score > best_score:
            best_index = index
            best_score = score
    return best_index, best_score


def _representative_ids(
    record_ids: Sequence[str],
    vector_by_id: Mapping[str, SparseVector],
    limit: int,
) -> List[str]:
    scored: List[Tuple[float, str]] = []
    for record_id in record_ids:
        vector = vector_by_id.get(record_id, {})
        if len(record_ids) == 1:
            score = 1.0
        else:
            score = sum(
                cosine_similarity(vector, vector_by_id.get(other_id, {}))
                for other_id in record_ids
                if other_id != record_id
            ) / max(1, len(record_ids) - 1)
        scored.append((score, record_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [record_id for _, record_id in scored[:limit]]


def _top_terms(vector: SparseVector, limit: int) -> List[str]:
    return [
        token
        for token, _ in sorted(vector.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "default"


def _cluster_prefixes_by_route(
    records_by_route: Mapping[str, Sequence[IntentRecord]],
) -> Dict[str, str]:
    """Keep legacy route slugs unless exact route bytes collide on one slug."""
    routes_by_slug: Dict[str, List[str]] = defaultdict(list)
    for route in records_by_route:
        routes_by_slug[_slug(route)].append(route)

    prefixes: Dict[str, str] = {}
    for slug, routes in routes_by_slug.items():
        if len(routes) == 1:
            prefixes[routes[0]] = slug
            continue
        for route in routes:
            digest = hashlib.sha256(route.encode("utf-8")).hexdigest()[:12]
            prefixes[route] = f"{slug}-{digest}"
    if len(set(prefixes.values())) != len(prefixes):
        raise ValueError("route-derived cluster prefixes must be unique")
    return prefixes


def assert_unique_cluster_ids(clusters: Sequence[IntentCluster]) -> None:
    """Reject duplicate cluster identities before any keyed conversion."""
    seen: Dict[str, str] = {}
    for cluster in clusters:
        if cluster.cluster_id in seen:
            raise ValueError(
                f"duplicate cluster_id '{cluster.cluster_id}' for routes "
                f"'{seen[cluster.cluster_id]}' and '{cluster.route}'"
            )
        seen[cluster.cluster_id] = cluster.route
