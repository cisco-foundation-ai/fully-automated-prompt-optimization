# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import json
import threading
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.hephaestus import local_authority_io as authority_io
from src.hephaestus.artifact_io import atomic_write_bytes_at
from src.hephaestus.types import EvalCaseResult, EvalProgress


class ProgressTracker:
    """Thread-safe tracker that persists progress after each case."""

    def __init__(
        self,
        output_dir: Path,
        total_cases: int,
        run_id: str = "",
        case_ids: Sequence[str] | None = None,
        *,
        progress_sink: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        if total_cases < 0:
            raise ValueError("total_cases cannot be negative")
        if case_ids is not None:
            ordered_case_ids = list(case_ids)
            if len(ordered_case_ids) != total_cases:
                raise ValueError("case_ids length must equal total_cases")
            if len(set(ordered_case_ids)) != len(ordered_case_ids):
                raise ValueError("case_ids must be unique")
        else:
            ordered_case_ids = []
        if progress_sink is not None and not callable(progress_sink):
            raise TypeError("progress_sink must be callable")

        self._output_dir = output_dir
        self._progress_sink = progress_sink
        self._directory_identity: tuple[int, int, int] | None = None
        if progress_sink is None:
            directory = authority_io.open_or_create_bound_directory(self._output_dir)
            try:
                self._directory_identity = directory.identity
            finally:
                directory.close()
        self._lock = threading.Lock()
        self._has_case_order = case_ids is not None
        self._case_order = {
            case_id: index for index, case_id in enumerate(ordered_case_ids)
        }
        self._attempted_case_ids: set[str] = set()
        self._successful_case_ids: set[str] = set()
        self._failed_case_ids: set[str] = set()
        self._in_flight_case_ids: set[str] = set()

        now = datetime.now(timezone.utc).isoformat()
        self._progress = EvalProgress(
            status="running",
            total_cases=total_cases,
            completed_cases=0,
            started_at=now,
            updated_at=now,
            avg_composite_score=None,
            score_breakdown_averages={},
            failed_case_ids=[],
            run_id=run_id,
        )
        self._score_sum: float = 0.0
        self._breakdown_sums: dict[str, float] = {}
        self._points_earned_sum: float = 0.0
        self._points_possible_sum: float = 0.0
        self._trust_tier_stats: dict[str, dict[str, float | int]] = {}
        self._write()

    def record_start(self, case_id: str) -> None:
        """Mark a case as in-flight."""
        with self._lock:
            self._validate_case_id(case_id)
            if case_id not in self._attempted_case_ids:
                self._in_flight_case_ids.add(case_id)
            self._sync_case_ids()
            self._progress.updated_at = datetime.now(timezone.utc).isoformat()
            self._write()

    def record_result(self, result: EvalCaseResult) -> None:
        with self._lock:
            self._validate_case_id(result.case_id)
            if result.case_id in self._attempted_case_ids:
                raise ValueError(f"result already recorded for case_id {result.case_id!r}")

            self._in_flight_case_ids.discard(result.case_id)
            self._attempted_case_ids.add(result.case_id)
            if result.execution_status == "succeeded":
                self._record_success(result)
            else:
                self._failed_case_ids.add(result.case_id)
            self._record_trust_tier(result)
            self._sync_case_ids()

            self._progress.updated_at = datetime.now(timezone.utc).isoformat()
            self._write()

    def mark_completed(self) -> None:
        with self._lock:
            if (
                self._progress.total_cases > 0
                and self._progress.successful_cases == self._progress.total_cases
                and self._progress.completed_cases == self._progress.total_cases
            ):
                self._progress.status = "completed"
            elif self._progress.successful_cases > 0:
                self._progress.status = "degraded"
            else:
                self._progress.status = "failed"
            self._progress.updated_at = datetime.now(timezone.utc).isoformat()
            self._write()

    def mark_failed(self) -> None:
        with self._lock:
            self._progress.status = "failed"
            self._progress.updated_at = datetime.now(timezone.utc).isoformat()
            self._write()

    def snapshot(self) -> EvalProgress:
        with self._lock:
            return EvalProgress(
                status=self._progress.status,
                total_cases=self._progress.total_cases,
                completed_cases=self._progress.completed_cases,
                started_at=self._progress.started_at,
                updated_at=self._progress.updated_at,
                avg_composite_score=self._progress.avg_composite_score,
                score_breakdown_averages=dict(self._progress.score_breakdown_averages),
                failed_case_ids=list(self._progress.failed_case_ids),
                in_flight_case_ids=list(self._progress.in_flight_case_ids),
                run_id=self._progress.run_id,
                successful_cases=self._progress.successful_cases,
                attempted_case_ids=list(self._progress.attempted_case_ids),
                successful_case_ids=list(self._progress.successful_case_ids),
                trust_tier_summaries={
                    tier: dict(summary)
                    for tier, summary in self._progress.trust_tier_summaries.items()
                },
            )

    def snapshot_payload(self) -> dict[str, Any]:
        """Return an isolated copy of the full persisted progress payload."""
        with self._lock:
            return self._payload()

    def _record_success(self, result: EvalCaseResult) -> None:
        self._successful_case_ids.add(result.case_id)
        self._score_sum += result.composite_score
        successful_cases = len(self._successful_case_ids)
        self._progress.avg_composite_score = self._score_sum / successful_cases

        for key, value in result.score_breakdown.items():
            if isinstance(value, (int, float)):
                self._breakdown_sums[key] = self._breakdown_sums.get(key, 0.0) + value
        self._progress.score_breakdown_averages = {
            key: value / successful_cases for key, value in self._breakdown_sums.items()
        }

        breakdown = result.score_breakdown
        if "points_earned" in breakdown and "points_possible" in breakdown:
            self._points_earned_sum += float(breakdown["points_earned"])
            self._points_possible_sum += float(breakdown["points_possible"])

    def _record_trust_tier(self, result: EvalCaseResult) -> None:
        trust_tier = result.evaluation_provenance.get("trust_tier")
        if trust_tier is None:
            return
        stats = self._trust_tier_stats.setdefault(
            trust_tier,
            {
                "total_cases": 0,
                "successful_cases": 0,
                "failed_cases": 0,
                "score_sum": 0.0,
            },
        )
        stats["total_cases"] += 1
        if result.execution_status == "succeeded":
            stats["successful_cases"] += 1
            stats["score_sum"] += result.composite_score
        else:
            stats["failed_cases"] += 1
        self._progress.trust_tier_summaries = self._trust_tier_summaries()

    def _trust_tier_summaries(self) -> dict[str, dict[str, Any]]:
        summaries: dict[str, dict[str, Any]] = {}
        for trust_tier in sorted(self._trust_tier_stats):
            stats = self._trust_tier_stats[trust_tier]
            successful_cases = int(stats["successful_cases"])
            summaries[trust_tier] = {
                "total_cases": int(stats["total_cases"]),
                "successful_cases": successful_cases,
                "failed_cases": int(stats["failed_cases"]),
                "mean_composite_score": (
                    float(stats["score_sum"]) / successful_cases
                    if successful_cases > 0
                    else None
                ),
            }
        return summaries

    def _validate_case_id(self, case_id: str) -> None:
        if self._has_case_order and case_id not in self._case_order:
            raise ValueError(f"case_id {case_id!r} is not in the ordered case list")

    def _ordered(self, case_ids: set[str]) -> list[str]:
        if self._has_case_order:
            return sorted(case_ids, key=self._case_order.__getitem__)
        return sorted(case_ids)

    def _sync_case_ids(self) -> None:
        self._progress.completed_cases = len(self._attempted_case_ids)
        self._progress.successful_cases = len(self._successful_case_ids)
        self._progress.attempted_case_ids = self._ordered(self._attempted_case_ids)
        self._progress.successful_case_ids = self._ordered(self._successful_case_ids)
        self._progress.failed_case_ids = self._ordered(self._failed_case_ids)
        self._progress.in_flight_case_ids = self._ordered(self._in_flight_case_ids)

    def _payload(self) -> dict[str, Any]:
        weighted_avg = (
            (self._points_earned_sum / self._points_possible_sum * 100.0)
            if self._points_possible_sum > 0
            else None
        )
        return copy.deepcopy(
            {
                "run_id": self._progress.run_id,
                "status": self._progress.status,
                "total_cases": self._progress.total_cases,
                "completed_cases": self._progress.completed_cases,
                "successful_cases": self._progress.successful_cases,
                "started_at": self._progress.started_at,
                "updated_at": self._progress.updated_at,
                "avg_composite_score": self._progress.avg_composite_score,
                "weighted_avg_score": weighted_avg,
                "score_breakdown_averages": self._progress.score_breakdown_averages,
                "failed_case_ids": self._progress.failed_case_ids,
                "attempted_case_ids": self._progress.attempted_case_ids,
                "successful_case_ids": self._progress.successful_case_ids,
                "in_flight_case_ids": self._progress.in_flight_case_ids,
                "trust_tier_summaries": self._progress.trust_tier_summaries,
            }
        )

    def _write(self) -> None:
        """Persist progress through its owner or one bound standalone writer."""
        data = self._payload()
        if self._progress_sink is not None:
            self._progress_sink(data)
            return

        content = json.dumps(data, indent=2).encode("utf-8")
        directory = authority_io.open_bound_directory(self._output_dir)
        try:
            if directory.identity != self._directory_identity:
                raise ValueError("progress output directory identity changed")
            atomic_write_bytes_at(directory, "progress.json", content)
        finally:
            directory.close()


def read_progress(output_dir: Path) -> Optional[EvalProgress]:
    """Read and deserialize ``progress.json``. Returns ``None`` if missing."""
    path = output_dir / "progress.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return EvalProgress(
        status=data["status"],
        total_cases=data["total_cases"],
        completed_cases=data["completed_cases"],
        started_at=data["started_at"],
        updated_at=data["updated_at"],
        avg_composite_score=data["avg_composite_score"],
        score_breakdown_averages=data.get("score_breakdown_averages", {}),
        failed_case_ids=data.get("failed_case_ids", []),
        in_flight_case_ids=data.get("in_flight_case_ids", []),
        run_id=data.get("run_id", ""),
        successful_cases=data.get(
            "successful_cases",
            max(0, data["completed_cases"] - len(data.get("failed_case_ids", []))),
        ),
        attempted_case_ids=data.get("attempted_case_ids", []),
        successful_case_ids=data.get("successful_case_ids", []),
        trust_tier_summaries=data.get("trust_tier_summaries", {}),
    )
