# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Controlled comparison of manifest-authenticated evaluation runs."""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.hephaestus.runs.bundle import ValidatedRunBundle, load_run_bundle
from src.hephaestus.runs.identity import ALLOWED_VARIANT_DIMENSIONS
from src.hephaestus.runs.io_utils import _normalize_timings


@dataclass(frozen=True)
class ComparisonIssue:
    """One machine-readable reason a run comparison is not controlled."""

    code: str
    message: str
    baseline: object | None = None
    candidate: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        """Return the safe public representation of the issue."""
        return {
            "code": self.code,
            "message": self.message,
            "baseline": self.baseline,
            "candidate": self.candidate,
        }


class RunComparisonError(ValueError):
    """Base class for a structured rejected run comparison."""

    def __init__(self, message: str, issues: Sequence[ComparisonIssue]) -> None:
        self.issues = tuple(issues)
        detail = "; ".join(issue.code for issue in self.issues)
        super().__init__(f"{message}: {detail}" if detail else message)


class RunComparisonBundleError(RunComparisonError):
    """A bundle is unauthenticated, invalid, or not completed."""


class RunComparisonIncompatibilityError(RunComparisonError):
    """Authenticated completed bundles do not establish controlled comparability."""


def _usable_tenant_id(value: object) -> str | None:
    """Return one safe tenant identity, never a path-like alias."""
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
    ):
        return None
    return value


def compare_runs(
    baseline_dir: Path,
    candidate_dir: Path,
    *,
    exploratory: bool = False,
) -> dict[str, Any]:
    """Compare two completed, manifest-authenticated evaluation bundles.

    Default operation refuses a score comparison unless permanent controls,
    undeclared dimensions, and variant declarations prove compatibility. An
    explicit exploratory comparison retains all incompatibility evidence but
    never upgrades invalid or non-completed bundles into eligible inputs.
    """
    baseline, candidate = _load_completed_bundles(baseline_dir, candidate_dir)
    result_issues = _comparison_result_issues(baseline.results, candidate.results)
    if result_issues:
        raise RunComparisonBundleError(
            "run bundle score eligibility failed",
            result_issues,
        )
    incompatibilities, variant_differences = _compatibility(
        baseline.run_identity,
        candidate.run_identity,
    )
    if incompatibilities and not exploratory:
        raise RunComparisonIncompatibilityError(
            "run comparison is not controlled",
            incompatibilities,
        )

    comparison = _compare_results(baseline.results, candidate.results)
    effective_exploratory = exploratory and bool(incompatibilities)
    compatibility = {
        "controlled": not incompatibilities,
        "exploratory": effective_exploratory,
        "uncontrolled": bool(incompatibilities),
        "incompatibilities": [issue.to_dict() for issue in incompatibilities],
        "variant_differences": variant_differences,
    }
    comparison["compatibility"] = compatibility
    comparison["summary_md"] = _build_summary(
        comparison["composite_delta"],
        comparison["check_deltas"],
        comparison["timing_deltas"],
        comparison["regressions"],
        comparison["improvements"],
        compatibility=compatibility,
    )
    return comparison


def _load_completed_bundles(
    baseline_dir: Path,
    candidate_dir: Path,
) -> tuple[ValidatedRunBundle, ValidatedRunBundle]:
    loaded: list[ValidatedRunBundle | None] = []
    issues: list[ComparisonIssue] = []
    tenant_ids: dict[str, str] = {}
    for role, output_dir in (("baseline", baseline_dir), ("candidate", candidate_dir)):
        try:
            bundle = load_run_bundle(output_dir)
        except (OSError, ValueError):
            issues.append(
                ComparisonIssue(
                    code=f"{role}.bundle.not_manifest_authenticated",
                    message=(
                        f"{role} is not a complete manifest-authenticated run bundle"
                    ),
                )
            )
            loaded.append(None)
            continue
        if bundle.status != "completed":
            issues.append(
                ComparisonIssue(
                    code=f"{role}.bundle.not_completed",
                    message=(
                        f"{role} status must be completed, received {bundle.status!r}"
                    ),
                    baseline=bundle.status if role == "baseline" else None,
                    candidate=bundle.status if role == "candidate" else None,
                )
            )
        tenant_id = _usable_tenant_id(bundle.run_config.get("tenant_id"))
        if tenant_id is None:
            issues.append(
                ComparisonIssue(
                    code=f"{role}.run_config.tenant_id.unavailable",
                    message=f"{role} has no usable tenant identity",
                )
            )
        else:
            tenant_ids[role] = tenant_id
        loaded.append(bundle)

    if (
        tenant_ids.get("baseline") is not None
        and tenant_ids.get("candidate") is not None
        and tenant_ids["baseline"] != tenant_ids["candidate"]
    ):
        issues.append(
            ComparisonIssue(
                code="run_config.tenant_id.mismatch",
                message="baseline and candidate belong to different tenants",
            )
        )

    if issues:
        raise RunComparisonBundleError("run bundle eligibility failed", issues)
    baseline, candidate = loaded
    assert baseline is not None and candidate is not None
    return baseline, candidate


def _comparison_result_issues(
    baseline: Sequence[Mapping[str, Any]],
    candidate: Sequence[Mapping[str, Any]],
) -> list[ComparisonIssue]:
    issues: list[ComparisonIssue] = []
    breakdown_keys: dict[str, dict[str, list[str]]] = {}
    for role, results in (("baseline", baseline), ("candidate", candidate)):
        role_keys: dict[str, list[str]] = {}
        for result_index, result in enumerate(results):
            case_id = str(result["case_id"])
            prefix = f"{role}.results.{case_id}"
            if "composite_score" not in result:
                issues.append(
                    _role_issue(
                        role,
                        f"{prefix}.composite_score.missing",
                        f"{role} result {case_id!r} is missing composite_score",
                    )
                )
            else:
                _append_score_value_issue(
                    issues,
                    role=role,
                    code=f"{prefix}.composite_score",
                    message=f"{role} result {case_id!r} composite_score",
                    value=result["composite_score"],
                    maximum=100,
                )
            _append_timing_issues(
                issues,
                role=role,
                result_index=result_index,
                timings=result.get("step_timings"),
            )

            if "score_breakdown" not in result:
                issues.append(
                    _role_issue(
                        role,
                        f"{prefix}.score_breakdown.missing",
                        f"{role} result {case_id!r} is missing score_breakdown",
                    )
                )
                continue
            breakdown = result["score_breakdown"]
            if not isinstance(breakdown, Mapping):
                issues.append(
                    _role_issue(
                        role,
                        f"{prefix}.score_breakdown.not_object",
                        f"{role} result {case_id!r} score_breakdown is not an object",
                    )
                )
                continue

            valid_keys = True
            for name, value in breakdown.items():
                if not isinstance(name, str) or not name:
                    valid_keys = False
                    issues.append(
                        _role_issue(
                            role,
                            f"{prefix}.score_breakdown.key.invalid",
                            f"{role} result {case_id!r} has an invalid score_breakdown key",
                        )
                    )
                    continue
                _append_score_value_issue(
                    issues,
                    role=role,
                    code=f"{prefix}.score_breakdown.{name}",
                    message=f"{role} result {case_id!r} score_breakdown {name!r}",
                    value=value,
                    maximum=None,
                )
            if valid_keys:
                role_keys[case_id] = sorted(breakdown)
        breakdown_keys[role] = role_keys

    baseline_keys = breakdown_keys["baseline"]
    candidate_keys = breakdown_keys["candidate"]
    for case_id in sorted(set(baseline_keys) & set(candidate_keys)):
        if baseline_keys[case_id] != candidate_keys[case_id]:
            issues.append(
                ComparisonIssue(
                    code=f"results.{case_id}.score_breakdown_keys.mismatch",
                    message=(
                        f"score_breakdown metric coverage differs for case {case_id!r}"
                    ),
                    baseline=baseline_keys[case_id],
                    candidate=candidate_keys[case_id],
                )
            )
    return issues


def _append_timing_issues(
    issues: list[ComparisonIssue],
    *,
    role: str,
    result_index: int,
    timings: object,
) -> None:
    """Validate legacy and current timing representations without echoing values."""
    prefix = f"{role}.results.{result_index}.step_timings"
    if timings is None:
        return
    if isinstance(timings, Mapping):
        entries: list[object] = list(timings.items())
    elif isinstance(timings, list):
        entries = timings
    else:
        issues.append(
            _role_issue(
                role,
                f"{prefix}.not_collection",
                f"{role} result step_timings must be a list or object",
            )
        )
        return

    totals: dict[str, float] = {}
    for entry in entries:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            issues.append(
                _role_issue(
                    role,
                    f"{prefix}.entry.invalid",
                    f"{role} result has an invalid step_timings entry",
                )
            )
            continue
        name, duration = entry
        valid_name = isinstance(name, str) and bool(name)
        if not valid_name:
            issues.append(
                _role_issue(
                    role,
                    f"{prefix}.name.invalid",
                    f"{role} result has an invalid step_timings name",
                )
            )
        numeric_duration, problem = _safe_finite_float(duration)
        if problem == "not_numeric":
            issues.append(
                _role_issue(
                    role,
                    f"{prefix}.duration.not_numeric",
                    f"{role} result step_timings duration must be numeric",
                )
            )
            continue
        if problem == "not_finite":
            issues.append(
                _role_issue(
                    role,
                    f"{prefix}.duration.not_finite",
                    f"{role} result step_timings duration must be finite",
                )
            )
            continue
        if numeric_duration is not None and numeric_duration < 0:
            issues.append(
                _role_issue(
                    role,
                    f"{prefix}.duration.negative",
                    f"{role} result step_timings duration must be non-negative",
                )
            )
            continue
        if valid_name and numeric_duration is not None:
            aggregate = totals.get(name, 0.0) + numeric_duration
            if not math.isfinite(aggregate):
                issues.append(
                    _role_issue(
                        role,
                        f"{prefix}.aggregate.not_finite",
                        f"{role} result step_timings aggregate must be finite",
                    )
                )
            else:
                totals[name] = aggregate


def _safe_finite_float(value: object) -> tuple[float | None, str | None]:
    """Classify one persisted numeric value before any downstream conversion."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, "not_numeric"
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        return None, "not_finite"
    if not math.isfinite(converted):
        return None, "not_finite"
    return converted, None


def _append_score_value_issue(
    issues: list[ComparisonIssue],
    *,
    role: str,
    code: str,
    message: str,
    value: object,
    maximum: int | None,
) -> None:
    numeric_value, problem = _safe_finite_float(value)
    if problem == "not_numeric":
        issues.append(
            _role_issue(
                role,
                f"{code}.not_numeric",
                f"{message} must be a non-boolean number",
            )
        )
    elif problem == "not_finite":
        issues.append(
            _role_issue(
                role,
                f"{code}.not_finite",
                f"{message} must be finite",
            )
        )
    elif numeric_value is not None and (
        numeric_value < 0
        or (maximum is not None and numeric_value > maximum)
    ):
        issues.append(
            _role_issue(
                role,
                f"{code}.out_of_range",
                (
                    f"{message} must be non-negative"
                    if maximum is None
                    else f"{message} must be between 0 and {maximum}"
                ),
            )
        )


def _role_issue(
    role: str,
    code: str,
    message: str,
    value: object | None = None,
) -> ComparisonIssue:
    return ComparisonIssue(
        code=code,
        message=message,
        baseline=value if role == "baseline" else None,
        candidate=value if role == "candidate" else None,
    )


def _compatibility(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> tuple[list[ComparisonIssue], list[dict[str, object]]]:
    issues: list[ComparisonIssue] = []
    baseline_controls = baseline["always_controls"]
    candidate_controls = candidate["always_controls"]
    for name in ("ordered_case_ids", "dataset_path"):
        _append_exact_issue(
            issues,
            f"always_controls.{name}",
            baseline_controls[name],
            candidate_controls[name],
        )
    for name in ("dataset", "split", "scorer", "metric"):
        _append_fact_issue(
            issues,
            f"always_controls.{name}",
            baseline_controls[name],
            candidate_controls[name],
        )

    baseline_declared = tuple(baseline["declared_variant_dimensions"])
    candidate_declared = tuple(candidate["declared_variant_dimensions"])
    if baseline_declared != candidate_declared:
        _append_exact_issue(
            issues,
            "declared_variant_dimensions",
            list(baseline_declared),
            list(candidate_declared),
        )

    baseline_declared_set = set(baseline_declared)
    candidate_declared_set = set(candidate_declared)
    variant_differences: list[dict[str, object]] = []
    for dimension in ALLOWED_VARIANT_DIMENSIONS:
        baseline_fact = _dimension_fact(
            baseline,
            baseline_declared_set,
            dimension,
        )
        candidate_fact = _dimension_fact(
            candidate,
            candidate_declared_set,
            dimension,
        )
        baseline_is_variant = dimension in baseline_declared_set
        candidate_is_variant = dimension in candidate_declared_set
        if baseline_is_variant and candidate_is_variant:
            if baseline_fact != candidate_fact:
                variant_differences.append(
                    {
                        "dimension": dimension,
                        "baseline": dict(baseline_fact),
                        "candidate": dict(candidate_fact),
                    }
                )
        elif not baseline_is_variant and not candidate_is_variant:
            _append_fact_issue(
                issues,
                f"control_dimensions.{dimension}",
                baseline_fact,
                candidate_fact,
            )
        else:
            _append_fact_issue(
                issues,
                f"dimensions.{dimension}",
                baseline_fact,
                candidate_fact,
            )
    return issues, variant_differences


def _dimension_fact(
    identity: Mapping[str, Any],
    declared: set[str],
    dimension: str,
) -> Mapping[str, Any]:
    source = "variants" if dimension in declared else "control_dimensions"
    return identity[source][dimension]


def _append_exact_issue(
    issues: list[ComparisonIssue],
    name: str,
    baseline: object,
    candidate: object,
) -> None:
    if baseline != candidate:
        issues.append(
            ComparisonIssue(
                code=f"{name}.mismatch",
                message=f"{name} differs between the baseline and candidate",
                baseline=baseline,
                candidate=candidate,
            )
        )


def _append_fact_issue(
    issues: list[ComparisonIssue],
    name: str,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> None:
    if baseline["status"] == "unavailable" or candidate["status"] == "unavailable":
        issues.append(
            ComparisonIssue(
                code=f"{name}.unavailable",
                message=f"{name} lacks the evidence required for a controlled comparison",
                baseline=dict(baseline),
                candidate=dict(candidate),
            )
        )
    elif baseline != candidate:
        issues.append(
            ComparisonIssue(
                code=f"{name}.mismatch",
                message=f"{name} differs between the baseline and candidate",
                baseline=dict(baseline),
                candidate=dict(candidate),
            )
        )


def _compare_results(
    baseline: Sequence[Mapping[str, Any]],
    candidate: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baseline_by_id = {row.get("case_id", index): row for index, row in enumerate(baseline)}
    candidate_by_id = {row.get("case_id", index): row for index, row in enumerate(candidate)}
    baseline_scores = [float(row["composite_score"]) for row in baseline]
    candidate_scores = [float(row["composite_score"]) for row in candidate]
    regressions, improvements = _case_changes(baseline_by_id, candidate_by_id)
    return {
        "composite_delta": _score_delta(baseline_scores, candidate_scores),
        "check_deltas": _check_deltas(baseline, candidate),
        "timing_deltas": _timing_deltas(baseline, candidate),
        "regressions": regressions,
        "improvements": improvements,
    }


def _score_delta(
    baseline_scores: Sequence[float], candidate_scores: Sequence[float]
) -> dict[str, float]:
    """Compute mean and median delta between two score lists."""
    baseline_mean = statistics.mean(baseline_scores) if baseline_scores else 0.0
    candidate_mean = statistics.mean(candidate_scores) if candidate_scores else 0.0
    baseline_median = statistics.median(baseline_scores) if baseline_scores else 0.0
    candidate_median = statistics.median(candidate_scores) if candidate_scores else 0.0
    return {
        "baseline_mean": baseline_mean,
        "candidate_mean": candidate_mean,
        "mean_delta": candidate_mean - baseline_mean,
        "baseline_median": baseline_median,
        "candidate_median": candidate_median,
        "median_delta": candidate_median - baseline_median,
    }


def _check_deltas(
    baseline: Sequence[Mapping[str, Any]], candidate: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, float]]:
    """Compute per-check average score deltas."""
    baseline_checks: dict[str, list[float]] = {}
    candidate_checks: dict[str, list[float]] = {}
    for result in baseline:
        for name, value in result["score_breakdown"].items():
            baseline_checks.setdefault(name, []).append(float(value))
    for result in candidate:
        for name, value in result["score_breakdown"].items():
            candidate_checks.setdefault(name, []).append(float(value))
    return _grouped_deltas(baseline_checks, candidate_checks, "baseline_avg", "candidate_avg")


def _aggregate_timings_per_case(trace: Sequence[Sequence[Any]]) -> dict[str, float]:
    """Sum durations by node name within a single case trace."""
    totals: dict[str, float] = {}
    for name, duration in trace:
        totals[str(name)] = totals.get(str(name), 0.0) + float(duration)
    return totals


def _timing_deltas(
    baseline: Sequence[Mapping[str, Any]], candidate: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, float]]:
    """Compute per-step average timing deltas."""
    baseline_timings: dict[str, list[float]] = {}
    candidate_timings: dict[str, list[float]] = {}
    for results, timings in ((baseline, baseline_timings), (candidate, candidate_timings)):
        for result in results:
            trace = _normalize_timings(result.get("step_timings"))
            for name, value in _aggregate_timings_per_case(trace).items():
                timings.setdefault(name, []).append(value)
    return _grouped_deltas(
        baseline_timings,
        candidate_timings,
        "baseline_avg",
        "candidate_avg",
    )


def _grouped_deltas(
    baseline: Mapping[str, Sequence[float]],
    candidate: Mapping[str, Sequence[float]],
    baseline_key: str,
    candidate_key: str,
) -> dict[str, dict[str, float]]:
    deltas: dict[str, dict[str, float]] = {}
    for name in sorted(set(baseline) | set(candidate)):
        baseline_average = statistics.mean(baseline[name]) if name in baseline else 0.0
        candidate_average = statistics.mean(candidate[name]) if name in candidate else 0.0
        deltas[name] = {
            baseline_key: baseline_average,
            candidate_key: candidate_average,
            "delta": candidate_average - baseline_average,
        }
    return deltas


def _case_changes(
    baseline_by_id: Mapping[object, Mapping[str, Any]],
    candidate_by_id: Mapping[object, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Identify regressions and improvements at the case level."""
    common_ids = sorted(set(baseline_by_id) & set(candidate_by_id))
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    for case_id in common_ids:
        baseline_score = float(baseline_by_id[case_id]["composite_score"])
        candidate_score = float(candidate_by_id[case_id]["composite_score"])
        delta = candidate_score - baseline_score
        entry = {
            "case_id": case_id,
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "delta": delta,
        }
        if delta < 0:
            regressions.append(entry)
        elif delta > 0:
            improvements.append(entry)
    regressions.sort(key=lambda entry: entry["delta"])
    improvements.sort(key=lambda entry: entry["delta"], reverse=True)
    return regressions, improvements


def _build_summary(
    composite_delta: Mapping[str, float],
    check_deltas: Mapping[str, Mapping[str, float]],
    timing_deltas: Mapping[str, Mapping[str, float]],
    regressions: Sequence[Mapping[str, Any]],
    improvements: Sequence[Mapping[str, Any]],
    *,
    compatibility: Mapping[str, Any],
) -> str:
    """Build a markdown summary without overstating exploratory evidence."""
    lines = ["# Run Comparison", ""]
    if compatibility["exploratory"]:
        lines.extend(
            [
                "> **EXPLORATORY / UNCONTROLLED:** this comparison does not support "
                "causal or headline claims.",
                "",
                "## Incompatibilities",
                "",
            ]
        )
        for issue in compatibility["incompatibilities"]:
            lines.append(f"- `{issue['code']}`: {issue['message']}")
        lines.append("")
    lines.extend(
        [
            "## Composite Score",
            f"- Baseline mean: {composite_delta['baseline_mean']:.2f}",
            f"- Candidate mean: {composite_delta['candidate_mean']:.2f}",
            f"- Mean delta: {composite_delta['mean_delta']:+.2f}",
            f"- Median delta: {composite_delta['median_delta']:+.2f}",
            "",
        ]
    )
    if check_deltas:
        lines.extend(
            [
                "## Per-Check Deltas",
                "",
                "| Check | Baseline | Candidate | Delta |",
                "|-------|----------|-----------|-------|",
            ]
        )
        for name, values in sorted(check_deltas.items()):
            lines.append(
                f"| {name} | {values['baseline_avg']:.2f} | "
                f"{values['candidate_avg']:.2f} | {values['delta']:+.2f} |"
            )
        lines.append("")
    if timing_deltas:
        lines.extend(
            [
                "## Per-Step Timing Deltas",
                "",
                "| Step | Baseline (s) | Candidate (s) | Delta (s) |",
                "|------|-------------|---------------|-----------|",
            ]
        )
        for name, values in sorted(timing_deltas.items()):
            lines.append(
                f"| {name} | {values['baseline_avg']:.3f} | "
                f"{values['candidate_avg']:.3f} | {values['delta']:+.3f} |"
            )
        lines.append("")
    if compatibility["uncontrolled"]:
        lines.extend(
            [
                "## Observed Case Score Changes",
                f"- Observed score increases: {len(improvements)}",
                f"- Observed score decreases: {len(regressions)}",
            ]
        )
    else:
        lines.extend(
            [
                "## Case Changes",
                f"- Improvements: {len(improvements)}",
                f"- Regressions: {len(regressions)}",
            ]
        )
    if regressions:
        lines.extend(
            [
                "",
                (
                    "### Largest Observed Score Decreases"
                    if compatibility["uncontrolled"]
                    else "### Top Regressions"
                ),
            ]
        )
        for regression in regressions[:5]:
            lines.append(
                f"- `{regression['case_id']}`: {regression['baseline_score']:.0f} -> "
                f"{regression['candidate_score']:.0f} ({regression['delta']:+.0f})"
            )
    if improvements:
        lines.extend(
            [
                "",
                (
                    "### Largest Observed Score Increases"
                    if compatibility["uncontrolled"]
                    else "### Top Improvements"
                ),
            ]
        )
        for improvement in improvements[:5]:
            lines.append(
                f"- `{improvement['case_id']}`: {improvement['baseline_score']:.0f} -> "
                f"{improvement['candidate_score']:.0f} ({improvement['delta']:+.0f})"
            )
    return "\n".join(lines) + "\n"
