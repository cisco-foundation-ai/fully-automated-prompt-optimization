# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Pure review, fingerprint, and exact-duplicate-family contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence as SequenceCollection
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from src.hephaestus.evaluation_assets.dependencies import (
    STAGE_SEVEN_DEPENDENCY_SCHEMA_VERSION,
    STAGE_SIX_DEPENDENCY_SCHEMA_VERSION,
    dependency_matches,
)

DERIVED_REVIEW_ITEM_SCHEMA_VERSION = "fapo-derived-review-item-v1"
REVIEW_QUEUE_SCHEMA_VERSION = DERIVED_REVIEW_ITEM_SCHEMA_VERSION
DERIVED_CASE_CONTENT_SCHEMA_VERSION = "fapo-derived-case-content-v1"
MODEL_CONTEXT_FINGERPRINT_SCHEMA_VERSION = "fapo-model-context-fingerprint-v1"
EXPECTED_TRUTH_FINGERPRINT_SCHEMA_VERSION = "fapo-expected-truth-fingerprint-v2"
REVIEW_DEPENDENCY_FINGERPRINT_SCHEMA_VERSION = "fapo-review-dependency-fingerprint-v1"
DERIVED_REVIEW_FINGERPRINT_SCHEMA_VERSION = "fapo-derived-review-fingerprint-v1"
REVIEW_DECISION_SCHEMA_VERSION = "fapo-review-decision-v1"
REVIEW_DECISION_IDENTITY_SCHEMA_VERSION = "fapo-review-decision-identity-v1"
REVIEW_SET_FINGERPRINT_SCHEMA_VERSION = "fapo-review-set-fingerprint-v1"
REVIEW_DECISION_SET_FINGERPRINT_SCHEMA_VERSION = "fapo-review-decision-set-fingerprint-v1"
REVIEW_AUTHORITY_REVISION_SCHEMA_VERSION = "fapo-review-authority-revision-v1"
REVIEW_FINALIZATION_SCHEMA_VERSION = "fapo-review-finalization-v1"
REVIEW_FINALIZATION_IDENTITY_SCHEMA_VERSION = "fapo-review-finalization-identity-v1"
DUPLICATE_FAMILY_SCHEMA_VERSION = "fapo-duplicate-family-v1"
DUPLICATE_FAMILY_IDENTITY_SCHEMA_VERSION = "fapo-duplicate-family-identity-v1"
SPLIT_GROUP_IDENTITY_SCHEMA_VERSION = "fapo-split-group-identity-v1"

REVIEW_ITEM_FIELDS = frozenset(
    {
        "schema_version",
        "case_id",
        "trust_tier",
        "fingerprint",
        "case_content_sha256",
        "context_fingerprint",
        "truth_fingerprint",
        "dependency_fingerprint",
        "source_provenance",
        "case",
        "initial_decision",
    }
)

_INITIAL_DECISION_FIELDS = frozenset({"status", "reviewer", "timestamp"})
REVIEW_DECISION_FIELDS = frozenset(
    {
        "schema_version",
        "decision_id",
        "case_id",
        "fingerprint",
        "status",
        "reviewer",
        "timestamp",
        "note",
        "inherited_from",
    }
)
INHERITED_REVIEW_DECISION_FIELDS = REVIEW_DECISION_FIELDS | frozenset(
    {"original_reviewer", "original_timestamp"}
)
_INHERITED_FROM_FIELDS = frozenset({"parent_asset_id", "parent_decision_id", "parent_fingerprint"})
REVIEW_FINALIZATION_FIELDS = frozenset(
    {
        "schema_version",
        "finalization_id",
        "review_set_fingerprint",
        "stage7_receipt_sha256",
        "reviewer",
        "timestamp",
        "note",
        "items",
        "held",
        "counts",
    }
)
_FINALIZATION_ITEM_FIELDS = frozenset({"case_id", "fingerprint", "status", "decision_id"})
_FINALIZATION_HELD_FIELDS = frozenset({"case_id", "fingerprint", "reason"})
_FINALIZATION_COUNT_FIELDS = frozenset({"trusted", "approved", "pending", "rejected", "held"})
DUPLICATE_FAMILY_FIELDS = frozenset(
    {
        "schema_version",
        "family_id",
        "context_fingerprints",
        "group_ids",
        "split_group_id",
        "split_group_aliases",
        "members",
        "truth_fingerprints",
        "assigned_early_split",
        "hold_reasons",
    }
)
DUPLICATE_FAMILY_MEMBER_FIELDS = frozenset(
    {
        "case_id",
        "trust_tier",
        "context_fingerprint",
        "truth_fingerprint",
        "group_id",
        "supplied_split_group_id",
        "early_split",
    }
)
_FAMILY_ID = re.compile(r"^family-[0-9a-f]{24}$")
_SCOUT_STAGE_SIX_DEPENDENCY_FIELDS = frozenset(
    {
        "schema_version",
        "trusted_split_plan_sha256",
        "cluster",
        "match",
        "guideline",
        "source_members",
        "provider",
        "prompt",
        "pipeline_settings",
    }
)
_SCOUT_STAGE_SEVEN_DEPENDENCY_FIELDS = frozenset(
    {
        "schema_version",
        "cluster",
        "representative_members",
        "inference_dependency_fingerprint",
        "rubric",
        "provider",
        "prompt",
        "pipeline_settings",
    }
)
_SOURCE_PROVENANCE_REQUIRED_FIELDS = frozenset(
    {
        "source_record_ids",
        "source_record_sha256s",
        "source_cluster",
        "matched_intent_id",
    }
)
_FINGERPRINTED_DEPENDENCY_MEMBER_FIELDS = frozenset({"identity", "content_sha256"})
_CONTEXT_JSON_FIELDS = frozenset({"messages_json", "tool_context_json", "runtime_json"})
_SCORING_TRUTH_FIELDS = frozenset(
    {
        "answer",
        "deterministic_checks",
        "expected_output",
        "label",
        "reference_output",
        "rubric",
        "tool_expectations",
    }
)
_RELEASE_LOCAL_METADATA_FIELDS = frozenset(
    {
        "dataset_version",
        "decision_id",
        "generation_id",
        "release_generation_id",
        "review_decision_id",
        "review_status",
        "split",
        "split_group_id",
    }
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_RAW_SHA256 = re.compile(r"^[0-9a-f]{64}$")

ScoreabilityCheck = Callable[[Mapping[str, Any]], bool]


class ReviewDecisionConflictError(ValueError):
    """Raised when a caller tries to reverse an immutable terminal decision."""


class ReviewIntegrityError(ValueError):
    """Raised when corrupt review authority makes a mutation unsafe."""


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize one strict JSON value without lossy normalization."""
    normalized = _strict_json_value(payload)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def fingerprint_json(payload: Any) -> str:
    """Return the versioned SHA-256 representation used by review artifacts."""
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def dependency_fingerprint(dependency: Mapping[str, Any]) -> str:
    """Bind every field of one Stage 6 or Stage 7 dependency descriptor."""
    descriptor = _validate_dependency(dependency)
    return fingerprint_json(
        {
            "schema_version": REVIEW_DEPENDENCY_FINGERPRINT_SCHEMA_VERSION,
            "dependency": descriptor,
        }
    )


def case_content_fingerprint(case: Mapping[str, Any]) -> str:
    """Hash the complete pre-publication case without a field exclusion list."""
    complete_case = _validate_case(case, derived=False)
    return fingerprint_json(
        {
            "schema_version": DERIVED_CASE_CONTENT_SCHEMA_VERSION,
            "case": complete_case,
        }
    )


def model_visible_context(case: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact chain-visible context projection for duplicate identity."""
    complete_case = _validate_case(case, derived=False)
    context = dict(complete_case["context"])
    for field in _CONTEXT_JSON_FIELDS & set(context):
        encoded = context[field]
        if not isinstance(encoded, str):
            raise ValueError(f"case context {field} must be a JSON string")
        try:
            context[field] = _strict_json_value(json.loads(encoded))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError(f"case context {field} is not valid strict JSON") from exc
    return {
        "schema_version": MODEL_CONTEXT_FINGERPRINT_SCHEMA_VERSION,
        "context": _strict_json_value(context),
    }


def model_visible_context_fingerprint(case: Mapping[str, Any]) -> str:
    """Hash only the exact context visible to the task model."""
    return fingerprint_json(model_visible_context(case))


def expected_truth_fingerprint(case: Mapping[str, Any]) -> str:
    """Hash task routing and only fields that define scoring truth."""
    complete_case = _validate_case(case, derived=False)
    expected = complete_case["expected"]
    return fingerprint_json(
        {
            "schema_version": EXPECTED_TRUTH_FINGERPRINT_SCHEMA_VERSION,
            "task_type": complete_case["task_type"],
            "expected": {
                field: expected[field]
                for field in sorted(_SCORING_TRUTH_FIELDS)
                if field in expected
            },
        }
    )


def build_review_item(
    *,
    case: Mapping[str, Any],
    dependency: Mapping[str, Any],
    source_provenance: Mapping[str, Any],
    reviewer: str,
    timestamp: str,
    scoreability: ScoreabilityCheck | None = None,
) -> dict[str, Any]:
    """Build one immutable pending item bound to complete semantic dependencies."""
    complete_case = _validate_case(case, derived=True)
    source = _validate_source_provenance(source_provenance)
    dependency_sha256 = dependency_fingerprint(dependency)
    item = {
        "schema_version": DERIVED_REVIEW_ITEM_SCHEMA_VERSION,
        "case_id": complete_case["case_id"],
        "trust_tier": complete_case["metadata"]["trust_tier"],
        "fingerprint": _review_fingerprint(
            complete_case,
            dependency_sha256,
            source,
        ),
        "case_content_sha256": case_content_fingerprint(complete_case),
        "context_fingerprint": model_visible_context_fingerprint(complete_case),
        "truth_fingerprint": expected_truth_fingerprint(complete_case),
        "dependency_fingerprint": dependency_sha256,
        "source_provenance": source,
        "case": complete_case,
        "initial_decision": {
            "status": "pending",
            "reviewer": _nonempty_string(reviewer, "reviewer"),
            "timestamp": _utc_timestamp(timestamp, "timestamp"),
        },
    }
    return validate_review_item(
        item,
        dependency=dependency,
        scoreability=scoreability,
    )


def validate_review_item(
    value: Mapping[str, Any],
    *,
    dependency: Mapping[str, Any] | None = None,
    scoreability: ScoreabilityCheck | None = None,
) -> dict[str, Any]:
    """Validate the closed review-queue row and recompute all available hashes."""
    item = _exact_mapping(value, REVIEW_ITEM_FIELDS, "review item")
    if item.get("schema_version") != DERIVED_REVIEW_ITEM_SCHEMA_VERSION:
        raise ValueError("review item schema_version is unsupported")
    case = _validate_case(_mapping(item.get("case"), "review item case"), derived=True)
    case_id = _nonempty_string(item.get("case_id"), "review item case_id")
    trust_tier = _nonempty_string(item.get("trust_tier"), "review item trust_tier")
    if case_id != case["case_id"] or trust_tier != case["metadata"]["trust_tier"]:
        raise ValueError("review item identity does not match its complete case")
    source = _validate_source_provenance(item.get("source_provenance"))
    dependency_sha256 = _require_sha256(
        item.get("dependency_fingerprint"),
        "review item dependency_fingerprint",
    )
    if dependency is not None and dependency_fingerprint(dependency) != dependency_sha256:
        raise ValueError("review item dependency fingerprint does not match")
    expected_hashes = {
        "fingerprint": _review_fingerprint(case, dependency_sha256, source),
        "case_content_sha256": case_content_fingerprint(case),
        "context_fingerprint": model_visible_context_fingerprint(case),
        "truth_fingerprint": expected_truth_fingerprint(case),
    }
    for field, expected in expected_hashes.items():
        if _require_sha256(item.get(field), f"review item {field}") != expected:
            raise ValueError(f"review item {field} does not match")
    initial = _exact_mapping(
        item.get("initial_decision"),
        _INITIAL_DECISION_FIELDS,
        "review item initial_decision",
    )
    if initial.get("status") != "pending":
        raise ValueError("review item initial decision must be pending")
    _nonempty_string(initial.get("reviewer"), "review item initial reviewer")
    _utc_timestamp(initial.get("timestamp"), "review item initial timestamp")
    _require_scoreable(case["expected"], scoreability)
    return _strict_json_value(item)


def resolve_review_decision(
    item: Mapping[str, Any],
    decisions: Sequence[Any] | None,
    *,
    dependency: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one current item, treating every authority anomaly as pending."""
    try:
        current = validate_review_item(item, dependency=dependency)
    except (TypeError, ValueError):
        return _pending_resolution(item)
    valid, malformed = _matching_decisions(current, decisions)
    if malformed or len(valid) != 1:
        return _pending_resolution(current)
    decision = valid[0]
    return {
        "case_id": decision["case_id"],
        "fingerprint": decision["fingerprint"],
        "status": decision["status"],
        "decision_id": decision["decision_id"],
        "reviewer": decision["reviewer"],
        "timestamp": decision["timestamp"],
        "note": decision["note"],
        "inherited_from": decision["inherited_from"],
    }


def record_review_decision(
    item: Mapping[str, Any],
    decisions: Sequence[Any] | None,
    *,
    status: str,
    reviewer: str,
    timestamp: str,
    note: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Return a new terminal row, an idempotent replay, or an immutable conflict."""
    try:
        current = validate_review_item(item)
    except (TypeError, ValueError) as exc:
        raise ReviewIntegrityError("current review item is invalid") from exc
    if status not in {"approved", "rejected"}:
        raise ValueError("review decision status must be approved or rejected")
    valid, malformed = _matching_decisions(current, decisions)
    if malformed:
        raise ReviewIntegrityError("current review decision authority is malformed")
    if len(valid) > 1:
        raise ReviewIntegrityError("multiple terminal review decisions exist")
    if valid:
        existing = valid[0]
        if existing["status"] != status:
            raise ReviewDecisionConflictError("terminal review decision is immutable")
        return existing, False
    return (
        _build_decision_row(
            case_id=current["case_id"],
            fingerprint=current["fingerprint"],
            status=status,
            reviewer=reviewer,
            timestamp=timestamp,
            note=note,
            inherited_from=None,
        ),
        True,
    )


def validate_review_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one closed immutable terminal decision row and its identity."""
    decision = _mapping(value, "review decision")
    inherited = decision.get("inherited_from")
    expected_fields = (
        INHERITED_REVIEW_DECISION_FIELDS if isinstance(inherited, Mapping) else REVIEW_DECISION_FIELDS
    )
    if set(decision) != expected_fields:
        raise ValueError("review decision schema is invalid")
    if decision.get("schema_version") != REVIEW_DECISION_SCHEMA_VERSION:
        raise ValueError("review decision schema_version is unsupported")
    _require_sha256(decision.get("decision_id"), "review decision_id")
    _nonempty_string(decision.get("case_id"), "review decision case_id")
    _require_sha256(decision.get("fingerprint"), "review decision fingerprint")
    if decision.get("status") not in {"approved", "rejected"}:
        raise ValueError("review decision status is invalid")
    _nonempty_string(decision.get("reviewer"), "review decision reviewer")
    _utc_timestamp(decision.get("timestamp"), "review decision timestamp")
    note = decision.get("note")
    if note is not None and not isinstance(note, str):
        raise ValueError("review decision note must be a string or null")
    if inherited is None:
        pass
    elif isinstance(inherited, Mapping):
        inherited_payload = _exact_mapping(
            inherited,
            _INHERITED_FROM_FIELDS,
            "review decision inherited_from",
        )
        _nonempty_string(
            inherited_payload.get("parent_asset_id"),
            "review decision parent_asset_id",
        )
        _require_sha256(
            inherited_payload.get("parent_decision_id"),
            "review decision parent_decision_id",
        )
        _require_sha256(
            inherited_payload.get("parent_fingerprint"),
            "review decision parent_fingerprint",
        )
        _nonempty_string(
            decision.get("original_reviewer"),
            "review decision original_reviewer",
        )
        _utc_timestamp(
            decision.get("original_timestamp"),
            "review decision original_timestamp",
        )
    else:
        raise ValueError("review decision inherited_from is invalid")
    if decision["decision_id"] != _decision_id(decision):
        raise ValueError("review decision_id does not match its immutable row")
    return _strict_json_value(decision)


def inherit_review_decision(
    *,
    parent_item: Mapping[str, Any],
    child_item: Mapping[str, Any],
    parent_decisions: Sequence[Any] | None,
    parent_asset_id: str,
    reviewer: str,
    timestamp: str,
) -> dict[str, Any] | None:
    """Copy terminal authority only for a byte-identical current review identity."""
    try:
        parent = validate_review_item(parent_item)
        child = validate_review_item(child_item)
    except (TypeError, ValueError):
        return None
    if parent["fingerprint"] != child["fingerprint"] or canonical_json_bytes(
        parent["case"]
    ) != canonical_json_bytes(child["case"]):
        return None
    valid, malformed = _matching_decisions(parent, parent_decisions)
    if malformed or len(valid) != 1:
        return None
    source = valid[0]
    original_reviewer = source.get("original_reviewer", source["reviewer"])
    original_timestamp = source.get("original_timestamp", source["timestamp"])
    return _build_decision_row(
        case_id=child["case_id"],
        fingerprint=child["fingerprint"],
        status=source["status"],
        reviewer=reviewer,
        timestamp=timestamp,
        note=source["note"],
        inherited_from={
            "parent_asset_id": _nonempty_string(
                parent_asset_id,
                "parent_asset_id",
            ),
            "parent_decision_id": source["decision_id"],
            "parent_fingerprint": parent["fingerprint"],
        },
        original_reviewer=original_reviewer,
        original_timestamp=original_timestamp,
    )


def review_set_fingerprint(
    *,
    stage7_receipt_sha256: str,
    review_items: Sequence[Mapping[str, Any]],
    held_cases: Sequence[Mapping[str, Any]],
    dependencies: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """Bind the exact Stage 7 receipt, eligible fingerprints, and held set."""
    receipt = _require_sha256(stage7_receipt_sha256, "Stage 7 receipt sha256")
    items = _validated_review_items(review_items, dependencies=dependencies)
    held = _project_held_cases(held_cases)
    item_fingerprints = [item["fingerprint"] for item in items]
    held_fingerprints = [row["fingerprint"] for row in held]
    if set(item_fingerprints) & set(held_fingerprints):
        raise ValueError("review items and held cases must be disjoint")
    return fingerprint_json(
        {
            "schema_version": REVIEW_SET_FINGERPRINT_SCHEMA_VERSION,
            "stage7_receipt_sha256": receipt,
            "item_fingerprints": sorted(item_fingerprints),
            "held_fingerprints": sorted(held_fingerprints),
        }
    )


def decision_set_fingerprint(
    *,
    review_set_fingerprint: str,
    review_items: Sequence[Mapping[str, Any]],
    dependencies: Mapping[str, Mapping[str, Any]],
    decisions: Sequence[Any] | None,
) -> str:
    """Bind the exact resolved decision snapshot for one immutable review set."""
    current_set = _require_sha256(
        review_set_fingerprint,
        "review set fingerprint",
    )
    dependency_map = _mapping(dependencies, "review dependencies")
    authority = _validated_decision_authority(decisions)
    items = _validated_review_items(
        review_items,
        dependencies=dependency_map,
    )
    snapshot: list[dict[str, Any]] = []
    for item in items:
        matches, malformed = _matching_decisions(item, authority)
        if malformed or len(matches) > 1:
            raise ReviewIntegrityError("current review decision authority is malformed")
        resolved = resolve_review_decision(
            item,
            authority,
            dependency=dependency_map[item["case_id"]],
        )
        snapshot.append(
            {
                "case_id": item["case_id"],
                "fingerprint": item["fingerprint"],
                "status": resolved["status"],
                "decision_id": resolved["decision_id"],
            }
        )
    return fingerprint_json(
        {
            "schema_version": REVIEW_DECISION_SET_FINGERPRINT_SCHEMA_VERSION,
            "review_set_fingerprint": current_set,
            "decisions": snapshot,
        }
    )


def review_authority_revision(
    *,
    decision_set_sha256: str,
    finalization_id: str | None,
) -> str:
    """Return a safe polling revision for decisions plus finalization identity."""
    current_decisions = _require_sha256(
        decision_set_sha256,
        "decision set fingerprint",
    )
    current_finalization = (
        _require_sha256(finalization_id, "review finalization_id")
        if finalization_id is not None
        else None
    )
    return fingerprint_json(
        {
            "schema_version": REVIEW_AUTHORITY_REVISION_SCHEMA_VERSION,
            "decision_set_fingerprint": current_decisions,
            "finalization_id": current_finalization,
        }
    )


def build_review_finalization(
    *,
    review_items: Sequence[Mapping[str, Any]],
    dependencies: Mapping[str, Mapping[str, Any]],
    decisions: Sequence[Any] | None,
    held_cases: Sequence[Mapping[str, Any]],
    stage7_receipt_sha256: str,
    trusted_count: int,
    reviewer: str,
    timestamp: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Freeze one explicit immutable snapshot; pending items remain pending."""
    dependency_map = _mapping(dependencies, "review dependencies")
    authority = _validated_decision_authority(decisions)
    items = _validated_review_items(review_items, dependencies=dependency_map)
    held = _project_held_cases(held_cases)
    snapshot_items: list[dict[str, Any]] = []
    for item in items:
        matches, malformed = _matching_decisions(item, authority)
        if malformed or len(matches) > 1:
            raise ReviewIntegrityError("current review decision authority is malformed")
        resolved = resolve_review_decision(
            item,
            authority,
            dependency=dependency_map[item["case_id"]],
        )
        snapshot_items.append(
            {
                "case_id": item["case_id"],
                "fingerprint": item["fingerprint"],
                "status": resolved["status"],
                "decision_id": resolved["decision_id"],
            }
        )
    snapshot_items.sort(key=lambda row: (row["case_id"], row["fingerprint"]))
    counts = {
        "trusted": _nonnegative_int(trusted_count, "trusted_count"),
        "approved": sum(row["status"] == "approved" for row in snapshot_items),
        "pending": sum(row["status"] == "pending" for row in snapshot_items),
        "rejected": sum(row["status"] == "rejected" for row in snapshot_items),
        "held": len(held),
    }
    row: dict[str, Any] = {
        "schema_version": REVIEW_FINALIZATION_SCHEMA_VERSION,
        "finalization_id": "",
        "review_set_fingerprint": review_set_fingerprint(
            stage7_receipt_sha256=stage7_receipt_sha256,
            review_items=items,
            held_cases=held,
            dependencies=dependency_map,
        ),
        "stage7_receipt_sha256": _require_sha256(
            stage7_receipt_sha256,
            "Stage 7 receipt sha256",
        ),
        "reviewer": _nonempty_string(reviewer, "finalization reviewer"),
        "timestamp": _utc_timestamp(timestamp, "finalization timestamp"),
        "note": note,
        "items": snapshot_items,
        "held": held,
        "counts": counts,
    }
    row["finalization_id"] = _finalization_id(row)
    return validate_review_finalization(
        row,
        review_items=items,
        dependencies=dependency_map,
        decisions=authority,
        held_cases=held,
        stage7_receipt_sha256=stage7_receipt_sha256,
    )


def parse_review_finalization(value: Mapping[str, Any]) -> dict[str, Any]:
    """Parse a structurally authentic snapshot without authorizing release."""
    row = _exact_mapping(
        value,
        REVIEW_FINALIZATION_FIELDS,
        "review finalization",
    )
    if row.get("schema_version") != REVIEW_FINALIZATION_SCHEMA_VERSION:
        raise ValueError("review finalization schema_version is unsupported")
    _require_sha256(row.get("finalization_id"), "review finalization_id")
    _require_sha256(
        row.get("review_set_fingerprint"),
        "review finalization review_set_fingerprint",
    )
    _require_sha256(
        row.get("stage7_receipt_sha256"),
        "review finalization Stage 7 receipt",
    )
    _nonempty_string(row.get("reviewer"), "review finalization reviewer")
    _utc_timestamp(row.get("timestamp"), "review finalization timestamp")
    note = row.get("note")
    if note is not None and not isinstance(note, str):
        raise ValueError("review finalization note must be a string or null")
    snapshot_items = _validate_finalization_items(row.get("items"))
    snapshot_held = _validate_finalization_held(row.get("held"))
    counts = _exact_mapping(
        row.get("counts"),
        _FINALIZATION_COUNT_FIELDS,
        "review finalization counts",
    )
    expected_counts = {
        "trusted": _nonnegative_int(counts.get("trusted"), "trusted count"),
        "approved": sum(item["status"] == "approved" for item in snapshot_items),
        "pending": sum(item["status"] == "pending" for item in snapshot_items),
        "rejected": sum(item["status"] == "rejected" for item in snapshot_items),
        "held": len(snapshot_held),
    }
    if counts != expected_counts:
        raise ValueError("review finalization counts do not match its snapshot")
    if row["finalization_id"] != _finalization_id(row):
        raise ValueError("review finalization_id does not match its snapshot")
    return _strict_json_value(row)


def validate_review_finalization(
    value: Mapping[str, Any],
    *,
    review_items: Sequence[Mapping[str, Any]] | None = None,
    dependencies: Mapping[str, Mapping[str, Any]] | None = None,
    decisions: Sequence[Any] | None = None,
    held_cases: Sequence[Mapping[str, Any]] | None = None,
    stage7_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    """Authorize a finalization only against complete current live authority."""
    row = parse_review_finalization(value)
    if (
        review_items is None
        or dependencies is None
        or decisions is None
        or held_cases is None
        or stage7_receipt_sha256 is None
    ):
        raise ReviewIntegrityError("live review authority is required to validate finalization")
    receipt = _require_sha256(
        stage7_receipt_sha256,
        "expected Stage 7 receipt",
    )
    if row["stage7_receipt_sha256"] != receipt:
        raise ValueError("review finalization Stage 7 receipt does not match")
    dependency_map = _mapping(dependencies, "review dependencies")
    authority = _validated_decision_authority(decisions)
    current_items = _validated_review_items(
        review_items,
        dependencies=dependency_map,
    )
    current_held = _project_held_cases(held_cases)
    expected_set = review_set_fingerprint(
        stage7_receipt_sha256=receipt,
        review_items=current_items,
        held_cases=current_held,
        dependencies=dependency_map,
    )
    if row["review_set_fingerprint"] != expected_set:
        raise ValueError("review finalization review set does not match")
    current_identities = [
        {"case_id": item["case_id"], "fingerprint": item["fingerprint"]} for item in current_items
    ]
    snapshot_items = row["items"]
    snapshot_identities = [
        {"case_id": item["case_id"], "fingerprint": item["fingerprint"]} for item in snapshot_items
    ]
    if snapshot_identities != current_identities or row["held"] != current_held:
        raise ValueError("review finalization snapshot does not match review set")
    expected_snapshot = []
    for item in current_items:
        matches, malformed = _matching_decisions(item, authority)
        if malformed or len(matches) > 1:
            raise ReviewIntegrityError("current review decision authority is malformed")
        resolved = resolve_review_decision(
            item,
            authority,
            dependency=dependency_map[item["case_id"]],
        )
        expected_snapshot.append(
            {
                "case_id": item["case_id"],
                "fingerprint": item["fingerprint"],
                "status": resolved["status"],
                "decision_id": resolved["decision_id"],
            }
        )
    if snapshot_items != expected_snapshot:
        raise ValueError("review finalization decisions do not match authority")
    return _strict_json_value(row)


def _validated_review_items(
    values: Sequence[Mapping[str, Any]],
    *,
    dependencies: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if dependencies is None:
        items = [validate_review_item(value) for value in values]
    else:
        dependency_map = _mapping(dependencies, "review dependencies")
        raw_case_ids = [value.get("case_id") for value in values if isinstance(value, Mapping)]
        if (
            len(raw_case_ids) != len(values)
            or any(not isinstance(case_id, str) for case_id in raw_case_ids)
            or set(dependency_map) != set(raw_case_ids)
        ):
            raise ValueError("review dependencies must identify every current case exactly")
        items = [
            validate_review_item(
                value,
                dependency=dependency_map[str(value["case_id"])],
            )
            for value in values
        ]
    items.sort(key=lambda row: (row["case_id"], row["fingerprint"]))
    if len({item["case_id"] for item in items}) != len(items):
        raise ValueError("review item case_ids must be unique")
    if len({item["fingerprint"] for item in items}) != len(items):
        raise ValueError("review item fingerprints must be unique")
    return items


def _project_held_cases(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    held: list[dict[str, Any]] = []
    for value in values:
        row = _mapping(value, "held review case")
        held.append(
            {
                "case_id": _nonempty_string(
                    row.get("case_id"),
                    "held review case_id",
                ),
                "fingerprint": _require_sha256(
                    row.get("fingerprint"),
                    "held review fingerprint",
                ),
                "reason": _nonempty_string(
                    row.get("reason"),
                    "held review reason",
                ),
            }
        )
    held.sort(key=lambda row: (row["case_id"], row["fingerprint"]))
    if len({row["case_id"] for row in held}) != len(held):
        raise ValueError("held review case_ids must be unique")
    if len({row["fingerprint"] for row in held}) != len(held):
        raise ValueError("held review fingerprints must be unique")
    return held


def _validate_finalization_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("review finalization items must be an array")
    items: list[dict[str, Any]] = []
    for value_item in value:
        item = _exact_mapping(
            value_item,
            _FINALIZATION_ITEM_FIELDS,
            "review finalization item",
        )
        _nonempty_string(item.get("case_id"), "review finalization case_id")
        _require_sha256(item.get("fingerprint"), "review finalization fingerprint")
        status = item.get("status")
        if status not in {"pending", "approved", "rejected"}:
            raise ValueError("review finalization item status is invalid")
        decision_id = item.get("decision_id")
        if status == "pending":
            if decision_id is not None:
                raise ValueError("pending finalization item has a decision_id")
        else:
            _require_sha256(decision_id, "review finalization decision_id")
        items.append(item)
    expected = sorted(items, key=lambda row: (row["case_id"], row["fingerprint"]))
    if items != expected:
        raise ValueError("review finalization items are not canonical")
    if len({item["case_id"] for item in items}) != len(items):
        raise ValueError("review finalization case_ids are not unique")
    if len({item["fingerprint"] for item in items}) != len(items):
        raise ValueError("review finalization fingerprints are not unique")
    return items


def _validate_finalization_held(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("review finalization held must be an array")
    held = [
        _exact_mapping(
            item,
            _FINALIZATION_HELD_FIELDS,
            "review finalization held item",
        )
        for item in value
    ]
    projected = _project_held_cases(held)
    if held != projected:
        raise ValueError("review finalization held items are not canonical")
    return held


def _finalization_id(row: Mapping[str, Any]) -> str:
    identity = {
        key: row[key]
        for key in (
            "review_set_fingerprint",
            "stage7_receipt_sha256",
            "items",
            "held",
            "counts",
        )
    }
    return fingerprint_json(
        {
            "schema_version": REVIEW_FINALIZATION_IDENTITY_SCHEMA_VERSION,
            "snapshot": identity,
        }
    )


def build_duplicate_families(
    cases: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build exact transitive components across contexts and supplied groups."""
    members = [_family_member(case) for case in cases]
    case_ids = [member["case_id"] for member in members]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("duplicate-family case_ids must be unique")
    parents = list(range(len(members)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(first: int, second: int) -> None:
        left = find(first)
        right = find(second)
        if left == right:
            return
        if left < right:
            parents[right] = left
        else:
            parents[left] = right

    seen_edges: dict[tuple[str, str], int] = {}
    for index, member in enumerate(members):
        edges = [
            ("context", member["context_fingerprint"]),
            ("group", member["group_id"]),
        ]
        supplied_split_group = member["supplied_split_group_id"]
        if supplied_split_group is not None:
            edges.append(("split_group", supplied_split_group))
        for edge in edges:
            previous = seen_edges.setdefault(edge, index)
            union(index, previous)

    components: dict[int, list[dict[str, Any]]] = {}
    for index, member in enumerate(members):
        components.setdefault(find(index), []).append(member)
    families = [_family_from_members(component) for component in components.values()]
    families.sort(key=lambda row: row["family_id"])
    return families


def validate_duplicate_family(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one closed duplicate-family row and recompute its structure."""
    family = _exact_mapping(
        value,
        DUPLICATE_FAMILY_FIELDS,
        "duplicate family",
    )
    if family.get("schema_version") != DUPLICATE_FAMILY_SCHEMA_VERSION:
        raise ValueError("duplicate family schema_version is unsupported")
    family_id = family.get("family_id")
    if not isinstance(family_id, str) or _FAMILY_ID.fullmatch(family_id) is None:
        raise ValueError("duplicate family_id is invalid")
    members_value = family.get("members")
    if not isinstance(members_value, list) or not members_value:
        raise ValueError("duplicate family members must be a non-empty array")
    members: list[dict[str, Any]] = []
    for value_member in members_value:
        member = _exact_mapping(
            value_member,
            DUPLICATE_FAMILY_MEMBER_FIELDS,
            "duplicate family member",
        )
        _nonempty_string(member.get("case_id"), "duplicate family case_id")
        _nonempty_string(
            member.get("trust_tier"),
            "duplicate family trust_tier",
        )
        _require_sha256(
            member.get("context_fingerprint"),
            "duplicate family context_fingerprint",
        )
        _require_sha256(
            member.get("truth_fingerprint"),
            "duplicate family truth_fingerprint",
        )
        _nonempty_string(member.get("group_id"), "duplicate family group_id")
        for field in ("supplied_split_group_id", "early_split"):
            field_value = member.get(field)
            if field_value is not None:
                _nonempty_string(field_value, f"duplicate family {field}")
        members.append(member)
    expected_members = sorted(members, key=lambda row: row["case_id"])
    if members != expected_members:
        raise ValueError("duplicate family members are not canonical")
    if len({member["case_id"] for member in members}) != len(members):
        raise ValueError("duplicate family case_ids are not unique")
    if not _family_members_connected(members):
        raise ValueError("duplicate family members are not one connected component")
    expected = _family_from_members(members, validate=False)
    if family != expected:
        raise ValueError("duplicate family structure does not match its members")
    return _strict_json_value(family)


def _family_member(case: Mapping[str, Any]) -> dict[str, Any]:
    complete_case = _validate_case(case, derived=False)
    metadata = _mapping(complete_case["metadata"], "case metadata")
    group_id = _nonempty_string(metadata.get("group_id"), "case metadata group_id")
    trust_tier = _nonempty_string(
        metadata.get("trust_tier"),
        "case metadata trust_tier",
    )
    supplied_split_group = metadata.get("split_group_id")
    if supplied_split_group is not None:
        supplied_split_group = _nonempty_string(
            supplied_split_group,
            "case metadata split_group_id",
        )
    split_values = {
        _nonempty_string(metadata[field], f"case metadata {field}")
        for field in ("trusted_split", "early_split", "split")
        if field in metadata and metadata[field] is not None
    }
    if len(split_values) > 1:
        raise ValueError("case metadata declares conflicting early splits")
    early_split = next(iter(split_values), None)
    return {
        "case_id": complete_case["case_id"],
        "trust_tier": trust_tier,
        "context_fingerprint": model_visible_context_fingerprint(complete_case),
        "truth_fingerprint": expected_truth_fingerprint(complete_case),
        "group_id": group_id,
        "supplied_split_group_id": supplied_split_group,
        "early_split": early_split,
    }


def _family_members_connected(members: Sequence[Mapping[str, Any]]) -> bool:
    if not members:
        return False

    def edges(member: Mapping[str, Any]) -> set[tuple[str, str]]:
        values = {
            ("context", str(member["context_fingerprint"])),
            ("group", str(member["group_id"])),
        }
        split_group = member["supplied_split_group_id"]
        if split_group is not None:
            values.add(("split_group", str(split_group)))
        return values

    member_edges = [edges(member) for member in members]
    visited = {0}
    frontier = [0]
    while frontier:
        current = frontier.pop()
        for index, candidate_edges in enumerate(member_edges):
            if index not in visited and member_edges[current] & candidate_edges:
                visited.add(index)
                frontier.append(index)
    return len(visited) == len(members)


def _family_from_members(
    values: Sequence[Mapping[str, Any]],
    *,
    validate: bool = True,
) -> dict[str, Any]:
    members = [dict(value) for value in values]
    members.sort(key=lambda row: row["case_id"])
    context_fingerprints = sorted({str(member["context_fingerprint"]) for member in members})
    truth_fingerprints = sorted({str(member["truth_fingerprint"]) for member in members})
    group_ids = sorted({str(member["group_id"]) for member in members})
    supplied_groups = sorted(
        {
            str(member["supplied_split_group_id"])
            for member in members
            if member["supplied_split_group_id"] is not None
        }
    )
    if supplied_groups:
        split_group_id = supplied_groups[0]
        split_group_aliases = supplied_groups[1:]
    else:
        split_identity = fingerprint_json(
            {
                "schema_version": SPLIT_GROUP_IDENTITY_SCHEMA_VERSION,
                "group_ids": group_ids,
                "context_fingerprints": context_fingerprints,
            }
        )
        split_group_id = "splitgrp-" + split_identity.removeprefix("sha256:")[:24]
        split_group_aliases = []
    early_splits = sorted(
        {str(member["early_split"]) for member in members if member["early_split"] is not None}
    )
    assigned_early_split = early_splits[0] if len(early_splits) == 1 else None
    truth_by_context: dict[str, set[str]] = {}
    for member in members:
        truth_by_context.setdefault(member["context_fingerprint"], set()).add(member["truth_fingerprint"])
    hold_reasons = []
    if any(len(truths) > 1 for truths in truth_by_context.values()):
        hold_reasons.append("conflicting_expected_truth")
    if len(early_splits) > 1:
        hold_reasons.append("early_split_component_conflict")
    identity = fingerprint_json(
        {
            "schema_version": DUPLICATE_FAMILY_IDENTITY_SCHEMA_VERSION,
            "members": members,
        }
    )
    family = {
        "schema_version": DUPLICATE_FAMILY_SCHEMA_VERSION,
        "family_id": "family-" + identity.removeprefix("sha256:")[:24],
        "context_fingerprints": context_fingerprints,
        "group_ids": group_ids,
        "split_group_id": split_group_id,
        "split_group_aliases": split_group_aliases,
        "members": members,
        "truth_fingerprints": truth_fingerprints,
        "assigned_early_split": assigned_early_split,
        "hold_reasons": hold_reasons,
    }
    return validate_duplicate_family(family) if validate else family


def _validated_decision_authority(
    decisions: Sequence[Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(decisions, SequenceCollection) or isinstance(
        decisions,
        (str, bytes, bytearray),
    ):
        raise ReviewIntegrityError("current review decision authority is missing or malformed")
    authority: list[dict[str, Any]] = []
    for raw in decisions:
        if not isinstance(raw, Mapping):
            raise ReviewIntegrityError("current review decision authority is malformed")
        try:
            authority.append(validate_review_decision(raw))
        except (TypeError, ValueError) as exc:
            raise ReviewIntegrityError("current review decision authority is malformed") from exc
    return authority


def _matching_decisions(
    item: Mapping[str, Any],
    decisions: Sequence[Any] | None,
) -> tuple[list[dict[str, Any]], bool]:
    matches: list[dict[str, Any]] = []
    if not isinstance(decisions, SequenceCollection) or isinstance(
        decisions,
        (str, bytes, bytearray),
    ):
        return matches, True
    malformed = False
    for raw in decisions:
        if not isinstance(raw, Mapping):
            malformed = True
            continue
        try:
            decision = validate_review_decision(raw)
        except (TypeError, ValueError):
            malformed = True
            continue
        if decision["fingerprint"] != item["fingerprint"]:
            continue
        if decision["case_id"] != item["case_id"]:
            malformed = True
            continue
        matches.append(decision)
    return matches, malformed


def _pending_resolution(item: Mapping[str, Any]) -> dict[str, Any]:
    initial = item.get("initial_decision")
    initial_mapping = initial if isinstance(initial, Mapping) else {}
    case_id = item.get("case_id")
    fingerprint = item.get("fingerprint")
    return {
        "case_id": case_id if isinstance(case_id, str) else None,
        "fingerprint": fingerprint if isinstance(fingerprint, str) else None,
        "status": "pending",
        "decision_id": None,
        "reviewer": initial_mapping.get("reviewer"),
        "timestamp": initial_mapping.get("timestamp"),
        "note": None,
        "inherited_from": None,
    }


def _build_decision_row(
    *,
    case_id: str,
    fingerprint: str,
    status: str,
    reviewer: str,
    timestamp: str,
    note: str | None,
    inherited_from: Mapping[str, Any] | None,
    original_reviewer: str | None = None,
    original_timestamp: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": REVIEW_DECISION_SCHEMA_VERSION,
        "decision_id": "",
        "case_id": _nonempty_string(case_id, "review decision case_id"),
        "fingerprint": _require_sha256(
            fingerprint,
            "review decision fingerprint",
        ),
        "status": status,
        "reviewer": _nonempty_string(reviewer, "review decision reviewer"),
        "timestamp": _utc_timestamp(timestamp, "review decision timestamp"),
        "note": note,
        "inherited_from": (_strict_json_value(inherited_from) if inherited_from is not None else None),
    }
    if inherited_from is not None:
        row["original_reviewer"] = _nonempty_string(
            original_reviewer,
            "review decision original_reviewer",
        )
        row["original_timestamp"] = _utc_timestamp(
            original_timestamp,
            "review decision original_timestamp",
        )
    row["decision_id"] = _decision_id(row)
    return validate_review_decision(row)


def _decision_id(decision: Mapping[str, Any]) -> str:
    identity = {key: value for key, value in decision.items() if key != "decision_id"}
    return fingerprint_json(
        {
            "schema_version": REVIEW_DECISION_IDENTITY_SCHEMA_VERSION,
            "decision": identity,
        }
    )


def _review_fingerprint(
    case: Mapping[str, Any],
    dependency_sha256: str,
    source_provenance: Mapping[str, Any],
) -> str:
    return fingerprint_json(
        {
            "schema_version": DERIVED_REVIEW_FINGERPRINT_SCHEMA_VERSION,
            "case": case,
            "dependency_fingerprint": dependency_sha256,
            "source_provenance": source_provenance,
        }
    )


def _validate_case(
    value: Mapping[str, Any],
    *,
    derived: bool,
) -> dict[str, Any]:
    case = _mapping(value, "case")
    missing = {"case_id", "task_type", "context", "expected", "metadata"} - set(case)
    if missing:
        raise ValueError(f"case is missing fields {sorted(missing)}")
    _nonempty_string(case.get("case_id"), "case_id")
    _nonempty_string(case.get("task_type"), "task_type")
    _mapping(case.get("context"), "case context")
    _mapping(case.get("expected"), "case expected")
    metadata = _mapping(case.get("metadata"), "case metadata")
    if derived:
        _nonempty_string(metadata.get("trust_tier"), "case metadata trust_tier")
        forbidden = _RELEASE_LOCAL_METADATA_FIELDS & set(metadata)
        if forbidden:
            raise ValueError(
                "pre-publication review case contains release-local metadata " f"{sorted(forbidden)}"
            )
    return _strict_json_value(case)


def _require_scoreable(
    expected: Mapping[str, Any],
    scoreability: ScoreabilityCheck | None,
) -> None:
    if scoreability is None:
        return
    result = scoreability(dict(expected))
    if not isinstance(result, bool):
        raise TypeError("scoreability callback must return a boolean")
    if not result:
        raise ValueError("review case expected payload is not scoreable")


def _validate_dependency(value: Any) -> dict[str, Any]:
    dependency = _nonempty_mapping(value, "dependency")
    if dependency_matches(dependency, dependency):
        _validate_authentic_dependency_provenance(dependency)
        return dependency
    schema_version = dependency.get("schema_version")
    if schema_version == "fapo-stage6-dependency-v1":
        missing = _SCOUT_STAGE_SIX_DEPENDENCY_FIELDS - set(dependency)
        if missing:
            raise ValueError(f"dependency is missing fields {sorted(missing)}")
        _require_sha256(
            dependency.get("trusted_split_plan_sha256"),
            "dependency trusted_split_plan_sha256",
        )
        for field in ("cluster", "match", "guideline", "pipeline_settings"):
            _nonempty_mapping(dependency.get(field), f"dependency {field}")
        _validate_dependency_members(
            dependency.get("source_members"),
            fields=(
                "record_id",
                "prepared_record_sha256",
                "raw_record_sha256",
            ),
        )
    elif schema_version == "fapo-stage7-dependency-v1":
        missing = _SCOUT_STAGE_SEVEN_DEPENDENCY_FIELDS - set(dependency)
        if missing:
            raise ValueError(f"dependency is missing fields {sorted(missing)}")
        for field in ("cluster", "rubric", "pipeline_settings"):
            _nonempty_mapping(dependency.get(field), f"dependency {field}")
        _require_sha256(
            dependency.get("inference_dependency_fingerprint"),
            "dependency inference_dependency_fingerprint",
        )
        _validate_dependency_members(
            dependency.get("representative_members"),
            fields=("record_id", "prepared_record_sha256"),
        )
    else:
        raise ValueError("dependency schema is unsupported or unauthentic")
    _validate_dependency_provider(dependency.get("provider"))
    _validate_dependency_prompt(dependency.get("prompt"))
    return dependency


def _validate_authentic_dependency_provenance(
    dependency: Mapping[str, Any],
) -> None:
    schema_version = dependency.get("schema_version")
    descriptor = _nonempty_mapping(
        dependency.get("descriptor"),
        "dependency descriptor",
    )
    _nonempty_mapping(descriptor.get("cluster"), "dependency cluster")
    _validate_dependency_provider(descriptor.get("provider"))
    _validate_dependency_prompt(descriptor.get("prompt"))
    _nonempty_string(
        descriptor.get("algorithm_revision"),
        "dependency algorithm_revision",
    )
    if schema_version == STAGE_SIX_DEPENDENCY_SCHEMA_VERSION:
        _nonempty_mapping(descriptor.get("match"), "dependency match")
        _nonempty_mapping(descriptor.get("guideline"), "dependency guideline")
        _validate_fingerprinted_dependency_members(
            descriptor.get("source_members"),
            "dependency source_members",
        )
    elif schema_version == STAGE_SEVEN_DEPENDENCY_SCHEMA_VERSION:
        _nonempty_mapping(descriptor.get("rubric"), "dependency rubric")
        _validate_fingerprinted_dependency_members(
            descriptor.get("comparison_members"),
            "dependency comparison_members",
        )
        _nonempty_mapping(descriptor.get("settings"), "dependency settings")
        nested = descriptor.get("stage_six_dependency")
        _validate_dependency(nested)
    else:  # pragma: no cover - dependency_matches already excludes this case.
        raise ValueError("dependency schema is unsupported or unauthentic")


def _validate_fingerprinted_dependency_members(value: Any, label: str) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty array")
    members: list[dict[str, Any]] = []
    for raw in value:
        member = _exact_mapping(
            raw,
            _FINGERPRINTED_DEPENDENCY_MEMBER_FIELDS,
            "dependency member",
        )
        _nonempty_string(member.get("identity"), "dependency member identity")
        digest = member.get("content_sha256")
        if not isinstance(digest, str) or _RAW_SHA256.fullmatch(digest) is None:
            raise ValueError("dependency member content_sha256 is invalid")
        members.append(member)
    identities = [str(member["identity"]) for member in members]
    if len(set(identities)) != len(identities):
        raise ValueError("dependency member identities must be unique")
    if members != sorted(members, key=lambda member: str(member["identity"])):
        raise ValueError("dependency members are not canonical")


def _validate_dependency_members(value: Any, *, fields: tuple[str, ...]) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("dependency members must be a non-empty array")
    identities: list[str] = []
    for raw in value:
        member = _mapping(raw, "dependency member")
        record_id = _nonempty_string(
            member.get(fields[0]),
            f"dependency member {fields[0]}",
        )
        identities.append(record_id)
        for field in fields[1:]:
            _require_sha256(
                member.get(field),
                f"dependency member {field}",
            )
    if len(set(identities)) != len(identities):
        raise ValueError("dependency member identities must be unique")


def _validate_dependency_provider(value: Any) -> None:
    provider = _nonempty_mapping(value, "dependency provider")
    _nonempty_string(provider.get("provider"), "dependency provider identity")
    _nonempty_string(provider.get("model"), "dependency provider model")
    settings = provider.get("request_settings", provider.get("settings"))
    _nonempty_mapping(settings, "dependency provider settings")


def _validate_dependency_prompt(value: Any) -> None:
    prompt = _nonempty_mapping(value, "dependency prompt")
    name = prompt.get("name", prompt.get("revision"))
    _nonempty_string(name, "dependency prompt name")
    digest = prompt.get("sha256")
    if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest):
        return
    _require_sha256(digest, "dependency prompt sha256")


def _validate_source_provenance(value: Any) -> dict[str, Any]:
    source = _nonempty_mapping(value, "source_provenance")
    missing = _SOURCE_PROVENANCE_REQUIRED_FIELDS - set(source)
    if missing:
        raise ValueError(f"source_provenance is missing fields {sorted(missing)}")
    record_ids = source.get("source_record_ids")
    record_hashes = source.get("source_record_sha256s")
    if not isinstance(record_ids, list) or not record_ids:
        raise ValueError("source_provenance source_record_ids must be non-empty")
    if not isinstance(record_hashes, list) or len(record_hashes) != len(record_ids):
        raise ValueError("source_provenance record identities and hashes must align")
    normalized_ids = [_nonempty_string(record_id, "source_provenance record_id") for record_id in record_ids]
    if len(set(normalized_ids)) != len(normalized_ids):
        raise ValueError("source_provenance record_ids must be unique")
    for digest in record_hashes:
        _require_sha256(digest, "source_provenance record sha256")
    _nonempty_string(
        source.get("source_cluster"),
        "source_provenance source_cluster",
    )
    _nonempty_string(
        source.get("matched_intent_id"),
        "source_provenance matched_intent_id",
    )
    return source


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return _strict_json_value(value)


def _nonempty_mapping(value: Any, label: str) -> dict[str, Any]:
    output = _mapping(value, label)
    if not output:
        raise ValueError(f"{label} must not be empty")
    return output


def _exact_mapping(
    value: Any,
    fields: frozenset[str],
    label: str,
) -> dict[str, Any]:
    output = _mapping(value, label)
    if set(output) != fields:
        raise ValueError(f"{label} schema is invalid")
    return output


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical sha256 fingerprint")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _utc_timestamp(value: Any, label: str) -> str:
    timestamp = _nonempty_string(value, label)
    iso_timestamp = f"{timestamp.removesuffix('Z')}+00:00" if timestamp.endswith("Z") else timestamp
    try:
        parsed = datetime.fromisoformat(iso_timestamp)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{label} must be an ISO-8601 UTC timestamp")
    return timestamp


def _strict_json_value(value: Any, *, path: str = "$") -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite JSON numbers")
        return value
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, member in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} JSON object keys must be strings")
            output[key] = _strict_json_value(member, path=f"{path}.{key}")
        return output
    if isinstance(value, list):
        return [_strict_json_value(member, path=f"{path}[{index}]") for index, member in enumerate(value)]
    raise TypeError(f"{path} contains a non-JSON value")
