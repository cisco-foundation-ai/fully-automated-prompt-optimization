# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Fail-closed validation for evaluation-asset recovery journal authority."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.durability import verify_release_candidate
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
    STAGE_LABELS,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)

JOURNAL_SCHEMA_VERSION = "fapo-recovery-journal-v1"
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
        "before",
        "target",
        "target_config",
        "target_state",
        "history_entry",
        "event_entry",
        "invalidated_stages",
        "result",
    },
    "checkpoint_rebuild": {
        "schema_version",
        "operation_id",
        "kind",
        "phase",
        "prepared_at",
        "before",
        "target",
        "target_state",
        "event_entry",
        "invalidated_stages",
        "result",
    },
    "legacy_adoption": {
        "schema_version",
        "operation_id",
        "kind",
        "phase",
        "prepared_at",
        "before",
        "target",
        "target_receipts",
        "target_state",
        "event_entry",
        "result",
    },
}


def validate_recovery_journal(
    layout: Any,
    entries: Sequence[Mapping[str, Any]],
) -> None:
    """Validate the complete log and every uncommitted intermediate state."""
    prepared: dict[str, dict[str, Any]] = {}
    committed: dict[str, dict[str, Any]] = {}
    identities: set[tuple[str, str]] = set()
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
            or (operation_id, str(phase)) in identities
        ):
            raise ValueError("journal operation identity is invalid")
        identities.add((operation_id, str(phase)))
        if phase == "prepared":
            _exact_keys(row, _PREPARED_FIELDS[str(kind)])
            _utc_timestamp(row.get("prepared_at"))
            if operation_id in committed:
                raise ValueError("journal commit precedes its prepare")
            if operation_id in prepared:
                raise ValueError("journal prepare timestamp is invalid")
            prepared[operation_id] = row
        else:
            _exact_keys(row, _COMMITTED_FIELDS)
            committed_at = _utc_timestamp(row.get("committed_at"))
            if operation_id not in prepared:
                raise ValueError("journal commit has no preceding prepare")
            if committed_at < _utc_timestamp(prepared[operation_id]["prepared_at"]):
                raise ValueError("journal commit timestamp is invalid")
            committed[operation_id] = row
    if set(committed) - set(prepared) or any(
        committed[operation_id]["kind"] != prepared[operation_id]["kind"]
        for operation_id in committed
    ):
        raise ValueError("journal commit has no matching prepare")
    outstanding = set(prepared) - set(committed)
    if len(outstanding) > 1:
        raise ValueError("journal has competing uncommitted operations")
    for operation_id, row in prepared.items():
        _validate_prepared(layout, row, uncommitted=operation_id in outstanding)


def _validate_prepared(
    layout: Any,
    row: Mapping[str, Any],
    *,
    uncommitted: bool,
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
            _validate_rebuild(row, state, operation_id)
        else:
            _validate_adoption(layout, row, state, operation_id, target)

    _validate_event(layout, row, operation_id)
    if not uncommitted:
        _require_committed_audit_rows(layout, row)
        return
    event_installed = _validate_existing_audit_row(
        layout.events_path,
        row["event_entry"],
        operation_id,
    )
    history_installed = False
    if kind == "configuration_revision":
        history_installed = _validate_existing_audit_row(
            layout.config_history_path,
            row["history_entry"],
            operation_id,
        )
    _validate_intermediate_authority(
        layout,
        row,
        before,
        target,
        history_installed=history_installed,
        event_installed=event_installed,
    )
    if kind == "legacy_adoption":
        receipt_hashes = _mapping(target["receipt_sha256"])
        installed_receipts = 0
        for stage in PipelineStage:
            path = layout.receipt_path(stage)
            if path.is_file():
                installed_receipts += 1
                if _file_sha256(path) != receipt_hashes[stage.value]:
                    raise ValueError(
                        "installed adoption receipt is not a target intermediate"
                    )
        if _file_sha256(layout.state_path) == target["state_sha256"] and (
            installed_receipts != len(PipelineStage)
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
    verify_release_candidate(
        layout,
        state,
        receipts={
            stage: _mapping(receipts[stage.value]) for stage in PipelineStage
        },
    )


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


def _require_committed_audit_rows(layout: Any, row: Mapping[str, Any]) -> None:
    operation_id = str(row["operation_id"])
    if not _validate_existing_audit_row(
        layout.events_path,
        row["event_entry"],
        operation_id,
    ):
        raise ValueError("committed journal event is missing")
    if row["kind"] == "configuration_revision" and not _validate_existing_audit_row(
        layout.config_history_path,
        row["history_entry"],
        operation_id,
    ):
        raise ValueError("committed revision history is missing")


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


def _validate_existing_audit_row(
    path: Path,
    expected: Mapping[str, Any],
    operation_id: str,
) -> bool:
    if not path.is_file():
        return False
    matches = [
        value
        for value in _audit_rows(path)
        if value.get("operation_id") == operation_id
    ]
    if len(matches) > 1 or (matches and matches[0] != dict(expected)):
        raise ValueError("journal audit intermediate is inconsistent")
    return bool(matches)


def _audit_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, Mapping):
            raise ValueError("audit log row is invalid")
        rows.append(dict(value))
    return rows


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
