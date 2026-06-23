# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict

from src.hephaestus.loader import _load_module
from src.hephaestus.scoring.scorer import Scorer


def load_tenant_scorer(scoring_profile: Dict[str, Any]) -> Scorer:
    scorer_raw = scoring_profile.get("scorer")
    if not isinstance(scorer_raw, dict):
        raise ValueError("scoring_profile.scorer is required and must be an object")

    module_path_raw = scorer_raw.get("module_path")
    if not isinstance(module_path_raw, str) or not module_path_raw.strip():
        raise ValueError("scoring_profile.scorer.module_path is required")
    module_path = Path(module_path_raw)

    legacy_keys = {"score_fn", "validate_fn"} & set(scorer_raw.keys())
    if legacy_keys:
        raise ValueError(
            "Legacy scorer keys are not supported: "
            + ", ".join(sorted(legacy_keys))
            + ". Use scoring_profile.scorer.class_name."
        )

    class_name = str(scorer_raw.get("class_name", "Scorer")).strip()
    if not class_name:
        raise ValueError("scoring_profile.scorer.class_name must be a non-empty string")

    module = _load_module(module_path)

    scorer_cls = getattr(module, class_name, None)
    if scorer_cls is None:
        raise ValueError(
            f"scoring_profile.scorer.class_name '{class_name}' was not found in {module_path}"
        )
    if not isinstance(scorer_cls, type):
        raise ValueError(
            f"scoring_profile.scorer.class_name '{class_name}' in {module_path} must refer to a class"
        )

    scorer = scorer_cls()
    if not isinstance(scorer, Scorer):
        raise ValueError(
            f"scoring_profile.scorer.class_name '{class_name}' in {module_path} must subclass "
            "src.hephaestus.scoring.scorer.Scorer"
        )

    return scorer


def _coerce_score(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not math.isfinite(score):
        raise ValueError(f"{field_name} must be a finite number")
    if score < 0.0 or score > 100.0:
        raise ValueError(f"{field_name} must be between 0 and 100")
    return score


def _coerce_breakdown_value(value: Any, field_name: str) -> float:
    """Like _coerce_score but allows values above 100 (e.g. raw point totals)."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not math.isfinite(score):
        raise ValueError(f"{field_name} must be a finite number")
    if score < 0.0:
        raise ValueError(f"{field_name} must be non-negative")
    return score


def validate_score_payload(payload: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
    if not isinstance(payload, dict):
        raise ValueError("score_case must return an object")
    if "composite_score" not in payload:
        raise ValueError("score_case result missing required field 'composite_score'")
    if "score_breakdown" not in payload:
        raise ValueError("score_case result missing required field 'score_breakdown'")

    composite_score = _coerce_score(payload["composite_score"], "composite_score")
    score_breakdown_raw = payload["score_breakdown"]
    if not isinstance(score_breakdown_raw, dict):
        raise ValueError("score_breakdown must be an object")

    score_breakdown: Dict[str, float] = {}
    for key, value in score_breakdown_raw.items():
        name = str(key)
        if not name:
            raise ValueError("score_breakdown keys must be non-empty")
        score_breakdown[name] = _coerce_breakdown_value(value, f"score_breakdown.{name}")

    return composite_score, score_breakdown


def extract_score_diagnostics(payload: Dict[str, Any]) -> list[str]:
    """Pull a scorer's optional free-text ``diagnostics`` out of its payload.

    Unlike ``score_breakdown`` (numeric only), ``diagnostics`` carries human-
    readable notes — e.g. an LLM judge's rationale — so they survive into the
    persisted case result. Returns an empty list when the key is absent.
    """
    raw = payload.get("diagnostics")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if not isinstance(raw, (list, tuple)):
        raise ValueError("score_breakdown 'diagnostics' must be a string or list of strings")
    return [str(item) for item in raw]
