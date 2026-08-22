# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Pure contracts for leakage-safe evaluation-asset split isolation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence, cast

DatasetSplit = Literal["regression", "train", "validation", "test"]
AssignmentSource = Literal["seeded", "inherited"]
MODEL_VISIBLE_CONTEXT_REVISION = "fapo-model-visible-context-v1"
SPLIT_GROUP_REVISION = "fapo-split-group-v1"
SPLIT_ASSIGNMENT_REVISION = "fapo-trusted-split-v1"
SPLIT_PLAN_SCHEMA_VERSION = "fapo-trusted-split-plan-v1"
ELIGIBILITY_SCHEMA_VERSION = "fapo-feedback-eligibility-v1"
PARENT_SPLIT_ASSIGNMENT_CONFLICT = "parent_split_assignment_conflict"
INSUFFICIENT_CORRECTNESS_EVIDENCE = "insufficient_correctness_evidence"
DATASET_SPLITS = frozenset({"regression", "train", "validation", "test"})
CORRECTNESS_SIGNAL_KINDS = ("deterministic", "executable")


class ParentAssignmentConflictError(ValueError):
    """Raised when a new component bridges incompatible parent assignments."""

    reason = PARENT_SPLIT_ASSIGNMENT_CONFLICT


@dataclass(frozen=True)
class SplitGroup:
    """One connected leakage boundary derived without changing source groups."""

    split_group_id: str
    group_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    context_fingerprints: tuple[str, ...]


@dataclass(frozen=True)
class TrustedSplitPlanEntry:
    """One persisted assignment for a connected trusted-feedback group."""

    split_group_id: str
    group_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    context_fingerprints: tuple[str, ...]
    split: DatasetSplit
    assignment_source: AssignmentSource

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical JSONL row for this assignment."""
        return {
            "schema_version": SPLIT_PLAN_SCHEMA_VERSION,
            "split_group_id": self.split_group_id,
            "group_ids": list(self.group_ids),
            "record_ids": list(self.record_ids),
            "context_fingerprints": list(self.context_fingerprints),
            "split": self.split,
            "assignment_source": self.assignment_source,
        }


@dataclass(frozen=True)
class TrustedRecordSplitAssignment:
    """Expanded record-level view of one trusted split-plan entry."""

    record_id: str
    split_group_id: str
    split: DatasetSplit
    assignment_source: AssignmentSource


@dataclass(frozen=True)
class CorrectnessEligibility:
    """Per-record decision about eligibility for correctness authoring."""

    record_id: str
    group_id: str
    eligible: bool
    evidence_sources: tuple[str, ...]
    hold_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical JSONL row for this eligibility decision."""
        return {
            "schema_version": ELIGIBILITY_SCHEMA_VERSION,
            "record_id": self.record_id,
            "group_id": self.group_id,
            "eligible": self.eligible,
            "evidence_sources": list(self.evidence_sources),
            "hold_reason": self.hold_reason,
        }


def model_visible_context(row: Mapping[str, Any]) -> dict[str, str]:
    """Compile the exact serialized context shape used by a FAPO case."""
    messages = [
        *row["conversation_context"],
        {"role": "user", "content": row["user_input"]},
    ]
    return {
        "messages_json": json.dumps(messages, sort_keys=True),
        "tool_context_json": json.dumps(row["tool_calls"], sort_keys=True),
        "runtime_json": json.dumps(row["runtime"], sort_keys=True),
    }


def model_visible_context_fingerprint(row: Mapping[str, Any]) -> str:
    """Hash the exact canonical context supplied to a fresh task-model call."""
    payload = {
        "revision": MODEL_VISIBLE_CONTEXT_REVISION,
        "context": model_visible_context(row),
    }
    return _canonical_sha256(payload)


def derive_split_groups(rows: Sequence[Mapping[str, Any]]) -> tuple[SplitGroup, ...]:
    """Union records sharing an original group or exact model-visible context."""
    parents = list(range(len(rows)))
    first_by_group: dict[str, int] = {}
    first_by_context: dict[str, int] = {}
    context_fingerprints: list[str] = []

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    for index, row in enumerate(rows):
        group_id = str(row["group_id"])
        context_fingerprint = model_visible_context_fingerprint(row)
        context_fingerprints.append(context_fingerprint)
        if group_id in first_by_group:
            union(index, first_by_group[group_id])
        else:
            first_by_group[group_id] = index
        if context_fingerprint in first_by_context:
            union(index, first_by_context[context_fingerprint])
        else:
            first_by_context[context_fingerprint] = index

    members_by_root: dict[int, list[int]] = {}
    for index in range(len(rows)):
        members_by_root.setdefault(find(index), []).append(index)

    groups: list[SplitGroup] = []
    for member_indices in members_by_root.values():
        group_ids = tuple(
            sorted({str(rows[index]["group_id"]) for index in member_indices})
        )
        record_ids = tuple(
            sorted(str(rows[index]["record_id"]) for index in member_indices)
        )
        fingerprints = tuple(
            sorted({context_fingerprints[index] for index in member_indices})
        )
        groups.append(
            SplitGroup(
                split_group_id=_split_group_id(group_ids),
                group_ids=group_ids,
                record_ids=record_ids,
                context_fingerprints=fingerprints,
            )
        )
    return tuple(sorted(groups, key=lambda group: group.group_ids))


def assign_split(split_group_id: str, *, split_seed: int) -> DatasetSplit:
    """Assign one group from one stable split-seed hash fraction."""
    return split_from_fraction(_stable_fraction(split_seed, split_group_id))


def split_from_fraction(fraction: float) -> DatasetSplit:
    """Map one unit-interval fraction onto the closed split allocation."""
    if isinstance(fraction, bool) or not 0.0 <= fraction < 1.0:
        raise ValueError("split fraction must be in [0, 1)")
    if fraction < 0.2:
        return "regression"
    if fraction < 0.68:
        return "train"
    if fraction < 0.84:
        return "validation"
    return "test"


def build_trusted_split_plan(
    rows: Sequence[Mapping[str, Any]],
    *,
    split_seed: int,
    parent_assignments: Mapping[str, DatasetSplit | str] | None = None,
) -> tuple[TrustedSplitPlanEntry, ...]:
    """Assign connected groups while retaining known parent group locations."""
    inherited_by_group = _validated_parent_assignments(parent_assignments or {})
    plan = []
    for group in derive_split_groups(rows):
        inherited_splits = sorted(
            {
                inherited_by_group[group_id]
                for group_id in group.group_ids
                if group_id in inherited_by_group
            }
        )
        if len(inherited_splits) > 1:
            raise ParentAssignmentConflictError(
                f"{PARENT_SPLIT_ASSIGNMENT_CONFLICT}: connected group_ids "
                f"{', '.join(group.group_ids)} bridge parent splits "
                f"{', '.join(inherited_splits)}"
            )
        if inherited_splits:
            split = inherited_splits[0]
            source: AssignmentSource = "inherited"
        else:
            split = assign_split(group.split_group_id, split_seed=split_seed)
            source = "seeded"
        plan.append(
            TrustedSplitPlanEntry(
                split_group_id=group.split_group_id,
                group_ids=group.group_ids,
                record_ids=group.record_ids,
                context_fingerprints=group.context_fingerprints,
                split=split,
                assignment_source=source,
            )
        )
    return tuple(plan)


def expand_trusted_split_plan(
    plan: Sequence[TrustedSplitPlanEntry | Mapping[str, Any]],
) -> tuple[TrustedRecordSplitAssignment, ...]:
    """Expand component plan rows into a deterministic per-record view."""
    expanded: list[TrustedRecordSplitAssignment] = []
    seen_record_ids: set[str] = set()
    for entry in plan:
        split_group_id = _plan_string(entry, "split_group_id")
        split = _plan_split(entry)
        assignment_source = _plan_assignment_source(entry)
        for record_id in _plan_string_array(entry, "record_ids"):
            if record_id in seen_record_ids:
                raise ValueError(
                    f"duplicate split-plan record_id '{record_id}'"
                )
            seen_record_ids.add(record_id)
            expanded.append(
                TrustedRecordSplitAssignment(
                    record_id=record_id,
                    split_group_id=split_group_id,
                    split=split,
                    assignment_source=assignment_source,
                )
            )
    return tuple(sorted(expanded, key=lambda entry: entry.record_id))


def split_assignments_by_record_id(
    plan: Sequence[TrustedSplitPlanEntry | Mapping[str, Any]],
) -> dict[str, DatasetSplit]:
    """Return the split assigned to every record in a trusted plan."""
    return {
        entry.record_id: entry.split
        for entry in expand_trusted_split_plan(plan)
    }


def parent_assignments_by_group_id(
    plan: Sequence[TrustedSplitPlanEntry | Mapping[str, Any]],
) -> dict[str, DatasetSplit]:
    """Recover original-group assignments from persisted component rows."""
    assignments: dict[str, DatasetSplit] = {}
    for entry in plan:
        split = _plan_split(entry)
        for group_id in _plan_string_array(entry, "group_ids"):
            if group_id in assignments:
                if assignments[group_id] != split:
                    raise ParentAssignmentConflictError(
                        f"{PARENT_SPLIT_ASSIGNMENT_CONFLICT}: group_id "
                        f"'{group_id}' has both {assignments[group_id]} and {split}"
                    )
                raise ValueError(
                    f"duplicate split-plan group_id '{group_id}'"
                )
            assignments[group_id] = split
    return assignments


def assess_correctness_eligibility(
    row: Mapping[str, Any],
) -> CorrectnessEligibility:
    """Require explicit, material correctness evidence for Stage 3 authoring."""
    feedback = row.get("feedback")
    evidence_sources: list[str] = []
    if isinstance(feedback, Mapping):
        rationale = feedback.get("rationale")
        if isinstance(rationale, str) and rationale.strip():
            evidence_sources.append("rationale")
        if "correction" in feedback and _is_material(feedback["correction"]):
            evidence_sources.append("correction")
        signals = feedback.get("correctness_signals")
        if isinstance(signals, list):
            valid_kinds = {
                str(signal["kind"])
                for signal in signals
                if _is_valid_correctness_signal(signal)
            }
            evidence_sources.extend(
                f"correctness_signal:{kind}"
                for kind in CORRECTNESS_SIGNAL_KINDS
                if kind in valid_kinds
            )
    eligible = bool(evidence_sources)
    return CorrectnessEligibility(
        record_id=str(row["record_id"]),
        group_id=str(row["group_id"]),
        eligible=eligible,
        evidence_sources=tuple(evidence_sources),
        hold_reason=(None if eligible else INSUFFICIENT_CORRECTNESS_EVIDENCE),
    )


def assess_correctness_eligibility_records(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[CorrectnessEligibility, ...]:
    """Assess and deterministically order every trusted-feedback record."""
    entries = tuple(assess_correctness_eligibility(row) for row in rows)
    eligibility_by_record_id(entries)
    return tuple(sorted(entries, key=lambda entry: entry.record_id))


def eligibility_by_record_id(
    entries: Sequence[CorrectnessEligibility],
) -> dict[str, CorrectnessEligibility]:
    """Index eligibility decisions without silently overwriting duplicates."""
    indexed: dict[str, CorrectnessEligibility] = {}
    for entry in entries:
        if entry.record_id in indexed:
            raise ValueError(
                f"duplicate feedback-eligibility record_id '{entry.record_id}'"
            )
        indexed[entry.record_id] = entry
    return indexed


def _stable_fraction(split_seed: int, split_group_id: str) -> float:
    digest = hashlib.sha256(
        f"{SPLIT_ASSIGNMENT_REVISION}:{split_seed}:{split_group_id}".encode(
            "utf-8"
        )
    ).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def _split_group_id(group_ids: Sequence[str]) -> str:
    digest = _canonical_sha256(
        {
            "revision": SPLIT_GROUP_REVISION,
            "group_ids": list(group_ids),
        }
    )
    return f"split-group-{digest}"


def _validated_parent_assignments(
    assignments: Mapping[str, DatasetSplit | str],
) -> dict[str, DatasetSplit]:
    validated: dict[str, DatasetSplit] = {}
    for group_id, value in assignments.items():
        if not isinstance(group_id, str) or not group_id.strip():
            raise ValueError("parent group_id must be a non-empty string")
        validated[group_id] = _validated_split(value, field="parent split")
    return validated


def _validated_split(value: Any, *, field: str) -> DatasetSplit:
    if not isinstance(value, str) or value not in DATASET_SPLITS:
        allowed = ", ".join(sorted(DATASET_SPLITS))
        raise ValueError(f"{field} '{value}' must be one of: {allowed}")
    return cast(DatasetSplit, value)


def _plan_value(
    entry: TrustedSplitPlanEntry | Mapping[str, Any],
    field: str,
) -> Any:
    if isinstance(entry, TrustedSplitPlanEntry):
        return getattr(entry, field)
    if field not in entry:
        raise ValueError(f"split-plan field '{field}' is required")
    return entry[field]


def _plan_string(
    entry: TrustedSplitPlanEntry | Mapping[str, Any],
    field: str,
) -> str:
    value = _plan_value(entry, field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"split-plan field '{field}' must be a non-empty string")
    return value


def _plan_string_array(
    entry: TrustedSplitPlanEntry | Mapping[str, Any],
    field: str,
) -> tuple[str, ...]:
    value = _plan_value(entry, field)
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"split-plan field '{field}' must be a string array")
    return tuple(value)


def _plan_split(
    entry: TrustedSplitPlanEntry | Mapping[str, Any],
) -> DatasetSplit:
    return _validated_split(_plan_value(entry, "split"), field="split-plan split")


def _plan_assignment_source(
    entry: TrustedSplitPlanEntry | Mapping[str, Any],
) -> AssignmentSource:
    value = _plan_value(entry, "assignment_source")
    if not isinstance(value, str) or value not in {"seeded", "inherited"}:
        raise ValueError(
            "split-plan assignment_source must be one of: inherited, seeded"
        )
    return cast(AssignmentSource, value)


def _is_material(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(_is_material(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_is_material(item) for item in value)
    return True


def _is_valid_correctness_signal(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("kind") in CORRECTNESS_SIGNAL_KINDS
        and isinstance(value.get("check_id"), str)
        and bool(value["check_id"].strip())
        and isinstance(value.get("passed"), bool)
    )


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
