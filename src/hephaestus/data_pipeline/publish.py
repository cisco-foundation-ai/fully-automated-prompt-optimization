# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Eval cases and the human review report."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from src.hephaestus.data_pipeline.config import AssetConfig
from src.hephaestus.data_pipeline.contract import effective_route
from src.hephaestus.data_pipeline.prepare import SPLITS, PreparedRecord
from src.hephaestus.data_pipeline.trace import model_visible_context
from src.hephaestus.datasets.trust_tiers import INFERRED_FROM_TRUSTED_FEEDBACK, TRUSTED_FEEDBACK

LOW_CONFIDENCE = 0.5
_LIST_LIMIT = 20


def build_cases(
    records: Sequence[PreparedRecord],
    rubrics: Sequence[Mapping[str, Any]],
    asset_id: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Return eval cases, and the records excluded for lack of criteria."""
    cases: List[Dict[str, Any]] = []
    unscoreable: List[Dict[str, str]] = []
    for record, rubric in zip(records, rubrics):
        if not any(group["criteria"] for group in rubric["evaluation_guidelines"]):
            unscoreable.append({"record_id": record.record_id, "reason": "no_checkable_criteria"})
            continue
        cases.append(build_case(record, rubric, asset_id))
    return cases, unscoreable


def build_case(record: PreparedRecord, rubric: Mapping[str, Any], asset_id: str) -> Dict[str, Any]:
    """Return one eval case.

    ``expected.evaluation_guidelines`` holds every criterion the judge
    scores: each chosen catalog guideline, then a ``case`` group with the
    case-specific criteria.
    """
    row = record.row
    tier = TRUSTED_FEEDBACK if record.labeled else INFERRED_FROM_TRUSTED_FEEDBACK
    expected: Dict[str, Any] = {
        "label_source": tier,
        "provenance": rubric["provenance"],
        "confidence": rubric["confidence"],
        "intent_label": rubric["intent_label"],
        "evaluation_guideline_ids": list(rubric["evaluation_guideline_ids"]),
        "evaluation_guidelines": list(rubric["evaluation_guidelines"]),
        "tool_expectations": dict(rubric["tool_expectations"]),
        "reference_output": rubric["reference_output"],
    }
    if record.labeled:
        expected["feedback_polarity"] = row["feedback"]["polarity"]
    return {
        "case_id": f"{'feedback' if record.labeled else 'inferred'}-{record.record_id}",
        "task_type": str(row["task_type"]),
        "context": model_visible_context(row),
        "expected": expected,
        "metadata": {
            "source": "feedback_trace" if record.labeled else "unlabeled_trace",
            "dataset_version": asset_id,
            "record_id": record.record_id,
            "group_id": str(row["group_id"]),
            "request_id": str(row.get("request_id") or record.record_id),
            "route": effective_route(row),
            "split": record.split,
            "trust_tier": tier,
        },
    }


def review_summary(
    *,
    config: AssetConfig,
    records: Sequence[PreparedRecord],
    excluded: Sequence[Mapping[str, str]],
    lessons: Sequence[Mapping[str, Any]],
    dropped: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    call_stats: Mapping[str, Mapping[str, int]],
) -> Dict[str, Any]:
    """Return the machine-readable review report."""
    splits = [split for split in SPLITS if split != "regression" or config.regression_split]
    datasets = {split: {"trusted": 0, "inferred": 0} for split in splits}
    for case in cases:
        tier = "trusted" if case["metadata"]["trust_tier"] == TRUSTED_FEEDBACK else "inferred"
        datasets[case["metadata"]["split"]][tier] += 1
    included = [g for g in catalog["guidelines"] if g["included"]]
    covered_routes = {g["route"] for g in included}
    return {
        "asset": f"{config.tenant_id}/{config.asset_id}",
        "model": config.model,
        "datasets": datasets,
        "records": {
            "feedback": sum(1 for record in records if record.labeled),
            "unlabeled": sum(1 for record in records if not record.labeled),
            "excluded": list(excluded),
        },
        "lessons": {
            "kept": len(lessons),
            "episodes": len({lesson["record_id"] for lesson in lessons}),
            "by_signal": dict(Counter(lesson["signal"] for lesson in lessons)),
            "dropped": dict(Counter(item["reason"] for item in dropped)),
        },
        "catalog": {
            "guidelines": len(catalog["guidelines"]),
            "included": len(included),
            "strong": sum(1 for g in included if g["strength"] == "strong"),
            "cannot_fix_lessons": sum(len(item["lesson_ids"]) for item in catalog["cannot_fix"]),
            "set_aside_lessons": sum(len(item["lesson_ids"]) for item in catalog["set_aside"]),
        },
        "routes_without_guidelines": sorted(
            {effective_route(record.row) for record in records} - covered_routes
        ),
        "trace_inferred_cases": sum(
            1 for case in cases if case["expected"]["provenance"] == "trace_inferred"
        ),
        "low_confidence_cases": [
            {"case_id": case["case_id"], "confidence": case["expected"]["confidence"]}
            for case in sorted(cases, key=lambda item: item["expected"]["confidence"])
            if case["expected"]["confidence"] < LOW_CONFIDENCE
        ],
        "calls": {step: dict(stats) for step, stats in sorted(call_stats.items())},
    }


def render_review(
    summary: Mapping[str, Any],
    catalog: Mapping[str, Any],
    lessons: Sequence[Mapping[str, Any]],
    dropped: Sequence[Mapping[str, Any]],
) -> str:
    """Render the review report as Markdown."""
    by_id = {lesson["lesson_id"]: lesson for lesson in lessons}
    lines = [
        f"# Evaluation asset review: {summary['asset']}",
        "",
        f"Built with `{summary['model']}`. Read this report before optimizing against the datasets.",
        "",
        "## Datasets",
        "",
        "| Split | Trusted | Inferred | Total |",
        "|---|---|---|---|",
    ]
    for split, counts in summary["datasets"].items():
        lines.append(
            _row(split, counts["trusted"], counts["inferred"], counts["trusted"] + counts["inferred"])
        )
    lines += ["", "Each split is in `datasets/<split>.jsonl`. No connected group spans two splits.", ""]

    excluded = summary["records"]["excluded"]
    if excluded:
        lines += ["### Excluded records", ""]
        for reason, count in sorted(Counter(item["reason"] for item in excluded).items()):
            ids = [item["record_id"] for item in excluded if item["reason"] == reason]
            lines.append(f"- `{reason}`: {count} ({_names(ids)})")
        lines.append("")

    stats = summary["lessons"]
    lines += [
        "## Guideline catalog",
        "",
        f"Built from {stats['kept']} lessons on {stats['episodes']} train episodes. Only train episodes "
        "are observed; validation, test, and regression feedback is used only for each case's own rubric.",
        "",
    ]
    for guideline in catalog["guidelines"]:
        signals = ", ".join(f"{count} {signal}" for signal, count in guideline["signals"].items())
        lines += [
            f"### {guideline['guideline_id']}: {guideline['title']}",
            "",
            f"Route `{guideline['route']}`, {guideline['strength']}, "
            f"{guideline['support']} episodes ({signals}).",
        ]
        if not guideline["included"]:
            lines.append("**Not in the catalog:** support is below `min_guideline_support`.")
        lines += ["", f"Dividing line: {guideline['dividing_line']}", ""]
        for criterion in guideline["criteria"]:
            lines.append(
                f"- `{criterion['criterion_id']}` **{criterion['kind']}, {criterion['severity']}:** "
                f"{criterion['statement']} *Applies when:* {criterion['applicability']}"
            )
        lines += ["", f"Lessons: {_names(guideline['lesson_ids'])}."]
        if guideline["counter_examples"]:
            lines.append(f"Counter-examples: {_names(guideline['counter_examples'])}.")
        lines.append("")

    for name, title in (("cannot_fix", "Lessons that cannot be checked"), ("set_aside", "Lessons set aside")):
        if not catalog[name]:
            continue
        lines += [f"## {title}", ""]
        for item in catalog[name]:
            lines.append(f"- Route `{item['route']}`: {item['reason']}")
            for lesson_id in item["lesson_ids"][:_LIST_LIMIT]:
                lines.append(f"  - `{lesson_id}`: {by_id[lesson_id]['lesson']}")
            if len(item["lesson_ids"]) > _LIST_LIMIT:
                lines.append(f"  - and {len(item['lesson_ids']) - _LIST_LIMIT} more")
        lines.append("")

    if catalog["facts"]:
        lines += ["## Environment facts", ""]
        lines += [f"- Route `{item['route']}`: {item['fact']}" for item in catalog["facts"]]
        lines.append("")

    if dropped:
        lines += ["## Dropped lessons", ""]
        for reason, count in sorted(stats["dropped"].items()):
            lines.append(f"- `{reason}`: {count}")
        lines.append("")

    lines += ["## Cases to check", ""]
    lines.append(f"- Trace-inferred cases (no catalog guideline applied): {summary['trace_inferred_cases']}")
    if summary["routes_without_guidelines"]:
        lines.append(f"- Routes with no catalog guideline: {_names(summary['routes_without_guidelines'])}")
    if summary["low_confidence_cases"]:
        names = [f"{item['case_id']} ({item['confidence']:.2f})" for item in summary["low_confidence_cases"]]
        lines.append(f"- Rubric confidence below {LOW_CONFIDENCE}: {_names(names)}")
    lines += [
        "",
        "## Model calls",
        "",
        "Calls and tokens cover every run of this build; reused responses count this run only.",
        "",
        "| Step | Model calls | Reused from cache | Input tokens | Output tokens |",
        "|---|---|---|---|---|",
    ]
    for step, counts in summary["calls"].items():
        lines.append(
            _row(step, *(counts[name] for name in ("calls", "cached", "input_tokens", "output_tokens")))
        )
    return "\n".join(lines) + "\n"


def _row(*cells: Any) -> str:
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def _names(values: Sequence[str]) -> str:
    shown = ", ".join(f"`{value}`" for value in values[:_LIST_LIMIT])
    extra = len(values) - _LIST_LIMIT
    return shown + (f", and {extra} more" if extra > 0 else "")
