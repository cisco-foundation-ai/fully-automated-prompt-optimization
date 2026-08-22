# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for deterministic evaluation-asset split isolation contracts."""

from __future__ import annotations

import importlib
from typing import Any

import pytest


def _record(
    record_id: str,
    group_id: str,
    *,
    user_input: str = "Hello",
    conversation_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "group_id": group_id,
        "user_input": user_input,
        "conversation_context": (
            conversation_context
            if conversation_context is not None
            else [{"role": "system", "content": "Rules"}]
        ),
        "tool_calls": [{"name": "lookup", "arguments": {"q": "x"}}],
        "runtime": {"temperature": 0},
        "feedback": {"polarity": "positive", "rationale": "Useful."},
    }


def test_model_visible_context_fingerprint_has_a_canonical_exact_boundary() -> None:
    """Only exact canonical model-visible context determines the fingerprint."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )

    row = {
        **_record("record-1", "group-1"),
        "assistant_output": "Not part of a new model invocation.",
        "metadata": {"private_note": "Not model-visible."},
    }

    context = module.model_visible_context(row)
    fingerprint = module.model_visible_context_fingerprint(row)

    assert module.MODEL_VISIBLE_CONTEXT_REVISION == "fapo-model-visible-context-v1"
    assert context == {
        "messages_json": (
            '[{"content": "Rules", "role": "system"}, '
            '{"content": "Hello", "role": "user"}]'
        ),
        "tool_context_json": (
            '[{"arguments": {"q": "x"}, "name": "lookup"}]'
        ),
        "runtime_json": '{"temperature": 0}',
    }
    assert fingerprint == "1670e828d22e3923a2d0423d4479127c39940897de79da001c6a4e7750e08aa1"
    assert fingerprint == module.model_visible_context_fingerprint(
        {
            **_record("record-2", "different-group"),
            "assistant_output": "Different historical answer.",
            "metadata": {"private_note": "Different metadata."},
        }
    )


def test_split_groups_are_transitive_across_group_and_exact_context_edges() -> None:
    """A context bridge must union whole original groups without rewriting them."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )
    rows = [
        _record("record-a1", "group-a", user_input="alpha"),
        _record("record-a2", "group-a", user_input="shared"),
        _record("record-b1", "group-b", user_input="shared"),
        _record("record-c1", "group-c", user_input="separate"),
    ]

    groups = module.derive_split_groups(rows)
    reversed_groups = module.derive_split_groups(list(reversed(rows)))

    assert groups == reversed_groups
    assert [group.group_ids for group in groups] == [
        ("group-a", "group-b"),
        ("group-c",),
    ]
    assert [group.record_ids for group in groups] == [
        ("record-a1", "record-a2", "record-b1"),
        ("record-c1",),
    ]
    assert all(group.split_group_id.startswith("split-group-") for group in groups)
    assert len({group.split_group_id for group in groups}) == 2


def test_seeded_split_assignment_uses_one_stable_draw() -> None:
    """One stable hash fraction must implement the documented split proportions."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )

    assert module.assign_split("split-group-0", split_seed=42) == "validation"
    assert module.assign_split("split-group-1", split_seed=42) == "validation"
    assert module.assign_split("split-group-2", split_seed=42) == "train"
    assert module.assign_split("split-group-3", split_seed=42) == "regression"
    assert module.assign_split("split-group-8", split_seed=42) == "test"
    assert module.assign_split("split-group-0", split_seed=43) == "test"


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [
        (0.0, "regression"),
        (0.199999999, "regression"),
        (0.2, "train"),
        (0.679999999, "train"),
        (0.68, "validation"),
        (0.839999999, "validation"),
        (0.84, "test"),
        (0.999999999, "test"),
    ],
)
def test_split_thresholds_are_closed_and_exhaustive(
    fraction: float,
    expected: str,
) -> None:
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )

    assert module.split_from_fraction(fraction) == expected


def test_trusted_split_plan_retains_parent_assignment_after_safe_component_growth() -> None:
    """A child component touching one parent split must inherit that assignment."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )
    rows = [
        _record("parent-a", "group-a", user_input="shared"),
        _record("child-b", "group-b", user_input="shared"),
    ]

    plan = module.build_trusted_split_plan(
        rows,
        split_seed=42,
        parent_assignments={"group-a": "validation"},
    )

    assert len(plan) == 1
    assert plan[0].group_ids == ("group-a", "group-b")
    assert plan[0].record_ids == ("child-b", "parent-a")
    assert plan[0].split == "validation"
    assert plan[0].assignment_source == "inherited"
    assert plan[0].to_dict() == {
        "schema_version": "fapo-trusted-split-plan-v1",
        "split_group_id": plan[0].split_group_id,
        "group_ids": ["group-a", "group-b"],
        "record_ids": ["child-b", "parent-a"],
        "context_fingerprints": list(plan[0].context_fingerprints),
        "split": "validation",
        "assignment_source": "inherited",
    }


def test_trusted_split_plan_fails_closed_when_a_bridge_joins_parent_splits() -> None:
    """A new exact-context bridge cannot choose between prior split assignments."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )
    rows = [
        _record("parent-a", "group-a", user_input="alpha"),
        _record("bridge-a", "group-a", user_input="shared"),
        _record("parent-b", "group-b", user_input="shared"),
    ]

    with pytest.raises(module.ParentAssignmentConflictError) as raised:
        module.build_trusted_split_plan(
            rows,
            split_seed=42,
            parent_assignments={
                "group-a": "train",
                "group-b": "validation",
            },
        )

    assert raised.value.reason == "parent_split_assignment_conflict"
    assert "group-a" in str(raised.value)
    assert "group-b" in str(raised.value)
    assert "train" in str(raised.value)
    assert "validation" in str(raised.value)


def test_trusted_split_plan_rejects_an_unknown_parent_split() -> None:
    """Persisted parent assignments are a closed, fail-closed enum."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )

    with pytest.raises(ValueError, match="parent split.*holdout"):
        module.build_trusted_split_plan(
            [_record("record-a", "group-a")],
            split_seed=42,
            parent_assignments={"group-a": "holdout"},
        )


def test_split_plan_expands_to_unambiguous_record_and_parent_maps() -> None:
    """Pipeline integration can resolve records and retain parent group splits."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )
    plan = module.build_trusted_split_plan(
        [
            _record("record-a", "group-a", user_input="shared"),
            _record("record-b", "group-b", user_input="shared"),
        ],
        split_seed=42,
        parent_assignments={"group-a": "validation"},
    )

    expanded = module.expand_trusted_split_plan(plan)

    assert [entry.record_id for entry in expanded] == ["record-a", "record-b"]
    assert {entry.split for entry in expanded} == {"validation"}
    assert module.split_assignments_by_record_id(plan) == {
        "record-a": "validation",
        "record-b": "validation",
    }
    assert module.parent_assignments_by_group_id(
        [entry.to_dict() for entry in plan]
    ) == {
        "group-a": "validation",
        "group-b": "validation",
    }


@pytest.mark.parametrize(
    ("feedback", "expected_source"),
    [
        (
            {"polarity": "positive", "rationale": "  Supported rule.  "},
            "rationale",
        ),
        (
            {"polarity": "negative", "rationale": "", "correction": False},
            "correction",
        ),
        (
            {"polarity": "negative", "rationale": "", "correction": 0},
            "correction",
        ),
        (
            {
                "polarity": "negative",
                "rationale": "",
                "correctness_signals": [
                    {
                        "kind": "executable",
                        "check_id": "exit-status",
                        "passed": False,
                    }
                ],
            },
            "correctness_signal:executable",
        ),
    ],
)
def test_correctness_eligibility_accepts_only_explicit_material_evidence(
    feedback: dict[str, Any],
    expected_source: str,
) -> None:
    """Each allowed explicit evidence form independently activates eligibility."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )
    row = {**_record("record-1", "group-1"), "feedback": feedback}

    result = module.assess_correctness_eligibility(row)

    assert result.eligible is True
    assert result.hold_reason is None
    assert result.evidence_sources == (expected_source,)


def test_correctness_eligibility_holds_empty_evidence_even_with_a_tool_error() -> None:
    """Ordinary tool errors must never be promoted into correctness evidence."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )
    row = {
        **_record("record-1", "group-1"),
        "tool_calls": [
            {"name": "lookup", "arguments": {}, "error": "request failed"}
        ],
        "feedback": {
            "polarity": "negative",
            "rationale": "  ",
            "correction": {"replacement": [None, "", [], {}]},
        },
    }

    result = module.assess_correctness_eligibility(row)

    assert result.eligible is False
    assert result.hold_reason == "insufficient_correctness_evidence"
    assert result.evidence_sources == ()
    assert result.to_dict() == {
        "schema_version": "fapo-feedback-eligibility-v1",
        "record_id": "record-1",
        "group_id": "group-1",
        "eligible": False,
        "evidence_sources": [],
        "hold_reason": "insufficient_correctness_evidence",
    }


def test_correctness_eligibility_batch_is_a_per_record_mapping() -> None:
    """The persisted eligibility artifact deterministically covers every record."""
    module = importlib.import_module(
        "src.hephaestus.evaluation_assets.split_isolation"
    )

    entries = module.assess_correctness_eligibility_records(
        [
            _record("record-b", "group-b"),
            {
                **_record("record-a", "group-a"),
                "feedback": {"polarity": "negative", "rationale": ""},
            },
        ]
    )

    assert [entry.record_id for entry in entries] == ["record-a", "record-b"]
    assert module.eligibility_by_record_id(entries) == {
        "record-a": entries[0],
        "record-b": entries[1],
    }
