# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
from pathlib import Path

import pytest

from src.hephaestus.datasets import jsonl_loader
from src.hephaestus.datasets.jsonl_loader import load_cases


def test_load_cases_valid_jsonl(tmp_path: Path):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        '{"case_id":"c1","task_type":"x","context":{},"expected":{"label":"malicious"},"metadata":{}}\n',
        encoding="utf-8",
    )

    cases = load_cases(path)
    assert isinstance(cases, list)
    assert len(cases) == 1
    assert cases[0].case_id == "c1"
    assert cases[0].expected["label"] == "malicious"


def test_load_cases_rejects_missing_required_key(tmp_path: Path):
    path = tmp_path / "cases.jsonl"
    path.write_text('{"case_id":"c1"}\n', encoding="utf-8")

    with pytest.raises(ValueError):
        load_cases(path)


def test_load_cases_accepts_expected_without_label(tmp_path: Path):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        '{"case_id":"c1","task_type":"x","context":{},'
        '"expected":{"rubric":"structured_output"},"metadata":{}}\n',
        encoding="utf-8",
    )

    cases = load_cases(path)
    assert cases[0].expected["rubric"] == "structured_output"


def test_load_cases_with_identity_uses_one_raw_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "cases.jsonl"
    raw_bytes = (
        b"\n"
        b'{"case_id":"c1","task_type":"x","context":{},'
        b'"expected":{},"metadata":{}}\n'
        b"\n"
        b'{"case_id":"c2","task_type":"y","context":{},'
        b'"expected":{},"metadata":{}}\n'
    )
    path.write_bytes(raw_bytes)

    read_count = 0
    original_read_bytes = Path.read_bytes

    def tracked_read_bytes(candidate: Path) -> bytes:
        nonlocal read_count
        if candidate == path:
            read_count += 1
        return original_read_bytes(candidate)

    def reject_read_text(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("dataset must be parsed from the hashed byte snapshot")

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    monkeypatch.setattr(Path, "read_text", reject_read_text)

    snapshot = jsonl_loader.load_cases_with_identity(path)

    assert read_count == 1
    assert [case.case_id for case in snapshot.cases] == ["c1", "c2"]
    assert snapshot.raw_sha256 == hashlib.sha256(raw_bytes).hexdigest()
    assert snapshot.ordered_case_ids == ("c1", "c2")
    assert snapshot.physical_rows_by_case_id == {"c1": 2, "c2": 4}


def test_load_cases_with_identity_rejects_duplicate_ids_with_physical_rows(
    tmp_path: Path,
):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        "\n"
        '{"case_id":"duplicate","task_type":"x","context":{},'
        '"expected":{},"metadata":{}}\n'
        "\n\n"
        '{"case_id":"duplicate","task_type":"y","context":{},'
        '"expected":{},"metadata":{}}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"Duplicate case_id 'duplicate' at rows 2 and 5",
    ):
        jsonl_loader.load_cases_with_identity(path)

    with pytest.raises(
        ValueError,
        match=r"Duplicate case_id 'duplicate' at rows 2 and 5",
    ):
        load_cases(path)
