# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Fail-closed validation for evaluation-asset recovery journal authority."""

from __future__ import annotations

import hashlib
import json
import math
import re
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.control_jsonl import (
    parse_strict_json_object,
    parse_strict_jsonl_objects,
    read_strict_jsonl_objects,
    resolve_local_authority_file,
)
from src.hephaestus.evaluation_assets.journal_transitions import (
    JOURNAL_SCHEMA_VERSION,
    PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2,
    PERSISTED_STAGE_VALUES_V2,
    append_jsonl_bytes,
    audit_descriptor,
    derive_adoption_plan,
    derive_rebuild_plan,
    derive_release_publication_plan,
    derive_revision_plan,
    normalized_legacy_completed_state_v1,
)
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
    STAGE_LABELS,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
    StageState,
)

_OPERATION_ID = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_JOURNAL_AUTHORITY_SNAPSHOT: ContextVar[Mapping[Path, bytes] | None] = ContextVar(
    "evaluation_asset_journal_authority_snapshot",
    default=None,
)
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
_STATE_V2_STAGE_ORDER = PERSISTED_STAGE_VALUES_V2


def _local_authority_file(layout: Any, path: Path) -> tuple[bool, bytes]:
    """Return presence and no-follow bytes for one journal authority node."""
    snapshot = _JOURNAL_AUTHORITY_SNAPSHOT.get()
    if snapshot is not None:
        lexical_path = Path(path).absolute()
        if lexical_path not in snapshot:
            return False, b""
        return True, snapshot[lexical_path]
    prospective = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="write",
    )
    if not prospective.exists:
        return False, b""
    authority = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="read",
    )
    if authority.data is None:
        raise ValueError("local authority read did not return bytes")
    return True, authority.data
_STATE_V2_STAGE_LABELS = {
    "raw_inputs": "Validate raw inputs",
    "prepared_inputs": "Prepare canonical inputs",
    "rubric_extraction": "Create evaluation guidelines",
    "intent_clustering": "Mine intent clusters",
    "coverage_decisions": "Apply coverage decisions",
    "label_inference": "Infer reviewable labels",
    "synthetic_coverage": "Optional synthetic coverage",
    "dataset_splits": "Build dataset splits",
}
_STATE_V2_STAGE_COUNT_KEYS = {
    "raw_inputs": frozenset(
        {"feedback_records", "unlabeled_records"}
    ),
    "prepared_inputs": frozenset(
        {"prepared_feedback", "prepared_intents"}
    ),
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
    "label_inference": frozenset(
        {"inferred_cases", "review_clusters"}
    ),
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
_ALL_COUNT_KEYS = frozenset().union(*_STATE_V2_STAGE_COUNT_KEYS.values())
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
        "before_manifests",
        "target_manifests",
        "target_state",
        "event_entry",
        "result",
        "audit",
    },
    "release_publication": {
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
    *,
    artifact_overrides: Mapping[Path, bytes] | None = None,
) -> ValidatedRecoveryJournal:
    """Validate a journal against one optional closed authority snapshot."""
    token = _JOURNAL_AUTHORITY_SNAPSHOT.set(artifact_overrides)
    try:
        return _validate_recovery_journal(layout, entries)
    finally:
        _JOURNAL_AUTHORITY_SNAPSHOT.reset(token)


def _validate_recovery_journal(
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
    historical_profile = _frozen_journal_endpoint(layout) or bool(
        prepared_rows
        and prepared_rows[-1].get("kind")
        in {"legacy_adoption", "release_publication"}
    )
    for index, row in enumerate(prepared_rows):
        operation_id = str(row["operation_id"])
        _validate_prepared(
            layout,
            row,
            uncommitted=operation_id in outstanding,
            final_operation=index == len(prepared_rows) - 1,
            historical_profile=historical_profile,
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


def _frozen_journal_endpoint(layout: Any) -> bool:
    """Return whether persisted state is a complete v2 handoff or release."""
    present, state_bytes = _local_authority_file(layout, layout.state_path)
    if not present:
        return False
    raw = parse_strict_json_object(state_bytes)
    stages = raw.get("stages")
    return bool(
        raw.get("schema_version") == STATE_SCHEMA_VERSION
        and raw.get("status") in {"running", "released"}
        and (
            raw.get("status") == "released"
            or (
                raw.get("status") == "running"
                and raw.get("error") is None
            )
        )
        and raw.get("current_stage") in {None, PERSISTED_STAGE_VALUES_V2[-1]}
        and isinstance(stages, list)
        and [
            item.get("stage") if isinstance(item, Mapping) else None
            for item in stages
        ]
        == list(PERSISTED_STAGE_VALUES_V2)
        and all(
            isinstance(item, Mapping)
            and item.get("status") == "completed"
            and isinstance(item.get("receipt_sha256"), str)
            and _SHA256.fullmatch(item["receipt_sha256"])
            for item in stages
        )
    )


def _validate_prepared(
    layout: Any,
    row: Mapping[str, Any],
    *,
    uncommitted: bool,
    final_operation: bool,
    historical_profile: bool,
) -> None:
    operation_id = str(row["operation_id"])
    kind = str(row["kind"])
    before_raw = _mapping(row["before"])
    before_release = None
    if kind in {"release_publication", "legacy_adoption"}:
        _exact_keys(before_raw, {"config_sha256", "state_sha256", "release"})
        before_release = _release_descriptor(before_raw["release"])
        before = _hash_mapping(
            {key: before_raw[key] for key in ("config_sha256", "state_sha256")}
        )
    else:
        before = _hash_mapping(before_raw)
    target = _hash_mapping(row["target"])
    expected_hash_fields = {
        "config_sha256",
        "state_sha256",
        "release_sha256",
        "stage_8_receipt_sha256",
        "generation_manifest_sha256",
        "build_provenance_sha256",
    } if kind == "release_publication" else {
        "config_sha256",
        "state_sha256",
        "receipt_sha256",
        "release_sha256",
        "stage_8_receipt_sha256",
        "generation_manifest_sha256",
        "build_provenance_sha256",
    } if kind == "legacy_adoption" else {"config_sha256", "state_sha256"}
    if set(before) != {"config_sha256", "state_sha256"} or set(target) != expected_hash_fields:
        raise ValueError("journal control hashes are incomplete")

    before_config = _mapping(row["before_config"])
    _validate_config_shape(before_config)
    canonical_before_config = EvaluationAssetConfig.from_dict(before_config).to_dict()
    before_state = _mapping(row["before_state"])
    historical_state = historical_profile or kind in {
        "legacy_adoption",
        "release_publication",
    }
    _validate_before_state_shape(
        before_state,
        historical=historical_state,
    )
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
    _validate_state_shape(state_raw, historical=historical_state)
    state = _state_v2_from_validated_raw(state_raw)
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
            historical_profile=historical_profile,
        )
        _require_exact_plan(row, plan)
        _validate_revision(
            layout,
            row,
            state,
            config_raw,
            before,
            operation_id,
            historical_profile=historical_profile,
        )
    else:
        if target["config_sha256"] != before["config_sha256"]:
            raise ValueError("journal unexpectedly changes configuration")
        if kind == "checkpoint_rebuild":
            request = _mapping(row["request"])
            _exact_keys(request, {"boundary"})
            try:
                boundary = str(request["boundary"])
                if historical_profile:
                    if boundary not in PERSISTED_STAGE_VALUES_V2:
                        raise ValueError
                else:
                    boundary = PipelineStage(boundary)
            except (TypeError, ValueError) as exc:
                raise ValueError("checkpoint boundary request is invalid") from exc
            plan = derive_rebuild_plan(
                before_config,
                before_state,
                boundary,
                operation_id=operation_id,
                prepared_at=str(row["prepared_at"]),
                historical_profile=historical_profile,
            )
            _require_exact_plan(row, plan)
            _validate_rebuild(
                row,
                state,
                operation_id,
                historical_profile=historical_profile,
            )
        elif kind == "legacy_adoption":
            request = _mapping(row["request"])
            _exact_keys(request, {"release_pointer"})
            pointer = _mapping(request["release_pointer"])
            receipts = _mapping(row["target_receipts"])
            plan = derive_adoption_plan(
                before_config,
                before_state,
                receipts,
                pointer,
                operation_id=operation_id,
                prepared_at=str(row["prepared_at"]),
            )
            _require_exact_plan(row, plan, excluded={"receipt_sha256"})
            if target.get("receipt_sha256") != plan["receipt_sha256"]:
                raise ValueError("adoption target receipt hashes are inconsistent")
            _validate_adoption(
                layout,
                row,
                state,
                operation_id,
                target,
                pointer,
            )
        else:
            request = _mapping(row["request"])
            _exact_keys(request, {"release_pointer"})
            pointer = _mapping(request["release_pointer"])
            plan = derive_release_publication_plan(
                before_config,
                before_state,
                pointer,
                operation_id=operation_id,
                prepared_at=str(row["prepared_at"]),
            )
            _require_exact_plan(row, plan)
            _validate_release_publication(
                layout,
                row,
                state,
                operation_id,
                target,
                pointer,
            )

    _validate_event(layout, row, operation_id)
    history_installed, event_installed = _validate_audit_authority(
        layout,
        row,
        uncommitted=uncommitted,
    )
    installed_receipts: list[bool] = []
    if kind == "legacy_adoption":
        manifests_installed = _validate_adoption_manifest_prefix(
            layout,
            row,
            committed=not uncommitted,
        )
        receipt_hashes = _mapping(target["receipt_sha256"])
        for stage in _STATE_V2_STAGE_ORDER:
            path = layout.receipt_path(stage)
            present, receipt_bytes = _local_authority_file(layout, path)
            installed_receipts.append(present)
            if present and (
                hashlib.sha256(receipt_bytes).hexdigest()
                != receipt_hashes[stage]
            ):
                raise ValueError(
                    "installed adoption receipt is not a target intermediate"
                )
        prefix_length = sum(installed_receipts)
        if installed_receipts != [
            index < prefix_length for index in range(len(_STATE_V2_STAGE_ORDER))
        ]:
            raise ValueError("installed adoption receipts are not an ordered prefix")
        if any(installed_receipts) and not manifests_installed:
            raise ValueError("adoption receipts precede manifest authority")
    if not uncommitted:
        if kind == "legacy_adoption" and not all(installed_receipts):
            raise ValueError("committed adoption receipt authority is incomplete")
        if kind == "legacy_adoption":
            if not final_operation:
                raise ValueError("committed adoption is not terminal")
            _validate_committed_adoption_terminal(layout, row, target)
        elif kind == "release_publication":
            if not final_operation:
                raise ValueError("committed release publication is not terminal")
            _validate_committed_release_terminal(layout, row, target)
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
        before_release=before_release,
    )
    if kind == "legacy_adoption":
        if _file_sha256(
            layout,
            layout.state_path,
        ) == target["state_sha256"] and not all(
            installed_receipts
        ):
            raise ValueError("adoption state precedes its receipt authority")
        current_release = _current_release_descriptor(
            layout,
            layout.release_pointer_path,
        )
        pointer = _mapping(_mapping(row["request"])["release_pointer"])
        target_release = {
            "present": True,
            "bytes": len(_persisted_json_bytes(pointer)),
            "sha256": target["release_sha256"],
        }
        if current_release != before_release and current_release != target_release:
            raise ValueError("adoption pointer is outside reachable intermediates")
        if current_release == target_release and not all(installed_receipts):
            raise ValueError("adoption pointer precedes its receipt authority")
        if (
            _file_sha256(layout, layout.state_path) == target["state_sha256"]
            and current_release != target_release
        ):
            raise ValueError("adoption state precedes its pointer authority")


def _validate_revision(
    layout: Any,
    row: Mapping[str, Any],
    state: PipelineState,
    target_config: Mapping[str, Any],
    before: Mapping[str, Any],
    operation_id: str,
    *,
    historical_profile: bool,
) -> None:
    invalidated = _stage_suffix(
        row["invalidated_stages"],
        historical=historical_profile,
    )
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
    dependencies = (
        PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2
        if historical_profile
        else {
            name: stage.value
            for name, stage in CONFIG_STAGE_DEPENDENCIES.items()
        }
    )
    before_config = dict(target_config)
    for field, raw_change in changed_fields.items():
        if field not in dependencies:
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
    ordered = (
        PERSISTED_STAGE_VALUES_V2
        if historical_profile
        else tuple(stage.value for stage in PipelineStage)
    )
    earliest = min(
        (dependencies[field] for field in changed_fields),
        key=ordered.index,
    )
    resume = _validate_mutable_target_state(
        state,
        invalidated,
        historical=historical_profile,
    )
    if (
        history.get("operation_id") != operation_id
        or history.get("event") != "configuration_updated"
        or not isinstance(history.get("revision"), int)
        or isinstance(history.get("revision"), bool)
        or history.get("revision", 0) < 2
        or result.get("revision") != history.get("revision")
        or history.get("timestamp") != row.get("prepared_at")
        or result.get("invalidated_from_stage") != earliest
        or history.get("invalidated_from_stage") != earliest
        or invalidated[0] != earliest
        or result.get("resume_from_stage") != resume
        or history.get("resume_from_stage") != resume
        or state.current_stage != resume
        or state.updated_at != row.get("prepared_at")
    ):
        raise ValueError("configuration revision journal payload is inconsistent")
    _validate_existing_revision_sequence(layout, history, operation_id)


def _validate_rebuild(
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
    *,
    historical_profile: bool,
) -> None:
    del operation_id
    invalidated = _stage_suffix(
        row["invalidated_stages"],
        historical=historical_profile,
    )
    result = _mapping(row["result"])
    _exact_keys(result, {"resume_from_stage"})
    resume = _validate_mutable_target_state(
        state,
        invalidated,
        historical=historical_profile,
    )
    if (
        result["resume_from_stage"] != invalidated[0]
        or resume != invalidated[0]
        or state.current_stage != invalidated[0]
        or state.updated_at != row.get("prepared_at")
    ):
        raise ValueError("checkpoint rebuild journal payload is inconsistent")


def _validate_adoption(
    layout: Any,
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
    target: Mapping[str, Any],
    pointer: Mapping[str, Any],
) -> None:
    before_manifests = _mapping(row["before_manifests"])
    _exact_keys(
        before_manifests,
        {"asset_manifest", "dataset_manifest", "generation_manifest"},
    )
    for descriptor in before_manifests.values():
        _release_descriptor(descriptor)
    manifests = _mapping(row["target_manifests"])
    _exact_keys(
        manifests,
        {"asset_manifest", "dataset_manifest", "generation_manifest"},
    )
    asset_manifest = _mapping(manifests["asset_manifest"])
    dataset_manifest = _mapping(manifests["dataset_manifest"])
    generation_manifest = _mapping(manifests["generation_manifest"])
    published = _mapping(asset_manifest.get("published_datasets"))
    if (
        asset_manifest != dataset_manifest
        or published.get("generation_id") != pointer.get("generation_id")
        or published.get("generation_manifest_sha256")
        != target.get("generation_manifest_sha256")
        or published.get("build_provenance_sha256")
        != target.get("build_provenance_sha256")
        or _persisted_sha256(generation_manifest)
        != target.get("generation_manifest_sha256")
    ):
        raise ValueError("adoption manifest targets are inconsistent")
    receipts = _mapping(row["target_receipts"])
    receipt_hashes = _mapping(target["receipt_sha256"])
    expected = set(_STATE_V2_STAGE_ORDER)
    if set(receipts) != expected or set(receipt_hashes) != expected:
        raise ValueError("adoption receipt inventory is incomplete")
    for stage in _STATE_V2_STAGE_ORDER:
        receipt = _mapping(receipts[stage])
        counts = _mapping(receipt.get("counts"))
        if (
            receipt.get("stage") != stage
            or receipt.get("origin") != "legacy_adoption"
            or set(counts) != _STATE_V2_STAGE_COUNT_KEYS[stage]
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in counts.values()
            )
            or _persisted_sha256(receipt) != receipt_hashes[stage]
        ):
            raise ValueError("adoption receipt target is inconsistent")
        stage_state = next(item for item in state.stages if item.stage == stage)
        if (
            stage_state.status != "completed"
            or stage_state.receipt_sha256 != receipt_hashes[stage]
            or any(state.counts.get(key) != value for key, value in counts.items())
        ):
            raise ValueError("adoption state receipt authority is inconsistent")
    if (
        state.schema_version != STATE_SCHEMA_VERSION
        or state.status != "released"
        or state.current_stage is not None
        or state.error is not None
        or row["result"]
        != {
            "status": "released",
            "generation_id": pointer.get("generation_id"),
            "release_sha256": target["release_sha256"],
            "stage_8_receipt_sha256": target["stage_8_receipt_sha256"],
        }
        or pointer.get("stage_8_receipt_sha256")
        != target["stage_8_receipt_sha256"]
        or pointer.get("generation_manifest_sha256")
        != target["generation_manifest_sha256"]
        or pointer.get("build_provenance_sha256")
        != target["build_provenance_sha256"]
        or _persisted_sha256(pointer) != target["release_sha256"]
        or layout.tenant_id != state.tenant_id
        or state.updated_at != row.get("prepared_at")
        or state.last_operation_id != operation_id
        or set(state.counts) != _ALL_COUNT_KEYS
    ):
        raise ValueError("adoption target lifecycle is inconsistent")


def _validate_release_publication(
    layout: Any,
    row: Mapping[str, Any],
    state: PipelineState,
    operation_id: str,
    target: Mapping[str, Any],
    pointer: Mapping[str, Any],
) -> None:
    result = _mapping(row["result"])
    _exact_keys(
        result,
        {
            "status",
            "generation_id",
            "release_sha256",
            "stage_8_receipt_sha256",
        },
    )
    stage_eight = next(
        item for item in state.stages if item.stage == "dataset_splits"
    )
    if (
        state.schema_version != STATE_SCHEMA_VERSION
        or state.status != "released"
        or state.current_stage is not None
        or state.error is not None
        or state.updated_at != row.get("prepared_at")
        or state.last_operation_id != operation_id
        or any(
            item.status != "completed" or item.receipt_sha256 is None
            for item in state.stages
        )
        or set(state.counts) != _ALL_COUNT_KEYS
        or result.get("status") != "released"
        or result.get("generation_id") != pointer.get("generation_id")
        or result.get("release_sha256") != target["release_sha256"]
        or result.get("stage_8_receipt_sha256")
        != target["stage_8_receipt_sha256"]
        or pointer.get("stage_8_receipt_sha256")
        != target["stage_8_receipt_sha256"]
        or pointer.get("generation_manifest_sha256")
        != target["generation_manifest_sha256"]
        or pointer.get("build_provenance_sha256")
        != target["build_provenance_sha256"]
        or stage_eight.receipt_sha256 != target["stage_8_receipt_sha256"]
        or _persisted_sha256(pointer) != target["release_sha256"]
    ):
        raise ValueError("release publication target is inconsistent")


def _validate_committed_release_terminal(
    layout: Any,
    row: Mapping[str, Any],
    target: Mapping[str, Any],
) -> None:
    if (
        _file_sha256(layout, layout.config_path) != target["config_sha256"]
        or _file_sha256(layout, layout.state_path) != target["state_sha256"]
        or _current_release_descriptor(layout, layout.release_pointer_path)
        != {
            "present": True,
            "bytes": len(_local_authority_file(layout, layout.release_pointer_path)[1]),
            "sha256": target["release_sha256"],
        }
    ):
        raise ValueError("committed release controls are not at the target")
    audit = _mapping(row["audit"])
    for name, path in (
        ("config_history", layout.config_history_path),
        ("events", layout.events_path),
    ):
        target_descriptor = _audit_descriptor_mapping(
            _mapping(audit[name])["target"]
        )
        present, current = _local_authority_file(layout, path)
        if audit_descriptor(current, present=present) != target_descriptor:
            raise ValueError("committed release audit is not at the target")


def _validate_operation_chronology(
    layout: Any,
    previous: Mapping[str, Any],
    previous_commit: Mapping[str, Any],
    current: Mapping[str, Any],
) -> None:
    if previous["kind"] in {"legacy_adoption", "release_publication"}:
        raise ValueError("journal operation follows a terminal release")
    previous_state = _mapping(previous["target_state"])
    current_before_state = _mapping(current["before_state"])
    previous_target = _hash_mapping(previous["target"])
    current_before_raw = _mapping(current["before"])
    current_before = _hash_mapping(
        {
            key: value
            for key, value in current_before_raw.items()
            if key != "release"
        }
    )
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
    _, current_bytes = _local_authority_file(layout, layout.events_path)
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
        _file_sha256(layout, layout.config_path) != target["config_sha256"]
        or _file_sha256(layout, layout.state_path) != target["state_sha256"]
        or _current_release_descriptor(
            layout,
            layout.release_pointer_path,
        ).get("sha256")
        != target["release_sha256"]
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
        present, current = _local_authority_file(layout, path)
        if audit_descriptor(current, present=present) != target_descriptor:
            raise ValueError("committed adoption audit is not at the target")


def _validate_committed_mutation_terminal(
    layout: Any,
    row: Mapping[str, Any],
    target: Mapping[str, Any],
) -> None:
    if _file_sha256(layout, layout.config_path) != target["config_sha256"]:
        raise ValueError("committed mutation config is not at the target")
    audit = _mapping(row["audit"])
    target_descriptor = _audit_descriptor_mapping(
        _mapping(audit["config_history"])["target"]
    )
    present, current = _local_authority_file(
        layout,
        layout.config_history_path,
    )
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
    elif kind == "legacy_adoption":
        expected_event = "legacy_asset_adopted"
        expected_details = {"previous_status": "completed"}
    else:
        expected_event = "pipeline_released"
        expected_details = {
            key: value
            for key, value in _mapping(prepared["result"]).items()
            if key != "status"
        }
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
    invalidated: tuple[str, ...],
    *,
    historical: bool,
) -> str:
    invalidated_names = set(invalidated)
    invalidated_count_keys = {
        key
        for stage in invalidated
        for key in (
            _STATE_V2_STAGE_COUNT_KEYS[stage]
            if historical
            else STAGE_COUNT_KEYS[PipelineStage(stage)]
        )
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
            item.stage
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
        or state.current_stage != first_incomplete
        or any(key in state.counts for key in invalidated_count_keys)
    ):
        raise ValueError("journal target lifecycle is inconsistent")
    ordered = (
        PERSISTED_STAGE_VALUES_V2
        if historical
        else tuple(stage.value for stage in PipelineStage)
    )
    first_index = ordered.index(first_incomplete)
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


def _validate_before_state_shape(
    raw: Mapping[str, Any],
    *,
    historical: bool,
) -> None:
    if raw.get("status") == "completed":
        raw = normalized_legacy_completed_state_v1(raw)
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
        if historical:
            if current_stage not in PERSISTED_STAGE_VALUES_V2:
                raise ValueError("journal before current stage is invalid")
        else:
            try:
                PipelineStage(current_stage)
            except (TypeError, ValueError) as exc:
                raise ValueError("journal before current stage is invalid") from exc
    ordered = _STATE_V2_STAGE_ORDER if historical else tuple(PipelineStage)
    count_keys = (
        _ALL_COUNT_KEYS
        if historical
        else frozenset().union(
            *(frozenset(STAGE_COUNT_KEYS[stage]) for stage in ordered)
        )
    )
    labels = _STATE_V2_STAGE_LABELS if historical else STAGE_LABELS
    counts = _mapping(raw["counts"])
    if set(counts) - count_keys or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in counts.values()
    ):
        raise ValueError("journal before counts are invalid")
    stages = list(raw["stages"])
    if len(stages) != len(ordered):
        raise ValueError("journal before stage inventory is invalid")
    for stage, value in zip(ordered, stages):
        stage_value = stage if historical else stage.value
        item = _mapping(value)
        _exact_keys(item, _STAGE_STATE_FIELDS)
        if (
            item.get("stage") != stage_value
            or item.get("label") != labels[stage]
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


def _validate_state_shape(
    raw: Mapping[str, Any],
    *,
    historical: bool,
) -> None:
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
        if historical:
            if current_stage not in PERSISTED_STAGE_VALUES_V2:
                raise ValueError("journal target current stage is invalid")
        else:
            try:
                PipelineStage(current_stage)
            except (TypeError, ValueError) as exc:
                raise ValueError("journal target current stage is invalid") from exc
    ordered = _STATE_V2_STAGE_ORDER if historical else tuple(PipelineStage)
    count_keys = (
        _ALL_COUNT_KEYS
        if historical
        else frozenset().union(
            *(frozenset(STAGE_COUNT_KEYS[stage]) for stage in ordered)
        )
    )
    labels = _STATE_V2_STAGE_LABELS if historical else STAGE_LABELS
    counts = _mapping(raw["counts"])
    if set(counts) - count_keys or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in counts.values()
    ):
        raise ValueError("journal target counts are invalid")
    stages = list(raw["stages"])
    if len(stages) != len(ordered):
        raise ValueError("journal target stage inventory is invalid")
    for stage, value in zip(ordered, stages):
        stage_value = stage if historical else stage.value
        item = _mapping(value)
        _exact_keys(item, _STAGE_STATE_FIELDS)
        if (
            item.get("stage") != stage_value
            or item.get("label") != labels[stage]
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


def _state_v2_from_validated_raw(raw: Mapping[str, Any]) -> PipelineState:
    """Materialize an already validated v2 state without current registries."""
    return PipelineState(
        tenant_id=str(raw["tenant_id"]),
        asset_id=str(raw["asset_id"]),
        schema_version=str(raw["schema_version"]),
        status=str(raw["status"]),
        current_stage=raw["current_stage"],
        created_at=str(raw["created_at"]),
        updated_at=str(raw["updated_at"]),
        error=raw["error"],
        counts=dict(_mapping(raw["counts"])),
        stages=[StageState(**dict(_mapping(item))) for item in raw["stages"]],
        mutation_sequence=int(raw["mutation_sequence"]),
        last_operation_id=str(raw["last_operation_id"]),
    )


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
    before_release: Mapping[str, Any] | None,
) -> None:
    config_hash = _file_sha256(layout, layout.config_path)
    state_hash = _file_sha256(layout, layout.state_path)
    before_pair = (before["config_sha256"], before["state_sha256"])
    target_pair = (target["config_sha256"], target["state_sha256"])
    if row["kind"] == "release_publication":
        if before_release is None:
            raise ValueError("release publication lacks prior pointer evidence")
        pointer = _mapping(_mapping(row["request"])["release_pointer"])
        current_release = _current_release_descriptor(
            layout,
            layout.release_pointer_path,
        )
        target_release = {
            "present": True,
            "bytes": len(_persisted_json_bytes(pointer)),
            "sha256": target["release_sha256"],
        }
        current_pair = (config_hash, state_hash)
        allowed = {
            (
                _release_descriptor_key(before_release),
                (before["config_sha256"], before["state_sha256"]),
                False,
            ),
            (
                _release_descriptor_key(target_release),
                (target["config_sha256"], before["state_sha256"]),
                False,
            ),
            (
                _release_descriptor_key(target_release),
                (target["config_sha256"], target["state_sha256"]),
                False,
            ),
            (
                _release_descriptor_key(target_release),
                (target["config_sha256"], target["state_sha256"]),
                True,
            ),
        }
        if (
            _release_descriptor_key(current_release),
            current_pair,
            event_installed,
        ) not in allowed:
            raise ValueError("release publication authority order is unreachable")
        if history_installed:
            raise ValueError("release publication cannot append configuration history")
        return
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
        layout,
        layout.config_history_path,
        _mapping(audit["config_history"]),
        appended_row=history_row,
        uncommitted=uncommitted,
    )
    event_installed = _validate_audit_file(
        layout,
        layout.events_path,
        _mapping(audit["events"]),
        appended_row=_mapping(row["event_entry"]),
        uncommitted=uncommitted,
    )
    return history_installed, event_installed


def _validate_audit_file(
    layout: Any,
    path: Path,
    transition: Mapping[str, Any],
    *,
    appended_row: Mapping[str, Any] | None,
    uncommitted: bool,
) -> bool:
    _exact_keys(transition, {"before", "target"})
    before = _audit_descriptor_mapping(transition["before"])
    target = _audit_descriptor_mapping(transition["target"])
    current_present, current = _local_authority_file(layout, path)
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
    rows = _audit_rows(layout, layout.config_history_path)
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


def _stage_suffix(value: Any, *, historical: bool) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("journal cleanup boundary is invalid")
    try:
        stages = tuple(str(item) for item in value)
        ordered = PERSISTED_STAGE_VALUES_V2 if historical else tuple(
            stage.value for stage in PipelineStage
        )
        if any(stage not in ordered for stage in stages):
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ValueError("journal cleanup boundary is invalid") from exc
    if stages != ordered[ordered.index(stages[0]) :]:
        raise ValueError("journal cleanup stages are not an ordered suffix")
    return stages


def _audit_rows(layout: Any, path: Path) -> list[dict[str, Any]]:
    return read_strict_jsonl_objects(
        path,
        trusted_root=layout.tenants_root,
    )


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


def _release_descriptor(value: Any) -> dict[str, Any]:
    descriptor = _mapping(value)
    _exact_keys(descriptor, {"present", "bytes", "sha256"})
    if not isinstance(descriptor["present"], bool):
        raise ValueError("journal release presence is invalid")
    size = descriptor["bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("journal release size is invalid")
    digest = descriptor["sha256"]
    if descriptor["present"]:
        if size < 1 or not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ValueError("journal release hash is invalid")
    elif size != 0 or digest is not None:
        raise ValueError("journal absent release descriptor is invalid")
    return descriptor


def _current_release_descriptor(
    layout: Any,
    path: Path,
) -> dict[str, Any]:
    present, data = _local_authority_file(layout, path)
    if not present:
        return {"present": False, "bytes": 0, "sha256": None}
    return {
        "present": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _validate_adoption_manifest_prefix(
    layout: Any,
    row: Mapping[str, Any],
    *,
    committed: bool,
) -> bool:
    before = _mapping(row["before_manifests"])
    targets = _mapping(row["target_manifests"])
    names_and_paths = (
        ("asset_manifest", layout.manifest_path),
        (
            "dataset_manifest",
            layout.artifact_path(
                _STATE_V2_STAGE_ORDER[-1],
                "dataset_manifest.json",
            ),
        ),
        (
            "generation_manifest",
            layout.artifact_path(
                _STATE_V2_STAGE_ORDER[-1],
                "generation_manifest.json",
            ),
        ),
    )
    current = tuple(
        _release_descriptor_key(_current_release_descriptor(layout, path))
        for _, path in names_and_paths
    )
    before_keys = tuple(
        _release_descriptor_key(_release_descriptor(before[name]))
        for name, _ in names_and_paths
    )
    target_keys = tuple(
        _release_descriptor_key(
            {
                "present": True,
                "bytes": len(_persisted_json_bytes(_mapping(targets[name]))),
                "sha256": _persisted_sha256(_mapping(targets[name])),
            }
        )
        for name, _ in names_and_paths
    )
    allowed = {
        before_keys,
        (target_keys[0], before_keys[1], before_keys[2]),
        (target_keys[0], target_keys[1], before_keys[2]),
        target_keys,
    }
    if current not in allowed or (committed and current != target_keys):
        raise ValueError("adoption manifests are outside their ordered prefix")
    return current == target_keys


def _release_descriptor_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    return (value["present"], value["bytes"], value["sha256"])


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
    return hashlib.sha256(_persisted_json_bytes(payload)).hexdigest()


def _persisted_json_bytes(payload: Mapping[str, Any]) -> bytes:
    serialized = (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return serialized.encode("utf-8")


def _file_sha256(layout: Any, path: Path) -> str:
    present, data = _local_authority_file(layout, path)
    if not present:
        raise ValueError("journal authority file is missing")
    return hashlib.sha256(data).hexdigest()
