# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Durability contracts shared by evaluation-asset mutation paths."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.control_jsonl import (
    read_strict_jsonl_objects,
)
from src.hephaestus.evaluation_assets.journal_transitions import (
    JOURNAL_SCHEMA_VERSION,
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
    STAGE_COUNT_KEYS,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)
from src.hephaestus.evaluation_assets.provenance import (
    not_applicable,
    validate_build_provenance,
    validate_build_provenance_call_ledgers,
    working_source_identity,
)
from src.hephaestus.evaluation_assets.publication import (
    LOGICAL_SPLITS,
    resolve_evaluation_asset_release,
    validate_evaluation_asset_release_candidate,
)

STAGE_RECEIPT_SCHEMA_VERSION = "fapo-stage-receipt-v1"
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
_STAGE_RECEIPT_FIELDS = {
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

STAGE_SPECIFICATIONS = {
    PipelineStage.RAW_INPUTS: StageSpecification(
        required_outputs=("input_manifest.json",),
        direct_inputs=(
            (PipelineStage.RAW_INPUTS, "labeled_feedback.jsonl"),
            (PipelineStage.RAW_INPUTS, "unlabeled.jsonl"),
        ),
    ),
    PipelineStage.PREPARED_INPUTS: StageSpecification(
        required_outputs=("normalized_feedback.jsonl", "intent_records.jsonl"),
        direct_inputs=(
            (PipelineStage.RAW_INPUTS, "labeled_feedback.jsonl"),
            (PipelineStage.RAW_INPUTS, "unlabeled.jsonl"),
        ),
        upstream_stages=(PipelineStage.RAW_INPUTS,),
    ),
    PipelineStage.RUBRIC_EXTRACTION: StageSpecification(
        required_outputs=(
            "feedback_evidence.jsonl",
            "candidate_guidelines.jsonl",
            "evaluation_guidelines.jsonl",
            "trusted_intents.jsonl",
            "trusted_cases.jsonl",
        ),
        direct_inputs=(
            (PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl"),
        ),
        upstream_stages=(
            PipelineStage.RAW_INPUTS,
            PipelineStage.PREPARED_INPUTS,
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
    PipelineStage.INTENT_CLUSTERING: StageSpecification(
        required_outputs=("intent_inventory.jsonl",),
        direct_inputs=((PipelineStage.PREPARED_INPUTS, "intent_records.jsonl"),),
        upstream_stages=(
            PipelineStage.RAW_INPUTS,
            PipelineStage.PREPARED_INPUTS,
        ),
        config_fields=(
            "embedding_provider",
            "embedding_model",
            "cluster_count",
        ),
        provider_roles=("embedding",),
    ),
    PipelineStage.COVERAGE_DECISIONS: StageSpecification(
        required_outputs=(
            "intent_matches.jsonl",
            "coverage_report.md",
            "review_queue/labeling_queue.jsonl",
        ),
        direct_inputs=(
            (PipelineStage.PREPARED_INPUTS, "intent_records.jsonl"),
            (PipelineStage.RUBRIC_EXTRACTION, "trusted_intents.jsonl"),
            (PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl"),
        ),
        upstream_stages=(
            PipelineStage.RAW_INPUTS,
            PipelineStage.PREPARED_INPUTS,
            PipelineStage.RUBRIC_EXTRACTION,
            PipelineStage.INTENT_CLUSTERING,
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
    PipelineStage.LABEL_INFERENCE: StageSpecification(
        required_outputs=(
            "inferred_unlabeled_cluster_rubrics.jsonl",
            "inferred_unlabeled_labels.jsonl",
            "missing_labeled_feedback_clusters.jsonl",
            "missing_labeled_feedback_report.md",
            "inferred_cases.jsonl",
        ),
        direct_inputs=(
            (PipelineStage.RAW_INPUTS, "unlabeled.jsonl"),
            (PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl"),
            (PipelineStage.PREPARED_INPUTS, "intent_records.jsonl"),
            (PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl"),
            (PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl"),
            (PipelineStage.COVERAGE_DECISIONS, "intent_matches.jsonl"),
        ),
        upstream_stages=tuple(list(PipelineStage)[:5]),
        config_fields=("rubric_provider", "rubric_model", "batch_size"),
        prompt_names=("label_inference",),
        provider_roles=("rubric",),
        legacy_direct_inputs=(
            (PipelineStage.RAW_INPUTS, "unlabeled.jsonl"),
            (PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl"),
            (PipelineStage.PREPARED_INPUTS, "intent_records.jsonl"),
            (PipelineStage.RUBRIC_EXTRACTION, "feedback_rubrics.jsonl"),
            (PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl"),
            (PipelineStage.COVERAGE_DECISIONS, "intent_matches.jsonl"),
        ),
    ),
    PipelineStage.SYNTHETIC_COVERAGE: StageSpecification(
        required_outputs=(
            "synthetic_candidates.jsonl",
            "rejected_synthetic.jsonl",
            "synthetic_filter_issues.jsonl",
            "synthetic_cases.jsonl",
        ),
        direct_inputs=(
            (PipelineStage.PREPARED_INPUTS, "intent_records.jsonl"),
            (PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl"),
            (PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl"),
            (
                PipelineStage.LABEL_INFERENCE,
                "inferred_unlabeled_cluster_rubrics.jsonl",
            ),
            (PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl"),
        ),
        upstream_stages=tuple(list(PipelineStage)[:6]),
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
    PipelineStage.DATASET_SPLITS: StageSpecification(
        required_outputs=_SPLIT_OUTPUTS
        + ("dataset_manifest.json", "generation_manifest.json"),
        legacy_required_outputs=_SPLIT_OUTPUTS + ("dataset_manifest.json",),
        direct_inputs=(
            (PipelineStage.RAW_INPUTS, "input_manifest.json"),
            (PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl"),
            (PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl"),
            (PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl"),
        ),
        upstream_stages=tuple(list(PipelineStage)[:7]),
        config_fields=("split_seed",),
        required_asset_outputs=("asset_manifest.json", "build_provenance.json"),
    ),
}

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
    stage: PipelineStage,
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
) -> dict[str, Any]:
    """Build one receipt after all declared stage outputs exist."""
    specification = STAGE_SPECIFICATIONS[stage]
    required_outputs, direct_inputs, artifact_profile = _stage_artifact_profile(
        layout,
        stage,
        allow_legacy=origin == "legacy_adoption",
    )
    unavailable = (
        LEGACY_UNAVAILABLE_PROVENANCE
        if historical_unavailable
        else UNAVAILABLE_PROVENANCE
    )
    inputs = [
        _file_record(
            layout,
            layout.artifact_path(input_stage, name),
            scope="asset",
            artifact_overrides=artifact_overrides,
        )
        for input_stage, name in direct_inputs
    ]
    inputs.extend(
        _file_record(
            layout,
            path,
            scope="asset",
            artifact_overrides=artifact_overrides,
        )
        for path in extension_receipt_input_paths(layout, stage)
    )
    outputs = [
        _file_record(
            layout,
            layout.artifact_path(stage, name),
            scope="asset",
            required=True,
            artifact_overrides=artifact_overrides,
        )
        for name in required_outputs
    ]
    outputs.extend(
        _file_record(
            layout,
            layout.artifact_path(stage, name),
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
            )
        )
    if stage == PipelineStage.INTENT_CLUSTERING and layout.lineage_path.is_file():
        outputs.append(
            _file_record(
                layout,
                layout.artifact_path(stage, "cluster_lineage.jsonl"),
                scope="asset",
                required=True,
                artifact_overrides=artifact_overrides,
            )
        )
    outputs.extend(
        _file_record(
            layout,
            layout.root / name,
            scope="asset",
            required=True,
            artifact_overrides=artifact_overrides,
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
        )
        for path in extension_receipt_output_paths(layout, stage)
    )
    upstream = []
    for dependency in specification.upstream_stages:
        if upstream_receipts is None:
            receipt_path = layout.receipt_path(dependency)
            receipt_hash = file_sha256(receipt_path)
        else:
            receipt_hash = persisted_json_sha256(upstream_receipts[dependency])
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
        else file_sha256(layout.artifact_path(stage, "provider_calls.jsonl"))
        if specification.provider_roles
        else canonical_sha256(not_applicable("stage_has_no_provider_role"))
    )
    receipt = {
        "schema_version": STAGE_RECEIPT_SCHEMA_VERSION,
        "stage": stage.value,
        "stage_index": list(PipelineStage).index(stage) + 1,
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
    if stage == PipelineStage.DATASET_SPLITS:
        receipt["config_history_sha256"] = file_sha256(
            layout.config_history_path
        )
        receipt["build_provenance_sha256"] = file_sha256(
            layout.build_provenance_path
        )
        generation_manifest_path = layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            "generation_manifest.json",
        )
        generation_override = (artifact_overrides or {}).get(
            generation_manifest_path
        )
        receipt["generation_manifest_sha256"] = (
            hashlib.sha256(generation_override).hexdigest()
            if generation_override is not None
            else file_sha256(generation_manifest_path)
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


def _verify_release_evidence(
    layout: Any,
    state: PipelineState,
    *,
    require_persisted_state: bool,
    candidate_receipts: Mapping[PipelineStage, Mapping[str, Any]] | None,
    candidate_release_pointer: Mapping[str, Any] | None = None,
) -> None:
    try:
        config = _validate_released_control_state(
            layout,
            state,
            require_persisted_state=require_persisted_state,
        )
        journal_entries = (
            read_strict_jsonl_objects(layout.recovery_journal_path)
            if layout.recovery_journal_path.is_file()
            else []
        )
        journal = validate_recovery_journal(layout, journal_entries)
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
            candidate_release_pointer=candidate_release_pointer,
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


def _verify_prospective_legacy_adoption_candidate(
    layout: Any,
    state: PipelineState,
    receipts: Mapping[PipelineStage, Mapping[str, Any]],
    *,
    legacy_state: PipelineState | None = None,
    artifact_overrides: Mapping[Path, bytes] | None = None,
) -> None:
    """Verify one internal pre-WAL adoption target without public compatibility."""
    source_state = legacy_state or layout.load_state()
    config = layout.load_config()
    if not source_state.legacy_completed:
        raise ValueError("prospective adoption source is not a legacy completion")
    counts = {
        key: value
        for stage in PipelineStage
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
        stage.value: persisted_json_sha256(receipts[stage]) for stage in PipelineStage
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
    stage_eight_path = layout.receipt_path(PipelineStage.DATASET_SPLITS)
    stage_eight_sha256 = file_sha256(stage_eight_path)
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
    if persisted_json_sha256(receipts[PipelineStage.DATASET_SPLITS]) != (
        snapshot.stage_8_receipt_sha256
    ):
        raise ValueError("release pointer does not match Stage 8 receipt authority")
    if file_sha256(layout.build_provenance_path) != snapshot.build_provenance_sha256:
        raise ValueError("release pointer does not match build provenance")
    provenance = _read_json_object(layout.build_provenance_path)
    if {receipt.get("origin") for receipt in receipts.values()} == {"native"}:
        validate_build_provenance_call_ledgers(
            provenance,
            {
                stage.value: read_strict_jsonl_objects(
                    layout.artifact_path(stage, "provider_calls.jsonl")
                )
                for stage, specification in STAGE_SPECIFICATIONS.items()
                if specification.provider_roles
            },
        )
    else:
        validate_build_provenance(provenance)
    if provenance["identity_sha256"] != snapshot.build_fingerprint:
        raise ValueError("release build fingerprint is inconsistent")
    workspace_generation_manifest = layout.artifact_path(
        PipelineStage.DATASET_SPLITS,
        "generation_manifest.json",
    )
    if (
        file_sha256(workspace_generation_manifest)
        != snapshot.generation_manifest_sha256
    ):
        raise ValueError("workspace generation manifest is inconsistent")
    for split in LOGICAL_SPLITS:
        workspace_split = layout.artifact_path(
            PipelineStage.DATASET_SPLITS,
            f"{split}.jsonl",
        )
        if file_sha256(workspace_split) != file_sha256(snapshot.files[split]):
            raise ValueError("workspace and immutable generation splits differ")
    dataset_manifest = _read_json_object(
        layout.artifact_path(PipelineStage.DATASET_SPLITS, "dataset_manifest.json")
    )
    asset_manifest = _read_json_object(layout.manifest_path)
    if dataset_manifest != asset_manifest:
        raise ValueError("asset manifests differ")
    generation_directory = snapshot.generation_dir.relative_to(
        layout.tenants_root.parent
    ).as_posix()
    expected_published = {
        "directory": layout.published_datasets.relative_to(
            layout.tenant_root
        ).as_posix(),
        "release_pointer": layout.release_pointer_path.relative_to(
            layout.tenant_root
        ).as_posix(),
        "generation_id": snapshot.generation_id,
        "generation_manifest_sha256": snapshot.generation_manifest_sha256,
        "build_provenance_sha256": snapshot.build_provenance_sha256,
        "build_fingerprint": snapshot.build_fingerprint,
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
        "input_manifest_sha256": file_sha256(
            layout.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json")
        ),
        "raw_receipt_sha256": file_sha256(
            layout.receipt_path(PipelineStage.RAW_INPUTS)
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
        "stage_8_receipt_sha256": file_sha256(
            layout.receipt_path(PipelineStage.DATASET_SPLITS)
        ),
        "released_state_sha256": file_sha256(layout.state_path),
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
    for stage in PipelineStage:
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
    stage_state = _stage_state(state, stage)
    receipt_path = layout.receipt_path(stage)
    if not stage_state.receipt_sha256 or not receipt_path.is_file():
        raise _integrity(layout, stage, "receipt is missing")
    if file_sha256(receipt_path) != stage_state.receipt_sha256:
        raise _integrity(layout, stage, "receipt hash does not match state")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _integrity(layout, stage, "receipt is not valid JSON") from exc
    if not isinstance(receipt, Mapping):
        raise _integrity(layout, stage, "receipt is not a JSON object")
    if receipt.get("schema_version") != STAGE_RECEIPT_SCHEMA_VERSION:
        raise _integrity(layout, stage, "receipt schema is unsupported")
    expected_fields = set(_STAGE_RECEIPT_FIELDS)
    if stage == PipelineStage.DATASET_SPLITS:
        expected_fields.update(
            {
                "config_history_sha256",
                "build_provenance_sha256",
                "generation_manifest_sha256",
            }
        )
        try:
            history_sha256 = file_sha256(layout.config_history_path)
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
        if receipt.get("build_provenance_sha256") != file_sha256(
            layout.build_provenance_path
        ) or receipt.get("generation_manifest_sha256") != file_sha256(
            layout.artifact_path(
                PipelineStage.DATASET_SPLITS,
                "generation_manifest.json",
            )
        ):
            raise _integrity(
                layout,
                stage,
                "release provenance evidence changed",
            )
    if set(receipt) != expected_fields:
        raise _integrity(layout, stage, "receipt field inventory is invalid")
    if receipt.get("stage") != stage.value or receipt.get("stage_index") != (
        list(PipelineStage).index(stage) + 1
    ):
        raise _integrity(layout, stage, "receipt stage identity is inconsistent")

    specification = STAGE_SPECIFICATIONS[stage]
    artifact_profile = receipt.get("artifact_profile", "native")
    if artifact_profile not in {"native", "legacy"}:
        raise _integrity(layout, stage, "artifact profile is unsupported")
    if artifact_profile == "legacy" and receipt.get("origin") != "legacy_adoption":
        raise _integrity(layout, stage, "legacy artifacts lack adoption evidence")
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
    )
    outputs = receipt.get("outputs")
    if not isinstance(outputs, list):
        raise _integrity(layout, stage, "receipt output inventory is invalid")
    recorded_outputs = {
        (str(item.get("scope")), str(item.get("path")))
        for item in outputs
        if isinstance(item, Mapping) and item.get("required") is True
    }
    if recorded_outputs != expected_outputs:
        raise _integrity(layout, stage, "required output inventory is incomplete")
    for item in outputs:
        _verify_file_record(layout, stage, item)
    expected_provider_calls_sha256 = (
        file_sha256(layout.artifact_path(stage, "provider_calls.jsonl"))
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

    inputs = receipt.get("inputs")
    if not isinstance(inputs, list):
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
            for path in extension_receipt_input_paths(layout, stage)
        )
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise _integrity(layout, stage, "extension input evidence is inconsistent") from exc
    recorded_inputs = {
        (str(item.get("scope")), str(item.get("path")))
        for item in inputs
        if isinstance(item, Mapping)
    }
    if recorded_inputs != expected_inputs:
        raise _integrity(layout, stage, "direct input inventory is incomplete")
    for item in inputs:
        _verify_file_record(layout, stage, item)

    upstream = receipt.get("upstream_receipts")
    if not isinstance(upstream, list):
        raise _integrity(layout, stage, "upstream receipt inventory is invalid")
    expected_upstream = {
        dependency.value: file_sha256(layout.receipt_path(dependency))
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
    ):
        raise _integrity(layout, stage, "upstream receipt chain is inconsistent")

    counts = receipt.get("counts")
    if not isinstance(counts, Mapping):
        raise _integrity(layout, stage, "receipt counts are invalid")
    for key in STAGE_COUNT_KEYS[stage]:
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
        raw_state = _read_json_object(layout.state_path)
        if raw_state != state.to_dict():
            raise EvaluationAssetIntegrityError(
                layout.tenant_id,
                layout.asset_id,
                "the supplied state does not match persisted authority",
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
    expected_stages = [stage.value for stage in PipelineStage]
    if [stage.stage for stage in state.stages] != expected_stages or any(
        stage.status != "completed" or not stage.receipt_sha256
        for stage in state.stages
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "released stage authority is incomplete",
        )
    expected_counts = {
        key for keys in STAGE_COUNT_KEYS.values() for key in keys
    }
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
    raw_config = _read_json_object(layout.config_path)
    config = EvaluationAssetConfig.from_dict(raw_config)
    if raw_config != config.to_dict() or (
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
) -> list[str]:
    rows = read_strict_jsonl_objects(layout.config_history_path)
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
        lineage = _read_json_object(layout.lineage_path)
        if lineage.get("parent_asset_id") != parent_asset_id:
            raise ValueError("configuration history parent identity is inconsistent")
    elif layout.lineage_path.is_file():
        raise ValueError("extension configuration history origin is invalid")

    journal_rows = (
        read_strict_jsonl_objects(layout.recovery_journal_path)
        if layout.recovery_journal_path.is_file()
        else []
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
        earliest = min(
            (CONFIG_STAGE_DEPENDENCIES[field] for field in changes),
            key=list(PipelineStage).index,
        )
        if row.get("invalidated_from_stage") != earliest.value:
            raise ValueError("configuration history boundary is invalid")
        try:
            PipelineStage(str(row.get("resume_from_stage")))
        except ValueError as exc:
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
    for stage in PipelineStage:
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
    final_hash = receipts[PipelineStage.DATASET_SPLITS].get(
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
) -> dict[PipelineStage, dict[str, Any]]:
    """Authenticate an in-memory adoption chain before installing authority."""
    if set(receipts) != set(PipelineStage):
        raise ValueError("candidate receipt inventory is incomplete")
    config = layout.load_config()
    resolved_config = config.to_dict()
    verified: dict[PipelineStage, dict[str, Any]] = {}
    for stage in PipelineStage:
        receipt = dict(receipts[stage])
        specification = STAGE_SPECIFICATIONS[stage]
        expected_fields = set(_STAGE_RECEIPT_FIELDS)
        if stage == PipelineStage.DATASET_SPLITS:
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
            or receipt.get("stage_index") != list(PipelineStage).index(stage) + 1
            or receipt.get("origin") != "legacy_adoption"
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
            )
        if recorded_outputs != expected_outputs:
            raise ValueError("candidate receipt output inventory is incomplete")

        inputs = receipt.get("inputs")
        expected_inputs = {
            (
                "asset",
                layout.artifact_path(input_stage, name)
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
            for path in extension_receipt_input_paths(layout, stage)
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
            )
        if recorded_inputs != expected_inputs:
            raise ValueError("candidate receipt input inventory is incomplete")

        expected_upstream = [
            {
                "stage": dependency.value,
                "sha256": persisted_json_sha256(receipts[dependency]),
            }
            for dependency in STAGE_SPECIFICATIONS[stage].upstream_stages
        ]
        if receipt.get("upstream_receipts") != expected_upstream:
            raise ValueError("candidate receipt chain is invalid")
        counts = receipt.get("counts")
        if (
            not isinstance(counts, Mapping)
            or set(counts) != STAGE_COUNT_KEYS[stage]
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
        if stage == PipelineStage.DATASET_SPLITS and receipt.get(
            "config_history_sha256"
        ) != file_sha256(layout.config_history_path):
            raise ValueError("candidate configuration history evidence changed")
        if stage == PipelineStage.DATASET_SPLITS and (
            receipt.get("build_provenance_sha256")
            != file_sha256(layout.build_provenance_path)
            or receipt.get("generation_manifest_sha256")
            != _file_or_override_sha256(
                layout.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "generation_manifest.json",
                ),
                artifact_overrides,
            )
        ):
            raise ValueError("candidate release provenance evidence changed")
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
    stage_state = _stage_state(state, PipelineStage.RAW_INPUTS)
    receipt_path = layout.receipt_path(PipelineStage.RAW_INPUTS)
    try:
        events = read_strict_jsonl_objects(layout.events_path)
    except (OSError, UnicodeError, ValueError) as exc:
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot audit authority is malformed",
        ) from exc
    prior_stage_completion = any(
        event.get("event") == "stage_completed" for event in events
    )
    unclaimed_status_is_coherent = (
        stage_state.status == "pending"
        and state.status in {"draft", "queued", "running", "failed"}
    ) or (
        stage_state.status in {"running", "failed"}
        and state.status == stage_state.status
        and state.current_stage == PipelineStage.RAW_INPUTS.value
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
    if (
        stage_state.status != "completed"
        or not isinstance(stage_state.receipt_sha256, str)
        or not _SHA256.fullmatch(stage_state.receipt_sha256)
        or not receipt_path.is_file()
        or file_sha256(receipt_path) != stage_state.receipt_sha256
    ):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "immutable raw input snapshot receipt authority is inconsistent",
        )
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
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
        or receipt.get("stage") != PipelineStage.RAW_INPUTS.value
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
            _verify_file_record(layout, PipelineStage.RAW_INPUTS, item)
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
) -> set[tuple[str, str]]:
    expected = {
        (
            "asset",
            layout.artifact_path(stage, name).relative_to(layout.root).as_posix(),
        )
        for name in required_outputs
    }
    if include_native_evidence:
        expected.update(
            (
                "asset",
                layout.artifact_path(stage, name)
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
    if stage == PipelineStage.INTENT_CLUSTERING and layout.lineage_path.is_file():
        expected.add(
            (
                "asset",
                layout.artifact_path(stage, "cluster_lineage.jsonl")
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
            for path in extension_receipt_output_paths(layout, stage)
        )
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise _integrity(layout, stage, "extension output evidence is inconsistent") from exc
    return expected


def validate_legacy_release_candidate(
    layout: Any,
    state: PipelineState,
    config: EvaluationAssetConfig,
    *,
    prepared_release: Mapping[str, Any] | None = None,
    manifest_payload: Mapping[str, Any] | None = None,
) -> dict[str, int]:
    """Validate a pre-v2 completion and return independently derived counts."""
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
        for stage in PipelineStage:
            if _stage_state(state, stage).status != "completed":
                raise ValueError("legacy stage is incomplete")
            specification = STAGE_SPECIFICATIONS[stage]
            required_outputs, direct_inputs, artifact_profile = _stage_artifact_profile(
                layout,
                stage,
                allow_legacy=True,
            )
            artifact_profiles[stage] = artifact_profile
            paths = [
                layout.artifact_path(stage, name) for name in required_outputs
            ]
            paths.extend(
                layout.artifact_path(input_stage, name)
                for input_stage, name in direct_inputs
            )
            paths.extend(
                layout.root / name
                for name in (
                    ("asset_manifest.json",)
                    if stage == PipelineStage.DATASET_SPLITS
                    else specification.required_asset_outputs
                )
            )
            if stage == PipelineStage.DATASET_SPLITS:
                paths.extend(
                    layout.published_datasets / name
                    for name in _LEGACY_CATALOG_OUTPUTS
                )
            if stage == PipelineStage.INTENT_CLUSTERING and layout.lineage_path.is_file():
                paths.append(
                    layout.artifact_path(stage, "cluster_lineage.jsonl")
                )
            for path in paths:
                if not path.is_file():
                    raise ValueError("required artifact is missing")
                _validate_artifact_syntax(layout, stage, path)

        validate_legacy_stage_semantics(layout, artifact_profiles)

        input_manifest = _read_json_object(
            layout.artifact_path(PipelineStage.RAW_INPUTS, "input_manifest.json")
        )
        feedback_rows = _read_jsonl_objects(layout.feedback_path)
        unlabeled_rows = _read_jsonl_objects(layout.unlabeled_path)
        expected_inputs = {
            "labeled_feedback": (layout.feedback_path, len(feedback_rows)),
            "unlabeled": (layout.unlabeled_path, len(unlabeled_rows)),
        }
        manifest_inputs = input_manifest.get("inputs")
        if not isinstance(manifest_inputs, Mapping):
            raise ValueError("input manifest is incomplete")
        for name, (path, row_count) in expected_inputs.items():
            details = manifest_inputs.get(name)
            if not isinstance(details, Mapping) or (
                details.get("file") != path.name
                or details.get("rows") != row_count
                or details.get("sha256") != file_sha256(path)
            ):
                raise ValueError("input manifest is inconsistent")

        dataset_manifest = (
            dict(manifest_payload)
            if manifest_payload is not None
            else _read_json_object(
                layout.artifact_path(
                    PipelineStage.DATASET_SPLITS,
                    "dataset_manifest.json",
                )
            )
        )
        asset_manifest = (
            dict(manifest_payload)
            if manifest_payload is not None
            else _read_json_object(layout.manifest_path)
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
                    layout.artifact_path(PipelineStage.DATASET_SPLITS, name)
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
            stage_path = layout.artifact_path(PipelineStage.DATASET_SPLITS, name)
            catalog_path = layout.published_datasets / name
            if file_sha256(stage_path) != file_sha256(catalog_path):
                raise ValueError("published dataset copy is inconsistent")

        if layout.lineage_path.is_file():
            lineage = _read_json_object(layout.lineage_path)
            reuse = _read_json_object(layout.reuse_manifest_path)
            if dataset_manifest.get("lineage") != lineage or not reuse:
                raise ValueError("extension lineage is inconsistent")
        return _derive_legacy_counts(layout, split_counts)
    except EvaluationAssetLegacyError:
        raise
    except (KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
        raise _legacy_invalid(layout) from exc


def _stage_artifact_profile(
    layout: Any,
    stage: PipelineStage,
    *,
    allow_legacy: bool,
) -> tuple[
    tuple[str, ...],
    tuple[tuple[PipelineStage, str], ...],
    str,
]:
    specification = STAGE_SPECIFICATIONS[stage]
    if not allow_legacy:
        return specification.required_outputs, specification.direct_inputs, "native"
    if specification.legacy_required_outputs:
        native_complete = all(
            layout.artifact_path(stage, name).is_file()
            for name in specification.required_outputs
        )
        legacy_complete = all(
            layout.artifact_path(stage, name).is_file()
            for name in specification.legacy_required_outputs
        )
        if not native_complete and legacy_complete:
            return (
                specification.legacy_required_outputs,
                specification.direct_inputs,
                "legacy",
            )
    if specification.legacy_direct_inputs:
        native_complete = all(
            layout.artifact_path(input_stage, name).is_file()
            for input_stage, name in specification.direct_inputs
        )
        legacy_complete = all(
            layout.artifact_path(input_stage, name).is_file()
            for input_stage, name in specification.legacy_direct_inputs
        )
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


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON document is not an object")
    return value


def _read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("JSONL row is not an object")
        rows.append(value)
    return rows


def _derive_legacy_counts(
    layout: Any,
    split_counts: Mapping[str, int],
) -> dict[str, int]:
    def rows(stage: PipelineStage, name: str) -> list[dict[str, Any]]:
        return _read_jsonl_objects(layout.artifact_path(stage, name))

    feedback = rows(PipelineStage.RAW_INPUTS, "labeled_feedback.jsonl")
    unlabeled = rows(PipelineStage.RAW_INPUTS, "unlabeled.jsonl")
    normalized = rows(PipelineStage.PREPARED_INPUTS, "normalized_feedback.jsonl")
    intents = rows(PipelineStage.PREPARED_INPUTS, "intent_records.jsonl")
    guidelines = (
        rows(PipelineStage.RUBRIC_EXTRACTION, "evaluation_guidelines.jsonl")
        if layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "evaluation_guidelines.jsonl",
        ).is_file()
        else []
    )
    evidence = (
        rows(PipelineStage.RUBRIC_EXTRACTION, "feedback_evidence.jsonl")
        if layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "feedback_evidence.jsonl",
        ).is_file()
        else []
    )
    candidates = (
        rows(PipelineStage.RUBRIC_EXTRACTION, "candidate_guidelines.jsonl")
        if layout.artifact_path(
            PipelineStage.RUBRIC_EXTRACTION,
            "candidate_guidelines.jsonl",
        ).is_file()
        else []
    )
    trusted = rows(PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl")
    clusters = rows(PipelineStage.INTENT_CLUSTERING, "intent_inventory.jsonl")
    matches = rows(PipelineStage.COVERAGE_DECISIONS, "intent_matches.jsonl")
    allowed_statuses = {
        "matched_trusted_intent",
        "needs_more_trusted_examples",
        "missing_or_weak_labels",
    }
    if any(row.get("status") not in allowed_statuses for row in matches):
        raise ValueError("coverage status is unsupported")
    queue = rows(
        PipelineStage.COVERAGE_DECISIONS,
        "review_queue/labeling_queue.jsonl",
    )
    inferred = rows(PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl")
    missing = rows(
        PipelineStage.LABEL_INFERENCE,
        "missing_labeled_feedback_clusters.jsonl",
    )
    synthetic = rows(PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl")
    rejected = rows(
        PipelineStage.SYNTHETIC_COVERAGE,
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
) -> None:
    if not isinstance(item, Mapping):
        raise _integrity(layout, stage, "artifact inventory row is invalid")
    scope = item.get("scope")
    if scope not in {"asset", "tenant"}:
        raise _integrity(layout, stage, "artifact scope is invalid")
    relative = Path(str(item.get("path") or ""))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise _integrity(layout, stage, "artifact path is unsafe")
    base = layout.root if scope == "asset" else layout.tenant_root
    path = base / relative
    override = (artifact_overrides or {}).get(path)
    if override is not None:
        if len(override) != item.get("bytes") or hashlib.sha256(
            override
        ).hexdigest() != item.get("sha256"):
            raise _integrity(
                layout,
                stage,
                "a required artifact hash is inconsistent",
            )
        _validate_artifact_bytes(layout, stage, path, override)
        return
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise _integrity(layout, stage, "a required artifact is missing") from exc
    resolved_base = base.resolve()
    if resolved_base not in resolved.parents:
        raise _integrity(layout, stage, "artifact path escapes its allowed scope")
    if not resolved.is_file():
        raise _integrity(layout, stage, "a required artifact is missing")
    if resolved.stat().st_size != item.get("bytes") or file_sha256(resolved) != item.get(
        "sha256"
    ):
        raise _integrity(layout, stage, "a required artifact hash is inconsistent")
    _validate_artifact_syntax(layout, stage, resolved)


def _validate_artifact_syntax(layout: Any, stage: PipelineStage, path: Path) -> None:
    try:
        if path.suffix == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, Mapping):
                raise ValueError("not an object")
        elif path.suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip() and not isinstance(json.loads(line), Mapping):
                    raise ValueError("row is not an object")
        elif path.suffix == ".md" and not path.read_text(encoding="utf-8").strip():
            raise ValueError("empty markdown")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise _integrity(layout, stage, "a required artifact is malformed") from exc


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
    path: Path,
    overrides: Mapping[Path, bytes] | None,
) -> str:
    override = (overrides or {}).get(path)
    return (
        hashlib.sha256(override).hexdigest()
        if override is not None
        else file_sha256(path)
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
) -> dict[str, Any]:
    override = (artifact_overrides or {}).get(path)
    if override is None and not path.is_file():
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "a required stage artifact is missing",
        )
    base = layout.root if scope == "asset" else layout.tenant_root
    record = {
        "path": path.relative_to(base).as_posix(),
        "scope": scope,
        "sha256": (
            hashlib.sha256(override).hexdigest()
            if override is not None
            else file_sha256(path)
        ),
        "bytes": len(override) if override is not None else path.stat().st_size,
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
