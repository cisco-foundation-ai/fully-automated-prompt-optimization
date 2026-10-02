# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Extend trusted runtime memory cards with mined inferred-trace evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from src.hephaestus.artifact_io import atomic_write_json, atomic_write_jsonl
from src.hephaestus.datasets.rubric_providers import (
    DEFAULT_OPENAI_RUBRIC_MODEL,
    OpenAIRubricProvider,
)
from src.hephaestus.memory_assets import (
    MEMORY_ASSET_SCHEMA_VERSION,
    MEMORY_CARD_SCHEMA_VERSION,
    MemoryCardProvider,
    _file_sha256,
    _inferred_supporting_trace,
    _inferred_trace_details,
    _load_json,
    _load_jsonl,
    _memory_id,
    _nonempty_string,
    _render_memory,
    _safe_name,
    _string_list,
)

EVIDENCE_MINING_REVISION = "memory-evidence-mining-v1"
ADDITIVE_MEMORY_REVISION = "memory-card-additive-evidence-v1"
PATTERN_KINDS = frozenset({"procedure", "avoid", "tool_guidance", "example"})

EVIDENCE_MINING_PROMPT = """\
Mine compact, reusable runtime-memory evidence from a batch of approved inferred
training traces. The supplied trusted guidelines are the only normative source.
The trusted memory spines must not be rewritten, weakened, or contradicted.

For each trace, compare observable user and assistant messages, tool calls,
arguments, results, and errors with its applicable trusted guidelines and
case-specific rubric. Extract a pattern only when it adds useful procedural
knowledge not already expressed by the trusted memory spine. Valid patterns
include a successful procedure, a clearly criterion-grounded agent mistake, a
repair, tool-state guidance, or an abstract example. A tool error, rejected
operation, or incomplete outcome is not automatically an agent mistake.

Ignore ambiguous evidence. Do not infer policy from recurrence. Do not invent
tool names, arguments, outcomes, or hidden reasoning. Generalize private and
case-specific values. Pattern text must be suitable for later agent injection
and must not mention scoring, rubrics, datasets, source records, or judges.

Return exactly one JSON object with exactly one field, `patterns`. `patterns`
is an array of at most 12 objects. Every object contains exactly:
guideline_id, kind, text, source_criterion_ids, source_trace_ids, confidence.

- guideline_id must be one supplied applicable guideline ID.
- kind is one of: procedure, avoid, tool_guidance, example.
- text is one concise non-empty string.
- source_criterion_ids cites one or more criteria from that guideline.
- source_trace_ids cites one or more trace IDs from this batch for which the
  guideline is applicable.
- confidence is between 0 and 1.

Return an empty array when the batch contains no genuinely additive evidence.
"""

ADDITIVE_CONSOLIDATION_PROMPT = """\
Select a very small inferred-evidence addendum for one trusted runtime memory
card. The trusted guideline is the only normative source, and the trusted memory
spine is frozen. Do not rewrite, paraphrase, remove, or repeat anything already
in the spine.

Choose only patterns that add material procedural value and are directly
supported by their cited traces and trusted criteria. Prefer patterns supported
across multiple traces or clusters, but retain a rare critical failure pattern
when its evidence is clear. Do not promote ambiguous behavior or ordinary tool
errors. Keep the final card focused: return at most three additions total.

Return exactly one JSON object with exactly one field, `additions`. `additions`
is an array of objects containing exactly: kind, text, source_criterion_ids,
source_trace_ids, source_pattern_ids.

- kind is one of: procedure, avoid, tool_guidance, example.
- text is concise agent-facing guidance and does not mention evidence, scoring,
  rubrics, datasets, source records, or judges.
- every cited criterion, trace, and pattern ID must be supplied.
- an addition may cite only source patterns of the same kind.

Return an empty array when the candidate patterns do not improve the trusted
memory spine.
"""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sha256_value(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _trusted_body(card: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "title": card["title"],
        "summary": card["summary"],
        "when_to_use": deepcopy(card["when_to_use"]),
        "when_not_to_use": deepcopy(card["when_not_to_use"]),
        "instructions": deepcopy(card["instructions"]),
        "avoid": deepcopy(card["avoid"]),
        "tool_guidance": deepcopy(card["tool_guidance"]),
        "example_steps": deepcopy(card["example_steps"]),
    }


def _guideline_for_mining(
    guideline: Mapping[str, Any],
    card: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "guideline_id": guideline["guideline_id"],
        "description": guideline.get("description"),
        "criteria": guideline.get("criteria"),
        "tool_expectations": guideline.get("tool_expectations"),
        "trusted_memory_spine": _trusted_body(card),
    }


def _validate_inferred_cases(
    cases: Sequence[Mapping[str, Any]],
    *,
    guideline_ids: set[str],
    raw_rows_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    seen: set[str] = set()
    for case in cases:
        case_id = _nonempty_string(case.get("case_id"), "case_id")
        if case_id in seen:
            raise ValueError("inferred training case IDs must be unique")
        seen.add(case_id)
        metadata = case.get("metadata")
        expected = case.get("expected")
        if not isinstance(metadata, Mapping) or not isinstance(expected, Mapping):
            raise ValueError(f"inferred case {case_id} is missing metadata or expected")
        if (
            metadata.get("review_status") != "approved"
            or metadata.get("split") != "train"
            or metadata.get("trust_tier") != "inferred_from_trusted_feedback"
        ):
            raise ValueError(f"inferred case is not approved train evidence: {case_id}")
        applicable = _string_list(
            metadata.get("applicable_guideline_ids"),
            f"{case_id}.applicable_guideline_ids",
            required=True,
        )
        expected_ids = _string_list(
            expected.get("evaluation_guideline_ids"),
            f"{case_id}.evaluation_guideline_ids",
            required=True,
        )
        if set(applicable) != set(expected_ids):
            raise ValueError(f"inferred case guideline bindings disagree: {case_id}")
        unknown = sorted(set(applicable) - guideline_ids)
        if unknown:
            raise ValueError(f"inferred case {case_id} cites unknown guidelines: {unknown}")
        request_id = _nonempty_string(metadata.get("request_id"), f"{case_id}.request_id")
        if request_id not in raw_rows_by_id:
            raise ValueError(f"approved inferred case has no source trace: {request_id}")


def _cluster_interleaved(cases: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    buckets: dict[str, deque[Mapping[str, Any]]] = defaultdict(deque)
    for case in sorted(cases, key=lambda item: str(item.get("case_id") or "")):
        metadata = case["metadata"]
        buckets[str(metadata.get("source_cluster") or "unclustered")].append(case)
    ordered: list[Mapping[str, Any]] = []
    while buckets:
        for cluster in sorted(list(buckets)):
            ordered.append(buckets[cluster].popleft())
            if not buckets[cluster]:
                del buckets[cluster]
    return ordered


def _trace_index(
    cases: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    alias_by_case_id = {
        str(case["case_id"]): f"trace-{index:06d}"
        for index, case in enumerate(
            sorted(cases, key=lambda item: str(item.get("case_id") or "")),
            start=1,
        )
    }
    rows = []
    for case in sorted(cases, key=lambda item: str(item.get("case_id") or "")):
        metadata = case["metadata"]
        rows.append(
            {
                "trace_id": alias_by_case_id[str(case["case_id"])],
                "inferred_case_id": str(case["case_id"]),
                "source_record_id": str(metadata["request_id"]),
                "source_cluster": str(metadata.get("source_cluster") or "unclustered"),
                "applicable_guideline_ids": list(metadata["applicable_guideline_ids"]),
            }
        )
    return alias_by_case_id, rows


def _episode_for_mining(
    case: Mapping[str, Any],
    *,
    alias: str,
    raw_rows_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    details = _inferred_trace_details(case, raw_rows_by_id)
    row = _inferred_supporting_trace(details, alias)
    return {
        "trace_id": row["trace_id"],
        "inferred_case_id": row["inferred_case_id"],
        "source_cluster": row["source_cluster"],
        "rubric_confidence": row["rubric_confidence"],
        "applicable_guideline_ids": list(case["metadata"]["applicable_guideline_ids"]),
        "case_specific_rubric": row["case_specific_rubric"],
        "trace": row["trace"],
    }


def _normalize_patterns(
    response: Mapping[str, Any],
    *,
    batch_trace_guidelines: Mapping[str, set[str]],
    criterion_ids_by_guideline: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    if set(response) != {"patterns"} or not isinstance(response["patterns"], list):
        raise ValueError("evidence response must contain exactly one patterns array")
    if len(response["patterns"]) > 12:
        raise ValueError("evidence response exceeds 12 patterns")
    normalized = []
    required_fields = {
        "guideline_id",
        "kind",
        "text",
        "source_criterion_ids",
        "source_trace_ids",
        "confidence",
    }
    for raw in response["patterns"]:
        if not isinstance(raw, Mapping) or set(raw) != required_fields:
            raise ValueError("evidence pattern fields do not match the contract")
        guideline_id = _nonempty_string(raw["guideline_id"], "guideline_id")
        if guideline_id not in criterion_ids_by_guideline:
            raise ValueError(f"pattern cites unknown guideline: {guideline_id}")
        kind = _nonempty_string(raw["kind"], "kind")
        if kind not in PATTERN_KINDS:
            raise ValueError(f"pattern kind is invalid: {kind}")
        criterion_ids = _string_list(
            raw["source_criterion_ids"],
            "source_criterion_ids",
            required=True,
        )
        unknown_criteria = sorted(
            set(criterion_ids) - criterion_ids_by_guideline[guideline_id]
        )
        if unknown_criteria:
            raise ValueError(f"pattern cites unknown criteria: {unknown_criteria}")
        trace_ids = _string_list(
            raw["source_trace_ids"],
            "source_trace_ids",
            required=True,
        )
        for trace_id in trace_ids:
            if guideline_id not in batch_trace_guidelines.get(trace_id, set()):
                raise ValueError(
                    f"pattern trace {trace_id} is not bound to guideline {guideline_id}"
                )
        confidence = float(raw["confidence"])
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("pattern confidence must be between 0 and 1")
        normalized.append(
            {
                "guideline_id": guideline_id,
                "kind": kind,
                "text": _nonempty_string(raw["text"], "text"),
                "source_criterion_ids": criterion_ids,
                "source_trace_ids": trace_ids,
                "confidence": confidence,
            }
        )
    return normalized


def _pattern_key(pattern: Mapping[str, Any]) -> tuple[str, str, str]:
    normalized_text = re.sub(r"[^a-z0-9]+", " ", str(pattern["text"]).lower()).strip()
    return (str(pattern["guideline_id"]), str(pattern["kind"]), normalized_text)


def _consolidate_exact_patterns(
    patterns: Sequence[Mapping[str, Any]],
    *,
    trace_clusters: Mapping[str, str],
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
    for pattern in patterns:
        key = _pattern_key(pattern)
        if key not in merged:
            merged[key] = {
                "guideline_id": pattern["guideline_id"],
                "kind": pattern["kind"],
                "text": pattern["text"],
                "source_criterion_ids": set(pattern["source_criterion_ids"]),
                "source_trace_ids": set(pattern["source_trace_ids"]),
                "confidence": float(pattern["confidence"]),
            }
        else:
            merged[key]["source_criterion_ids"].update(pattern["source_criterion_ids"])
            merged[key]["source_trace_ids"].update(pattern["source_trace_ids"])
            merged[key]["confidence"] = max(
                merged[key]["confidence"],
                float(pattern["confidence"]),
            )
    result = []
    for key in sorted(merged):
        item = merged[key]
        trace_ids = sorted(item["source_trace_ids"])
        identity = {
            "guideline_id": item["guideline_id"],
            "kind": item["kind"],
            "normalized_text": key[2],
        }
        result.append(
            {
                "pattern_id": "pattern-"
                + hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()[:16],
                "guideline_id": item["guideline_id"],
                "kind": item["kind"],
                "text": item["text"],
                "source_criterion_ids": sorted(item["source_criterion_ids"]),
                "source_trace_ids": trace_ids,
                "source_clusters": sorted({trace_clusters[trace_id] for trace_id in trace_ids}),
                "support_count": len(trace_ids),
                "confidence": item["confidence"],
            }
        )
    return result


def _normalize_additions(
    response: Mapping[str, Any],
    *,
    patterns_by_id: Mapping[str, Mapping[str, Any]],
    criterion_ids: set[str],
    max_additions: int,
) -> list[dict[str, Any]]:
    if set(response) != {"additions"} or not isinstance(response["additions"], list):
        raise ValueError("consolidation response must contain exactly one additions array")
    if len(response["additions"]) > max_additions:
        raise ValueError(f"consolidation response exceeds {max_additions} additions")
    required_fields = {
        "kind",
        "text",
        "source_criterion_ids",
        "source_trace_ids",
        "source_pattern_ids",
    }
    additions = []
    seen_text: set[str] = set()
    for raw in response["additions"]:
        if not isinstance(raw, Mapping) or set(raw) != required_fields:
            raise ValueError("addition fields do not match the contract")
        kind = _nonempty_string(raw["kind"], "kind")
        if kind not in PATTERN_KINDS:
            raise ValueError(f"addition kind is invalid: {kind}")
        text = _nonempty_string(raw["text"], "text")
        text_key = re.sub(r"\s+", " ", text.lower()).strip()
        if text_key in seen_text:
            raise ValueError("consolidation response contains duplicate additions")
        seen_text.add(text_key)
        pattern_ids = _string_list(
            raw["source_pattern_ids"],
            "source_pattern_ids",
            required=True,
        )
        unknown_patterns = sorted(set(pattern_ids) - set(patterns_by_id))
        if unknown_patterns:
            raise ValueError(f"addition cites unknown patterns: {unknown_patterns}")
        source_patterns = [patterns_by_id[pattern_id] for pattern_id in pattern_ids]
        if any(pattern["kind"] != kind for pattern in source_patterns):
            raise ValueError("addition kind does not match every source pattern")
        allowed_criteria = {
            criterion_id
            for pattern in source_patterns
            for criterion_id in pattern["source_criterion_ids"]
        }
        addition_criteria = _string_list(
            raw["source_criterion_ids"],
            "source_criterion_ids",
            required=True,
        )
        if not set(addition_criteria).issubset(criterion_ids & allowed_criteria):
            raise ValueError("addition criteria are not supported by cited patterns")
        allowed_traces = {
            trace_id
            for pattern in source_patterns
            for trace_id in pattern["source_trace_ids"]
        }
        addition_traces = _string_list(
            raw["source_trace_ids"],
            "source_trace_ids",
            required=True,
        )
        if not set(addition_traces).issubset(allowed_traces):
            raise ValueError("addition traces are not supported by cited patterns")
        additions.append(
            {
                "kind": kind,
                "text": text,
                "source_criterion_ids": addition_criteria,
                "source_trace_ids": addition_traces,
                "source_pattern_ids": pattern_ids,
            }
        )
    return additions


def _drain_provider_calls(
    provider: MemoryCardProvider,
    *,
    phase: str,
    identifier: str,
    call_index: int,
    attempt: int,
    validation_error: str | None,
) -> list[dict[str, Any]]:
    drain = getattr(provider, "drain_call_metadata", None)
    rows = drain() if callable(drain) else []
    if not isinstance(rows, list):
        raise ValueError("provider call metadata must be an array")
    return [
        {
            "call_index": call_index,
            "phase": phase,
            "identifier": identifier,
            "attempt": attempt,
            "validation_error": validation_error,
            "provider": provider.provider_name,
            "model": provider.model,
            "transport": dict(row) if isinstance(row, Mapping) else {},
        }
        for row in rows
    ]


def _generate_validated(
    *,
    provider: MemoryCardProvider,
    prompt: str,
    payload: Mapping[str, Any],
    validator: Callable[[Mapping[str, Any]], list[dict[str, Any]]],
    phase: str,
    identifier: str,
    call_rows: list[dict[str, Any]],
    call_counter: list[int],
    max_attempts: int = 3,
) -> list[dict[str, Any]]:
    last_error: ValueError | None = None
    retry_payload = dict(payload)
    for attempt in range(1, max_attempts + 1):
        call_counter[0] += 1
        response = provider.generate_json(prompt, retry_payload)
        try:
            normalized = validator(response)
        except ValueError as error:
            last_error = error
            call_rows.extend(
                _drain_provider_calls(
                    provider,
                    phase=phase,
                    identifier=identifier,
                    call_index=call_counter[0],
                    attempt=attempt,
                    validation_error=str(error),
                )
            )
            retry_payload = {
                **payload,
                "retry_contract_error": str(error),
                "retry_instruction": "Return the exact requested JSON contract only.",
            }
            continue
        call_rows.extend(
            _drain_provider_calls(
                provider,
                phase=phase,
                identifier=identifier,
                call_index=call_counter[0],
                attempt=attempt,
                validation_error=None,
            )
        )
        return normalized
    raise ValueError(f"{phase} failed validation after {max_attempts} attempts") from last_error


def _append_additions(
    base_card: Mapping[str, Any],
    additions: Sequence[Mapping[str, Any]],
    *,
    source_record_by_trace: Mapping[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    body = _trusted_body(base_card)
    restored = []
    for addition in additions:
        item = {
            "kind": addition["kind"],
            "text": addition["text"],
            "source_criterion_ids": list(addition["source_criterion_ids"]),
            "source_record_ids": [
                source_record_by_trace[trace_id]
                for trace_id in addition["source_trace_ids"]
            ],
            "source_pattern_ids": list(addition["source_pattern_ids"]),
        }
        restored.append(item)
        if addition["kind"] == "example":
            body["example_steps"].append(
                {
                    "text": addition["text"],
                    "source_record_ids": item["source_record_ids"],
                }
            )
        else:
            target = {
                "procedure": "instructions",
                "avoid": "avoid",
                "tool_guidance": "tool_guidance",
            }[str(addition["kind"])]
            body[target].append(
                {
                    "text": addition["text"],
                    "source_criterion_ids": list(addition["source_criterion_ids"]),
                }
            )
    return body, restored


def build_additive_memory_asset(
    *,
    tenants_root: Path,
    tenant_id: str,
    source_asset_id: str,
    base_memory_asset_id: str,
    memory_asset_id: str,
    model: str | None = None,
    batch_size: int = 8,
    max_additions_per_card: int = 3,
    provider: MemoryCardProvider | None = None,
) -> dict[str, Any]:
    """Mine every approved inferred training trace and append bounded additions."""
    tenant_id = _safe_name(tenant_id, "tenant_id")
    source_asset_id = _safe_name(source_asset_id, "source_asset_id")
    base_memory_asset_id = _safe_name(base_memory_asset_id, "base_memory_asset_id")
    memory_asset_id = _safe_name(memory_asset_id, "memory_asset_id")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if max_additions_per_card < 1:
        raise ValueError("max_additions_per_card must be positive")

    tenants_root = tenants_root.resolve()
    tenant_root = tenants_root / tenant_id
    source_root = tenant_root / "evaluation_assets" / source_asset_id
    base_root = tenant_root / "memory_assets" / base_memory_asset_id
    output_root = tenant_root / "memory_assets" / memory_asset_id
    if output_root.exists():
        raise FileExistsError(f"memory asset already exists: {output_root}")

    state_path = source_root / "pipeline_state.json"
    source_manifest_path = source_root / "asset_manifest.json"
    config_path = source_root / "config.json"
    guidelines_path = (
        source_root / "stages" / "03_evaluation_guidelines" / "evaluation_guidelines.jsonl"
    )
    train_inferred_path = (
        source_root / "stages" / "08_dataset_splits" / "train_inferred.jsonl"
    )
    unlabeled_path = source_root / "stages" / "01_raw_inputs" / "unlabeled.jsonl"
    base_manifest_path = base_root / "manifest.json"
    base_cards_path = base_root / "memory_cards.jsonl"

    if _load_json(state_path).get("status") != "released":
        raise ValueError("source evaluation asset must be released")
    _load_json(source_manifest_path)
    source_config = _load_json(config_path)
    base_manifest = _load_json(base_manifest_path)
    if base_manifest.get("source_evaluation_asset_id") != source_asset_id:
        raise ValueError("base memory asset does not match the source evaluation asset")
    guidelines = _load_jsonl(guidelines_path)
    base_cards = _load_jsonl(base_cards_path)
    inferred_cases = _load_jsonl(train_inferred_path)
    unlabeled_rows = _load_jsonl(unlabeled_path)
    if not guidelines or not inferred_cases:
        raise ValueError("source asset must contain guidelines and inferred training cases")

    guidelines_by_id = {
        _nonempty_string(row.get("guideline_id"), "guideline_id"): row
        for row in guidelines
    }
    cards_by_guideline = {
        _nonempty_string(row.get("source_guideline_id"), "source_guideline_id"): row
        for row in base_cards
    }
    if len(guidelines_by_id) != len(guidelines):
        raise ValueError("evaluation guideline IDs must be unique")
    if len(cards_by_guideline) != len(base_cards):
        raise ValueError("base memory source guideline IDs must be unique")
    if set(cards_by_guideline) != set(guidelines_by_id):
        raise ValueError("base memory cards do not cover exactly the source guidelines")
    raw_rows_by_id = {
        _nonempty_string(
            row.get("record_id") or row.get("request_id"),
            "unlabeled.record_id",
        ): row
        for row in unlabeled_rows
    }
    if len(raw_rows_by_id) != len(unlabeled_rows):
        raise ValueError("unlabeled record IDs must be unique")
    _validate_inferred_cases(
        inferred_cases,
        guideline_ids=set(guidelines_by_id),
        raw_rows_by_id=raw_rows_by_id,
    )

    criterion_ids_by_guideline = {
        guideline_id: {
            _nonempty_string(criterion.get("criterion_id"), "criterion_id")
            for criterion in guideline.get("criteria") or []
            if isinstance(criterion, Mapping)
        }
        for guideline_id, guideline in guidelines_by_id.items()
    }
    if any(not ids for ids in criterion_ids_by_guideline.values()):
        raise ValueError("every guideline must contain criteria")

    selected_model = model or str(
        source_config.get("rubric_model") or DEFAULT_OPENAI_RUBRIC_MODEL
    )
    active_provider = provider or OpenAIRubricProvider(model=selected_model)
    if model is not None and active_provider.model != model:
        raise ValueError("injected provider model does not match requested model")

    alias_by_case_id, trace_rows = _trace_index(inferred_cases)
    trace_guidelines = {
        row["trace_id"]: set(row["applicable_guideline_ids"]) for row in trace_rows
    }
    trace_clusters = {row["trace_id"]: row["source_cluster"] for row in trace_rows}
    source_record_by_trace = {
        row["trace_id"]: row["source_record_id"] for row in trace_rows
    }
    mining_catalog = [
        _guideline_for_mining(guidelines_by_id[guideline_id], cards_by_guideline[guideline_id])
        for guideline_id in sorted(guidelines_by_id)
    ]

    call_rows: list[dict[str, Any]] = []
    call_counter = [0]
    raw_patterns: list[dict[str, Any]] = []
    ordered_cases = _cluster_interleaved(inferred_cases)
    batch_count = 0
    for offset in range(0, len(ordered_cases), batch_size):
        batch_count += 1
        batch = ordered_cases[offset : offset + batch_size]
        episodes = [
            _episode_for_mining(
                case,
                alias=alias_by_case_id[str(case["case_id"])],
                raw_rows_by_id=raw_rows_by_id,
            )
            for case in batch
        ]
        batch_aliases = {str(row["trace_id"]) for row in episodes}
        batch_trace_guidelines = {
            trace_id: trace_guidelines[trace_id] for trace_id in batch_aliases
        }
        patterns = _generate_validated(
            provider=active_provider,
            prompt=EVIDENCE_MINING_PROMPT,
            payload={
                "mode": "runtime_memory_evidence_mining",
                "batch_id": f"batch-{batch_count:04d}",
                "trusted_guidelines_and_memory_spines": mining_catalog,
                "episodes": episodes,
            },
            validator=lambda response, bindings=batch_trace_guidelines: _normalize_patterns(
                response,
                batch_trace_guidelines=bindings,
                criterion_ids_by_guideline=criterion_ids_by_guideline,
            ),
            phase="evidence_mining",
            identifier=f"batch-{batch_count:04d}",
            call_rows=call_rows,
            call_counter=call_counter,
        )
        for pattern in patterns:
            raw_patterns.append({**pattern, "source_batch_id": f"batch-{batch_count:04d}"})

    patterns = _consolidate_exact_patterns(
        raw_patterns,
        trace_clusters=trace_clusters,
    )
    patterns_by_guideline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pattern in patterns:
        patterns_by_guideline[str(pattern["guideline_id"])].append(pattern)

    cards: list[dict[str, Any]] = []
    addition_rows: list[dict[str, Any]] = []
    for guideline_id in sorted(guidelines_by_id):
        guideline_patterns = patterns_by_guideline.get(guideline_id, [])
        patterns_by_id = {str(item["pattern_id"]): item for item in guideline_patterns}
        if guideline_patterns:
            additions = _generate_validated(
                provider=active_provider,
                prompt=ADDITIVE_CONSOLIDATION_PROMPT,
                payload={
                    "mode": "runtime_memory_additive_consolidation",
                    "max_additions": max_additions_per_card,
                    "trusted_guideline": guidelines_by_id[guideline_id],
                    "trusted_memory_spine": _trusted_body(cards_by_guideline[guideline_id]),
                    "candidate_patterns": guideline_patterns,
                },
                validator=lambda response, source=patterns_by_id, criteria=(
                    criterion_ids_by_guideline[guideline_id]
                ): _normalize_additions(
                    response,
                    patterns_by_id=source,
                    criterion_ids=criteria,
                    max_additions=max_additions_per_card,
                ),
                phase="additive_consolidation",
                identifier=guideline_id,
                call_rows=call_rows,
                call_counter=call_counter,
            )
        else:
            additions = []
        body, restored_additions = _append_additions(
            cards_by_guideline[guideline_id],
            additions,
            source_record_by_trace=source_record_by_trace,
        )
        selected_pattern_ids = sorted(
            {
                pattern_id
                for addition in additions
                for pattern_id in addition["source_pattern_ids"]
            }
        )
        selected_trace_ids = sorted(
            {
                trace_id
                for addition in additions
                for trace_id in addition["source_trace_ids"]
            }
        )
        base_card = cards_by_guideline[guideline_id]
        card = {
            "schema_version": MEMORY_CARD_SCHEMA_VERSION,
            "memory_id": _memory_id(guideline_id, body),
            "source_guideline_id": guideline_id,
            "route": base_card.get("route") or "default",
            **body,
            "injection_text": _render_memory(body),
            "confidence": float(base_card.get("confidence") or 0.5),
            "trust_tier": "trusted_memory_with_approved_inferred_addendum",
            "source_record_ids": deepcopy(base_card.get("source_record_ids") or []),
            "selected_source_record_ids": sorted(
                set(base_card.get("selected_source_record_ids") or [])
                | {source_record_by_trace[trace_id] for trace_id in selected_trace_ids}
            ),
            "base_memory_asset_id": base_memory_asset_id,
            "base_memory_id": base_card.get("memory_id"),
            "trusted_spine_sha256": _sha256_value(_trusted_body(base_card)),
            "trusted_spine_preserved": True,
            "inferred_candidate_count": sum(
                guideline_id in set(case["metadata"]["applicable_guideline_ids"])
                for case in inferred_cases
            ),
            "mined_pattern_count": len(guideline_patterns),
            "addition_count": len(restored_additions),
            "selected_pattern_ids": selected_pattern_ids,
            "selected_inferred_record_ids": [
                source_record_by_trace[trace_id] for trace_id in selected_trace_ids
            ],
            "additions": restored_additions,
            "provider": active_provider.provider_name,
            "model": active_provider.model,
            "prompt_revision": ADDITIVE_MEMORY_REVISION,
        }
        cards.append(card)
        addition_rows.append(
            {
                "source_guideline_id": guideline_id,
                "base_memory_id": base_card.get("memory_id"),
                "trusted_spine_sha256": card["trusted_spine_sha256"],
                "candidate_pattern_count": len(guideline_patterns),
                "additions": restored_additions,
            }
        )

    output_root.mkdir(parents=True, exist_ok=False)
    cards_path = output_root / "memory_cards.jsonl"
    patterns_path = output_root / "evidence_patterns.jsonl"
    additions_path = output_root / "card_additions.jsonl"
    trace_index_path = output_root / "trace_index.jsonl"
    calls_path = output_root / "provider_calls.jsonl"
    atomic_write_jsonl(cards_path, cards)
    atomic_write_jsonl(patterns_path, patterns)
    atomic_write_jsonl(additions_path, addition_rows)
    atomic_write_jsonl(trace_index_path, trace_rows)
    atomic_write_jsonl(calls_path, call_rows)
    manifest = {
        "schema_version": MEMORY_ASSET_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "memory_asset_id": memory_asset_id,
        "source_evaluation_asset_id": source_asset_id,
        "base_memory_asset_id": base_memory_asset_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "card_count": len(cards),
        "provider": active_provider.provider_name,
        "model": active_provider.model,
        "evidence_mode": "trusted_plus_approved_inferred",
        "include_approved_inferred": True,
        "construction_mode": "trusted_spine_with_batched_inferred_addendum",
        "inferred_candidate_pool": len(inferred_cases),
        "inferred_cases_processed": len(ordered_cases),
        "batch_size": batch_size,
        "batch_count": batch_count,
        "raw_pattern_count": len(raw_patterns),
        "consolidated_pattern_count": len(patterns),
        "addition_count": sum(len(row["additions"]) for row in addition_rows),
        "max_additions_per_card": max_additions_per_card,
        "prompt_revisions": {
            "evidence_mining": EVIDENCE_MINING_REVISION,
            "additive_consolidation": ADDITIVE_MEMORY_REVISION,
        },
        "prompt_sha256": {
            "evidence_mining": _sha256_value(EVIDENCE_MINING_PROMPT),
            "additive_consolidation": _sha256_value(ADDITIVE_CONSOLIDATION_PROMPT),
        },
        "source_artifacts": {
            "asset_manifest.json": _file_sha256(source_manifest_path),
            "config.json": _file_sha256(config_path),
            "evaluation_guidelines.jsonl": _file_sha256(guidelines_path),
            "train_inferred.jsonl": _file_sha256(train_inferred_path),
            "unlabeled.jsonl": _file_sha256(unlabeled_path),
            "base_manifest.json": _file_sha256(base_manifest_path),
            "base_memory_cards.jsonl": _file_sha256(base_cards_path),
        },
        "artifacts": {
            "memory_cards.jsonl": _file_sha256(cards_path),
            "evidence_patterns.jsonl": _file_sha256(patterns_path),
            "card_additions.jsonl": _file_sha256(additions_path),
            "trace_index.jsonl": _file_sha256(trace_index_path),
            "provider_calls.jsonl": _file_sha256(calls_path),
        },
    }
    atomic_write_json(output_root / "manifest.json", manifest)
    return {**manifest, "output_path": str(output_root)}


__all__ = [
    "ADDITIVE_CONSOLIDATION_PROMPT",
    "ADDITIVE_MEMORY_REVISION",
    "EVIDENCE_MINING_PROMPT",
    "EVIDENCE_MINING_REVISION",
    "build_additive_memory_asset",
]
