# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Tau-to-FAFO complete-episode adapter."""

from __future__ import annotations

import json

from tenants.tau3_retail.code.export_fafo_traces import export_records


def _simulation() -> dict:
    return {
        "id": "simulation-0-0",
        "task_id": 0,
        "trial": 0,
        "seed": 300,
        "mode": "text",
        "termination_reason": "user_stop",
        "reward": 1,
        "reward_info": {"expected_actions": ["secret"]},
        "messages": [
            {"role": "assistant", "content": "Hello.", "turn_idx": 0},
            {"role": "user", "content": "Where is my order?", "turn_idx": 1},
            {
                "role": "assistant",
                "content": None,
                "turn_idx": 2,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "get_order_details",
                        "arguments": {"order_id": "#100"},
                    }
                ],
            },
            {
                "role": "tool",
                "id": "call-1",
                "content": "{\"status\":\"shipped\"}",
                "error": False,
                "turn_idx": 2,
            },
            {
                "role": "assistant",
                "content": "Order #100 is shipped.",
                "turn_idx": 3,
            },
        ],
    }


def _split() -> dict:
    return {
        "release": "v1.0.1",
        "release_commit": "fc0055dc",
        "freeze_id": "test-freeze",
        "task_assignments": [
            {
                "task_id": 0,
                "partition": "development",
                "scenario_family_id": "order-status",
            }
        ],
    }


def test_export_keeps_the_whole_episode_but_not_native_oracles() -> None:
    rows, counts = export_records(
        {"simulations": [_simulation()]},
        _split(),
        partition="development",
        source_run="unit-test",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["group_id"] == "order-status"
    assert row["user_input"] == "Where is my order?"
    assert row["assistant_output"] == "Order #100 is shipped."
    assert [event["type"] for event in row["episode"]["events"]] == [
        "message",
        "message",
        "tool_call",
        "tool_result",
        "message",
    ]
    assert row["tool_calls"][0]["result"] == '{"status":"shipped"}'
    assert counts["tool_calls"] == 1
    serialized = json.dumps(row)
    assert "reward" not in serialized
    assert "expected_actions" not in serialized


def test_export_rejects_wrong_partition() -> None:
    try:
        export_records(
            {"simulations": [_simulation()]},
            _split(),
            partition="final_holdout",
            source_run="unit-test",
        )
    except ValueError as exc:
        assert "not assigned to final_holdout" in str(exc)
    else:
        raise AssertionError("wrong-partition export should fail")
