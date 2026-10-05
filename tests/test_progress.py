# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

import copy
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from src.hephaestus.runs.progress import ProgressTracker, read_progress
from src.hephaestus.types import EvalCaseResult


def _make_result(
    case_id: str = "c1",
    composite_score: float = 80.0,
    breakdown: dict | None = None,
    *,
    execution_status: str = "succeeded",
    execution_error: dict[str, str] | None = None,
    evaluation_provenance: dict[str, Any] | None = None,
) -> EvalCaseResult:
    return EvalCaseResult(
        case_id=case_id,
        task_type="security",
        diagnostics=[],
        score_breakdown=breakdown or {"quality": 90.0, "format": 70.0},
        composite_score=composite_score,
        output_text="output",
        step_outputs={},
        execution_status=execution_status,
        execution_error=execution_error,
        evaluation_provenance=evaluation_provenance or {},
    )


def test_initial_state(tmp_path: Path) -> None:
    tracker = ProgressTracker(tmp_path / "out", total_cases=5)
    snap = tracker.snapshot()
    assert snap.status == "running"
    assert snap.total_cases == 5
    assert snap.completed_cases == 0
    assert snap.avg_composite_score is None
    assert snap.score_breakdown_averages == {}
    assert snap.failed_case_ids == []


def test_progress_sink_owns_persistence_without_creating_an_output_directory(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "sink-owned-output"
    payloads: list[str] = []

    tracker = ProgressTracker(
        output_dir,
        total_cases=1,
        run_id="run-001",
        case_ids=["case-1"],
        progress_sink=lambda payload: payloads.append(
            json.dumps(payload, sort_keys=True)
        ),
    )
    tracker.record_result(_make_result("case-1"))
    tracker.mark_completed()

    assert not output_dir.exists()
    assert len(payloads) == 3
    assert json.loads(payloads[-1]) == {
        "attempted_case_ids": ["case-1"],
        "avg_composite_score": 80.0,
        "completed_cases": 1,
        "failed_case_ids": [],
        "in_flight_case_ids": [],
        "run_id": "run-001",
        "score_breakdown_averages": {"format": 70.0, "quality": 90.0},
        "started_at": tracker.snapshot().started_at,
        "status": "completed",
        "successful_case_ids": ["case-1"],
        "successful_cases": 1,
        "total_cases": 1,
        "trust_tier_summaries": {},
        "updated_at": tracker.snapshot().updated_at,
        "weighted_avg_score": None,
    }


def test_snapshot_payload_matches_the_sink_and_is_deep_copied(tmp_path: Path) -> None:
    payloads: list[dict[str, Any]] = []

    def capture(payload: Any) -> None:
        payloads.append(copy.deepcopy(dict(payload)))

    tracker = ProgressTracker(
        tmp_path / "sink-owned-output",
        total_cases=1,
        run_id="run-001",
        case_ids=["case-1"],
        progress_sink=capture,
    )
    tracker.record_result(
        _make_result(
            "case-1",
            breakdown={
                "quality": 80.0,
                "points_earned": 1.0,
                "points_possible": 2.0,
            },
            evaluation_provenance={"trust_tier": "trusted_feedback"},
        )
    )
    tracker.mark_completed()

    payload = tracker.snapshot_payload()
    assert payload == payloads[-1]
    assert payload["weighted_avg_score"] == 50.0

    payload["attempted_case_ids"].append("forged-case")
    payload["score_breakdown_averages"]["quality"] = -1.0
    payload["trust_tier_summaries"]["trusted_feedback"]["total_cases"] = 99

    assert tracker.snapshot_payload() == payloads[-1]


def test_standalone_progress_does_not_follow_a_fixed_temporary_symlink(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    victim = tmp_path / "victim.txt"
    victim.write_bytes(b"ORIGINAL")
    planted = output_dir / "progress.json.tmp"
    try:
        planted.symlink_to(victim)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks are unavailable: {exc}")

    ProgressTracker(output_dir, total_cases=0, run_id="run-001", case_ids=[])

    assert victim.read_bytes() == b"ORIGINAL"
    assert planted.is_symlink()
    assert (output_dir / "progress.json").is_file()
    assert not (output_dir / "progress.json").is_symlink()


def test_standalone_progress_rejects_a_symlinked_intermediate_ancestor(
    tmp_path: Path,
) -> None:
    external = tmp_path / "external"
    external.mkdir()
    linked_parent = tmp_path / "linked-parent"
    try:
        linked_parent.symlink_to(external, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(ValueError, match="ancestor"):
        ProgressTracker(
            linked_parent / "nested" / "out",
            total_cases=0,
            run_id="run-001",
            case_ids=[],
        )

    assert list(external.iterdir()) == []


def test_standalone_progress_rejects_a_symlinked_output_directory(
    tmp_path: Path,
) -> None:
    external = tmp_path / "external"
    external.mkdir()
    output_dir = tmp_path / "linked-output"
    try:
        output_dir.symlink_to(external, target_is_directory=True)
    except OSError as exc:  # pragma: no cover - platform privilege dependent
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(ValueError):
        ProgressTracker(
            output_dir,
            total_cases=0,
            run_id="run-001",
            case_ids=[],
        )

    assert list(external.iterdir()) == []


def test_record_result_updates_count_and_averages(tmp_path: Path) -> None:
    tracker = ProgressTracker(tmp_path / "out", total_cases=2)

    tracker.record_result(_make_result("c1", 80.0, {"quality": 90.0, "format": 70.0}))
    snap = tracker.snapshot()
    assert snap.completed_cases == 1
    assert snap.avg_composite_score == 80.0
    assert snap.score_breakdown_averages == {"quality": 90.0, "format": 70.0}

    tracker.record_result(_make_result("c2", 60.0, {"quality": 70.0, "format": 50.0}))
    snap = tracker.snapshot()
    assert snap.completed_cases == 2
    assert snap.avg_composite_score == 70.0
    assert snap.score_breakdown_averages == {"quality": 80.0, "format": 60.0}


def test_progress_json_is_valid_after_each_write(tmp_path: Path) -> None:
    out = tmp_path / "out"
    tracker = ProgressTracker(out, total_cases=3)

    data = json.loads((out / "progress.json").read_text(encoding="utf-8"))
    assert data["status"] == "running"
    assert data["completed_cases"] == 0

    tracker.record_result(_make_result())
    data = json.loads((out / "progress.json").read_text(encoding="utf-8"))
    assert data["completed_cases"] == 1


def test_no_lingering_tmp_file(tmp_path: Path) -> None:
    out = tmp_path / "out"
    tracker = ProgressTracker(out, total_cases=1)
    tracker.record_result(_make_result())
    assert not (out / "progress.json.tmp").exists()


def test_mark_completed_sets_status(tmp_path: Path) -> None:
    tracker = ProgressTracker(tmp_path / "out", total_cases=1)
    tracker.record_result(_make_result())
    tracker.mark_completed()
    snap = tracker.snapshot()
    assert snap.status == "completed"


def test_mark_failed_sets_status(tmp_path: Path) -> None:
    tracker = ProgressTracker(tmp_path / "out", total_cases=2)
    tracker.record_result(_make_result())
    tracker.mark_failed()
    snap = tracker.snapshot()
    assert snap.status == "failed"
    assert snap.completed_cases == 1  # Partial progress is preserved


def test_thread_safety_concurrent_records(tmp_path: Path) -> None:
    n = 50
    tracker = ProgressTracker(tmp_path / "out", total_cases=n)

    def record(i: int) -> None:
        tracker.record_result(_make_result(f"c{i}", 100.0, {"q": 100.0}))

    threads = [threading.Thread(target=record, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    snap = tracker.snapshot()
    assert snap.completed_cases == n
    assert snap.avg_composite_score == 100.0


def test_progress_includes_run_id(tmp_path: Path) -> None:
    out = tmp_path / "out"
    tracker = ProgressTracker(out, total_cases=1, run_id="hephaestus-demo-m5kx7r")
    tracker.record_result(_make_result())
    tracker.mark_completed()

    data = json.loads((out / "progress.json").read_text(encoding="utf-8"))
    assert data["run_id"] == "hephaestus-demo-m5kx7r"

    snap = tracker.snapshot()
    assert snap.run_id == "hephaestus-demo-m5kx7r"


def test_read_progress_returns_run_id(tmp_path: Path) -> None:
    out = tmp_path / "out"
    tracker = ProgressTracker(out, total_cases=1, run_id="hephaestus-demo-abc123")
    tracker.record_result(_make_result())
    tracker.mark_completed()

    progress = read_progress(out)
    assert progress is not None
    assert progress.run_id == "hephaestus-demo-abc123"


def test_read_progress_missing_run_id_defaults_empty(tmp_path: Path) -> None:
    """Old progress.json without run_id should default to empty string."""
    out = tmp_path / "out"
    out.mkdir(parents=True)
    data = {
        "status": "completed",
        "total_cases": 1,
        "completed_cases": 1,
        "started_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "avg_composite_score": 80.0,
        "score_breakdown_averages": {},
        "failed_case_ids": [],
    }
    (out / "progress.json").write_text(json.dumps(data), encoding="utf-8")

    progress = read_progress(out)
    assert progress is not None
    assert progress.run_id == ""
    assert progress.successful_cases == 1
    assert progress.attempted_case_ids == []
    assert progress.successful_case_ids == []
    assert progress.trust_tier_summaries == {}


def test_read_progress_returns_none_when_missing(tmp_path: Path) -> None:
    assert read_progress(tmp_path / "nonexistent") is None


def test_read_progress_deserializes_written_file(tmp_path: Path) -> None:
    out = tmp_path / "out"
    tracker = ProgressTracker(out, total_cases=1)
    tracker.record_result(_make_result("c1", 90.0, {"quality": 90.0}))
    tracker.mark_completed()

    progress = read_progress(out)
    assert progress is not None
    assert progress.status == "completed"
    assert progress.total_cases == 1
    assert progress.completed_cases == 1
    assert progress.avg_composite_score == 90.0
    assert progress.score_breakdown_averages == {"quality": 90.0}


def test_mixed_results_use_successful_only_scores_and_dataset_order(
    tmp_path: Path,
) -> None:
    """Failed cases must not dilute scores or acquire completion-order IDs."""
    from src.hephaestus.runs.errors import build_execution_error

    tracker = ProgressTracker(
        tmp_path / "out",
        total_cases=3,
        case_ids=["case-b", "case-a", "case-c"],
    )

    tracker.record_start("case-c")
    tracker.record_result(
        _make_result(
            "case-c",
            composite_score=100.0,
            breakdown={"quality": 100.0},
            execution_status="failed",
            execution_error=build_execution_error("chain", "connection"),
        )
    )
    tracker.record_result(_make_result("case-b", composite_score=0.0, breakdown={"quality": 0.0}))
    tracker.record_result(
        _make_result(
            "case-a",
            composite_score=75.0,
            breakdown={"quality": 75.0},
            execution_status="failed",
            execution_error=build_execution_error("scorer", "invalid_response"),
        )
    )
    tracker.mark_completed()

    snap = tracker.snapshot()
    assert snap.status == "degraded"
    assert snap.completed_cases == 3
    assert snap.successful_cases == 1
    assert snap.avg_composite_score == 0.0
    assert snap.score_breakdown_averages == {"quality": 0.0}
    assert snap.attempted_case_ids == ["case-b", "case-a", "case-c"]
    assert snap.successful_case_ids == ["case-b"]
    assert snap.failed_case_ids == ["case-a", "case-c"]
    assert snap.in_flight_case_ids == []


def test_all_failed_results_produce_failed_terminal_status(tmp_path: Path) -> None:
    """A run with no successful cases must not look like a zero-scoring run."""
    from src.hephaestus.runs.errors import build_execution_error

    tracker = ProgressTracker(
        tmp_path / "out",
        total_cases=2,
        case_ids=["case-2", "case-1"],
    )
    for case_id in ("case-1", "case-2"):
        tracker.record_result(
            _make_result(
                case_id,
                composite_score=0.0,
                breakdown={"quality": 0.0},
                execution_status="failed",
                execution_error=build_execution_error("chain", "runtime"),
            )
        )
    tracker.mark_completed()

    snap = tracker.snapshot()
    assert snap.status == "failed"
    assert snap.successful_cases == 0
    assert snap.avg_composite_score is None
    assert snap.score_breakdown_averages == {}
    assert snap.failed_case_ids == ["case-2", "case-1"]


def test_successful_zero_score_produces_completed_terminal_status(tmp_path: Path) -> None:
    """A legitimate zero score remains a successful completed evaluation."""
    tracker = ProgressTracker(
        tmp_path / "out",
        total_cases=1,
        case_ids=["zero-score"],
    )
    tracker.record_result(
        _make_result("zero-score", composite_score=0.0, breakdown={"quality": 0.0})
    )
    tracker.mark_completed()

    snap = tracker.snapshot()
    assert snap.status == "completed"
    assert snap.successful_cases == 1
    assert snap.successful_case_ids == ["zero-score"]
    assert snap.failed_case_ids == []
    assert snap.avg_composite_score == 0.0


def test_progress_summarizes_only_allowlisted_trust_tiers(tmp_path: Path) -> None:
    """Trust summaries must ignore arbitrary metadata and failed-case scores."""
    from src.hephaestus.runs.errors import build_execution_error

    tracker = ProgressTracker(
        tmp_path / "out",
        total_cases=3,
        case_ids=["trusted-ok", "trusted-failed", "synthetic-ok"],
    )
    tracker.record_result(
        _make_result(
            "trusted-ok",
            composite_score=80.0,
            breakdown={"quality": 80.0},
            evaluation_provenance={
                "trust_tier": "trusted_feedback",
                "expected": {"answer": "must-not-persist"},
            },
        )
    )
    tracker.record_result(
        _make_result(
            "trusted-failed",
            composite_score=100.0,
            breakdown={"quality": 100.0},
            execution_status="failed",
            execution_error=build_execution_error("scorer", "runtime"),
            evaluation_provenance={"trust_tier": "trusted_feedback"},
        )
    )
    tracker.record_result(
        _make_result(
            "synthetic-ok",
            composite_score=20.0,
            breakdown={"quality": 20.0},
            evaluation_provenance={
                "trust_tier": "synthetic_from_trusted_rubric",
                "context": {"secret": "must-not-persist"},
            },
        )
    )

    data = json.loads((tmp_path / "out" / "progress.json").read_text(encoding="utf-8"))
    assert data["trust_tier_summaries"] == {
        "synthetic_from_trusted_rubric": {
            "total_cases": 1,
            "successful_cases": 1,
            "failed_cases": 0,
            "mean_composite_score": 20.0,
        },
        "trusted_feedback": {
            "total_cases": 2,
            "successful_cases": 1,
            "failed_cases": 1,
            "mean_composite_score": 80.0,
        },
    }
    serialized = json.dumps(data)
    assert "must-not-persist" not in serialized
    assert "expected" not in serialized
    assert "context" not in serialized


def test_read_progress_preserves_new_outcome_fields(tmp_path: Path) -> None:
    """The persisted outcome identities and summaries must survive a read."""
    tracker = ProgressTracker(
        tmp_path / "out",
        total_cases=1,
        case_ids=["case-1"],
    )
    tracker.record_result(
        _make_result(
            "case-1",
            composite_score=40.0,
            evaluation_provenance={"trust_tier": "inferred_from_trusted_feedback"},
        )
    )
    tracker.mark_completed()

    progress = read_progress(tmp_path / "out")
    assert progress is not None
    assert progress.successful_cases == 1
    assert progress.attempted_case_ids == ["case-1"]
    assert progress.successful_case_ids == ["case-1"]
    assert progress.failed_case_ids == []
    assert progress.trust_tier_summaries == {
        "inferred_from_trusted_feedback": {
            "total_cases": 1,
            "successful_cases": 1,
            "failed_cases": 0,
            "mean_composite_score": 40.0,
        }
    }
