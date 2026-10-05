# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from typing import Any

import pytest

from src.hephaestus.types import EvalCaseResult


def _result(**overrides: Any) -> EvalCaseResult:
    values: dict[str, Any] = {
        "case_id": "case-1",
        "task_type": "classification",
        "diagnostics": [],
        "score_breakdown": {"quality": 0.0},
        "composite_score": 0.0,
        "output_text": "",
        "step_outputs": {},
    }
    values.update(overrides)
    return EvalCaseResult(**values)


def test_legacy_result_construction_defaults_to_success() -> None:
    """Existing result producers must remain successful without new arguments."""
    result = _result()

    assert result.execution_status == "succeeded"
    assert result.execution_error is None
    assert result.evaluation_provenance == {}


def test_execution_error_uses_only_fixed_allowlisted_fields() -> None:
    """Persisted failures must not expose exception classes or messages."""
    from src.hephaestus.runs.errors import sanitize_execution_error

    class SecretProviderFailure(RuntimeError):
        pass

    error = sanitize_execution_error(
        SecretProviderFailure("Bearer secret-token expected=protected-answer"),
        phase="chain",
    )

    assert error == {
        "phase": "chain",
        "category": "runtime",
        "summary": "Chain execution failed.",
    }
    serialized = json.dumps(error)
    assert "SecretProviderFailure" not in serialized
    assert "secret-token" not in serialized
    assert "protected-answer" not in serialized


def test_execution_error_classifies_a_safe_cause_without_persisting_it() -> None:
    """A causal timeout should retain only its fixed safe category and summary."""
    from src.hephaestus.runs.errors import sanitize_execution_error

    try:
        try:
            raise TimeoutError("upstream secret timeout details")
        except TimeoutError as cause:
            raise RuntimeError("wrapper includes protected context") from cause
    except RuntimeError as exc:
        error = sanitize_execution_error(exc, phase="scorer")

    assert error == {
        "phase": "scorer",
        "category": "timeout",
        "summary": "Scorer execution timed out.",
    }
    assert "secret" not in json.dumps(error)
    assert "protected" not in json.dumps(error)


@pytest.mark.parametrize(
    ("phase", "category"),
    [("provider", "runtime"), ("chain", "authentication")],
)
def test_execution_error_builder_rejects_non_allowlisted_values(
    phase: str,
    category: str,
) -> None:
    """Unknown persisted error identities must fail closed."""
    from src.hephaestus.runs.errors import build_execution_error

    with pytest.raises(ValueError):
        build_execution_error(phase, category)


def test_result_rejects_inconsistent_execution_state() -> None:
    """A failed result requires a safe error and a success cannot carry one."""
    from src.hephaestus.runs.errors import build_execution_error

    with pytest.raises(ValueError, match="failed EvalCaseResult requires execution_error"):
        _result(execution_status="failed")
    with pytest.raises(ValueError, match="succeeded EvalCaseResult cannot carry execution_error"):
        _result(execution_error=build_execution_error("chain", "runtime"))
    with pytest.raises(ValueError, match="execution_status"):
        _result(execution_status="completed")


def test_result_rejects_noncanonical_persisted_error_data() -> None:
    """Callers cannot bypass the error allowlist with dynamic fields or text."""
    with pytest.raises(ValueError, match="must contain only"):
        _result(
            execution_status="failed",
            execution_error={
                "phase": "chain",
                "category": "runtime",
                "summary": "Chain execution failed.",
                "message": "protected answer and token",
            },
        )
    with pytest.raises(ValueError, match="fixed safe summary"):
        _result(
            execution_status="failed",
            execution_error={
                "phase": "chain",
                "category": "runtime",
                "summary": "Dynamic provider failure detail",
            },
        )


def test_result_provenance_retains_only_a_current_trust_tier() -> None:
    """Result provenance must never carry arbitrary case metadata."""
    result = _result(
        evaluation_provenance={
            "trust_tier": "inferred_from_trusted_feedback",
            "expected": {"answer": "protected"},
            "context": {"user": "private"},
            "group_id": "sensitive-group",
        }
    )

    assert result.evaluation_provenance == {
        "trust_tier": "inferred_from_trusted_feedback"
    }
    serialized = json.dumps(result.evaluation_provenance)
    assert "protected" not in serialized
    assert "private" not in serialized
    assert "sensitive-group" not in serialized


def test_result_provenance_drops_unknown_trust_tiers() -> None:
    """Historical or arbitrary trust labels must not enter current results."""
    result = _result(
        evaluation_provenance={
            "trust_tier": "untrusted_external_label",
            "source": "protected-source",
        }
    )

    assert result.evaluation_provenance == {}
