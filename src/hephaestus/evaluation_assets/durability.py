# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Durability contracts shared by evaluation-asset mutation paths."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STAGE_COUNT_KEYS,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
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


_SPLIT_OUTPUTS = tuple(
    f"{split}{suffix}.jsonl"
    for split in ("train", "validation", "test")
    for suffix in ("_trusted", "_inferred", "_synthetic", "")
) + ("regression_trusted.jsonl", "triage_hold.jsonl")

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
        required_outputs=_SPLIT_OUTPUTS + ("dataset_manifest.json",),
        direct_inputs=(
            (PipelineStage.RAW_INPUTS, "input_manifest.json"),
            (PipelineStage.RUBRIC_EXTRACTION, "trusted_cases.jsonl"),
            (PipelineStage.LABEL_INFERENCE, "inferred_cases.jsonl"),
            (PipelineStage.SYNTHETIC_COVERAGE, "synthetic_cases.jsonl"),
        ),
        upstream_stages=tuple(list(PipelineStage)[:7]),
        config_fields=("split_seed",),
        required_asset_outputs=("asset_manifest.json",),
        required_catalog_outputs=(
            "train.jsonl",
            "validation.jsonl",
            "test.jsonl",
            "regression_trusted.jsonl",
        ),
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
    serialized = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
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
    origin: str = "native",
    historical_unavailable: bool = False,
    upstream_receipts: Mapping[PipelineStage, Mapping[str, Any]] | None = None,
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
        )
        for input_stage, name in direct_inputs
    ]
    outputs = [
        _file_record(
            layout,
            layout.artifact_path(stage, name),
            scope="asset",
            required=True,
        )
        for name in required_outputs
    ]
    if stage == PipelineStage.INTENT_CLUSTERING and layout.lineage_path.is_file():
        outputs.append(
            _file_record(
                layout,
                layout.artifact_path(stage, "cluster_lineage.jsonl"),
                scope="asset",
                required=True,
            )
        )
    outputs.extend(
        _file_record(
            layout,
            layout.root / name,
            scope="asset",
            required=True,
        )
        for name in specification.required_asset_outputs
    )
    outputs.extend(
        _file_record(
            layout,
            layout.published_datasets / name,
            scope="tenant",
            required=True,
        )
        for name in specification.required_catalog_outputs
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
        else _provider_identity(config, specification.provider_roles)
    )
    code = unavailable if historical_unavailable else _code_identity()
    return {
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
        "provider_identity_sha256": canonical_sha256(providers),
        "provider_calls_sha256": canonical_sha256(unavailable),
        "code": code,
        "code_sha256": canonical_sha256(code),
        "counts": {str(key): int(value) for key, value in counts.items()},
    }


def current_dependency_hashes(
    stage: PipelineStage,
    config: EvaluationAssetConfig,
    prompt_values: Mapping[str, str],
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
            _provider_identity(config, specification.provider_roles)
        ),
        "code_sha256": canonical_sha256(code),
    }


def verify_released_asset(layout: Any, state: PipelineState) -> None:
    """Verify a released receipt/artifact chain without current-code equality."""
    if state.status != "released":
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "the persisted lifecycle is not released",
        )
    verify_receipt_chain(layout, state)


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
    return {
        "stage_8_receipt_sha256": file_sha256(
            layout.receipt_path(PipelineStage.DATASET_SPLITS)
        ),
        "released_state_sha256": file_sha256(layout.state_path),
        "source_lineage_sha256": canonical_sha256(lineage_payload),
    }


def verify_receipt_chain(layout: Any, state: PipelineState) -> None:
    """Verify all historical receipts without comparing the current checkout."""
    config = layout.load_config()
    for stage in PipelineStage:
        verify_stage_receipt(
            layout,
            state,
            stage,
            config,
            prompt_values={},
            compare_current_dependencies=False,
        )


def mutable_rebuild_boundary(
    layout: Any,
    state: PipelineState,
    config: EvaluationAssetConfig,
    prompt_values_by_stage: Mapping[PipelineStage, Mapping[str, str]],
) -> PipelineStage | None:
    """Return the first incomplete or invalid mutable checkpoint boundary."""
    _verify_raw_snapshot_floor(layout, state)
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
        if key not in counts or int(counts[key]) != state.counts.get(key):
            raise _integrity(layout, stage, "receipt counts do not match state")

    if compare_current_dependencies:
        expected_dependencies = current_dependency_hashes(
            stage,
            config,
            prompt_values,
        )
        if any(
            receipt.get(key) != expected_value
            for key, expected_value in expected_dependencies.items()
        ):
            raise _integrity(layout, stage, "mutable dependencies changed")
    return dict(receipt)


def _verify_raw_snapshot_floor(layout: Any, state: PipelineState) -> None:
    raw_paths = (layout.feedback_path, layout.unlabeled_path)
    if not all(path.is_file() for path in raw_paths):
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "an immutable raw input snapshot is missing",
        )
    stage_state = _stage_state(state, PipelineStage.RAW_INPUTS)
    receipt_path = layout.receipt_path(PipelineStage.RAW_INPUTS)
    if not stage_state.receipt_sha256 or not receipt_path.is_file():
        return
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
    inputs = receipt.get("inputs") if isinstance(receipt, Mapping) else None
    if not isinstance(inputs, list):
        return
    raw_relative_paths = {
        path.relative_to(layout.root).as_posix() for path in raw_paths
    }
    records = {
        str(item.get("path")): item
        for item in inputs
        if isinstance(item, Mapping)
        and item.get("scope") == "asset"
        and item.get("path") in raw_relative_paths
    }
    if set(records) != raw_relative_paths:
        return
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
) -> set[tuple[str, str]]:
    expected = {
        (
            "asset",
            layout.artifact_path(stage, name).relative_to(layout.root).as_posix(),
        )
        for name in required_outputs
    }
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
    return expected


def validate_legacy_release_candidate(
    layout: Any,
    state: PipelineState,
    config: EvaluationAssetConfig,
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
        for stage in PipelineStage:
            if _stage_state(state, stage).status != "completed":
                raise ValueError("legacy stage is incomplete")
            specification = STAGE_SPECIFICATIONS[stage]
            required_outputs, direct_inputs, _ = _stage_artifact_profile(
                layout,
                stage,
                allow_legacy=True,
            )
            paths = [
                layout.artifact_path(stage, name) for name in required_outputs
            ]
            paths.extend(
                layout.artifact_path(input_stage, name)
                for input_stage, name in direct_inputs
            )
            paths.extend(layout.root / name for name in specification.required_asset_outputs)
            paths.extend(
                layout.published_datasets / name
                for name in specification.required_catalog_outputs
            )
            if stage == PipelineStage.INTENT_CLUSTERING and layout.lineage_path.is_file():
                paths.append(
                    layout.artifact_path(stage, "cluster_lineage.jsonl")
                )
            for path in paths:
                if not path.is_file():
                    raise ValueError("required artifact is missing")
                _validate_artifact_syntax(layout, stage, path)

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

        dataset_manifest = _read_json_object(
            layout.artifact_path(PipelineStage.DATASET_SPLITS, "dataset_manifest.json")
        )
        asset_manifest = _read_json_object(layout.manifest_path)
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
        stage_eight_specification = STAGE_SPECIFICATIONS[
            PipelineStage.DATASET_SPLITS
        ]
        expected_catalog = {
            Path(name).stem: (layout.published_datasets / name)
            .relative_to(layout.tenant_root)
            .as_posix()
            for name in stage_eight_specification.required_catalog_outputs
        }
        expected_catalog_directory = layout.published_datasets.relative_to(
            layout.tenant_root
        ).as_posix()
        if not isinstance(published, Mapping) or (
            published.get("directory") != expected_catalog_directory
            or published.get("files") != expected_catalog
        ):
            raise ValueError("published dataset manifest is inconsistent")
        for name in stage_eight_specification.required_catalog_outputs:
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
        lineage = _read_json_object(layout.lineage_path)
        reuse = _read_json_object(layout.reuse_manifest_path)
        if lineage.get("asset_id") != layout.asset_id:
            raise ValueError("lineage asset identity is inconsistent")
        parent_asset_id = lineage.get("parent_asset_id")
        if not isinstance(parent_asset_id, str) or not parent_asset_id:
            raise ValueError("lineage parent identity is missing")
        if reuse.get("parent_asset_id") != parent_asset_id:
            raise ValueError("reuse parent identity is inconsistent")
        snapshot = reuse.get("parent_snapshot")
        if not isinstance(snapshot, Mapping):
            raise ValueError("parent snapshot inventory is missing")
        expected_snapshot_path = layout.parent_snapshot.relative_to(
            layout.root
        ).as_posix()
        if snapshot.get("path") != expected_snapshot_path:
            raise ValueError("parent snapshot path is inconsistent")
        artifacts = snapshot.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError("parent snapshot inventory is empty")
        seen: set[str] = set()
        for item in artifacts:
            if not isinstance(item, Mapping):
                raise ValueError("parent snapshot row is invalid")
            relative = Path(str(item.get("file") or ""))
            if (
                relative.is_absolute()
                or len(relative.parts) != 1
                or relative.name in seen
            ):
                raise ValueError("parent snapshot path is unsafe")
            seen.add(relative.name)
            path = layout.parent_snapshot / relative
            if not path.is_file() or item.get("sha256") != file_sha256(path):
                raise ValueError("parent snapshot hash is inconsistent")
        manifest = _read_json_object(layout.manifest_path)
        if manifest.get("lineage") != lineage:
            raise ValueError("asset manifest lineage is inconsistent")
        return lineage, reuse
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
) -> dict[str, Any]:
    if not path.is_file():
        raise EvaluationAssetIntegrityError(
            layout.tenant_id,
            layout.asset_id,
            "a required stage artifact is missing",
        )
    base = layout.root if scope == "asset" else layout.tenant_root
    record = {
        "path": path.relative_to(base).as_posix(),
        "scope": scope,
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
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
    repository_root = Path(__file__).resolve().parents[3]
    source_paths = sorted(
        (repository_root / "src" / "hephaestus" / "evaluation_assets").glob("*.py")
    )
    source_paths.extend(
        repository_root / "src" / "hephaestus" / relative
        for relative in (
            "artifact_io.py",
            "datasets/evaluation_assets.py",
            "datasets/intent_assets.py",
            "datasets/embedding_providers.py",
            "datasets/rubric_providers.py",
        )
    )
    digest = hashlib.sha256()
    members = []
    for path in sorted(source_paths):
        relative = path.relative_to(repository_root).as_posix()
        members.append(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {
        "fingerprint": digest.hexdigest(),
        "git_commit": "unavailable",
        "members": members,
    }

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
