# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Durability contracts shared by evaluation-asset mutation paths."""

from __future__ import annotations

import hashlib
import json
import re
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.control_jsonl import (
    capture_local_authority_tree,
    parse_strict_json_object,
    parse_strict_jsonl_objects,
    read_strict_jsonl_objects,
    resolve_local_authority_file,
)
from src.hephaestus.evaluation_assets.input_contract import validate_input_records
from src.hephaestus.evaluation_assets.journal_transitions import (
    _LEGACY_SAFE_ASSET_ID_V1,
    JOURNAL_SCHEMA_VERSION,
    PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2,
    PERSISTED_STAGE_VALUES_V2,
    _legacy_config_value,
    is_exact_legacy_event_row_v1,
    normalized_legacy_completed_state_v1,
)
from src.hephaestus.evaluation_assets.journal_validation import (
    ValidatedRecoveryJournal,
    validate_recovery_journal,
)
from src.hephaestus.evaluation_assets.legacy_validation import (
    validate_legacy_stage_semantics,
)
from src.hephaestus.evaluation_assets.lineage_validation import (
    extension_receipt_input_paths,
    extension_receipt_output_paths,
    validate_extension_evidence,
)
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    LEGACY_STATE_SCHEMA_VERSION,
    STAGE_COUNT_KEYS,
    STAGE_LABELS,
    STATE_SCHEMA_VERSION,
    TOP_LEVEL_STATUSES,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
    StageState,
)
from src.hephaestus.evaluation_assets.provenance import (
    HISTORICAL_LEGACY_PROVENANCE_PROFILE_V1,
    HISTORICAL_LEGACY_PROVENANCE_PROFILE_V2,
    HISTORICAL_PROVENANCE_PROFILE_V1,
    HISTORICAL_PROVENANCE_PROFILE_V2,
    PROMPT_REVISIONS,
    build_algorithm_inventory,
    historical_algorithm_inventory_v1,
    historical_build_provenance_profile,
    historical_legacy_stage_provenance_profile,
    historical_provider_call_stages,
    historical_stage_provenance_profile,
    not_applicable,
    validate_build_provenance,
    validate_build_provenance_call_ledgers,
    validate_stage_provenance,
    working_source_identity,
)
from src.hephaestus.evaluation_assets.publication import (
    LOGICAL_SPLITS,
    resolve_evaluation_asset_release,
    validate_evaluation_asset_release_candidate,
    validate_historical_generation,
)

_RELEASE_AUTHORITY_SNAPSHOT: ContextVar[Mapping[Path, bytes] | None] = ContextVar(
    "evaluation_asset_release_authority_snapshot",
    default=None,
)

STAGE_RECEIPT_SCHEMA_VERSION = "fapo-stage-receipt-v2"
_HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V1 = "fapo-stage-receipt-v1"
_HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V2 = "fapo-stage-receipt-v2"
UNAVAILABLE_PROVENANCE = {
    "status": "unavailable",
    "reason": "provider_call_metadata_not_recorded",
}
LEGACY_UNAVAILABLE_PROVENANCE = {
    "status": "unavailable",
    "reason": "legacy_checkpoint_predates_provenance",
}
_OPERATION_ID = re.compile(r"^[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HISTORICAL_STAGE_RECEIPT_FIELDS_V1 = frozenset(
    {
    "schema_version",
    "stage",
    "stage_index",
    "origin",
    "artifact_profile",
    "completed_at",
    "inputs",
    "upstream_receipts",
    "outputs",
    "resolved_config_sha256",
    "dependency_config_sha256",
    "prompt_set_sha256",
    "provider_identity",
    "provider_identity_sha256",
    "provider_calls_sha256",
    "code",
    "code_sha256",
    "counts",
    }
)
_STAGE_RECEIPT_FIELDS = set(_HISTORICAL_STAGE_RECEIPT_FIELDS_V1)
_HISTORICAL_STAGE_RECEIPT_FIELDS_V2 = frozenset(_STAGE_RECEIPT_FIELDS)
_CREATED_HISTORY_FIELDS = {
    "timestamp",
    "revision",
    "event",
    "configuration",
}
_INHERITED_HISTORY_FIELDS = {
    *_CREATED_HISTORY_FIELDS,
    "parent_asset_id",
}
_UPDATED_HISTORY_FIELDS = {
    "timestamp",
    "revision",
    "event",
    "operation_id",
    "changed_fields",
    "invalidated_from_stage",
    "resume_from_stage",
}


class _HistoricalPipelineStageV2(str, Enum):
    """Immutable stage keys for persisted v1/v2 release authority."""

    RAW_INPUTS = "raw_inputs"
    PREPARED_INPUTS = "prepared_inputs"
    RUBRIC_EXTRACTION = "rubric_extraction"
    INTENT_CLUSTERING = "intent_clustering"
    COVERAGE_DECISIONS = "coverage_decisions"
    LABEL_INFERENCE = "label_inference"
    SYNTHETIC_COVERAGE = "synthetic_coverage"
    DATASET_SPLITS = "dataset_splits"


@dataclass(frozen=True)
class StageSpecification:
    """Declarative artifact and dependency contract for one pipeline stage."""

    required_outputs: tuple[str, ...]
    direct_inputs: tuple[tuple[PipelineStage, str], ...] = ()
    upstream_stages: tuple[PipelineStage, ...] = ()
    config_fields: tuple[str, ...] = ()
    prompt_names: tuple[str, ...] = ()
    provider_roles: tuple[str, ...] = ()
    required_asset_outputs: tuple[str, ...] = ()
    required_catalog_outputs: tuple[str, ...] = ()
    legacy_required_outputs: tuple[str, ...] = ()
    legacy_direct_inputs: tuple[tuple[PipelineStage, str], ...] = ()
    required_evidence_outputs: tuple[str, ...] = ("provenance.json",)


_SPLIT_OUTPUTS = tuple(
    f"{split}{suffix}.jsonl"
    for split in ("train", "validation", "test")
    for suffix in ("_trusted", "_inferred", "_synthetic", "")
) + ("regression_trusted.jsonl", "triage_hold.jsonl")
_LEGACY_CATALOG_OUTPUTS = (
    "train.jsonl",
    "validation.jsonl",
    "test.jsonl",
    "regression_trusted.jsonl",
)

_HISTORICAL_STAGE_SPECIFICATIONS_V1 = MappingProxyType({
    _HistoricalPipelineStageV2.RAW_INPUTS: StageSpecification(
        required_outputs=("input_manifest.json",),
        direct_inputs=(
            (_HistoricalPipelineStageV2.RAW_INPUTS, "labeled_feedback.jsonl"),
            (_HistoricalPipelineStageV2.RAW_INPUTS, "unlabeled.jsonl"),
        ),
    ),
    _HistoricalPipelineStageV2.PREPARED_INPUTS: StageSpecification(
        required_outputs=("normalized_feedback.jsonl", "intent_records.jsonl"),
        direct_inputs=(
            (_HistoricalPipelineStageV2.RAW_INPUTS, "labeled_feedback.jsonl"),
            (_HistoricalPipelineStageV2.RAW_INPUTS, "unlabeled.jsonl"),
        ),
        upstream_stages=(_HistoricalPipelineStageV2.RAW_INPUTS,),
    ),
    _HistoricalPipelineStageV2.RUBRIC_EXTRACTION: StageSpecification(
        required_outputs=(
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
        ),
        direct_inputs=(
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "normalized_feedback.jsonl"),
        ),
        upstream_stages=(
            _HistoricalPipelineStageV2.RAW_INPUTS,
            _HistoricalPipelineStageV2.PREPARED_INPUTS,
        ),
        config_fields=("rubric_provider", "rubric_model", "batch_size"),
        prompt_names=("evidence_extraction", "guideline_synthesis"),
        provider_roles=("rubric",),
        legacy_required_outputs=(
            "feedback_rubrics.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
        ),
    ),
    _HistoricalPipelineStageV2.INTENT_CLUSTERING: StageSpecification(
        required_outputs=("intent_inventory.jsonl",),
        direct_inputs=(
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "intent_records.jsonl"),
        ),
        upstream_stages=(
            _HistoricalPipelineStageV2.RAW_INPUTS,
            _HistoricalPipelineStageV2.PREPARED_INPUTS,
        ),
        config_fields=(
            "embedding_provider",
            "embedding_model",
            "cluster_count",
        ),
        provider_roles=("embedding",),
    ),
    _HistoricalPipelineStageV2.COVERAGE_DECISIONS: StageSpecification(
        required_outputs=(
            "intent_matches.jsonl",
            "coverage_report.md",
            "review_queue/labeling_queue.jsonl",
        ),
        direct_inputs=(
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "intent_records.jsonl"),
            (_HistoricalPipelineStageV2.RUBRIC_EXTRACTION, "trusted_intents.jsonl"),
            (_HistoricalPipelineStageV2.INTENT_CLUSTERING, "intent_inventory.jsonl"),
        ),
        upstream_stages=(
            _HistoricalPipelineStageV2.RAW_INPUTS,
            _HistoricalPipelineStageV2.PREPARED_INPUTS,
            _HistoricalPipelineStageV2.RUBRIC_EXTRACTION,
            _HistoricalPipelineStageV2.INTENT_CLUSTERING,
        ),
        config_fields=(
            "embedding_provider",
            "embedding_model",
            "match_threshold",
            "min_trusted_examples",
            "min_trusted_groups",
            "max_unlabeled_to_trusted_ratio",
        ),
        provider_roles=("embedding",),
    ),
    _HistoricalPipelineStageV2.LABEL_INFERENCE: StageSpecification(
        required_outputs=(
            "inferred_unlabeled_cluster_rubrics.jsonl",
            "inferred_unlabeled_labels.jsonl",
            "missing_labeled_feedback_clusters.jsonl",
            "missing_labeled_feedback_report.md",
            "inferred_cases.jsonl",
        ),
        direct_inputs=(
            (_HistoricalPipelineStageV2.RAW_INPUTS, "unlabeled.jsonl"),
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "normalized_feedback.jsonl"),
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "intent_records.jsonl"),
            (
                _HistoricalPipelineStageV2.RUBRIC_EXTRACTION,
                "evaluation_guidelines.jsonl",
            ),
            (_HistoricalPipelineStageV2.INTENT_CLUSTERING, "intent_inventory.jsonl"),
            (_HistoricalPipelineStageV2.COVERAGE_DECISIONS, "intent_matches.jsonl"),
        ),
        upstream_stages=(
            _HistoricalPipelineStageV2.RAW_INPUTS,
            _HistoricalPipelineStageV2.PREPARED_INPUTS,
            _HistoricalPipelineStageV2.RUBRIC_EXTRACTION,
            _HistoricalPipelineStageV2.INTENT_CLUSTERING,
            _HistoricalPipelineStageV2.COVERAGE_DECISIONS,
        ),
        config_fields=("rubric_provider", "rubric_model", "batch_size"),
        prompt_names=("label_inference",),
        provider_roles=("rubric",),
        legacy_direct_inputs=(
            (_HistoricalPipelineStageV2.RAW_INPUTS, "unlabeled.jsonl"),
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "normalized_feedback.jsonl"),
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "intent_records.jsonl"),
            (_HistoricalPipelineStageV2.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl"),
            (_HistoricalPipelineStageV2.INTENT_CLUSTERING, "intent_inventory.jsonl"),
            (_HistoricalPipelineStageV2.COVERAGE_DECISIONS, "intent_matches.jsonl"),
        ),
    ),
    _HistoricalPipelineStageV2.SYNTHETIC_COVERAGE: StageSpecification(
        required_outputs=(
            "synthetic_candidates.jsonl",
            "rejected_synthetic.jsonl",
            "synthetic_filter_issues.jsonl",
            "synthetic_cases.jsonl",
        ),
        direct_inputs=(
            (_HistoricalPipelineStageV2.PREPARED_INPUTS, "intent_records.jsonl"),
            (_HistoricalPipelineStageV2.RUBRIC_EXTRACTION, "trusted_cases.jsonl"),
            (_HistoricalPipelineStageV2.INTENT_CLUSTERING, "intent_inventory.jsonl"),
            (
                _HistoricalPipelineStageV2.LABEL_INFERENCE,
                "inferred_unlabeled_cluster_rubrics.jsonl",
            ),
            (_HistoricalPipelineStageV2.LABEL_INFERENCE, "inferred_cases.jsonl"),
        ),
        upstream_stages=(
            _HistoricalPipelineStageV2.RAW_INPUTS,
            _HistoricalPipelineStageV2.PREPARED_INPUTS,
            _HistoricalPipelineStageV2.RUBRIC_EXTRACTION,
            _HistoricalPipelineStageV2.INTENT_CLUSTERING,
            _HistoricalPipelineStageV2.COVERAGE_DECISIONS,
            _HistoricalPipelineStageV2.LABEL_INFERENCE,
        ),
        config_fields=(
            "rubric_provider",
            "rubric_model",
            "batch_size",
            "synthetic_coverage_enabled",
            "synthetic_cases_per_cluster",
        ),
        prompt_names=("synthetic_coverage",),
        provider_roles=("rubric",),
    ),
    _HistoricalPipelineStageV2.DATASET_SPLITS: StageSpecification(
        required_outputs=_SPLIT_OUTPUTS
        + ("dataset_manifest.json", "generation_manifest.json"),
        legacy_required_outputs=_SPLIT_OUTPUTS + ("dataset_manifest.json",),
        direct_inputs=(
            (_HistoricalPipelineStageV2.RAW_INPUTS, "input_manifest.json"),
            (_HistoricalPipelineStageV2.RUBRIC_EXTRACTION, "trusted_cases.jsonl"),
            (_HistoricalPipelineStageV2.LABEL_INFERENCE, "inferred_cases.jsonl"),
            (_HistoricalPipelineStageV2.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl"),
        ),
        upstream_stages=(
            _HistoricalPipelineStageV2.RAW_INPUTS,
            _HistoricalPipelineStageV2.PREPARED_INPUTS,
            _HistoricalPipelineStageV2.RUBRIC_EXTRACTION,
            _HistoricalPipelineStageV2.INTENT_CLUSTERING,
            _HistoricalPipelineStageV2.COVERAGE_DECISIONS,
            _HistoricalPipelineStageV2.LABEL_INFERENCE,
            _HistoricalPipelineStageV2.SYNTHETIC_COVERAGE,
        ),
        config_fields=("split_seed",),
        required_asset_outputs=("asset_manifest.json", "build_provenance.json"),
    ),
})
STAGE_SPECIFICATIONS = dict(_HISTORICAL_STAGE_SPECIFICATIONS_V1)

_HISTORICAL_STAGE_LABELS_V1 = MappingProxyType(
    {
        _HistoricalPipelineStageV2.RAW_INPUTS: "Validate raw inputs",
        _HistoricalPipelineStageV2.PREPARED_INPUTS: "Prepare canonical inputs",
        _HistoricalPipelineStageV2.RUBRIC_EXTRACTION: "Create evaluation guidelines",
        _HistoricalPipelineStageV2.INTENT_CLUSTERING: "Mine intent clusters",
        _HistoricalPipelineStageV2.COVERAGE_DECISIONS: "Apply coverage decisions",
        _HistoricalPipelineStageV2.LABEL_INFERENCE: "Infer reviewable labels",
        _HistoricalPipelineStageV2.SYNTHETIC_COVERAGE: "Optional synthetic coverage",
        _HistoricalPipelineStageV2.DATASET_SPLITS: "Build dataset splits",
    }
)
_HISTORICAL_PIPELINE_STAGES_V1 = (
    _HistoricalPipelineStageV2.RAW_INPUTS,
    _HistoricalPipelineStageV2.PREPARED_INPUTS,
    _HistoricalPipelineStageV2.RUBRIC_EXTRACTION,
    _HistoricalPipelineStageV2.INTENT_CLUSTERING,
    _HistoricalPipelineStageV2.COVERAGE_DECISIONS,
    _HistoricalPipelineStageV2.LABEL_INFERENCE,
    _HistoricalPipelineStageV2.SYNTHETIC_COVERAGE,
    _HistoricalPipelineStageV2.DATASET_SPLITS,
)
if tuple(stage.value for stage in _HISTORICAL_PIPELINE_STAGES_V1) != (
    PERSISTED_STAGE_VALUES_V2
):
    raise RuntimeError("persisted stage profiles are inconsistent")
_HISTORICAL_STAGE_BY_VALUE_V1 = MappingProxyType(
    {stage.value: stage for stage in _HISTORICAL_PIPELINE_STAGES_V1}
)
_HISTORICAL_STAGE_INDEX_V1 = MappingProxyType(
    {
        stage: index
        for index, stage in enumerate(_HISTORICAL_PIPELINE_STAGES_V1, start=1)
    }
)
_HISTORICAL_STAGE_INDEX_BY_VALUE_V1 = MappingProxyType(
    {
        stage.value: index
        for stage, index in _HISTORICAL_STAGE_INDEX_V1.items()
    }
)

_HISTORICAL_STAGE_COUNT_KEYS_V1 = MappingProxyType(
    {
        _HistoricalPipelineStageV2.RAW_INPUTS: frozenset(
            {"feedback_records", "unlabeled_records"}
        ),
        _HistoricalPipelineStageV2.PREPARED_INPUTS: frozenset(
            {"prepared_feedback", "prepared_intents"}
        ),
        _HistoricalPipelineStageV2.RUBRIC_EXTRACTION: frozenset(
            {
                "feedback_evidence",
                "candidate_guidelines",
                "evaluation_guidelines",
                "trusted_cases",
            }
        ),
        _HistoricalPipelineStageV2.INTENT_CLUSTERING: frozenset({"intent_clusters"}),
        _HistoricalPipelineStageV2.COVERAGE_DECISIONS: frozenset(
            {
                "matched_clusters",
                "needs_more_feedback_clusters",
                "missing_label_clusters",
                "labeling_queue_clusters",
                "labeling_queue_traces",
            }
        ),
        _HistoricalPipelineStageV2.LABEL_INFERENCE: frozenset(
            {"inferred_cases", "review_clusters"}
        ),
        _HistoricalPipelineStageV2.SYNTHETIC_COVERAGE: frozenset(
            {"synthetic_cases", "rejected_synthetic_cases"}
        ),
        _HistoricalPipelineStageV2.DATASET_SPLITS: frozenset(
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
_HISTORICAL_COMPLETED_COUNT_FIELDS_V1 = frozenset(
    key for keys in _HISTORICAL_STAGE_COUNT_KEYS_V1.values() for key in keys
)

# Keep the config dependency map and receipt projections synchronized.
for _config_field, _stage in CONFIG_STAGE_DEPENDENCIES.items():
    if _config_field not in STAGE_SPECIFICATIONS[_stage].config_fields:
        raise RuntimeError(
            f"Missing receipt config dependency {_config_field} for {_stage.value}"
        )


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize deterministic JSON bytes for dependency identities."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    """Hash one canonical JSON value."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _local_authority_bytes(layout: Any, path: Path) -> bytes:
    """Read one exact no-follow authority file beneath the tenants root."""
    snapshot = _RELEASE_AUTHORITY_SNAPSHOT.get()
    if snapshot is not None:
        lexical_path = Path(path).absolute()
        try:
            return snapshot[lexical_path]
        except KeyError as exc:
            raise ValueError("release authority snapshot is incomplete") from exc
    authority = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="read",
    )
    if authority.data is None:
        raise ValueError("local authority read did not return bytes")
    return authority.data


def _local_authority_sha256(layout: Any, path: Path) -> str:
    """Hash the exact bytes read from one no-follow authority handle."""
    return hashlib.sha256(_local_authority_bytes(layout, path)).hexdigest()


def _local_authority_node_exists(layout: Any, path: Path) -> bool:
    """Observe one authority node without following it or splitting probes."""
    try:
        return resolve_local_authority_file(
            path,
            layout.tenants_root,
            access="read_optional",
        ).exists
    except (OSError, ValueError):
        return True


def _validate_local_authority_layout(layout: Any) -> None:
    """Preflight every mutable or persisted local authority file without writes."""
    workspace_generation_manifest = layout.artifact_path(
        _HISTORICAL_PIPELINE_STAGES_V1[-1],
        "generation_manifest.json",
    )
    paths = [
        layout.state_path,
        layout.config_path,
        layout.config_history_path,
        layout.events_path,
        layout.recovery_journal_path,
        layout.historical_feedback_path,
        layout.historical_unlabeled_path,
        layout.lineage_path,
        layout.reuse_manifest_path,
        layout.build_provenance_path,
        layout.manifest_path,
        layout.release_pointer_path,
        layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[0],
            "input_manifest.json",
        ),
        layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[-1],
            "dataset_manifest.json",
        ),
        workspace_generation_manifest,
    ]
    for stage in _HISTORICAL_PIPELINE_STAGES_V1:
        paths.extend(
            (
                layout.receipt_path(stage),
                layout.stage_provenance_path(stage),
                layout.artifact_path(stage, "provider_calls.jsonl"),
            )
        )
    captured = {
        path: resolve_local_authority_file(
            path,
            layout.tenants_root,
            access="read_optional",
        )
        for path in paths
    }
    generation_ids: set[str] = set()
    for control_path in (workspace_generation_manifest, layout.release_pointer_path):
        control = captured[control_path]
        if not control.exists:
            continue
        raw = control.data
        if raw is None:
            continue
        try:
            generation_id = parse_strict_json_object(raw).get("generation_id")
        except ValueError:
            continue
        if isinstance(generation_id, str) and re.fullmatch(
            r"sha256-[0-9a-f]{64}",
            generation_id,
        ):
            generation_ids.add(generation_id)
    for generation_id in generation_ids:
        generation_root = layout.generations_root / generation_id
        for name in (
            "generation_manifest.json",
            *(f"{split}.jsonl" for split in ("train", "validation", "test", "regression_trusted")),
        ):
            resolve_local_authority_file(
                generation_root / name,
                layout.tenants_root,
                access="read_optional",
            )


_PIPELINE_STATE_FIELDS = {
    "asset_id",
    "counts",
    "created_at",
    "current_stage",
    "error",
    "last_operation_id",
    "mutation_sequence",
    "schema_version",
    "stages",
    "status",
    "tenant_id",
    "updated_at",
}
_STAGE_STATE_FIELDS = {
    "completed_at",
    "label",
    "message",
    "receipt_sha256",
    "stage",
    "started_at",
    "status",
}
_CONFIG_STRING_FIELDS = {
    "asset_id",
    "embedding_model",
    "embedding_provider",
    "rubric_model",
    "rubric_provider",
    "tenant_id",
}
_CONFIG_INTEGER_FIELDS = {
    "batch_size",
    "cluster_count",
    "min_trusted_examples",
    "min_trusted_groups",
    "split_seed",
    "synthetic_cases_per_cluster",
}
_CONFIG_FLOAT_FIELDS = {"match_threshold"}
_CONFIG_OPTIONAL_FLOAT_FIELDS = {"max_unlabeled_to_trusted_ratio"}
_CONFIG_BOOLEAN_FIELDS = {"synthetic_coverage_enabled"}
_CONFIG_FIELDS = (
    _CONFIG_STRING_FIELDS
    | _CONFIG_INTEGER_FIELDS
    | _CONFIG_FLOAT_FIELDS
    | _CONFIG_OPTIONAL_FLOAT_FIELDS
    | _CONFIG_BOOLEAN_FIELDS
)
_PRE_V2_CONFIG_FIELDS = frozenset(
    {
        "asset_id",
        "batch_size",
        "cluster_count",
        "embedding_model",
        "embedding_provider",
        "match_threshold",
        "max_unlabeled_to_trusted_ratio",
        "min_trusted_examples",
        "min_trusted_groups",
        "rubric_model",
        "rubric_provider",
        "split_seed",
        "synthetic_cases_per_cluster",
        "synthetic_coverage_enabled",
        "tenant_id",
    }
)
_COMPLETED_COUNT_FIELDS = _HISTORICAL_COMPLETED_COUNT_FIELDS_V1


def _is_json_integer(value: Any) -> bool:
    """Return whether a strict JSON scalar is an integer but not a boolean."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_exact_pre_v2_config_value(field: str, value: Any) -> bool:
    """Validate one scalar against the immutable pre-v2 writer domain."""
    if field in {"asset_id", "tenant_id"}:
        return isinstance(value, str) and bool(value)
    return _legacy_config_value(field, value)


def _exact_pre_v2_config_mapping(
    layout: Any,
    value: Any,
) -> dict[str, Any]:
    """Return one type-exact configuration from the frozen pre-v2 profile."""
    if (
        not isinstance(value, Mapping)
        or set(value) != _PRE_V2_CONFIG_FIELDS
        or any(
            not _is_exact_pre_v2_config_value(str(field), item)
            for field, item in value.items()
        )
        or value.get("tenant_id") != layout.tenant_id
        or value.get("asset_id") != layout.asset_id
    ):
        raise ValueError("pre-v2 configuration is invalid")
    return dict(value)


def _exact_v2_state(
    raw: Mapping[str, Any],
    *,
    historical: bool = True,
) -> PipelineState:
    """Validate a closed v2 state against a historical or authoring profile."""
    ordered_stages = (
        _HISTORICAL_PIPELINE_STAGES_V1
        if historical
        else tuple(PipelineStage)
    )
    stage_labels = (
        _HISTORICAL_STAGE_LABELS_V1 if historical else STAGE_LABELS
    )
    if historical:
        count_fields = _COMPLETED_COUNT_FIELDS
        current_count_fields = frozenset()
    else:
        current_count_fields = frozenset().union(
            *(frozenset(STAGE_COUNT_KEYS[stage]) for stage in ordered_stages)
        )
        count_fields = _COMPLETED_COUNT_FIELDS | current_count_fields
    if set(raw) != _PIPELINE_STATE_FIELDS:
        raise ValueError("v2 state field inventory is invalid")
    if any(
        not isinstance(raw.get(field), str)
        for field in {
            "asset_id",
            "created_at",
            "schema_version",
            "status",
            "tenant_id",
            "updated_at",
        }
    ) or (
        raw.get("schema_version") != STATE_SCHEMA_VERSION
        or raw.get("status") not in TOP_LEVEL_STATUSES
    ):
        raise ValueError("v2 state scalar identity is invalid")
    if not _canonical_utc_timestamp(raw["created_at"]) or not (
        _canonical_utc_timestamp(raw["updated_at"])
    ):
        raise ValueError("v2 state timestamp identity is invalid")
    if raw.get("current_stage") is not None and (
        not isinstance(raw["current_stage"], str)
        or raw["current_stage"]
        not in {stage.value for stage in ordered_stages}
    ):
        raise ValueError("v2 state stage cursor is invalid")
    if raw.get("error") is not None and not isinstance(raw["error"], str):
        raise ValueError("v2 state error identity is invalid")
    if raw.get("last_operation_id") is not None and (
        not isinstance(raw["last_operation_id"], str)
        or not _OPERATION_ID.fullmatch(raw["last_operation_id"])
    ):
        raise ValueError("v2 state operation identity is invalid")
    sequence = raw.get("mutation_sequence")
    if not _is_json_integer(sequence) or sequence < 0:
        raise ValueError("v2 state mutation identity is invalid")
    counts = raw.get("counts")
    if (
        not isinstance(counts, dict)
        or not set(counts) <= count_fields
        or any(
            not _is_json_integer(value) or value < 0
            for value in counts.values()
        )
    ):
        raise ValueError("v2 state count identity is invalid")
    stages = raw.get("stages")
    if not isinstance(stages, list):
        raise ValueError("v2 state stage inventory is invalid")
    current_stage_values = {stage.value for stage in ordered_stages}
    historical_stage_values = {
        stage.value for stage in _HISTORICAL_PIPELINE_STAGES_V1
    }
    raw_stage_values = [
        stage.get("stage") if isinstance(stage, Mapping) else None
        for stage in stages
    ]
    if historical:
        if raw_stage_values != [stage.value for stage in ordered_stages]:
            raise ValueError("v2 state stage inventory is invalid")
    elif (
        len(raw_stage_values) != len(set(raw_stage_values))
        or frozenset(raw_stage_values)
        not in {frozenset(current_stage_values), frozenset(historical_stage_values)}
    ):
        raise ValueError("v2 mutable state stage inventory is invalid")
    labels_by_value: dict[str, frozenset[str]] = {}
    for stage, label in _HISTORICAL_STAGE_LABELS_V1.items():
        labels_by_value[stage.value] = frozenset({label})
    for stage, label in stage_labels.items():
        labels_by_value[stage.value] = labels_by_value.get(
            stage.value,
            frozenset(),
        ) | frozenset({label})
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict) or set(stage) != _STAGE_STATE_FIELDS:
            raise ValueError("v2 state stage schema is invalid")
        if any(
            not isinstance(stage.get(field), str)
            for field in {"label", "message", "stage", "status"}
        ):
            raise ValueError("v2 state stage scalar identity is invalid")
        if (
            stage["stage"] not in labels_by_value
            or stage["label"] not in labels_by_value[stage["stage"]]
            or historical
            and stage["stage"] != ordered_stages[index].value
            or stage["status"] not in {"pending", "running", "completed", "failed"}
        ):
            raise ValueError("v2 state stage lifecycle is invalid")
        if any(
            stage.get(field) is not None and not isinstance(stage[field], str)
            for field in {"completed_at", "receipt_sha256", "started_at"}
        ):
            raise ValueError("v2 state stage evidence type is invalid")
        for field in {"completed_at", "started_at"}:
            if stage.get(field) is not None and not _canonical_utc_timestamp(
                stage[field]
            ):
                raise ValueError("v2 state stage timestamp is invalid")
        if stage.get("receipt_sha256") is not None and not _SHA256.fullmatch(
            stage["receipt_sha256"]
        ):
            raise ValueError("v2 state stage receipt identity is invalid")
    if not historical:
        normalized = PipelineState.from_dict(raw)
        normalized.counts = {
            key: value
            for key, value in normalized.counts.items()
            if key in current_count_fields
        }
        return normalized
    return PipelineState(
        tenant_id=raw["tenant_id"],
        asset_id=raw["asset_id"],
        schema_version=raw["schema_version"],
        status=raw["status"],
        current_stage=raw["current_stage"],
        created_at=raw["created_at"],
        updated_at=raw["updated_at"],
        error=raw["error"],
        counts=dict(raw["counts"]),
        stages=[StageState(**dict(stage)) for stage in stages],
        mutation_sequence=raw["mutation_sequence"],
        last_operation_id=raw["last_operation_id"],
    )


def _exact_completed_state(raw: Mapping[str, Any]) -> PipelineState:
    """Validate and load one closed, type-exact completed v2 state object."""
    state = _exact_v2_state(raw)
    counts = raw["counts"]
    if set(counts) != _COMPLETED_COUNT_FIELDS:
        raise ValueError("completed state count inventory is invalid")
    for stage in raw["stages"]:
        if (
            stage["status"] != "completed"
            or not _canonical_utc_timestamp(stage.get("started_at"))
            or not _canonical_utc_timestamp(stage.get("completed_at"))
            or not isinstance(stage.get("receipt_sha256"), str)
            or not _SHA256.fullmatch(stage["receipt_sha256"])
        ):
            raise ValueError("completed state stage evidence is invalid")
    return state


def _exact_evaluation_asset_config(
    raw: Mapping[str, Any],
) -> EvaluationAssetConfig:
    """Validate and load one closed, type-exact evaluation asset config."""
    if set(raw) != _CONFIG_FIELDS:
        raise ValueError("evaluation asset configuration fields are invalid")
    if any(
        not isinstance(raw.get(field), str) for field in _CONFIG_STRING_FIELDS
    ):
        raise ValueError("evaluation asset configuration strings are invalid")
    if any(
        not _is_json_integer(raw.get(field)) for field in _CONFIG_INTEGER_FIELDS
    ):
        raise ValueError("evaluation asset configuration integers are invalid")
    if any(
        not isinstance(raw.get(field), float) for field in _CONFIG_FLOAT_FIELDS
    ):
        raise ValueError("evaluation asset configuration floats are invalid")
    if any(
        raw.get(field) is not None and not isinstance(raw[field], float)
        for field in _CONFIG_OPTIONAL_FLOAT_FIELDS
    ):
        raise ValueError("evaluation asset optional configuration floats are invalid")
    if any(
        not isinstance(raw.get(field), bool) for field in _CONFIG_BOOLEAN_FIELDS
    ):
        raise ValueError("evaluation asset configuration booleans are invalid")
    config = EvaluationAssetConfig.from_dict(raw)
    if canonical_json_bytes(raw) != canonical_json_bytes(config.to_dict()):
        raise ValueError("evaluation asset configuration coercion is forbidden")
    return config


def persisted_json_sha256(payload: Mapping[str, Any]) -> str:
    """Hash the exact bytes emitted by the shared JSON artifact writer."""
    serialized = (
        json.dumps(dict(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    """Hash a file without loading it entirely into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_stage_receipt(
    layout: Any,
    stage: PipelineStage | str,
    config: EvaluationAssetConfig,
    counts: Mapping[str, int],
    *,
    completed_at: str,
    prompt_values: Mapping[str, str],
    provider_identity: Mapping[str, Any] | None = None,
    origin: str = "native",
    historical_unavailable: bool = False,
    upstream_receipts: Mapping[PipelineStage, Mapping[str, Any]] | None = None,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    artifact_path_overrides: Mapping[tuple[str, str], Path] | None = None,
    artifact_profile_override: str | None = None,
) -> dict[str, Any]:
    """Build one receipt after all declared stage outputs exist."""
    stage_value = str(getattr(stage, "value", stage))
    stage = (
        _HISTORICAL_STAGE_BY_VALUE_V1[stage_value]
        if historical_unavailable
        else PipelineStage(stage_value)
    )
    specification = (
        _HISTORICAL_STAGE_SPECIFICATIONS_V1[stage]
        if historical_unavailable
        else STAGE_SPECIFICATIONS[stage]
    )
    if artifact_profile_override is not None:
        if origin != "legacy_adoption" or artifact_profile_override not in {
            "native",
            "legacy",
        }:
            raise ValueError("receipt artifact profile override is invalid")
        artifact_profile = artifact_profile_override
        required_outputs, direct_inputs = _declared_artifacts_for_profile(
            specification,
            artifact_profile,
        )
    else:
        required_outputs, direct_inputs, artifact_profile = _stage_artifact_profile(
            layout,
            stage,
            allow_legacy=origin == "legacy_adoption",
            specification=specification,
            artifact_snapshot=(
                dict(artifact_overrides)
                if origin == "legacy_adoption" and artifact_overrides is not None
                else None
            ),
        )

    def selected_path(selected_stage: PipelineStage, name: str) -> Path:
        key = (selected_stage.value, name)
        if artifact_path_overrides is not None:
            try:
                return artifact_path_overrides[key]
            except KeyError as exc:
                raise ValueError(
                    "legacy artifact path snapshot is incomplete"
                ) from exc
        return layout.artifact_path(selected_stage, name)

    closed_legacy_snapshot = origin == "legacy_adoption"
    unavailable = (
        LEGACY_UNAVAILABLE_PROVENANCE
        if historical_unavailable
        else UNAVAILABLE_PROVENANCE
    )
    inputs = [
        _file_record(
            layout,
            selected_path(input_stage, name),
            scope="asset",
            artifact_overrides=artifact_overrides,
            closed_overrides=closed_legacy_snapshot,
        )
        for input_stage, name in direct_inputs
    ]
    inputs.extend(
        _file_record(
            layout,
            path,
            scope="asset",
            artifact_overrides=artifact_overrides,
            closed_overrides=closed_legacy_snapshot,
        )
        for path in extension_receipt_input_paths(
            layout,
            stage,
            historical=historical_unavailable,
            artifact_overrides=artifact_overrides,
        )
    )
    outputs = [
        _file_record(
            layout,
            selected_path(stage, name),
            scope="asset",
            required=True,
            artifact_overrides=artifact_overrides,
            closed_overrides=closed_legacy_snapshot,
        )
        for name in required_outputs
    ]
    outputs.extend(
        _file_record(
            layout,
            _stage_evidence_path(layout, stage, name),
            scope="asset",
            required=True,
            artifact_overrides=artifact_overrides,
        )
        for name in specification.required_evidence_outputs
    )
    if not historical_unavailable and specification.provider_roles:
        outputs.append(
            _file_record(
                layout,
                layout.artifact_path(stage, "provider_calls.jsonl"),
                scope="asset",
                required=True,
                artifact_overrides=artifact_overrides,
                closed_overrides=closed_legacy_snapshot,
            )
        )
    lineage_present = (
        layout.lineage_path in artifact_overrides
        if artifact_overrides is not None
        else layout.lineage_path.is_file()
    )
    if stage.value == "intent_clustering" and lineage_present:
        outputs.append(
            _file_record(
                layout,
                selected_path(stage, "cluster_lineage.jsonl"),
                scope="asset",
                required=True,
                artifact_overrides=artifact_overrides,
                closed_overrides=closed_legacy_snapshot,
            )
        )
    outputs.extend(
        _file_record(
            layout,
            layout.root / name,
            scope="asset",
            required=True,
            artifact_overrides=artifact_overrides,
            closed_overrides=closed_legacy_snapshot,
        )
        for name in specification.required_asset_outputs
    )
    outputs.extend(
        _file_record(
            layout,
            layout.published_datasets / name,
            scope="tenant",
            required=True,
            artifact_overrides=artifact_overrides,
            closed_overrides=closed_legacy_snapshot,
        )
        for name in specification.required_catalog_outputs
    )
    outputs.extend(
        _file_record(
            layout,
            path,
            scope="asset",
            required=True,
            artifact_overrides=artifact_overrides,
            closed_overrides=closed_legacy_snapshot,
        )
        for path in extension_receipt_output_paths(
            layout,
            stage,
            historical=historical_unavailable,
            artifact_overrides=artifact_overrides,
        )
    )
    upstream = []
    for dependency in specification.upstream_stages:
        if upstream_receipts is None:
            receipt_path = layout.receipt_path(dependency)
            receipt_hash = _local_authority_sha256(layout, receipt_path)
        else:
            receipt_hash = persisted_json_sha256(
                upstream_receipts[dependency.value]
            )
        upstream.append({"stage": dependency.value, "sha256": receipt_hash})

    resolved_config = config.to_dict()
    dependency_config = {
        field: resolved_config[field] for field in specification.config_fields
    }
    prompts = (
        unavailable
        if historical_unavailable
        else {
            name: hashlib.sha256(prompt_values[name].encode("utf-8")).hexdigest()
            for name in specification.prompt_names
        }
        if specification.prompt_names
        else {"status": "not_applicable"}
    )
    providers = (
        unavailable
        if historical_unavailable
        else dict(provider_identity)
        if provider_identity is not None
        else _provider_identity(config, specification.provider_roles)
    )
    code = unavailable if historical_unavailable else _code_identity()
    provider_calls_sha256 = (
        canonical_sha256(unavailable)
        if historical_unavailable
        else _local_authority_sha256(
            layout,
            layout.artifact_path(stage, "provider_calls.jsonl"),
        )
        if specification.provider_roles
        else canonical_sha256(not_applicable("stage_has_no_provider_role"))
    )
    receipt = {
        "schema_version": STAGE_RECEIPT_SCHEMA_VERSION,
        "stage": stage.value,
        "stage_index": (
            _HISTORICAL_STAGE_INDEX_BY_VALUE_V1[stage.value]
            if historical_unavailable
            else list(PipelineStage).index(stage) + 1
        ),
        "origin": origin,
        "artifact_profile": artifact_profile,
        "completed_at": completed_at,
        "inputs": inputs,
        "upstream_receipts": upstream,
        "outputs": outputs,
        "resolved_config_sha256": canonical_sha256(resolved_config),
        "dependency_config_sha256": canonical_sha256(dependency_config),
        "prompt_set_sha256": canonical_sha256(prompts),
        "provider_identity": providers,
        "provider_identity_sha256": canonical_sha256(providers),
        "provider_calls_sha256": provider_calls_sha256,
        "code": code,
        "code_sha256": canonical_sha256(code),
        "counts": {str(key): int(value) for key, value in counts.items()},
    }
    if stage.value == "dataset_splits":
        receipt["config_history_sha256"] = _local_authority_sha256(
            layout,
            layout.config_history_path
        )
        receipt["build_provenance_sha256"] = _local_authority_sha256(
            layout,
            layout.build_provenance_path
        )
        generation_manifest_path = layout.artifact_path(
            stage,
            "generation_manifest.json",
        )
        generation_override = (artifact_overrides or {}).get(
            generation_manifest_path
        )
        receipt["generation_manifest_sha256"] = (
            hashlib.sha256(generation_override).hexdigest()
            if generation_override is not None
            else _local_authority_sha256(layout, generation_manifest_path)
        )
    return receipt


def current_dependency_hashes(
    stage: PipelineStage,
    config: EvaluationAssetConfig,
    prompt_values: Mapping[str, str],
    provider_identity: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Return mutable-resume dependency identities for one stage."""
    specification = STAGE_SPECIFICATIONS[stage]
    config_values = config.to_dict()
    prompts = (
        {
            name: hashlib.sha256(prompt_values[name].encode("utf-8")).hexdigest()
            for name in specification.prompt_names
        }
        if specification.prompt_names
        else {"status": "not_applicable"}
    )
    code = _code_identity()
    return {
        "dependency_config_sha256": canonical_sha256(
            {field: config_values[field] for field in specification.config_fields}
        ),
        "prompt_set_sha256": canonical_sha256(prompts),
        "provider_identity_sha256": canonical_sha256(
            dict(provider_identity)
            if provider_identity is not None
            else _provider_identity(config, specification.provider_roles)
        ),
        "code_sha256": canonical_sha256(code),
    }


def verify_released_asset(layout: Any, state: PipelineState) -> None:
    """Verify a released receipt/artifact chain without current-code equality."""
    if (
        state.schema_version == "fapo-evaluation-asset-state-v2"
        and state.status == "released"
        and not layout.release_pointer_path.is_file()
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "this interim v2 release has no release.json publication pointer; "
            "repair it from a verified backup or rebuild it as a new asset version",
        )
    _verify_release_evidence(
        layout,
        state,
        require_persisted_state=True,
        candidate_receipts=None,
    )


def verify_release_candidate(
    layout: Any,
    state: PipelineState,
    *,
    receipts: Mapping[PipelineStage, Mapping[str, Any]] | None = None,
    release_pointer: Mapping[str, Any] | None = None,
) -> None:
    """Verify complete terminal evidence before installing released authority."""
    _verify_release_evidence(
        layout,
        state,
        require_persisted_state=False,
        candidate_receipts=receipts,
        candidate_release_pointer=release_pointer,
    )


def verify_completed_release_candidate(
    layout: Any,
    state: PipelineState,
) -> Any:
    """Verify one completed handoff against a single closed authority snapshot."""
    try:
        authority_snapshot, authority_records = _capture_release_authority(layout)
    except (OSError, TypeError, ValueError) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "completed release candidate evidence is invalid; restore it from a "
            "verified backup or rebuild a new asset version",
        ) from exc
    snapshot_token = _RELEASE_AUTHORITY_SNAPSHOT.set(authority_snapshot)
    try:
        generation = _verify_completed_release_candidate(layout, state)
        current_snapshot, current_records = _capture_release_authority(layout)
        if (
            current_snapshot != authority_snapshot
            or current_records != authority_records
        ):
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "completed handoff authority changed during verification",
            )
        return generation
    finally:
        _RELEASE_AUTHORITY_SNAPSHOT.reset(snapshot_token)


def _verify_completed_release_candidate(
    layout: Any,
    state: PipelineState,
) -> Any:
    """Read-only verify a fully receipted native handoff before any resume write."""
    try:
        _validate_local_authority_layout(layout)
        persisted_state = parse_strict_json_object(
            _local_authority_bytes(layout, layout.state_path)
        )
        exact_state = _exact_completed_state(persisted_state)
        if (
            canonical_json_bytes(persisted_state)
            != canonical_json_bytes(state.to_dict())
            or canonical_json_bytes(persisted_state)
            != canonical_json_bytes(exact_state.to_dict())
            or state.schema_version != "fapo-evaluation-asset-state-v2"
            or state.status != "running"
            or state.error is not None
            or state.current_stage not in {None, "dataset_splits"}
            or any(
                item.status != "completed" or not item.receipt_sha256
                for item in state.stages
            )
        ):
            raise ValueError("completed handoff lifecycle is invalid")
        raw_config = parse_strict_json_object(
            _local_authority_bytes(layout, layout.config_path)
        )
        config = _exact_evaluation_asset_config(raw_config)
        if (
            config.tenant_id != layout.tenant_id
            or config.asset_id != layout.asset_id
        ):
            raise ValueError("completed handoff configuration is invalid")
        receipts = verify_receipt_chain(layout, state)
        if {receipt.get("origin") for receipt in receipts.values()} != {"native"}:
            raise ValueError("completed handoff receipt origin is invalid")
        config_hashes = _replay_config_history(
            layout,
            config,
            state,
            allow_pre_wal_history=False,
        )
        _verify_receipt_config_history(layout, receipts, config_hashes, config)
        provenance = parse_strict_json_object(
            _local_authority_bytes(layout, layout.build_provenance_path)
        )
        build_profile = historical_build_provenance_profile(provenance)
        validate_build_provenance_call_ledgers(
            provenance,
            {
                stage_value: _read_jsonl_objects(
                    layout,
                    layout.artifact_path(
                        _HISTORICAL_STAGE_BY_VALUE_V1[stage_value],
                        "provider_calls.jsonl",
                    ),
                )
                for stage_value in historical_provider_call_stages(build_profile)
            },
            profile=build_profile,
        )
        _verify_build_provenance_authority_links(
            layout,
            provenance,
            receipts,
            config,
        )
        for stage in _HISTORICAL_PIPELINE_STAGES_V1:
            _validate_stage_provenance_evidence(
                layout,
                stage,
                receipts[stage],
                config,
                release_provenance=provenance,
                historical_evidence=True,
            )
        workspace_generation_manifest = parse_strict_json_object(
            _local_authority_bytes(
                layout,
                layout.artifact_path(
                    _HISTORICAL_PIPELINE_STAGES_V1[-1],
                    "generation_manifest.json",
                ),
            )
        )
        generation_id = workspace_generation_manifest.get("generation_id")
        if not isinstance(generation_id, str):
            raise ValueError("completed handoff generation identity is invalid")
        generation = validate_historical_generation(
            layout.generations_root / generation_id,
            expected_tenant_id=layout.tenant_id,
            expected_asset_id=layout.asset_id,
            trusted_root=layout.tenant_root,
        )
        _verify_generation_content_links(layout, provenance, generation)
        return generation
    except (
        EvaluationAssetIntegrityError,
        KeyError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "completed release candidate evidence is invalid; restore it from a "
            "verified backup or rebuild a new asset version",
        ) from exc


def load_completed_release_handoff_control(
    layout: Any,
) -> tuple[PipelineState, EvaluationAssetConfig] | None:
    """Load an exact native handoff before coercive models or provider setup.

    A failed state with a retained receipt chain is an established mutable
    checkpoint shape.  It is validated here, but deliberately returned to the
    ordinary dependency-invalidation path instead of being treated as an
    immutable historical handoff.
    """
    try:
        _validate_local_authority_layout(layout)
        raw_state = parse_strict_json_object(
            _local_authority_bytes(layout, layout.state_path)
        )
        if _is_exact_legacy_completed_sentinel(layout, raw_state):
            return None
        if raw_state.get("schema_version") != STATE_SCHEMA_VERSION:
            if _has_native_authority_evidence(layout, raw_state):
                raise ValueError(
                    "non-v2 state retains native receipt or publication authority"
                )
            return None
        if raw_state.get("status") == "released":
            _exact_v2_state(raw_state)
            raw_config = parse_strict_json_object(
                _local_authority_bytes(layout, layout.config_path)
            )
            config = _exact_evaluation_asset_config(raw_config)
            if (
                config.tenant_id != layout.tenant_id
                or config.asset_id != layout.asset_id
            ):
                raise ValueError("released configuration identity is invalid")
            return None
        raw_stages = raw_state.get("stages")
        raw_counts = raw_state.get("counts")
        complete_counts = isinstance(raw_counts, dict) and (
            _COMPLETED_COUNT_FIELDS <= set(raw_counts)
        )
        regular_stage_inventory = (
            isinstance(raw_stages, list)
            and len(raw_stages) == len(_HISTORICAL_PIPELINE_STAGES_V1)
            and all(isinstance(stage, dict) for stage in raw_stages)
        )
        frozen_stage_inventory = regular_stage_inventory and [
            stage.get("stage") for stage in raw_stages
        ] == list(PERSISTED_STAGE_VALUES_V2)
        all_receipts = regular_stage_inventory and all(
            stage.get("receipt_sha256") is not None for stage in raw_stages
        )
        all_completed = regular_stage_inventory and all(
            stage.get("status") == "completed" for stage in raw_stages
        )
        eligible_handoff_lifecycle = (
            raw_state.get("status") == "running"
            and raw_state.get("error") is None
            and raw_state.get("current_stage") in {None, "dataset_splits"}
        )
        if not eligible_handoff_lifecycle:
            if (
                raw_state.get("status") == "running"
                and frozen_stage_inventory
                and (complete_counts or all_receipts or all_completed)
            ):
                raise ValueError("completed handoff lifecycle is invalid")
            if isinstance(raw_stages, list) and any(
                isinstance(stage, Mapping)
                and stage.get("receipt_sha256") is not None
                for stage in raw_stages
            ):
                raw_config = parse_strict_json_object(
                    _local_authority_bytes(layout, layout.config_path)
                )
                config = _exact_evaluation_asset_config(raw_config)
                if (
                    config.tenant_id != layout.tenant_id
                    or config.asset_id != layout.asset_id
                ):
                    raise ValueError(
                        "receipted checkpoint configuration is invalid"
                    )
            _exact_v2_state(raw_state, historical=False)
            return None
        if not frozen_stage_inventory or (
            not complete_counts and not all_receipts and not all_completed
        ):
            _exact_v2_state(raw_state, historical=False)
            return None
        _exact_v2_state(raw_state)
        state = _exact_completed_state(raw_state)
        if state.tenant_id != layout.tenant_id or state.asset_id != layout.asset_id:
            raise ValueError("completed handoff state identity is invalid")
        raw_config = parse_strict_json_object(
            _local_authority_bytes(layout, layout.config_path)
        )
        config = _exact_evaluation_asset_config(raw_config)
        if (
            config.tenant_id != layout.tenant_id
            or config.asset_id != layout.asset_id
        ):
            raise ValueError("completed handoff configuration is invalid")
        if (
            state.status != "running"
            or state.error is not None
            or state.current_stage
            not in {None, "dataset_splits"}
        ):
            raise ValueError("completed handoff lifecycle is invalid")
        return state, config
    except (
        KeyError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "completed release candidate control is invalid; restore it from a "
            "verified backup or rebuild a new asset version",
        ) from exc


def _is_exact_legacy_completed_sentinel(
    layout: Any,
    raw_state: Mapping[str, Any],
) -> bool:
    """Recognize only the receipt-free pre-v2 adoption checkpoint."""
    expected_state_fields = {
        "tenant_id",
        "asset_id",
        "status",
        "current_stage",
        "created_at",
        "updated_at",
        "error",
        "counts",
        "stages",
    }
    expected_stage_fields = {
        "stage",
        "label",
        "status",
        "message",
        "started_at",
        "completed_at",
    }
    actual_state_fields = set(raw_state)
    exact_state_fields = actual_state_fields == expected_state_fields or (
        actual_state_fields == expected_state_fields | {"schema_version"}
        and raw_state.get("schema_version") == LEGACY_STATE_SCHEMA_VERSION
    )
    stages = raw_state.get("stages")
    if (
        not exact_state_fields
        or raw_state.get("status") != "completed"
        or not isinstance(stages, list)
        or len(stages) != len(_HISTORICAL_PIPELINE_STAGES_V1)
        or any(
            not isinstance(stage, Mapping) or set(stage) != expected_stage_fields
            for stage in stages
        )
    ):
        return False
    try:
        normalized_legacy_completed_state_v1(raw_state)
    except (KeyError, TypeError, ValueError):
        return False
    native_authority_paths = [
        *(layout.receipt_path(stage) for stage in _HISTORICAL_PIPELINE_STAGES_V1),
        *(
            layout.stage_provenance_path(stage)
            for stage in _HISTORICAL_PIPELINE_STAGES_V1
        ),
        *(
            layout.artifact_path(
                _HISTORICAL_STAGE_BY_VALUE_V1[stage_value],
                "provider_calls.jsonl",
            )
            for stage_value in historical_provider_call_stages(
                HISTORICAL_PROVENANCE_PROFILE_V1
            )
        ),
        layout.build_provenance_path,
        layout.recovery_journal_path,
        layout.release_pointer_path,
        layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[-1],
            "generation_manifest.json",
        ),
        layout.generations_root,
    ]
    if any(
        _local_authority_node_exists(layout, path)
        for path in native_authority_paths
    ):
        return False
    try:
        events = read_strict_jsonl_objects(
            layout.events_path,
            trusted_root=layout.tenants_root,
        )
    except (OSError, TypeError, UnicodeError, ValueError):
        return False
    return all(
        is_exact_legacy_event_row_v1(
            row,
            tenant_id=layout.tenant_id,
            asset_id=layout.asset_id,
        )
        for row in events
    )


def _has_native_authority_evidence(
    layout: Any,
    raw_state: Mapping[str, Any],
) -> bool:
    """Detect native receipt/publication evidence before legacy fallback."""
    raw_stages = raw_state.get("stages")
    if isinstance(raw_stages, list) and any(
        isinstance(stage, Mapping) and stage.get("receipt_sha256") is not None
        for stage in raw_stages
    ):
        return True

    native_paths = [
        *(layout.receipt_path(stage) for stage in _HISTORICAL_PIPELINE_STAGES_V1),
        *(
            layout.stage_provenance_path(stage)
            for stage in _HISTORICAL_PIPELINE_STAGES_V1
        ),
        *(
            layout.artifact_path(
                _HISTORICAL_STAGE_BY_VALUE_V1[stage_value],
                "provider_calls.jsonl",
            )
            for stage_value in historical_provider_call_stages(
                HISTORICAL_PROVENANCE_PROFILE_V1
            )
        ),
        layout.build_provenance_path,
        layout.recovery_journal_path,
        layout.release_pointer_path,
        layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[-1],
            "generation_manifest.json",
        ),
        layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[-1],
            "dataset_manifest.json",
        ),
        layout.manifest_path,
    ]
    if any(_local_authority_node_exists(layout, path) for path in native_paths):
        return True
    if _local_authority_node_exists(layout, layout.generations_root):
        return True

    return _has_native_config_history_authority(
        layout
    ) or _has_native_event_authority(layout)


def _has_native_config_history_authority(layout: Any) -> bool:
    """Reject any history row outside the exact pre-v2 writer profiles."""
    try:
        authority = resolve_local_authority_file(
            layout.config_history_path,
            layout.tenants_root,
            access="read_optional",
        )
        if not authority.exists:
            return False
        if authority.data is None:
            return True
        rows = parse_strict_jsonl_objects(authority.data)
    except (OSError, TypeError, UnicodeError, ValueError):
        return True
    if not rows:
        return True
    legacy_update_fields = _UPDATED_HISTORY_FIELDS - {"operation_id"}
    replayed: dict[str, Any] | None = None
    previous_timestamp: datetime | None = None
    for index, row in enumerate(rows, start=1):
        event = row.get("event")
        if event in {"configuration_created", "configuration_inherited"}:
            expected = (
                _INHERITED_HISTORY_FIELDS
                if event == "configuration_inherited"
                else _CREATED_HISTORY_FIELDS
            )
            revision = row.get("revision")
            if (
                index != 1
                or set(row) != expected
                or not _is_json_integer(revision)
                or revision != 1
                or not _canonical_utc_timestamp(row.get("timestamp"))
            ):
                return True
            try:
                configuration = _exact_pre_v2_config_mapping(
                    layout,
                    row.get("configuration"),
                )
            except (TypeError, ValueError):
                return True
            if event == "configuration_inherited":
                parent_asset_id = row.get("parent_asset_id")
                if (
                    not isinstance(parent_asset_id, str)
                    or _LEGACY_SAFE_ASSET_ID_V1.fullmatch(parent_asset_id)
                    is None
                    or parent_asset_id == layout.asset_id
                ):
                    return True
            replayed = configuration
            previous_timestamp = datetime.fromisoformat(str(row["timestamp"]))
            continue
        changes = row.get("changed_fields")
        timestamp = row.get("timestamp")
        revision = row.get("revision")
        if (
            event != "configuration_updated"
            or set(row) != legacy_update_fields
            or not _is_json_integer(revision)
            or revision != index
            or index < 2
            or replayed is None
            or previous_timestamp is None
            or not _canonical_utc_timestamp(timestamp)
            or not isinstance(changes, Mapping)
            or not changes
        ):
            return True
        parsed_timestamp = datetime.fromisoformat(str(timestamp))
        if parsed_timestamp < previous_timestamp:
            return True
        previous_timestamp = parsed_timestamp
        updated = dict(replayed)
        for field, change in changes.items():
            if (
                field not in PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2
                or field not in updated
                or not isinstance(change, Mapping)
                or set(change) != {"previous", "new"}
                or not _is_exact_pre_v2_config_value(
                    str(field),
                    change.get("previous"),
                )
                or not _is_exact_pre_v2_config_value(
                    str(field),
                    change.get("new"),
                )
                or canonical_json_bytes(change.get("previous"))
                != canonical_json_bytes(updated[field])
                or canonical_json_bytes(change.get("new"))
                == canonical_json_bytes(updated[field])
            ):
                return True
            updated[field] = change["new"]
        try:
            replayed = _exact_pre_v2_config_mapping(layout, updated)
        except (TypeError, ValueError):
            return True
        earliest = min(
            (
                PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2[field]
                for field in changes
            ),
            key=PERSISTED_STAGE_VALUES_V2.index,
        )
        if (
            row.get("invalidated_from_stage") != earliest
            or row.get("resume_from_stage") != earliest
        ):
            return True
    try:
        config_authority = resolve_local_authority_file(
            layout.config_path,
            layout.tenants_root,
            access="read",
        )
        if config_authority.data is None:
            return True
        raw_config = parse_strict_json_object(config_authority.data)
        current = _exact_pre_v2_config_mapping(layout, raw_config)
    except (OSError, TypeError, UnicodeError, ValueError):
        return True
    if canonical_json_bytes(current) != canonical_json_bytes(replayed):
        return True
    return False


def _has_native_event_authority(layout: Any) -> bool:
    """Return whether event authority is malformed or not exactly pre-v2."""
    try:
        events = read_strict_jsonl_objects(
            layout.events_path,
            trusted_root=layout.tenants_root,
        )
    except (OSError, TypeError, UnicodeError, ValueError):
        return True
    return any(
        not is_exact_legacy_event_row_v1(
            row,
            tenant_id=layout.tenant_id,
            asset_id=layout.asset_id,
        )
        for row in events
    )


def _capture_release_authority(
    layout: Any,
) -> tuple[
    dict[Path, bytes],
    tuple[tuple[tuple[str, str, int, int], ...], ...],
]:
    """Capture all asset and publication authority for one verification pass."""
    asset_files, asset_records = capture_local_authority_tree(
        layout.root,
        layout.tenants_root,
    )
    publication_files, publication_records = capture_local_authority_tree(
        layout.published_datasets,
        layout.tenant_root,
    )
    overlap = set(asset_files) & set(publication_files)
    if overlap:
        raise ValueError("release authority roots overlap")
    return (
        {**asset_files, **publication_files},
        (asset_records, publication_records),
    )


def _verify_release_evidence(
    layout: Any,
    state: PipelineState,
    *,
    require_persisted_state: bool,
    candidate_receipts: Mapping[PipelineStage, Mapping[str, Any]] | None,
    candidate_release_pointer: Mapping[str, Any] | None = None,
) -> None:
    try:
        authority_snapshot, authority_records = _capture_release_authority(layout)
    except (OSError, TypeError, ValueError) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released control evidence is invalid",
        ) from exc
    snapshot_token = _RELEASE_AUTHORITY_SNAPSHOT.set(authority_snapshot)
    try:
        try:
            _validate_local_authority_layout(layout)
            config = _validate_released_control_state(
                layout,
                state,
                require_persisted_state=require_persisted_state,
            )
            journal_entries = _read_jsonl_objects(
                layout,
                layout.recovery_journal_path,
            )
            journal = validate_recovery_journal(
                layout,
                journal_entries,
                artifact_overrides=authority_snapshot,
            )
            verified_receipts = (
                _verify_candidate_receipts(layout, state, candidate_receipts)
                if candidate_receipts is not None
                else verify_receipt_chain(layout, state)
            )
            legacy_adoption = _legacy_receipt_authority(
                journal,
                verified_receipts,
            )
            config_hashes = _replay_config_history(
                layout,
                config,
                state,
                allow_pre_wal_history=legacy_adoption is not None,
            )
            _verify_receipt_config_history(
                layout,
                verified_receipts,
                config_hashes,
                config,
            )
            _verify_release_publication_links(
                layout,
                state,
                verified_receipts,
                journal,
                config,
                candidate_release_pointer=candidate_release_pointer,
            )
            current_snapshot, current_records = _capture_release_authority(layout)
            if (
                current_snapshot != authority_snapshot
                or current_records != authority_records
            ):
                raise EvaluationAssetIntegrityError(
                    layout.tenant_id,
                    layout.asset_id,
                    "release authority changed during verification",
                )
        except EvaluationAssetIntegrityError:
            raise
        except (
            EvaluationAssetLegacyError,
            KeyError,
            OSError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as exc:
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "released control evidence is invalid",
            ) from exc
    finally:
        _RELEASE_AUTHORITY_SNAPSHOT.reset(snapshot_token)


def _verify_prospective_legacy_adoption_candidate(
    layout: Any,
    state: PipelineState,
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
    *,
    legacy_state: PipelineState | None = None,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    artifact_path_overrides: Mapping[tuple[str, str], Path] | None = None,
) -> None:
    """Verify prospective adoption against its one closed authority mapping."""
    token = _RELEASE_AUTHORITY_SNAPSHOT.set(artifact_overrides)
    try:
        _verify_prospective_legacy_adoption_candidate_from_snapshot(
            layout,
            state,
            receipts,
            legacy_state=legacy_state,
            artifact_overrides=artifact_overrides,
            artifact_path_overrides=artifact_path_overrides,
        )
    finally:
        _RELEASE_AUTHORITY_SNAPSHOT.reset(token)


def _verify_prospective_legacy_adoption_candidate_from_snapshot(
    layout: Any,
    state: PipelineState,
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
    *,
    legacy_state: PipelineState | None = None,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    artifact_path_overrides: Mapping[tuple[str, str], Path] | None = None,
) -> None:
    """Verify one internal pre-WAL adoption target without public compatibility."""
    _validate_local_authority_layout(layout)
    source_state = legacy_state or layout.load_state()
    config = _exact_evaluation_asset_config(
        parse_strict_json_object(_local_authority_bytes(layout, layout.config_path))
    )
    if not source_state.legacy_completed:
        raise ValueError("prospective adoption source is not a legacy completion")
    counts = {
        key: value
        for stage in _HISTORICAL_PIPELINE_STAGES_V1
        for key, value in dict(receipts[stage].get("counts") or {}).items()
    }
    if state.counts != counts:
        raise ValueError("prospective adoption counts are inconsistent")
    _validate_released_control_state(
        layout,
        state,
        require_persisted_state=False,
    )
    verified_receipts = _verify_candidate_receipts(
        layout,
        state,
        receipts,
        artifact_overrides=artifact_overrides,
        artifact_path_overrides=artifact_path_overrides,
    )
    if any(
        receipt.get("origin") != "legacy_adoption"
        for receipt in verified_receipts.values()
    ):
        raise ValueError("prospective adoption receipt origin is invalid")
    config_hashes = _replay_config_history(
        layout,
        config,
        state,
        allow_pre_wal_history=True,
        artifact_overrides=artifact_overrides,
    )
    _verify_receipt_config_history(layout, verified_receipts, config_hashes, config)


def _legacy_receipt_authority(
    journal: ValidatedRecoveryJournal,
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    origins = {receipt.get("origin") for receipt in receipts.values()}
    if origins == {"native"}:
        return None
    if origins != {"legacy_adoption"}:
        raise ValueError("release receipt origins are inconsistent")
    receipt_hashes = {
        stage.value: persisted_json_sha256(receipts[stage])
        for stage in _HISTORICAL_PIPELINE_STAGES_V1
    }
    if not journal.prepared:
        raise ValueError("legacy receipt authority lacks a matching adoption")
    adoption = journal.prepared[-1]
    operation_id = str(adoption.get("operation_id") or "")
    outstanding_operation = (
        str(journal.outstanding.get("operation_id") or "")
        if journal.outstanding is not None
        else None
    )
    operation_is_authorized = (
        operation_id in journal.committed_operation_ids
        or operation_id == outstanding_operation
    )
    if (
        adoption.get("kind") != "legacy_adoption"
        or not operation_is_authorized
        or not isinstance(adoption.get("target"), Mapping)
        or adoption["target"].get("receipt_sha256") != receipt_hashes
    ):
        raise ValueError("legacy receipt authority lacks a matching adoption")
    return adoption


def _verify_release_publication_links(
    layout: Any,
    state: PipelineState,
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
    journal: ValidatedRecoveryJournal,
    config: EvaluationAssetConfig,
    *,
    candidate_release_pointer: Mapping[str, Any] | None = None,
) -> None:
    """Verify the one-way pointer, generation, provenance, receipt authority DAG."""
    if not journal.prepared:
        raise ValueError("released asset lacks terminal publication authority")
    terminal = journal.prepared[-1]
    if (
        terminal.get("operation_id") != state.last_operation_id
        or terminal.get("kind") not in {"release_publication", "legacy_adoption"}
    ):
        raise ValueError("released state does not match terminal publication authority")
    final_stage = _HISTORICAL_PIPELINE_STAGES_V1[-1]
    stage_eight_path = layout.receipt_path(final_stage)
    stage_eight_sha256 = _local_authority_sha256(layout, stage_eight_path)
    resolver = (
        validate_evaluation_asset_release_candidate
        if candidate_release_pointer is not None
        else resolve_evaluation_asset_release
    )
    resolver_args = (
        (layout.published_datasets, candidate_release_pointer)
        if candidate_release_pointer is not None
        else (layout.published_datasets,)
    )
    snapshot = resolver(
        *resolver_args,
        expected_tenant_id=layout.tenant_id,
        expected_asset_id=layout.asset_id,
        expected_stage_8_receipt_sha256=stage_eight_sha256,
        trusted_root=layout.tenant_root,
    )
    if persisted_json_sha256(receipts[final_stage]) != (
        snapshot.stage_8_receipt_sha256
    ):
        raise ValueError("release pointer does not match Stage 8 receipt authority")
    if _local_authority_sha256(
        layout,
        layout.build_provenance_path,
    ) != snapshot.build_provenance_sha256:
        raise ValueError("release pointer does not match build provenance")
    provenance = _read_json_object(layout, layout.build_provenance_path)
    build_profile = historical_build_provenance_profile(provenance)
    if {receipt.get("origin") for receipt in receipts.values()} == {"native"}:
        validate_build_provenance_call_ledgers(
            provenance,
            {
                stage_value: _read_jsonl_objects(
                    layout,
                    layout.artifact_path(
                        _HISTORICAL_STAGE_BY_VALUE_V1[stage_value],
                        "provider_calls.jsonl",
                    ),
                )
                for stage_value in historical_provider_call_stages(build_profile)
            },
            profile=build_profile,
        )
    else:
        validate_build_provenance(provenance, profile=build_profile)
    _verify_build_provenance_authority_links(
        layout,
        provenance,
        receipts,
        config,
    )
    for stage in _HISTORICAL_PIPELINE_STAGES_V1:
        _validate_stage_provenance_evidence(
            layout,
            stage,
            receipts[stage],
            config,
            release_provenance=provenance,
            historical_evidence=True,
        )
    _verify_generation_content_links(layout, provenance, snapshot)


def _validated_input_row_count(
    layout: Any,
    path: Path,
    *,
    labeled: bool,
) -> tuple[int, bytes]:
    """Validate/count one input from the same bound authority bytes."""
    rows: list[dict[str, Any]] = []
    row_numbers: list[int] = []
    raw = _local_authority_bytes(layout, path)
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line.strip():
            continue
        rows.append(parse_strict_json_object(raw_line))
        row_numbers.append(line_number)
    validate_input_records(
        rows,
        labeled=labeled,
        path=path,
        row_numbers=row_numbers,
    )
    return len(rows), raw


def _verify_build_provenance_authority_links(
    layout: Any,
    provenance: Mapping[str, Any],
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
    config: EvaluationAssetConfig,
) -> None:
    """Bind build claims to receipt-authenticated local release authority."""
    identity = provenance.get("identity")
    audit = provenance.get("audit")
    if not isinstance(identity, Mapping) or not isinstance(audit, Mapping):
        raise ValueError("build provenance authority is invalid")
    expected_config = config.to_dict()
    expected_config_sha256 = canonical_sha256(expected_config)
    resolved = identity.get("resolved_configuration")
    stage_eight = receipts.get(_HISTORICAL_PIPELINE_STAGES_V1[-1])
    if (
        not isinstance(resolved, Mapping)
        or canonical_json_bytes(resolved.get("values"))
        != canonical_json_bytes(expected_config)
        or resolved.get("sha256") != expected_config_sha256
        or not isinstance(stage_eight, Mapping)
        or stage_eight.get("resolved_config_sha256")
        != expected_config_sha256
    ):
        raise ValueError("build provenance configuration differs from authority")

    input_manifest = _read_json_object(
        layout,
        layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[0],
            "input_manifest.json",
        )
    )
    manifest_inputs = input_manifest.get("inputs")
    expected_inputs: dict[str, dict[str, Any]] = {}
    if not isinstance(manifest_inputs, Mapping) or set(manifest_inputs) != {
        "labeled_feedback",
        "unlabeled",
    }:
        raise ValueError("build provenance inputs differ from authority")
    for name, path in (
        ("labeled_feedback", layout.historical_feedback_path),
        ("unlabeled", layout.historical_unlabeled_path),
    ):
        details = manifest_inputs.get(name)
        if not isinstance(details, Mapping) or set(details) != {
            "file",
            "rows",
            "sha256",
        }:
            raise ValueError("build provenance inputs differ from authority")
        actual_rows, input_bytes = _validated_input_row_count(
            layout,
            path,
            labeled=name == "labeled_feedback",
        )
        expected_inputs[name] = {
            "path": path.relative_to(layout.root).as_posix(),
            "bytes": len(input_bytes),
            "rows": actual_rows,
            "sha256": hashlib.sha256(input_bytes).hexdigest(),
        }
        if details.get("file") != path.name or details.get(
            "sha256"
        ) != expected_inputs[name]["sha256"] or canonical_json_bytes(
            details.get("rows")
        ) != canonical_json_bytes(actual_rows):
            raise ValueError("build provenance inputs differ from authority")
    raw_receipt = receipts.get(_HISTORICAL_PIPELINE_STAGES_V1[0])
    expected_stage_counts = {
        "feedback_records": expected_inputs["labeled_feedback"]["rows"],
        "unlabeled_records": expected_inputs["unlabeled"]["rows"],
    }
    if not isinstance(raw_receipt, Mapping) or canonical_json_bytes(
        raw_receipt.get("counts")
    ) != canonical_json_bytes(expected_stage_counts):
        raise ValueError("build provenance inputs differ from authority")
    if canonical_json_bytes(identity.get("inputs")) != canonical_json_bytes(
        expected_inputs
    ):
        raise ValueError("build provenance inputs differ from authority")

    release_snapshot = _RELEASE_AUTHORITY_SNAPSHOT.get()
    if release_snapshot is not None:
        has_lineage = layout.lineage_path.absolute() in release_snapshot
        has_reuse = layout.reuse_manifest_path.absolute() in release_snapshot
    else:
        if layout.lineage_path.is_symlink() or layout.reuse_manifest_path.is_symlink():
            raise ValueError("build provenance lineage differs from authority")
        has_lineage = layout.lineage_path.is_file()
        has_reuse = layout.reuse_manifest_path.is_file()
    if not has_lineage:
        if has_reuse or (
            release_snapshot is None
            and any(
                path.exists() or path.is_symlink()
                for path in (layout.lineage_path, layout.reuse_manifest_path)
            )
        ):
            raise ValueError("build provenance lineage differs from authority")
        return
    evidence = validate_extension_evidence(
        layout,
        require_asset_manifest=True,
        historical=True,
        artifact_overrides=release_snapshot,
    )
    lineage = evidence.lineage
    expected_lineage = {
        key: lineage[key]
        for key in (
            "parent_asset_id",
            "clustering_mode",
            "added_labeled_record_ids",
            "added_unlabeled_record_ids",
            "parent_input_counts",
            "extended_input_counts",
        )
    }
    expected_lineage["parent_generation_id"] = lineage["parent_release"][
        "generation_id"
    ]
    legacy = identity.get("source") == LEGACY_UNAVAILABLE_PROVENANCE
    if not legacy:
        dependencies = {
            "lineage_sha256": _local_authority_sha256(
                layout,
                layout.lineage_path,
            ),
            "reuse_manifest_sha256": _local_authority_sha256(
                layout,
                layout.reuse_manifest_path,
            ),
            "parent_release": lineage["parent_release"],
        }
        expected_lineage["file_dependencies"] = dependencies
        if canonical_json_bytes(audit.get("lineage_files")) != canonical_json_bytes(
            dependencies
        ):
            raise ValueError("build provenance lineage differs from authority")
    if canonical_json_bytes(identity.get("lineage")) != canonical_json_bytes(
        expected_lineage
    ):
        raise ValueError("build provenance lineage differs from authority")


def _verify_generation_content_links(
    layout: Any,
    provenance: Mapping[str, Any],
    generation: Any,
) -> None:
    """Verify immutable generation, workspace, and manifest cross-links."""
    if provenance["identity_sha256"] != generation.descriptor["build_fingerprint"]:
        raise ValueError("release build fingerprint is inconsistent")
    workspace_generation_manifest = layout.artifact_path(
        _HISTORICAL_PIPELINE_STAGES_V1[-1],
        "generation_manifest.json",
    )
    if (
        _local_authority_sha256(layout, workspace_generation_manifest)
        != generation.generation_manifest_sha256
    ):
        raise ValueError("workspace generation manifest is inconsistent")
    for split in LOGICAL_SPLITS:
        workspace_split = layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[-1],
            f"{split}.jsonl",
        )
        if _local_authority_sha256(
            layout,
            workspace_split,
        ) != _local_authority_sha256(layout, generation.files[split]):
            raise ValueError("workspace and immutable generation splits differ")
    dataset_manifest = _read_json_object(
        layout,
        layout.artifact_path(
            _HISTORICAL_PIPELINE_STAGES_V1[-1],
            "dataset_manifest.json",
        )
    )
    asset_manifest = _read_json_object(layout, layout.manifest_path)
    if dataset_manifest != asset_manifest:
        raise ValueError("asset manifests differ")
    generation_directory = generation.generation_dir.relative_to(
        layout.tenants_root.parent
    ).as_posix()
    expected_published = {
        "directory": layout.published_datasets.relative_to(
            layout.tenant_root
        ).as_posix(),
        "release_pointer": layout.release_pointer_path.relative_to(
            layout.tenant_root
        ).as_posix(),
        "generation_id": generation.generation_id,
        "generation_manifest_sha256": generation.generation_manifest_sha256,
        "build_provenance_sha256": _local_authority_sha256(
            layout,
            layout.build_provenance_path,
        ),
        "build_fingerprint": generation.descriptor["build_fingerprint"],
        "files": {
            split: f"{generation_directory}/{split}.jsonl"
            for split in LOGICAL_SPLITS
        },
    }
    if dataset_manifest.get("published_datasets") != expected_published:
        raise ValueError("published dataset manifest is inconsistent")


def released_parent_evidence(
    layout: Any,
    state: PipelineState,
) -> dict[str, str]:
    """Verify a parent release and return portable source-lineage identities."""
    verify_released_asset(layout, state)
    lineage_payload: dict[str, Any] = {
        "input_manifest_sha256": _local_authority_sha256(
            layout,
            layout.artifact_path(
                _HISTORICAL_PIPELINE_STAGES_V1[0],
                "input_manifest.json",
            )
        ),
        "raw_receipt_sha256": _local_authority_sha256(
            layout,
            layout.receipt_path(_HISTORICAL_PIPELINE_STAGES_V1[0])
        ),
        "lineage_sha256": None,
        "reuse_manifest_sha256": None,
    }
    if layout.lineage_path.is_file():
        lineage, reuse = _verify_extension_lineage(layout)
        lineage_payload["lineage_sha256"] = canonical_sha256(lineage)
        lineage_payload["reuse_manifest_sha256"] = canonical_sha256(reuse)
    elif layout.reuse_manifest_path.exists():
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "source lineage metadata is inconsistent",
        )
    snapshot = resolve_evaluation_asset_release(
        layout.published_datasets,
        expected_tenant_id=layout.tenant_id,
        expected_asset_id=layout.asset_id,
        trusted_root=layout.tenant_root,
    )
    return {
        "stage_8_receipt_sha256": _local_authority_sha256(
            layout,
            layout.receipt_path(_HISTORICAL_PIPELINE_STAGES_V1[-1])
        ),
        "released_state_sha256": _local_authority_sha256(
            layout,
            layout.state_path,
        ),
        "source_lineage_sha256": canonical_sha256(lineage_payload),
        "release_pointer_sha256": snapshot.pointer_sha256,
        "generation_id": snapshot.generation_id,
        "generation_manifest_sha256": snapshot.generation_manifest_sha256,
        "build_provenance_sha256": snapshot.build_provenance_sha256,
        "build_fingerprint": snapshot.build_fingerprint,
    }


def verify_receipt_chain(
    layout: Any,
    state: PipelineState,
) -> dict[PipelineStage, dict[str, Any]]:
    """Verify all historical receipts without comparing the current checkout."""
    config = layout.load_config()
    receipts: dict[PipelineStage, dict[str, Any]] = {}
    for stage in _HISTORICAL_PIPELINE_STAGES_V1:
        receipts[stage] = verify_stage_receipt(
            layout,
            state,
            stage,
            config,
            prompt_values={},
            compare_current_dependencies=False,
        )
    return receipts


def mutable_rebuild_boundary(
    layout: Any,
    state: PipelineState,
    config: EvaluationAssetConfig,
    prompt_values_by_stage: Mapping[PipelineStage, Mapping[str, str]],
    provider_identities_by_stage: Mapping[
        PipelineStage,
        Mapping[str, Any],
    ] | None = None,
) -> PipelineStage | None:
    """Return the first incomplete or invalid mutable checkpoint boundary."""
    verify_raw_snapshot_floor(layout, state)
    for stage in PipelineStage:
        stage_state = _stage_state(state, stage)
        if stage_state.status != "completed" or not stage_state.receipt_sha256:
            return stage
        try:
            verify_stage_receipt(
                layout,
                state,
                stage,
                config,
                prompt_values=prompt_values_by_stage.get(stage, {}),
                provider_identity=(provider_identities_by_stage or {}).get(stage),
                compare_current_dependencies=True,
            )
        except EvaluationAssetIntegrityError:
            return stage
    return None


def _stage_seed_evidence(
    stage: PipelineStage,
    config: EvaluationAssetConfig,
    *,
    call_count: int,
    provider_backed: bool | None = None,
) -> dict[str, Any]:
    if stage.value == "dataset_splits":
        return {"split": config.split_seed}
    if (
        bool(STAGE_SPECIFICATIONS[stage].provider_roles)
        if provider_backed is None
        else provider_backed
    ):
        reason = (
            "provider_does_not_use_sampling"
            if call_count
            else "stage_made_no_provider_calls"
        )
        return {"sampling": not_applicable(reason)}
    return {"sampling": not_applicable("stage_has_no_provider_role")}


def _stage_algorithm_evidence(
    layout: Any,
    stage: PipelineStage,
    config: EvaluationAssetConfig,
    *,
    historical: bool = False,
) -> dict[str, Any]:
    inventory_builder = (
        historical_algorithm_inventory_v1 if historical else build_algorithm_inventory
    )
    inventory = inventory_builder(
        config.to_dict(),
        extension=layout.lineage_path.is_file(),
    )
    return {"stage": stage.value, "revision": inventory[stage.value]}


def _prompt_inventory(prompt_values: Mapping[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "revision": PROMPT_REVISIONS[name],
            "bytes": len(value.encode("utf-8")),
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        }
        for name, value in sorted(prompt_values.items())
    ]


def _read_stage_provenance(
    layout: Any,
    stage: PipelineStage,
    artifact_overrides: Mapping[Path, bytes] | None = None,
) -> dict[str, Any]:
    path = layout.stage_provenance_path(stage)
    raw = (artifact_overrides or {}).get(path)
    if raw is None:
        raw = _local_authority_bytes(layout, path)
    return parse_strict_json_object(raw)


def _require_receipt_stage_profile(
    receipt: Mapping[str, Any],
    stage_profile: str,
) -> None:
    """Require one receipt and stage record to use the same schema generation."""
    expected_schema = {
        HISTORICAL_PROVENANCE_PROFILE_V1: (
            _HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V1
        ),
        HISTORICAL_LEGACY_PROVENANCE_PROFILE_V1: (
            _HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V1
        ),
        HISTORICAL_PROVENANCE_PROFILE_V2: (
            _HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V2
        ),
        HISTORICAL_LEGACY_PROVENANCE_PROFILE_V2: (
            _HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V2
        ),
        "native": STAGE_RECEIPT_SCHEMA_VERSION,
        "legacy": STAGE_RECEIPT_SCHEMA_VERSION,
    }.get(stage_profile)
    if expected_schema is None or receipt.get("schema_version") != expected_schema:
        raise ValueError("receipt and stage provenance profiles differ")


def _validate_stage_provenance_evidence(
    layout: Any,
    stage: PipelineStage,
    receipt: Mapping[str, Any],
    config: EvaluationAssetConfig,
    *,
    prompt_values: Mapping[str, str] | None = None,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    release_provenance: Mapping[str, Any] | None = None,
    historical_evidence: bool = False,
) -> None:
    """Bind one strict stage record to its receipt, ledger, and release facts."""
    payload = _read_stage_provenance(layout, stage, artifact_overrides)
    profile = "legacy" if receipt.get("origin") == "legacy_adoption" else "native"
    if profile == "legacy":
        if historical_evidence or release_provenance is not None:
            profile = historical_legacy_stage_provenance_profile(payload)
        _require_receipt_stage_profile(receipt, profile)
        if release_provenance is not None:
            build_profile = historical_build_provenance_profile(
                release_provenance
            )
            expected_profile = (
                HISTORICAL_LEGACY_PROVENANCE_PROFILE_V1
                if build_profile == HISTORICAL_PROVENANCE_PROFILE_V1
                else HISTORICAL_LEGACY_PROVENANCE_PROFILE_V2
            )
            if profile != expected_profile:
                raise ValueError("stage and build provenance profiles differ")
        validate_stage_provenance(
            payload,
            expected_stage=stage.value,
            profile=profile,
        )
        return

    if historical_evidence or release_provenance is not None:
        profile = historical_stage_provenance_profile(payload)
    _require_receipt_stage_profile(receipt, profile)
    if release_provenance is not None:
        build_profile = historical_build_provenance_profile(release_provenance)
        expected_stage_profile = (
            HISTORICAL_LEGACY_PROVENANCE_PROFILE_V1
            if build_profile == HISTORICAL_PROVENANCE_PROFILE_V1
            else HISTORICAL_LEGACY_PROVENANCE_PROFILE_V2
        ) if receipt.get("origin") == "legacy_adoption" else build_profile
        actual_stage_profile = (
            historical_legacy_stage_provenance_profile(payload)
            if receipt.get("origin") == "legacy_adoption"
            else profile
        )
        if actual_stage_profile != expected_stage_profile:
            raise ValueError("stage and build provenance profiles differ")

    has_provider_role = (
        isinstance(payload.get("calls"), list)
        if profile != "native"
        else bool(STAGE_SPECIFICATIONS[stage].provider_roles)
    )
    calls = (
        _read_jsonl_objects(
            layout,
            layout.artifact_path(stage, "provider_calls.jsonl"),
        )
        if has_provider_role
        else None
    )
    provider_identity: Any = receipt.get("provider_identity")
    source: Any = receipt.get("code")
    expected_prompts = (
        _prompt_inventory(prompt_values)
        if prompt_values is not None
        else None
    )
    if release_provenance is not None:
        identity = release_provenance.get("identity")
        if not isinstance(identity, Mapping):
            raise ValueError("release stage provenance identity is invalid")
        providers = identity.get("providers")
        if has_provider_role:
            if not isinstance(providers, Mapping):
                raise ValueError("release stage provider inventory is invalid")
            persisted_provider_identity = payload.get("provider_identity")
            if not isinstance(persisted_provider_identity, Mapping):
                raise ValueError("release stage provider identity is invalid")
            provider_identity = {
                role: (
                    {
                        field: providers[role][field]
                        for field in ("provider", "model", "source")
                    }
                    if profile == HISTORICAL_PROVENANCE_PROFILE_V1
                    else dict(providers[role])
                )
                for role in persisted_provider_identity
            }
        else:
            provider_identity = {"status": "not_applicable"}
        source = identity.get("source")
        build_prompts = identity.get("prompts")
        if not isinstance(build_prompts, list):
            raise ValueError("release stage prompt inventory is invalid")
        persisted_prompts = payload.get("prompts")
        if not isinstance(persisted_prompts, list):
            raise ValueError("release stage prompt inventory is invalid")
        names = {
            row.get("name")
            for row in persisted_prompts
            if isinstance(row, Mapping)
        }
        expected_prompts = [
            dict(row)
            for row in build_prompts
            if isinstance(row, Mapping) and row.get("name") in names
        ]
        build_algorithms = identity.get("algorithms")
        if not isinstance(build_algorithms, Mapping):
            raise ValueError("release stage algorithm inventory is invalid")
        expected_algorithms = {
            "stage": stage.value,
            "revision": build_algorithms.get(stage.value),
        }
    else:
        expected_algorithms = _stage_algorithm_evidence(
            layout,
            stage,
            config,
            historical=profile != "native",
        )

    if (
        canonical_sha256(receipt.get("provider_identity"))
        != receipt.get("provider_identity_sha256")
        or canonical_sha256(receipt.get("code")) != receipt.get("code_sha256")
    ):
        raise ValueError("stage provenance receipt evidence is inconsistent")
    if release_provenance is not None and (
        canonical_sha256(receipt.get("provider_identity"))
        != canonical_sha256(provider_identity)
        or canonical_sha256(receipt.get("code")) != canonical_sha256(source)
    ):
        raise ValueError("stage receipt facts differ from build provenance")
    validate_stage_provenance(
        payload,
        expected_stage=stage.value,
        profile=profile,
        expected_provider_identity=provider_identity,
        expected_prompt_set_sha256=str(receipt.get("prompt_set_sha256") or ""),
        expected_prompts=expected_prompts,
        expected_calls=calls,
        expected_source=source,
        expected_seeds=_stage_seed_evidence(
            stage,
            config,
            call_count=len(calls or []),
            provider_backed=has_provider_role,
        ),
        expected_algorithms=expected_algorithms,
    )


def verify_stage_receipt(
    layout: Any,
    state: PipelineState,
    stage: PipelineStage,
    config: EvaluationAssetConfig,
    *,
    prompt_values: Mapping[str, str],
    provider_identity: Mapping[str, Any] | None = None,
    compare_current_dependencies: bool,
) -> dict[str, Any]:
    """Verify one receipt, its declared files, and its upstream chain."""
    historical = not compare_current_dependencies
    stage_state = _stage_state(state, stage)
    receipt_path = layout.receipt_path(stage)
    if not stage_state.receipt_sha256:
        raise _integrity(layout, stage, "receipt is missing")
    try:
        receipt_bytes = _local_authority_bytes(layout, receipt_path)
        if hashlib.sha256(receipt_bytes).hexdigest() != stage_state.receipt_sha256:
            raise _integrity(layout, stage, "receipt hash does not match state")
        receipt = parse_strict_json_object(receipt_bytes)
    except (OSError, UnicodeError, ValueError) as exc:
        raise _integrity(layout, stage, "receipt is not valid JSON") from exc
    persisted_receipt_schema = receipt.get("schema_version")
    if historical and persisted_receipt_schema == (
        _HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V1
    ):
        expected_receipt_fields = _HISTORICAL_STAGE_RECEIPT_FIELDS_V1
    elif historical and persisted_receipt_schema == (
        _HISTORICAL_STAGE_RECEIPT_SCHEMA_VERSION_V2
    ):
        expected_receipt_fields = _HISTORICAL_STAGE_RECEIPT_FIELDS_V2
    elif not historical and persisted_receipt_schema == (
        STAGE_RECEIPT_SCHEMA_VERSION
    ):
        expected_receipt_fields = _STAGE_RECEIPT_FIELDS
    else:
        raise _integrity(layout, stage, "receipt schema is unsupported")
    expected_fields = set(expected_receipt_fields)
    if stage.value == "dataset_splits":
        expected_fields.update(
            {
                "config_history_sha256",
                "build_provenance_sha256",
                "generation_manifest_sha256",
            }
        )
        try:
            history_sha256 = _local_authority_sha256(
                layout,
                layout.config_history_path,
            )
        except OSError as exc:
            raise _integrity(
                layout,
                stage,
                "configuration history evidence is missing",
            ) from exc
        if receipt.get("config_history_sha256") != history_sha256:
            raise _integrity(
                layout,
                stage,
                "configuration history evidence changed",
            )
        if receipt.get("build_provenance_sha256") != _local_authority_sha256(
            layout,
            layout.build_provenance_path,
        ) or receipt.get("generation_manifest_sha256") != (
            _local_authority_sha256(
                layout,
                layout.artifact_path(
                    stage,
                    "generation_manifest.json",
                ),
            )
        ):
            raise _integrity(
                layout,
                stage,
                "release provenance evidence changed",
            )
    if set(receipt) != expected_fields:
        raise _integrity(layout, stage, "receipt field inventory is invalid")
    stage_index = receipt.get("stage_index")
    if (
        receipt.get("stage") != stage.value
        or not isinstance(stage_index, int)
        or isinstance(stage_index, bool)
        or stage_index
        != (
            _HISTORICAL_STAGE_INDEX_V1[stage]
            if historical
            else list(PipelineStage).index(stage) + 1
        )
    ):
        raise _integrity(layout, stage, "receipt stage identity is inconsistent")
    if not _canonical_utc_timestamp(receipt.get("completed_at")):
        raise _integrity(layout, stage, "receipt completion timestamp is invalid")
    hash_fields = {
        "resolved_config_sha256",
        "dependency_config_sha256",
        "prompt_set_sha256",
        "provider_identity_sha256",
        "provider_calls_sha256",
        "code_sha256",
    }
    if stage.value == "dataset_splits":
        hash_fields.update(
            {
                "config_history_sha256",
                "build_provenance_sha256",
                "generation_manifest_sha256",
            }
        )
    if any(
        not isinstance(receipt.get(field), str)
        or not _SHA256.fullmatch(receipt[field])
        for field in hash_fields
    ):
        raise _integrity(layout, stage, "receipt hash inventory is invalid")

    specification = (
        _HISTORICAL_STAGE_SPECIFICATIONS_V1[stage]
        if historical
        else STAGE_SPECIFICATIONS[stage]
    )
    artifact_profile = receipt.get("artifact_profile", "native")
    origin = receipt.get("origin")
    if (origin, artifact_profile) not in {
        ("native", "native"),
        ("legacy_adoption", "native"),
        ("legacy_adoption", "legacy"),
    }:
        raise _integrity(layout, stage, "receipt origin or artifact profile is invalid")
    if origin == "legacy_adoption":
        marker_hash = canonical_sha256(LEGACY_UNAVAILABLE_PROVENANCE)
        if state.status != "released" or any(
            (
                receipt.get("prompt_set_sha256") != marker_hash,
                receipt.get("provider_identity")
                != LEGACY_UNAVAILABLE_PROVENANCE,
                receipt.get("provider_identity_sha256") != marker_hash,
                receipt.get("provider_calls_sha256") != marker_hash,
                receipt.get("code") != LEGACY_UNAVAILABLE_PROVENANCE,
                receipt.get("code_sha256") != marker_hash,
            )
        ):
            raise _integrity(
                layout,
                stage,
                "receipt origin or artifact profile is invalid",
            )
    required_outputs, direct_inputs = _declared_artifacts_for_profile(
        specification,
        artifact_profile,
    )
    expected_outputs = _expected_output_locations(
        layout,
        stage,
        specification,
        required_outputs,
        include_native_evidence=True,
        include_provider_calls=receipt.get("origin") != "legacy_adoption",
        historical=historical,
    )
    outputs = receipt.get("outputs")
    if not isinstance(outputs, list) or any(
        not isinstance(item, Mapping)
        or set(item) != {"path", "scope", "sha256", "bytes", "required"}
        for item in outputs
    ):
        raise _integrity(layout, stage, "receipt output inventory is invalid")
    recorded_outputs = {
        (str(item.get("scope")), str(item.get("path")))
        for item in outputs
        if isinstance(item, Mapping) and item.get("required") is True
    }
    if recorded_outputs != expected_outputs or len(outputs) != len(expected_outputs):
        raise _integrity(layout, stage, "required output inventory is incomplete")
    for item in outputs:
        _verify_file_record(layout, stage, item)
    expected_provider_calls_sha256 = (
        _local_authority_sha256(
            layout,
            layout.artifact_path(stage, "provider_calls.jsonl"),
        )
        if specification.provider_roles
        and receipt.get("origin") != "legacy_adoption"
        else canonical_sha256(
            LEGACY_UNAVAILABLE_PROVENANCE
            if receipt.get("origin") == "legacy_adoption"
            else not_applicable("stage_has_no_provider_role")
        )
    )
    if receipt.get("provider_calls_sha256") != expected_provider_calls_sha256:
        raise _integrity(layout, stage, "provider call ledger is inconsistent")
    try:
        _validate_stage_provenance_evidence(
            layout,
            stage,
            receipt,
            config,
            prompt_values=prompt_values if compare_current_dependencies else None,
            historical_evidence=not compare_current_dependencies,
        )
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise _integrity(layout, stage, "stage provenance is invalid") from exc

    inputs = receipt.get("inputs")
    if not isinstance(inputs, list) or any(
        not isinstance(item, Mapping)
        or set(item) != {"path", "scope", "sha256", "bytes"}
        for item in inputs
    ):
        raise _integrity(layout, stage, "receipt input inventory is invalid")
    expected_inputs = {
        (
            "asset",
            layout.artifact_path(input_stage, name)
            .relative_to(layout.root)
            .as_posix(),
        )
        for input_stage, name in direct_inputs
    }
    try:
        expected_inputs.update(
            (
                "asset",
                path.relative_to(layout.root).as_posix(),
            )
            for path in extension_receipt_input_paths(
                layout,
                stage,
                historical=historical,
                artifact_overrides=(
                    _RELEASE_AUTHORITY_SNAPSHOT.get()
                    if historical
                    else None
                ),
            )
        )
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise _integrity(layout, stage, "extension input evidence is inconsistent") from exc
    recorded_inputs = {
        (str(item.get("scope")), str(item.get("path")))
        for item in inputs
        if isinstance(item, Mapping)
    }
    if recorded_inputs != expected_inputs or len(inputs) != len(expected_inputs):
        raise _integrity(layout, stage, "direct input inventory is incomplete")
    for item in inputs:
        _verify_file_record(layout, stage, item)

    upstream = receipt.get("upstream_receipts")
    if not isinstance(upstream, list) or any(
        not isinstance(item, Mapping) or set(item) != {"stage", "sha256"}
        for item in upstream
    ):
        raise _integrity(layout, stage, "upstream receipt inventory is invalid")
    expected_upstream = {
        dependency.value: _local_authority_sha256(
            layout,
            layout.receipt_path(dependency),
        )
        for dependency in specification.upstream_stages
        if layout.receipt_path(dependency).is_file()
    }
    recorded_upstream = {
        str(item.get("stage")): str(item.get("sha256"))
        for item in upstream
        if isinstance(item, Mapping)
    }
    if recorded_upstream != expected_upstream or len(expected_upstream) != len(
        specification.upstream_stages
    ) or len(upstream) != len(expected_upstream):
        raise _integrity(layout, stage, "upstream receipt chain is inconsistent")

    counts = receipt.get("counts")
    expected_count_keys = (
        _HISTORICAL_STAGE_COUNT_KEYS_V1[stage]
        if historical
        else STAGE_COUNT_KEYS[stage]
    )
    if not isinstance(counts, Mapping) or set(counts) != expected_count_keys:
        raise _integrity(layout, stage, "receipt counts are invalid")
    for key in expected_count_keys:
        value = counts.get(key)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or value != state.counts.get(key)
        ):
            raise _integrity(layout, stage, "receipt counts do not match state")

    if compare_current_dependencies:
        expected_dependencies = current_dependency_hashes(
            stage,
            config,
            prompt_values,
            provider_identity,
        )
        if any(
            receipt.get(key) != expected_value
            for key, expected_value in expected_dependencies.items()
        ):
            raise _integrity(layout, stage, "mutable dependencies changed")
    return dict(receipt)


def _validate_released_control_state(
    layout: Any,
    state: PipelineState,
    *,
    require_persisted_state: bool,
) -> EvaluationAssetConfig:
    if state.schema_version != "fapo-evaluation-asset-state-v2" or (
        state.status != "released"
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "the persisted lifecycle is not a v2 release",
        )
    raw_state = state.to_dict()
    if require_persisted_state:
        raw_state = parse_strict_json_object(
            _local_authority_bytes(layout, layout.state_path)
        )
        if canonical_json_bytes(raw_state) != canonical_json_bytes(state.to_dict()):
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "the supplied state does not match persisted authority",
            )
    exact_state = _exact_completed_state(raw_state)
    if canonical_json_bytes(raw_state) != canonical_json_bytes(exact_state.to_dict()):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released state identity is inconsistent",
        )
    if state.tenant_id != layout.tenant_id or state.asset_id != layout.asset_id:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released state identity is inconsistent",
        )
    if state.current_stage is not None or state.error is not None:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released terminal state is inconsistent",
        )
    if not _canonical_utc_timestamp(state.created_at) or not (
        _canonical_utc_timestamp(state.updated_at)
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released timestamps are incomplete",
        )
    expected_stages = [
        stage.value for stage in _HISTORICAL_PIPELINE_STAGES_V1
    ]
    if [stage.stage for stage in state.stages] != expected_stages or any(
        stage.status != "completed" or not stage.receipt_sha256
        for stage in state.stages
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released stage authority is incomplete",
        )
    expected_counts = _HISTORICAL_COMPLETED_COUNT_FIELDS_V1
    if set(state.counts) != expected_counts or any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        for value in state.counts.values()
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released count authority is invalid",
        )
    raw_sequence = raw_state.get("mutation_sequence")
    if (
        not isinstance(raw_sequence, int)
        or isinstance(raw_sequence, bool)
        or raw_sequence < 0
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released mutation identity is invalid",
        )
    raw_config = parse_strict_json_object(
        _local_authority_bytes(layout, layout.config_path)
    )
    config = _exact_evaluation_asset_config(raw_config)
    if (
        config.tenant_id != layout.tenant_id
        or config.asset_id != layout.asset_id
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released configuration identity is inconsistent",
        )
    return config


def _replay_config_history(
    layout: Any,
    current_config: EvaluationAssetConfig,
    state: PipelineState,
    *,
    allow_pre_wal_history: bool,
    artifact_overrides: Mapping[Path, bytes] | None = None,
) -> list[str]:
    rows = _read_jsonl_objects(
        layout,
        layout.config_history_path,
        artifact_overrides,
    )
    if not rows:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "configuration history is missing",
        )
    first = rows[0]
    origin_event = first.get("event")
    expected_origin_fields = (
        _INHERITED_HISTORY_FIELDS
        if origin_event == "configuration_inherited"
        else _CREATED_HISTORY_FIELDS
    )
    if (
        origin_event not in {"configuration_created", "configuration_inherited"}
        or set(first) != expected_origin_fields
        or not isinstance(first.get("revision"), int)
        or isinstance(first.get("revision"), bool)
        or first["revision"] != 1
        or not _canonical_utc_timestamp(first.get("timestamp"))
        or first["timestamp"] != state.created_at
    ):
        raise ValueError("configuration history origin is invalid")
    initial = first.get("configuration")
    if not isinstance(initial, Mapping):
        raise ValueError("configuration history origin is incomplete")
    initial_config = EvaluationAssetConfig.from_dict(initial)
    replayed = initial_config.to_dict()
    if dict(initial) != replayed or (
        initial_config.tenant_id != layout.tenant_id
        or initial_config.asset_id != layout.asset_id
    ):
        raise ValueError("configuration history origin configuration is invalid")
    if origin_event == "configuration_inherited":
        parent_asset_id = first.get("parent_asset_id")
        if not isinstance(parent_asset_id, str) or not parent_asset_id.strip():
            raise ValueError("configuration history parent identity is invalid")
        lineage = _read_json_object(
            layout,
            layout.lineage_path,
            artifact_overrides,
        )
        if lineage.get("parent_asset_id") != parent_asset_id:
            raise ValueError("configuration history parent identity is inconsistent")
    elif (
        layout.lineage_path in artifact_overrides
        if artifact_overrides is not None
        else layout.lineage_path.is_file()
    ):
        raise ValueError("extension configuration history origin is invalid")

    journal_rows = _read_jsonl_objects(
        layout,
        layout.recovery_journal_path,
        artifact_overrides,
        optional=True,
    )
    revision_journal_rows = [
        row
        for row in journal_rows
        if row.get("kind") == "configuration_revision"
    ]
    snapshots = [canonical_sha256(replayed)]
    update_rows: list[Mapping[str, Any]] = []
    previous_timestamp = datetime.fromisoformat(str(first["timestamp"]))
    for revision, row in enumerate(rows[1:], start=2):
        timestamp = row.get("timestamp")
        if (
            set(row) != _UPDATED_HISTORY_FIELDS
            or row.get("event") != "configuration_updated"
            or not isinstance(row.get("revision"), int)
            or isinstance(row.get("revision"), bool)
            or row["revision"] != revision
            or not _canonical_utc_timestamp(timestamp)
        ):
            raise ValueError("configuration history sequence is invalid")
        parsed_timestamp = datetime.fromisoformat(str(timestamp))
        if parsed_timestamp < previous_timestamp:
            raise ValueError("configuration history timestamps are out of order")
        previous_timestamp = parsed_timestamp
        operation_id = row.get("operation_id")
        if not isinstance(operation_id, str) or not _OPERATION_ID.fullmatch(
            operation_id
        ):
            raise ValueError("configuration history operation is invalid")
        changes = row.get("changed_fields")
        if not isinstance(changes, Mapping) or not changes:
            raise ValueError("configuration history changes are invalid")
        updated = dict(replayed)
        for field, change in changes.items():
            if field not in updated or not isinstance(change, Mapping) or set(
                change
            ) != {"previous", "new"}:
                raise ValueError("configuration history change is invalid")
            if change["previous"] != updated[field]:
                raise ValueError("configuration history predecessor is invalid")
            if change["new"] == change["previous"]:
                raise ValueError("configuration history change is empty")
            updated[field] = change["new"]
        replayed = EvaluationAssetConfig.from_dict(updated).to_dict()
        try:
            earliest = min(
                (
                    PERSISTED_CONFIG_STAGE_DEPENDENCIES_V2[field]
                    for field in changes
                ),
                key=PERSISTED_STAGE_VALUES_V2.index,
            )
        except KeyError as exc:
            raise ValueError(
                "configuration history change is invalid"
            ) from exc
        if row.get("invalidated_from_stage") != earliest:
            raise ValueError("configuration history boundary is invalid")
        try:
            _HISTORICAL_STAGE_BY_VALUE_V1[str(row.get("resume_from_stage"))]
        except KeyError as exc:
            raise ValueError("configuration history resume stage is invalid") from exc
        update_rows.append(row)
        snapshots.append(canonical_sha256(replayed))
    if not allow_pre_wal_history:
        if len(revision_journal_rows) != 2 * len(update_rows):
            raise ValueError("configuration history journal authority is invalid")
        for index, history_entry in enumerate(update_rows):
            prepared = revision_journal_rows[2 * index]
            committed = revision_journal_rows[2 * index + 1]
            operation_id = history_entry["operation_id"]
            if (
                prepared.get("schema_version") != JOURNAL_SCHEMA_VERSION
                or prepared.get("phase") != "prepared"
                or prepared.get("operation_id") != operation_id
                or prepared.get("history_entry") != history_entry
                or committed.get("schema_version") != JOURNAL_SCHEMA_VERSION
                or committed.get("phase") != "committed"
                or committed.get("operation_id") != operation_id
            ):
                raise ValueError("configuration history journal authority is invalid")
    if replayed != current_config.to_dict():
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "configuration history does not reach persisted configuration",
        )
    return snapshots


def _verify_receipt_config_history(
    layout: Any,
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
    config_hashes: Sequence[str],
    current_config: EvaluationAssetConfig,
) -> None:
    history_index = 0
    for stage in _HISTORICAL_PIPELINE_STAGES_V1:
        receipt_hash = receipts[stage].get("resolved_config_sha256")
        match = next(
            (
                index
                for index in range(history_index, len(config_hashes))
                if config_hashes[index] == receipt_hash
            ),
            None,
        )
        if match is None:
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "a receipt configuration lacks revision-history authority",
            )
        history_index = match
    final_hash = receipts[_HISTORICAL_PIPELINE_STAGES_V1[-1]].get(
        "resolved_config_sha256"
    )
    if final_hash != canonical_sha256(current_config.to_dict()):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "the final receipt does not authenticate persisted configuration",
        )


def _verify_candidate_receipts(
    layout: Any,
    state: PipelineState,
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
    *,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    artifact_path_overrides: Mapping[tuple[str, str], Path] | None = None,
) -> dict[PipelineStage, dict[str, Any]]:
    """Authenticate an in-memory adoption chain before installing authority."""
    if set(receipts) != set(_HISTORICAL_PIPELINE_STAGES_V1):
        raise ValueError("candidate receipt inventory is incomplete")
    config = layout.load_config()
    resolved_config = config.to_dict()
    verified: dict[PipelineStage, dict[str, Any]] = {}
    for stage in _HISTORICAL_PIPELINE_STAGES_V1:
        receipt = dict(receipts[stage])
        specification = _HISTORICAL_STAGE_SPECIFICATIONS_V1[stage]
        expected_fields = set(_STAGE_RECEIPT_FIELDS)
        if stage.value == "dataset_splits":
            expected_fields.update(
                {
                    "config_history_sha256",
                    "build_provenance_sha256",
                    "generation_manifest_sha256",
                }
            )
        if (
            set(receipt) != expected_fields
            or receipt.get("schema_version") != STAGE_RECEIPT_SCHEMA_VERSION
            or receipt.get("stage") != stage.value
            or not isinstance(receipt.get("stage_index"), int)
            or isinstance(receipt.get("stage_index"), bool)
            or receipt.get("stage_index") != _HISTORICAL_STAGE_INDEX_V1[stage]
            or receipt.get("origin") != "legacy_adoption"
            or not _canonical_utc_timestamp(receipt.get("completed_at"))
        ):
            raise ValueError("candidate receipt identity is invalid")
        receipt_sha256 = persisted_json_sha256(receipt)
        if _stage_state(state, stage).receipt_sha256 != receipt_sha256:
            raise ValueError("candidate state receipt identity is invalid")
        artifact_profile = receipt.get("artifact_profile")
        if artifact_profile not in {"native", "legacy"}:
            raise ValueError("candidate receipt artifact profile is invalid")
        required_outputs, direct_inputs = _declared_artifacts_for_profile(
            specification,
            artifact_profile,
        )
        outputs = receipt.get("outputs")
        expected_outputs = _expected_output_locations(
            layout,
            stage,
            specification,
            required_outputs,
            include_native_evidence=True,
            include_provider_calls=False,
            historical=True,
            artifact_overrides=artifact_overrides,
            artifact_path_overrides=artifact_path_overrides,
        )
        if not isinstance(outputs, list) or len(outputs) != len(expected_outputs):
            raise ValueError("candidate receipt output inventory is invalid")
        recorded_outputs: set[tuple[str, str]] = set()
        for item in outputs:
            if not isinstance(item, Mapping) or set(item) != {
                "path",
                "scope",
                "sha256",
                "bytes",
                "required",
            } or item.get("required") is not True:
                raise ValueError("candidate receipt output row is invalid")
            recorded_outputs.add((str(item.get("scope")), str(item.get("path"))))
            _verify_file_record(
                layout,
                stage,
                item,
                artifact_overrides=artifact_overrides,
                closed_overrides=artifact_overrides is not None,
            )
        if recorded_outputs != expected_outputs:
            raise ValueError("candidate receipt output inventory is incomplete")

        inputs = receipt.get("inputs")
        expected_inputs = {
            (
                "asset",
                _selected_legacy_artifact_path(
                    layout,
                    input_stage,
                    name,
                    artifact_path_overrides,
                )
                .relative_to(layout.root)
                .as_posix(),
            )
            for input_stage, name in direct_inputs
        }
        expected_inputs.update(
            (
                "asset",
                path.relative_to(layout.root).as_posix(),
            )
            for path in extension_receipt_input_paths(
                layout,
                stage,
                historical=True,
                artifact_overrides=artifact_overrides,
            )
        )
        if not isinstance(inputs, list) or len(inputs) != len(expected_inputs):
            raise ValueError("candidate receipt input inventory is invalid")
        recorded_inputs: set[tuple[str, str]] = set()
        for item in inputs:
            if not isinstance(item, Mapping) or set(item) != {
                "path",
                "scope",
                "sha256",
                "bytes",
            }:
                raise ValueError("candidate receipt input row is invalid")
            recorded_inputs.add((str(item.get("scope")), str(item.get("path"))))
            _verify_file_record(
                layout,
                stage,
                item,
                artifact_overrides=artifact_overrides,
                closed_overrides=artifact_overrides is not None,
            )
        if recorded_inputs != expected_inputs:
            raise ValueError("candidate receipt input inventory is incomplete")

        expected_upstream = [
            {
                "stage": dependency.value,
                "sha256": persisted_json_sha256(receipts[dependency]),
            }
            for dependency in specification.upstream_stages
        ]
        if receipt.get("upstream_receipts") != expected_upstream:
            raise ValueError("candidate receipt chain is invalid")
        counts = receipt.get("counts")
        if (
            not isinstance(counts, Mapping)
            or set(counts) != _HISTORICAL_STAGE_COUNT_KEYS_V1[stage]
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                or state.counts.get(key) != value
                for key, value in counts.items()
            )
        ):
            raise ValueError("candidate receipt counts are invalid")
        unavailable_sha256 = canonical_sha256(LEGACY_UNAVAILABLE_PROVENANCE)
        dependency_config = {
            field: resolved_config[field] for field in specification.config_fields
        }
        if (
            receipt.get("resolved_config_sha256")
            != canonical_sha256(resolved_config)
            or receipt.get("dependency_config_sha256")
            != canonical_sha256(dependency_config)
            or receipt.get("prompt_set_sha256") != unavailable_sha256
            or receipt.get("provider_identity") != LEGACY_UNAVAILABLE_PROVENANCE
            or receipt.get("provider_identity_sha256") != unavailable_sha256
            or receipt.get("provider_calls_sha256") != unavailable_sha256
            or receipt.get("code") != LEGACY_UNAVAILABLE_PROVENANCE
            or receipt.get("code_sha256") != unavailable_sha256
            or not isinstance(receipt.get("completed_at"), str)
            or not receipt["completed_at"]
        ):
            raise ValueError("candidate receipt evidence is invalid")
        for field in (
            "resolved_config_sha256",
            "dependency_config_sha256",
            "prompt_set_sha256",
            "provider_identity_sha256",
            "provider_calls_sha256",
            "code_sha256",
        ):
            if not isinstance(receipt.get(field), str) or not _SHA256.fullmatch(
                receipt[field]
            ):
                raise ValueError("candidate receipt hash is invalid")
        if stage.value == "dataset_splits" and receipt.get(
            "config_history_sha256"
        ) != _local_authority_sha256(layout, layout.config_history_path):
            raise ValueError("candidate configuration history evidence changed")
        if stage.value == "dataset_splits" and (
            receipt.get("build_provenance_sha256")
            != _local_authority_sha256(layout, layout.build_provenance_path)
            or receipt.get("generation_manifest_sha256")
            != _file_or_override_sha256(
                layout,
                layout.artifact_path(
                    _HISTORICAL_PIPELINE_STAGES_V1[-1],
                    "generation_manifest.json",
                ),
                artifact_overrides,
            )
        ):
            raise ValueError("candidate release provenance evidence changed")
        _validate_stage_provenance_evidence(
            layout,
            stage,
            receipt,
            config,
            artifact_overrides=artifact_overrides,
            historical_evidence=True,
        )
        verified[stage] = receipt
    return verified


def _canonical_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return (
        parsed.tzinfo is not None
        and parsed.utcoffset() == timedelta(0)
        and parsed.isoformat() == value
    )


def verify_raw_snapshot_floor(layout: Any, state: PipelineState) -> None:
    """Fail closed when the immutable Stage 1 rebuild floor is unavailable."""
    raw_paths = (layout.feedback_path, layout.unlabeled_path)
    if not all(path.is_file() for path in raw_paths):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "an immutable raw input snapshot is missing",
        )
    raw_stage = _HISTORICAL_PIPELINE_STAGES_V1[0]
    stage_state = _stage_state(state, raw_stage)
    receipt_path = layout.receipt_path(raw_stage)
    try:
        events = read_strict_jsonl_objects(
            layout.events_path,
            trusted_root=layout.tenants_root,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot audit authority is malformed",
        ) from exc
    prior_stage_completion = state.schema_version == STATE_SCHEMA_VERSION and any(
        event.get("event") == "stage_completed" for event in events
    )
    unclaimed_status_is_coherent = (
        stage_state.status == "pending"
        and state.status in {"draft", "queued", "running", "failed"}
    ) or (
        stage_state.status in {"running", "failed"}
        and state.status == stage_state.status
        and state.current_stage == raw_stage.value
    )
    never_receipted = (
        stage_state.status != "completed"
        and stage_state.receipt_sha256 is None
        and not receipt_path.exists()
        and not prior_stage_completion
        and unclaimed_status_is_coherent
    )
    if never_receipted:
        return
    receipt_bytes = (
        _local_authority_bytes(layout, receipt_path)
        if receipt_path.is_file()
        else None
    )
    if (
        stage_state.status != "completed"
        or not isinstance(stage_state.receipt_sha256, str)
        or not _SHA256.fullmatch(stage_state.receipt_sha256)
        or receipt_bytes is None
        or hashlib.sha256(receipt_bytes).hexdigest()
        != stage_state.receipt_sha256
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot receipt authority is inconsistent",
        )
    try:
        receipt = json.loads(receipt_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot receipt is malformed",
        ) from exc
    if (
        not isinstance(receipt, Mapping)
        or set(receipt) != _STAGE_RECEIPT_FIELDS
        or receipt.get("schema_version") != STAGE_RECEIPT_SCHEMA_VERSION
        or receipt.get("stage") != raw_stage.value
        or receipt.get("stage_index") != 1
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot receipt is invalid",
        )
    inputs = receipt.get("inputs")
    raw_relative_paths = {
        path.relative_to(layout.root).as_posix() for path in raw_paths
    }
    if not isinstance(inputs, list) or len(inputs) != len(raw_relative_paths):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot receipt inventory is incomplete",
        )
    records = {
        str(item.get("path")): item
        for item in inputs
        if isinstance(item, Mapping)
        and set(item) == {"path", "scope", "sha256", "bytes"}
        and item.get("scope") == "asset"
        and item.get("path") in raw_relative_paths
    }
    if set(records) != raw_relative_paths:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot receipt inventory is incomplete",
        )
    for item in records.values():
        try:
            _verify_file_record(layout, raw_stage, item)
        except EvaluationAssetIntegrityError as exc:
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "an immutable raw input snapshot is corrupt",
            ) from exc


def _expected_output_locations(
    layout: Any,
    stage: PipelineStage,
    specification: StageSpecification,
    required_outputs: Sequence[str],
    *,
    include_native_evidence: bool,
    include_provider_calls: bool,
    historical: bool,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    artifact_path_overrides: Mapping[tuple[str, str], Path] | None = None,
) -> set[tuple[str, str]]:
    expected = {
        (
            "asset",
            _selected_legacy_artifact_path(
                layout,
                stage,
                name,
                artifact_path_overrides,
            )
            .relative_to(layout.root)
            .as_posix(),
        )
        for name in required_outputs
    }
    if include_native_evidence:
        expected.update(
            (
                "asset",
                _stage_evidence_path(layout, stage, name)
                .relative_to(layout.root)
                .as_posix(),
            )
            for name in specification.required_evidence_outputs
        )
        if include_provider_calls and specification.provider_roles:
            expected.add(
                (
                    "asset",
                    layout.artifact_path(stage, "provider_calls.jsonl")
                    .relative_to(layout.root)
                    .as_posix(),
                )
            )
    lineage_present = (
        layout.lineage_path in artifact_overrides
        if artifact_overrides is not None
        else layout.lineage_path.is_file()
    )
    if stage.value == "intent_clustering" and lineage_present:
        expected.add(
            (
                "asset",
                _selected_legacy_artifact_path(
                    layout,
                    stage,
                    "cluster_lineage.jsonl",
                    artifact_path_overrides,
                )
                .relative_to(layout.root)
                .as_posix(),
            )
        )
    expected.update(("asset", name) for name in specification.required_asset_outputs)
    expected.update(
        (
            "tenant",
            (layout.published_datasets / name)
            .relative_to(layout.tenant_root)
            .as_posix(),
        )
        for name in specification.required_catalog_outputs
    )
    try:
        expected.update(
            (
                "asset",
                path.relative_to(layout.root).as_posix(),
            )
            for path in extension_receipt_output_paths(
                layout,
                stage,
                historical=historical,
                artifact_overrides=artifact_overrides,
            )
        )
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise _integrity(layout, stage, "extension output evidence is inconsistent") from exc
    return expected


def _selected_legacy_artifact_path(
    layout: Any,
    stage: PipelineStage,
    name: str,
    artifact_path_overrides: Mapping[tuple[str, str], Path] | None,
) -> Path:
    """Resolve one already-selected legacy artifact path without rebinding it."""
    if artifact_path_overrides is not None:
        try:
            return artifact_path_overrides[(stage.value, name)]
        except KeyError as exc:
            raise ValueError("legacy artifact path snapshot is incomplete") from exc
    return layout.artifact_path(stage, name)


def _stage_evidence_path(layout: Any, stage: PipelineStage, name: str) -> Path:
    if name == "provenance.json":
        return layout.stage_provenance_path(stage)
    return layout.artifact_path(stage, name)


def _capture_optional_legacy_artifact(
    layout: Any,
    stage: PipelineStage,
    path: Path,
    artifact_snapshot: dict[Path, bytes],
    artifact_presence: dict[Path, bool],
) -> bool:
    """Capture one exact optional-node presence result and its bound bytes."""
    if path in artifact_presence:
        return artifact_presence[path]
    prospective = resolve_local_authority_file(
        path,
        layout.tenants_root,
        access="write",
    )
    artifact_presence[path] = prospective.exists
    if prospective.exists:
        artifact_snapshot[path] = _validate_artifact_syntax(
            layout,
            stage,
            path,
        )
    return prospective.exists


def _capture_legacy_extension_authority(
    layout: Any,
    artifact_snapshot: dict[Path, bytes],
    artifact_presence: dict[Path, bool],
) -> None:
    """Capture extension control and declared snapshot members before semantics."""
    stage = _HISTORICAL_PIPELINE_STAGES_V1[0]
    lineage_exists = _capture_optional_legacy_artifact(
        layout,
        stage,
        layout.lineage_path,
        artifact_snapshot,
        artifact_presence,
    )
    reuse_exists = _capture_optional_legacy_artifact(
        layout,
        stage,
        layout.reuse_manifest_path,
        artifact_snapshot,
        artifact_presence,
    )
    if not lineage_exists and not reuse_exists:
        return
    if not lineage_exists or not reuse_exists:
        raise ValueError("extension authority inventory is incomplete")
    reuse = parse_strict_json_object(artifact_snapshot[layout.reuse_manifest_path])
    snapshot = reuse.get("parent_snapshot")
    if not isinstance(snapshot, Mapping) or not isinstance(
        snapshot.get("artifacts"),
        list,
    ):
        raise ValueError("extension parent snapshot inventory is invalid")
    names: set[str] = set()
    for row in snapshot["artifacts"]:
        if not isinstance(row, Mapping):
            raise ValueError("extension parent snapshot row is invalid")
        name = row.get("file")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in names
        ):
            raise ValueError("extension parent snapshot name is invalid")
        names.add(name)
        path = layout.historical_parent_snapshot / name
        if not _capture_optional_legacy_artifact(
            layout,
            stage,
            path,
            artifact_snapshot,
            artifact_presence,
        ):
            raise ValueError("extension parent snapshot member is missing")


def validate_legacy_release_candidate(
    layout: Any,
    state: PipelineState,
    config: EvaluationAssetConfig,
    *,
    prepared_release: Mapping[str, Any] | None = None,
    manifest_payload: Mapping[str, Any] | None = None,
    artifact_snapshot_out: dict[Path, bytes] | None = None,
    artifact_presence_out: dict[Path, bool] | None = None,
    artifact_paths_out: dict[tuple[str, str], Path] | None = None,
    artifact_profiles_out: dict[str, str] | None = None,
) -> dict[str, int]:
    """Validate a pre-v2 completion and return independently derived counts."""
    _validate_local_authority_layout(layout)
    if not state.legacy_completed:
        raise EvaluationAssetLegacyError(
            layout.tenant_id,
            layout.asset_id,
            "only a pre-v2 completed state can be adopted",
        )
    if state.tenant_id != layout.tenant_id or state.asset_id != layout.asset_id:
        raise _legacy_invalid(layout)
    if config.tenant_id != layout.tenant_id or config.asset_id != layout.asset_id:
        raise _legacy_invalid(layout)
    try:
        artifact_profiles: dict[PipelineStage, str] = {}
        artifact_paths: dict[tuple[str, str], Path] = {}
        artifact_snapshot: dict[Path, bytes] = {}
        artifact_presence: dict[Path, bool] = {}
        _capture_legacy_extension_authority(
            layout,
            artifact_snapshot,
            artifact_presence,
        )
        for stage in _HISTORICAL_PIPELINE_STAGES_V1:
            if _stage_state(state, stage).status != "completed":
                raise ValueError("legacy stage is incomplete")
            specification = _HISTORICAL_STAGE_SPECIFICATIONS_V1[stage]
            required_outputs, direct_inputs, artifact_profile = _stage_artifact_profile(
                layout,
                stage,
                allow_legacy=True,
                specification=specification,
                artifact_snapshot=artifact_snapshot,
                artifact_presence=artifact_presence,
            )
            artifact_profiles[stage] = artifact_profile
            output_paths = [
                layout.artifact_path(stage, name) for name in required_outputs
            ]
            input_paths = [
                layout.artifact_path(input_stage, name)
                for input_stage, name in direct_inputs
            ]
            for name, path in zip(required_outputs, output_paths, strict=True):
                artifact_paths[(stage.value, name)] = path
            for (input_stage, name), path in zip(
                direct_inputs,
                input_paths,
                strict=True,
            ):
                key = (input_stage.value, name)
                if key in artifact_paths and artifact_paths[key] != path:
                    raise ValueError("legacy artifact path selection is inconsistent")
                artifact_paths[key] = path
            paths = [*output_paths, *input_paths]
            paths.extend(
                layout.root / name
                for name in (
                    ("asset_manifest.json",)
                    if stage.value == "dataset_splits"
                    else specification.required_asset_outputs
                )
            )
            if stage.value == "dataset_splits":
                paths.extend(
                    layout.published_datasets / name
                    for name in _LEGACY_CATALOG_OUTPUTS
                )
            if (
                stage.value == "intent_clustering"
                and artifact_presence.get(layout.lineage_path, False)
            ):
                cluster_lineage_path = layout.artifact_path(
                    stage,
                    "cluster_lineage.jsonl",
                )
                artifact_paths[(stage.value, "cluster_lineage.jsonl")] = (
                    cluster_lineage_path
                )
                paths.append(cluster_lineage_path)
            for path in paths:
                if not _capture_optional_legacy_artifact(
                    layout,
                    stage,
                    path,
                    artifact_snapshot,
                    artifact_presence,
                ):
                    raise ValueError("required artifact is missing")
            extension_paths = extension_receipt_input_paths(
                layout,
                stage,
                historical=True,
                artifact_overrides=artifact_snapshot,
            )
            if any(path not in artifact_snapshot for path in extension_paths):
                raise ValueError("extension authority snapshot is incomplete")

        validate_legacy_stage_semantics(
            layout,
            artifact_profiles,
            artifact_snapshot=artifact_snapshot,
        )

        input_manifest = _read_json_object(
            layout,
            layout.artifact_path(
                _HISTORICAL_PIPELINE_STAGES_V1[0],
                "input_manifest.json",
            ),
            artifact_snapshot,
        )
        feedback_rows = _read_jsonl_objects(
            layout,
            layout.historical_feedback_path,
            artifact_snapshot,
        )
        unlabeled_rows = _read_jsonl_objects(
            layout,
            layout.historical_unlabeled_path,
            artifact_snapshot,
        )
        expected_inputs = {
            "labeled_feedback": (
                layout.historical_feedback_path,
                len(feedback_rows),
            ),
            "unlabeled": (
                layout.historical_unlabeled_path,
                len(unlabeled_rows),
            ),
        }
        manifest_inputs = input_manifest.get("inputs")
        if not isinstance(manifest_inputs, Mapping):
            raise ValueError("input manifest is incomplete")
        for name, (path, row_count) in expected_inputs.items():
            details = manifest_inputs.get(name)
            if not isinstance(details, Mapping) or (
                details.get("file") != path.name
                or details.get("rows") != row_count
                or details.get("sha256")
                != hashlib.sha256(artifact_snapshot[path]).hexdigest()
            ):
                raise ValueError("input manifest is inconsistent")

        dataset_manifest = (
            dict(manifest_payload)
            if manifest_payload is not None
            else _read_json_object(
                layout,
                layout.artifact_path(
                    _HISTORICAL_PIPELINE_STAGES_V1[-1],
                    "dataset_manifest.json",
                ),
                artifact_snapshot,
            )
        )
        asset_manifest = (
            dict(manifest_payload)
            if manifest_payload is not None
            else _read_json_object(
                layout,
                layout.manifest_path,
                artifact_snapshot,
            )
        )
        if dataset_manifest != asset_manifest:
            raise ValueError("asset manifests differ")
        if dataset_manifest.get("asset_id") != layout.asset_id or (
            dataset_manifest.get("tenant_id") != layout.tenant_id
        ):
            raise ValueError("asset manifest identity is inconsistent")
        expected_source_hashes = {
            name: str(manifest_inputs[name]["sha256"])
            for name in expected_inputs
        }
        if dataset_manifest.get("source_hashes") != expected_source_hashes:
            raise ValueError("source hashes are inconsistent")

        split_counts: dict[str, int] = {}
        for name in _SPLIT_OUTPUTS:
            split_counts[Path(name).stem] = len(
                _read_jsonl_objects(
                    layout,
                    layout.artifact_path(
                        _HISTORICAL_PIPELINE_STAGES_V1[-1],
                        name,
                    ),
                    artifact_snapshot,
                )
            )
        manifest_split_counts = dataset_manifest.get("split_counts")
        if not isinstance(manifest_split_counts, Mapping) or any(
            manifest_split_counts.get(name) != count
            for name, count in split_counts.items()
        ):
            raise ValueError("split counts are inconsistent")

        published = dataset_manifest.get("published_datasets")
        expected_catalog = {
            Path(name).stem: (layout.published_datasets / name)
            .relative_to(layout.tenant_root)
            .as_posix()
            for name in _LEGACY_CATALOG_OUTPUTS
        }
        expected_catalog_directory = layout.published_datasets.relative_to(
            layout.tenant_root
        ).as_posix()
        expected_published: Mapping[str, Any]
        if prepared_release is None:
            expected_published = {
                "directory": expected_catalog_directory,
                "files": expected_catalog,
            }
        else:
            generation_id = str(prepared_release.get("generation_id") or "")
            generation_directory = (
                layout.generations_root / generation_id
            ).relative_to(
                layout.tenants_root.parent
                if manifest_payload is not None
                else layout.tenant_root
            ).as_posix()
            expected_published = {
                "directory": expected_catalog_directory,
                "release_pointer": layout.release_pointer_path.relative_to(
                    layout.tenant_root
                ).as_posix(),
                "generation_id": generation_id,
                "generation_manifest_sha256": prepared_release.get(
                    "generation_manifest_sha256"
                ),
                "build_provenance_sha256": prepared_release.get(
                    "build_provenance_sha256"
                ),
                "build_fingerprint": prepared_release.get("build_fingerprint"),
                "files": {
                    split: f"{generation_directory}/{split}.jsonl"
                    for split in LOGICAL_SPLITS
                },
            }
        if not isinstance(published, Mapping) or dict(published) != dict(
            expected_published
        ):
            raise ValueError("published dataset manifest is inconsistent")
        for name in _LEGACY_CATALOG_OUTPUTS:
            stage_path = layout.artifact_path(
                _HISTORICAL_PIPELINE_STAGES_V1[-1],
                name,
            )
            catalog_path = layout.published_datasets / name
            if hashlib.sha256(artifact_snapshot[stage_path]).digest() != (
                hashlib.sha256(artifact_snapshot[catalog_path]).digest()
            ):
                raise ValueError("published dataset copy is inconsistent")

        if layout.lineage_path in artifact_snapshot:
            lineage = _read_json_object(
                layout,
                layout.lineage_path,
                artifact_snapshot,
            )
            reuse = _read_json_object(
                layout,
                layout.reuse_manifest_path,
                artifact_snapshot,
            )
            if dataset_manifest.get("lineage") != lineage or not reuse:
                raise ValueError("extension lineage is inconsistent")
        counts = _derive_legacy_counts(
            layout,
            split_counts,
            artifact_snapshot,
        )
        if artifact_snapshot_out is not None:
            artifact_snapshot_out.update(artifact_snapshot)
        if artifact_presence_out is not None:
            artifact_presence_out.update(artifact_presence)
        if artifact_paths_out is not None:
            artifact_paths_out.update(artifact_paths)
        if artifact_profiles_out is not None:
            artifact_profiles_out.update(
                {stage.value: profile for stage, profile in artifact_profiles.items()}
            )
        return counts
    except EvaluationAssetLegacyError:
        raise
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise _legacy_invalid(layout) from exc


def _stage_artifact_profile(
    layout: Any,
    stage: PipelineStage,
    *,
    allow_legacy: bool,
    specification: StageSpecification | None = None,
    artifact_snapshot: dict[Path, bytes] | None = None,
    artifact_presence: dict[Path, bool] | None = None,
) -> tuple[
    tuple[str, ...],
    tuple[tuple[PipelineStage, str], ...],
    str,
]:
    specification = specification or STAGE_SPECIFICATIONS[stage]
    if not allow_legacy:
        return specification.required_outputs, specification.direct_inputs, "native"
    capture_inventory = artifact_snapshot is not None

    def present(path: Path) -> bool:
        if capture_inventory:
            if artifact_presence is None:
                return path in artifact_snapshot
            return _capture_optional_legacy_artifact(
                layout,
                stage,
                path,
                artifact_snapshot,
                artifact_presence,
            )
        return path.is_file()

    if stage.value == "rubric_extraction":
        canonical_root = layout.stages_root / "03_evaluation_guidelines"
        legacy_root = layout.stages_root / "03_rubric_extraction"
        native_presence = tuple(
            present(canonical_root / name)
            for name in specification.required_outputs
        )
        legacy_presence = tuple(
            present(legacy_root / name)
            for name in specification.legacy_required_outputs
        )
        native_complete = all(native_presence)
        legacy_complete = all(legacy_presence)
        if native_complete and legacy_complete:
            raise ValueError("stage three has competing complete artifact profiles")
    if specification.legacy_required_outputs:
        native_presence = tuple(
            present(layout.artifact_path(stage, name))
            for name in specification.required_outputs
        )
        legacy_presence = tuple(
            present(layout.artifact_path(stage, name))
            for name in specification.legacy_required_outputs
        )
        native_complete = all(native_presence)
        legacy_complete = all(legacy_presence)
        if not native_complete and legacy_complete:
            return (
                specification.legacy_required_outputs,
                specification.direct_inputs,
                "legacy",
            )
    if specification.legacy_direct_inputs:
        native_presence = tuple(
            present(layout.artifact_path(input_stage, name))
            for input_stage, name in specification.direct_inputs
        )
        legacy_presence = tuple(
            present(layout.artifact_path(input_stage, name))
            for input_stage, name in specification.legacy_direct_inputs
        )
        native_complete = all(native_presence)
        legacy_complete = all(legacy_presence)
        if not native_complete and legacy_complete:
            return (
                specification.required_outputs,
                specification.legacy_direct_inputs,
                "legacy",
            )
    return specification.required_outputs, specification.direct_inputs, "native"


def _declared_artifacts_for_profile(
    specification: StageSpecification,
    artifact_profile: Any,
) -> tuple[tuple[str, ...], tuple[tuple[PipelineStage, str], ...]]:
    if artifact_profile == "legacy":
        return (
            specification.legacy_required_outputs
            or specification.required_outputs,
            specification.legacy_direct_inputs or specification.direct_inputs,
        )
    return specification.required_outputs, specification.direct_inputs


def _authority_bytes(
    layout: Any,
    path: Path,
    artifact_snapshot: Mapping[Path, bytes] | None,
) -> bytes:
    if artifact_snapshot is not None:
        try:
            return artifact_snapshot[path]
        except KeyError as exc:
            raise ValueError("legacy authority snapshot is incomplete") from exc
    return _local_authority_bytes(layout, path)


def _read_json_object(
    layout: Any,
    path: Path,
    artifact_snapshot: Mapping[Path, bytes] | None = None,
) -> dict[str, Any]:
    return parse_strict_json_object(
        _authority_bytes(layout, path, artifact_snapshot)
    )


def _read_jsonl_objects(
    layout: Any,
    path: Path,
    artifact_snapshot: Mapping[Path, bytes] | None = None,
    *,
    optional: bool = False,
) -> list[dict[str, Any]]:
    if optional and artifact_snapshot is not None and path not in artifact_snapshot:
        return []
    if optional and artifact_snapshot is None:
        release_snapshot = _RELEASE_AUTHORITY_SNAPSHOT.get()
        lexical_path = Path(path).absolute()
        if release_snapshot is not None and lexical_path not in release_snapshot:
            return []
        if release_snapshot is None:
            authority = resolve_local_authority_file(
                path,
                layout.tenants_root,
                access="read_optional",
            )
            if not authority.exists:
                return []
            if authority.data is None:
                raise ValueError("optional authority read did not return bytes")
            artifact_snapshot = {path: authority.data}
    return parse_strict_jsonl_objects(
        _authority_bytes(
            layout,
            path,
            artifact_snapshot,
        )
    )


def _derive_legacy_counts(
    layout: Any,
    split_counts: Mapping[str, int],
    artifact_snapshot: Mapping[Path, bytes] | None = None,
) -> dict[str, int]:
    def rows(stage: PipelineStage, name: str) -> list[dict[str, Any]]:
        return _read_jsonl_objects(
            layout,
            layout.artifact_path(stage, name),
            artifact_snapshot,
        )

    def captured(stage: PipelineStage, name: str) -> bool:
        path = layout.artifact_path(stage, name)
        if artifact_snapshot is not None:
            return path in artifact_snapshot
        return path.is_file()

    feedback = rows(_HISTORICAL_PIPELINE_STAGES_V1[0], "labeled_feedback.jsonl")
    unlabeled = rows(_HISTORICAL_PIPELINE_STAGES_V1[0], "unlabeled.jsonl")
    normalized = rows(
        _HISTORICAL_PIPELINE_STAGES_V1[1],
        "normalized_feedback.jsonl",
    )
    intents = rows(_HISTORICAL_PIPELINE_STAGES_V1[1], "intent_records.jsonl")
    guidelines = (
        rows(_HISTORICAL_PIPELINE_STAGES_V1[2], "evaluation_guidelines.jsonl")
        if captured(
            _HISTORICAL_PIPELINE_STAGES_V1[2], "evaluation_guidelines.jsonl"
        )
        else []
    )
    evidence = (
        rows(_HISTORICAL_PIPELINE_STAGES_V1[2], "feedback_evidence.jsonl")
        if captured(
            _HISTORICAL_PIPELINE_STAGES_V1[2], "feedback_evidence.jsonl"
        )
        else []
    )
    candidates = (
        rows(_HISTORICAL_PIPELINE_STAGES_V1[2], "candidate_guidelines.jsonl")
        if captured(
            _HISTORICAL_PIPELINE_STAGES_V1[2], "candidate_guidelines.jsonl"
        )
        else []
    )
    trusted = rows(_HISTORICAL_PIPELINE_STAGES_V1[2], "trusted_cases.jsonl")
    clusters = rows(_HISTORICAL_PIPELINE_STAGES_V1[3], "intent_inventory.jsonl")
    matches = rows(_HISTORICAL_PIPELINE_STAGES_V1[4], "intent_matches.jsonl")
    allowed_statuses = {
        "matched_trusted_intent",
        "needs_more_trusted_examples",
        "missing_or_weak_labels",
    }
    if any(row.get("status") not in allowed_statuses for row in matches):
        raise ValueError("coverage status is unsupported")
    queue = rows(
        _HISTORICAL_PIPELINE_STAGES_V1[4],
        "review_queue/labeling_queue.jsonl",
    )
    inferred = rows(_HISTORICAL_PIPELINE_STAGES_V1[5], "inferred_cases.jsonl")
    missing = rows(
        _HISTORICAL_PIPELINE_STAGES_V1[5],
        "missing_labeled_feedback_clusters.jsonl",
    )
    synthetic = rows(_HISTORICAL_PIPELINE_STAGES_V1[6], "synthetic_cases.jsonl")
    rejected = rows(
        _HISTORICAL_PIPELINE_STAGES_V1[6],
        "rejected_synthetic.jsonl",
    )
    return {
        "feedback_records": len(feedback),
        "unlabeled_records": len(unlabeled),
        "prepared_feedback": len(normalized),
        "prepared_intents": len(intents),
        "feedback_evidence": len(evidence),
        "candidate_guidelines": len(candidates),
        "evaluation_guidelines": len(guidelines),
        "trusted_cases": len(trusted),
        "intent_clusters": len(clusters),
        "matched_clusters": sum(
            row["status"] == "matched_trusted_intent" for row in matches
        ),
        "needs_more_feedback_clusters": sum(
            row["status"] == "needs_more_trusted_examples" for row in matches
        ),
        "missing_label_clusters": sum(
            row["status"] == "missing_or_weak_labels" for row in matches
        ),
        "labeling_queue_clusters": len({row["cluster_id"] for row in queue}),
        "labeling_queue_traces": len(queue),
        "inferred_cases": len(inferred),
        "review_clusters": len(missing),
        "synthetic_cases": len(synthetic),
        "rejected_synthetic_cases": len(rejected),
        "dataset_cases": len(trusted) + len(inferred) + len(synthetic),
        "train_cases": int(split_counts["train"]),
        "validation_cases": int(split_counts["validation"]),
        "test_cases": int(split_counts["test"]),
        "regression_trusted_cases": int(split_counts["regression_trusted"]),
        "triage_hold_cases": int(split_counts["triage_hold"]),
    }


def _legacy_invalid(layout: Any) -> EvaluationAssetLegacyError:
    return EvaluationAssetLegacyError(
        layout.tenant_id,
        layout.asset_id,
        "required stage artifacts or manifests failed verification",
    )


def _verify_extension_lineage(
    layout: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        evidence = validate_extension_evidence(
            layout,
            require_asset_manifest=True,
            historical=True,
            artifact_overrides=_RELEASE_AUTHORITY_SNAPSHOT.get(),
        )
        return evidence.lineage, evidence.reuse
    except EvaluationAssetIntegrityError:
        raise
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "source lineage metadata is inconsistent",
        ) from exc


def _verify_file_record(
    layout: Any,
    stage: PipelineStage,
    item: Any,
    *,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    closed_overrides: bool = False,
) -> None:
    if not isinstance(item, Mapping):
        raise _integrity(layout, stage, "artifact inventory row is invalid")
    scope = item.get("scope")
    if scope not in {"asset", "tenant"}:
        raise _integrity(layout, stage, "artifact scope is invalid")
    recorded_path = item.get("path")
    recorded_bytes = item.get("bytes")
    recorded_sha256 = item.get("sha256")
    if (
        not isinstance(recorded_path, str)
        or not recorded_path
        or not isinstance(recorded_bytes, int)
        or isinstance(recorded_bytes, bool)
        or recorded_bytes < 0
        or not isinstance(recorded_sha256, str)
        or not _SHA256.fullmatch(recorded_sha256)
    ):
        raise _integrity(layout, stage, "artifact inventory scalar is invalid")
    relative = Path(recorded_path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise _integrity(layout, stage, "artifact path is unsafe")
    base = layout.root if scope == "asset" else layout.tenant_root
    path = base / relative
    release_snapshot = _RELEASE_AUTHORITY_SNAPSHOT.get()
    effective_overrides = (
        release_snapshot if artifact_overrides is None and release_snapshot is not None
        else artifact_overrides
    )
    override = (effective_overrides or {}).get(path)
    if override is not None:
        if len(override) != recorded_bytes or hashlib.sha256(
            override
        ).hexdigest() != recorded_sha256:
            raise _integrity(
                layout,
                stage,
                "a required artifact hash is inconsistent",
            )
        _validate_artifact_bytes(layout, stage, path, override)
        return
    if closed_overrides or release_snapshot is not None:
        raise _integrity(layout, stage, "authority snapshot is incomplete")
    try:
        authority = resolve_local_authority_file(
            path,
            layout.tenants_root,
            access="read",
        )
    except (OSError, ValueError) as exc:
        raise _integrity(layout, stage, "a required artifact is missing") from exc
    data = authority.data
    if data is None:
        raise _integrity(layout, stage, "a required artifact is missing")
    if len(data) != recorded_bytes or hashlib.sha256(data).hexdigest() != recorded_sha256:
        raise _integrity(layout, stage, "a required artifact hash is inconsistent")
    _validate_artifact_bytes(layout, stage, path, data)


def _validate_artifact_syntax(
    layout: Any,
    stage: PipelineStage,
    path: Path,
) -> bytes:
    try:
        payload = _local_authority_bytes(layout, path)
        _validate_artifact_bytes(
            layout,
            stage,
            path,
            payload,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise _integrity(layout, stage, "a required artifact is malformed") from exc
    return payload


def _validate_artifact_bytes(
    layout: Any,
    stage: PipelineStage,
    path: Path,
    payload: bytes,
) -> None:
    try:
        text = payload.decode("utf-8")
        if path.suffix == ".json":
            value = json.loads(text)
            if not isinstance(value, Mapping):
                raise ValueError("not an object")
        elif path.suffix == ".jsonl":
            for line in text.splitlines():
                if line.strip() and not isinstance(json.loads(line), Mapping):
                    raise ValueError("row is not an object")
        elif path.suffix == ".md" and not text.strip():
            raise ValueError("empty markdown")
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise _integrity(layout, stage, "a required artifact is malformed") from exc


def _file_or_override_sha256(
    layout: Any,
    path: Path,
    overrides: Mapping[Path, bytes] | None,
) -> str:
    override = (overrides or {}).get(path)
    return (
        hashlib.sha256(override).hexdigest()
        if override is not None
        else _local_authority_sha256(layout, path)
    )


def _stage_state(state: PipelineState, stage: PipelineStage) -> Any:
    try:
        return next(item for item in state.stages if item.stage == stage.value)
    except StopIteration as exc:
        raise ValueError(f"Pipeline state is missing stage {stage.value}") from exc


def _integrity(
    layout: Any,
    stage: PipelineStage,
    reason: str,
) -> EvaluationAssetIntegrityError:
    return EvaluationAssetIntegrityError(
        layout.tenant_id,
        layout.asset_id,
        f"stage {stage.value} {reason}",
    )


def _file_record(
    layout: Any,
    path: Path,
    *,
    scope: str,
    required: bool = False,
    artifact_overrides: Mapping[Path, bytes] | None = None,
    closed_overrides: bool = False,
) -> dict[str, Any]:
    override = (artifact_overrides or {}).get(path)
    if override is None:
        if closed_overrides:
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "legacy authority snapshot is incomplete",
            )
        try:
            payload = _local_authority_bytes(layout, path)
        except (OSError, ValueError) as exc:
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "a required stage artifact is missing",
            ) from exc
    else:
        payload = override
    base = layout.root if scope == "asset" else layout.tenant_root
    record = {
        "path": path.relative_to(base).as_posix(),
        "scope": scope,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }
    if required:
        record["required"] = True
    return record


def _provider_identity(
    config: EvaluationAssetConfig,
    roles: Sequence[str],
) -> Mapping[str, Any]:
    identities: dict[str, Any] = {}
    if "rubric" in roles:
        identities["rubric"] = {
            "provider": config.rubric_provider,
            "model": config.rubric_model,
        }
    if "embedding" in roles:
        identities["embedding"] = {
            "provider": config.embedding_provider,
            "model": config.embedding_model,
        }
    return identities or {"status": "not_applicable"}


def _code_identity() -> dict[str, Any]:
    return working_source_identity(Path(__file__).resolve().parents[3])

class EvaluationAssetError(RuntimeError):
    """Base class for stable, API-safe evaluation-asset failures."""


class EvaluationAssetBusyError(EvaluationAssetError):
    """Raised when another process owns an asset's mutation lock."""

    def __init__(self, tenant_id: str, asset_id: str) -> None:
        super().__init__(
            f"Evaluation asset {tenant_id}/{asset_id} is already being modified; "
            "retry after the active mutation finishes."
        )


class EvaluationAssetImmutableError(EvaluationAssetError):
    """Raised when a caller attempts to mutate a released asset."""

    def __init__(self, tenant_id: str, asset_id: str) -> None:
        super().__init__(
            f"Evaluation asset {tenant_id}/{asset_id} is released and immutable; "
            "create a child with assets extend "
            f"--parent-asset-id {asset_id} --asset-id <new-id>."
        )


class EvaluationAssetIntegrityError(EvaluationAssetError):
    """Raised when authoritative asset evidence fails closed verification."""

    def __init__(self, tenant_id: str, asset_id: str, reason: str) -> None:
        super().__init__(
            f"Evaluation asset integrity verification failed for "
            f"{tenant_id}/{asset_id}: {reason}. Repair this asset or create a "
            "new child version."
        )


class EvaluationAssetLegacyError(EvaluationAssetError):
    """Raised when a legacy completion requires explicit adoption."""

    def __init__(self, tenant_id: str, asset_id: str, reason: str) -> None:
        super().__init__(
            f"Legacy evaluation asset {tenant_id}/{asset_id} cannot be used: "
            f"{reason}. Run assets adopt after repair, or create a new asset version."
        )
