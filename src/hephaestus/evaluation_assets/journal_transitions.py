# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Pure, versioned state-transition plans for recovery journal operations."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)

JOURNAL_SCHEMA_VERSION = "fapo-recovery-journal-v2"


def canonical_jsonl_row_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize one row exactly as the durable JSONL writer does."""
    return (json.dumps(dict(payload), sort_keys=True) + "\n").encode("utf-8")


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
    serialized = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def derive_revision_plan(
    before_config: Mapping[str, Any],
    before_state: Mapping[str, Any],
    updates: Mapping[str, Any],
    *,
    operation_id: str,
    prepared_at: str,
    revision: int,
) -> dict[str, Any]:
    """Derive the only writer-reachable configuration revision payload."""
    unknown = set(updates) - set(CONFIG_STAGE_DEPENDENCIES)
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
        for key in CONFIG_STAGE_DEPENDENCIES
        if current.to_dict()[key] != target_config[key]
    }
    if not changes:
        raise ValueError("configuration revision is empty")
    ordered = list(PipelineStage)
    earliest = min(
        (CONFIG_STAGE_DEPENDENCIES[field] for field in changes),
        key=ordered.index,
    )
    invalidated = ordered[ordered.index(earliest) :]
    first_incomplete = next(
        (
            PipelineStage(str(item["stage"]))
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
    )
    result = {
        "changed_fields": changes,
        "invalidated_from_stage": earliest.value,
        "resume_from_stage": resume.value,
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
            "invalidated_from_stage": earliest.value,
            "resume_from_stage": resume.value,
        },
        "event_entry": {
            "timestamp": prepared_at,
            "event": "configuration_updated",
            "tenant_id": before_state["tenant_id"],
            "asset_id": before_state["asset_id"],
            "operation_id": operation_id,
            "details": result,
        },
        "invalidated_stages": [stage.value for stage in invalidated],
        "result": result,
    }


def derive_rebuild_plan(
    before_config: Mapping[str, Any],
    before_state: Mapping[str, Any],
    boundary: PipelineStage,
    *,
    operation_id: str,
    prepared_at: str,
) -> dict[str, Any]:
    """Derive the only writer-reachable checkpoint rebuild payload."""
    del before_config
    ordered = list(PipelineStage)
    invalidated = ordered[ordered.index(boundary) :]
    target_state = derive_mutable_target_state(
        before_state,
        invalidated,
        resume_stage=boundary,
        operation_id=operation_id,
        prepared_at=prepared_at,
    )
    return {
        "target_state": target_state,
        "event_entry": {
            "timestamp": prepared_at,
            "event": "checkpoint_rebuild_started",
            "tenant_id": before_state["tenant_id"],
            "asset_id": before_state["asset_id"],
            "operation_id": operation_id,
            "details": {"stage": boundary.value},
        },
        "invalidated_stages": [stage.value for stage in invalidated],
        "result": {"resume_from_stage": boundary.value},
    }


def derive_adoption_plan(
    before_config: Mapping[str, Any],
    before_state: Mapping[str, Any],
    target_receipts: Mapping[str, Mapping[str, Any]],
    *,
    operation_id: str,
    prepared_at: str,
) -> dict[str, Any]:
    """Derive the only writer-reachable explicit legacy adoption payload."""
    del before_config
    expected_stages = {stage.value for stage in PipelineStage}
    if set(target_receipts) != expected_stages:
        raise ValueError("adoption receipt inventory is incomplete")
    normalized_before = PipelineState.from_dict(dict(before_state))
    if not normalized_before.legacy_completed:
        raise ValueError("adoption before state is not a legacy completion")
    target_state = normalized_before.to_dict()
    target_state["schema_version"] = STATE_SCHEMA_VERSION
    target_state["status"] = "released"
    target_state["current_stage"] = None
    target_state["error"] = None
    target_state["updated_at"] = prepared_at
    target_state["mutation_sequence"] = normalized_before.mutation_sequence + 1
    target_state["last_operation_id"] = operation_id
    counts: dict[str, int] = {}
    receipt_hashes: dict[str, str] = {}
    for stage in PipelineStage:
        receipt = dict(target_receipts[stage.value])
        receipt_hashes[stage.value] = persisted_sha256(receipt)
        counts.update(dict(receipt["counts"]))
        stage_state = next(
            item
            for item in target_state["stages"]
            if item["stage"] == stage.value
        )
        stage_state["receipt_sha256"] = receipt_hashes[stage.value]
    target_state["counts"] = counts
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
        "result": {"status": "released"},
        "receipt_sha256": receipt_hashes,
    }


def derive_mutable_target_state(
    before_state: Mapping[str, Any],
    invalidated: Sequence[PipelineStage],
    *,
    resume_stage: PipelineStage,
    operation_id: str,
    prepared_at: str,
) -> dict[str, Any]:
    """Clone a state and blank exactly one declared suffix."""
    target = deepcopy(dict(before_state))
    invalidated_names = {stage.value for stage in invalidated}
    invalidated_count_keys = {
        key for stage in invalidated for key in STAGE_COUNT_KEYS[stage]
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
    target["current_stage"] = resume_stage.value
    target["error"] = None
    target["updated_at"] = prepared_at
    target["mutation_sequence"] = before_state["mutation_sequence"] + 1
    target["last_operation_id"] = operation_id
    return target
