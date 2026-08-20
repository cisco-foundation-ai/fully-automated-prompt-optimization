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
from src.hephaestus.evaluation_assets.models import PipelineStage

_MATCH_STATUSES = {
    "matched_trusted_intent",
    "needs_more_trusted_examples",
    "missing_or_weak_labels",
}
_TRUST_TIERS = {
    "trusted": "trusted_feedback",
    "inferred": "inferred_from_trusted_feedback",
    "synthetic": "synthetic",
}
_SOURCE_NAMES = {
    "trusted": "feedback_trace",
    "inferred": "unlabeled_trace",
    "synthetic": "synthetic_generation",
}


def validate_legacy_stage_semantics(
    layout: Any,
    artifact_profiles: Mapping[PipelineStage, str],
) -> None:
    """Cross-validate the full historical stage graph before adoption writes."""
    _reject_ambiguous_stage_three(layout)

    feedback = _rows(layout.feedback_path)
    unlabeled = _rows(layout.unlabeled_path)
    validate_input_records(feedback, labeled=True, path=layout.feedback_path)
    validate_input_records(unlabeled, labeled=False, path=layout.unlabeled_path)
    feedback_by_id = _unique_by(feedback, "record_id")
    unlabeled_by_id = _unique_by(unlabeled, "record_id")
    normalized = _rows(
        layout.artifact_path(PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl")
    )
    intents = _rows(
        layout.artifact_path(PipelineStage.PREPARED_INPUTS, "intent_records.jsonl")
    )
    validate_input_records(
        normalized,
        labeled=True,
        path=layout.artifact_path(
            PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl"
        ),
    )
    validate_input_records(
        intents,
        labeled=False,
        path=layout.artifact_path(PipelineStage.PREPARED_INPUTS, "intent_records.jsonl"),
    )
    normalized_by_id = _unique_by(normalized, "record_id")
    intents_by_id = _unique_by(intents, "record_id")
    _validate_prepared_identity(feedback_by_id, normalized_by_id, labeled=True)
    _validate_prepared_identity(unlabeled_by_id, intents_by_id, labeled=False)

    stage_three_profile = artifact_profiles[PipelineStage.RUBRIC_EXTRACTION]
    trusted_intents, trusted_cases = _validate_stage_three(
        layout,
        stage_three_profile,
        normalized_by_id,
    )
    clusters = _validate_clusters(layout, intents_by_id)
    matches = _validate_matches(layout, clusters, trusted_intents)
    _validate_queue(layout, clusters, matches, intents_by_id)
    inferred_cases = _validate_inference(
        layout,
        clusters,
        matches,
        trusted_intents,
        intents_by_id,
    )
    synthetic_cases = _validate_synthetic(
        layout,
        clusters,
        matches,
        [*trusted_cases, *inferred_cases],
    )
    _validate_splits(layout, trusted_cases, inferred_cases, synthetic_cases)


def _reject_ambiguous_stage_three(layout: Any) -> None:
    if not layout.stages_root.is_dir():
        return
    canonical = layout.stages_root / "03_evaluation_guidelines"
    historical = layout.stages_root / "03_rubric_extraction"
    native_names = (
        "feedback_evidence.jsonl",
        "candidate_guidelines.jsonl",
        "evaluation_guidelines.jsonl",
        "trusted_intents.jsonl",
        "trusted_cases.jsonl",
    )
    legacy_names = (
        "feedback_rubrics.jsonl",
        "trusted_intents.jsonl",
        "trusted_cases.jsonl",
    )
    canonical_complete = all((canonical / name).is_file() for name in native_names)
    historical_complete = all((historical / name).is_file() for name in legacy_names)
    if canonical_complete and historical_complete:
        raise ValueError("stage three has competing complete artifact profiles")


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
) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]]]:
    stage = PipelineStage.RUBRIC_EXTRACTION
    trusted_intent_rows = _rows(layout.artifact_path(stage, "trusted_intents.jsonl"))
    trusted_intents = _unique_by(trusted_intent_rows, "intent_id")
    for row in trusted_intent_rows:
        _nonempty_string(row, "label")
        _string_list(row, "texts", require_nonempty=True)
        if "route" in row and row["route"] is not None:
            _nonempty_string(row, "route")
        metadata = _object(row, "metadata")
        source_ids = _string_list(metadata, "source_record_ids", require_nonempty=True)
        if not set(source_ids) <= set(feedback_by_id):
            raise ValueError("trusted intent references unknown feedback")

    trusted_cases = _case_rows(layout.artifact_path(stage, "trusted_cases.jsonl"))
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

    if profile == "legacy":
        rubric_rows = _rows(layout.artifact_path(stage, "feedback_rubrics.jsonl"))
        rubrics = _unique_by(rubric_rows, "record_id")
        if set(rubrics) != set(feedback_by_id):
            raise ValueError("legacy rubrics do not exactly cover feedback")
        for row in rubric_rows:
            scoreable = False
            for field in ("must", "must_not", "should"):
                if field in row:
                    scoreable = bool(_string_list(row, field)) or scoreable
            checks = row.get("deterministic_checks", [])
            if not isinstance(checks, list):
                raise ValueError("legacy rubric deterministic checks are invalid")
            if not scoreable and not checks and not row.get("reference_output"):
                raise ValueError("legacy rubric has no scoreable expected value")
        covered = {
            source_id
            for row in trusted_intent_rows
            for source_id in _string_list(_object(row, "metadata"), "source_record_ids")
        }
        if covered != set(feedback_by_id):
            raise ValueError("trusted intents do not exactly cover legacy rubrics")
        intent_sources = {
            intent_id: set(
                _string_list(_object(intent, "metadata"), "source_record_ids")
            )
            for intent_id, intent in trusted_intents.items()
        }
        for case in trusted_cases:
            source_id = str(case["case_id"])[len("feedback-") :]
            linked = case["expected"].get("evaluation_guideline_ids", [])
            if not isinstance(linked, list) or any(
                not isinstance(intent_id, str)
                or intent_id not in intent_sources
                or source_id not in intent_sources[intent_id]
                for intent_id in linked
            ):
                raise ValueError("legacy trusted case intent lineage is invalid")
        return trusted_intents, trusted_cases

    evidence_rows = _rows(layout.artifact_path(stage, "feedback_evidence.jsonl"))
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

    candidate_rows = _rows(layout.artifact_path(stage, "candidate_guidelines.jsonl"))
    for row in candidate_rows:
        source_ids = _string_list(row, "source_record_ids", require_nonempty=True)
        if not set(source_ids) <= set(evidence) or any(
            evidence[source_id]["route"] != row.get("route")
            for source_id in source_ids
        ):
            raise ValueError("candidate guideline references unknown evidence")

    guideline_rows = _rows(layout.artifact_path(stage, "evaluation_guidelines.jsonl"))
    guidelines = _unique_by(guideline_rows, "guideline_id")
    represented: set[str] = set()
    for row in guideline_rows:
        source_ids = _string_list(row, "source_record_ids", require_nonempty=True)
        if not set(source_ids) <= set(evidence) or any(
            evidence[source_id]["route"] != row.get("route")
            for source_id in source_ids
        ):
            raise ValueError("evaluation guideline references unknown evidence")
        represented.update(source_ids)
        _nonempty_string(row, "route")
        criteria = row.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            raise ValueError("evaluation guideline criteria are missing")
        for criterion in criteria:
            if not isinstance(criterion, Mapping):
                raise ValueError("evaluation guideline criterion is invalid")
            _nonempty_string(criterion, "criterion_id")
            _nonempty_string(criterion, "statement")
            criterion_sources = _string_list(
                criterion, "source_record_ids", require_nonempty=True
            )
            if not set(criterion_sources) <= set(source_ids):
                raise ValueError("criterion source evidence is inconsistent")
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
        ids = _string_list(case["expected"], "evaluation_guideline_ids", require_nonempty=True)
        source_id = str(case["case_id"])[len("feedback-") :]
        if set(ids) != guideline_ids_by_source[source_id]:
            raise ValueError("trusted case references unknown guidelines")
    return trusted_intents, trusted_cases


def _validate_clusters(
    layout: Any,
    intents_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    rows = _rows(
        layout.artifact_path(PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl")
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
) -> dict[str, Mapping[str, Any]]:
    rows = _rows(
        layout.artifact_path(PipelineStage.COVERAGE_DECISIONS, "intent_matches.jsonl")
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
) -> None:
    rows = _rows(
        layout.artifact_path(
            PipelineStage.COVERAGE_DECISIONS,
            "review_queue/labeling_queue.jsonl",
        )
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
        seen.add(key)


def _validate_inference(
    layout: Any,
    clusters: Mapping[str, Mapping[str, Any]],
    matches: Mapping[str, Mapping[str, Any]],
    trusted_intents: Mapping[str, Mapping[str, Any]],
    intents: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    stage = PipelineStage.LABEL_INFERENCE
    matched_clusters = {
        cluster_id
        for cluster_id, row in matches.items()
        if row["status"] == "matched_trusted_intent"
    }
    rubric_rows = _rows(
        layout.artifact_path(stage, "inferred_unlabeled_cluster_rubrics.jsonl")
    )
    rubrics = _unique_by(rubric_rows, "cluster_id")
    if set(rubrics) != matched_clusters:
        raise ValueError("inferred rubrics do not exactly cover matched clusters")
    for cluster_id, row in rubrics.items():
        if row.get("label_source") != "inferred_from_trusted_feedback":
            raise ValueError("inferred rubric label source is invalid")
        for field in ("must", "must_not", "should"):
            _string_list(row, field)
        _number(row, "confidence", minimum=0.0)

    label_rows = _rows(layout.artifact_path(stage, "inferred_unlabeled_labels.jsonl"))
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
        _validate_expected(_object(row, "expected"))

    cases = _case_rows(layout.artifact_path(stage, "inferred_cases.jsonl"))
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
        layout.artifact_path(stage, "missing_labeled_feedback_clusters.jsonl")
    )
    missing = _unique_by(missing_rows, "cluster_id")
    if set(missing) != set(clusters) - matched_clusters:
        raise ValueError("missing-feedback inventory is inconsistent")
    for cluster_id, row in missing.items():
        if row.get("status") != matches[cluster_id].get("status"):
            raise ValueError("missing-feedback status is inconsistent")
    return cases


def _validate_synthetic(
    layout: Any,
    clusters: Mapping[str, Mapping[str, Any]],
    matches: Mapping[str, Mapping[str, Any]],
    existing_cases: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    stage = PipelineStage.SYNTHETIC_COVERAGE
    candidates = _case_rows(layout.artifact_path(stage, "synthetic_candidates.jsonl"))
    rejected = _case_rows(layout.artifact_path(stage, "rejected_synthetic.jsonl"))
    accepted = _case_rows(layout.artifact_path(stage, "synthetic_cases.jsonl"))
    candidates_by_id = _unique_by(candidates, "case_id")
    rejected_by_id = _unique_by(rejected, "case_id")
    accepted_by_id = _unique_by(accepted, "case_id")
    if set(accepted_by_id) & set(rejected_by_id):
        raise ValueError("synthetic accepted and rejected sets overlap")
    if candidates_by_id and set(candidates_by_id) != set(accepted_by_id) | set(rejected_by_id):
        raise ValueError("synthetic filtering is not an exact partition")
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
            or metadata.get("trust_tier") != _TRUST_TIERS["synthetic"]
            or not isinstance(cluster_id, str)
            or cluster_id not in clusters
            or cluster_id not in matched
            or metadata.get("review_status") != "review_required"
        ):
            raise ValueError("synthetic case provenance is inconsistent")
        _validate_expected(case["expected"])
    issues = _rows(layout.artifact_path(stage, "synthetic_filter_issues.jsonl"))
    for row in issues:
        case_id = _nonempty_string(row, "case_id")
        if case_id not in rejected_by_id:
            raise ValueError("synthetic filter issue references a non-rejected case")
        _nonempty_string(row, "code")
        _nonempty_string(row, "message")
    inherited = (
        _case_rows(layout.parent_snapshot / "parent_synthetic_cases.jsonl")
        if (layout.parent_snapshot / "parent_synthetic_cases.jsonl").is_file()
        else []
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
    if Counter(_canonical(row) for row in rejected) != Counter(
        _canonical(row) for row in filtered.rejected
    ) or Counter(_canonical(row) for row in issues) != Counter(
        _canonical(row) for row in expected_issues
    ):
        raise ValueError("synthetic filter artifacts do not reproduce")
    if not {
        str(row["case_id"]) for row in filtered.accepted
    } <= set(accepted_by_id):
        raise ValueError("accepted synthetic candidates are incomplete")
    return accepted


def _validate_splits(
    layout: Any,
    trusted_cases: Sequence[Mapping[str, Any]],
    inferred_cases: Sequence[Mapping[str, Any]],
    synthetic_cases: Sequence[Mapping[str, Any]],
) -> None:
    stage = PipelineStage.DATASET_SPLITS
    source_by_tier = {
        "trusted": _unique_by(trusted_cases, "case_id"),
        "inferred": _unique_by(inferred_cases, "case_id"),
        "synthetic": _unique_by(synthetic_cases, "case_id"),
    }
    split_rows: dict[str, list[dict[str, Any]]] = {}
    for split in ("train", "validation", "test"):
        components: list[dict[str, Any]] = []
        for tier in ("trusted", "inferred", "synthetic"):
            rows = _case_rows(layout.artifact_path(stage, f"{split}_{tier}.jsonl"))
            _unique_by(rows, "case_id")
            for case in rows:
                case_id = case["case_id"]
                if (
                    _case_metadata(case).get("trust_tier") != _TRUST_TIERS[tier]
                    or case_id not in source_by_tier[tier]
                    or case != source_by_tier[tier][case_id]
                ):
                    raise ValueError("split component provenance is inconsistent")
            split_rows[f"{split}_{tier}"] = rows
            components.extend(rows)
        combined = _case_rows(layout.artifact_path(stage, f"{split}.jsonl"))
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

    regression = _case_rows(layout.artifact_path(stage, "regression_trusted.jsonl"))
    triage = _case_rows(layout.artifact_path(stage, "triage_hold.jsonl"))
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
            _TRUST_TIERS["synthetic"],
        }:
            raise ValueError("triage case trust tier is invalid")
        source = source_by_tier[
            "inferred" if trust_tier == _TRUST_TIERS["inferred"] else "synthetic"
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


def _rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("artifact row is not an object")
        rows.append(value)
    return rows


def _case_rows(path: Path) -> list[dict[str, Any]]:
    rows = _rows(path)
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
) -> float:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("required artifact number is invalid")
    number = float(value)
    if not math.isfinite(number) or (minimum is not None and number < minimum):
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
    checks = expected.get("deterministic_checks", [])
    if not isinstance(checks, list):
        raise ValueError("case deterministic checks are invalid")
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
        _number(expected, "confidence", minimum=0.0)


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
