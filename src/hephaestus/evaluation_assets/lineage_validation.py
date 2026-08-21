# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Schemas and receipt dependencies for self-contained extension lineage."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from src.hephaestus.evaluation_assets.control_jsonl import (
    parse_strict_json_object,
    resolve_local_authority_file,
)
from src.hephaestus.evaluation_assets.journal_transitions import (
    PERSISTED_STAGE_VALUES_V2,
)
from src.hephaestus.evaluation_assets.models import PipelineStage

LINEAGE_SCHEMA_VERSION = "fapo-evaluation-asset-lineage-v1"
REUSE_SCHEMA_VERSION = "fapo-evaluation-asset-reuse-v1"
SNAPSHOT_SCHEMA_VERSION = "fapo-evaluation-asset-parent-snapshot-v1"

NATIVE_STAGE_THREE_SEEDS = (
    "feedback_evidence.jsonl",
    "candidate_guidelines.jsonl",
    "evaluation_guidelines.jsonl",
    "trusted_intents.jsonl",
    "trusted_cases.jsonl",
)
LEGACY_STAGE_THREE_SEEDS = (
    "feedback_rubrics.jsonl",
    "trusted_intents.jsonl",
    "trusted_cases.jsonl",
)
COMMON_PARENT_SNAPSHOT_FILES = (
    "parent_intent_inventory.jsonl",
    "parent_intent_matches.jsonl",
    "parent_inferred_cluster_rubrics.jsonl",
    "parent_synthetic_cases.jsonl",
    "parent_train.jsonl",
    "parent_validation.jsonl",
    "parent_test.jsonl",
    "parent_regression_trusted.jsonl",
)
_STATIC_SNAPSHOT_INPUTS = {
    "intent_clustering": ("parent_intent_inventory.jsonl",),
    "coverage_decisions": ("parent_intent_matches.jsonl",),
    "label_inference": (
        "parent_intent_matches.jsonl",
        "parent_inferred_cluster_rubrics.jsonl",
    ),
    "synthetic_coverage": (
        "parent_intent_matches.jsonl",
        "parent_synthetic_cases.jsonl",
    ),
    "dataset_splits": (
        "parent_train.jsonl",
        "parent_validation.jsonl",
        "parent_test.jsonl",
        "parent_regression_trusted.jsonl",
    ),
}
_HASH = re.compile(r"^[0-9a-f]{64}$")
_GENERATION_ID = re.compile(r"^sha256-[0-9a-f]{64}$")
_PARENT_RELEASE_FIELDS = {
    "stage_8_receipt_sha256",
    "released_state_sha256",
    "source_lineage_sha256",
    "release_pointer_sha256",
    "generation_id",
    "generation_manifest_sha256",
    "build_provenance_sha256",
    "build_fingerprint",
}


@dataclass(frozen=True)
class ExtensionEvidence:
    """Validated extension metadata and its exact snapshot inventory."""

    lineage: dict[str, Any]
    reuse: dict[str, Any]
    stage_three_seeds: tuple[str, ...]


def validate_parent_release_evidence(value: Any) -> dict[str, str]:
    """Validate the exact immutable parent-release evidence schema."""
    return _parent_release(value)


def validate_provenance_lineage_identity(value: Any) -> dict[str, Any]:
    """Validate the reduced extension lineage embedded in build provenance."""
    row = _mapping(value)
    _exact_keys(
        row,
        {
            "parent_asset_id",
            "clustering_mode",
            "added_labeled_record_ids",
            "added_unlabeled_record_ids",
            "parent_input_counts",
            "extended_input_counts",
            "parent_generation_id",
            "file_dependencies",
        },
    )
    if not _safe_identifier(row["parent_asset_id"]) or row[
        "clustering_mode"
    ] not in {"keep", "refresh"}:
        raise ValueError("provenance lineage identity is invalid")
    added_labeled = _identifier_list(row["added_labeled_record_ids"])
    added_unlabeled = _identifier_list(row["added_unlabeled_record_ids"])
    if row["clustering_mode"] == "keep" and added_unlabeled:
        raise ValueError("keep provenance lineage cannot add unlabeled records")
    parent_counts = _counts(row["parent_input_counts"])
    extended_counts = _counts(row["extended_input_counts"])
    if extended_counts != {
        "labeled": parent_counts["labeled"] + len(added_labeled),
        "unlabeled": parent_counts["unlabeled"] + len(added_unlabeled),
    }:
        raise ValueError("provenance lineage input counts are inconsistent")
    dependencies = _mapping(row["file_dependencies"])
    _exact_keys(
        dependencies,
        {"lineage_sha256", "reuse_manifest_sha256", "parent_release"},
    )
    if any(
        not isinstance(dependencies[field], str)
        or not _HASH.fullmatch(dependencies[field])
        for field in ("lineage_sha256", "reuse_manifest_sha256")
    ):
        raise ValueError("provenance lineage dependency hash is invalid")
    parent_release = _parent_release(dependencies["parent_release"])
    if row["parent_generation_id"] != parent_release["generation_id"]:
        raise ValueError("provenance lineage generation is inconsistent")
    return row


def validate_extension_evidence(
    layout: Any,
    *,
    require_asset_manifest: bool,
    historical: bool = False,
    artifact_overrides: Mapping[Path, bytes] | None = None,
) -> ExtensionEvidence:
    """Validate complete lineage/reuse schemas and all self-contained snapshots."""
    lineage = _json_object(layout, layout.lineage_path, artifact_overrides)
    reuse = _json_object(layout, layout.reuse_manifest_path, artifact_overrides)
    _exact_keys(
        lineage,
        {
            "schema_version",
            "asset_id",
            "parent_asset_id",
            "creation_mode",
            "clustering_mode",
            "created_at",
            "parent_release",
            "added_labeled_record_ids",
            "added_unlabeled_record_ids",
            "parent_input_counts",
            "extended_input_counts",
        },
    )
    if (
        lineage["schema_version"] != LINEAGE_SCHEMA_VERSION
        or lineage["asset_id"] != layout.asset_id
        or not _safe_identifier(lineage["parent_asset_id"])
        or lineage["parent_asset_id"] == layout.asset_id
        or lineage["creation_mode"] != "incremental_feedback"
        or lineage["clustering_mode"] not in {"keep", "refresh"}
        or not _nonempty_string(lineage["created_at"])
    ):
        raise ValueError("lineage identity or lifecycle is invalid")
    parent_release = _parent_release(lineage["parent_release"])
    added_labeled = _identifier_list(lineage["added_labeled_record_ids"])
    added_unlabeled = _identifier_list(lineage["added_unlabeled_record_ids"])
    if lineage["clustering_mode"] == "keep" and added_unlabeled:
        raise ValueError("keep lineage cannot add unlabeled records")
    parent_counts = _counts(lineage["parent_input_counts"])
    extended_counts = _counts(lineage["extended_input_counts"])
    if extended_counts != {
        "labeled": parent_counts["labeled"] + len(added_labeled),
        "unlabeled": parent_counts["unlabeled"] + len(added_unlabeled),
    }:
        raise ValueError("lineage input counts are inconsistent")
    _validate_child_sources(
        layout,
        added_labeled,
        added_unlabeled,
        extended_counts,
        historical=historical,
        artifact_overrides=artifact_overrides,
    )

    _exact_keys(
        reuse,
        {
            "schema_version",
            "asset_id",
            "parent_asset_id",
            "parent_release",
            "parent_snapshot",
            "seeded_incremental_stage",
            "reused_stages",
        },
    )
    if (
        reuse["schema_version"] != REUSE_SCHEMA_VERSION
        or reuse["asset_id"] != layout.asset_id
        or reuse["parent_asset_id"] != lineage["parent_asset_id"]
        or _parent_release(reuse["parent_release"]) != parent_release
    ):
        raise ValueError("reuse identity differs from lineage")

    seeded = _mapping(reuse["seeded_incremental_stage"])
    _exact_keys(seeded, {"stage", "artifacts", "operation"})
    stage_three_seeds = tuple(_identifier_list(seeded["artifacts"]))
    if (
        seeded["stage"] != "rubric_extraction"
        or seeded["operation"] != "append_evidence_and_rebuild_guidelines"
        or stage_three_seeds
        not in {NATIVE_STAGE_THREE_SEEDS, LEGACY_STAGE_THREE_SEEDS}
    ):
        raise ValueError("seeded incremental stage is invalid")

    reused = reuse["reused_stages"]
    if not isinstance(reused, list):
        raise ValueError("reused stage inventory is invalid")
    if lineage["clustering_mode"] == "keep":
        if len(reused) != 1 or not isinstance(reused[0], Mapping):
            raise ValueError("keep lineage is missing its reused stage")
        row = dict(reused[0])
        _exact_keys(row, {"stage", "artifacts", "reason"})
        if (
            row["stage"] != "intent_clustering"
            or tuple(_identifier_list(row["artifacts"]))
            != ("intent_inventory.jsonl", "cluster_lineage.jsonl")
            or row["reason"]
            != "no unlabeled records or clustering settings changed"
        ):
            raise ValueError("keep reused stage is invalid")
    elif reused:
        raise ValueError("refresh lineage cannot claim reused stages")

    snapshot_root = (
        layout.historical_parent_snapshot
        if historical
        else layout.parent_snapshot
    )
    snapshot = _mapping(reuse["parent_snapshot"])
    _exact_keys(snapshot, {"schema_version", "path", "artifacts"})
    if (
        snapshot["schema_version"] != SNAPSHOT_SCHEMA_VERSION
        or snapshot["path"] != snapshot_root.relative_to(layout.root).as_posix()
        or not isinstance(snapshot["artifacts"], list)
    ):
        raise ValueError("parent snapshot descriptor is invalid")
    expected_names = {
        *(f"parent_{name}" for name in stage_three_seeds),
        *COMMON_PARENT_SNAPSHOT_FILES,
    }
    recorded_names: set[str] = set()
    for raw in snapshot["artifacts"]:
        row = _mapping(raw)
        _exact_keys(row, {"file", "sha256", "bytes"})
        name = row["file"]
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in recorded_names
            or not isinstance(row["sha256"], str)
            or not _HASH.fullmatch(row["sha256"])
            or isinstance(row["bytes"], bool)
            or not isinstance(row["bytes"], int)
            or row["bytes"] < 0
        ):
            raise ValueError("parent snapshot row is invalid")
        recorded_names.add(name)
        path = snapshot_root / name
        payload = _authority_bytes(layout, path, artifact_overrides)
        if (
            len(payload) != row["bytes"]
            or hashlib.sha256(payload).hexdigest() != row["sha256"]
        ):
            raise ValueError("parent snapshot bytes are inconsistent")
    if recorded_names != expected_names:
        raise ValueError("parent snapshot inventory is incomplete")

    if require_asset_manifest:
        manifest = _json_object(
            layout,
            layout.manifest_path,
            artifact_overrides,
        )
        if manifest.get("lineage") != lineage:
            raise ValueError("asset manifest lineage is inconsistent")
    return ExtensionEvidence(
        lineage=lineage,
        reuse=reuse,
        stage_three_seeds=stage_three_seeds,
    )


def extension_receipt_input_paths(
    layout: Any,
    stage: PipelineStage,
    *,
    historical: bool = False,
    artifact_overrides: Mapping[Path, bytes] | None = None,
) -> tuple[Path, ...]:
    """Return validated conditional extension inputs for one receipt."""
    lineage_present = (
        layout.lineage_path in artifact_overrides
        if artifact_overrides is not None
        else layout.lineage_path.is_file()
    )
    reuse_present = (
        layout.reuse_manifest_path in artifact_overrides
        if artifact_overrides is not None
        else layout.reuse_manifest_path.exists()
    )
    if not lineage_present and not reuse_present:
        return ()
    evidence = validate_extension_evidence(
        layout,
        require_asset_manifest=False,
        historical=historical,
        artifact_overrides=artifact_overrides,
    )
    stage_value = stage.value
    ordered = (
        PERSISTED_STAGE_VALUES_V2
        if historical
        else tuple(item.value for item in PipelineStage)
    )
    if stage_value not in ordered[2:]:
        return ()
    snapshot_names = (
        tuple(f"parent_{name}" for name in evidence.stage_three_seeds)
        if stage_value == "rubric_extraction"
        else _STATIC_SNAPSHOT_INPUTS.get(stage_value, ())
    )
    return (
        layout.lineage_path,
        layout.reuse_manifest_path,
        *(
            (
                layout.historical_parent_snapshot
                if historical
                else layout.parent_snapshot
            )
            / name
            for name in snapshot_names
        ),
    )


def extension_receipt_output_paths(
    layout: Any,
    stage: PipelineStage,
    *,
    historical: bool = False,
    artifact_overrides: Mapping[Path, bytes] | None = None,
) -> tuple[Path, ...]:
    """Return extension control files anchored by the final stage receipt."""
    final_stage = (
        PERSISTED_STAGE_VALUES_V2[-1]
        if historical
        else tuple(PipelineStage)[-1].value
    )
    lineage_present = (
        layout.lineage_path in artifact_overrides
        if artifact_overrides is not None
        else layout.lineage_path.is_file()
    )
    if stage.value != final_stage or not lineage_present:
        return ()
    validate_extension_evidence(
        layout,
        require_asset_manifest=True,
        historical=historical,
        artifact_overrides=artifact_overrides,
    )
    return (layout.lineage_path, layout.reuse_manifest_path)


def _validate_child_sources(
    layout: Any,
    added_labeled: tuple[str, ...],
    added_unlabeled: tuple[str, ...],
    counts: Mapping[str, int],
    *,
    historical: bool,
    artifact_overrides: Mapping[Path, bytes] | None,
) -> None:
    feedback_path = (
        layout.historical_feedback_path if historical else layout.feedback_path
    )
    unlabeled_path = (
        layout.historical_unlabeled_path if historical else layout.unlabeled_path
    )
    feedback_ids = _jsonl_ids(layout, feedback_path, artifact_overrides)
    unlabeled_ids = _jsonl_ids(layout, unlabeled_path, artifact_overrides)
    if (
        len(feedback_ids) != counts["labeled"]
        or len(unlabeled_ids) != counts["unlabeled"]
        or not set(added_labeled) <= feedback_ids
        or not set(added_unlabeled) <= unlabeled_ids
    ):
        raise ValueError("lineage source inventory is inconsistent")


def _jsonl_ids(
    layout: Any,
    path: Path,
    artifact_overrides: Mapping[Path, bytes] | None,
) -> set[str]:
    identities: set[str] = set()
    count = 0
    for line in _authority_bytes(
        layout,
        path,
        artifact_overrides,
    ).decode("utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        row = json.loads(line)
        if not isinstance(row, Mapping) or not _safe_identifier(row.get("record_id")):
            raise ValueError("lineage source row is invalid")
        identities.add(str(row["record_id"]))
    if len(identities) != count:
        raise ValueError("lineage source identities are not unique")
    return identities


def _parent_release(value: Any) -> dict[str, str]:
    row = _mapping(value)
    _exact_keys(row, _PARENT_RELEASE_FIELDS)
    if (
        not isinstance(row["generation_id"], str)
        or not _GENERATION_ID.fullmatch(row["generation_id"])
        or any(
            not isinstance(row[field], str) or not _HASH.fullmatch(row[field])
            for field in row
            if field != "generation_id"
        )
    ):
        raise ValueError("parent release evidence is invalid")
    return {field: str(row[field]) for field in _PARENT_RELEASE_FIELDS}


def _counts(value: Any) -> dict[str, int]:
    row = _mapping(value)
    _exact_keys(row, {"labeled", "unlabeled"})
    if any(
        isinstance(row[field], bool)
        or not isinstance(row[field], int)
        or row[field] < 0
        for field in row
    ):
        raise ValueError("lineage counts are invalid")
    return {field: int(row[field]) for field in ("labeled", "unlabeled")}


def _identifier_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not _safe_identifier(item) for item in value):
        raise ValueError("lineage identifier list is invalid")
    values = tuple(str(item) for item in value)
    if len(set(values)) != len(values):
        raise ValueError("lineage identifier list has duplicates")
    return values


def _mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("lineage object is invalid")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError("lineage object fields are invalid")


def _safe_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and "/" not in value and "\\" not in value


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _authority_bytes(
    layout: Any,
    path: Path,
    artifact_overrides: Mapping[Path, bytes] | None,
) -> bytes:
    if artifact_overrides is not None:
        try:
            return artifact_overrides[path]
        except KeyError as exc:
            raise ValueError("lineage authority snapshot is incomplete") from exc
    authority = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="read",
    )
    if authority.data is None:
        raise ValueError("lineage authority read did not return bytes")
    return authority.data


def _json_object(
    layout: Any,
    path: Path,
    artifact_overrides: Mapping[Path, bytes] | None,
) -> dict[str, Any]:
    return parse_strict_json_object(
        _authority_bytes(layout, path, artifact_overrides)
    )
