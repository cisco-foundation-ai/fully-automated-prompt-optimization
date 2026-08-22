# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Compatibility tests for the third evaluation-asset persistence profile."""

from __future__ import annotations

import ast
import inspect
import sys
import types
from typing import Any

import pytest

from src.hephaestus.evaluation_assets import durability as durability_module
from src.hephaestus.evaluation_assets import journal_transitions, journal_validation, lineage_validation
from src.hephaestus.evaluation_assets import provenance as provenance_module
from src.hephaestus.evaluation_assets.models import (
    CONFIG_STAGE_DEPENDENCIES,
    STATE_SCHEMA_VERSION,
    EvaluationAssetConfig,
    PipelineStage,
    PipelineState,
)

_JOURNAL_V2 = "fapo-recovery-journal-v2"
_JOURNAL_V3 = "fapo-recovery-journal-v3"
_RECEIPT_V2 = "fapo-stage-receipt-v2"
_RECEIPT_V3 = "fapo-stage-receipt-v3"


def _completed_state(config: EvaluationAssetConfig) -> dict[str, Any]:
    state = PipelineState.new(config, "2026-08-21T12:00:00+00:00")
    state.status = "running"
    state.current_stage = None
    for stage in state.stages:
        stage.status = "completed"
        stage.started_at = "2026-08-21T12:00:00+00:00"
        stage.completed_at = "2026-08-21T12:00:01+00:00"
        stage.receipt_sha256 = "a" * 64
    return state.to_dict()


def _schema_row(schema: str, operation_id: str, phase: str) -> dict[str, str]:
    return {
        "schema_version": schema,
        "operation_id": operation_id,
        "phase": phase,
    }


def test_state_profile_stays_v2_while_split_seed_moves_to_stage_two() -> None:
    """Keep the state wire shape stable while moving the live dependency boundary."""
    assert STATE_SCHEMA_VERSION == "fapo-evaluation-asset-state-v2"
    assert CONFIG_STAGE_DEPENDENCIES["split_seed"] is PipelineStage.PREPARED_INPUTS


def test_journal_profiles_freeze_v2_and_bind_v3_split_seed_to_stage_two() -> None:
    """Select revision semantics from each journal row's persisted schema."""
    assert journal_transitions.JOURNAL_SCHEMA_VERSION == _JOURNAL_V3
    v2 = journal_transitions.journal_transition_profile(_JOURNAL_V2)
    v3 = journal_transitions.journal_transition_profile(_JOURNAL_V3)

    assert v2.config_stage_dependencies["split_seed"] == "dataset_splits"
    assert v3.config_stage_dependencies["split_seed"] == "prepared_inputs"
    assert v2.stage_values == v3.stage_values
    assert v2.stage_count_keys == v3.stage_count_keys
    with pytest.raises(ValueError, match="journal schema is unsupported"):
        journal_transitions.journal_transition_profile("fapo-recovery-journal-v4")


def test_revision_derivation_uses_the_explicit_journal_profile() -> None:
    """Re-derive old and new split-seed revisions at their original boundaries."""
    config = EvaluationAssetConfig(tenant_id="profile-test", asset_id="v1")
    before = _completed_state(config)
    common = {
        "before_config": config.to_dict(),
        "before_state": before,
        "updates": {"split_seed": 73},
        "operation_id": "1" * 32,
        "prepared_at": "2026-08-21T12:01:00+00:00",
        "revision": 2,
    }

    v2 = journal_transitions.derive_revision_plan(
        **common,
        journal_schema_version=_JOURNAL_V2,
    )
    v3 = journal_transitions.derive_revision_plan(
        **common,
        journal_schema_version=_JOURNAL_V3,
    )

    assert v2["result"]["invalidated_from_stage"] == "dataset_splits"
    assert v2["invalidated_stages"] == ["dataset_splits"]
    assert v3["result"]["invalidated_from_stage"] == "prepared_inputs"
    assert v3["invalidated_stages"][0] == "prepared_inputs"


def test_journal_schema_sequence_allows_only_a_v2_prefix_then_v3() -> None:
    """Allow in-place upgrades without allowing a journal profile downgrade."""
    first = "1" * 32
    second = "2" * 32
    rows = [
        _schema_row(_JOURNAL_V2, first, "prepared"),
        _schema_row(_JOURNAL_V2, first, "committed"),
        _schema_row(_JOURNAL_V3, second, "prepared"),
        _schema_row(_JOURNAL_V3, second, "committed"),
    ]
    assert journal_validation._validate_journal_schema_sequence(rows) == (
        _JOURNAL_V2,
        _JOURNAL_V3,
    )

    mismatched = list(rows[:1]) + [_schema_row(_JOURNAL_V3, first, "committed")]
    with pytest.raises(ValueError, match="prepare and commit schemas differ"):
        journal_validation._validate_journal_schema_sequence(mismatched)

    downgraded = rows[2:] + rows[:2]
    with pytest.raises(ValueError, match="journal schema sequence is not monotonic"):
        journal_validation._validate_journal_schema_sequence(downgraded)


def test_receipt_v3_specs_freeze_v2_and_bind_new_stage_authority() -> None:
    """Keep old receipt inventories exact while declaring Task 5-7 authority."""
    assert durability_module.STAGE_RECEIPT_SCHEMA_VERSION == _RECEIPT_V3
    old_stage_two = durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V2,
        PipelineStage.PREPARED_INPUTS,
    )
    stage_two = durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V3,
        PipelineStage.PREPARED_INPUTS,
    )
    stage_three = durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V3,
        PipelineStage.RUBRIC_EXTRACTION,
    )
    stage_six = durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V3,
        PipelineStage.LABEL_INFERENCE,
    )
    stage_seven = durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V3,
        PipelineStage.SYNTHETIC_COVERAGE,
    )
    stage_eight = durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V3,
        PipelineStage.DATASET_SPLITS,
    )

    assert old_stage_two.required_outputs == (
        "normalized_feedback.jsonl",
        "intent_records.jsonl",
    )
    assert "split_seed" not in old_stage_two.config_fields
    assert {
        "trusted_split_plan.jsonl",
        "feedback_eligibility.jsonl",
    } <= set(stage_two.required_outputs)
    assert stage_two.config_fields == ("split_seed",)
    assert {
        "protected_feedback_evidence.jsonl",
        "protected_candidate_guidelines.jsonl",
        "protected_evaluation_guidelines.jsonl",
        "protected_trusted_cases.jsonl",
    } <= set(stage_three.required_outputs)
    assert {
        "trusted_split_plan.jsonl",
        "feedback_eligibility.jsonl",
    } <= {name for _, name in stage_three.direct_inputs}
    assert {
        "inference_dependencies.jsonl",
        "held_inference_outputs.jsonl",
    } <= set(stage_six.required_outputs)
    assert {
        "synthetic_dependencies.jsonl",
        "derived_review_items.jsonl",
        "duplicate_families.jsonl",
        "held_derived_cases.jsonl",
    } <= set(stage_seven.required_outputs)
    assert stage_eight.required_asset_inputs == (
        "reviews/decisions.jsonl",
        "reviews/finalizations.jsonl",
    )
    assert "review_snapshot.json" in stage_eight.required_outputs
    assert "split_seed" not in stage_eight.config_fields
    assert {
        "trusted_split_plan.jsonl",
        "trusted_cases.jsonl",
        "protected_trusted_cases.jsonl",
        "inference_dependencies.jsonl",
        "held_inference_outputs.jsonl",
        "synthetic_dependencies.jsonl",
        "derived_review_items.jsonl",
        "duplicate_families.jsonl",
        "held_derived_cases.jsonl",
    } <= {name for _, name in stage_eight.direct_inputs}


def test_stage_three_replay_text_profile_is_explicit_by_receipt_generation() -> None:
    """Replay old releases historically while validating v3 native source text."""
    selector = durability_module.stage_three_text_profile_for_receipt_schema

    assert selector("fapo-stage-receipt-v1") == "historical_v1"
    assert selector(_RECEIPT_V2) == "historical_v1"
    assert selector(_RECEIPT_V3) == "current"
    assert selector(_RECEIPT_V3, origin="legacy_adoption") == "historical_v1"
    with pytest.raises(ValueError, match="receipt schema is unsupported"):
        selector("fapo-stage-receipt-v4")


def test_historical_v3_receipt_profile_ignores_live_v4_registry_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A released v3 receipt remains bound to its frozen v3 stage inventory."""
    frozen = durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V3,
        PipelineStage.DATASET_SPLITS,
    )
    monkeypatch.setattr(
        durability_module,
        "STAGE_RECEIPT_SCHEMA_VERSION",
        "fapo-stage-receipt-v4",
    )
    monkeypatch.setattr(durability_module, "STAGE_SPECIFICATIONS", {})

    assert durability_module.stage_specification_for_receipt_schema(
        _RECEIPT_V3,
        PipelineStage.DATASET_SPLITS,
    ) == frozen
    assert durability_module.stage_three_text_profile_for_receipt_schema(
        _RECEIPT_V3
    ) == "current"


def test_historical_receipt_fields_survive_live_v4_source_evolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A future writer field cannot redefine persisted v2/v3 receipt schemas."""
    historical_fields = frozenset(
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

    class FutureReceiptWriter(ast.NodeTransformer):
        def visit_Assign(self, node: ast.Assign) -> ast.Assign:
            names = {
                target.id for target in node.targets if isinstance(target, ast.Name)
            }
            if "STAGE_RECEIPT_SCHEMA_VERSION" in names:
                node.value = ast.copy_location(
                    ast.Constant(value="fapo-stage-receipt-v4"),
                    node.value,
                )
            elif "_STAGE_RECEIPT_FIELDS" in names:
                node.value = ast.copy_location(
                    ast.BinOp(
                        left=node.value,
                        op=ast.BitOr(),
                        right=ast.Set(elts=[ast.Constant(value="future_field")]),
                    ),
                    node.value,
                )
            return node

    source = inspect.getsource(durability_module)
    tree = FutureReceiptWriter().visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    module_name = "_fapo_test_future_durability"
    future = types.ModuleType(module_name)
    future.__file__ = str(inspect.getsourcefile(durability_module))
    monkeypatch.setitem(sys.modules, module_name, future)

    exec(compile(tree, future.__file__, "exec"), future.__dict__)

    assert future.STAGE_RECEIPT_SCHEMA_VERSION == "fapo-stage-receipt-v4"
    assert future._STAGE_RECEIPT_FIELDS == historical_fields | {"future_field"}
    assert future._HISTORICAL_STAGE_RECEIPT_FIELDS_V2 == historical_fields
    assert future._HISTORICAL_STAGE_RECEIPT_FIELDS_V3 == historical_fields


def test_provenance_v3_selectors_preserve_v2_and_provider_call_v2() -> None:
    """Use v3 build profiles without changing the provider-call row schema."""
    assert provenance_module.PROVIDER_CALL_SCHEMA_VERSION == "fapo-provider-call-v2"
    assert provenance_module.STAGE_PROVENANCE_SCHEMA_VERSION == ("fapo-stage-provenance-v3")
    assert provenance_module.BUILD_PROVENANCE_SCHEMA_VERSION == ("fapo-evaluation-build-provenance-v3")
    assert provenance_module.BUILD_IDENTITY_SCHEMA_VERSION == ("fapo-evaluation-build-identity-v3")

    v2_stage = {"schema_version": "fapo-stage-provenance-v2"}
    v3_stage = {"schema_version": provenance_module.STAGE_PROVENANCE_SCHEMA_VERSION}
    assert provenance_module.historical_stage_provenance_profile(v2_stage) == (
        provenance_module.HISTORICAL_PROVENANCE_PROFILE_V2
    )
    assert provenance_module.historical_stage_provenance_profile(v3_stage) == (
        provenance_module.HISTORICAL_PROVENANCE_PROFILE_V3
    )

    v3_build = {
        "schema_version": provenance_module.BUILD_PROVENANCE_SCHEMA_VERSION,
        "identity": {
            "schema_version": provenance_module.BUILD_IDENTITY_SCHEMA_VERSION,
        },
    }
    profile = provenance_module.historical_build_provenance_profile(v3_build)
    assert profile == provenance_module.HISTORICAL_PROVENANCE_PROFILE_V3
    assert provenance_module.historical_provider_call_stages(profile) == (
        "rubric_extraction",
        "intent_clustering",
        "coverage_decisions",
        "label_inference",
        "synthetic_coverage",
    )


def test_historical_v3_provenance_registries_are_source_literals() -> None:
    """Prevent future live-registry edits from redefining persisted v3 evidence."""
    names = {
        "_HISTORICAL_SOURCE_FIXED_MEMBERS_V3",
        "_HISTORICAL_PROVIDER_STAGE_ROLES_V3",
        "_HISTORICAL_STAGE_PROMPT_NAMES_V3",
        "_HISTORICAL_PROMPT_REVISIONS_V3",
    }
    assignments = {
        target.id: node.value
        for node in ast.parse(inspect.getsource(provenance_module)).body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id in names
    }

    assert set(assignments) == names
    for value in assignments.values():
        assert isinstance(value, ast.Tuple)
        assert not any(
            isinstance(node, (ast.Name, ast.Call, ast.Attribute, ast.Subscript))
            for node in ast.walk(value)
        )


def test_provenance_v3_freezes_acquisition_and_source_semantics() -> None:
    """Bind the Task 5-7 modules and non-probability queue claim only in v3."""
    config = EvaluationAssetConfig(tenant_id="profile-test").to_dict()
    current = provenance_module.build_algorithm_inventory(config, extension=False)
    frozen_v2 = provenance_module.historical_algorithm_inventory_v2(
        config,
        extension=False,
    )

    assert current["coverage_decisions"]["queue_acquisition"] == {
        "purpose": "correctness_label_acquisition",
        "method": "deterministic_centroid_nearest",
        "sampling_semantics": "non_probability",
    }
    assert "queue_acquisition" not in frozen_v2["coverage_decisions"]
    assert "src/hephaestus/evaluation_assets/dependencies.py" in (provenance_module.SOURCE_FIXED_MEMBERS)
    assert "src/hephaestus/evaluation_assets/dependencies.py" not in (
        provenance_module._HISTORICAL_SOURCE_FIXED_MEMBERS_V2
    )


@pytest.mark.parametrize("extension", [False, True], ids=["native", "extension"])
def test_provenance_v3_names_pr3_generation_semantics(
    extension: bool,
) -> None:
    """Describe PR3 isolation, dependencies, review, and publication exactly."""
    config = EvaluationAssetConfig(tenant_id="profile-test").to_dict()
    current = provenance_module.build_algorithm_inventory(
        config,
        extension=extension,
    )

    assert current["prepared_inputs"] == {
        "algorithm": "fapo-evaluation-canonical-preparation-v1",
        "trusted_split_assignment": "connected-model-context-stable-hash-v1",
        "correctness_evidence_eligibility": (
            "deterministic-explicit-correctness-evidence-v1"
        ),
    }
    assert current["rubric_extraction"] == {
        "algorithm": "fapo-evaluation-guideline-v1",
        "reusable_scope": "eligible_train_only",
        "protected_scope": "split_group_group_route_local",
    }
    assert current["label_inference"] == {
        "algorithm": "trusted-guideline-inference-v1",
        "dependency": "stage-six-dependency-v1",
        "scoreability": "scoreable-rubric-or-hold-v1",
        "extension_reuse": (
            {"authorization": "exact-stage-six-dependency-match-v1"}
            if extension
            else {
                "status": "not_applicable",
                "reason": "native_asset_has_no_parent",
            }
        ),
    }
    assert current["synthetic_coverage"] == {
        "algorithm": "fapo-synthetic-filter-v1",
        "dependency": "stage-seven-dependency-v1",
        "scoreability": "scoreable-case-or-hold-v1",
        "review_binding": (
            "complete-case-dependency-provenance-review-fingerprint-v1"
        ),
        "duplicate_families": "exact-model-context-connected-family-v1",
        "decision_reuse": "exact-fingerprint-decision-inheritance-v1",
        "extension_reuse": (
            {
                "authorization": (
                    "exact-final-stage-seven-dependency-match-v1"
                ),
                "invalidation": "canonical-order-fixed-point-v1",
            }
            if extension
            else {
                "status": "not_applicable",
                "reason": "native_asset_has_no_parent",
            }
        ),
    }
    assert current["dataset_splits"] == {
        "algorithm": (
            "approved-exact-family-early-split-stable-extension-v1"
            if extension
            else "approved-exact-family-early-split-v1"
        ),
        "trusted_split_assignment": "connected-model-context-stable-hash-v1",
        "regression_selection": "deterministic-early-connected-group-hash-v1",
        "derived_inclusion": "approved-exact-fingerprint-only-v1",
        "hold_policy": "exclude-held-cases-and-families-v1",
        "regression_fraction": 0.2,
    }
    assert provenance_module.historical_algorithm_inventory_v3(
        config,
        extension=extension,
    ) == current

    frozen_v1 = provenance_module.historical_algorithm_inventory_v1(
        config,
        extension=extension,
    )
    assert frozen_v1["prepared_inputs"] == (
        "fapo-evaluation-canonical-preparation-v1"
    )
    assert frozen_v1["rubric_extraction"] == "fapo-evaluation-guideline-v1"
    assert frozen_v1["label_inference"] == "trusted-guideline-inference-v1"
    assert frozen_v1["synthetic_coverage"] == "fapo-synthetic-filter-v1"
    assert frozen_v1["dataset_splits"]["algorithm"] == (
        "group-safe-stable-fraction-extension-v1"
        if extension
        else "group-safe-random-v1"
    )
    assert provenance_module.historical_algorithm_inventory_v2(
        config,
        extension=extension,
    ) == frozen_v1


def test_historical_v3_algorithm_profile_ignores_live_v4_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Released v3 algorithm evidence never rebinds to a future live builder."""
    config = EvaluationAssetConfig(tenant_id="profile-test").to_dict()
    expected = provenance_module.historical_algorithm_inventory_v3(
        config,
        extension=False,
    )
    monkeypatch.setattr(
        provenance_module,
        "build_algorithm_inventory",
        lambda *_args, **_kwargs: {"future": "v4"},
    )

    assert provenance_module.historical_algorithm_inventory_v3(
        config,
        extension=False,
    ) == expected


def test_extension_v2_profile_keeps_v1_snapshot_semantics_frozen() -> None:
    """Select parent-snapshot inventories from persisted reuse schema versions."""
    assert lineage_validation.LINEAGE_SCHEMA_VERSION == ("fapo-evaluation-asset-lineage-v1")
    assert lineage_validation.REUSE_SCHEMA_VERSION == "fapo-evaluation-asset-reuse-v2"
    assert lineage_validation.SNAPSHOT_SCHEMA_VERSION == ("fapo-evaluation-asset-parent-snapshot-v2")

    v1 = lineage_validation.extension_persistence_profile("fapo-evaluation-asset-reuse-v1")
    v2 = lineage_validation.extension_persistence_profile(lineage_validation.REUSE_SCHEMA_VERSION)
    assert v1.snapshot_schema_version == "fapo-evaluation-asset-parent-snapshot-v1"
    assert "parent_trusted_split_plan.jsonl" not in v1.common_parent_snapshot_files
    assert "prepared_inputs" not in v1.static_snapshot_inputs
    assert v2.snapshot_schema_version == lineage_validation.SNAPSHOT_SCHEMA_VERSION
    assert v2.static_snapshot_inputs["prepared_inputs"] == ("parent_trusted_split_plan.jsonl",)
    assert {
        "parent_inferred_cases.jsonl",
        "parent_inference_dependencies.jsonl",
        "parent_held_inference_outputs.jsonl",
    } <= set(v2.static_snapshot_inputs["label_inference"])
    assert {
        "parent_synthetic_dependencies.jsonl",
        "parent_derived_review_items.jsonl",
        "parent_duplicate_families.jsonl",
        "parent_held_derived_cases.jsonl",
    } <= set(v2.static_snapshot_inputs["synthetic_coverage"])
    assert {
        "protected_feedback_evidence.jsonl",
        "protected_candidate_guidelines.jsonl",
        "protected_evaluation_guidelines.jsonl",
        "protected_trusted_cases.jsonl",
    } <= set(v2.native_stage_three_seeds)
    with pytest.raises(ValueError, match="reuse schema is unsupported"):
        lineage_validation.extension_persistence_profile("fapo-evaluation-asset-reuse-v3")


def test_extension_v2_profile_survives_live_v3_source_evolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A future extension writer cannot remove or redefine persisted reuse-v2."""

    def projection(profile: Any) -> dict[str, Any]:
        return {
            "reuse_schema_version": profile.reuse_schema_version,
            "snapshot_schema_version": profile.snapshot_schema_version,
            "native_stage_three_seeds": tuple(profile.native_stage_three_seeds),
            "legacy_stage_three_seeds": tuple(profile.legacy_stage_three_seeds),
            "stage_three_operation": profile.stage_three_operation,
            "common_parent_snapshot_files": tuple(
                profile.common_parent_snapshot_files
            ),
            "static_snapshot_inputs": {
                str(stage): tuple(files)
                for stage, files in profile.static_snapshot_inputs.items()
            },
        }

    frozen_v2 = projection(
        lineage_validation.extension_persistence_profile(
            "fapo-evaluation-asset-reuse-v2"
        )
    )

    class FutureReuseWriter(ast.NodeTransformer):
        def visit_Assign(self, node: ast.Assign) -> ast.Assign:
            names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if "REUSE_SCHEMA_VERSION" in names:
                node.value = ast.copy_location(
                    ast.Constant(value="fapo-evaluation-asset-reuse-v3"),
                    node.value,
                )
            elif "SNAPSHOT_SCHEMA_VERSION" in names:
                node.value = ast.copy_location(
                    ast.Constant(value="fapo-evaluation-asset-parent-snapshot-v3"),
                    node.value,
                )
            elif names & {
                "NATIVE_STAGE_THREE_SEEDS",
                "LEGACY_STAGE_THREE_SEEDS",
                "COMMON_PARENT_SNAPSHOT_FILES",
            }:
                node.value = ast.copy_location(
                    ast.BinOp(
                        left=node.value,
                        op=ast.Add(),
                        right=ast.Tuple(
                            elts=[ast.Constant(value="future-only.jsonl")],
                            ctx=ast.Load(),
                        ),
                    ),
                    node.value,
                )
            elif "_STATIC_SNAPSHOT_INPUTS" in names:
                value = node.value
                if (
                    isinstance(value, ast.Call)
                    and value.args
                    and isinstance(value.args[0], ast.Dict)
                ):
                    value.args[0].keys.append(ast.Constant(value="future_stage"))
                    value.args[0].values.append(
                        ast.Tuple(
                            elts=[ast.Constant(value="future-only.jsonl")],
                            ctx=ast.Load(),
                        )
                    )
            return self.generic_visit(node)

    source = inspect.getsource(lineage_validation)
    tree = FutureReuseWriter().visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    module_name = "_fapo_test_future_lineage_validation"
    future = types.ModuleType(module_name)
    future.__file__ = str(inspect.getsourcefile(lineage_validation))
    monkeypatch.setitem(sys.modules, module_name, future)
    exec(compile(tree, future.__file__, "exec"), future.__dict__)

    live_v3 = future.extension_persistence_profile(
        "fapo-evaluation-asset-reuse-v3"
    )
    assert live_v3.snapshot_schema_version == (
        "fapo-evaluation-asset-parent-snapshot-v3"
    )
    assert "future-only.jsonl" in live_v3.native_stage_three_seeds
    assert "future-only.jsonl" in live_v3.legacy_stage_three_seeds
    assert "future-only.jsonl" in live_v3.common_parent_snapshot_files
    assert live_v3.static_snapshot_inputs["future_stage"] == (
        "future-only.jsonl",
    )
    assert projection(
        future.extension_persistence_profile(
            "fapo-evaluation-asset-reuse-v2"
        )
    ) == frozen_v2
