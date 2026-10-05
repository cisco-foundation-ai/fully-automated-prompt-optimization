# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for manifest-authenticated dataset joins in step attribution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from src.hephaestus.analysis.step_attribution import attribute_verified_run
from src.hephaestus.runs.bundle import RunBundleWriter
from src.hephaestus.runs.identity import build_run_identity


def _dataset_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        for row in rows
    )


def _case(case_id: str, *, question: str = "question") -> dict[str, Any]:
    return {
        "case_id": case_id,
        "task_type": "demo",
        "context": {"question": question},
        "expected": {"answer": "private-gold-answer"},
        "metadata": {},
    }


def _result(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "task_type": "demo",
        "diagnostics": [],
        "score_breakdown": {},
        "composite_score": 0.0,
        "output_text": "private-gold-answer with a long explanation",
        "step_outputs": {
            "answer": "private-gold-answer with a long explanation"
        },
        "execution_status": "succeeded",
        "execution_error": None,
        "evaluation_provenance": {},
    }


def _identity(
    dataset_path: Path,
    content: bytes,
    ordered_case_ids: list[str],
) -> dict[str, Any]:
    return build_run_identity(
        ordered_case_ids=ordered_case_ids,
        dataset_path=str(dataset_path),
        dataset_fingerprint="sha256:" + hashlib.sha256(content).hexdigest(),
        split_fingerprint=None,
        scorer_fingerprint=None,
        metric_fingerprint=None,
    ).to_dict()


def _publish_bundle(
    output_dir: Path,
    *,
    dataset_path: Path,
    identity: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    run_id = "run-attribution"
    case_ids = [str(result["case_id"]) for result in results]
    writer = RunBundleWriter.reserve(output_dir, run_id=run_id)
    writer.publish(
        run_config={
            "run_id": run_id,
            "dataset_path": str(dataset_path),
        },
        run_identity=identity,
        results=results,
        summary="# Evaluation Summary\n",
        progress={
            "run_id": run_id,
            "status": "completed",
            "total_cases": len(case_ids),
            "completed_cases": len(case_ids),
            "successful_cases": len(case_ids),
            "attempted_case_ids": case_ids,
            "successful_case_ids": case_ids,
            "failed_case_ids": [],
            "in_flight_case_ids": [],
            "trust_tier_summaries": {},
        },
    )


def test_verified_run_joins_protected_evidence_only_after_full_authority(
    tmp_path: Path,
) -> None:
    """A valid bundle, identity, dataset hash, and order enable an in-memory join."""
    dataset_path = tmp_path / "cases.jsonl"
    content = _dataset_bytes([_case("c1", question="private-question-canary")])
    dataset_path.write_bytes(content)
    identity = _identity(dataset_path, content, ["c1"])
    output_dir = tmp_path / "run"
    _publish_bundle(
        output_dir,
        dataset_path=dataset_path,
        identity=identity,
        results=[_result("c1")],
    )

    attribution = attribute_verified_run(output_dir)

    assert attribution["answer"]["heuristic"] == "format_failure"
    serialized = json.dumps(attribution, sort_keys=True)
    assert "private-question-canary" not in serialized
    assert "private-gold-answer" not in serialized


def test_verified_run_rejects_dataset_fingerprint_mismatch(tmp_path: Path) -> None:
    """Changed dataset bytes cannot supply protected attribution evidence."""
    dataset_path = tmp_path / "cases.jsonl"
    original = _dataset_bytes([_case("c1", question="original")])
    dataset_path.write_bytes(original)
    output_dir = tmp_path / "run"
    _publish_bundle(
        output_dir,
        dataset_path=dataset_path,
        identity=_identity(dataset_path, original, ["c1"]),
        results=[_result("c1")],
    )
    dataset_path.write_bytes(_dataset_bytes([_case("c1", question="changed")]))

    with pytest.raises(ValueError, match="dataset fingerprint"):
        attribute_verified_run(output_dir)


def test_verified_run_rejects_dataset_order_mismatch(tmp_path: Path) -> None:
    """Matching bytes cannot override an identity with a different case order."""
    dataset_path = tmp_path / "cases.jsonl"
    content = _dataset_bytes([_case("c2"), _case("c1")])
    dataset_path.write_bytes(content)
    output_dir = tmp_path / "run"
    _publish_bundle(
        output_dir,
        dataset_path=dataset_path,
        identity=_identity(dataset_path, content, ["c1", "c2"]),
        results=[_result("c1"), _result("c2")],
    )

    with pytest.raises(ValueError, match="ordered case IDs"):
        attribute_verified_run(output_dir)


def test_verified_run_rejects_unavailable_dataset_fingerprint(tmp_path: Path) -> None:
    """A completed run without a dataset fingerprint cannot join case evidence."""
    dataset_path = tmp_path / "cases.jsonl"
    content = _dataset_bytes([_case("c1")])
    dataset_path.write_bytes(content)
    identity = build_run_identity(
        ordered_case_ids=["c1"],
        dataset_path=str(dataset_path),
        dataset_fingerprint=None,
        split_fingerprint=None,
        scorer_fingerprint=None,
        metric_fingerprint=None,
    ).to_dict()
    output_dir = tmp_path / "run"
    _publish_bundle(
        output_dir,
        dataset_path=dataset_path,
        identity=identity,
        results=[_result("c1")],
    )

    with pytest.raises(ValueError, match="dataset fingerprint is unavailable"):
        attribute_verified_run(output_dir)


def test_verified_run_never_falls_back_to_loose_result_files(tmp_path: Path) -> None:
    """An unauthoritative output directory cannot trigger a protected join."""
    output_dir = tmp_path / "loose-run"
    output_dir.mkdir()
    (output_dir / "results.jsonl").write_text(
        json.dumps(_result("c1")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="bundle.*inventory"):
        attribute_verified_run(output_dir)
