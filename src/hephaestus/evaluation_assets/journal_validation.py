# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Fail-closed validation for evaluation-asset recovery journal authority."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.models import (
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)

JOURNAL_SCHEMA_VERSION = "fapo-recovery-journal-v1"
_OPERATION_ID = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
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
            if not _nonempty_string(row.get("prepared_at")):
                raise ValueError("journal prepare timestamp is invalid")
            prepared[operation_id] = row
        else:
            _exact_keys(row, _COMMITTED_FIELDS)
            if not _nonempty_string(row.get("committed_at")):
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
        config = EvaluationAssetConfig.from_dict(config_raw)
        if (
            config.to_dict() != config_raw
            or config.tenant_id != layout.tenant_id
            or config.asset_id != layout.asset_id
            or _persisted_sha256(config_raw) != target["config_sha256"]
        ):
            raise ValueError("journal target config is inconsistent")
        _validate_revision(row, state, operation_id)
    else:
        if target["config_sha256"] != before["config_sha256"]:
            raise ValueError("journal unexpectedly changes configuration")
        if kind == "checkpoint_rebuild":
            _validate_rebuild(row, state, operation_id)
        else:
            _validate_adoption(layout, row, state, operation_id, target)

    _validate_event(layout, row["event_entry"], operation_id)
    if not uncommitted:
        return
    if _file_sha256(layout.config_path) not in {
        before["config_sha256"],
        target["config_sha256"],
    } or _file_sha256(layout.state_path) not in {
        before["state_sha256"],
        target["state_sha256"],
    }:
        raise ValueError("journal control files are outside recorded intermediates")
    _validate_existing_audit_row(layout.events_path, row["event_entry"], operation_id)
    if kind == "configuration_revision":
        _validate_existing_audit_row(
            layout.config_history_path,
            row["history_entry"],
            operation_id,
        )
    elif kind == "legacy_adoption":
        receipt_hashes = _mapping(target["receipt_sha256"])
        for stage in PipelineStage:
            path = layout.receipt_path(stage)
            if path.is_file() and _file_sha256(path) != receipt_hashes[stage.value]:
                raise ValueError("installed adoption receipt is not a target intermediate")


def _validate_revision(
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
) -> None:
    invalidated = _stage_suffix(row["invalidated_stages"])
    result = _mapping(row["result"])
    history = _mapping(row["history_entry"])
    if (
        history.get("operation_id") != operation_id
        or history.get("event") != "configuration_updated"
        or not isinstance(history.get("revision"), int)
        or isinstance(history.get("revision"), bool)
        or history.get("revision", 0) < 2
        or result.get("revision") != history.get("revision")
        or result.get("changed_fields") != history.get("changed_fields")
        or not isinstance(result.get("changed_fields"), Mapping)
        or not result["changed_fields"]
        or result.get("invalidated_from_stage") != invalidated[0].value
        or history.get("invalidated_from_stage") != invalidated[0].value
        or result.get("resume_from_stage") != history.get("resume_from_stage")
        or state.current_stage != result.get("resume_from_stage")
    ):
        raise ValueError("configuration revision journal payload is inconsistent")
    _validate_invalidated_state(state, invalidated)


def _validate_rebuild(
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
) -> None:
    del operation_id
    invalidated = _stage_suffix(row["invalidated_stages"])
    result = _mapping(row["result"])
    if set(result) != {"resume_from_stage"} or (
        result["resume_from_stage"] != invalidated[0].value
        or state.current_stage != invalidated[0].value
    ):
        raise ValueError("checkpoint rebuild journal payload is inconsistent")
    _validate_invalidated_state(state, invalidated)


def _validate_adoption(
    layout: Any,
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
    target: Mapping[str, Any],
) -> None:
    del operation_id
    receipts = _mapping(row["target_receipts"])
    receipt_hashes = _mapping(target["receipt_sha256"])
    expected = {stage.value for stage in PipelineStage}
    if set(receipts) != expected or set(receipt_hashes) != expected:
        raise ValueError("adoption receipt inventory is incomplete")
    for stage in PipelineStage:
        receipt = _mapping(receipts[stage.value])
        if (
            receipt.get("stage") != stage.value
            or _persisted_sha256(receipt) != receipt_hashes[stage.value]
        ):
            raise ValueError("adoption receipt target is inconsistent")
        stage_state = next(item for item in state.stages if item.stage == stage.value)
        if stage_state.receipt_sha256 != receipt_hashes[stage.value]:
            raise ValueError("adoption state receipt authority is inconsistent")
    if (
        state.status != "released"
        or state.current_stage is not None
        or state.error is not None
        or row["result"] != {"status": "released"}
        or layout.tenant_id != state.tenant_id
    ):
        raise ValueError("adoption target lifecycle is inconsistent")


def _validate_event(layout: Any, value: Any, operation_id: str) -> None:
    row = _mapping(value)
    if (
        row.get("operation_id") != operation_id
        or row.get("tenant_id") != layout.tenant_id
        or row.get("asset_id") != layout.asset_id
        or not _nonempty_string(row.get("event"))
        or not _nonempty_string(row.get("timestamp"))
        or not isinstance(row.get("details"), Mapping)
    ):
        raise ValueError("journal event identity is inconsistent")


def _validate_invalidated_state(
    state: PipelineState,
    invalidated: tuple[PipelineStage, ...],
) -> None:
    invalidated_names = {stage.value for stage in invalidated}
    for item in state.stages:
        if item.stage in invalidated_names and (
            item.status != "pending" or item.receipt_sha256 is not None
        ):
            raise ValueError("journal target state retains invalidated authority")
    if state.status != "queued" or state.error is not None:
        raise ValueError("journal target lifecycle is inconsistent")


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
) -> None:
    if not path.is_file():
        return
    matches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, Mapping):
            raise ValueError("audit log row is invalid")
        if value.get("operation_id") == operation_id:
            matches.append(dict(value))
    if len(matches) > 1 or (matches and matches[0] != dict(expected)):
        raise ValueError("journal audit intermediate is inconsistent")


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


def _persisted_sha256(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
