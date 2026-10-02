# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Integrity and family-isolation checks for the frozen Retail split."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[1] / "recipe/retail-split.json"


def test_split_assigns_every_task_once_and_keeps_families_disjoint() -> None:
    split = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assignments = split["task_assignments"]

    assert len(assignments) == split["task_count"] == 114
    assert len({str(row["task_id"]) for row in assignments}) == 114
    development = {
        str(task_id) for task_id in split["partitions"]["development"]["task_ids"]
    }
    final_holdout = {
        str(task_id) for task_id in split["partitions"]["final_holdout"]["task_ids"]
    }
    assert len(development) == 92
    assert len(final_holdout) == 22
    assert not development & final_holdout
    assert development | final_holdout == {str(index) for index in range(114)}

    family_partitions: dict[str, set[str]] = {}
    for row in assignments:
        family_partitions.setdefault(str(row["scenario_family_id"]), set()).add(
            str(row["partition"])
        )
    assert len(family_partitions) == split["scenario_family_count"] == 73
    assert all(len(partitions) == 1 for partitions in family_partitions.values())
    assert split["leakage_audit"]["family_cross_partition_count"] == 0
