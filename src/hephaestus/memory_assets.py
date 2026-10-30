# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Build compact runtime memory cards from evaluation assets built by ``assets build``."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Protocol, Sequence

from src.hephaestus.artifact_io import atomic_write_json, atomic_write_jsonl
from src.hephaestus.data_pipeline.config import TraceSettings
from src.hephaestus.data_pipeline.prepare import load_input
from src.hephaestus.data_pipeline.trace import episode_view, redact_record
from src.hephaestus.datasets.rubric_providers import (
    DEFAULT_OPENAI_RUBRIC_MODEL,
    OpenAIRubricProvider,
)

MEMORY_CARD_SCHEMA_VERSION = "fafo-runtime-memory-card-v1"
MEMORY_ASSET_SCHEMA_VERSION = "fafo-runtime-memory-asset-v1"
MEMORY_PROMPT_REVISION = "memory-card-v1"
SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")

MEMORY_CARD_PROMPT = """\
Convert one trusted FAFO evaluation guideline and a bounded set of its supporting
traces into one compact memory card that can be injected into an agent at run
time. The card teaches how to act; it must not talk about judging, scoring,
rubrics, datasets, or source records.

Use the guideline as the only source of normative requirements. Use the traces
to make those requirements procedural: preserve supported action ordering,
preconditions, decision points, tool-result checks, common failure patterns, and
repairs. A returned tool result proves only that an outcome was observed; it does
not prove that the tool choice, arguments, state change, or overall behavior was
correct. Distinguish agent mistakes from environment or tool failures.

Generalize private identifiers, names, addresses, exact amounts, order numbers,
and other case-specific values into placeholders. Do not copy hidden reasoning.
Do not invent policy, tool names, tool arguments, tool results, or successful
state changes. Tool advice should describe purpose and observable conditions;
require a literal tool name only when the guideline itself establishes it.

Return exactly one JSON object with a `memory_card` object containing exactly:
title, summary, when_to_use, when_not_to_use, instructions, avoid,
tool_guidance, and example_steps.

- title and summary are non-empty strings.
- when_to_use is a non-empty array of strings.
- when_not_to_use is an array of strings and may be empty.
- instructions is a non-empty array of objects with exactly `text` and
  `source_criterion_ids`. Every instruction must cite one or more criterion IDs
  supplied in the guideline.
- avoid and tool_guidance use the same object shape and may be empty.
- example_steps is an array of objects with exactly `text` and
  `source_trace_ids`. It may be empty. Every example step must cite one or more
  supplied trace aliases. Keep examples abstract and never claim an unobserved
  tool outcome.
"""

_BODY_FIELDS = {
    "title",
    "summary",
    "when_to_use",
    "when_not_to_use",
    "instructions",
    "avoid",
    "tool_guidance",
    "example_steps",
}


class MemoryCardProvider(Protocol):
    """Minimal JSON provider interface used by the memory compiler."""

    provider_name: str
    model: str

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return one JSON object."""


def _safe_name(value: str, field: str) -> str:
    if SAFE_NAME.fullmatch(value) is None:
        raise ValueError(f"{field} must be a safe identifier")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required source artifact is unavailable: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"source artifact must contain one JSON object: {path}")
    return payload


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required source artifact is unavailable: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row {line_number} must be an object: {path}")
        rows.append(row)
    return rows


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str, *, required: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array of strings")
    result = [_nonempty_string(item, field) for item in value]
    if required and not result:
        raise ValueError(f"{field} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _cited_items(
    value: Any,
    field: str,
    *,
    citation_field: str,
    allowed_ids: set[str],
    allowed_trace_ids: set[str] | None = None,
    required: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    result: list[dict[str, Any]] = []
    for item in value:
        allowed_fields = {"text", citation_field}
        if allowed_trace_ids is not None:
            allowed_fields.add("source_trace_ids")
        if (
            not isinstance(item, Mapping)
            or not {"text", citation_field}.issubset(item)
            or not set(item).issubset(allowed_fields)
        ):
            raise ValueError(f"{field} items must contain exactly text and {citation_field}")
        citations = _string_list(item[citation_field], f"{field}.{citation_field}", required=True)
        unknown = sorted(set(citations) - allowed_ids)
        if unknown:
            raise ValueError(f"{field} cites unknown IDs: {unknown}")
        if citation_field != "source_trace_ids" and "source_trace_ids" in item:
            trace_citations = _string_list(
                item["source_trace_ids"],
                f"{field}.source_trace_ids",
                required=True,
            )
            unknown_traces = sorted(set(trace_citations) - (allowed_trace_ids or set()))
            if unknown_traces:
                raise ValueError(f"{field} cites unknown trace IDs: {unknown_traces}")
        result.append(
            {
                "text": _nonempty_string(item["text"], f"{field}.text"),
                citation_field: citations,
            }
        )
    if required and not result:
        raise ValueError(f"{field} must not be empty")
    return result


def _normalize_memory_body(
    response: Mapping[str, Any],
    *,
    criterion_ids: set[str],
    trace_aliases: set[str],
) -> dict[str, Any]:
    if set(response) != {"memory_card"} or not isinstance(response["memory_card"], Mapping):
        raise ValueError("memory response must contain exactly one memory_card object")
    raw = response["memory_card"]
    if set(raw) != _BODY_FIELDS:
        raise ValueError("memory_card fields do not match the v1 contract")
    return {
        "title": _nonempty_string(raw["title"], "title"),
        "summary": _nonempty_string(raw["summary"], "summary"),
        "when_to_use": _string_list(raw["when_to_use"], "when_to_use", required=True),
        "when_not_to_use": _string_list(raw["when_not_to_use"], "when_not_to_use"),
        "instructions": _cited_items(
            raw["instructions"],
            "instructions",
            citation_field="source_criterion_ids",
            allowed_ids=criterion_ids,
            allowed_trace_ids=trace_aliases,
            required=True,
        ),
        "avoid": _cited_items(
            raw["avoid"],
            "avoid",
            citation_field="source_criterion_ids",
            allowed_ids=criterion_ids,
            allowed_trace_ids=trace_aliases,
        ),
        "tool_guidance": _cited_items(
            raw["tool_guidance"],
            "tool_guidance",
            citation_field="source_criterion_ids",
            allowed_ids=criterion_ids,
            allowed_trace_ids=trace_aliases,
        ),
        "example_steps": _cited_items(
            raw["example_steps"],
            "example_steps",
            citation_field="source_trace_ids",
            allowed_ids=trace_aliases,
        ),
    }


@dataclass
class SourceAsset:
    """A finished evaluation asset, read for memory construction.

    Attributes:
        root: The asset directory.
        model: The model the asset was built with.
        trace_settings: The asset's tool-result compaction settings.
        guidelines: Catalog guidelines that entered the catalog, each with
            ``source_record_ids`` (its train feedback episodes) and
            ``confidence`` (the mean confidence of its lessons).
        feedback_by_id: Feedback records, redacted as the build redacted them.
        unlabeled_by_id: Unlabeled records, redacted the same way.
        split_by_id: The split of every kept record.
        source_files: Files whose hashes the memory manifest records.
    """

    root: Path
    model: str
    trace_settings: TraceSettings
    guidelines: list[dict[str, Any]]
    feedback_by_id: dict[str, dict[str, Any]]
    unlabeled_by_id: dict[str, dict[str, Any]]
    split_by_id: dict[str, str]
    source_files: dict[str, Path]


def load_source_asset(tenant_root: Path, asset_id: str) -> SourceAsset:
    """Read a finished asset under ``tenant_root/evaluation_assets/``.

    Raises:
        ValueError: If the asset is unfinished or its files are inconsistent.
    """
    root = tenant_root / "evaluation_assets" / asset_id
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"source evaluation asset is not finished (no manifest.json): {root}")
    settings = _load_json(root / "build.json").get("settings")
    if not isinstance(settings, Mapping):
        raise ValueError(f"source evaluation asset has no build settings: {root}")
    trace_settings = TraceSettings(**dict(settings.get("trace") or {}))
    prepare = redact_record if settings.get("redact", True) else dict

    feedback_path = root / "inputs" / "feedback.jsonl"
    unlabeled_path = root / "inputs" / "unlabeled.jsonl"
    feedback = {str(row["record_id"]): prepare(row) for row in load_input(feedback_path, labeled=True)}
    unlabeled = (
        {str(row["record_id"]): prepare(row) for row in load_input(unlabeled_path, labeled=False)}
        if unlabeled_path.is_file()
        else {}
    )
    split_by_id = {str(row["record_id"]): str(row["split"]) for row in _load_jsonl(root / "splits.jsonl")}
    lessons = {str(row["lesson_id"]): row for row in _load_jsonl(root / "lessons.jsonl")}

    guidelines = []
    for guideline in _load_json(root / "catalog.json").get("guidelines") or []:
        if not guideline.get("included"):
            continue
        guideline_id = _nonempty_string(guideline.get("guideline_id"), "guideline_id")
        supporting = [lessons[str(lesson_id)] for lesson_id in guideline.get("lesson_ids") or []]
        if not supporting:
            raise ValueError(f"guideline {guideline_id} has no lessons")
        trusted = sorted(
            {str(lesson["record_id"]) for lesson in supporting if lesson.get("source") == "feedback"}
        )
        guidelines.append(
            {
                **guideline,
                "source_record_ids": trusted,
                "confidence": round(mean(float(lesson["confidence"]) for lesson in supporting), 4),
            }
        )
    files = {
        "manifest.json": manifest_path,
        "build.json": root / "build.json",
        "catalog.json": root / "catalog.json",
        "lessons.jsonl": root / "lessons.jsonl",
        "inputs/feedback.jsonl": feedback_path,
    }
    return SourceAsset(
        root=root,
        model=str(settings.get("model") or DEFAULT_OPENAI_RUBRIC_MODEL),
        trace_settings=trace_settings,
        guidelines=guidelines,
        feedback_by_id=feedback,
        unlabeled_by_id=unlabeled,
        split_by_id=split_by_id,
        source_files=files,
    )


def guideline_payload(guideline: Mapping[str, Any]) -> dict[str, Any]:
    """Return the guideline fields a memory prompt needs."""
    fields = ("guideline_id", "route", "title", "dividing_line", "criteria", "strength", "support")
    return {name: guideline[name] for name in fields if name in guideline}


def trace_view(row: Mapping[str, Any], settings: TraceSettings) -> dict[str, Any]:
    """Return an episode view without its record ID, which prompts see only as an alias."""
    view = episode_view(row, settings)
    view.pop("record_id")
    return view


def _feedback_polarity(row: Mapping[str, Any]) -> str:
    feedback = row.get("feedback")
    if isinstance(feedback, Mapping):
        return str(feedback.get("polarity") or "").lower()
    return ""


def _select_supporting_rows(
    source_ids: Sequence[str],
    rows_by_id: Mapping[str, Mapping[str, Any]],
    limit: int,
) -> list[Mapping[str, Any]]:
    rows = [rows_by_id[source_id] for source_id in sorted(source_ids)]
    selected: list[Mapping[str, Any]] = []
    for polarity in ("positive", "negative"):
        match = next((row for row in rows if _feedback_polarity(row) == polarity), None)
        if match is not None and match not in selected:
            selected.append(match)
    for row in rows:
        if row not in selected:
            selected.append(row)
    return selected[:limit]


def _supporting_trace(row: Mapping[str, Any], alias: str, settings: TraceSettings) -> dict[str, Any]:
    feedback = row.get("feedback")
    return {
        "trace_id": alias,
        "evidence_tier": "trusted_feedback_trace",
        "task_type": str(row.get("task_type") or ""),
        "route": str(row.get("route") or row.get("task_type") or ""),
        "trace": trace_view(row, settings),
        "trusted_feedback": dict(feedback) if isinstance(feedback, Mapping) else None,
    }


def inferred_supporting_trace(
    case: Mapping[str, Any],
    raw: Mapping[str, Any],
    alias: str,
    settings: TraceSettings,
) -> dict[str, Any]:
    """Return one inferred training case and its trace as memory evidence."""
    metadata = case["metadata"]
    expected = case["expected"]
    case_criteria = [
        criterion
        for group in expected.get("evaluation_guidelines") or []
        if group.get("guideline_id") == "case"
        for criterion in group.get("criteria") or []
    ]
    return {
        "trace_id": alias,
        "evidence_tier": "inferred_training_trace",
        "inferred_case_id": str(case.get("case_id") or ""),
        "source_record_id": str(metadata["record_id"]),
        "task_type": str(case.get("task_type") or ""),
        "route": str(metadata.get("route") or case.get("task_type") or ""),
        "source_group": str(metadata.get("group_id") or ""),
        "rubric_confidence": float(expected.get("confidence") or 0.0),
        "case_criteria": case_criteria,
        "trace": trace_view(raw, settings),
        "trusted_feedback": None,
    }


def _render_memory(body: Mapping[str, Any]) -> str:
    lines = [
        f"Runtime memory: {body['title']}",
        (
            "Use this as relevant prior experience. Current system instructions, "
            "policies, tool definitions, and observed state take precedence."
        ),
        str(body["summary"]),
        "",
        "Use when:",
    ]
    lines.extend(f"- {item}" for item in body["when_to_use"])
    if body["when_not_to_use"]:
        lines.extend(["", "Do not use when:"])
        lines.extend(f"- {item}" for item in body["when_not_to_use"])
    lines.extend(["", "Procedure:"])
    lines.extend(f"{index}. {item['text']}" for index, item in enumerate(body["instructions"], start=1))
    if body["avoid"]:
        lines.extend(["", "Avoid:"])
        lines.extend(f"- {item['text']}" for item in body["avoid"])
    if body["tool_guidance"]:
        lines.extend(["", "Tool guidance:"])
        lines.extend(f"- {item['text']}" for item in body["tool_guidance"])
    if body["example_steps"]:
        lines.extend(["", "Abstract example:"])
        lines.extend(f"{index}. {item['text']}" for index, item in enumerate(body["example_steps"], start=1))
    return "\n".join(lines)


def _memory_id(guideline_id: str, body: Mapping[str, Any]) -> str:
    identity = json.dumps(
        {
            "schema_version": MEMORY_CARD_SCHEMA_VERSION,
            "guideline_id": guideline_id,
            "body": dict(body),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "memory-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _provider_calls(
    provider: MemoryCardProvider,
    *,
    guideline_id: str,
    call_index: int,
) -> list[dict[str, Any]]:
    drain = getattr(provider, "drain_call_metadata", None)
    if not callable(drain):
        return []
    rows = drain()
    if not isinstance(rows, list):
        raise ValueError("provider call metadata must be an array")
    return [
        {
            "call_index": call_index,
            "guideline_id": guideline_id,
            "provider": provider.provider_name,
            "model": provider.model,
            "transport": dict(row) if isinstance(row, Mapping) else {},
        }
        for row in rows
    ]


def build_memory_asset(
    *,
    tenants_root: Path,
    tenant_id: str,
    source_asset_id: str,
    memory_asset_id: str,
    model: str | None = None,
    max_source_traces: int = 5,
    provider: MemoryCardProvider | None = None,
) -> dict[str, Any]:
    """Compile one trusted-only runtime memory card per reusable guideline."""
    tenant_id = _safe_name(tenant_id, "tenant_id")
    source_asset_id = _safe_name(source_asset_id, "source_asset_id")
    memory_asset_id = _safe_name(memory_asset_id, "memory_asset_id")
    if max_source_traces < 1:
        raise ValueError("max_source_traces must be positive")

    tenants_root = tenants_root.resolve()
    tenant_root = tenants_root / tenant_id
    output_root = tenant_root / "memory_assets" / memory_asset_id
    if output_root.exists():
        raise FileExistsError(f"memory asset already exists: {output_root}")

    source = load_source_asset(tenant_root, source_asset_id)
    guidelines = [guideline for guideline in source.guidelines if guideline["source_record_ids"]]
    skipped_guideline_ids = sorted(
        str(guideline["guideline_id"])
        for guideline in source.guidelines
        if not guideline["source_record_ids"]
    )
    if not guidelines:
        raise ValueError("source evaluation asset has no guidelines backed by trusted feedback")
    rows_by_id = source.feedback_by_id

    selected_model = model or source.model
    active_provider = provider or OpenAIRubricProvider(model=selected_model)
    if model is not None and active_provider.model != model:
        raise ValueError("injected provider model does not match requested model")

    cards: list[dict[str, Any]] = []
    call_rows: list[dict[str, Any]] = []
    for call_index, guideline in enumerate(
        sorted(guidelines, key=lambda item: str(item.get("guideline_id") or "")),
        start=1,
    ):
        guideline_id = _nonempty_string(guideline.get("guideline_id"), "guideline_id")
        source_ids = _string_list(
            guideline.get("source_record_ids"),
            "source_record_ids",
            required=True,
        )
        missing = sorted(set(source_ids) - set(rows_by_id))
        if missing:
            raise ValueError(f"guideline {guideline_id} has missing source records: {missing}")
        for source_id in source_ids:
            if source.split_by_id.get(source_id) != "train":
                raise ValueError(f"guideline {guideline_id} cites non-train feedback: {source_id}")

        criteria = guideline.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            raise ValueError(f"guideline {guideline_id} has no criteria")
        criterion_ids = {
            _nonempty_string(item.get("criterion_id"), "criterion_id")
            for item in criteria
            if isinstance(item, Mapping)
        }
        if len(criterion_ids) != len(criteria):
            raise ValueError(f"guideline {guideline_id} has invalid criterion IDs")

        selected_rows = _select_supporting_rows(source_ids, rows_by_id, max_source_traces)
        alias_by_id = {
            str(row["record_id"]): f"trace-{index:03d}" for index, row in enumerate(selected_rows, start=1)
        }
        supporting_traces = [
            _supporting_trace(row, alias_by_id[str(row["record_id"])], source.trace_settings)
            for row in selected_rows
        ]
        response = active_provider.generate_json(
            MEMORY_CARD_PROMPT,
            {
                "mode": "runtime_memory_card",
                "evidence_mode": "trusted_only",
                "guideline": guideline_payload(guideline),
                "supporting_traces": supporting_traces,
            },
        )
        body = _normalize_memory_body(
            response,
            criterion_ids=criterion_ids,
            trace_aliases=set(alias_by_id.values()),
        )
        restored_example_steps = [
            {
                "text": item["text"],
                "source_record_ids": [
                    next(record_id for record_id, alias in alias_by_id.items() if alias == trace_alias)
                    for trace_alias in item["source_trace_ids"]
                ],
            }
            for item in body["example_steps"]
        ]
        body["example_steps"] = restored_example_steps
        card = {
            "schema_version": MEMORY_CARD_SCHEMA_VERSION,
            "memory_id": _memory_id(guideline_id, body),
            "source_guideline_id": guideline_id,
            "route": str(guideline.get("route") or "default"),
            "title": body["title"],
            "summary": body["summary"],
            "when_to_use": body["when_to_use"],
            "when_not_to_use": body["when_not_to_use"],
            "instructions": body["instructions"],
            "avoid": body["avoid"],
            "tool_guidance": body["tool_guidance"],
            "example_steps": body["example_steps"],
            "injection_text": _render_memory(body),
            "confidence": float(guideline.get("confidence") or 0.5),
            "trust_tier": "trusted_feedback",
            "source_record_ids": source_ids,
            "selected_source_record_ids": sorted(alias_by_id),
            "selected_trusted_record_ids": sorted(alias_by_id),
            "eligible_inferred_case_count": 0,
            "selected_inferred_case_ids": [],
            "selected_inferred_record_ids": [],
            "provider": active_provider.provider_name,
            "model": active_provider.model,
            "prompt_revision": MEMORY_PROMPT_REVISION,
        }
        cards.append(card)
        call_rows.extend(
            _provider_calls(
                active_provider,
                guideline_id=guideline_id,
                call_index=call_index,
            )
        )

    output_root.mkdir(parents=True, exist_ok=False)
    cards_path = output_root / "memory_cards.jsonl"
    calls_path = output_root / "provider_calls.jsonl"
    atomic_write_jsonl(cards_path, cards)
    atomic_write_jsonl(calls_path, call_rows)
    manifest = {
        "schema_version": MEMORY_ASSET_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "memory_asset_id": memory_asset_id,
        "source_evaluation_asset_id": source_asset_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "card_count": len(cards),
        "provider": active_provider.provider_name,
        "model": active_provider.model,
        "max_source_traces": max_source_traces,
        "skipped_guideline_ids": skipped_guideline_ids,
        "evidence_mode": "trusted_only",
        "include_inferred": False,
        "inferred_candidate_pool": 0,
        "max_inferred_traces": 0,
        "prompt_revision": MEMORY_PROMPT_REVISION,
        "prompt_sha256": "sha256:" + hashlib.sha256(MEMORY_CARD_PROMPT.encode("utf-8")).hexdigest(),
        "source_artifacts": {name: _file_sha256(path) for name, path in source.source_files.items()},
        "artifacts": {
            "memory_cards.jsonl": _file_sha256(cards_path),
            "provider_calls.jsonl": _file_sha256(calls_path),
        },
    }
    atomic_write_json(output_root / "manifest.json", manifest)
    return {**manifest, "output_path": str(output_root)}


__all__ = [
    "SourceAsset",
    "load_source_asset",
    "MEMORY_CARD_PROMPT",
    "MEMORY_CARD_SCHEMA_VERSION",
    "MEMORY_ASSET_SCHEMA_VERSION",
    "build_memory_asset",
]
