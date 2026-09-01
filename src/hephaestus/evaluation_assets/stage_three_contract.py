# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Pure producer and replay contracts for evaluation-asset Stage 3."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Optional, Sequence

from src.hephaestus.datasets.evaluation_assets import validate_fapo_case
from src.hephaestus.evaluation_assets.input_contract import (
    canonical_user_intent_text,
    effective_route,
)
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
    return canonical_user_intent_text(row)


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


APPLICABILITY_CONTRACT_SCHEMA_VERSION = "fapo-applicability-contract-v1"
_APPLICABILITY_STATUSES = frozenset(
    {"applicable", "not_applicable", "unknown"}
)


@dataclass(frozen=True)
class EpisodeFacts:
    """Structured, evidence-linked facts extracted from one observable episode."""

    tags: frozenset[str]
    known_dimensions: frozenset[str]
    evidence_by_tag: Mapping[str, tuple[str, ...]]

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""
        return {
            "tags": sorted(self.tags),
            "known_dimensions": sorted(self.known_dimensions),
            "evidence_by_tag": {
                tag: list(self.evidence_by_tag[tag])
                for tag in sorted(self.evidence_by_tag)
            },
        }


@dataclass(frozen=True)
class ApplicabilityContractDecision:
    """Tri-state result from deterministic applicability evaluation."""

    status: str
    reason: str
    evidence_pointers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in _APPLICABILITY_STATUSES:
            raise ValueError(f"Invalid applicability status: {self.status!r}")


_USER_FACT_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "action",
        "action:reverse_cancellation",
        re.compile(
            r"\b(?:undo|reverse|revert|reinstate|restore|reactivate)\b.{0,50}"
            r"\b(?:cancel|cancellation|cancelled|canceled)\b|"
            r"\b(?:cancel|cancellation|cancelled|canceled)\b.{0,50}"
            r"\b(?:undo|reverse|revert|reinstate|restore|reactivate)\b",
            re.I,
        ),
    ),
    (
        "action",
        "action:cancel",
        re.compile(r"\b(?:cancel|cancellation|cancelled|canceled)\b", re.I),
    ),
    (
        "action",
        "action:return",
        re.compile(r"\b(?:return|returns|returning|returned)\b", re.I),
    ),
    (
        "action",
        "action:exchange",
        re.compile(
            r"\b(?:exchange|exchanges|exchanging|exchage|exchages|exchaging)\b|"
            r"\b(?:swap|swapping)(?:\s+out)?\b.{0,60}"
            r"\b(?:items?|products?|size|color|colour|variant|model|version|"
            r"laptops?|watches?|shirts?|shoes?|boots?|jackets?|bottles?|"
            r"speakers?|tablets?|lamps?|cameras?|helmets?)\b|"
            r"\b(?:items?|products?|laptops?|watches?|shirts?|shoes?|boots?|"
            r"jackets?|bottles?|speakers?|tablets?|lamps?|cameras?|helmets?)"
            r"\b.{0,100}"
            r"\b(?:swap|swapping)\b",
            re.I,
        ),
    ),
    (
        "action",
        "action:modify_item",
        re.compile(
            r"\b(?:change|modify|replace|switch|upgrade|downgrade)\b.{0,80}"
            r"\b(?:item|product|size|color|colour|variant|model|version|"
            r"laptop|watch|shirt|shoe|boot|jacket|bottle|speaker|tablet)\b",
            re.I,
        ),
    ),
    (
        "action",
        "action:remove_item",
        re.compile(
            r"\b(?:remove|cancel)\b.{0,60}\b(?:item|items|just|only|selected)\b|"
            r"\b(?:item|items)\b.{0,60}\b(?:remove|cancel)\b",
            re.I,
        ),
    ),
    (
        "action",
        "action:update_address",
        re.compile(
            r"\b(?:address|ship|shipping|deliver|delivery|sent)\b.{0,80}"
            r"\b(?:change|update|new|instead|to)\b|"
            r"\b(?:change|update|send|ship|deliver)\b.{0,80}\baddress\b",
            re.I,
        ),
    ),
    (
        "scope",
        "scope:default_address",
        re.compile(
            r"\b(?:default|account|profile|future[- ]order)\b.{0,40}\baddress\b|"
            r"\baddress\b.{0,40}\b(?:default|account|profile|future[- ]order)\b",
            re.I,
        ),
    ),
    (
        "scope",
        "scope:order_address",
        re.compile(
            r"\b(?:shipping|delivery|order)\b.{0,50}\baddress\b|"
            r"\baddress\b.{0,50}\b(?:shipping|delivery|order)\b|"
            r"\b(?:send|ship|deliver|sent)\b.{0,80}\b(?:order|it|this)\b",
            re.I,
        ),
    ),
    (
        "action",
        "action:change_payment",
        re.compile(
            r"\b(?:change|switch|use|charge|refund)\b.{0,80}"
            r"\b(?:payment|card|paypal|gift card|visa|mastercard|amex)\b|"
            r"\b(?:payment method|gift card)\b.{0,80}\b(?:change|switch|use)\b",
            re.I,
        ),
    ),
    (
        "action",
        "action:factual_question",
        re.compile(
            r"\b(?:how much|how many|what(?:'s| is| are)|which|list|show|tell me|"
            r"check|available|availability|option|options|tracking|total|balance|"
            r"status|price difference|order details|recent orders)\b",
            re.I,
        ),
    ),
    (
        "condition",
        "condition:all_pending_orders",
        re.compile(
            r"\b(?:all|every|any)\b.{0,40}\b(?:pending|open|unshipped)\b.{0,30}"
            r"\border|orders\b|\b(?:pending|open|unshipped) orders\b",
            re.I,
        ),
    ),
    (
        "condition",
        "condition:refund_routing",
        re.compile(
            r"\brefund\b.{0,80}\b(?:card|paypal|gift card|original|payment method)\b|"
            r"\b(?:card|paypal|gift card|original payment method)\b.{0,80}\brefund\b",
            re.I,
        ),
    ),
    (
        "request",
        "request:exact_factual_value",
        re.compile(
            r"\btracking\s+(?:number|id)\b|"
            r"\bexactly\s+how\s+many\b|"
            r"\bhow\s+much\s+(?:i(?:'|’)?(?:ll|d)\s+get\s+back|"
            r"i\s+(?:paid|would\s+get)|money\s+i(?:'|’)?m\s+getting\s+back|"
            r"(?:the\s+)?refund|(?:the\s+)?items?\s+i(?:'|’)?m\s+keeping)|"
            r"\b(?:total\s+(?:amount|price)|amount\s+.*?\s+total)\b|"
            r"\b(?:price|amount)\s+i\s+paid\b|"
            r"\b(?:check|confirm|tell\s+me|know)\b.{0,80}"
            r"\b(?:storage\s+size|battery\s+life|which\s+address|"
            r"still\s+on\s+the\s+way)\b|"
            r"\boptions?.{0,80}\balong\s+with\s+(?:their\s+)?prices\b|"
            r"\bwhich\s+one\s+saves\s+me\s+more\b|"
            r"\bwhy\b.{0,80}\bdelay\b|"
            r"\bwhen\s+(?:it(?:'|’)s|is)\s+arriving\b|"
            r"\border\s+status\b|"
            r"\bwhich\b.{0,80}\b(?:i|we)\s+ordered\b|"
            r"\bwhat\b.{0,50}\bmaterials?\b",
            re.I,
        ),
    ),
    (
        "topic",
        "topic:gift_card_balance",
        re.compile(
            r"\bgift\s*card\b.{0,70}\b(?:balance|left|remaining)\b|"
            r"\b(?:balance|left|remaining)\b.{0,70}\bgift\s*card\b|"
            r"\bhow\s+much\b.{0,70}\bgift\s*card\b",
            re.I,
        ),
    ),
    (
        "scope",
        "scope:pending_request",
        re.compile(
            r"\b(?:pending|hasn['’]?t shipped|haven['’]?t shipped|"
            r"not yet shipped|still processing|just placed|recently placed)\b",
            re.I,
        ),
    ),
    (
        "scope",
        "scope:delivered_request",
        re.compile(r"\b(?:received|delivered|just got|i got|arrived)\b", re.I),
    ),
    (
        "request",
        "request:return_items",
        re.compile(
            r"\b(?:want|need|like|help\s+me|can\s+you|please|"
            r"go\s+ahead\s+and)\b.{0,50}\breturn\b|"
            r"\bprocess\s+(?:the\s+)?return\b|"
            r"\breturn\s+(?:my|the|all|everything|just|only|an?)\b",
            re.I,
        ),
    ),
    (
        "request",
        "request:update_default_address",
        re.compile(
            r"\b(?:make|set|change|update)\b.{0,70}"
            r"\b(?:default|account|profile|future[- ]order)\b.{0,40}"
            r"\baddress\b|"
            r"\b(?:default|account|profile|future[- ]order)\b.{0,40}"
            r"\baddress\b.{0,70}\b(?:change|update|set|new)\b",
            re.I,
        ),
    ),
    (
        "request",
        "request:update_order_address",
        re.compile(
            r"\b(?:change|update|fix|correct)\b.{0,100}"
            r"\b(?:shipping|delivery|order)\s+address\b|"
            r"\b(?:shipping|delivery|order)\s+address\b.{0,100}"
            r"\b(?:change|update|fix|correct|new|instead)\b",
            re.I,
        ),
    ),
    (
        "request",
        "request:partial_order_removal",
        re.compile(
            r"\b(?:cancel|remove|return)\s+"
            r"(?:just|only|selected|the\s+following)\b|"
            r"\b(?:cancel|remove|return)\b.{0,80}"
            r"\b(?:except\s+for|but\s+keep|and\s+keep)\b|"
            r"\bkeep\s+(?!an?\s+eye\b).{0,60}\b(?:and|but)\b.{0,30}"
            r"\b(?:cancel|remove|return)\b",
            re.I,
        ),
    ),
)

_STATE_TAGS = {
    "pending": "pending",
    "delivered": "delivered",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "return requested": "return_requested",
    "exchange requested": "exchange_requested",
}


def extract_episode_facts(observable: Mapping[str, Any]) -> EpisodeFacts:
    """Extract conservative generic fact tags from user and tool evidence."""
    tags: set[str] = set()
    known_dimensions: set[str] = set()
    evidence: dict[str, list[str]] = {}

    user_messages = observable.get("user_messages")
    if isinstance(user_messages, list):
        known_dimensions.add("action")
        for index, message in enumerate(user_messages):
            pointer = f"user_messages[{index}]"
            for dimension, tag, pattern in _USER_FACT_PATTERNS:
                if not pattern.search(str(message)):
                    continue
                tags.add(tag)
                known_dimensions.add(dimension)
                evidence.setdefault(tag, []).append(pointer)

    tool_observations = observable.get("tool_observations")
    if isinstance(tool_observations, list):
        known_dimensions.add("tool")
        outcomes_by_name: dict[str, set[str]] = {}
        for index, raw_observation in enumerate(tool_observations):
            if not isinstance(raw_observation, Mapping):
                continue
            pointer = str(
                raw_observation.get("pointer") or f"tool_observations[{index}]"
            )
            name = str(raw_observation.get("name") or "").strip().lower()
            if name:
                _add_fact(tags, evidence, f"tool:{name}", pointer)
            outcome = str(raw_observation.get("outcome_status") or "")
            if name and outcome:
                _add_fact(
                    tags,
                    evidence,
                    f"tool_outcome:{name}:{outcome}",
                    pointer,
                )
                known_dimensions.add("tool_outcome")
                outcomes_by_name.setdefault(name, set()).add(outcome)
            serialized = json.dumps(
                raw_observation,
                sort_keys=True,
                ensure_ascii=False,
            ).lower()
            if outcome == "error_returned":
                _add_fact(tags, evidence, "condition:tool_error", pointer)
                known_dimensions.add("condition")
            if re.search(r"insufficient|not enough|cannot cover|can't cover", serialized):
                _add_fact(
                    tags,
                    evidence,
                    "condition:insufficient_payment",
                    pointer,
                )
                known_dimensions.add("condition")
            if name.startswith("find_user") and (
                outcome == "error_returned"
                or re.search(r"not found|no user|no matching", serialized)
            ):
                _add_fact(tags, evidence, "condition:lookup_failed", pointer)
                known_dimensions.add("condition")
            for state, normalized in _STATE_TAGS.items():
                if not re.search(
                    rf'\b(?:status|state)\b[\\\"\s:=-]{{0,12}}\b{re.escape(state)}\b',
                    serialized,
                ):
                    continue
                _add_fact(tags, evidence, f"state:{normalized}", pointer)
                known_dimensions.add("state")

        recovered_lookup_names = sorted(
            name
            for name, outcomes in outcomes_by_name.items()
            if "error_returned" in outcomes
            and "result_returned" in outcomes
            and (
                name.startswith("find_")
                or name.startswith("get_")
                or "lookup" in name
                or "search" in name
            )
        )
        if recovered_lookup_names:
            recovery_pointers = [
                pointer
                for name in recovered_lookup_names
                for outcome in ("error_returned", "result_returned")
                for pointer in evidence.get(
                    f"tool_outcome:{name}:{outcome}",
                    [],
                )
            ]
            for pointer in recovery_pointers:
                _add_fact(
                    tags,
                    evidence,
                    "condition:lookup_recovered",
                    pointer,
                )
            known_dimensions.add("condition")

    return EpisodeFacts(
        tags=frozenset(tags),
        known_dimensions=frozenset(known_dimensions),
        evidence_by_tag={
            tag: tuple(_ordered_unique(pointers))
            for tag, pointers in evidence.items()
        },
    )


def normalize_applicability_contract(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a machine-readable applicability contract."""
    if raw.get("schema_version") != APPLICABILITY_CONTRACT_SCHEMA_VERSION:
        raise ValueError("Applicability contract schema_version is invalid")
    requires = _normalize_applicability_clauses(
        raw.get("requires"),
        field="requires",
    )
    excludes = _normalize_applicability_clauses(
        raw.get("excludes", []),
        field="excludes",
    )
    deterministic_accept = raw.get("deterministic_accept", False)
    if not isinstance(deterministic_accept, bool):
        raise ValueError("Applicability deterministic_accept must be boolean")
    return {
        "schema_version": APPLICABILITY_CONTRACT_SCHEMA_VERSION,
        "requires": requires,
        "excludes": excludes,
        "deterministic_accept": deterministic_accept,
    }


def compile_applicability_contract(
    guideline: Mapping[str, Any],
    *,
    infer_unreviewed: bool = False,
) -> Optional[dict[str, Any]]:
    """Return an explicit contract or infer a conservative action prefilter."""
    explicit = guideline.get("applicability_contract")
    if isinstance(explicit, Mapping):
        return normalize_applicability_contract(explicit)
    if not infer_unreviewed:
        return None

    text = " ".join(
        [
            str(guideline.get("intent_label") or ""),
            str(guideline.get("description") or ""),
            *[
                str(item.get("applicability") or "")
                for item in guideline.get("criteria") or []
                if isinstance(item, Mapping)
            ],
        ]
    ).lower()
    action_tags = _inferred_guideline_action_tags(text)
    if not action_tags:
        return None
    excludes: list[dict[str, Any]] = []
    if "action:cancel" in action_tags and not re.search(
        r"undo|reverse|reinstate|restore|reactivate", text
    ):
        excludes.append(
            {
                "dimension": "action",
                "any_of": ["action:reverse_cancellation"],
                "on_known_absence": "unknown",
            }
        )
    return normalize_applicability_contract(
        {
            "schema_version": APPLICABILITY_CONTRACT_SCHEMA_VERSION,
            "requires": [
                {
                    "dimension": "action",
                    "any_of": sorted(action_tags),
                    "on_known_absence": "not_applicable",
                }
            ],
            "excludes": excludes,
            "deterministic_accept": False,
        }
    )


def evaluate_applicability_contract(
    facts: EpisodeFacts,
    contract: Mapping[str, Any],
) -> ApplicabilityContractDecision:
    """Evaluate a normalized contract using conservative tri-state logic."""
    normalized = normalize_applicability_contract(contract)
    for clause in normalized["excludes"]:
        matched = sorted(set(clause["any_of"]) & facts.tags)
        if matched:
            return ApplicabilityContractDecision(
                status="not_applicable",
                reason="deterministic exclusion matched: " + ", ".join(matched),
                evidence_pointers=_evidence_for_tags(facts, matched),
            )

    unresolved: list[str] = []
    for clause in normalized["requires"]:
        alternatives = set(clause["any_of"])
        if alternatives & facts.tags:
            continue
        dimension = str(clause["dimension"])
        if (
            dimension in facts.known_dimensions
            and clause["on_known_absence"] == "not_applicable"
        ):
            return ApplicabilityContractDecision(
                status="not_applicable",
                reason=(
                    f"known {dimension} facts do not satisfy any required tag: "
                    + ", ".join(sorted(alternatives))
                ),
                evidence_pointers=(),
            )
        unresolved.append(dimension)

    if unresolved or not normalized["deterministic_accept"]:
        reason = "contract requires semantic review"
        if unresolved:
            reason += "; unresolved dimensions: " + ", ".join(
                sorted(set(unresolved))
            )
        return ApplicabilityContractDecision(
            status="unknown",
            reason=reason,
            evidence_pointers=(),
        )

    matched_tags = sorted(
        {
            tag
            for clause in normalized["requires"]
            for tag in clause["any_of"]
            if tag in facts.tags
        }
    )
    return ApplicabilityContractDecision(
        status="applicable",
        reason="all deterministic applicability requirements matched",
        evidence_pointers=_evidence_for_tags(facts, matched_tags),
    )


def _normalize_applicability_clauses(
    value: Any,
    *,
    field: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (field == "requires" and not value):
        raise ValueError(f"Applicability contract {field} must be a nonempty list")
    normalized: list[dict[str, Any]] = []
    for raw_clause in value:
        if not isinstance(raw_clause, Mapping):
            raise ValueError(f"Applicability contract {field} clause is invalid")
        dimension = str(raw_clause.get("dimension") or "").strip()
        any_of = raw_clause.get("any_of")
        on_known_absence = str(
            raw_clause.get("on_known_absence") or "unknown"
        ).strip()
        if (
            not dimension
            or not isinstance(any_of, list)
            or not any_of
            or not all(isinstance(item, str) and item.strip() for item in any_of)
            or on_known_absence not in {"unknown", "not_applicable"}
        ):
            raise ValueError(f"Applicability contract {field} clause is invalid")
        normalized.append(
            {
                "dimension": dimension,
                "any_of": _ordered_unique(str(item).strip() for item in any_of),
                "on_known_absence": on_known_absence,
            }
        )
    return normalized


def _inferred_guideline_action_tags(text: str) -> set[str]:
    tags: set[str] = set()
    keyword_tags = (
        (r"\b(?:cancel|cancellation)\b", "action:cancel"),
        (r"\breturn\b", "action:return"),
        (r"\bexchange\b", "action:exchange"),
        (
            r"\b(?:item modification|item change|replace|replacement variant)\b",
            "action:modify_item",
        ),
        (r"\b(?:remove item|item removal)\b", "action:remove_item"),
        (r"\b(?:address|shipping)\b", "action:update_address"),
        (
            r"\b(?:payment method|gift.card balance|switch.*payment)\b",
            "action:change_payment",
        ),
        (
            r"\b(?:factual|question|tracking|availability|order total|specific value)\b",
            "action:factual_question",
        ),
        (
            r"\b(?:lookup fails|failed.*lookup|corrected.*identity)\b",
            "action:factual_question",
        ),
    )
    for pattern, tag in keyword_tags:
        if re.search(pattern, text):
            tags.add(tag)
    return tags


def _add_fact(
    tags: set[str],
    evidence: dict[str, list[str]],
    tag: str,
    pointer: str,
) -> None:
    tags.add(tag)
    evidence.setdefault(tag, []).append(pointer)


def _evidence_for_tags(
    facts: EpisodeFacts,
    tags: Sequence[str],
) -> tuple[str, ...]:
    return tuple(
        _ordered_unique(
            pointer
            for tag in tags
            for pointer in facts.evidence_by_tag.get(tag, ())
        )
    )


def _ordered_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))
