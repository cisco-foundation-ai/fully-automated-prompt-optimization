# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

import tempfile
from pathlib import Path

import pytest

from src.hephaestus.runs.io_utils import write_outputs


def test_write_outputs_normalizes_breakdown_by_total_cases(tmp_path: Path):
    output_dir = tmp_path / "out"
    run_config = {"tenant_id": "demo"}
    results = [
        {"case_id": "c1", "composite_score": 80.0, "score_breakdown": {"format": 100.0}},
        {"case_id": "c2", "composite_score": 0.0, "score_breakdown": {}},
    ]

    write_outputs(output_dir, run_config, results)

    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "- format: 50.00" in summary


def test_write_outputs_excludes_execution_failures_and_reports_trust_tiers(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "out"
    results = [
        {
            "case_id": "trusted-ok",
            "execution_status": "succeeded",
            "composite_score": 80.0,
            "score_breakdown": {"quality": 80.0},
            "evaluation_provenance": {"trust_tier": "trusted_feedback"},
        },
        {
            "case_id": "synthetic-failed",
            "execution_status": "failed",
            "composite_score": 0.0,
            "score_breakdown": {},
            "evaluation_provenance": {
                "trust_tier": "synthetic_from_trusted_rubric"
            },
        },
        {
            "case_id": "inferred-ok",
            "execution_status": "succeeded",
            "composite_score": 40.0,
            "score_breakdown": {"quality": 40.0},
            "evaluation_provenance": {
                "trust_tier": "inferred_from_trusted_feedback"
            },
        },
        {
            "case_id": "unknown-tier",
            "execution_status": "succeeded",
            "composite_score": 60.0,
            "score_breakdown": {"quality": 60.0},
            "evaluation_provenance": {
                "trust_tier": "private-arbitrary-metadata"
            },
        },
    ]

    write_outputs(output_dir, {"tenant_id": "demo"}, results)

    summary = (output_dir / "summary.md").read_text(encoding="utf-8")
    assert "Successful cases: 3" in summary
    assert "Infrastructure failures: 1" in summary
    assert "- average: 60.00" in summary
    assert "| trusted_feedback | 1 | 1 | 0 | 80.00 |" in summary
    assert "| synthetic_from_trusted_rubric | 1 | 0 | 1 | N/A |" in summary
    assert "private-arbitrary-metadata" not in summary


def test_write_outputs_attributes_in_memory_without_a_temporary_results_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_named_temporary_file = tempfile.NamedTemporaryFile

    def _reject_results_tempfile(*args: object, **kwargs: object) -> object:
        if kwargs.get("suffix") == ".jsonl" and kwargs.get("delete") is False:
            raise AssertionError(
                "attribution must not serialize an intermediate results file"
            )
        return original_named_temporary_file(*args, **kwargs)

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _reject_results_tempfile)
    results = [
        {
            "case_id": "low-score",
            "execution_status": "succeeded",
            "composite_score": 0.0,
            "score_breakdown": {},
            "step_outputs": {"answer": {"confidence": "low"}},
        }
    ]

    write_outputs(tmp_path / "out", {"tenant_id": "demo"}, results)

    assert (tmp_path / "out" / "summary.md").exists()
