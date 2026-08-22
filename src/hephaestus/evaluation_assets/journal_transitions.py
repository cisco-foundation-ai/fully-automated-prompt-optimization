# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Pure, versioned state-transition plans for recovery journal operations."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    LEGACY_STATE_SCHEMA_VERSION,
    STAGE_COUNT_KEYS,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
)

HISTORICAL_JOURNAL_SCHEMA_VERSION_V2 = "fapo-recovery-journal-v2"
HISTORICAL_JOURNAL_SCHEMA_VERSION_V3 = "fapo-recovery-journal-v3"
JOURNAL_SCHEMA_VERSION = HISTORICAL_JOURNAL_SCHEMA_VERSION_V3
PERSISTED_STAGE_VALUES_V2 = (
    "raw_inputs",
    "prepared_inputs",
    "rubric_extraction",
    "intent_clustering",
    "coverage_decisions",
    "label_inference",
    "synthetic_coverage",
    "dataset_splits",
)
PERSISTED_STAGE_INDEX_V2 = MappingProxyType(
    {
        value: index
        for index, value in enumerate(PERSISTED_STAGE_VALUES_V2, start=1)
    }
)
PERSISTED_STAGE_COUNT_KEYS_V2 = MappingProxyType(
    {
        "raw_inputs": frozenset({"feedback_records", "unlabeled_records"}),
        "prepared_inputs": frozenset({"prepared_feedback", "prepared_intents"}),
        "rubric_extraction": frozenset(
            {
                "feedback_evidence",
                "candidate_guidelines",
                "evaluation_guidelines",
                "trusted_cases",
            }
        ),
        "intent_clustering": frozenset({"intent_clusters"}),
        "coverage_decisions": frozenset(
            {
                "matched_clusters",
                "needs_more_feedback_clusters",
                "missing_label_clusters",
                "labeling_queue_clusters",
                "labeling_queue_traces",
            }
        ),
        "label_inference": frozenset({"inferred_cases", "review_clusters"}),
        "synthetic_coverage": frozenset(
            {"synthetic_cases", "rejected_synthetic_cases"}
        ),
        "dataset_splits": frozenset(
            {
                "dataset_cases",
                "train_cases",
                "validation_cases",
                "test_cases",
                "regression_trusted_cases",
                "triage_hold_cases",
            }
        ),
    }
)
PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2 = MappingProxyType(
    {
        "rubric_provider": "rubric_extraction",
        "rubric_model": "rubric_extraction",
        "batch_size": "rubric_extraction",
        "embedding_provider": "intent_clustering",
        "embedding_model": "intent_clustering",
        "cluster_count": "intent_clustering",
        "match_threshold": "coverage_decisions",
        "min_trusted_examples": "coverage_decisions",
        "min_trusted_groups": "coverage_decisions",
        "max_unlabeled_to_trusted_ratio": "coverage_decisions",
        "synthetic_coverage_enabled": "synthetic_coverage",
        "synthetic_cases_per_cluster": "synthetic_coverage",
        "split_seed": "dataset_splits",
    }
)
PERSISTED_CONFIG_STAGE_DEPENDENCIES_V3 = MappingProxyType(
    {
        "rubric_provider": "rubric_extraction",
        "rubric_model": "rubric_extraction",
        "batch_size": "rubric_extraction",
        "embedding_provider": "intent_clustering",
        "embedding_model": "intent_clustering",
        "cluster_count": "intent_clustering",
        "match_threshold": "coverage_decisions",
        "min_trusted_examples": "coverage_decisions",
        "min_trusted_groups": "coverage_decisions",
        "max_unlabeled_to_trusted_ratio": "coverage_decisions",
        "synthetic_coverage_enabled": "synthetic_coverage",
        "synthetic_cases_per_cluster": "synthetic_coverage",
        "split_seed": "prepared_inputs",
    }
)


@dataclass(frozen=True)
class JournalTransitionProfile:
    """Frozen transition registries selected by one persisted journal schema."""

    schema_version: str
    stage_values: tuple[str, ...]
    stage_count_keys: Mapping[str, frozenset[str]]
    config_stage_dependencies: Mapping[str, str]


_JOURNAL_TRANSITION_PROFILES = MappingProxyType(
    {
        HISTORICAL_JOURNAL_SCHEMA_VERSION_V2: JournalTransitionProfile(
            schema_version=HISTORICAL_JOURNAL_SCHEMA_VERSION_V2,
            stage_values=PERSISTED_STAGE_VALUES_V2,
            stage_count_keys=PERSISTED_STAGE_COUNT_KEYS_V2,
            config_stage_dependencies=PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2,
        ),
        HISTORICAL_JOURNAL_SCHEMA_VERSION_V3: JournalTransitionProfile(
            schema_version=HISTORICAL_JOURNAL_SCHEMA_VERSION_V3,
            stage_values=PERSISTED_STAGE_VALUES_V2,
            stage_count_keys=PERSISTED_STAGE_COUNT_KEYS_V2,
            config_stage_dependencies=PERSISTED_CONFIG_STAGE_DEPENDENCIES_V3,
        ),
    }
)


def journal_transition_profile(schema_version: Any) -> JournalTransitionProfile:
    """Return the immutable transition profile named by persisted authority."""
    try:
        return _JOURNAL_TRANSITION_PROFILES[str(schema_version)]
    except (KeyError, TypeError) as exc:
        raise ValueError("journal schema is unsupported") from exc


def _require_profile_stage_inventory(
    state: Mapping[str, Any],
    profile: JournalTransitionProfile,
) -> None:
    """Reject authoring changes that require an unversioned journal profile."""
    stages = state.get("stages")
    actual = (
        tuple(str(item.get("stage")) for item in stages)
        if isinstance(stages, list)
        and all(isinstance(item, Mapping) for item in stages)
        else ()
    )
    if actual != profile.stage_values:
        raise ValueError(
            "state stage inventory is incompatible with journal schema "
            f"{profile.schema_version}; define a new journal schema profile"
        )


if {
    field: stage.value for field, stage in CONFIG_STAGE_DEPENDENCIES.items()
} != dict(PERSISTED_CONFIG_STAGE_DEPENDENCIES_V3):
    raise RuntimeError("live and persisted v3 config dependencies differ")
if tuple(stage.value for stage in PipelineStage) != PERSISTED_STAGE_VALUES_V2 or {
    stage.value: frozenset(keys) for stage, keys in STAGE_COUNT_KEYS.items()
} != dict(PERSISTED_STAGE_COUNT_KEYS_V2):
    raise RuntimeError("live state/count shape differs from persisted v2")
_RELEASE_STAGE_VALUES_V2 = PERSISTED_STAGE_VALUES_V2
_RELEASE_STAGE_LABELS_V2 = MappingProxyType({
    "raw_inputs": "Validate raw inputs",
    "prepared_inputs": "Prepare canonical inputs",
    "rubric_extraction": "Create evaluation guidelines",
    "intent_clustering": "Mine intent clusters",
    "coverage_decisions": "Apply coverage decisions",
    "label_inference": "Infer reviewable labels",
    "synthetic_coverage": "Optional synthetic coverage",
    "dataset_splits": "Build dataset splits",
})
_RELEASE_COUNT_FIELDS_V2 = {
    "feedback_records",
    "unlabeled_records",
    "prepared_feedback",
    "prepared_intents",
    "feedback_evidence",
    "candidate_guidelines",
    "evaluation_guidelines",
    "trusted_cases",
    "intent_clusters",
    "matched_clusters",
    "needs_more_feedback_clusters",
    "missing_label_clusters",
    "labeling_queue_clusters",
    "labeling_queue_traces",
    "inferred_cases",
    "review_clusters",
    "synthetic_cases",
    "rejected_synthetic_cases",
    "dataset_cases",
    "train_cases",
    "validation_cases",
    "test_cases",
    "regression_trusted_cases",
    "triage_hold_cases",
}
if _RELEASE_COUNT_FIELDS_V2 != set().union(
    *PERSISTED_STAGE_COUNT_KEYS_V2.values()
):
    raise RuntimeError("persisted stage count profiles are inconsistent")
_LEGACY_STATE_FIELDS = {
    "tenant_id",
    "asset_id",
    "schema_version",
    "status",
    "current_stage",
    "created_at",
    "updated_at",
    "error",
    "counts",
    "stages",
    "mutation_sequence",
    "last_operation_id",
}
_LEGACY_STAGE_FIELDS = {
    "stage",
    "label",
    "status",
    "message",
    "started_at",
    "completed_at",
    "receipt_sha256",
}
_LEGACY_EVENT_FIELDS_V1 = frozenset(
    {"timestamp", "event", "tenant_id", "asset_id", "details"}
)
_LEGACY_EVENT_DETAIL_FIELDS_V1 = MappingProxyType(
    {
        "pipeline_created": frozenset({"status"}),
        "pipeline_extended": frozenset(
            {
                "parent_asset_id",
                "clustering_mode",
                "added_labeled_records",
                "added_unlabeled_records",
            }
        ),
        "pipeline_started": frozenset(),
        "stage_started": frozenset({"stage"}),
        "stage_failed": frozenset({"stage", "error"}),
        "stage_completed": frozenset({"stage", "counts"}),
        "pipeline_completed": frozenset({"counts"}),
        "configuration_updated": frozenset(
            {
                "revision",
                "changed_fields",
                "invalidated_from_stage",
                "resume_from_stage",
            }
        ),
    }
)
V2_OPERATION_EVENT_TYPES = frozenset(
    {
        "configuration_updated",
        "checkpoint_rebuild_started",
        "legacy_asset_adopted",
        "pipeline_extended",
        "pipeline_released",
    }
)
_LEGACY_SAFE_ASSET_ID_V1 = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$"
)
_LEGACY_CONFIG_DEPENDENCY_STAGE_V1 = MappingProxyType(
    {
        "rubric_provider": "rubric_extraction",
        "rubric_model": "rubric_extraction",
        "batch_size": "rubric_extraction",
        "embedding_provider": "intent_clustering",
        "embedding_model": "intent_clustering",
        "cluster_count": "intent_clustering",
        "match_threshold": "coverage_decisions",
        "min_trusted_examples": "coverage_decisions",
        "min_trusted_groups": "coverage_decisions",
        "max_unlabeled_to_trusted_ratio": "coverage_decisions",
        "synthetic_coverage_enabled": "synthetic_coverage",
        "synthetic_cases_per_cluster": "synthetic_coverage",
        "split_seed": "dataset_splits",
    }
)


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_counts(value: Any) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(key, str) and _is_nonnegative_int(count)
        for key, count in value.items()
    )


def _is_stage_or_none(value: Any) -> bool:
    return value is None or value in _RELEASE_STAGE_VALUES_V2


def _legacy_config_value(field: str, value: Any) -> bool:
    if field in {
        "rubric_provider",
        "rubric_model",
        "embedding_provider",
        "embedding_model",
    }:
        return isinstance(value, str) and bool(value)
    if field in {
        "batch_size",
        "cluster_count",
        "min_trusted_examples",
    }:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 1
    if field == "min_trusted_groups":
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    if field == "synthetic_cases_per_cluster":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and 1 <= value <= 100
        )
    if field == "split_seed":
        return isinstance(value, int) and not isinstance(value, bool)
    if field == "match_threshold":
        return isinstance(value, float) and 0.0 <= value <= 1.0
    if field == "max_unlabeled_to_trusted_ratio":
        return value is None or isinstance(value, float) and value > 0.0
    if field == "synthetic_coverage_enabled":
        return isinstance(value, bool)
    return False


def _legacy_changes(value: Any) -> dict[str, Mapping[str, Any]] | None:
    if not isinstance(value, Mapping):
        return None
    changes: dict[str, Mapping[str, Any]] = {}
    for key, raw_change in value.items():
        if (
            key not in _LEGACY_CONFIG_DEPENDENCY_STAGE_V1
            or not isinstance(raw_change, Mapping)
            or set(raw_change) != {"previous", "new"}
            or not _legacy_config_value(str(key), raw_change["previous"])
            or not _legacy_config_value(str(key), raw_change["new"])
            or raw_change["previous"] == raw_change["new"]
        ):
            return None
        changes[str(key)] = raw_change
    return changes


def _legacy_revision_boundaries(
    details: Mapping[str, Any],
    *,
    allow_empty: bool,
) -> bool:
    changes = _legacy_changes(details.get("changed_fields"))
    if changes is None:
        return False
    invalidated = details.get("invalidated_from_stage")
    resume = details.get("resume_from_stage")
    if not changes:
        return allow_empty and invalidated is None and resume is None
    expected = min(
        (_LEGACY_CONFIG_DEPENDENCY_STAGE_V1[key] for key in changes),
        key=PERSISTED_STAGE_VALUES_V2.index,
    )
    return (
        invalidated == expected
        and resume in PERSISTED_STAGE_VALUES_V2
        and PERSISTED_STAGE_VALUES_V2.index(resume)
        <= PERSISTED_STAGE_VALUES_V2.index(expected)
    )


def is_exact_legacy_event_row_v1(
    row: Mapping[str, Any],
    *,
    tenant_id: str,
    asset_id: str,
) -> bool:
    """Return whether a row has one exact schema emitted before v2 authority."""
    if set(row) != _LEGACY_EVENT_FIELDS_V1:
        return False
    timestamp = row.get("timestamp")
    try:
        parsed_timestamp = (
            datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else None
        )
    except ValueError:
        return False
    if (
        parsed_timestamp is None
        or parsed_timestamp.tzinfo is None
        or parsed_timestamp.utcoffset() != timedelta(0)
        or parsed_timestamp.isoformat() != timestamp
    ):
        return False
    if row.get("tenant_id") != tenant_id or row.get("asset_id") != asset_id:
        return False
    event = row.get("event")
    details = row.get("details")
    expected_fields = _LEGACY_EVENT_DETAIL_FIELDS_V1.get(event)
    if expected_fields is None or not isinstance(details, Mapping):
        return False
    if set(details) != expected_fields:
        return False
    if event == "pipeline_created":
        return details.get("status") in {"draft", "queued"}
    if event == "pipeline_extended":
        parent_asset_id = details.get("parent_asset_id")
        mode = details.get("clustering_mode")
        labeled = details.get("added_labeled_records")
        unlabeled = details.get("added_unlabeled_records")
        return (
            isinstance(parent_asset_id, str)
            and _LEGACY_SAFE_ASSET_ID_V1.fullmatch(parent_asset_id) is not None
            and parent_asset_id != asset_id
            and mode in {"keep", "refresh"}
            and _is_nonnegative_int(labeled)
            and _is_nonnegative_int(unlabeled)
            and labeled + unlabeled > 0
            and (mode == "refresh" or unlabeled == 0)
        )
    if event in {"stage_started", "stage_failed", "stage_completed"} and (
        details.get("stage") not in _RELEASE_STAGE_VALUES_V2
    ):
        return False
    if event == "stage_failed":
        return isinstance(details.get("error"), str)
    if event == "stage_completed":
        counts = details.get("counts")
        return _is_counts(counts) and set(counts) == (
            PERSISTED_STAGE_COUNT_KEYS_V2[details["stage"]]
        )
    if event == "pipeline_completed":
        counts = details.get("counts")
        return _is_counts(counts) and set(counts) == _RELEASE_COUNT_FIELDS_V2
    if event == "configuration_updated":
        return (
            _is_nonnegative_int(details.get("revision"))
            and details["revision"] > 0
            and _legacy_revision_boundaries(details, allow_empty=False)
        )
    return event in {"pipeline_started", "stage_started"}


def canonical_jsonl_row_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize one row exactly as the durable JSONL writer does."""
    return (
        json.dumps(dict(payload), sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def append_jsonl_bytes(before: bytes, payload: Mapping[str, Any]) -> bytes:
    """Return the byte-exact result of the durable append primitive."""
    separator = b"\n" if before and not before.endswith(b"\n") else b""
    return before + separator + canonical_jsonl_row_bytes(payload)


def audit_descriptor(data: bytes, *, present: bool) -> dict[str, Any]:
    """Describe one exact append-only audit prefix."""
    return {
        "present": present,
        "byte_length": len(data),
        "row_count": len(data.splitlines()),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def derive_audit_transition(
    before: bytes,
    *,
    present: bool,
    appended_row: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Describe the authenticated before and exact append target prefixes."""
    target = (
        append_jsonl_bytes(before, appended_row)
        if appended_row is not None
        else before
    )
    return {
        "before": audit_descriptor(before, present=present),
        "target": audit_descriptor(
            target,
            present=present or appended_row is not None,
        ),
    }


def persisted_sha256(payload: Mapping[str, Any]) -> str:
    """Hash the exact indented, sorted JSON representation used on disk."""
    serialized = (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def derive_revision_plan(
    before_config: Mapping[str, Any],
    before_state: Mapping[str, Any],
    updates: Mapping[str, Any],
    *,
    operation_id: str,
    prepared_at: str,
    revision: int,
    journal_schema_version: str = JOURNAL_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Derive the only writer-reachable configuration revision payload."""
    profile = journal_transition_profile(journal_schema_version)
    _require_profile_stage_inventory(before_state, profile)
    dependencies = profile.config_stage_dependencies
    unknown = set(updates) - set(dependencies)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unsupported pipeline decision fields: {names}")
    current = EvaluationAssetConfig.from_dict(before_config)
    if current.to_dict() != dict(before_config):
        raise ValueError("configuration revision before state is not canonical")
    merged = current.to_dict()
    merged.update(dict(updates))
    if "embedding_model" in updates:
        merged["embedding_provider"] = (
            "tfidf" if updates["embedding_model"] == "tfidf" else "openai"
        )
    target_config = EvaluationAssetConfig.from_dict(merged).to_dict()
    changes = {
        key: {"previous": current.to_dict()[key], "new": target_config[key]}
        for key in dependencies
        if current.to_dict()[key] != target_config[key]
    }
    if not changes:
        raise ValueError("configuration revision is empty")
    ordered = list(profile.stage_values)
    earliest = min(
        (dependencies[field] for field in changes),
        key=ordered.index,
    )
    invalidated = ordered[ordered.index(earliest) :]
    first_incomplete = next(
        (
            str(item["stage"])
            for item in before_state["stages"]
            if item["status"] != "completed"
        ),
        earliest,
    )
    resume = min((earliest, first_incomplete), key=ordered.index)
    target_state = derive_mutable_target_state(
        before_state,
        invalidated,
        resume_stage=resume,
        operation_id=operation_id,
        prepared_at=prepared_at,
        journal_schema_version=journal_schema_version,
    )
    result = {
        "changed_fields": changes,
        "invalidated_from_stage": earliest,
        "resume_from_stage": resume,
        "revision": revision,
    }
    return {
        "target_config": target_config,
        "target_state": target_state,
        "history_entry": {
            "timestamp": prepared_at,
            "revision": revision,
            "event": "configuration_updated",
            "operation_id": operation_id,
            "changed_fields": changes,
            "invalidated_from_stage": earliest,
            "resume_from_stage": resume,
        },
        "event_entry": {
            "timestamp": prepared_at,
            "event": "configuration_updated",
            "tenant_id": before_state["tenant_id"],
            "asset_id": before_state["asset_id"],
            "operation_id": operation_id,
            "details": result,
        },
        "invalidated_stages": invalidated,
        "result": result,
    }


def derive_rebuild_plan(
    before_config: Mapping[str, Any],
    before_state: Mapping[str, Any],
    boundary: PipelineStage | str,
    *,
    operation_id: str,
    prepared_at: str,
    journal_schema_version: str = JOURNAL_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Derive the only writer-reachable checkpoint rebuild payload."""
    del before_config
    profile = journal_transition_profile(journal_schema_version)
    _require_profile_stage_inventory(before_state, profile)
    ordered = list(profile.stage_values)
    boundary_value = str(getattr(boundary, "value", boundary))
    invalidated = ordered[ordered.index(boundary_value) :]
    target_state = derive_mutable_target_state(
        before_state,
        invalidated,
        resume_stage=boundary_value,
        operation_id=operation_id,
        prepared_at=prepared_at,
        journal_schema_version=journal_schema_version,
    )
    return {
        "target_state": target_state,
        "event_entry": {
            "timestamp": prepared_at,
            "event": "checkpoint_rebuild_started",
            "tenant_id": before_state["tenant_id"],
            "asset_id": before_state["asset_id"],
            "operation_id": operation_id,
            "details": {"stage": boundary_value},
        },
        "invalidated_stages": invalidated,
        "result": {"resume_from_stage": boundary_value},
    }


def normalized_legacy_state_v1(
    before_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize one exact receipt-free legacy state without live registries."""
    normalized = deepcopy(dict(before_state))
    normalized.setdefault("schema_version", LEGACY_STATE_SCHEMA_VERSION)
    normalized.setdefault("mutation_sequence", 0)
    normalized.setdefault("last_operation_id", None)
    if (
        set(normalized) != _LEGACY_STATE_FIELDS
        or normalized.get("schema_version") != LEGACY_STATE_SCHEMA_VERSION
        or normalized.get("status")
        not in {
            "draft",
            "queued",
            "running",
            "awaiting_review",
            "released",
            "failed",
            "completed",
        }
        or normalized.get("current_stage")
        not in {None, *PERSISTED_STAGE_VALUES_V2}
        or normalized.get("error") is not None
        and not isinstance(normalized.get("error"), str)
        or not isinstance(normalized.get("tenant_id"), str)
        or not normalized["tenant_id"]
        or not isinstance(normalized.get("asset_id"), str)
        or not normalized["asset_id"]
        or not isinstance(normalized.get("created_at"), str)
        or not isinstance(normalized.get("updated_at"), str)
        or isinstance(normalized.get("mutation_sequence"), bool)
        or not isinstance(normalized.get("mutation_sequence"), int)
        or normalized["mutation_sequence"] < 0
        or normalized.get("last_operation_id") is not None
        or not isinstance(normalized.get("counts"), Mapping)
        or any(
            not isinstance(key, str)
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for key, value in normalized["counts"].items()
        )
        or not isinstance(normalized.get("stages"), list)
        or len(normalized["stages"]) != len(_RELEASE_STAGE_VALUES_V2)
    ):
        raise ValueError("legacy state is invalid")
    normalized_stages: list[dict[str, Any]] = []
    for stage_value, raw_stage in zip(
        _RELEASE_STAGE_VALUES_V2,
        normalized["stages"],
    ):
        if not isinstance(raw_stage, Mapping):
            raise ValueError("adoption before stage is invalid")
        stage = dict(raw_stage)
        stage.setdefault("receipt_sha256", None)
        if (
            set(stage) != _LEGACY_STAGE_FIELDS
            or stage.get("stage") != stage_value
            or stage.get("label") != _RELEASE_STAGE_LABELS_V2[stage_value]
            or stage.get("status")
            not in {"pending", "running", "completed", "failed"}
            or not isinstance(stage.get("message"), str)
            or stage.get("started_at") is not None
            and not isinstance(stage.get("started_at"), str)
            or stage.get("completed_at") is not None
            and not isinstance(stage.get("completed_at"), str)
            or stage.get("receipt_sha256") is not None
        ):
            raise ValueError("legacy stage is invalid")
        normalized_stages.append(stage)
    normalized["stages"] = normalized_stages
    return normalized


def normalized_legacy_completed_state_v1(
    before_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize the frozen receipt-free legacy sentinel without registries."""
    normalized = normalized_legacy_state_v1(before_state)
    if (
        normalized.get("status") != "completed"
        or normalized.get("current_stage") is not None
        or normalized.get("error") is not None
        or any(stage.get("status") != "completed" for stage in normalized["stages"])
    ):
        raise ValueError("adoption before state is not a legacy completion")
    return normalized


def derive_adoption_plan(
    before_config: Mapping[str, Any],
    before_state: Mapping[str, Any],
    target_receipts: Mapping[str, Mapping[str, Any]],
    release_pointer: Mapping[str, Any],
    *,
    operation_id: str,
    prepared_at: str,
) -> dict[str, Any]:
    """Derive the only writer-reachable explicit legacy adoption payload."""
    del before_config
    expected_stages = set(_RELEASE_STAGE_VALUES_V2)
    if set(target_receipts) != expected_stages:
        raise ValueError("adoption receipt inventory is incomplete")
    target_state = normalized_legacy_completed_state_v1(before_state)
    target_state["schema_version"] = STATE_SCHEMA_VERSION
    target_state["status"] = "released"
    target_state["current_stage"] = None
    target_state["error"] = None
    target_state["updated_at"] = prepared_at
    target_state["mutation_sequence"] = target_state["mutation_sequence"] + 1
    target_state["last_operation_id"] = operation_id
    counts: dict[str, int] = {}
    receipt_hashes: dict[str, str] = {}
    for stage_value in _RELEASE_STAGE_VALUES_V2:
        receipt = dict(target_receipts[stage_value])
        receipt_hashes[stage_value] = persisted_sha256(receipt)
        counts.update(dict(receipt["counts"]))
        stage_state = next(
            item
            for item in target_state["stages"]
            if item["stage"] == stage_value
        )
        stage_state["receipt_sha256"] = receipt_hashes[stage_value]
    target_state["counts"] = counts
    pointer = dict(release_pointer)
    result = {
        "status": "released",
        "generation_id": pointer.get("generation_id"),
        "release_sha256": persisted_sha256(pointer),
        "stage_8_receipt_sha256": pointer.get("stage_8_receipt_sha256"),
    }
    return {
        "target_state": target_state,
        "event_entry": {
            "timestamp": prepared_at,
            "event": "legacy_asset_adopted",
            "tenant_id": before_state["tenant_id"],
            "asset_id": before_state["asset_id"],
            "operation_id": operation_id,
            "details": {"previous_status": "completed"},
        },
        "result": result,
        "receipt_sha256": receipt_hashes,
    }


def derive_release_publication_plan(
    before_config: Mapping[str, Any],
    before_state: Mapping[str, Any],
    release_pointer: Mapping[str, Any],
    *,
    operation_id: str,
    prepared_at: str,
    journal_schema_version: str = JOURNAL_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Derive the only writer-reachable native release publication payload."""
    del before_config
    journal_transition_profile(journal_schema_version)
    raw_stages = before_state.get("stages")
    mutation_sequence = before_state.get("mutation_sequence")
    if (
        before_state.get("schema_version") != STATE_SCHEMA_VERSION
        or before_state.get("status") != "running"
        or before_state.get("current_stage") is not None
        or before_state.get("error") is not None
        or not isinstance(raw_stages, list)
        or [
            item.get("stage") if isinstance(item, Mapping) else None
            for item in raw_stages
        ]
        != list(_RELEASE_STAGE_VALUES_V2)
        or any(
            not isinstance(item, Mapping)
            or item.get("status") != "completed"
            or item.get("receipt_sha256") is None
            for item in raw_stages
        )
        or not isinstance(before_state.get("counts"), Mapping)
        or set(before_state["counts"]) != _RELEASE_COUNT_FIELDS_V2
        or not isinstance(mutation_sequence, int)
        or isinstance(mutation_sequence, bool)
        or mutation_sequence < 0
    ):
        raise ValueError("release before state is not a complete running build")
    pointer = dict(release_pointer)
    generation_id = pointer.get("generation_id")
    release_result = {
        "status": "released",
        "generation_id": generation_id,
        "release_sha256": persisted_sha256(pointer),
        "stage_8_receipt_sha256": pointer.get("stage_8_receipt_sha256"),
    }
    target_state = deepcopy(dict(before_state))
    target_state["status"] = "released"
    target_state["current_stage"] = None
    target_state["error"] = None
    target_state["updated_at"] = prepared_at
    target_state["mutation_sequence"] = mutation_sequence + 1
    target_state["last_operation_id"] = operation_id
    return {
        "target_state": target_state,
        "event_entry": {
            "timestamp": prepared_at,
            "event": "pipeline_released",
            "tenant_id": before_state["tenant_id"],
            "asset_id": before_state["asset_id"],
            "operation_id": operation_id,
            "details": {
                key: value
                for key, value in release_result.items()
                if key != "status"
            },
        },
        "result": release_result,
    }


def derive_mutable_target_state(
    before_state: Mapping[str, Any],
    invalidated: Sequence[PipelineStage | str],
    *,
    resume_stage: PipelineStage | str,
    operation_id: str,
    prepared_at: str,
    journal_schema_version: str = JOURNAL_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Clone a state and blank exactly one declared suffix."""
    profile = journal_transition_profile(journal_schema_version)
    target = deepcopy(dict(before_state))
    invalidated_names = {
        str(getattr(stage, "value", stage)) for stage in invalidated
    }
    invalidated_count_keys = {
        key
        for stage in invalidated
        for key in profile.stage_count_keys[str(getattr(stage, "value", stage))]
    }
    target["counts"] = {
        key: value
        for key, value in target["counts"].items()
        if key not in invalidated_count_keys
    }
    for stage_state in target["stages"]:
        if stage_state["stage"] not in invalidated_names:
            continue
        stage_state.update(
            {
                "status": "pending",
                "message": "",
                "started_at": None,
                "completed_at": None,
                "receipt_sha256": None,
            }
        )
    target["status"] = "queued"
    target["current_stage"] = str(getattr(resume_stage, "value", resume_stage))
    target["error"] = None
    target["updated_at"] = prepared_at
    target["mutation_sequence"] = before_state["mutation_sequence"] + 1
    target["last_operation_id"] = operation_id
    return target
