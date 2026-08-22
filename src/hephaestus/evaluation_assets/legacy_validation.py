# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Strict semantic validation for explicitly adopted legacy releases."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.datasets.evaluation_assets import (
    SCOREABLE_EXPECTED_KEYS,
    filter_synthetic_cases,
    validate_fapo_case,
)
from src.hephaestus.evaluation_assets.input_contract import (
    effective_route,
    validate_input_records,
)
from src.hephaestus.evaluation_assets.stage_three_contract import (
    GuidelineIdentityProfile,
    TrustedIntentTextProfile,
    replay_legacy_stage_three,
    replay_native_stage_three,
    validate_native_guideline_rows,
)

_MATCH_STATUSES = {
    "matched_trusted_intent",
    "needs_more_trusted_examples",
    "missing_or_weak_labels",
}
_TRUST_TIERS = {
    "trusted": "trusted_feedback",
    "inferred": "inferred_from_trusted_feedback",
}
_SYNTHETIC_TRUST_TIERS = frozenset(
    {"synthetic", "synthetic_from_trusted_rubric"}
)
_SOURCE_NAMES = {
    "trusted": "feedback_trace",
    "inferred": "unlabeled_trace",
    "synthetic": "synthetic_generation",
}


def _artifact_profile(
    artifact_profiles: Mapping[Any, str],
    stage_value: str,
) -> str:
    for stage, profile in artifact_profiles.items():
        if getattr(stage, "value", stage) == stage_value:
            return profile
    raise ValueError("legacy artifact profile is incomplete")


def validate_legacy_stage_semantics(
    layout: Any,
    artifact_profiles: Mapping[Any, str],
    *,
    artifact_snapshot: Mapping[Path, bytes],
    native_stage_three_identity_profile: GuidelineIdentityProfile = "historical_v1",
    native_stage_three_text_profile: TrustedIntentTextProfile = "historical_v1",
) -> None:
    """Cross-validate the full historical stage graph before adoption writes."""
    feedback = _rows(
        layout,
        layout.historical_feedback_path,
        artifact_snapshot,
    )
    unlabeled = _rows(
        layout,
        layout.historical_unlabeled_path,
        artifact_snapshot,
    )
    validate_input_records(
        feedback,
        labeled=True,
        path=layout.historical_feedback_path,
    )
    validate_input_records(
        unlabeled,
        labeled=False,
        path=layout.historical_unlabeled_path,
    )
    feedback_by_id = _unique_by(feedback, "record_id")
    unlabeled_by_id = _unique_by(unlabeled, "record_id")
    normalized = _rows(
        layout,
        layout.artifact_path("prepared_inputs", "normalized_feedback.jsonl"),
        artifact_snapshot,
    )
    intents = _rows(
        layout,
        layout.artifact_path("prepared_inputs", "intent_records.jsonl"),
        artifact_snapshot,
    )
    validate_input_records(
        normalized,
        labeled=True,
        path=layout.artifact_path(
            "prepared_inputs", "normalized_feedback.jsonl"
        ),
    )
    validate_input_records(
        intents,
        labeled=False,
        path=layout.artifact_path("prepared_inputs", "intent_records.jsonl"),
    )
    normalized_by_id = _unique_by(normalized, "record_id")
    intents_by_id = _unique_by(intents, "record_id")
    _validate_prepared_identity(feedback_by_id, normalized_by_id, labeled=True)
    _validate_prepared_identity(unlabeled_by_id, intents_by_id, labeled=False)

    stage_three_profile = _artifact_profile(
        artifact_profiles,
        "rubric_extraction",
    )
    trusted_intents, trusted_cases = _validate_stage_three(
        layout,
        stage_three_profile,
        normalized_by_id,
        artifact_snapshot,
        identity_profile=native_stage_three_identity_profile,
        text_profile=native_stage_three_text_profile,
    )
    clusters = _validate_clusters(layout, intents_by_id, artifact_snapshot)
    matches = _validate_matches(
        layout,
        clusters,
        trusted_intents,
        artifact_snapshot,
    )
    _validate_queue(
        layout,
        clusters,
        matches,
        intents_by_id,
        artifact_snapshot,
    )
    inferred_cases = _validate_inference(
        layout,
        clusters,
        matches,
        trusted_intents,
        intents_by_id,
        artifact_snapshot,
    )
    synthetic_cases = _validate_synthetic(
        layout,
        clusters,
        matches,
        [*trusted_cases, *inferred_cases],
        artifact_snapshot,
    )
    _validate_splits(
        layout,
        trusted_cases,
        inferred_cases,
        synthetic_cases,
        artifact_snapshot,
    )


def _validate_prepared_identity(
    source_by_id: Mapping[str, Mapping[str, Any]],
    prepared_by_id: Mapping[str, Mapping[str, Any]],
    *,
    labeled: bool,
) -> None:
    if set(source_by_id) != set(prepared_by_id):
        raise ValueError("prepared record identities differ from source records")
    common_fields = (
        "schema_version",
        "group_id",
        "task_type",
        "user_input",
        "conversation_context",
        "tool_calls",
        "runtime",
        "metadata",
    )
    for record_id, source in source_by_id.items():
        prepared = prepared_by_id[record_id]
        for field in common_fields:
            if prepared.get(field) != source.get(field):
                raise ValueError("prepared record content differs from source")
        if effective_route(prepared) != effective_route(source):
            raise ValueError("prepared route differs from source")
        request_id = source.get("request_id", record_id)
        if prepared.get("request_id") != request_id:
            raise ValueError("prepared request identity differs from source")
        if labeled:
            for field in ("assistant_output", "feedback"):
                if prepared.get(field) != source.get(field):
                    raise ValueError("prepared feedback differs from source")
        else:
            _nonempty_string(prepared, "canonical_intent_text")
            tool_names = prepared.get("tool_names")
            if not isinstance(tool_names, list) or not all(
                isinstance(item, str) and item for item in tool_names
            ):
                raise ValueError("prepared intent tool names are invalid")


def _validate_stage_three(
    layout: Any,
    profile: str,
    feedback_by_id: Mapping[str, Mapping[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
    *,
    identity_profile: GuidelineIdentityProfile,
    text_profile: TrustedIntentTextProfile,
) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]]]:
    stage = "rubric_extraction"
    trusted_intent_rows = _rows(
        layout,
        layout.artifact_path(stage, "trusted_intents.jsonl"),
        artifact_snapshot,
    )
    trusted_intents = _unique_by(trusted_intent_rows, "intent_id")
    trusted_cases = _case_rows(
        layout,
        layout.artifact_path(stage, "trusted_cases.jsonl"),
        artifact_snapshot,
    )
    if profile == "legacy":
        rubric_rows = _rows(
            layout,
            layout.artifact_path(stage, "feedback_rubrics.jsonl"),
            artifact_snapshot,
        )
        replayed = replay_legacy_stage_three(
            list(feedback_by_id.values()),
            rubric_rows,
            asset_id=layout.asset_id,
        )
        if (
            trusted_intent_rows != replayed["trusted_intents"]
            or trusted_cases != replayed["trusted_cases"]
        ):
            raise ValueError("legacy Stage 3 derivatives do not reproduce")
        return trusted_intents, trusted_cases
    for row in trusted_intent_rows:
        _nonempty_string(row, "label")
        _string_list(row, "texts", require_nonempty=True)
        if "route" in row and row["route"] is not None:
            _nonempty_string(row, "route")
        metadata = _object(row, "metadata")
        source_ids = _string_list(metadata, "source_record_ids", require_nonempty=True)
        if not set(source_ids) <= set(feedback_by_id):
            raise ValueError("trusted intent references unknown feedback")
        for field in ("trusted_example_count", "trusted_group_count"):
            if field in metadata:
                _integer(metadata, field, minimum=0)
        if "feedback_polarities" in metadata:
            _string_list(metadata, "feedback_polarities")

    trusted_cases_by_id = _unique_by(trusted_cases, "case_id")
    expected_case_ids = {f"feedback-{record_id}" for record_id in feedback_by_id}
    if set(trusted_cases_by_id) != expected_case_ids:
        raise ValueError("trusted cases do not exactly cover feedback")
    for record_id, feedback in feedback_by_id.items():
        case = trusted_cases_by_id[f"feedback-{record_id}"]
        metadata = _case_metadata(case)
        if (
            metadata.get("trust_tier") != _TRUST_TIERS["trusted"]
            or metadata.get("source") != _SOURCE_NAMES["trusted"]
            or metadata.get("group_id") != feedback["group_id"]
            or metadata.get("request_id") != feedback.get("request_id", record_id)
            or case.get("task_type") != feedback["task_type"]
        ):
            raise ValueError("trusted case provenance is inconsistent")
        _validate_expected(case["expected"])

    evidence_rows = _rows(
        layout,
        layout.artifact_path(stage, "feedback_evidence.jsonl"),
        artifact_snapshot,
    )
    evidence = _unique_by(evidence_rows, "record_id")
    if set(evidence) != set(feedback_by_id):
        raise ValueError("feedback evidence does not exactly cover feedback")
    for record_id, row in evidence.items():
        source = feedback_by_id[record_id]
        if (
            row.get("group_id") != source["group_id"]
            or row.get("task_type") != source["task_type"]
            or row.get("route") != effective_route(source)
            or row.get("evidence_source") != "trusted_feedback"
        ):
            raise ValueError("feedback evidence provenance is inconsistent")
        _nonempty_string(row, "intent_label")
        _number(row, "confidence", minimum=0.0, maximum=1.0)
        observations = _mapping_list(row, "observations")
        for observation in observations:
            for field in (
                "claim",
                "evidence_type",
                "evidence_pointer",
                "polarity",
            ):
                _nonempty_string(observation, field)
        _string_list(row, "requested_corrections")
        _string_list(row, "uncertainties")
        _nonempty_string(row, "guideline_provider")
        _nonempty_string(row, "guideline_model")

    candidate_rows = _rows(
        layout,
        layout.artifact_path(stage, "candidate_guidelines.jsonl"),
        artifact_snapshot,
    )
    for row in candidate_rows:
        _nonempty_string(row, "intent_label")
        _nonempty_string(row, "description")
        _nonempty_string(row, "route")
        _number(row, "confidence", minimum=0.0, maximum=1.0)
        source_ids = _string_list(row, "source_record_ids", require_nonempty=True)
        if not set(source_ids) <= set(evidence) or any(
            evidence[source_id]["route"] != row.get("route")
            for source_id in source_ids
        ):
            raise ValueError("candidate guideline references unknown evidence")
        _validate_candidate_criteria(row)
        _object(row, "tool_expectations")
        _nullable_string(row, "reference_output")
        for field in ("conflicts", "uncertainties"):
            if field in row:
                _string_list(row, field)

    guideline_rows = _rows(
        layout,
        layout.artifact_path(stage, "evaluation_guidelines.jsonl"),
        artifact_snapshot,
    )
    guidelines = _unique_by(guideline_rows, "guideline_id")
    represented: set[str] = set()
    for row in guideline_rows:
        _nonempty_string(row, "intent_label")
        _nonempty_string(row, "description")
        _number(row, "confidence", minimum=0.0, maximum=1.0)
        source_ids = _string_list(row, "source_record_ids", require_nonempty=True)
        if not set(source_ids) <= set(evidence) or any(
            evidence[source_id]["route"] != row.get("route")
            for source_id in source_ids
        ):
            raise ValueError("evaluation guideline references unknown evidence")
        represented.update(source_ids)
        _nonempty_string(row, "route")
        support = _object(row, "support")
        trusted_examples = _integer(support, "trusted_example_count", minimum=1)
        trusted_groups = _integer(support, "trusted_group_count", minimum=1)
        if trusted_examples != len(source_ids) or trusted_groups != len(
            {feedback_by_id[source_id]["group_id"] for source_id in source_ids}
        ):
            raise ValueError("evaluation guideline support is inconsistent")
        criteria = row.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            raise ValueError("evaluation guideline criteria are missing")
        for order, criterion in enumerate(criteria, start=1):
            if not isinstance(criterion, Mapping):
                raise ValueError("evaluation guideline criterion is invalid")
            _nonempty_string(criterion, "criterion_id")
            _nonempty_string(criterion, "statement")
            _validate_guideline_criterion(criterion, expected_order=order)
            criterion_sources = _string_list(
                criterion, "source_record_ids", require_nonempty=True
            )
            if not set(criterion_sources) <= set(source_ids):
                raise ValueError("criterion source evidence is inconsistent")
        _string_list(row, "conflicts")
        _string_list(row, "uncertainties")
        _object(row, "tool_expectations")
        _nullable_string(row, "reference_output")
        for field in (
            "unknown_policy",
            "activation_status",
            "calibration_status",
            "guideline_provider",
            "guideline_model",
            "oracle_version",
        ):
            _nonempty_string(row, field)
    if represented != set(feedback_by_id):
        raise ValueError("evaluation guidelines do not exactly cover evidence")
    if set(trusted_intents) != set(guidelines):
        raise ValueError("trusted intents do not exactly mirror guidelines")
    for intent_id, intent in trusted_intents.items():
        guideline = guidelines[intent_id]
        metadata = _object(intent, "metadata")
        if (
            metadata.get("evaluation_guideline_id") != intent_id
            or set(_string_list(metadata, "source_record_ids"))
            != set(_string_list(guideline, "source_record_ids"))
            or intent.get("route") != guideline.get("route")
            or intent.get("label") != guideline.get("intent_label")
            or metadata.get("trusted_example_count")
            != guideline["support"]["trusted_example_count"]
            or metadata.get("trusted_group_count")
            != guideline["support"]["trusted_group_count"]
        ):
            raise ValueError("trusted intent guideline lineage is inconsistent")
    guideline_ids_by_source = {
        record_id: {
            guideline_id
            for guideline_id, guideline in guidelines.items()
            if record_id in guideline["source_record_ids"]
        }
        for record_id in feedback_by_id
    }
    for case in trusted_cases:
        expected = case["expected"]
        ids = _string_list(expected, "evaluation_guideline_ids", require_nonempty=True)
        source_id = str(case["case_id"])[len("feedback-") :]
        if set(ids) != guideline_ids_by_source[source_id]:
            raise ValueError("trusted case references unknown guidelines")
        embedded = expected.get("evaluation_guidelines")
        if not isinstance(embedded, list) or embedded != [
            guidelines[guideline_id] for guideline_id in ids
        ]:
            raise ValueError("trusted case guideline payload is inconsistent")
        if (
            expected.get("feedback_polarity")
            != feedback_by_id[source_id]["feedback"]["polarity"]
            or expected.get("label_source")
            != "evaluation_guideline_from_trusted_feedback"
        ):
            raise ValueError("trusted case evidence lineage is inconsistent")
    validate_native_guideline_rows(guideline_rows)
    manifest = _json_object(layout, layout.manifest_path, artifact_snapshot)
    providers = _object(manifest, "providers")
    evidence_provider_pairs = {
        (row["guideline_provider"], row["guideline_model"])
        for row in evidence_rows
    }
    if evidence_provider_pairs != {
        (providers.get("rubric_provider"), providers.get("rubric_model"))
    }:
        raise ValueError("Stage 3 provider evidence differs from the manifest")
    replayed = replay_native_stage_three(
        list(feedback_by_id.values()),
        evidence_rows,
        candidate_rows,
        asset_id=layout.asset_id,
        identity_profile=identity_profile,
        text_profile=text_profile,
    )
    if (
        candidate_rows != replayed["candidates"]
        or guideline_rows != replayed["guidelines"]
        or trusted_intent_rows != replayed["trusted_intents"]
        or trusted_cases != replayed["trusted_cases"]
    ):
        raise ValueError("native Stage 3 derivatives do not reproduce")
    return trusted_intents, trusted_cases


def _validate_clusters(
    layout: Any,
    intents_by_id: Mapping[str, Mapping[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
) -> dict[str, Mapping[str, Any]]:
    rows = _rows(
        layout,
        layout.artifact_path("intent_clustering", "intent_inventory.jsonl"),
        artifact_snapshot,
    )
    clusters = _unique_by(rows, "cluster_id")
    members: list[str] = []
    for row in rows:
        route = _nonempty_string(row, "route")
        record_ids = _string_list(row, "record_ids", require_nonempty=True)
        representatives = _string_list(row, "representative_ids", require_nonempty=True)
        _string_list(row, "top_terms")
        size = _integer(row, "size", minimum=1)
        if size != len(record_ids) or len(set(record_ids)) != len(record_ids):
            raise ValueError("intent cluster size or membership is inconsistent")
        if not set(representatives) <= set(record_ids):
            raise ValueError("cluster representatives are not members")
        if any(
            record_id not in intents_by_id
            or effective_route(intents_by_id[record_id]) != route
            for record_id in record_ids
        ):
            raise ValueError("intent cluster references an incompatible record")
        members.extend(record_ids)
    if Counter(members) != Counter({record_id: 1 for record_id in intents_by_id}):
        raise ValueError("clusters are not an exact partition of intent records")
    return clusters


def _validate_matches(
    layout: Any,
    clusters: Mapping[str, Mapping[str, Any]],
    trusted_intents: Mapping[str, Mapping[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
) -> dict[str, Mapping[str, Any]]:
    rows = _rows(
        layout,
        layout.artifact_path("coverage_decisions", "intent_matches.jsonl"),
        artifact_snapshot,
    )
    matches = _unique_by(rows, "cluster_id")
    if set(matches) != set(clusters):
        raise ValueError("coverage matches do not exactly cover clusters")
    for cluster_id, row in matches.items():
        status = _nonempty_string(row, "status")
        if status not in _MATCH_STATUSES:
            raise ValueError("coverage match status is invalid")
        score = _number(row, "score")
        if not 0.0 <= score <= 1.0:
            raise ValueError("coverage match score is outside its domain")
        if _integer(row, "cluster_size", minimum=1) != _integer(
            clusters[cluster_id], "size", minimum=1
        ):
            raise ValueError("coverage match cluster size is inconsistent")
        matched_id = row.get("matched_intent_id")
        if status == "matched_trusted_intent":
            if not isinstance(matched_id, str) or matched_id not in trusted_intents:
                raise ValueError("matched coverage references an unknown intent")
            if row.get("matched_label") != trusted_intents[matched_id].get("label"):
                raise ValueError("matched coverage label is inconsistent")
        elif matched_id is not None and (
            not isinstance(matched_id, str) or matched_id not in trusted_intents
        ):
            raise ValueError("coverage candidate references an unknown intent")
        for field in ("trusted_example_count", "trusted_group_count"):
            _integer(row, field, minimum=0)
        if row.get("unlabeled_to_trusted_ratio") is not None:
            _number(row, "unlabeled_to_trusted_ratio", minimum=0.0)
    return matches


def _validate_queue(
    layout: Any,
    clusters: Mapping[str, Mapping[str, Any]],
    matches: Mapping[str, Mapping[str, Any]],
    intents: Mapping[str, Mapping[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
) -> None:
    rows = _rows(
        layout,
        layout.artifact_path(
            "coverage_decisions",
            "review_queue/labeling_queue.jsonl",
        ),
        artifact_snapshot,
    )
    seen: set[tuple[str, str]] = set()
    for row in rows:
        cluster_id = _nonempty_string(row, "cluster_id")
        if cluster_id not in clusters or matches[cluster_id]["status"] == "matched_trusted_intent":
            raise ValueError("labeling queue references a covered or unknown cluster")
        trace = row.get("trace")
        if isinstance(trace, Mapping):
            record_id = _nonempty_string(trace, "record_id")
        else:
            record_id = _nonempty_string(row, "record_id")
        key = (cluster_id, record_id)
        if key in seen or record_id not in clusters[cluster_id]["record_ids"]:
            raise ValueError("labeling queue record membership is inconsistent")
        if record_id not in intents:
            raise ValueError("labeling queue references an unknown intent record")
        for field in (
            "cluster_size",
            "sample_rank",
            "samples_from_cluster",
        ):
            if field in row:
                _integer(row, field, minimum=1)
        if "match_score" in row:
            _number(row, "match_score", minimum=0.0, maximum=1.0)
        if "sample_ratio" in row:
            _number(row, "sample_ratio", minimum=0.0, maximum=1.0)
        seen.add(key)


def _validate_inference(
    layout: Any,
    clusters: Mapping[str, Mapping[str, Any]],
    matches: Mapping[str, Mapping[str, Any]],
    trusted_intents: Mapping[str, Mapping[str, Any]],
    intents: Mapping[str, Mapping[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
) -> list[dict[str, Any]]:
    stage = "label_inference"
    matched_clusters = {
        cluster_id
        for cluster_id, row in matches.items()
        if row["status"] == "matched_trusted_intent"
    }
    rubric_rows = _rows(
        layout,
        layout.artifact_path(stage, "inferred_unlabeled_cluster_rubrics.jsonl"),
        artifact_snapshot,
    )
    rubrics = _unique_by(rubric_rows, "cluster_id")
    if set(rubrics) != matched_clusters:
        raise ValueError("inferred rubrics do not exactly cover matched clusters")
    for cluster_id, row in rubrics.items():
        if row.get("label_source") != "inferred_from_trusted_feedback":
            raise ValueError("inferred rubric label source is invalid")
        for field in ("must", "must_not", "should"):
            _string_list(row, field)
        _number(row, "confidence", minimum=0.0, maximum=1.0)
        _mapping_list(row, "deterministic_checks", default_empty=True)
        _object(row, "tool_expectations")
        _nullable_string(row, "reference_output")
        for field in (
            "intent_label",
            "rubric_provider",
            "rubric_model",
            "oracle_version",
            "review_status",
        ):
            _nonempty_string(row, field)

    label_rows = _rows(
        layout,
        layout.artifact_path(stage, "inferred_unlabeled_labels.jsonl"),
        artifact_snapshot,
    )
    labels = _unique_by(label_rows, "record_id")
    expected_records = {
        record_id
        for cluster_id in matched_clusters
        for record_id in clusters[cluster_id]["record_ids"]
    }
    if set(labels) != expected_records:
        raise ValueError("inferred labels do not exactly cover matched records")
    for record_id, row in labels.items():
        cluster_id = _nonempty_string(row, "cluster_id")
        if cluster_id not in matched_clusters or record_id not in clusters[cluster_id]["record_ids"]:
            raise ValueError("inferred label cluster membership is inconsistent")
        if row.get("matched_intent_id") != matches[cluster_id].get("matched_intent_id"):
            raise ValueError("inferred label intent lineage is inconsistent")
        if row.get("review_status") != "review_required":
            raise ValueError("inferred label review state is invalid")
        if _number(row, "match_score", minimum=0.0, maximum=1.0) != _number(
            matches[cluster_id],
            "score",
            minimum=0.0,
            maximum=1.0,
        ):
            raise ValueError("inferred label score is inconsistent")
        _validate_expected(_object(row, "expected"))

    cases = _case_rows(
        layout,
        layout.artifact_path(stage, "inferred_cases.jsonl"),
        artifact_snapshot,
    )
    cases_by_id = _unique_by(cases, "case_id")
    if set(cases_by_id) != {f"inferred-{record_id}" for record_id in expected_records}:
        raise ValueError("inferred cases do not exactly cover inferred labels")
    for record_id in expected_records:
        case = cases_by_id[f"inferred-{record_id}"]
        metadata = _case_metadata(case)
        cluster_id = labels[record_id]["cluster_id"]
        intent = intents[record_id]
        if (
            metadata.get("source") != _SOURCE_NAMES["inferred"]
            or metadata.get("trust_tier") != _TRUST_TIERS["inferred"]
            or metadata.get("source_cluster") != cluster_id
            or metadata.get("matched_intent_id") != matches[cluster_id].get("matched_intent_id")
            or metadata.get("review_status") != "review_required"
            or metadata.get("group_id") != intent["group_id"]
            or metadata.get("request_id") != intent["request_id"]
            or case.get("task_type") != intent["task_type"]
            or case["expected"] != labels[record_id]["expected"]
        ):
            raise ValueError("inferred case provenance is inconsistent")
        if metadata["matched_intent_id"] not in trusted_intents:
            raise ValueError("inferred case references an unknown trusted intent")
        _validate_expected(case["expected"])

    missing_rows = _rows(
        layout,
        layout.artifact_path(stage, "missing_labeled_feedback_clusters.jsonl"),
        artifact_snapshot,
    )
    missing = _unique_by(missing_rows, "cluster_id")
    if set(missing) != set(clusters) - matched_clusters:
        raise ValueError("missing-feedback inventory is inconsistent")
    for cluster_id, row in missing.items():
        if row.get("status") != matches[cluster_id].get("status"):
            raise ValueError("missing-feedback status is inconsistent")
        for field in ("cluster_size", "trusted_example_count", "trusted_group_count"):
            if field in row:
                _integer(row, field, minimum=0)
        if "match_score" in row:
            _number(row, "match_score", minimum=0.0, maximum=1.0)
    return cases


def _validate_synthetic(
    layout: Any,
    clusters: Mapping[str, Mapping[str, Any]],
    matches: Mapping[str, Mapping[str, Any]],
    existing_cases: Sequence[dict[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
) -> list[dict[str, Any]]:
    stage = "synthetic_coverage"
    candidates = _case_rows(
        layout,
        layout.artifact_path(stage, "synthetic_candidates.jsonl"),
        artifact_snapshot,
    )
    rejected = _case_rows(
        layout,
        layout.artifact_path(stage, "rejected_synthetic.jsonl"),
        artifact_snapshot,
    )
    accepted = _case_rows(
        layout,
        layout.artifact_path(stage, "synthetic_cases.jsonl"),
        artifact_snapshot,
    )
    _unique_by(candidates, "case_id")
    rejected_by_id = _unique_by(rejected, "case_id")
    accepted_by_id = _unique_by(accepted, "case_id")
    if set(accepted_by_id) & set(rejected_by_id):
        raise ValueError("synthetic accepted and rejected sets overlap")
    matched = {
        cluster_id
        for cluster_id, row in matches.items()
        if row["status"] == "matched_trusted_intent"
    }
    for case in candidates + rejected + accepted:
        metadata = _case_metadata(case)
        cluster_id = metadata.get("source_cluster")
        if (
            metadata.get("source") != _SOURCE_NAMES["synthetic"]
            or metadata.get("trust_tier") not in _SYNTHETIC_TRUST_TIERS
            or not isinstance(cluster_id, str)
            or cluster_id not in clusters
            or cluster_id not in matched
            or metadata.get("review_status") != "review_required"
        ):
            raise ValueError("synthetic case provenance is inconsistent")
        _validate_expected(case["expected"])
    issues = _rows(
        layout,
        layout.artifact_path(stage, "synthetic_filter_issues.jsonl"),
        artifact_snapshot,
    )
    for row in issues:
        case_id = _nonempty_string(row, "case_id")
        if case_id not in rejected_by_id:
            raise ValueError("synthetic filter issue references a non-rejected case")
        _nonempty_string(row, "code")
        _nonempty_string(row, "message")
    inherited = _inherited_synthetic_cases(
        layout,
        matches,
        artifact_snapshot,
    )
    filtered = filter_synthetic_cases(
        candidates,
        existing_cases=[*existing_cases, *inherited],
    )
    expected_issues = [
        {
            "case_id": issue.case_id,
            "code": issue.code,
            "message": issue.message,
        }
        for issue in filtered.issues
    ]
    expected_accepted = [*inherited, *filtered.accepted]
    if (
        [_canonical(row) for row in rejected]
        != [_canonical(row) for row in filtered.rejected]
        or [_canonical(row) for row in issues]
        != [_canonical(row) for row in expected_issues]
        or [_canonical(row) for row in accepted]
        != [_canonical(row) for row in expected_accepted]
    ):
        raise ValueError("synthetic filter artifacts do not reproduce")
    candidate_partition = [*filtered.accepted, *filtered.rejected]
    if Counter(_canonical(row) for row in candidates) != Counter(
        _canonical(row) for row in candidate_partition
    ):
        raise ValueError("synthetic filtering is not an exact partition")
    return accepted


def _inherited_synthetic_cases(
    layout: Any,
    matches: Mapping[str, Mapping[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
) -> list[dict[str, Any]]:
    """Reconstruct the exact keep-mode parent cases Stage 7 would retain."""
    if layout.lineage_path not in artifact_snapshot:
        return []
    lineage = _json_object(layout, layout.lineage_path, artifact_snapshot)
    if lineage.get("clustering_mode") != "keep":
        return []
    matches_path = (
        layout.historical_parent_snapshot / "parent_intent_matches.jsonl"
    )
    synthetic_path = (
        layout.historical_parent_snapshot / "parent_synthetic_cases.jsonl"
    )
    if matches_path not in artifact_snapshot or synthetic_path not in artifact_snapshot:
        raise ValueError("keep-mode synthetic snapshot is incomplete")
    previous_rows = _rows(layout, matches_path, artifact_snapshot)
    previous = _unique_by(previous_rows, "cluster_id")
    changed = {
        cluster_id
        for cluster_id, match in matches.items()
        if cluster_id not in previous
        or previous[cluster_id].get("status") != match.get("status")
        or previous[cluster_id].get("matched_intent_id")
        != match.get("matched_intent_id")
    }
    retained: list[dict[str, Any]] = []
    for case in _case_rows(layout, synthetic_path, artifact_snapshot):
        metadata = _case_metadata(case)
        cluster_id = metadata.get("source_cluster")
        if (
            isinstance(cluster_id, str)
            and cluster_id not in changed
            and cluster_id in matches
            and matches[cluster_id].get("status") == "matched_trusted_intent"
        ):
            copied = dict(case)
            copied_metadata = dict(metadata)
            copied_metadata["dataset_version"] = layout.asset_id
            copied["metadata"] = copied_metadata
            retained.append(copied)
    return retained


def _validate_splits(
    layout: Any,
    trusted_cases: Sequence[Mapping[str, Any]],
    inferred_cases: Sequence[Mapping[str, Any]],
    synthetic_cases: Sequence[Mapping[str, Any]],
    artifact_snapshot: Mapping[Path, bytes],
) -> None:
    stage = "dataset_splits"
    source_by_tier = {
        "trusted": _unique_by(trusted_cases, "case_id"),
        "inferred": _unique_by(inferred_cases, "case_id"),
        "synthetic": _unique_by(synthetic_cases, "case_id"),
    }
    split_rows: dict[str, list[dict[str, Any]]] = {}
    for split in ("train", "validation", "test"):
        components: list[dict[str, Any]] = []
        for tier in ("trusted", "inferred", "synthetic"):
            rows = _case_rows(
                layout,
                layout.artifact_path(stage, f"{split}_{tier}.jsonl"),
                artifact_snapshot,
            )
            _unique_by(rows, "case_id")
            for case in rows:
                case_id = case["case_id"]
                trust_tier = _case_metadata(case).get("trust_tier")
                tier_matches = (
                    trust_tier in _SYNTHETIC_TRUST_TIERS
                    if tier == "synthetic"
                    else trust_tier == _TRUST_TIERS[tier]
                )
                if (
                    not tier_matches
                    or case_id not in source_by_tier[tier]
                    or case != source_by_tier[tier][case_id]
                ):
                    raise ValueError("split component provenance is inconsistent")
            split_rows[f"{split}_{tier}"] = rows
            components.extend(rows)
        combined = _case_rows(
            layout,
            layout.artifact_path(stage, f"{split}.jsonl"),
            artifact_snapshot,
        )
        _unique_by(combined, "case_id")
        if Counter(_canonical(row) for row in combined) != Counter(
            _canonical(row) for row in components
        ):
            raise ValueError("combined split differs from its components")
        split_rows[split] = combined

    group_sets = {
        split: {_case_group(case) for case in split_rows[split]}
        for split in ("train", "validation", "test")
    }
    if any(
        group_sets[left] & group_sets[right]
        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))
    ):
        raise ValueError("group identity crosses train validation or test")
    standard_ids = [
        str(case["case_id"])
        for split in ("train", "validation", "test")
        for case in split_rows[split]
    ]
    if len(standard_ids) != len(set(standard_ids)):
        raise ValueError("case identity crosses standard splits")

    regression = _case_rows(
        layout,
        layout.artifact_path(stage, "regression_trusted.jsonl"),
        artifact_snapshot,
    )
    triage = _case_rows(
        layout,
        layout.artifact_path(stage, "triage_hold.jsonl"),
        artifact_snapshot,
    )
    regression_by_id = _unique_by(regression, "case_id")
    triage_by_id = _unique_by(triage, "case_id")
    trusted_source = source_by_tier["trusted"]
    for case_id, case in regression_by_id.items():
        if (
            case_id not in trusted_source
            or case != trusted_source[case_id]
            or _case_metadata(case).get("trust_tier") != _TRUST_TIERS["trusted"]
        ):
            raise ValueError("regression gate contains an untrusted case")
    regression_groups = {_case_group(case) for case in regression}
    if regression_groups & set().union(*group_sets.values()):
        raise ValueError("regression group appears in a standard split")
    for case_id, case in triage_by_id.items():
        metadata = _case_metadata(case)
        if metadata.get("trust_tier") == _TRUST_TIERS["trusted"]:
            raise ValueError("triage hold contains trusted regression evidence")
        if _case_group(case) not in regression_groups:
            raise ValueError("triage case does not conflict with regression")
        trust_tier = metadata.get("trust_tier")
        if trust_tier not in {
            _TRUST_TIERS["inferred"],
            *_SYNTHETIC_TRUST_TIERS,
        }:
            raise ValueError("triage case trust tier is invalid")
        source = source_by_tier[
            "inferred"
            if trust_tier == _TRUST_TIERS["inferred"]
            else "synthetic"
        ]
        if case_id not in source:
            raise ValueError("triage case is not part of the source dataset")

    output_ids = [*standard_ids, *regression_by_id, *triage_by_id]
    if len(output_ids) != len(set(output_ids)):
        raise ValueError("case identity crosses standard or holdout splits")
    all_output_ids = set(output_ids)
    all_source_ids = set().union(*(set(value) for value in source_by_tier.values()))
    if all_output_ids != all_source_ids:
        raise ValueError("dataset splits do not exactly partition source cases")


def _artifact_bytes(
    layout: Any,
    path: Path,
    artifact_snapshot: Mapping[Path, bytes],
) -> bytes:
    try:
        return artifact_snapshot[path]
    except KeyError as exc:
        raise ValueError("legacy semantic authority snapshot is incomplete") from exc


def _rows(
    layout: Any,
    path: Path,
    artifact_snapshot: Mapping[Path, bytes],
) -> list[dict[str, Any]]:
    data = _artifact_bytes(layout, path, artifact_snapshot)
    rows: list[dict[str, Any]] = []
    for line in data.decode("utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line, parse_constant=_reject_json_constant)
        _validate_json_numbers(value)
        if not isinstance(value, dict):
            raise ValueError("artifact row is not an object")
        rows.append(value)
    return rows


def _json_object(
    layout: Any,
    path: Path,
    artifact_snapshot: Mapping[Path, bytes],
) -> dict[str, Any]:
    data = _artifact_bytes(layout, path, artifact_snapshot)
    value = json.loads(
        data.decode("utf-8"),
        parse_constant=_reject_json_constant,
    )
    _validate_json_numbers(value)
    if not isinstance(value, dict):
        raise ValueError("artifact document is not an object")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-standard JSON numeric constant is invalid")


def _validate_json_numbers(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite JSON number is invalid")
    if isinstance(value, Mapping):
        for nested in value.values():
            _validate_json_numbers(nested)
    elif isinstance(value, list):
        for nested in value:
            _validate_json_numbers(nested)


def _case_rows(
    layout: Any,
    path: Path,
    artifact_snapshot: Mapping[Path, bytes],
) -> list[dict[str, Any]]:
    rows = _rows(layout, path, artifact_snapshot)
    for row in rows:
        validate_fapo_case(row)
        _nonempty_string(row, "task_type")
        _case_metadata(row)
    return rows


def _unique_by(
    rows: Sequence[Mapping[str, Any]],
    field: str,
) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _nonempty_string(row, field)
        if value in output:
            raise ValueError("artifact identities are not unique")
        output[value] = row
    return output


def _nonempty_string(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("required artifact string is invalid")
    return value


def _string_list(
    row: Mapping[str, Any],
    field: str,
    *,
    require_nonempty: bool = False,
) -> list[str]:
    value = row.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError("required artifact string array is invalid")
    if require_nonempty and not value:
        raise ValueError("required artifact string array is empty")
    return value


def _object(row: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    value = row.get(field)
    if not isinstance(value, Mapping):
        raise ValueError("required artifact object is invalid")
    return value


def _mapping_list(
    row: Mapping[str, Any],
    field: str,
    *,
    default_empty: bool = False,
) -> list[Mapping[str, Any]]:
    value = row.get(field, [] if default_empty else None)
    if not isinstance(value, list) or not all(
        isinstance(item, Mapping) for item in value
    ):
        raise ValueError("required artifact object array is invalid")
    return value


def _nullable_string(row: Mapping[str, Any], field: str) -> None:
    value = row.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError("optional artifact string is invalid")


def _boolean(row: Mapping[str, Any], field: str) -> bool:
    value = row.get(field)
    if not isinstance(value, bool):
        raise ValueError("required artifact boolean is invalid")
    return value


def _validate_candidate_criteria(row: Mapping[str, Any]) -> None:
    criteria = _mapping_list(row, "criteria")
    if not criteria:
        raise ValueError("candidate guideline criteria are missing")
    for criterion in criteria:
        for field in (
            "kind",
            "statement",
            "dimension",
            "severity",
            "scoring",
        ):
            _nonempty_string(criterion, field)
        applicability = criterion.get("applicability")
        if not isinstance(applicability, (str, Mapping)):
            raise ValueError("guideline criterion applicability is invalid")
        if isinstance(applicability, str) and not applicability.strip():
            raise ValueError("guideline criterion applicability is invalid")
        _boolean(criterion, "evidence_required")
        evaluator = _object(criterion, "evaluator")
        _nonempty_string(evaluator, "type")
        _nonempty_string(evaluator, "fallback")
        if "source_record_ids" in criterion:
            _string_list(criterion, "source_record_ids", require_nonempty=True)


def _validate_guideline_criterion(
    criterion: Mapping[str, Any],
    *,
    expected_order: int,
) -> None:
    for field in ("kind", "dimension", "severity", "scoring"):
        _nonempty_string(criterion, field)
    applicability = criterion.get("applicability")
    if not isinstance(applicability, (str, Mapping)):
        raise ValueError("guideline criterion applicability is invalid")
    if isinstance(applicability, str) and not applicability.strip():
        raise ValueError("guideline criterion applicability is invalid")
    _boolean(criterion, "evidence_required")
    if _integer(criterion, "order", minimum=1) != expected_order:
        raise ValueError("guideline criterion order is inconsistent")
    evaluator = _object(criterion, "evaluator")
    _nonempty_string(evaluator, "type")
    _nonempty_string(evaluator, "fallback")


def _integer(row: Mapping[str, Any], field: str, *, minimum: int) -> int:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError("required artifact integer is invalid")
    return value


def _number(
    row: Mapping[str, Any],
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("required artifact number is invalid")
    number = float(value)
    if (
        not math.isfinite(number)
        or (minimum is not None and number < minimum)
        or (maximum is not None and number > maximum)
    ):
        raise ValueError("required artifact number is invalid")
    return number


def _case_metadata(case: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = _object(case, "metadata")
    _nonempty_string(metadata, "group_id")
    return metadata


def _case_group(case: Mapping[str, Any]) -> str:
    return _nonempty_string(_case_metadata(case), "group_id")


def _validate_expected(expected: Mapping[str, Any]) -> None:
    if not set(expected) & SCOREABLE_EXPECTED_KEYS:
        raise ValueError("case expected value has no scoreable field")
    rubric = expected.get("rubric")
    scoreable = False
    if rubric is not None:
        if not isinstance(rubric, Mapping):
            raise ValueError("case rubric is invalid")
        for field in ("must", "must_not", "should"):
            scoreable = bool(_string_list(rubric, field)) or scoreable
    checks = _mapping_list(expected, "deterministic_checks", default_empty=True)
    scoreable = scoreable or bool(checks)
    for field in ("answer", "expected_output", "label", "reference_output"):
        value = expected.get(field)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError("case scoreable expected string is invalid")
            scoreable = scoreable or bool(value.strip())
    tool_expectations = expected.get("tool_expectations")
    if tool_expectations is not None:
        if not isinstance(tool_expectations, Mapping):
            raise ValueError("case tool expectations are invalid")
        scoreable = scoreable or bool(tool_expectations)
    if not scoreable:
        raise ValueError("case expected value is not scoreable")
    if "confidence" in expected:
        _number(expected, "confidence", minimum=0.0, maximum=1.0)


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
