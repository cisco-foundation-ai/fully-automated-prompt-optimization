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

from src.hephaestus.evaluation_assets.control_jsonl import parse_strict_json_object
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
    PipelineStage.INTENT_CLUSTERING: ("parent_intent_inventory.jsonl",),
    PipelineStage.COVERAGE_DECISIONS: ("parent_intent_matches.jsonl",),
    PipelineStage.LABEL_INFERENCE: (
        "parent_intent_matches.jsonl",
        "parent_inferred_cluster_rubrics.jsonl",
    ),
    PipelineStage.SYNTHETIC_COVERAGE: (
        "parent_intent_matches.jsonl",
        "parent_synthetic_cases.jsonl",
    ),
    PipelineStage.DATASET_SPLITS: (
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
) -> ExtensionEvidence:
    """Validate complete lineage/reuse schemas and all self-contained snapshots."""
    lineage = _json_object(layout.lineage_path)
    reuse = _json_object(layout.reuse_manifest_path)
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
        seeded["stage"] != PipelineStage.RUBRIC_EXTRACTION.value
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
            row["stage"] != PipelineStage.INTENT_CLUSTERING.value
            or tuple(_identifier_list(row["artifacts"]))
            != ("intent_inventory.jsonl", "cluster_lineage.jsonl")
            or row["reason"]
            != "no unlabeled records or clustering settings changed"
        ):
            raise ValueError("keep reused stage is invalid")
    elif reused:
        raise ValueError("refresh lineage cannot claim reused stages")

    snapshot = _mapping(reuse["parent_snapshot"])
    _exact_keys(snapshot, {"schema_version", "path", "artifacts"})
    if (
        snapshot["schema_version"] != SNAPSHOT_SCHEMA_VERSION
        or snapshot["path"] != layout.parent_snapshot.relative_to(layout.root).as_posix()
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
        path = layout.parent_snapshot / name
        if (
            not path.is_file()
            or path.stat().st_size != row["bytes"]
            or _sha256(path) != row["sha256"]
        ):
            raise ValueError("parent snapshot bytes are inconsistent")
    if recorded_names != expected_names:
        raise ValueError("parent snapshot inventory is incomplete")

    if require_asset_manifest:
        manifest = _json_object(layout.manifest_path)
        if manifest.get("lineage") != lineage:
            raise ValueError("asset manifest lineage is inconsistent")
    return ExtensionEvidence(
        lineage=lineage,
        reuse=reuse,
        stage_three_seeds=stage_three_seeds,
    )


def extension_receipt_input_paths(layout: Any, stage: PipelineStage) -> tuple[Path, ...]:
    """Return validated conditional extension inputs for one receipt."""
    if not layout.lineage_path.is_file() and not layout.reuse_manifest_path.exists():
        return ()
    evidence = validate_extension_evidence(layout, require_asset_manifest=False)
    if stage not in tuple(PipelineStage)[2:]:
        return ()
    snapshot_names = (
        tuple(f"parent_{name}" for name in evidence.stage_three_seeds)
        if stage == PipelineStage.RUBRIC_EXTRACTION
        else _STATIC_SNAPSHOT_INPUTS.get(stage, ())
    )
    return (
        layout.lineage_path,
        layout.reuse_manifest_path,
        *(layout.parent_snapshot / name for name in snapshot_names),
    )


def extension_receipt_output_paths(layout: Any, stage: PipelineStage) -> tuple[Path, ...]:
    """Return extension control files anchored by the final stage receipt."""
    if stage != PipelineStage.DATASET_SPLITS or not layout.lineage_path.is_file():
        return ()
    validate_extension_evidence(layout, require_asset_manifest=True)
    return (layout.lineage_path, layout.reuse_manifest_path)


def _validate_child_sources(
    layout: Any,
    added_labeled: tuple[str, ...],
    added_unlabeled: tuple[str, ...],
    counts: Mapping[str, int],
) -> None:
    feedback_ids = _jsonl_ids(layout.feedback_path)
    unlabeled_ids = _jsonl_ids(layout.unlabeled_path)
    if (
        len(feedback_ids) != counts["labeled"]
        or len(unlabeled_ids) != counts["unlabeled"]
        or not set(added_labeled) <= feedback_ids
        or not set(added_unlabeled) <= unlabeled_ids
    ):
        raise ValueError("lineage source inventory is inconsistent")


def _jsonl_ids(path: Path) -> set[str]:
    identities: set[str] = set()
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
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


def _json_object(path: Path) -> dict[str, Any]:
    return parse_strict_json_object(path.read_bytes())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
