# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for outcome-blind selection and trusted-feedback review."""

from __future__ import annotations

from tenants.tau3_retail.code.feedback_workflow import _review_text, select_records


def _record(index: int) -> dict:
    tool_name = (
        "return_delivered_order_items"
        if index % 2 == 0
        else "get_order_details"
    )
    return {
        "record_id": f"record-{index}",
        "group_id": f"group-{index}",
        "runtime": {"task_id": str(index), "trial": index % 4},
        "tool_calls": [
            {"name": tool_name, "arguments": {"order_id": f"#{index}"}, "error": None}
        ],
        "episode": {
            "events": [
                {
                    "sequence": 0,
                    "type": "message",
                    "role": "user",
                    "content": f"Request {index}",
                },
                {
                    "sequence": 1,
                    "type": "message",
                    "role": "assistant",
                    "content": f"Response {index}",
                },
            ]
        },
    }


def test_small_selection_is_exact_and_deterministic() -> None:
    rows = [_record(index) for index in range(12)]
    first, first_metrics = select_records(rows, count=3, seed="stable")
    second, second_metrics = select_records(rows, count=3, seed="stable")

    assert [row["record_id"] for row in first] == [
        row["record_id"] for row in second
    ]
    assert len(first) == len(first_metrics) == len(second_metrics) == 3
    assert len({row["group_id"] for row in first}) == 3


def test_review_template_contains_only_dialogue_and_empty_feedback() -> None:
    rendered = _review_text(_record(1), 1)

    assert "### User\n\nRequest 1" in rendered
    assert "### Assistant\n\nResponse 1" in rendered
    assert "get_order_details" not in rendered
    assert "**Rationale**:" in rendered
    assert "**Reviewed as trusted** (`yes` or `no`): no" in rendered
