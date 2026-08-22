# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from src.hephaestus.datasets.evaluation_assets import (
    filter_synthetic_cases,
    has_scoreable_rubric,
)


@pytest.mark.parametrize(
    ("rubric", "scoreable"),
    [
        ({"must": ["preserve the requested state"]}, True),
        ({"must_not": ["invent tool results"]}, True),
        ({"should": ["prefer the shorter path"]}, True),
        ({"deterministic_checks": [{"type": "state_check"}]}, True),
        ({"reference_output": "approved result"}, True),
        ({"tool_expectations": {"required": "lookup"}}, True),
        ({}, False),
        ({"must": ["  "]}, False),
        ({"deterministic_checks": []}, False),
        ({"deterministic_checks": [{}]}, False),
        ({"reference_output": "\t"}, False),
        ({"tool_expectations": {}}, False),
        ({"must": "preserve the requested state"}, False),
    ],
)
def test_has_scoreable_rubric_requires_a_nonempty_oracle_field(
    rubric: dict[str, object],
    scoreable: bool,
) -> None:
    assert has_scoreable_rubric(rubric) is scoreable


def test_filter_synthetic_cases_rejects_empty_deterministic_checks() -> None:
    candidate = {
        "case_id": "synthetic-empty-check",
        "task_type": "generic_task",
        "context": {"request": "process this request"},
        "expected": {"deterministic_checks": [{}]},
        "metadata": {"group_id": "synthetic-empty-check"},
    }

    result = filter_synthetic_cases([candidate])

    assert result.accepted == []
    assert [issue.code for issue in result.issues] == ["not_scoreable"]


def test_synthetic_leakage_check_is_literal_with_a_24_character_minimum() -> None:
    leaked_reference = "abcdefghijklmnopqrstuvwx"
    exact = _synthetic_case(
        "synthetic-exact-literal",
        f"prefix {leaked_reference} suffix",
        expected={
            "rubric": {"must": ["return the approved result"]},
            "reference_output": leaked_reference,
        },
    )
    shorter_literal = _synthetic_case(
        "synthetic-short-literal",
        "prefix abcdefghijklmnopqrstuvw suffix",
        expected={
            "rubric": {"must": ["return the approved result"]},
            "reference_output": "abcdefghijklmnopqrstuvw",
        },
    )
    semantic_paraphrase = _synthetic_case(
        "synthetic-paraphrase",
        "Please cancel my profile permanently.",
        expected={"reference_output": "Close the customer's account for good."},
    )

    exact_result = filter_synthetic_cases([exact])
    accepted_result = filter_synthetic_cases([shorter_literal, semantic_paraphrase])

    assert [issue.code for issue in exact_result.issues] == ["label_leakage"]
    assert [case["case_id"] for case in accepted_result.accepted] == [
        "synthetic-short-literal",
        "synthetic-paraphrase",
    ]


def test_synthetic_duplicate_check_uses_context_token_set_overlap() -> None:
    existing = _synthetic_case(
        "existing",
        "anchor alpha beta gamma omega",
    )
    same_token_set = _synthetic_case(
        "same-token-set",
        "anchor gamma beta alpha omega",
    )
    one_extra_token = _synthetic_case(
        "one-extra-token",
        "anchor gamma beta alpha novel omega",
    )

    result = filter_synthetic_cases(
        [same_token_set, one_extra_token],
        existing_cases=[existing],
        duplicate_threshold=1.0,
    )

    assert [case["case_id"] for case in result.accepted] == ["one-extra-token"]
    assert [issue.code for issue in result.issues] == ["near_duplicate"]


def _synthetic_case(
    case_id: str,
    request: str,
    *,
    expected: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "task_type": "generic_task",
        "context": {"request": request},
        "expected": (
            expected
            if expected is not None
            else {"rubric": {"must": ["answer the request"]}}
        ),
        "metadata": {"group_id": case_id},
    }
