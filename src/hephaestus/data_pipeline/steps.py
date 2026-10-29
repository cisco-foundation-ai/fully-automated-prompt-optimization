# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""The three model steps: observe, synthesize, and rubric.

Code validates every response, checks evidence quotes, assigns IDs, and
computes guideline support, so the model only makes judgment calls.
"""

from __future__ import annotations

import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, TypeVar

from src.hephaestus.data_pipeline.config import AssetConfig
from src.hephaestus.data_pipeline.llm import JsonCalls
from src.hephaestus.data_pipeline.prepare import PreparedRecord
from src.hephaestus.data_pipeline.prompts import OBSERVE_PROMPT, RUBRIC_PROMPT, SYNTHESIZE_PROMPT
from src.hephaestus.data_pipeline.trace import episode_view

LESSON_TYPES = ("failure", "success", "improvement")
SIGNALS = ("explicit", "clear", "weak")
CRITERION_KINDS = ("required", "prohibited", "preferred")
SEVERITIES = ("critical", "major", "minor")
STRONG_SUPPORT = 3
SYNTHESIS_CHUNK = 60
_MIN_QUOTE_CHARS = 8
_MIN_FRAGMENT_CHARS = 3
# Structural fields that are never evidence text.
_FEEDBACK_SKIP = {"polarity", "source", "kind", "check_id", "passed"}
_TRACE_SKIP = {"role", "outcome"}

T = TypeVar("T")
R = TypeVar("R")


def observe(
    calls: JsonCalls,
    records: Sequence[PreparedRecord],
    config: AssetConfig,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract lessons from train episodes.

    Only train records are observed, so no held-out episode can shape the
    catalog. Unlabeled train records are observed when ``observe_traces`` is
    set.

    Returns:
        Kept lessons with IDs, and dropped lessons with the reason.
    """
    sources = [r for r in records if r.split == "train" and (r.labeled or config.observe_traces)]
    payloads = {record.record_id: _observe_payload(record, config) for record in sources}
    batches = [sources[i : i + config.batch_size] for i in range(0, len(sources), config.batch_size)]

    def run(batch: Sequence[PreparedRecord]) -> Dict[str, List[Any]]:
        ids = [record.record_id for record in batch]
        payload = {"episodes": [payloads[record_id] for record_id in ids]}
        return calls.call("observe", OBSERVE_PROMPT, payload, partial(parse_observations, record_ids=ids))

    observed: Dict[str, List[Any]] = {}
    for result in _parallel(run, batches, config.workers):
        observed.update(result)

    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    for record in sources:
        for raw in observed[record.record_id]:
            lesson, reason = check_lesson(raw, payloads[record.record_id], config.min_lesson_confidence)
            if lesson is None:
                dropped.append({"record_id": record.record_id, "reason": reason, "lesson": raw})
                continue
            lesson.update(
                lesson_id=f"L{len(kept) + 1:04d}",
                record_id=record.record_id,
                route=payloads[record.record_id]["route"],
                source="feedback" if record.labeled else "trace",
            )
            kept.append(lesson)
    return kept, dropped


def _observe_payload(record: PreparedRecord, config: AssetConfig) -> Dict[str, Any]:
    payload = episode_view(record.row, config.trace)
    if record.labeled:
        payload["feedback"] = record.row["feedback"]
    return payload


def parse_observations(raw: Mapping[str, Any], *, record_ids: Sequence[str]) -> Dict[str, List[Any]]:
    """Return raw lessons by record ID; each lesson is checked separately."""
    episodes = raw["episodes"]
    if not isinstance(episodes, list):
        raise ValueError("episodes must be a list")
    found: Dict[str, List[Any]] = {}
    for episode in episodes:
        record_id = str(episode["record_id"])
        if record_id not in record_ids or record_id in found:
            raise ValueError(f"unexpected or repeated record_id '{record_id}'")
        lessons = episode["lessons"]
        if not isinstance(lessons, list):
            raise ValueError(f"lessons for '{record_id}' must be a list")
        found[record_id] = lessons
    missing = [record_id for record_id in record_ids if record_id not in found]
    if missing:
        raise ValueError(f"missing record_ids: {', '.join(missing)}")
    return found


def check_lesson(
    raw: Any,
    payload: Mapping[str, Any],
    min_confidence: float,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Validate one lesson and verify its quotes against the episode.

    An ``explicit`` signal needs a verified feedback quote; otherwise it is
    lowered to ``clear``.

    Returns:
        ``(lesson, None)`` when kept, or ``(None, reason)`` when dropped.
    """
    try:
        lesson = {
            "type": _choice(raw["type"], LESSON_TYPES, "type"),
            "lesson": _text(raw["lesson"], "lesson"),
            "signal": _choice(raw["signal"], SIGNALS, "signal"),
            "confidence": _unit(raw["confidence"], "confidence"),
        }
        knowable = raw["knowable"]
        quotes = [
            {
                "source": _choice(quote["source"], ("feedback", "trace"), "source"),
                "text": _text(quote["text"], "text"),
            }
            for quote in raw["evidence"]
        ]
    except (KeyError, TypeError, ValueError):
        return None, "malformed"
    if knowable is not True:
        return None, "needs_hindsight"
    if lesson["confidence"] < min_confidence:
        return None, "low_confidence"
    haystacks = {
        "feedback": _haystack(payload.get("feedback"), _FEEDBACK_SKIP),
        "trace": _haystack([payload.get("transcript"), payload.get("runtime")], _TRACE_SKIP),
    }
    verified = [quote for quote in quotes if _quote_found(quote["text"], haystacks[quote["source"]])]
    if not verified:
        return None, "unverified_evidence"
    if lesson["signal"] == "explicit" and not any(quote["source"] == "feedback" for quote in verified):
        lesson["signal"] = "clear"
    lesson["evidence"] = verified
    return lesson, None


def synthesize(calls: JsonCalls, lessons: Sequence[Mapping[str, Any]], config: AssetConfig) -> Dict[str, Any]:
    """Group lessons into a guideline catalog, one route at a time.

    Large routes are processed in chunks; each call updates the previous
    result. Code assigns guideline and criterion IDs and computes support:
    the number of distinct episodes behind a guideline. A guideline is
    ``strong`` with at least ``STRONG_SUPPORT`` episodes, and enters the
    catalog with at least ``min_guideline_support``.
    """
    by_id = {lesson["lesson_id"]: lesson for lesson in lessons}
    routes: Dict[str, List[Mapping[str, Any]]] = {}
    for lesson in lessons:
        routes.setdefault(lesson["route"], []).append(lesson)

    catalog: Dict[str, List[Dict[str, Any]]] = {
        "guidelines": [],
        "facts": [],
        "cannot_fix": [],
        "set_aside": [],
    }
    for route in sorted(routes):
        route_lessons = routes[route]
        result: Optional[Dict[str, Any]] = None
        for start in range(0, len(route_lessons), SYNTHESIS_CHUNK):
            chunk = route_lessons[start : start + SYNTHESIS_CHUNK]
            seen = {lesson["lesson_id"] for lesson in route_lessons[: start + SYNTHESIS_CHUNK]}
            payload = {
                "route": route,
                "lessons": [_synthesis_lesson(lesson) for lesson in chunk],
                "current": result,
            }
            result = calls.call(
                "synthesize", SYNTHESIZE_PROMPT, payload, partial(parse_synthesis, lesson_ids=seen)
            )
        assert result is not None
        for guideline in result["guidelines"]:
            catalog["guidelines"].append(
                _finish_guideline(guideline, route, by_id, config, len(catalog["guidelines"]) + 1)
            )
        catalog["facts"].extend({"route": route, "fact": fact} for fact in result["facts"])
        for name in ("cannot_fix", "set_aside"):
            catalog[name].extend({"route": route, **item} for item in result[name])
    return catalog


def _synthesis_lesson(lesson: Mapping[str, Any]) -> Dict[str, Any]:
    fields = ("lesson_id", "record_id", "type", "lesson", "evidence", "signal")
    return {name: lesson[name] for name in fields}


def _finish_guideline(
    guideline: Mapping[str, Any],
    route: str,
    lessons: Mapping[str, Mapping[str, Any]],
    config: AssetConfig,
    number: int,
) -> Dict[str, Any]:
    guideline_id = f"G{number:03d}"
    episodes = {lessons[lesson_id]["record_id"] for lesson_id in guideline["lesson_ids"]}
    signals = Counter(lessons[lesson_id]["signal"] for lesson_id in guideline["lesson_ids"])
    return {
        "guideline_id": guideline_id,
        "route": route,
        "title": guideline["title"],
        "dividing_line": guideline["dividing_line"],
        "criteria": [
            {"criterion_id": f"{guideline_id}.c{index}", **criterion}
            for index, criterion in enumerate(guideline["criteria"], start=1)
        ],
        "lesson_ids": list(guideline["lesson_ids"]),
        "counter_examples": list(guideline["counter_examples"]),
        "support": len(episodes),
        "signals": {signal: signals[signal] for signal in SIGNALS if signals[signal]},
        "strength": "strong" if len(episodes) >= STRONG_SUPPORT else "emerging",
        "included": len(episodes) >= config.min_guideline_support,
    }


def parse_synthesis(raw: Mapping[str, Any], *, lesson_ids: Set[str]) -> Dict[str, Any]:
    """Validate a synthesis result against the lesson IDs it must account for.

    Lessons the model left out are set aside with a reason, so every lesson
    stays visible in the review report.
    """
    accounted: Set[str] = set()

    def ids(value: Any, scope: str) -> List[str]:
        if not isinstance(value, list):
            raise ValueError(f"{scope} must be a list of lesson IDs")
        unknown = [str(item) for item in value if str(item) not in lesson_ids]
        if unknown:
            raise ValueError(f"{scope} names unknown lesson IDs: {', '.join(unknown)}")
        return [str(item) for item in value]

    guidelines = []
    for guideline in _list(raw["guidelines"], "guidelines"):
        supported = ids(guideline["lesson_ids"], "lesson_ids")
        if not supported:
            raise ValueError("every guideline needs at least one lesson ID")
        accounted.update(supported)
        guidelines.append(
            {
                "title": _text(guideline["title"], "title"),
                "dividing_line": _text(guideline["dividing_line"], "dividing_line"),
                "criteria": parse_criteria(guideline["criteria"], require=True),
                "lesson_ids": supported,
                "counter_examples": ids(guideline.get("counter_examples") or [], "counter_examples"),
            }
        )
    result: Dict[str, Any] = {
        "guidelines": guidelines,
        "facts": [_text(fact, "fact") for fact in _list(raw.get("facts") or [], "facts")],
    }
    for name in ("cannot_fix", "set_aside"):
        items = []
        for item in _list(raw.get(name) or [], name):
            listed = ids(item["lesson_ids"], f"{name}.lesson_ids")
            accounted.update(listed)
            items.append({"lesson_ids": listed, "reason": _text(item["reason"], "reason")})
        result[name] = items
    missing = sorted(lesson_ids - accounted)
    if missing:
        result["set_aside"].append({"lesson_ids": missing, "reason": "not addressed by the model"})
    return result


def write_rubrics(
    calls: JsonCalls,
    records: Sequence[PreparedRecord],
    catalog: Mapping[str, Any],
    config: AssetConfig,
) -> List[Dict[str, Any]]:
    """Write one rubric per record, in record order.

    A labeled record's own feedback is used only for its own rubric. The
    rubric's criteria are the chosen guidelines' criteria, verbatim, followed
    by the case-specific criteria.
    """
    guidelines = {g["guideline_id"]: g for g in catalog["guidelines"] if g["included"]}
    catalog_view = [
        {name: guideline[name] for name in ("guideline_id", "route", "title", "criteria")}
        for guideline in guidelines.values()
    ]

    def run(record: PreparedRecord) -> Dict[str, Any]:
        payload = {
            "catalog": catalog_view,
            "episode": episode_view(record.row, config.trace),
            "trusted_feedback": record.row["feedback"] if record.labeled else None,
        }
        parsed = calls.call(
            "rubric", RUBRIC_PROMPT, payload, partial(parse_rubric, guideline_ids=set(guidelines))
        )
        return assemble_rubric(record.record_id, parsed, guidelines)

    return _parallel(run, records, config.workers)


def parse_rubric(raw: Mapping[str, Any], *, guideline_ids: Set[str]) -> Dict[str, Any]:
    """Validate one rubric response.

    A criterion ID such as ``G001.c2`` names its guideline, ``G001``.
    """
    chosen = []
    for item in _list(raw["applicable_guideline_ids"], "applicable_guideline_ids"):
        guideline_id = str(item)
        if guideline_id not in guideline_ids and guideline_id.split(".")[0] in guideline_ids:
            guideline_id = guideline_id.split(".")[0]
        chosen.append(guideline_id)
    chosen = list(dict.fromkeys(chosen))
    unknown = [item for item in chosen if item not in guideline_ids]
    if unknown:
        raise ValueError(f"unknown guideline IDs: {', '.join(unknown)}")
    tool_expectations = raw.get("tool_expectations") or {}
    if not isinstance(tool_expectations, dict):
        raise ValueError("tool_expectations must be an object")
    reference = raw.get("reference_output")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("reference_output must be a string or null")
    return {
        "applicable_guideline_ids": chosen,
        "case_criteria": parse_criteria(raw["case_criteria"], require=False),
        "tool_expectations": tool_expectations,
        "reference_output": reference,
        "intent_label": str(raw.get("intent_label") or ""),
        "confidence": _unit(raw["confidence"], "confidence"),
    }


def assemble_rubric(
    record_id: str,
    parsed: Mapping[str, Any],
    guidelines: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Combine chosen catalog guidelines and case criteria into one rubric."""
    groups = [
        {
            "guideline_id": gid,
            "title": guidelines[gid]["title"],
            "criteria": list(guidelines[gid]["criteria"]),
        }
        for gid in parsed["applicable_guideline_ids"]
    ]
    if parsed["case_criteria"]:
        groups.append(
            {
                "guideline_id": "case",
                "title": "Case-specific criteria",
                "criteria": [
                    {"criterion_id": f"case.c{index}", **criterion}
                    for index, criterion in enumerate(parsed["case_criteria"], start=1)
                ],
            }
        )
    return {
        "record_id": record_id,
        "provenance": "guideline_grounded" if parsed["applicable_guideline_ids"] else "trace_inferred",
        "evaluation_guideline_ids": list(parsed["applicable_guideline_ids"]),
        "evaluation_guidelines": groups,
        "tool_expectations": parsed["tool_expectations"],
        "reference_output": parsed["reference_output"],
        "intent_label": parsed["intent_label"],
        "confidence": parsed["confidence"],
    }


def parse_criteria(value: Any, *, require: bool) -> List[Dict[str, str]]:
    """Validate a list of criteria; ``require`` rejects an empty list."""
    criteria = [
        {
            "kind": _choice(item["kind"], CRITERION_KINDS, "kind"),
            "statement": _text(item["statement"], "statement"),
            "applicability": _text(item["applicability"], "applicability"),
            "severity": _choice(item["severity"], SEVERITIES, "severity"),
            "scoring": _text(item["scoring"], "scoring"),
        }
        for item in _list(value, "criteria")
    ]
    if require and not criteria:
        raise ValueError("criteria must not be empty")
    return criteria


def _parallel(fn: Callable[[T], R], items: Sequence[T], workers: int) -> List[R]:
    if workers <= 1 or len(items) <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, items))


def _haystack(value: Any, skip: Set[str]) -> str:
    """Join the text values in ``value``, ignoring keys and the fields in ``skip``."""
    parts: List[str] = []

    def collect(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if key not in skip:
                    collect(nested)
        elif isinstance(item, list):
            for nested in item:
                collect(nested)
        elif isinstance(item, (str, int, float)) and not isinstance(item, bool):
            parts.append(_normalize(str(item)))

    collect(value)
    return "\x00".join(parts)


def _quote_found(quote: str, haystack: str) -> bool:
    """Match a quote verbatim, allowing elisions marked with an ellipsis.

    Each fragment between ellipses must appear, in order, within one text
    value of the episode.
    """
    parts = [part.strip(" \"'“”‘’") for part in re.split(r"\.\.\.|…", _normalize(quote))]
    parts = [part for part in parts if part]
    if sum(map(len, parts)) < _MIN_QUOTE_CHARS or any(len(part) < _MIN_FRAGMENT_CHARS for part in parts):
        return False
    pattern = ".*?".join(re.escape(part) for part in parts)
    return any(re.search(pattern, value) for value in haystack.split("\x00"))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold()


def _list(value: Any, name: str) -> Iterable[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _choice(value: Any, options: Sequence[str], name: str) -> str:
    if value not in options:
        raise ValueError(f"{name} must be one of {', '.join(options)}")
    return str(value)


def _unit(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be a number from 0 to 1")
    return float(value)
