# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from data_pipeline_fakes import make_record, write_jsonl

from src.hephaestus.data_pipeline.prepare import connected_groups, load_input, prepare_records


def _prepare(feedback, unlabeled=(), *, regression_split=False, seed=0):
    return prepare_records(
        feedback, list(unlabeled), seed=seed, regression_split=regression_split, redact=True
    )


class TestLoadInput:
    def test_validates_contract(self, tmp_path: Path) -> None:
        """Rows are validated against the input contract with physical line numbers."""
        path = tmp_path / "feedback.jsonl"
        row = make_record("r1", labeled=True)
        del row["feedback"]
        path.write_text("\n" + json.dumps(row) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match=r"feedback.jsonl:2"):
            load_input(path, labeled=True)

    def test_rejects_invalid_json(self, tmp_path: Path) -> None:
        """A malformed line names its file and line."""
        path = tmp_path / "unlabeled.jsonl"
        path.write_text("{not json}\n", encoding="utf-8")

        with pytest.raises(ValueError, match=r"unlabeled.jsonl:1: invalid JSON"):
            load_input(path, labeled=False)

    def test_line_separator_inside_string(self, tmp_path: Path) -> None:
        """Unicode line separators inside JSON strings do not split a row."""
        path = tmp_path / "feedback.jsonl"
        row = make_record("r1", labeled=True, rationale="first\u2028second")
        path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

        assert load_input(path, labeled=True)[0]["feedback"]["rationale"] == "first\u2028second"

    def test_reads_valid_rows(self, tmp_path: Path) -> None:
        """Valid rows load in file order."""
        path = tmp_path / "feedback.jsonl"
        write_jsonl(path, [make_record("b", labeled=True), make_record("a", labeled=True)])

        assert [row["record_id"] for row in load_input(path, labeled=True)] == ["b", "a"]


class TestConnectedGroups:
    def test_unions_shared_group_and_identical_context(self) -> None:
        """Records sharing a group_id or an identical context end up in one group."""
        rows = [
            make_record("a", labeled=False, group_id="g1"),
            make_record("b", labeled=False, group_id="g1"),
            make_record("c", labeled=False, group_id="g2"),
            make_record("d", labeled=False, group_id="g3"),
        ]
        rows[3]["user_input"] = rows[2]["user_input"]
        rows[3]["tool_calls"] = rows[2]["tool_calls"]

        assert connected_groups(rows) == [[0, 1], [2, 3]]


class TestPrepareRecords:
    def test_groups_never_span_splits(self) -> None:
        """Every member of a connected group gets the same split."""
        feedback = [make_record(f"f{i}", labeled=True, group_id=f"g{i // 2}") for i in range(20)]

        records, _ = _prepare(feedback)

        splits = {}
        for record in records:
            assert splits.setdefault(record.row["group_id"], record.split) == record.split
        assert len(set(splits.values())) == 3

    def test_unlabeled_companions_do_not_skew_feedback(self) -> None:
        """Feedback groups are balanced by feedback count, not by how many unlabeled records they hold."""
        feedback = [make_record(f"f{i:02d}", labeled=True, group_id=f"g{i:02d}") for i in range(10)]
        companions = [make_record(f"u{i:02d}", labeled=False, group_id="g03") for i in range(30)]

        for seed in range(6):
            records, _ = _prepare(feedback, companions, seed=seed)
            labeled = Counter(record.split for record in records if record.labeled)
            assert labeled == {"train": 6, "validation": 2, "test": 2}

    def test_balanced_split_sizes(self) -> None:
        """Feedback is divided 60/20/20 without regression."""
        records, excluded = _prepare([make_record(f"f{i:02d}", labeled=True) for i in range(20)])

        assert Counter(record.split for record in records) == {"train": 12, "validation": 4, "test": 4}
        assert excluded == []

    def test_regression_split_is_trusted_only(self) -> None:
        """Regression takes 20% of feedback groups and excludes their unlabeled members."""
        feedback = [make_record(f"f{i:02d}", labeled=True, group_id=f"g{i:02d}") for i in range(25)]
        companions = [make_record(f"u{i:02d}", labeled=False, group_id=f"g{i:02d}") for i in range(25)]

        records, excluded = _prepare(feedback, companions, regression_split=True)

        labeled_splits = Counter(record.split for record in records if record.labeled)
        assert labeled_splits == {"train": 12, "validation": 4, "test": 4, "regression": 5}
        assert not any(record.split == "regression" and not record.labeled for record in records)
        assert len(excluded) == 5
        assert {item["reason"] for item in excluded} == {"unlabeled_in_regression_group"}

    def test_unlabeled_only_groups_never_enter_regression(self) -> None:
        """Groups without feedback are split 60/20/20 even with regression on."""
        unlabeled = [make_record(f"u{i:02d}", labeled=False) for i in range(10)]

        records, _ = _prepare([make_record("f0", labeled=True)], unlabeled, regression_split=True)

        assert Counter(r.split for r in records if not r.labeled) == {"train": 6, "validation": 2, "test": 2}

    def test_seed_changes_assignment_deterministically(self) -> None:
        """The same seed reproduces the assignment; another seed reshuffles it."""
        feedback = [make_record(f"f{i:02d}", labeled=True) for i in range(20)]

        first = [r.split for r in _prepare(feedback, seed=1)[0]]

        assert first == [r.split for r in _prepare(feedback, seed=1)[0]]
        assert first != [r.split for r in _prepare(feedback, seed=2)[0]]

    def test_rejects_record_in_both_inputs(self) -> None:
        """A record ID cannot be both labeled and unlabeled."""
        with pytest.raises(ValueError, match="appears in both"):
            _prepare([make_record("x", labeled=True)], [make_record("x", labeled=False)])

    def test_redaction_can_be_disabled(self) -> None:
        """With redact off, content is kept verbatim."""
        row = make_record("f1", labeled=True, rationale="Write to a@b.com")

        records, _ = prepare_records([row], [], seed=0, regression_split=False, redact=False)

        assert records[0].row["feedback"]["rationale"] == "Write to a@b.com"
