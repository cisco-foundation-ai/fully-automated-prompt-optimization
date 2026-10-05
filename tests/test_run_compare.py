# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for manifest-authenticated controlled run comparisons."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.hephaestus.runs import compare as run_compare
from src.hephaestus.runs.bundle import RunBundleWriter
from src.hephaestus.runs.identity import (
    ALLOWED_VARIANT_DIMENSIONS,
    build_run_identity,
    fingerprint_value,
)

_CASE_IDS = ("case-1", "case-2")
_MISSING_TENANT_ID = object()
compare_runs = run_compare.compare_runs
RunComparisonBundleError = getattr(run_compare, "RunComparisonBundleError", ValueError)
RunComparisonIncompatibilityError = getattr(
    run_compare,
    "RunComparisonIncompatibilityError",
    ValueError,
)


def _fingerprint(label: str) -> str:
    return fingerprint_value({"label": label})


def _identity(**overrides: object) -> dict[str, object]:
    """Build one complete, non-sensitive identity for a comparison test."""
    arguments: dict[str, object] = {
        "ordered_case_ids": _CASE_IDS,
        "dataset_path": "datasets/releases/example/test.jsonl",
        "dataset_fingerprint": _fingerprint("dataset"),
        "split_fingerprint": _fingerprint("split"),
        "scorer_fingerprint": _fingerprint("scorer"),
        "metric_fingerprint": _fingerprint("metric"),
        "dimension_fingerprints": {
            dimension: _fingerprint(dimension)
            for dimension in ALLOWED_VARIANT_DIMENSIONS
        },
        "variant_dimensions": (),
    }
    arguments.update(overrides)
    return build_run_identity(**arguments).to_dict()


def _progress(
    *,
    run_id: str,
    status: str,
    case_ids: tuple[str, ...],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    attempted = [str(row["case_id"]) for row in rows]
    successful = [
        str(row["case_id"])
        for row in rows
        if row["execution_status"] == "succeeded"
    ]
    failed = [
        str(row["case_id"])
        for row in rows
        if row["execution_status"] == "failed"
    ]
    return {
        "run_id": run_id,
        "status": status,
        "total_cases": len(case_ids),
        "completed_cases": len(rows),
        "successful_cases": len(successful),
        "attempted_case_ids": attempted,
        "successful_case_ids": successful,
        "failed_case_ids": failed,
        "in_flight_case_ids": [],
        "trust_tier_summaries": {},
    }


def _publish_bundle(
    output_dir: Path,
    *,
    identity: dict[str, object] | None = None,
    status: str = "completed",
    scores: tuple[float, float] = (50.0, 50.0),
    result_rows: list[dict[str, object]] | None = None,
    tenant_id: object = "example",
) -> None:
    """Publish an authenticated bundle with the requested terminal outcome."""
    run_id = output_dir.name
    bundle_identity = identity or _identity()
    controls = bundle_identity["always_controls"]
    assert isinstance(controls, dict)
    case_ids = tuple(controls["ordered_case_ids"])
    assert all(isinstance(case_id, str) for case_id in case_ids)
    dataset_path = controls["dataset_path"]
    assert isinstance(dataset_path, str)
    if status == "completed":
        execution_statuses = ("succeeded", "succeeded")
    elif status == "degraded":
        execution_statuses = ("succeeded", "failed")
    elif status == "failed":
        execution_statuses = ("failed", "failed")
    else:
        raise AssertionError(f"unsupported test status: {status}")
    rows = result_rows or [
        {
            "case_id": case_id,
            "execution_status": execution_status,
            "composite_score": score,
            "score_breakdown": {"exact_match": score},
        }
        for case_id, execution_status, score in zip(
            case_ids,
            execution_statuses,
            scores,
            strict=True,
        )
    ]
    run_config: dict[str, object] = {
        "run_id": run_id,
        "dataset_path": dataset_path,
    }
    if tenant_id is not _MISSING_TENANT_ID:
        run_config["tenant_id"] = tenant_id
    RunBundleWriter.reserve(output_dir, run_id=run_id).publish(
        run_config=run_config,
        run_identity=bundle_identity,
        results=rows,
        summary="# Evaluation Summary\n",
        progress=_progress(
            run_id=run_id,
            status=status,
            case_ids=case_ids,
            rows=rows,
        ),
    )


def _issue_codes(error: RunComparisonIncompatibilityError) -> set[str]:
    return {issue.code for issue in error.issues}


def _completed_rows(
    *,
    first: dict[str, object] | None = None,
    second: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    rows = [
        {
            "case_id": "case-1",
            "execution_status": "succeeded",
            "composite_score": 50.0,
            "score_breakdown": {"exact_match": 50.0},
        },
        {
            "case_id": "case-2",
            "execution_status": "succeeded",
            "composite_score": 50.0,
            "score_breakdown": {"exact_match": 50.0},
        },
    ]
    rows[0].update(first or {})
    rows[1].update(second or {})
    return rows


def _authenticate_non_finite_value(output_dir: Path, *, field: str) -> None:
    """Replace one score with an authenticated JSON number that decodes to infinity."""
    original = (
        b'"composite_score":50.0'
        if field == "composite_score"
        else b'"exact_match":50.0'
    )
    replacement = original.replace(b"50.0", b"1e10000")
    results_path = output_dir / "results.jsonl"
    content = results_path.read_bytes().replace(original, replacement, 1)
    assert replacement in content
    results_path.write_bytes(content)
    manifest_path = output_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["results.jsonl"] = {
        "bytes": len(content),
        "sha256": f"sha256:{hashlib.sha256(content).hexdigest()}",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_completed_authenticated_equal_runs_are_controlled(tmp_path: Path) -> None:
    """A matching pair can report ordinary score deltas."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(candidate, scores=(80.0, 90.0))

    result = compare_runs(baseline, candidate)

    assert result["compatibility"] == {
        "controlled": True,
        "exploratory": False,
        "uncontrolled": False,
        "incompatibilities": [],
        "variant_differences": [],
    }
    assert result["composite_delta"]["mean_delta"] == 35.0
    assert "EXPLORATORY" not in result["summary_md"]


@pytest.mark.parametrize("role", ("baseline", "candidate"))
@pytest.mark.parametrize(
    "tenant_id",
    (_MISSING_TENANT_ID, None, "", " ", "../foreign", True),
    ids=("missing", "null", "empty", "whitespace", "path", "boolean"),
)
def test_missing_or_malformed_tenant_identity_rejects_in_every_mode(
    tmp_path: Path,
    role: str,
    tenant_id: object,
) -> None:
    """Neither comparison role can supply an unavailable tenant identity."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(
        baseline,
        tenant_id=tenant_id if role == "baseline" else "example",
    )
    _publish_bundle(
        candidate,
        tenant_id=tenant_id if role == "candidate" else "example",
    )

    for exploratory in (False, True):
        with pytest.raises(RunComparisonBundleError) as raised:
            compare_runs(baseline, candidate, exploratory=exploratory)

        assert (
            f"{role}.run_config.tenant_id.unavailable"
            in _issue_codes(raised.value)
        )


@pytest.mark.parametrize("exploratory", (False, True))
def test_cross_tenant_comparison_rejects_in_every_mode(
    tmp_path: Path,
    exploratory: bool,
) -> None:
    """Exploratory comparison cannot bypass the tenant authorization boundary."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline, tenant_id="tenant-a")
    _publish_bundle(candidate, tenant_id="tenant-b")

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate, exploratory=exploratory)

    assert "run_config.tenant_id.mismatch" in _issue_codes(raised.value)


def test_controlled_calculations_and_top_case_details(tmp_path: Path) -> None:
    """Controlled output retains exact aggregate, timing, and case-level evidence."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    identity = _identity(ordered_case_ids=("case-1", "case-2", "case-3"))
    baseline_rows = _completed_rows(
        first={
            "composite_score": 100.0,
            "score_breakdown": {"accuracy": 0.0, "format": 100.0},
            "step_timings": [["think", 1.0], ["think", 2.0]],
        },
        second={
            "composite_score": 0.0,
            "score_breakdown": {"accuracy": 0.0, "format": 100.0},
            "step_timings": [["think", 1.0]],
        },
    )
    baseline_rows.append(
        {
            "case_id": "case-3",
            "execution_status": "succeeded",
            "composite_score": 0.0,
            "score_breakdown": {"accuracy": 0.0, "format": 100.0},
            "step_timings": [["think", 2.0]],
        }
    )
    candidate_rows = _completed_rows(
        first={
            "composite_score": 50.0,
            "score_breakdown": {"accuracy": 50.0, "format": 100.0},
            "step_timings": [["think", 0.5]],
        },
        second={
            "composite_score": 80.0,
            "score_breakdown": {"accuracy": 50.0, "format": 100.0},
            "step_timings": [["think", 1.5]],
        },
    )
    candidate_rows.append(
        {
            "case_id": "case-3",
            "execution_status": "succeeded",
            "composite_score": 100.0,
            "score_breakdown": {"accuracy": 50.0, "format": 100.0},
            "step_timings": [["think", 1.0]],
        }
    )
    _publish_bundle(baseline, identity=identity, result_rows=baseline_rows)
    _publish_bundle(candidate, identity=identity, result_rows=candidate_rows)

    result = compare_runs(baseline, candidate)

    assert result["composite_delta"] == pytest.approx(
        {
            "baseline_mean": 100.0 / 3.0,
            "candidate_mean": 230.0 / 3.0,
            "mean_delta": 130.0 / 3.0,
            "baseline_median": 0.0,
            "candidate_median": 80.0,
            "median_delta": 80.0,
        }
    )
    assert result["check_deltas"] == {
        "accuracy": {"baseline_avg": 0.0, "candidate_avg": 50.0, "delta": 50.0},
        "format": {"baseline_avg": 100.0, "candidate_avg": 100.0, "delta": 0.0},
    }
    assert result["timing_deltas"]["think"] == {
        "baseline_avg": 2.0,
        "candidate_avg": 1.0,
        "delta": -1.0,
    }
    assert result["regressions"] == [
        {
            "case_id": "case-1",
            "baseline_score": 100.0,
            "candidate_score": 50.0,
            "delta": -50.0,
        }
    ]
    assert result["improvements"] == [
        {
            "case_id": "case-3",
            "baseline_score": 0.0,
            "candidate_score": 100.0,
            "delta": 100.0,
        },
        {
            "case_id": "case-2",
            "baseline_score": 0.0,
            "candidate_score": 80.0,
            "delta": 80.0,
        }
    ]
    assert "### Top Regressions" in result["summary_md"]
    assert "`case-1`: 100 -> 50 (-50)" in result["summary_md"]
    assert "### Top Improvements" in result["summary_md"]
    assert "`case-3`: 0 -> 100 (+100)" in result["summary_md"]
    assert "`case-2`: 0 -> 80 (+80)" in result["summary_md"]


@pytest.mark.parametrize(
    ("missing_field", "expected_code"),
    [
        ("composite_score", "candidate.results.case-1.composite_score.missing"),
        ("score_breakdown", "candidate.results.case-1.score_breakdown.missing"),
    ],
)
def test_required_score_fields_reject_before_comparison(
    tmp_path: Path,
    missing_field: str,
    expected_code: str,
) -> None:
    """A completed bundle cannot silently default a required scoring field."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    rows = _completed_rows()
    rows[0].pop(missing_field)
    _publish_bundle(baseline)
    _publish_bundle(candidate, result_rows=rows)

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    assert expected_code in _issue_codes(raised.value)


@pytest.mark.parametrize(
    ("value", "expected_suffix"),
    [
        (True, "not_numeric"),
        ("not-a-score", "not_numeric"),
        (-0.01, "out_of_range"),
        (100.01, "out_of_range"),
    ],
)
def test_invalid_composite_scores_reject_before_comparison(
    tmp_path: Path,
    value: object,
    expected_suffix: str,
) -> None:
    """Composite scores must be non-boolean finite numbers from zero to one hundred."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(
        candidate,
        result_rows=_completed_rows(first={"composite_score": value}),
    )

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    assert (
        f"candidate.results.case-1.composite_score.{expected_suffix}"
        in _issue_codes(raised.value)
    )


def test_invalid_score_values_do_not_escape_in_public_issues(tmp_path: Path) -> None:
    """Malformed persisted score values are never copied into public diagnostics."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    secret_canary = "sk-super-secret-canary"
    _publish_bundle(baseline)
    _publish_bundle(
        candidate,
        result_rows=_completed_rows(first={"composite_score": secret_canary}),
    )

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    public_issues = [issue.to_dict() for issue in raised.value.issues]
    assert secret_canary not in json.dumps(public_issues)
    issue = next(
        item
        for item in public_issues
        if item["code"]
        == "candidate.results.case-1.composite_score.not_numeric"
    )
    assert issue["baseline"] is None
    assert issue["candidate"] is None


def test_non_finite_composite_score_rejects_before_comparison(tmp_path: Path) -> None:
    """An authenticated number that decodes to infinity is not score evidence."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(candidate)
    _authenticate_non_finite_value(candidate, field="composite_score")

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    assert (
        "candidate.results.case-1.composite_score.not_finite"
        in _issue_codes(raised.value)
    )
    json.dumps(
        [issue.to_dict() for issue in raised.value.issues],
        allow_nan=False,
    )


def test_non_finite_breakdown_score_rejects_before_comparison(tmp_path: Path) -> None:
    """An authenticated infinite breakdown value is not score evidence."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(candidate)
    _authenticate_non_finite_value(candidate, field="score_breakdown")

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    assert (
        "candidate.results.case-1.score_breakdown.exact_match.not_finite"
        in _issue_codes(raised.value)
    )


@pytest.mark.parametrize(
    ("timings", "expected_suffix"),
    [
        ("not-a-timing-trace", "not_collection"),
        ([[]], "entry.invalid"),
        ([[False, 1.0]], "name.invalid"),
        ([["node", True]], "duration.not_numeric"),
        ([["node", "timing-secret-canary"]], "duration.not_numeric"),
        ([["node", -0.01]], "duration.negative"),
        ([["node", 10**400]], "duration.not_finite"),
        (
            [["node", 1e308], ["node", 1e308]],
            "aggregate.not_finite",
        ),
    ],
)
def test_malformed_step_timings_reject_with_redacted_bundle_issues(
    tmp_path: Path,
    timings: object,
    expected_suffix: str,
) -> None:
    """Persisted timing data cannot escape validation or leak into diagnostics."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(
        candidate,
        result_rows=_completed_rows(first={"step_timings": timings}),
    )

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    assert (
        f"candidate.results.0.step_timings.{expected_suffix}"
        in _issue_codes(raised.value)
    )
    public = json.dumps([issue.to_dict() for issue in raised.value.issues])
    assert "timing-secret-canary" not in public
    assert "timing-secret-canary" not in str(raised.value)


def test_legacy_mapping_step_timings_keep_existing_aggregation(tmp_path: Path) -> None:
    """The validated timing gate retains the historical mapping representation."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(
        baseline,
        result_rows=_completed_rows(
            first={"step_timings": {"think": 2.0}},
            second={"step_timings": {"think": 4.0}},
        ),
    )
    _publish_bundle(
        candidate,
        result_rows=_completed_rows(
            first={"step_timings": [["think", 1.0]]},
            second={"step_timings": [["think", 3.0]]},
        ),
    )

    result = compare_runs(baseline, candidate)

    assert result["timing_deltas"] == {
        "think": {
            "baseline_avg": 3.0,
            "candidate_avg": 2.0,
            "delta": -1.0,
        }
    }


@pytest.mark.parametrize(
    ("breakdown", "expected_suffix"),
    [
        (None, "not_object"),
        ({"": 50.0}, "key.invalid"),
        ({"exact_match": True}, "exact_match.not_numeric"),
        ({"exact_match": "not-a-score"}, "exact_match.not_numeric"),
        ({"exact_match": -0.01}, "exact_match.out_of_range"),
    ],
)
def test_invalid_score_breakdowns_reject_before_comparison(
    tmp_path: Path,
    breakdown: object,
    expected_suffix: str,
) -> None:
    """Breakdowns require safe names and finite non-negative numeric values."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(
        candidate,
        result_rows=_completed_rows(first={"score_breakdown": breakdown}),
    )

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    assert (
        f"candidate.results.case-1.score_breakdown.{expected_suffix}"
        in _issue_codes(raised.value)
    )


def test_raw_breakdown_values_above_one_hundred_are_allowed(tmp_path: Path) -> None:
    """Raw point totals remain valid when they exceed percentage-scale bounds."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline_rows = _completed_rows(
        first={
            "score_breakdown": {"points_earned": 190.0, "points_possible": 200.0}
        },
        second={
            "score_breakdown": {"points_earned": 190.0, "points_possible": 200.0}
        },
    )
    candidate_rows = _completed_rows(
        first={
            "score_breakdown": {"points_earned": 195.0, "points_possible": 200.0}
        },
        second={
            "score_breakdown": {"points_earned": 195.0, "points_possible": 200.0}
        },
    )
    _publish_bundle(baseline, result_rows=baseline_rows)
    _publish_bundle(candidate, result_rows=candidate_rows)

    result = compare_runs(baseline, candidate)

    assert result["check_deltas"] == {
        "points_earned": {
            "baseline_avg": 190.0,
            "candidate_avg": 195.0,
            "delta": 5.0,
        },
        "points_possible": {
            "baseline_avg": 200.0,
            "candidate_avg": 200.0,
            "delta": 0.0,
        },
    }


def test_non_representable_breakdown_integer_rejects_before_float_conversion(
    tmp_path: Path,
) -> None:
    """An authenticated huge integer cannot crash downstream float conversion."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(
        baseline,
        result_rows=_completed_rows(
            first={"score_breakdown": {"points_earned": 100}},
            second={"score_breakdown": {"points_earned": 200}},
        ),
    )
    _publish_bundle(
        candidate,
        result_rows=_completed_rows(
            first={"score_breakdown": {"points_earned": 10**400}},
            second={"score_breakdown": {"points_earned": 200}},
        ),
    )

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    assert (
        "candidate.results.case-1.score_breakdown.points_earned.not_finite"
        in _issue_codes(raised.value)
    )


def test_per_case_breakdown_metric_coverage_must_match(tmp_path: Path) -> None:
    """Per-check averages cannot compare different case subsets."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(
        candidate,
        result_rows=_completed_rows(second={"score_breakdown": {}}),
    )

    with pytest.raises(RunComparisonBundleError) as raised:
        compare_runs(baseline, candidate)

    issue = next(
        issue
        for issue in raised.value.issues
        if issue.code == "results.case-2.score_breakdown_keys.mismatch"
    )
    assert issue.baseline == ["exact_match"]
    assert issue.candidate == []


@pytest.mark.parametrize(
    ("name", "candidate_overrides", "expected_code"),
    [
        (
            "ordered case IDs",
            {"ordered_case_ids": tuple(reversed(_CASE_IDS))},
            "always_controls.ordered_case_ids.mismatch",
        ),
        (
            "dataset path",
            {"dataset_path": "datasets/releases/example/other.jsonl"},
            "always_controls.dataset_path.mismatch",
        ),
        (
            "dataset",
            {"dataset_fingerprint": _fingerprint("other-dataset")},
            "always_controls.dataset.mismatch",
        ),
        (
            "split",
            {"split_fingerprint": _fingerprint("other-split")},
            "always_controls.split.mismatch",
        ),
        (
            "scorer",
            {"scorer_fingerprint": _fingerprint("other-scorer")},
            "always_controls.scorer.mismatch",
        ),
        (
            "metric",
            {"metric_fingerprint": _fingerprint("other-metric")},
            "always_controls.metric.mismatch",
        ),
    ],
)
def test_permanent_control_difference_rejects_headline_comparison(
    tmp_path: Path,
    name: str,
    candidate_overrides: dict[str, object],
    expected_code: str,
) -> None:
    """Every permanent control is required for a controlled comparison."""
    baseline = tmp_path / f"baseline-{name}"
    candidate = tmp_path / f"candidate-{name}"
    _publish_bundle(baseline)
    _publish_bundle(candidate, identity=_identity(**candidate_overrides))

    with pytest.raises(RunComparisonIncompatibilityError) as raised:
        compare_runs(baseline, candidate)

    assert expected_code in _issue_codes(raised.value)


@pytest.mark.parametrize("dimension", ALLOWED_VARIANT_DIMENSIONS)
def test_each_undeclared_dimension_must_remain_fixed(
    tmp_path: Path,
    dimension: str,
) -> None:
    """A difference in any undeclared dimension rejects a headline result."""
    baseline = tmp_path / f"baseline-{dimension}"
    candidate = tmp_path / f"candidate-{dimension}"
    candidate_dimensions = {
        item: _fingerprint(item)
        for item in ALLOWED_VARIANT_DIMENSIONS
    }
    candidate_dimensions[dimension] = _fingerprint(f"changed-{dimension}")
    _publish_bundle(baseline)
    _publish_bundle(
        candidate,
        identity=_identity(dimension_fingerprints=candidate_dimensions),
    )

    with pytest.raises(RunComparisonIncompatibilityError) as raised:
        compare_runs(baseline, candidate)

    assert f"control_dimensions.{dimension}.mismatch" in _issue_codes(raised.value)


def test_unavailable_control_evidence_is_not_controlled(tmp_path: Path) -> None:
    """Matching unknown values do not establish that a control was held fixed."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    unknown_identity = _identity(dataset_fingerprint=None)
    _publish_bundle(baseline, identity=unknown_identity)
    _publish_bundle(candidate, identity=unknown_identity)

    with pytest.raises(RunComparisonIncompatibilityError) as raised:
        compare_runs(baseline, candidate)

    assert "always_controls.dataset.unavailable" in _issue_codes(raised.value)


def test_variant_declaration_mismatch_rejects_headline_comparison(tmp_path: Path) -> None:
    """Both runs must agree on what was intentionally varied."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline, identity=_identity(variant_dimensions=("prompts",)))
    _publish_bundle(candidate, identity=_identity(variant_dimensions=("skills",)))

    with pytest.raises(RunComparisonIncompatibilityError) as raised:
        compare_runs(baseline, candidate)

    assert "declared_variant_dimensions.mismatch" in _issue_codes(raised.value)


def test_variant_declaration_mismatch_lists_each_dimension_difference(
    tmp_path: Path,
) -> None:
    """A declaration conflict cannot hide facts that differ across the runs."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline_dimensions = {
        item: _fingerprint(item)
        for item in ALLOWED_VARIANT_DIMENSIONS
    }
    candidate_dimensions = dict(baseline_dimensions)
    candidate_dimensions["prompts"] = _fingerprint("candidate-prompts")
    candidate_dimensions["skills"] = _fingerprint("candidate-skills")
    _publish_bundle(
        baseline,
        identity=_identity(
            dimension_fingerprints=baseline_dimensions,
            variant_dimensions=("prompts",),
        ),
    )
    _publish_bundle(
        candidate,
        identity=_identity(
            dimension_fingerprints=candidate_dimensions,
            variant_dimensions=("skills",),
        ),
    )

    with pytest.raises(RunComparisonIncompatibilityError) as raised:
        compare_runs(baseline, candidate)

    assert _issue_codes(raised.value) == {
        "declared_variant_dimensions.mismatch",
        "dimensions.prompts.mismatch",
        "dimensions.skills.mismatch",
    }


def test_common_declared_variant_difference_remains_intended_when_sets_conflict(
    tmp_path: Path,
) -> None:
    """A declaration-set conflict does not reclassify a shared intended variant."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline_dimensions = {
        item: _fingerprint(item)
        for item in ALLOWED_VARIANT_DIMENSIONS
    }
    candidate_dimensions = dict(baseline_dimensions)
    candidate_dimensions["prompts"] = _fingerprint("candidate-prompts")
    candidate_dimensions["skills"] = _fingerprint("candidate-skills")
    _publish_bundle(
        baseline,
        identity=_identity(
            dimension_fingerprints=baseline_dimensions,
            variant_dimensions=("prompts",),
        ),
    )
    _publish_bundle(
        candidate,
        identity=_identity(
            dimension_fingerprints=candidate_dimensions,
            variant_dimensions=("prompts", "skills"),
        ),
    )

    result = compare_runs(baseline, candidate, exploratory=True)

    assert {
        issue["code"]
        for issue in result["compatibility"]["incompatibilities"]
    } == {
        "declared_variant_dimensions.mismatch",
        "dimensions.skills.mismatch",
    }
    assert result["compatibility"]["variant_differences"] == [
        {
            "dimension": "prompts",
            "baseline": {
                "status": "available",
                "fingerprint": baseline_dimensions["prompts"],
            },
            "candidate": {
                "status": "available",
                "fingerprint": candidate_dimensions["prompts"],
            },
        }
    ]


def test_declared_variant_difference_is_reported_but_controlled(tmp_path: Path) -> None:
    """An intended prompt change is distinct from an uncontrolled difference."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    baseline_dimensions = {
        item: _fingerprint(item)
        for item in ALLOWED_VARIANT_DIMENSIONS
    }
    candidate_dimensions = dict(baseline_dimensions)
    candidate_dimensions["prompts"] = _fingerprint("changed-prompts")
    _publish_bundle(
        baseline,
        identity=_identity(
            dimension_fingerprints=baseline_dimensions,
            variant_dimensions=("prompts",),
        ),
    )
    _publish_bundle(
        candidate,
        identity=_identity(
            dimension_fingerprints=candidate_dimensions,
            variant_dimensions=("prompts",),
        ),
    )

    result = compare_runs(baseline, candidate)

    assert result["compatibility"]["controlled"] is True
    assert result["compatibility"]["variant_differences"] == [
        {
            "dimension": "prompts",
            "baseline": {
                "status": "available",
                "fingerprint": baseline_dimensions["prompts"],
            },
            "candidate": {
                "status": "available",
                "fingerprint": candidate_dimensions["prompts"],
            },
        }
    ]


def test_exploratory_mode_lists_all_uncontrolled_differences(tmp_path: Path) -> None:
    """Exploratory output is fully labeled and never hides incompatibilities."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    candidate_dimensions = {
        item: _fingerprint(item)
        for item in ALLOWED_VARIANT_DIMENSIONS
    }
    candidate_dimensions["sampling"] = _fingerprint("changed-sampling")
    _publish_bundle(baseline)
    _publish_bundle(
        candidate,
        identity=_identity(
            dataset_fingerprint=_fingerprint("other-dataset"),
            split_fingerprint=_fingerprint("other-split"),
            dimension_fingerprints=candidate_dimensions,
        ),
        scores=(80.0, 20.0),
    )

    with pytest.raises(RunComparisonIncompatibilityError) as raised:
        compare_runs(baseline, candidate)

    expected_codes = {
        "always_controls.dataset.mismatch",
        "always_controls.split.mismatch",
        "control_dimensions.sampling.mismatch",
    }
    assert _issue_codes(raised.value) == expected_codes

    result = compare_runs(baseline, candidate, exploratory=True)

    compatibility = result["compatibility"]
    assert compatibility["controlled"] is False
    assert compatibility["exploratory"] is True
    assert compatibility["uncontrolled"] is True
    assert {
        issue["code"] for issue in compatibility["incompatibilities"]
    } == expected_codes
    assert "EXPLORATORY / UNCONTROLLED" in result["summary_md"]
    assert "does not support causal or headline claims" in result["summary_md"]
    for code in expected_codes:
        assert f"`{code}`" in result["summary_md"]
    assert "Improvements" not in result["summary_md"]
    assert "Regressions" not in result["summary_md"]
    assert "Observed score increases" in result["summary_md"]
    assert "Observed score decreases" in result["summary_md"]
    assert "### Largest Observed Score Increases" in result["summary_md"]
    assert "### Largest Observed Score Decreases" in result["summary_md"]


def test_exploratory_flag_is_inactive_for_compatible_runs(tmp_path: Path) -> None:
    """Exploratory mode is an effective state only when it relaxes incompatibility."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    _publish_bundle(candidate)

    result = compare_runs(baseline, candidate, exploratory=True)

    assert result["compatibility"] == {
        "controlled": True,
        "exploratory": False,
        "uncontrolled": False,
        "incompatibilities": [],
        "variant_differences": [],
    }
    assert "EXPLORATORY" not in result["summary_md"]
    assert "UNCONTROLLED" not in result["summary_md"]


@pytest.mark.parametrize("failure", ("legacy", "corrupt", "degraded", "failed", "running"))
def test_non_completed_or_unauthenticated_bundles_reject_even_exploratory(
    tmp_path: Path,
    failure: str,
) -> None:
    """Only manifest-authenticated completed bundles are eligible in every mode."""
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    _publish_bundle(baseline)
    if failure == "legacy":
        candidate.mkdir()
        (candidate / "results.jsonl").write_text("{}\n", encoding="utf-8")
    elif failure == "corrupt":
        _publish_bundle(candidate)
        (candidate / "results.jsonl").write_text("{}\n", encoding="utf-8")
    elif failure in {"degraded", "failed"}:
        _publish_bundle(candidate, status=failure)
    else:
        candidate.mkdir()
        (candidate / "progress.json").write_text(
            json.dumps({"run_id": candidate.name, "status": "running"}),
            encoding="utf-8",
        )

    with pytest.raises(RunComparisonBundleError):
        compare_runs(baseline, candidate)
    with pytest.raises(RunComparisonBundleError):
        compare_runs(baseline, candidate, exploratory=True)
