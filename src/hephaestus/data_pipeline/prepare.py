# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Load, validate, redact, and split input records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from src.hephaestus.data_pipeline.contract import validate_input_records
from src.hephaestus.data_pipeline.trace import model_visible_context, redact_record

SPLITS = ("train", "validation", "test", "regression")
_SHARES = {"train": 0.6, "validation": 0.2, "test": 0.2}
_SHARES_WITH_REGRESSION = {"train": 0.48, "validation": 0.16, "test": 0.16, "regression": 0.2}


@dataclass
class PreparedRecord:
    """One validated input record and its split.

    Attributes:
        row: The (redacted) input record.
        labeled: Whether the record came with trusted feedback.
        split: One of ``SPLITS``.
        group: Smallest record ID in the record's connected group.
    """

    row: Dict[str, Any]
    labeled: bool
    split: str
    group: str

    @property
    def record_id(self) -> str:
        return str(self.row["record_id"])


def load_input(path: Path, *, labeled: bool) -> List[Dict[str, Any]]:
    """Read and validate one ``fafo-evaluation-input-v1`` JSONL file."""
    rows: List[Dict[str, Any]] = []
    numbers: List[int] = []
    # Split on newlines only: str.splitlines would also break on U+2028 inside strings.
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{number}: each line must be a JSON object")
        rows.append(row)
        numbers.append(number)
    validate_input_records(rows, labeled=labeled, path=path, row_numbers=numbers)
    return rows


def prepare_records(
    feedback: Sequence[Mapping[str, Any]],
    unlabeled: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    regression_split: bool,
    redact: bool,
) -> Tuple[List[PreparedRecord], List[Dict[str, str]]]:
    """Redact records and assign every connected group to one split.

    Records that share a ``group_id`` or an identical model-visible context
    form one connected group, and a group never spans splits. Groups with
    feedback are balanced by their feedback records and unlabeled-only groups
    by their size, separately, so feedback is spread across every split. The
    optional regression split takes groups with feedback only; their
    unlabeled records are excluded.

    Returns:
        The kept records sorted by record ID, and ``{record_id, reason}`` for
        each excluded record.
    """
    feedback_ids = {str(row["record_id"]) for row in feedback}
    shared = sorted(feedback_ids & {str(row["record_id"]) for row in unlabeled})
    if shared:
        raise ValueError(f"record_id '{shared[0]}' appears in both the feedback and unlabeled inputs")
    rows = [redact_record(row) if redact else dict(row) for row in [*feedback, *unlabeled]]
    groups = connected_groups(rows)

    labeled_groups: List[List[int]] = []
    unlabeled_groups: List[List[int]] = []
    for group in groups:
        has_feedback = any(str(rows[i]["record_id"]) in feedback_ids for i in group)
        (labeled_groups if has_feedback else unlabeled_groups).append(group)
    labeled_shares = _SHARES_WITH_REGRESSION if regression_split else _SHARES
    split_by_index = {
        **_assign(
            labeled_groups, rows, labeled_shares, seed, lambda i: str(rows[i]["record_id"]) in feedback_ids
        ),
        **_assign(unlabeled_groups, rows, _SHARES, seed, lambda i: True),
    }

    records: List[PreparedRecord] = []
    excluded: List[Dict[str, str]] = []
    for group in groups:
        group_name = min(str(rows[i]["record_id"]) for i in group)
        for index in group:
            row = rows[index]
            labeled = str(row["record_id"]) in feedback_ids
            split = split_by_index[index]
            if split == "regression" and not labeled:
                excluded.append(
                    {"record_id": str(row["record_id"]), "reason": "unlabeled_in_regression_group"}
                )
                continue
            records.append(PreparedRecord(row=row, labeled=labeled, split=split, group=group_name))
    records.sort(key=lambda record: record.record_id)
    excluded.sort(key=lambda item: item["record_id"])
    return records, excluded


def connected_groups(rows: Sequence[Mapping[str, Any]]) -> List[List[int]]:
    """Return row indices grouped by shared ``group_id`` or identical context."""
    parents = list(range(len(rows)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    first_seen: Dict[Tuple[str, str], int] = {}
    for index, row in enumerate(rows):
        context = json.dumps(model_visible_context(row), sort_keys=True)
        for key in (("group", str(row["group_id"])), ("context", context)):
            if key in first_seen:
                parents[find(index)] = find(first_seen[key])
            else:
                first_seen[key] = index

    members: Dict[int, List[int]] = {}
    for index in range(len(rows)):
        members.setdefault(find(index), []).append(index)
    return sorted(members.values(), key=lambda group: min(str(rows[i]["record_id"]) for i in group))


def _assign(
    groups: Sequence[Sequence[int]],
    rows: Sequence[Mapping[str, Any]],
    shares: Mapping[str, float],
    seed: int,
    counts: Callable[[int], bool],
) -> Dict[int, str]:
    """Assign groups in seeded order, each to the split furthest below its target.

    A group's weight is the number of its rows for which ``counts`` is true.
    """
    weights = [sum(1 for index in group if counts(index)) for group in groups]
    total = sum(weights)
    filled = {split: 0 for split in shares}
    names = list(shares)

    def order(group: Sequence[int]) -> str:
        name = min(str(rows[i]["record_id"]) for i in group)
        return hashlib.sha256(f"{seed}:{name}".encode("utf-8")).hexdigest()

    assignment: Dict[int, str] = {}
    for group, weight in sorted(zip(groups, weights), key=lambda item: order(item[0])):
        split = max(names, key=lambda name: (shares[name] * total - filled[name], -names.index(name)))
        filled[split] += weight
        for index in group:
            assignment[index] = split
    return assignment
