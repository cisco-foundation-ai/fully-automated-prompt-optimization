# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Dict, List

from src.hephaestus.artifact_io import (
    atomic_write_json,
    atomic_write_jsonl,
    atomic_write_text,
)
from src.hephaestus.evaluation_assets.trust_tiers import CURRENT_TRUST_TIERS


def _normalize_timings(timings: Any) -> List[List]:
    """Convert step_timings to list-of-lists format (handles old dict format)."""
    if isinstance(timings, dict):
        return [[k, v] for k, v in timings.items()]
    return timings or []


def _is_successful(item: Mapping[str, Any]) -> bool:
    return item.get("execution_status", "succeeded") == "succeeded"


def render_summary(
    results: Sequence[Mapping[str, Any]],
    *,
    cases: Sequence[Any] | None = None,
) -> str:
    """Render successful-only metrics plus separate infrastructure diagnostics."""

    results_list = list(results)
    successful_results = [item for item in results_list if _is_successful(item)]
    total = len(results_list)
    successful_count = len(successful_results)
    infrastructure_failures = total - successful_count
    scores: List[float] = []
    breakdown_totals: Dict[str, float] = {}
    for item in successful_results:
        scores.append(float(item.get("composite_score", 0.0)))
        for key, value in item.get("score_breakdown", {}).items():
            breakdown_totals[key] = breakdown_totals.get(key, 0.0) + float(value)

    lines = [
        "# Evaluation Summary",
        "",
        f"Total cases: {total}",
        f"Successful cases: {successful_count}",
        f"Infrastructure failures: {infrastructure_failures}",
        "",
    ]
    if scores:
        lines.append("## Composite Score")
        lines.append(f"- average: {sum(scores)/len(scores):.2f}")
        lines.append("")
    if breakdown_totals:
        lines.append("## Score Breakdown")
        for key in sorted(breakdown_totals):
            average = breakdown_totals[key] / successful_count
            lines.append(f"- {key}: {average:.2f}")

    # Point-weighted score (for scoring schemes with earned/possible points)
    if "points_earned" in breakdown_totals and "points_possible" in breakdown_totals:
        total_earned = breakdown_totals["points_earned"]
        total_possible = breakdown_totals["points_possible"]
        weighted_score = (total_earned / total_possible * 100.0) if total_possible > 0 else 0.0
        lines.append("")
        lines.append("## Weighted Score")
        lines.append(f"- weighted_score: {weighted_score:.2f}")
        lines.append(f"- total_earned: {total_earned:.0f}")
        lines.append(f"- total_possible: {total_possible:.0f}")

    # Step timings section
    step_timings_by_name: Dict[str, List[float]] = {}
    case_totals: List[float] = []
    for item in successful_results:
        trace = _normalize_timings(item.get("step_timings"))
        if trace:
            case_totals.append(sum(d for _, d in trace))
            for step_name, duration in trace:
                step_timings_by_name.setdefault(step_name, []).append(duration)

    if step_timings_by_name:
        lines.append("")
        lines.append("## Step Timings")
        lines.append("")
        lines.append("| Step | Avg (s) | P50 (s) | P95 (s) |")
        lines.append("|------|---------|---------|---------|")
        for step_name in step_timings_by_name:
            vals = step_timings_by_name[step_name]
            avg = statistics.mean(vals)
            p50 = statistics.median(vals)
            p95 = sorted(vals)[int(math.ceil(len(vals) * 0.95)) - 1] if len(vals) > 1 else vals[0]
            lines.append(f"| {step_name} | {avg:.3f} | {p50:.3f} | {p95:.3f} |")
        if case_totals:
            avg_total = statistics.mean(case_totals)
            p50_total = statistics.median(case_totals)
            p95_total = (
                sorted(case_totals)[int(math.ceil(len(case_totals) * 0.95)) - 1]
                if len(case_totals) > 1
                else case_totals[0]
            )
            lines.append(f"| **Total** | **{avg_total:.3f}** | **{p50_total:.3f}** | **{p95_total:.3f}** |")

    tier_stats: Dict[str, Dict[str, float | int]] = {}
    for item in results_list:
        provenance = item.get("evaluation_provenance", {})
        trust_tier = (
            provenance.get("trust_tier")
            if isinstance(provenance, Mapping)
            else None
        )
        if trust_tier not in CURRENT_TRUST_TIERS:
            continue
        stats = tier_stats.setdefault(
            str(trust_tier),
            {"total": 0, "successful": 0, "failed": 0, "score_sum": 0.0},
        )
        stats["total"] += 1
        if _is_successful(item):
            stats["successful"] += 1
            stats["score_sum"] += float(item.get("composite_score", 0.0))
        else:
            stats["failed"] += 1

    if tier_stats:
        lines.extend(
            [
                "",
                "## Trust-Tier Diagnostics",
                "",
                "| Trust tier | Total | Successful | Failed | Mean composite score |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for trust_tier in sorted(tier_stats):
            stats = tier_stats[trust_tier]
            tier_successes = int(stats["successful"])
            mean = (
                f"{float(stats['score_sum']) / tier_successes:.2f}"
                if tier_successes
                else "N/A"
            )
            lines.append(
                f"| {trust_tier} | {int(stats['total'])} | {tier_successes} "
                f"| {int(stats['failed'])} | {mean} |"
            )

    # Step attribution uses protected evidence only through the caller-supplied
    # in-memory cases; neither those cases nor an intermediate join is written.
    has_step_outputs = any(item.get("step_outputs") for item in results_list)
    has_failures = infrastructure_failures > 0 or any(
        float(item.get("composite_score", 0)) < 100.0
        for item in successful_results
    )
    if has_step_outputs and has_failures:
        from src.hephaestus.analysis.step_attribution import (
            INFRASTRUCTURE_FAILURE_KEY,
            attribute_results,
        )

        attribution = attribute_results(results_list, cases)
        infrastructure = attribution.pop(INFRASTRUCTURE_FAILURE_KEY, None)
        if infrastructure:
            lines.extend(
                [
                    "",
                    "## Infrastructure Failures",
                    "",
                    f"- failed cases: {int(infrastructure['count'])}",
                ]
            )
        if attribution:
            lines.extend(
                [
                    "",
                    "## Step Attribution",
                    "",
                    "| Step | Failure Count |",
                    "|------|--------------|",
                ]
            )
            for step_name in sorted(
                attribution,
                key=lambda name: attribution[name]["count"],
                reverse=True,
            ):
                lines.append(f"| {step_name} | {attribution[step_name]['count']} |")

    return "\n".join(lines) + "\n"


def write_outputs(output_dir: Path, run_config: Dict, results: Iterable[Dict]) -> None:
    """Compatibility writer for callers outside the authoritative bundle path."""

    results_list: List[Dict] = list(results)
    atomic_write_json(output_dir / "run_config.json", run_config)
    atomic_write_jsonl(output_dir / "results.jsonl", results_list)
    atomic_write_text(output_dir / "summary.md", render_summary(results_list))
