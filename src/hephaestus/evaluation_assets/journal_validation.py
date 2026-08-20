# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Fail-closed validation for evaluation-asset recovery journal authority."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.control_jsonl import (
    parse_strict_jsonl_objects,
    read_strict_jsonl_objects,
)
from src.hephaestus.evaluation_assets.journal_transitions import (
    JOURNAL_SCHEMA_VERSION,
    append_jsonl_bytes,
    audit_descriptor,
    derive_adoption_plan,
    derive_rebuild_plan,
    derive_revision_plan,
)
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
    STAGE_LABELS,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)

_OPERATION_ID = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATE_FIELDS = {
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
_STAGE_STATE_FIELDS = {
    "stage",
    "label",
    "status",
    "message",
    "started_at",
    "completed_at",
    "receipt_sha256",
}
_STAGE_STATUSES = {"pending", "running", "completed", "failed"}
_CONFIG_FIELDS = set(EvaluationAssetConfig.__dataclass_fields__)
_ALL_COUNT_KEYS = set().union(*STAGE_COUNT_KEYS.values())
_EVENT_FIELDS = {
    "timestamp",
    "event",
    "tenant_id",
    "asset_id",
    "operation_id",
    "details",
}
_COMMITTED_FIELDS = {
    "schema_version",
    "operation_id",
    "kind",
    "phase",
    "committed_at",
}
_PREPARED_FIELDS = {
    "configuration_revision": {
        "schema_version",
        "operation_id",
        "kind",
        "phase",
        "prepared_at",
        "request",
        "before_config",
        "before_state",
        "before",
        "target",
        "target_config",
        "target_state",
        "history_entry",
        "event_entry",
        "invalidated_stages",
        "result",
        "audit",
    },
    "checkpoint_rebuild": {
        "schema_version",
        "operation_id",
        "kind",
        "phase",
        "prepared_at",
        "request",
        "before_config",
        "before_state",
        "before",
        "target",
        "target_state",
        "event_entry",
        "invalidated_stages",
        "result",
        "audit",
    },
    "legacy_adoption": {
        "schema_version",
        "operation_id",
        "kind",
        "phase",
        "prepared_at",
        "request",
        "before_config",
        "before_state",
        "before",
        "target",
        "target_receipts",
        "target_state",
        "event_entry",
        "result",
        "audit",
    },
}


@dataclass(frozen=True)
class ValidatedRecoveryJournal:
    """Authenticated operation ledger returned to release and recovery callers."""

    prepared: tuple[dict[str, Any], ...]
    committed_operation_ids: frozenset[str]
    outstanding: dict[str, Any] | None


def validate_recovery_journal(
    layout: Any,
    entries: Sequence[Mapping[str, Any]],
) -> ValidatedRecoveryJournal:
    """Validate the complete log and every uncommitted intermediate state."""
    prepared: dict[str, dict[str, Any]] = {}
    committed: dict[str, dict[str, Any]] = {}
    seen_operations: set[str] = set()
    active: tuple[str, str] | None = None
    for raw in entries:
        row = _mapping(raw)
        if row.get("schema_version") != JOURNAL_SCHEMA_VERSION:
            raise ValueError("journal schema is unsupported")
        operation_id = row.get("operation_id")
        phase = row.get("phase")
        kind = row.get("kind")
        if (
            not isinstance(operation_id, str)
            or not _OPERATION_ID.fullmatch(operation_id)
            or phase not in {"prepared", "committed"}
            or kind not in _PREPARED_FIELDS
        ):
            raise ValueError("journal operation identity is invalid")
        if phase == "prepared":
            if active is not None or operation_id in seen_operations:
                raise ValueError("journal operations are not contiguous")
            _exact_keys(row, _PREPARED_FIELDS[str(kind)])
            _utc_timestamp(row.get("prepared_at"))
            seen_operations.add(operation_id)
            active = (operation_id, str(kind))
            prepared[operation_id] = row
        else:
            if active != (operation_id, str(kind)):
                raise ValueError("journal commit is not contiguous with its prepare")
            _exact_keys(row, _COMMITTED_FIELDS)
            committed_at = _utc_timestamp(row.get("committed_at"))
            if committed_at < _utc_timestamp(prepared[operation_id]["prepared_at"]):
                raise ValueError("journal commit timestamp is invalid")
            committed[operation_id] = row
            active = None
    outstanding = set(prepared) - set(committed)
    if len(outstanding) > 1 or (bool(outstanding) != (active is not None)):
        raise ValueError("journal has competing uncommitted operations")
    prepared_rows = tuple(prepared.values())
    for index, row in enumerate(prepared_rows):
        operation_id = str(row["operation_id"])
        _validate_prepared(
            layout,
            row,
            uncommitted=operation_id in outstanding,
            final_operation=index == len(prepared_rows) - 1,
        )
        if index:
            previous = prepared_rows[index - 1]
            previous_operation = str(previous["operation_id"])
            if previous_operation not in committed:
                raise ValueError("journal chronology follows an uncommitted operation")
            _validate_operation_chronology(
                layout,
                previous,
                committed[previous_operation],
                row,
            )
    outstanding_row = (
        prepared[next(iter(outstanding))] if outstanding else None
    )
    return ValidatedRecoveryJournal(
        prepared=prepared_rows,
        committed_operation_ids=frozenset(committed),
        outstanding=outstanding_row,
    )


def _validate_prepared(
    layout: Any,
    row: Mapping[str, Any],
    *,
    uncommitted: bool,
    final_operation: bool,
) -> None:
    operation_id = str(row["operation_id"])
    kind = str(row["kind"])
    before = _hash_mapping(row["before"])
    target = _hash_mapping(row["target"])
    expected_hash_fields = (
        {"config_sha256", "state_sha256", "receipt_sha256"}
        if kind == "legacy_adoption"
        else {"config_sha256", "state_sha256"}
    )
    if set(before) != {"config_sha256", "state_sha256"} or set(target) != expected_hash_fields:
        raise ValueError("journal control hashes are incomplete")

    before_config = _mapping(row["before_config"])
    _validate_config_shape(before_config)
    canonical_before_config = EvaluationAssetConfig.from_dict(before_config).to_dict()
    before_state = _mapping(row["before_state"])
    _validate_before_state_shape(before_state)
    if (
        canonical_before_config != before_config
        or canonical_before_config.get("tenant_id") != layout.tenant_id
        or canonical_before_config.get("asset_id") != layout.asset_id
        or before_state.get("tenant_id") != layout.tenant_id
        or before_state.get("asset_id") != layout.asset_id
        or _persisted_sha256(before_config) != before["config_sha256"]
        or _persisted_sha256(before_state) != before["state_sha256"]
    ):
        raise ValueError("journal before snapshots are inconsistent")

    state_raw = _mapping(row["target_state"])
    _validate_state_shape(state_raw)
    state = PipelineState.from_dict(state_raw)
    if (
        state.to_dict() != state_raw
        or state.tenant_id != layout.tenant_id
        or state.asset_id != layout.asset_id
        or state.last_operation_id != operation_id
        or state.mutation_sequence < 1
        or _persisted_sha256(state_raw) != target["state_sha256"]
    ):
        raise ValueError("journal target state is inconsistent")

    if kind == "configuration_revision":
        config_raw = _mapping(row["target_config"])
        _validate_config_shape(config_raw)
        config = EvaluationAssetConfig.from_dict(config_raw)
        if (
            config.to_dict() != config_raw
            or config.tenant_id != layout.tenant_id
            or config.asset_id != layout.asset_id
            or _persisted_sha256(config_raw) != target["config_sha256"]
        ):
            raise ValueError("journal target config is inconsistent")
        request = _mapping(row["request"])
        _exact_keys(request, {"updates"})
        updates = _mapping(request["updates"])
        history = _mapping(row["history_entry"])
        revision = history.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool):
            raise ValueError("configuration revision number is invalid")
        plan = derive_revision_plan(
            before_config,
            before_state,
            updates,
            operation_id=operation_id,
            prepared_at=str(row["prepared_at"]),
            revision=revision,
        )
        _require_exact_plan(row, plan)
        _validate_revision(
            layout,
            row,
            state,
            config_raw,
            before,
            operation_id,
        )
    else:
        if target["config_sha256"] != before["config_sha256"]:
            raise ValueError("journal unexpectedly changes configuration")
        if kind == "checkpoint_rebuild":
            request = _mapping(row["request"])
            _exact_keys(request, {"boundary"})
            try:
                boundary = PipelineStage(request["boundary"])
            except (TypeError, ValueError) as exc:
                raise ValueError("checkpoint boundary request is invalid") from exc
            plan = derive_rebuild_plan(
                before_config,
                before_state,
                boundary,
                operation_id=operation_id,
                prepared_at=str(row["prepared_at"]),
            )
            _require_exact_plan(row, plan)
            _validate_rebuild(row, state, operation_id)
        else:
            request = _mapping(row["request"])
            _exact_keys(request, set())
            receipts = _mapping(row["target_receipts"])
            plan = derive_adoption_plan(
                before_config,
                before_state,
                receipts,
                operation_id=operation_id,
                prepared_at=str(row["prepared_at"]),
            )
            _require_exact_plan(row, plan, excluded={"receipt_sha256"})
            if target.get("receipt_sha256") != plan["receipt_sha256"]:
                raise ValueError("adoption target receipt hashes are inconsistent")
            _validate_adoption(layout, row, state, operation_id, target)

    _validate_event(layout, row, operation_id)
    history_installed, event_installed = _validate_audit_authority(
        layout,
        row,
        uncommitted=uncommitted,
    )
    installed_receipts: list[bool] = []
    if kind == "legacy_adoption":
        receipt_hashes = _mapping(target["receipt_sha256"])
        for stage in PipelineStage:
            path = layout.receipt_path(stage)
            installed_receipts.append(path.is_file())
            if path.is_file() and _file_sha256(path) != receipt_hashes[stage.value]:
                raise ValueError(
                    "installed adoption receipt is not a target intermediate"
                )
        prefix_length = sum(installed_receipts)
        if installed_receipts != [
            index < prefix_length for index in range(len(PipelineStage))
        ]:
            raise ValueError("installed adoption receipts are not an ordered prefix")
    if not uncommitted:
        if kind == "legacy_adoption" and not all(installed_receipts):
            raise ValueError("committed adoption receipt authority is incomplete")
        if kind == "legacy_adoption":
            if not final_operation:
                raise ValueError("committed adoption is not terminal")
            _validate_committed_adoption_terminal(layout, row, target)
        elif final_operation:
            _validate_committed_mutation_terminal(layout, row, target)
        return
    _validate_intermediate_authority(
        layout,
        row,
        before,
        target,
        history_installed=history_installed,
        event_installed=event_installed,
    )
    if kind == "legacy_adoption":
        if _file_sha256(layout.state_path) == target["state_sha256"] and not all(
            installed_receipts
        ):
            raise ValueError("adoption state precedes its receipt authority")


def _validate_revision(
    layout: Any,
    row: Mapping[str, Any],
    state: PipelineState,
    target_config: Mapping[str, Any],
    before: Mapping[str, Any],
    operation_id: str,
) -> None:
    invalidated = _stage_suffix(row["invalidated_stages"])
    result = _mapping(row["result"])
    history = _mapping(row["history_entry"])
    _exact_keys(
        history,
        {
            "timestamp",
            "revision",
            "event",
            "operation_id",
            "changed_fields",
            "invalidated_from_stage",
            "resume_from_stage",
        },
    )
    _exact_keys(
        result,
        {
            "revision",
            "changed_fields",
            "invalidated_from_stage",
            "resume_from_stage",
        },
    )
    changed_fields = _mapping(result.get("changed_fields"))
    if history.get("changed_fields") != changed_fields or not changed_fields:
        raise ValueError("configuration revision changes are inconsistent")
    before_config = dict(target_config)
    for field, raw_change in changed_fields.items():
        if field not in CONFIG_STAGE_DEPENDENCIES:
            raise ValueError("configuration revision field is unsupported")
        change = _mapping(raw_change)
        _exact_keys(change, {"previous", "new"})
        if change["previous"] == change["new"] or (
            target_config.get(field) != change["new"]
        ):
            raise ValueError("configuration revision change is inconsistent")
        before_config[field] = change["previous"]
    _validate_config_shape(before_config)
    EvaluationAssetConfig.from_dict(before_config)
    if _persisted_sha256(before_config) != before["config_sha256"]:
        raise ValueError("configuration revision prior config is inconsistent")
    ordered = tuple(PipelineStage)
    earliest = min(
        (CONFIG_STAGE_DEPENDENCIES[field] for field in changed_fields),
        key=ordered.index,
    )
    resume = _validate_mutable_target_state(state, invalidated)
    if (
        history.get("operation_id") != operation_id
        or history.get("event") != "configuration_updated"
        or not isinstance(history.get("revision"), int)
        or isinstance(history.get("revision"), bool)
        or history.get("revision", 0) < 2
        or result.get("revision") != history.get("revision")
        or history.get("timestamp") != row.get("prepared_at")
        or result.get("invalidated_from_stage") != earliest.value
        or history.get("invalidated_from_stage") != earliest.value
        or invalidated[0] != earliest
        or result.get("resume_from_stage") != resume.value
        or history.get("resume_from_stage") != resume.value
        or state.current_stage != resume.value
        or state.updated_at != row.get("prepared_at")
    ):
        raise ValueError("configuration revision journal payload is inconsistent")
    _validate_existing_revision_sequence(layout, history, operation_id)


def _validate_rebuild(
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
) -> None:
    del operation_id
    invalidated = _stage_suffix(row["invalidated_stages"])
    result = _mapping(row["result"])
    _exact_keys(result, {"resume_from_stage"})
    resume = _validate_mutable_target_state(state, invalidated)
    if (
        result["resume_from_stage"] != invalidated[0].value
        or resume != invalidated[0]
        or state.current_stage != invalidated[0].value
        or state.updated_at != row.get("prepared_at")
    ):
        raise ValueError("checkpoint rebuild journal payload is inconsistent")


def _validate_adoption(
    layout: Any,
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
    target: Mapping[str, Any],
) -> None:
    receipts = _mapping(row["target_receipts"])
    receipt_hashes = _mapping(target["receipt_sha256"])
    expected = {stage.value for stage in PipelineStage}
    if set(receipts) != expected or set(receipt_hashes) != expected:
        raise ValueError("adoption receipt inventory is incomplete")
    for stage in PipelineStage:
        receipt = _mapping(receipts[stage.value])
        counts = _mapping(receipt.get("counts"))
        if (
            receipt.get("stage") != stage.value
            or receipt.get("origin") != "legacy_adoption"
            or set(counts) != STAGE_COUNT_KEYS[stage]
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in counts.values()
            )
            or _persisted_sha256(receipt) != receipt_hashes[stage.value]
        ):
            raise ValueError("adoption receipt target is inconsistent")
        stage_state = next(item for item in state.stages if item.stage == stage.value)
        if (
            stage_state.status != "completed"
            or stage_state.receipt_sha256 != receipt_hashes[stage.value]
            or any(state.counts.get(key) != value for key, value in counts.items())
        ):
            raise ValueError("adoption state receipt authority is inconsistent")
    if (
        state.schema_version != STATE_SCHEMA_VERSION
        or state.status != "released"
        or state.current_stage is not None
        or state.error is not None
        or row["result"] != {"status": "released"}
        or layout.tenant_id != state.tenant_id
        or state.updated_at != row.get("prepared_at")
        or state.last_operation_id != operation_id
        or set(state.counts) != _ALL_COUNT_KEYS
    ):
        raise ValueError("adoption target lifecycle is inconsistent")


def _validate_operation_chronology(
    layout: Any,
    previous: Mapping[str, Any],
    previous_commit: Mapping[str, Any],
    current: Mapping[str, Any],
) -> None:
    if previous["kind"] == "legacy_adoption":
        raise ValueError("journal operation follows a terminal adoption")
    previous_state = _mapping(previous["target_state"])
    current_before_state = _mapping(current["before_state"])
    previous_target = _hash_mapping(previous["target"])
    current_before = _hash_mapping(current["before"])
    if (
        _utc_timestamp(current["prepared_at"])
        < _utc_timestamp(previous_commit["committed_at"])
        or current_before["config_sha256"] != previous_target["config_sha256"]
        or current_before_state.get("created_at") != previous_state.get("created_at")
        or current_before_state.get("mutation_sequence")
        != previous_state.get("mutation_sequence")
        or current_before_state.get("last_operation_id")
        != previous.get("operation_id")
    ):
        raise ValueError("journal operations are not chained in writer chronology")
    previous_audit = _mapping(previous["audit"])
    current_audit = _mapping(current["audit"])
    previous_history = _audit_descriptor_mapping(
        _mapping(previous_audit["config_history"])["target"]
    )
    current_history = _audit_descriptor_mapping(
        _mapping(current_audit["config_history"])["before"]
    )
    if previous_history != current_history:
        raise ValueError("journal configuration-history chronology is inconsistent")
    previous_events = _audit_descriptor_mapping(
        _mapping(previous_audit["events"])["target"]
    )
    current_events = _audit_descriptor_mapping(
        _mapping(current_audit["events"])["before"]
    )
    if (
        previous_events["present"] and not current_events["present"]
        or previous_events["byte_length"] > current_events["byte_length"]
        or previous_events["row_count"] > current_events["row_count"]
    ):
        raise ValueError("journal event chronology is inconsistent")
    current_bytes = (
        layout.events_path.read_bytes() if layout.events_path.is_file() else b""
    )
    previous_prefix = current_bytes[: previous_events["byte_length"]]
    later_prefix = current_bytes[: current_events["byte_length"]]
    if (
        audit_descriptor(previous_prefix, present=previous_events["present"])
        != previous_events
        or audit_descriptor(later_prefix, present=current_events["present"])
        != current_events
    ):
        raise ValueError("journal event prefixes are not monotonic")


def _validate_committed_adoption_terminal(
    layout: Any,
    row: Mapping[str, Any],
    target: Mapping[str, Any],
) -> None:
    if (
        _file_sha256(layout.config_path) != target["config_sha256"]
        or _file_sha256(layout.state_path) != target["state_sha256"]
    ):
        raise ValueError("committed adoption controls are not at the target")
    audit = _mapping(row["audit"])
    for name, path in (
        ("config_history", layout.config_history_path),
        ("events", layout.events_path),
    ):
        target_descriptor = _audit_descriptor_mapping(
            _mapping(audit[name])["target"]
        )
        present = path.is_file()
        current = path.read_bytes() if present else b""
        if audit_descriptor(current, present=present) != target_descriptor:
            raise ValueError("committed adoption audit is not at the target")


def _validate_committed_mutation_terminal(
    layout: Any,
    row: Mapping[str, Any],
    target: Mapping[str, Any],
) -> None:
    if _file_sha256(layout.config_path) != target["config_sha256"]:
        raise ValueError("committed mutation config is not at the target")
    audit = _mapping(row["audit"])
    target_descriptor = _audit_descriptor_mapping(
        _mapping(audit["config_history"])["target"]
    )
    present = layout.config_history_path.is_file()
    current = layout.config_history_path.read_bytes() if present else b""
    if audit_descriptor(current, present=present) != target_descriptor:
        raise ValueError("committed mutation config history is not at the target")


def _validate_event(
    layout: Any,
    prepared: Mapping[str, Any],
    operation_id: str,
) -> None:
    row = _mapping(prepared["event_entry"])
    _exact_keys(row, _EVENT_FIELDS)
    kind = prepared["kind"]
    if kind == "configuration_revision":
        expected_event = "configuration_updated"
        expected_details = prepared["result"]
    elif kind == "checkpoint_rebuild":
        expected_event = "checkpoint_rebuild_started"
        expected_details = {"stage": prepared["result"]["resume_from_stage"]}
    else:
        expected_event = "legacy_asset_adopted"
        expected_details = {"previous_status": "completed"}
    if (
        row.get("operation_id") != operation_id
        or row.get("tenant_id") != layout.tenant_id
        or row.get("asset_id") != layout.asset_id
        or row.get("event") != expected_event
        or row.get("timestamp") != prepared.get("prepared_at")
        or row.get("details") != expected_details
    ):
        raise ValueError("journal event identity is inconsistent")


def _validate_mutable_target_state(
    state: PipelineState,
    invalidated: tuple[PipelineStage, ...],
) -> PipelineStage:
    invalidated_names = {stage.value for stage in invalidated}
    invalidated_count_keys = {
        key for stage in invalidated for key in STAGE_COUNT_KEYS[stage]
    }
    for item in state.stages:
        if item.stage in invalidated_names and (
            item.status != "pending"
            or item.message != ""
            or item.started_at is not None
            or item.completed_at is not None
            or item.receipt_sha256 is not None
        ):
            raise ValueError("journal target state retains invalidated authority")
    first_incomplete = next(
        (
            PipelineStage(item.stage)
            for item in state.stages
            if item.status != "completed"
        ),
        None,
    )
    if (
        state.schema_version != STATE_SCHEMA_VERSION
        or state.status != "queued"
        or state.error is not None
        or first_incomplete is None
        or state.current_stage != first_incomplete.value
        or any(key in state.counts for key in invalidated_count_keys)
    ):
        raise ValueError("journal target lifecycle is inconsistent")
    first_index = tuple(PipelineStage).index(first_incomplete)
    if any(
        item.status == "completed" for item in state.stages[first_index + 1 :]
    ):
        raise ValueError("journal target prefix is not resumable")
    return first_incomplete


def _require_exact_plan(
    row: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    excluded: set[str] | None = None,
) -> None:
    for field, expected in plan.items():
        if field in (excluded or set()):
            continue
        if row.get(field) != expected:
            raise ValueError("journal target is not writer-derived")


def _validate_before_state_shape(raw: Mapping[str, Any]) -> None:
    if raw.get("status") == "completed":
        optional = {"schema_version", "mutation_sequence", "last_operation_id"}
        if not (_STATE_FIELDS - optional) <= set(raw) <= _STATE_FIELDS:
            raise ValueError("journal before state shape is invalid")
        for value in raw.get("stages", []):
            item = _mapping(value)
            if not (
                _STAGE_STATE_FIELDS - {"receipt_sha256"}
            ) <= set(item) <= _STAGE_STATE_FIELDS:
                raise ValueError("journal before stage state is invalid")
        normalized = PipelineState.from_dict(raw)
        if not normalized.legacy_completed:
            raise ValueError("journal before state shape is invalid")
        raw = normalized.to_dict()
    else:
        _exact_keys(raw, _STATE_FIELDS)
    if (
        raw.get("schema_version")
        not in {"fapo-evaluation-asset-state-v1", STATE_SCHEMA_VERSION}
        or raw.get("status")
        not in {
            "draft",
            "queued",
            "running",
            "awaiting_review",
            "released",
            "failed",
            "completed",
        }
        or not _nonempty_string(raw.get("tenant_id"))
        or not _nonempty_string(raw.get("asset_id"))
        or not isinstance(raw.get("counts"), Mapping)
        or not isinstance(raw.get("stages"), list)
        or isinstance(raw.get("mutation_sequence"), bool)
        or not isinstance(raw.get("mutation_sequence"), int)
        or raw.get("mutation_sequence", -1) < 0
    ):
        raise ValueError("journal before state shape is invalid")
    last_operation = raw.get("last_operation_id")
    if last_operation is not None and (
        not isinstance(last_operation, str) or not _OPERATION_ID.fullmatch(last_operation)
    ):
        raise ValueError("journal before mutation identity is invalid")
    _utc_timestamp(raw.get("created_at"))
    _utc_timestamp(raw.get("updated_at"))
    if raw.get("error") is not None and not isinstance(raw.get("error"), str):
        raise ValueError("journal before error is invalid")
    current_stage = raw.get("current_stage")
    if current_stage is not None:
        try:
            PipelineStage(current_stage)
        except (TypeError, ValueError) as exc:
            raise ValueError("journal before current stage is invalid") from exc
    counts = _mapping(raw["counts"])
    if set(counts) - _ALL_COUNT_KEYS or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in counts.values()
    ):
        raise ValueError("journal before counts are invalid")
    stages = list(raw["stages"])
    ordered = tuple(PipelineStage)
    if len(stages) != len(ordered):
        raise ValueError("journal before stage inventory is invalid")
    for stage, value in zip(ordered, stages):
        item = _mapping(value)
        _exact_keys(item, _STAGE_STATE_FIELDS)
        if (
            item.get("stage") != stage.value
            or item.get("label") != STAGE_LABELS[stage]
            or item.get("status") not in _STAGE_STATUSES
            or not isinstance(item.get("message"), str)
        ):
            raise ValueError("journal before stage state is invalid")
        for field in ("started_at", "completed_at"):
            if item.get(field) is not None:
                _utc_timestamp(item[field])
        receipt = item.get("receipt_sha256")
        if receipt is not None and (
            not isinstance(receipt, str) or not _SHA256.fullmatch(receipt)
        ):
            raise ValueError("journal before stage receipt is invalid")
        if item["status"] == "pending" and any(
            item[field] not in {None, ""}
            for field in (
                "message",
                "started_at",
                "completed_at",
                "receipt_sha256",
            )
        ):
            raise ValueError("journal before pending stage retains authority")
        if item["status"] == "completed" and (
            item["started_at"] is None or item["completed_at"] is None
        ):
            raise ValueError("journal before completed stage lacks timestamps")
        if item["status"] in {"running", "failed"} and (
            item["started_at"] is None or item["completed_at"] is not None
        ):
            raise ValueError("journal before active stage state is invalid")


def _validate_state_shape(raw: Mapping[str, Any]) -> None:
    _exact_keys(raw, _STATE_FIELDS)
    if (
        raw.get("schema_version") != STATE_SCHEMA_VERSION
        or not _nonempty_string(raw.get("tenant_id"))
        or not _nonempty_string(raw.get("asset_id"))
        or not isinstance(raw.get("counts"), Mapping)
        or not isinstance(raw.get("stages"), list)
        or isinstance(raw.get("mutation_sequence"), bool)
        or not isinstance(raw.get("mutation_sequence"), int)
        or raw.get("mutation_sequence", 0) < 1
        or not isinstance(raw.get("last_operation_id"), str)
        or not _OPERATION_ID.fullmatch(str(raw.get("last_operation_id")))
    ):
        raise ValueError("journal target state shape is invalid")
    _utc_timestamp(raw.get("created_at"))
    _utc_timestamp(raw.get("updated_at"))
    if raw.get("error") is not None and not isinstance(raw.get("error"), str):
        raise ValueError("journal target error is invalid")
    current_stage = raw.get("current_stage")
    if current_stage is not None:
        try:
            PipelineStage(current_stage)
        except (TypeError, ValueError) as exc:
            raise ValueError("journal target current stage is invalid") from exc
    counts = _mapping(raw["counts"])
    if set(counts) - _ALL_COUNT_KEYS or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in counts.values()
    ):
        raise ValueError("journal target counts are invalid")
    stages = list(raw["stages"])
    ordered = tuple(PipelineStage)
    if len(stages) != len(ordered):
        raise ValueError("journal target stage inventory is invalid")
    for stage, value in zip(ordered, stages):
        item = _mapping(value)
        _exact_keys(item, _STAGE_STATE_FIELDS)
        if (
            item.get("stage") != stage.value
            or item.get("label") != STAGE_LABELS[stage]
            or item.get("status") not in _STAGE_STATUSES
            or not isinstance(item.get("message"), str)
        ):
            raise ValueError("journal target stage state is invalid")
        for field in ("started_at", "completed_at"):
            if item.get(field) is not None:
                _utc_timestamp(item[field])
        receipt = item.get("receipt_sha256")
        if receipt is not None and (
            not isinstance(receipt, str) or not _SHA256.fullmatch(receipt)
        ):
            raise ValueError("journal target stage receipt is invalid")
        status = item["status"]
        if status == "pending" and any(
            item[field] not in {None, ""}
            for field in (
                "message",
                "started_at",
                "completed_at",
                "receipt_sha256",
            )
        ):
            raise ValueError("journal pending stage retains authority")
        if status == "completed" and (
            item["started_at"] is None
            or item["completed_at"] is None
            or item["receipt_sha256"] is None
        ):
            raise ValueError("journal completed stage lacks authority")
        if status in {"running", "failed"} and (
            item["started_at"] is None
            or item["completed_at"] is not None
            or item["receipt_sha256"] is not None
        ):
            raise ValueError("journal active stage state is invalid")


def _validate_config_shape(raw: Mapping[str, Any]) -> None:
    _exact_keys(raw, _CONFIG_FIELDS)
    for field in (
        "tenant_id",
        "asset_id",
        "rubric_provider",
        "rubric_model",
        "embedding_provider",
        "embedding_model",
    ):
        if not _nonempty_string(raw.get(field)):
            raise ValueError("journal target config string is invalid")
    for field in (
        "cluster_count",
        "batch_size",
        "min_trusted_examples",
        "min_trusted_groups",
        "synthetic_cases_per_cluster",
        "split_seed",
    ):
        value = raw.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("journal target config integer is invalid")
    for field in ("match_threshold", "max_unlabeled_to_trusted_ratio"):
        value = raw.get(field)
        if field == "max_unlabeled_to_trusted_ratio" and value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError("journal target config number is invalid")
    if not isinstance(raw.get("synthetic_coverage_enabled"), bool):
        raise ValueError("journal target config boolean is invalid")


def _validate_intermediate_authority(
    layout: Any,
    row: Mapping[str, Any],
    before: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    history_installed: bool,
    event_installed: bool,
) -> None:
    config_hash = _file_sha256(layout.config_path)
    state_hash = _file_sha256(layout.state_path)
    before_pair = (before["config_sha256"], before["state_sha256"])
    target_pair = (target["config_sha256"], target["state_sha256"])
    if row["kind"] == "configuration_revision":
        allowed = {
            before_pair,
            (target["config_sha256"], before["state_sha256"]),
            target_pair,
        }
        if history_installed and (config_hash, state_hash) != target_pair:
            raise ValueError("revision history precedes target controls")
        if event_installed and not history_installed:
            raise ValueError("revision event precedes its history")
    else:
        allowed = {before_pair, target_pair}
        if event_installed and (config_hash, state_hash) != target_pair:
            raise ValueError("journal event precedes target controls")
    if (config_hash, state_hash) not in allowed:
        raise ValueError("journal control files are outside reachable intermediates")


def _validate_audit_authority(
    layout: Any,
    row: Mapping[str, Any],
    *,
    uncommitted: bool,
) -> tuple[bool, bool]:
    audit = _mapping(row["audit"])
    _exact_keys(audit, {"config_history", "events"})
    history_row = (
        _mapping(row["history_entry"])
        if row["kind"] == "configuration_revision"
        else None
    )
    history_installed = _validate_audit_file(
        layout.config_history_path,
        _mapping(audit["config_history"]),
        appended_row=history_row,
        uncommitted=uncommitted,
    )
    event_installed = _validate_audit_file(
        layout.events_path,
        _mapping(audit["events"]),
        appended_row=_mapping(row["event_entry"]),
        uncommitted=uncommitted,
    )
    return history_installed, event_installed


def _validate_audit_file(
    path: Path,
    transition: Mapping[str, Any],
    *,
    appended_row: Mapping[str, Any] | None,
    uncommitted: bool,
) -> bool:
    _exact_keys(transition, {"before", "target"})
    before = _audit_descriptor_mapping(transition["before"])
    target = _audit_descriptor_mapping(transition["target"])
    current_present = path.is_file()
    current = path.read_bytes() if current_present else b""
    before_length = before["byte_length"]
    if len(current) < before_length:
        raise ValueError("journal audit prefix was truncated")
    before_bytes = current[:before_length]
    _strict_jsonl_bytes(before_bytes)
    if audit_descriptor(before_bytes, present=before["present"]) != before:
        raise ValueError("journal prior audit prefix is inconsistent")
    if not before["present"] and before_length != 0:
        raise ValueError("journal prior audit presence is inconsistent")
    target_bytes = (
        append_jsonl_bytes(before_bytes, appended_row)
        if appended_row is not None
        else before_bytes
    )
    expected_target = audit_descriptor(
        target_bytes,
        present=before["present"] or appended_row is not None,
    )
    if target != expected_target:
        raise ValueError("journal target audit prefix is inconsistent")
    _strict_jsonl_bytes(current)
    current_descriptor = audit_descriptor(current, present=current_present)
    if uncommitted:
        if current_descriptor == before:
            return False
        if current_descriptor == target:
            return appended_row is not None
        raise ValueError("journal audit file is outside reachable intermediates")
    if target["present"]:
        if not current_present or not current.startswith(target_bytes):
            raise ValueError("committed journal audit prefix is missing")
    elif current and before_length:
        raise ValueError("committed journal audit presence is inconsistent")
    return appended_row is not None


def _audit_descriptor_mapping(value: Any) -> dict[str, Any]:
    descriptor = _mapping(value)
    _exact_keys(descriptor, {"present", "byte_length", "row_count", "sha256"})
    if not isinstance(descriptor["present"], bool):
        raise ValueError("journal audit presence is invalid")
    for field in ("byte_length", "row_count"):
        item = descriptor[field]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ValueError("journal audit size is invalid")
    digest = descriptor["sha256"]
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ValueError("journal audit hash is invalid")
    return descriptor


def _validate_existing_revision_sequence(
    layout: Any,
    history: Mapping[str, Any],
    operation_id: str,
) -> None:
    rows = _audit_rows(layout.config_history_path)
    matching_indexes = [
        index
        for index, item in enumerate(rows)
        if item.get("operation_id") == operation_id
    ]
    if len(matching_indexes) > 1:
        raise ValueError("configuration revision history is duplicated")
    expected_revision = (
        matching_indexes[0] + 1 if matching_indexes else len(rows) + 1
    )
    if history.get("revision") != expected_revision:
        raise ValueError("configuration revision sequence is inconsistent")


def _stage_suffix(value: Any) -> tuple[PipelineStage, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("journal cleanup boundary is invalid")
    try:
        stages = tuple(PipelineStage(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError("journal cleanup boundary is invalid") from exc
    ordered = tuple(PipelineStage)
    if stages != ordered[ordered.index(stages[0]) :]:
        raise ValueError("journal cleanup stages are not an ordered suffix")
    return stages


def _audit_rows(path: Path) -> list[dict[str, Any]]:
    return read_strict_jsonl_objects(path)


def _strict_jsonl_bytes(raw: bytes) -> None:
    parse_strict_jsonl_objects(raw)


def _hash_mapping(value: Any) -> dict[str, Any]:
    row = _mapping(value)
    for field, item in row.items():
        if field == "receipt_sha256":
            receipt_hashes = _mapping(item)
            if any(
                not isinstance(digest, str) or not _SHA256.fullmatch(digest)
                for digest in receipt_hashes.values()
            ):
                raise ValueError("journal receipt hashes are invalid")
        elif not isinstance(item, str) or not _SHA256.fullmatch(item):
            raise ValueError("journal control hash is invalid")
    return row


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("journal object is invalid")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError("journal row fields are invalid")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _utc_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("journal timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("journal timestamp is invalid") from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() != timedelta(0)
        or parsed.isoformat() != value
    ):
        raise ValueError("journal timestamp is invalid")
    return parsed


def _persisted_sha256(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
