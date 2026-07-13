# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from src.hephaestus.types import EvalCase
from tenants.software_name_categorization.code.scorers.category_scorer import Scorer


def _case(expected: str = "network_and_remote_access") -> EvalCase:
    return EvalCase(
        case_id="case-001",
        task_type="software_name_categorization",
        context={"software_name": "Remmina"},
        expected={"category": expected},
        metadata={},
    )


def test_scorer_accepts_exact_label() -> None:
    result = Scorer().score_case(_case(), "network_and_remote_access", {})

    assert result["composite_score"] == 100.0
    assert result["score_breakdown"]["f1"] == 100.0
    assert result["score_breakdown"]["valid_label"] == 100.0


def test_scorer_extracts_last_line_label() -> None:
    result = Scorer().score_case(
        _case("exposure_testing"),
        "This is a security testing tool.\nexposure_testing",
        {},
    )

    assert result["composite_score"] == 100.0
    assert result["score_breakdown"]["strict_format"] == 0.0


def test_scorer_rejects_unknown_expected_label() -> None:
    with pytest.raises(ValueError, match="unknown expected.category"):
        Scorer().validate_case(_case("not_a_label"), {})


def test_scorer_requires_software_name_only_context() -> None:
    case = EvalCase(
        case_id="case-002",
        task_type="software_name_categorization",
        context={"software_name": "Remmina", "vendor": "extra"},
        expected={"category": "network_and_remote_access"},
        metadata={},
    )

    with pytest.raises(ValueError, match="context.software_name"):
        Scorer().validate_case(case, {})
