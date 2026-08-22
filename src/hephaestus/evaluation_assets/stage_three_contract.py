# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Pure producer and replay contracts for evaluation-asset Stage 3."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Literal, Mapping, Sequence

from src.hephaestus.datasets.evaluation_assets import validate_fapo_case
from src.hephaestus.evaluation_assets.input_contract import effective_route
from src.hephaestus.evaluation_assets.trust_tiers import TRUSTED_FEEDBACK

CRITERION_KINDS = frozenset({"required", "prohibited", "preferred"})
CRITERION_SEVERITIES = frozenset({"critical", "major", "minor"})
EVALUATOR_TYPES = frozenset(
    {
        "state_check",
        "deterministic_check",
        "semantic_trajectory",
        "llm_judge",
        "human_review",
    }
)
GuidelineIdentityProfile = Literal["current_v2", "historical_v1"]
TrustedIntentTextProfile = Literal["current", "historical_v1"]
_CURRENT_GUIDELINE_IDENTITY_REVISION = "fapo-guideline-identity-v2"
_CURRENT_CRITERION_IDENTITY_REVISION = "fapo-criterion-identity-v2"

_EVIDENCE_FIELDS = {
    "record_id",
    "group_id",
    "route",
    "task_type",
    "intent_label",
    "confidence",
    "observations",
    "requested_corrections",
    "uncertainties",
    "evidence_source",
    "guideline_provider",
    "guideline_model",
}
_OBSERVATION_FIELDS = {
    "claim",
    "evidence_type",
    "evidence_pointer",
    "polarity",
}
_CANDIDATE_FIELDS = {
    "intent_label",
    "description",
    "route",
    "source_record_ids",
    "confidence",
    "criteria",
    "tool_expectations",
    "reference_output",
    "conflicts",
    "uncertainties",
}
_CANDIDATE_CRITERION_FIELDS = {
    "kind",
    "statement",
    "source_record_ids",
    "dimension",
    "severity",
    "applicability",
    "scoring",
    "evidence_required",
    "evaluator",
}
_GUIDELINE_FIELDS = {
    "guideline_id",
    "route",
    "intent_label",
    "description",
    "confidence",
    "source_record_ids",
    "support",
    "criteria",
    "conflicts",
    "uncertainties",
    "tool_expectations",
    "reference_output",
    "unknown_policy",
    "activation_status",
    "calibration_status",
    "guideline_provider",
    "guideline_model",
    "oracle_version",
}
_GUIDELINE_CRITERION_FIELDS = {
    "criterion_id",
    *_CANDIDATE_CRITERION_FIELDS,
    "order",
}
_LEGACY_RUBRIC_FIELDS = {
    "record_id",
    "intent_label",
    "confidence",
    "must",
    "must_not",
    "should",
    "deterministic_checks",
    "tool_expectations",
    "reference_output",
    "label_source",
    "rubric_provider",
    "rubric_model",
    "oracle_version",
}


def normalize_guideline_response(
    response: Mapping[str, Any],
    *,
    route: str,
    evidence: Sequence[Mapping[str, Any]],
    rubric_provider: str,
    rubric_model: str,
    identity_profile: GuidelineIdentityProfile = "current_v2",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate and canonicalize provider candidates before persistence."""
    items = response.get("guidelines")
    if not isinstance(items, list) or not items:
        raise ValueError("Guideline response missing guidelines array")
    evidence_by_id = {str(item["record_id"]): item for item in evidence}
    candidates = [
        normalize_guideline_candidate(item, route, evidence_by_id)
        for item in items
        if isinstance(item, Mapping)
    ]
    if len(candidates) != len(items):
        raise ValueError("Guideline response contains an invalid candidate")
    return (
        candidates,
        compile_evaluation_guidelines(
            candidates,
            evidence,
            rubric_provider,
            rubric_model,
            identity_profile=identity_profile,
        ),
    )


def normalize_guideline_candidate(
    raw: Mapping[str, Any],
    route: str,
    evidence_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the exact persisted candidate-v1 shape or reject the row."""
    intent_label = _nonempty_string(raw.get("intent_label"))
    description = _nonempty_string(raw.get("description"))
    confidence = _number(raw.get("confidence"), minimum=0.0, maximum=1.0)
    source_ids = sorted(set(_string_list(raw.get("source_record_ids"), nonempty=True)))
    if any(
        record_id not in evidence_by_id
        or str(evidence_by_id[record_id].get("route")) != route
        for record_id in source_ids
    ):
        raise ValueError("candidate guideline references incompatible evidence")
    conflicts = _string_list(raw.get("conflicts", []))
    uncertainties = _string_list(raw.get("uncertainties", []))
    tool_expectations = raw.get("tool_expectations")
    if not isinstance(tool_expectations, Mapping):
        raise ValueError("candidate tool expectations must be an object")
    reference_output = raw.get("reference_output")
    if reference_output is not None and not isinstance(reference_output, str):
        raise ValueError("candidate reference output is invalid")
    criteria = normalize_guideline_criteria(
        raw.get("criteria"),
        route,
        source_ids,
    )
    if not criteria:
        raise ValueError("candidate guideline criteria are missing")
    candidate = {
        "intent_label": intent_label,
        "description": description,
        "route": route,
        "source_record_ids": source_ids,
        "confidence": confidence,
        "criteria": [
            {field: criterion[field] for field in _CANDIDATE_CRITERION_FIELDS}
            for criterion in criteria
        ],
        "tool_expectations": dict(tool_expectations),
        "reference_output": reference_output,
        "conflicts": conflicts,
        "uncertainties": uncertainties,
    }
    _validate_json_numbers(candidate)
    return candidate


def normalize_guideline_criteria(
    value: Any,
    route: str,
    guideline_source_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Compile strict candidate criteria into their canonical guideline shape."""
    if not isinstance(value, list) or not value:
        raise ValueError("candidate guideline criteria are missing")
    criteria: list[dict[str, Any]] = []
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            raise ValueError("candidate guideline criterion is invalid")
        kind = _enum(raw.get("kind"), CRITERION_KINDS, "criterion kind")
        statement = _nonempty_string(raw.get("statement"))
        dimension = _nonempty_string(raw.get("dimension"))
        severity = _enum(
            raw.get("severity"),
            CRITERION_SEVERITIES,
            "criterion severity",
        )
        applicability = raw.get("applicability")
        if isinstance(applicability, str):
            applicability = _nonempty_string(applicability)
        elif isinstance(applicability, Mapping):
            applicability = dict(applicability)
        else:
            raise ValueError("criterion applicability is invalid")
        scoring = _nonempty_string(raw.get("scoring"))
        evidence_required = raw.get("evidence_required")
        if not isinstance(evidence_required, bool):
            raise ValueError("criterion evidence requirement is invalid")
        evaluator = raw.get("evaluator")
        if not isinstance(evaluator, Mapping) or set(evaluator) != {
            "type",
            "fallback",
        }:
            raise ValueError("criterion evaluator is invalid")
        evaluator_type = _enum(
            evaluator.get("type"), EVALUATOR_TYPES, "criterion evaluator"
        )
        fallback = _enum(
            evaluator.get("fallback"), EVALUATOR_TYPES, "criterion fallback"
        )
        criterion_sources = sorted(
            set(
                _string_list(
                    raw.get("source_record_ids", list(guideline_source_ids)),
                    nonempty=True,
                )
            )
        )
        if not set(criterion_sources) <= set(guideline_source_ids):
            raise ValueError("criterion source evidence is inconsistent")
        digest = hashlib.sha256(
            f"{route}:{kind}:{statement}".encode("utf-8")
        ).hexdigest()[:10]
        criterion = {
            "criterion_id": f"criterion-{digest}",
            "kind": kind,
            "statement": statement,
            "source_record_ids": criterion_sources,
            "dimension": dimension,
            "severity": severity,
            "applicability": applicability,
            "scoring": scoring,
            "evidence_required": evidence_required,
            "evaluator": {"type": evaluator_type, "fallback": fallback},
            "order": index,
        }
        _validate_json_numbers(criterion)
        criteria.append(criterion)
    return criteria


def _guideline_identity_profile(value: str) -> GuidelineIdentityProfile:
    if value == "current_v2":
        return "current_v2"
    if value == "historical_v1":
        return "historical_v1"
    raise ValueError(f"Unsupported guideline identity profile {value!r}")


def _guideline_id(
    *,
    route: str,
    guideline_payload: Mapping[str, Any],
    identity_profile: GuidelineIdentityProfile,
) -> str:
    if identity_profile == "historical_v1":
        identity = json.dumps(
            {
                "route": route,
                "intent_label": guideline_payload["intent_label"],
                "criteria": [
                    item["statement"] for item in guideline_payload["criteria"]
                ],
            },
            sort_keys=True,
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    else:
        digest = _canonical_identity_digest(
            {
                "revision": _CURRENT_GUIDELINE_IDENTITY_REVISION,
                "guideline": guideline_payload,
            }
        )
    return f"guideline-{_slug(route)}-{digest}"


def _current_criterion_id(
    guideline_id: str,
    criterion_payload: Mapping[str, Any],
) -> str:
    digest = _canonical_identity_digest(
        {
            "revision": _CURRENT_CRITERION_IDENTITY_REVISION,
            "guideline_id": guideline_id,
            "criterion": criterion_payload,
        }
    )
    return f"criterion-{digest}"


def _canonical_identity_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compile_evaluation_guidelines(
    candidates: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    rubric_provider: str,
    rubric_model: str,
    *,
    identity_profile: GuidelineIdentityProfile = "current_v2",
) -> list[dict[str, Any]]:
    """Compile canonical candidates into exact versioned guideline rows."""
    identity_profile = _guideline_identity_profile(identity_profile)
    evidence_by_id = {str(item["record_id"]): item for item in evidence}
    represented: set[str] = set()
    provisional: list[dict[str, Any]] = []
    for raw in candidates:
        route = effective_route(raw)
        canonical = normalize_guideline_candidate(raw, route, evidence_by_id)
        source_ids = canonical["source_record_ids"]
        represented.update(source_ids)
        criteria = normalize_guideline_criteria(
            canonical["criteria"], route, source_ids
        )
        groups = {
            str(evidence_by_id[record_id].get("group_id") or record_id)
            for record_id in source_ids
        }
        corrections = {
            correction
            for record_id in source_ids
            for correction in evidence_by_id[record_id]["requested_corrections"]
        }
        criterion_payloads = [
            {
                field: value
                for field, value in criterion.items()
                if field != "criterion_id"
            }
            for criterion in criteria
        ]
        guideline_payload = {
            "route": route,
            "intent_label": canonical["intent_label"],
            "description": canonical["description"],
            "confidence": canonical["confidence"],
            "source_record_ids": source_ids,
            "support": {
                "trusted_example_count": len(source_ids),
                "trusted_group_count": len(groups),
            },
            "criteria": criterion_payloads,
            "conflicts": canonical["conflicts"],
            "uncertainties": sorted(
                {
                    *(
                        uncertainty
                        for record_id in source_ids
                        for uncertainty in evidence_by_id[record_id]["uncertainties"]
                    ),
                    *canonical["uncertainties"],
                }
            ),
            "tool_expectations": canonical["tool_expectations"],
            "reference_output": (
                next(iter(corrections)) if len(corrections) == 1 else None
            ),
            "unknown_policy": "needs_review",
            "activation_status": "active_from_trusted_evidence",
            "calibration_status": "uncalibrated",
            "guideline_provider": rubric_provider,
            "guideline_model": rubric_model,
            "oracle_version": "fapo-evaluation-guideline-v1",
        }
        guideline_id = _guideline_id(
            route=route,
            guideline_payload=guideline_payload,
            identity_profile=identity_profile,
        )
        if identity_profile == "current_v2":
            compiled_criteria = [
                {
                    "criterion_id": _current_criterion_id(
                        guideline_id,
                        criterion,
                    ),
                    **criterion,
                }
                for criterion in criterion_payloads
            ]
        else:
            compiled_criteria = criteria
        provisional.append(
            {
                "guideline_id": guideline_id,
                **guideline_payload,
                "criteria": compiled_criteria,
            }
        )
    missing = sorted(set(evidence_by_id) - represented)
    if missing:
        raise ValueError("candidate guidelines omit trusted evidence")
    guidelines = sorted(provisional, key=lambda item: str(item["guideline_id"]))
    validate_stage_three_identities(
        candidates=candidates,
        guidelines=guidelines,
    )
    return guidelines


def replay_native_stage_three(
    normalized: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    *,
    asset_id: str,
    identity_profile: GuidelineIdentityProfile,
    text_profile: TrustedIntentTextProfile,
) -> dict[str, list[dict[str, Any]]]:
    """Reconstruct every deterministic native Stage 3 derivative."""
    if (identity_profile, text_profile) not in {
        ("current_v2", "current"),
        ("historical_v1", "historical_v1"),
    }:
        raise ValueError("Stage 3 replay profiles are incompatible")
    normalized_by_id = _unique_by(normalized, "record_id")
    evidence_by_id = _unique_by(evidence, "record_id")
    if set(normalized_by_id) != set(evidence_by_id):
        raise ValueError("feedback evidence coverage is incomplete")
    provider_pairs: set[tuple[str, str]] = set()
    for record_id, row in evidence_by_id.items():
        if set(row) != _EVIDENCE_FIELDS:
            raise ValueError("feedback evidence schema is invalid")
        source = normalized_by_id[record_id]
        if (
            row.get("group_id") != source.get("group_id")
            or row.get("route") != effective_route(source)
            or row.get("task_type") != source.get("task_type")
            or row.get("evidence_source") != "trusted_feedback"
        ):
            raise ValueError("feedback evidence provenance is invalid")
        _nonempty_string(row.get("intent_label"))
        _number(row.get("confidence"), minimum=0.0, maximum=1.0)
        observations = row.get("observations")
        if not isinstance(observations, list):
            raise ValueError("feedback observations are invalid")
        for observation in observations:
            if not isinstance(observation, Mapping) or set(observation) != (
                _OBSERVATION_FIELDS
            ):
                raise ValueError("feedback observation schema is invalid")
            for value in observation.values():
                _nonempty_string(value)
        _string_list(row.get("requested_corrections"))
        _string_list(row.get("uncertainties"))
        provider_pairs.add(
            (
                _nonempty_string(row.get("guideline_provider")),
                _nonempty_string(row.get("guideline_model")),
            )
        )
    if len(provider_pairs) != 1:
        raise ValueError("feedback evidence provider identity is inconsistent")
    rubric_provider, rubric_model = next(iter(provider_pairs))
    evidence_by_route: dict[str, list[Mapping[str, Any]]] = {}
    for row in evidence:
        evidence_by_route.setdefault(str(row["route"]), []).append(row)
    canonical_candidates: list[dict[str, Any]] = []
    guidelines: list[dict[str, Any]] = []
    for route in sorted(evidence_by_route):
        route_evidence = sorted(
            evidence_by_route[route], key=lambda item: str(item["record_id"])
        )
        route_candidates = [row for row in candidates if row.get("route") == route]
        canonical_route = [
            normalize_guideline_candidate(row, route, evidence_by_id)
            for row in route_candidates
        ]
        if canonical_route != list(route_candidates):
            raise ValueError("candidate guideline schema is not canonical")
        canonical_candidates.extend(canonical_route)
        guidelines.extend(
            compile_evaluation_guidelines(
                canonical_route,
                route_evidence,
                rubric_provider,
                rubric_model,
                identity_profile=identity_profile,
            )
        )
    if len(canonical_candidates) != len(candidates):
        raise ValueError("candidate guideline route is unsupported")
    guidelines.sort(key=lambda item: str(item["guideline_id"]))
    grouped = guidelines_by_source_record(guidelines)
    trusted_intents = [
        trusted_intent_from_guideline(
            row,
            normalized_by_id,
            text_profile=text_profile,
        )
        for row in guidelines
    ]
    trusted_cases = [
        trusted_case(
            row,
            rubric_from_guidelines(
                str(row["record_id"]),
                grouped[str(row["record_id"])],
                rubric_provider,
                rubric_model,
            ),
            asset_id,
        )
        for row in normalized
    ]
    validate_stage_three_identities(
        candidates=canonical_candidates,
        guidelines=guidelines,
        trusted_intents=trusted_intents,
        trusted_cases=trusted_cases,
    )
    return {
        "candidates": canonical_candidates,
        "guidelines": guidelines,
        "trusted_intents": trusted_intents,
        "trusted_cases": trusted_cases,
    }


def replay_legacy_stage_three(
    normalized: Sequence[Mapping[str, Any]],
    rubrics: Sequence[Mapping[str, Any]],
    *,
    asset_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Reconstruct the only supported pre-guideline writer contract."""
    normalized_by_id = _unique_by(normalized, "record_id")
    rubric_by_id = _unique_by(rubrics, "record_id")
    if set(normalized_by_id) != set(rubric_by_id):
        raise ValueError("legacy rubrics do not exactly cover feedback")
    for row in rubrics:
        if set(row) != _LEGACY_RUBRIC_FIELDS:
            raise ValueError("legacy rubric schema is invalid")
        _nonempty_string(row.get("intent_label"))
        _number(row.get("confidence"), minimum=0.0, maximum=1.0)
        scoreable = False
        for field in ("must", "must_not", "should"):
            scoreable = bool(_string_list(row.get(field))) or scoreable
        checks = row.get("deterministic_checks")
        if not isinstance(checks, list) or any(
            not isinstance(check, Mapping) or not check for check in checks
        ):
            raise ValueError("legacy deterministic checks are invalid")
        tool_expectations = row.get("tool_expectations")
        if not isinstance(tool_expectations, Mapping):
            raise ValueError("legacy tool expectations are invalid")
        reference = row.get("reference_output")
        if reference is not None and not isinstance(reference, str):
            raise ValueError("legacy reference output is invalid")
        if not scoreable and not checks and not tool_expectations and not reference:
            raise ValueError("legacy rubric has no scoreable expected value")
        if row.get("label_source") != "human_feedback" or row.get(
            "oracle_version"
        ) != "fapo-evaluation-asset-v1":
            raise ValueError("legacy rubric provenance is invalid")
        _nonempty_string(row.get("rubric_provider"))
        _nonempty_string(row.get("rubric_model"))
    trusted_intents = [
        {
            "intent_id": str(row["record_id"]),
            "label": rubric_by_id[str(row["record_id"])]["intent_label"],
            "texts": [
                row["user_input"],
                " ".join(
                    [
                        *rubric_by_id[str(row["record_id"])]["must"],
                        *rubric_by_id[str(row["record_id"])]["must_not"],
                    ]
                ),
            ],
            "route": row["route"],
            "metadata": {
                "trusted_example_count": 1,
                "trusted_group_count": 1,
                "feedback_polarity": row["feedback"]["polarity"],
            },
        }
        for row in normalized
    ]
    trusted_cases = [
        trusted_case(row, rubric_by_id[str(row["record_id"])], asset_id)
        for row in normalized
    ]
    validate_stage_three_identities(
        trusted_intents=trusted_intents,
        trusted_cases=trusted_cases,
    )
    return {"trusted_intents": trusted_intents, "trusted_cases": trusted_cases}


def guidelines_by_source_record(
    guidelines: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for guideline in guidelines:
        for record_id in guideline["source_record_ids"]:
            grouped.setdefault(str(record_id), []).append(guideline)
    return grouped


def rubric_from_guidelines(
    record_id: str,
    guidelines: Sequence[Mapping[str, Any]],
    rubric_provider: str,
    rubric_model: str,
) -> dict[str, Any]:
    criteria = [
        criterion for guideline in guidelines for criterion in guideline["criteria"]
    ]
    deterministic_checks = [
        {
            "criterion_id": criterion["criterion_id"],
            "statement": criterion["statement"],
            "applicability": criterion["applicability"],
            "evaluator": criterion["evaluator"],
        }
        for criterion in criteria
        if criterion["evaluator"]["type"]
        in {"state_check", "deterministic_check"}
    ]
    semantic_trajectory = [
        criterion["statement"]
        for criterion in criteria
        if criterion["evaluator"]["type"] == "semantic_trajectory"
    ]
    tool_expectations: dict[str, Any] = {
        "guidelines": [
            dict(guideline["tool_expectations"])
            for guideline in guidelines
            if guideline["tool_expectations"]
        ]
    }
    if semantic_trajectory:
        tool_expectations["semantic_trajectory"] = semantic_trajectory
    references = {
        str(guideline["reference_output"])
        for guideline in guidelines
        if guideline.get("reference_output")
    }
    return {
        "record_id": record_id,
        "intent_label": " / ".join(
            sorted({str(guideline["intent_label"]) for guideline in guidelines})
        ),
        "confidence": min(float(guideline["confidence"]) for guideline in guidelines),
        "must": [
            criterion["statement"]
            for criterion in criteria
            if criterion["kind"] == "required"
        ],
        "must_not": [
            criterion["statement"]
            for criterion in criteria
            if criterion["kind"] == "prohibited"
        ],
        "should": [
            criterion["statement"]
            for criterion in criteria
            if criterion["kind"] == "preferred"
        ],
        "deterministic_checks": deterministic_checks,
        "tool_expectations": tool_expectations,
        "reference_output": next(iter(references)) if len(references) == 1 else None,
        "evaluation_guideline_ids": [
            str(guideline["guideline_id"]) for guideline in guidelines
        ],
        "evaluation_guidelines": [dict(guideline) for guideline in guidelines],
        "label_source": "evaluation_guideline_from_trusted_feedback",
        "rubric_provider": rubric_provider,
        "rubric_model": rubric_model,
        "oracle_version": "fapo-evaluation-guideline-v1",
    }


def trusted_intent_from_guideline(
    guideline: Mapping[str, Any],
    normalized_by_id: Mapping[str, Mapping[str, Any]],
    *,
    text_profile: TrustedIntentTextProfile = "current",
) -> dict[str, Any]:
    source_ids = [str(value) for value in guideline["source_record_ids"]]
    groups = {str(normalized_by_id[value]["group_id"]) for value in source_ids}
    polarities = sorted(
        {str(normalized_by_id[value]["feedback"]["polarity"]) for value in source_ids}
    )
    if text_profile == "historical_v1":
        texts = [
            str(guideline["description"]),
            *(str(item["statement"]) for item in guideline["criteria"]),
            *(str(normalized_by_id[value]["user_input"]) for value in source_ids),
        ]
    elif text_profile == "current":
        texts = [
            _canonical_source_intent_text(normalized_by_id[value])
            for value in source_ids
        ]
    else:
        raise ValueError(f"Unsupported trusted-intent text profile {text_profile!r}")
    return {
        "intent_id": guideline["guideline_id"],
        "label": guideline["intent_label"],
        "texts": texts,
        "route": guideline["route"],
        "metadata": {
            "trusted_example_count": len(source_ids),
            "trusted_group_count": len(groups),
            "feedback_polarities": polarities,
            "evaluation_guideline_id": guideline["guideline_id"],
            "source_record_ids": source_ids,
        },
    }


def _canonical_source_intent_text(row: Mapping[str, Any]) -> str:
    user_input = str(row.get("user_input") or "").strip()
    context_text = ""
    context = row.get("conversation_context")
    if isinstance(context, list):
        for message in reversed(context):
            if isinstance(message, Mapping) and message.get("content"):
                context_text = str(message["content"]).strip()
                break

    tool_names: set[str] = set()
    tool_calls = row.get("tool_calls")
    if isinstance(tool_calls, list):
        for call in tool_calls:
            name: Any = None
            if isinstance(call, str):
                name = call
            elif isinstance(call, Mapping):
                name = call.get("name") or call.get("tool")
            if name:
                tool_names.add(str(name))
    tools_text = f"tools {' '.join(sorted(tool_names))}" if tool_names else ""
    return " ".join(
        part for part in (user_input, context_text, tools_text) if part
    )


def expected_from_rubric(rubric: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "label_source": rubric["label_source"],
        "confidence": rubric["confidence"],
        "rubric": {
            "must": list(rubric["must"]),
            "must_not": list(rubric["must_not"]),
            "should": list(rubric["should"]),
        },
        "deterministic_checks": list(rubric["deterministic_checks"]),
        "tool_expectations": dict(rubric["tool_expectations"]),
        "reference_output": rubric["reference_output"],
    }
    if rubric.get("evaluation_guideline_ids"):
        expected["evaluation_guideline_ids"] = list(
            rubric["evaluation_guideline_ids"]
        )
        expected["evaluation_guidelines"] = list(
            rubric.get("evaluation_guidelines") or []
        )
    return expected


def trusted_case(
    row: Mapping[str, Any],
    rubric: Mapping[str, Any],
    asset_id: str,
) -> dict[str, Any]:
    case = {
        "case_id": f"feedback-{row['record_id']}",
        "task_type": row["task_type"],
        "context": _context(row),
        "expected": {
            **expected_from_rubric(rubric),
            "feedback_polarity": row["feedback"]["polarity"],
        },
        "metadata": {
            "source": "feedback_trace",
            "dataset_version": asset_id,
            "group_id": row["group_id"],
            "request_id": row["request_id"],
            "trust_tier": TRUSTED_FEEDBACK,
        },
    }
    validate_fapo_case(case)
    return case


def validate_native_guideline_rows(rows: Sequence[Mapping[str, Any]]) -> None:
    """Validate exact compiled row schemas before replay comparison."""
    for row in rows:
        if set(row) != _GUIDELINE_FIELDS:
            raise ValueError("evaluation guideline schema is invalid")
        criteria = row.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            raise ValueError("evaluation guideline criteria are missing")
        for criterion in criteria:
            if not isinstance(criterion, Mapping) or set(criterion) != (
                _GUIDELINE_CRITERION_FIELDS
            ):
                raise ValueError("evaluation guideline criterion schema is invalid")


def validate_stage_three_identities(
    *,
    candidates: Sequence[Mapping[str, Any]] = (),
    guidelines: Sequence[Mapping[str, Any]] = (),
    trusted_intents: Sequence[Mapping[str, Any]] = (),
    trusted_cases: Sequence[Mapping[str, Any]] = (),
) -> None:
    """Reject every duplicate or colliding canonical Stage 3 identity."""
    candidate_payloads: set[str] = set()
    for candidate in candidates:
        payload = json.dumps(
            dict(candidate),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        if payload in candidate_payloads:
            raise ValueError("Stage 3 candidates are not unique")
        candidate_payloads.add(payload)

    guideline_by_id: dict[str, Mapping[str, Any]] = {}
    for guideline in guidelines:
        guideline_id = _nonempty_string(guideline.get("guideline_id"))
        previous = guideline_by_id.get(guideline_id)
        if previous is not None:
            previous_sources = sorted(
                str(value) for value in previous.get("source_record_ids", [])
            )
            colliding_sources = sorted(
                str(value) for value in guideline.get("source_record_ids", [])
            )
            raise ValueError(
                f"Duplicate compiled guideline_id {guideline_id!r}: "
                f"source_record_ids {previous_sources!r} collides with "
                f"source_record_ids {colliding_sources!r}"
            )
        guideline_by_id[guideline_id] = guideline
    criterion_ids: set[str] = set()
    for guideline in guidelines:
        criteria = guideline.get("criteria")
        if not isinstance(criteria, list):
            raise ValueError("evaluation guideline criteria are invalid")
        for criterion in criteria:
            if not isinstance(criterion, Mapping):
                raise ValueError("evaluation guideline criterion is invalid")
            criterion_id = _nonempty_string(criterion.get("criterion_id"))
            if criterion_id in criterion_ids:
                raise ValueError("Stage 3 criterion identities are not unique")
            criterion_ids.add(criterion_id)
    _unique_by(trusted_intents, "intent_id")
    _unique_by(trusted_cases, "case_id")


def _context(row: Mapping[str, Any]) -> dict[str, str]:
    messages = [*row["conversation_context"], {"role": "user", "content": row["user_input"]}]
    return {
        "messages_json": json.dumps(messages, sort_keys=True),
        "tool_context_json": json.dumps(row["tool_calls"], sort_keys=True),
        "runtime_json": json.dumps(row["runtime"], sort_keys=True),
    }


def _unique_by(
    rows: Sequence[Mapping[str, Any]],
    field: str,
) -> dict[str, Mapping[str, Any]]:
    output: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _nonempty_string(row.get(field))
        if value in output:
            raise ValueError("Stage 3 identities are not unique")
        output[value] = row
    return output


def _nonempty_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Stage 3 string is invalid")
    return value


def _string_list(value: Any, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError("Stage 3 string array is invalid")
    if nonempty and not value:
        raise ValueError("Stage 3 string array is empty")
    return list(value)


def _number(
    value: Any,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Stage 3 number is invalid")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError("Stage 3 number is invalid")
    return number


def _enum(value: Any, allowed: frozenset[str], label: str) -> str:
    text = _nonempty_string(value)
    if text not in allowed:
        raise ValueError(f"{label} is unsupported")
    return text


def _validate_json_numbers(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Stage 3 contains a non-finite number")
    if isinstance(value, Mapping):
        for nested in value.values():
            _validate_json_numbers(nested)
    elif isinstance(value, list):
        for nested in value:
            _validate_json_numbers(nested)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "general"
