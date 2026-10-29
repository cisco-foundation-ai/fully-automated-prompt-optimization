# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json

from data_pipeline_fakes import make_record

from src.hephaestus.data_pipeline.config import TraceSettings
from src.hephaestus.data_pipeline.trace import (
    compact_result,
    compact_value,
    episode_view,
    model_visible_context,
    redact_record,
    transcript,
)


class TestRedactRecord:
    def test_redacts_content_but_not_identity(self) -> None:
        """Emails and IPv4 addresses are replaced everywhere except identity fields."""
        row = make_record("r1", labeled=True, rationale="Mail me at a@b.com from 10.0.0.1")
        row["record_id"] = "user@example.com"
        row["runtime"] = {"host": "192.168.1.5"}

        redacted = redact_record(row)

        assert redacted["record_id"] == "user@example.com"
        assert redacted["feedback"]["rationale"] == "Mail me at <email> from <ip_address>"
        assert redacted["runtime"] == {"host": "<ip_address>"}
        assert redacted["feedback"]["polarity"] == "negative"

    def test_redacts_object_keys(self) -> None:
        """Email and IPv4 addresses used as object keys are redacted too."""
        row = make_record("r1", labeled=False)
        row["runtime"] = {"alice@example.com": "10.0.0.1"}

        assert redact_record(row)["runtime"] == {"<email>": "<ip_address>"}


class TestTranscript:
    def test_record_without_episode(self) -> None:
        """Without an episode, order is context, user input, tool calls, final output."""
        row = make_record("r1", labeled=True)
        row["conversation_context"] = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]

        entries = transcript(row, TraceSettings())

        assert [entry.get("role") or entry["tool"] for entry in entries] == [
            "user",
            "assistant",
            "user",
            "update_order",
            "assistant",
        ]
        assert entries[3]["outcome"] == "result_returned"

    def test_episode_events_keep_order_and_outcomes(self) -> None:
        """Episode events are used in order, and tool results attach to their call."""
        row = make_record("r1", labeled=False)
        row["episode"] = {
            "events": [
                {"sequence": 1, "type": "message", "role": "user", "content": "Cancel it"},
                {"sequence": 2, "type": "tool_call", "call_id": "c1", "name": "cancel", "arguments": {}},
                {"sequence": 3, "type": "tool_result", "call_id": "c1", "error": "not allowed"},
                {"sequence": 4, "type": "message", "role": "assistant", "content": "Sorry"},
            ]
        }

        entries = transcript(row, TraceSettings())

        assert entries[1] == {
            "tool": "cancel",
            "arguments": {},
            "outcome": "error_returned",
            "error": "not allowed",
        }
        assert entries[-1] == {"role": "assistant", "content": "Sorry"}

    def test_final_output_not_duplicated(self) -> None:
        """The final output is not appended twice when the episode already ends with it."""
        row = make_record("r1", labeled=True)
        row["episode"] = {
            "events": [
                {"sequence": 1, "type": "message", "role": "user", "content": "Change it"},
                {"sequence": 2, "type": "message", "role": "assistant", "content": "Done."},
            ]
        }

        assert transcript(row, TraceSettings())[-1:] == [{"role": "assistant", "content": "Done."}]
        assert len(transcript(row, TraceSettings())) == 2

    def test_episode_without_user_message_keeps_request(self) -> None:
        """An episode with only tool events is preceded by the record's request."""
        row = make_record("r1", labeled=False)
        row["episode"] = {
            "events": [
                {"sequence": 1, "type": "tool_call", "call_id": "c1", "name": "lookup", "arguments": {}}
            ]
        }

        entries = transcript(row, TraceSettings())

        assert entries[0] == {"role": "user", "content": "Please change order r1."}
        assert entries[1]["tool"] == "lookup"


class TestCompaction:
    def test_compact_value_bounds_size(self) -> None:
        """Long strings, wide objects, and long lists are truncated."""
        value = {"text": "x" * 600, "items": list(range(30)), **{f"k{i}": i for i in range(40)}}

        compact = compact_value(value)

        assert len(compact) == 30
        assert compact["text"].endswith("...") and len(compact["text"]) == 500
        assert len(compact["items"]) == 20

    def test_compact_value_parses_json_strings(self) -> None:
        """JSON-encoded strings are parsed so their size can be bounded."""
        assert compact_value(json.dumps({"a": [1, 2]})) == {"a": [1, 2]}

    def test_result_filters(self) -> None:
        """Tenant filters keep matching keys, drop bulky keys, and keep nested matches."""
        settings = TraceSettings(result_keys="status|order_id", drop_keys=["catalog"])
        result = {
            "status": "ok",
            "notes": "long",
            "catalog": {"status": "x"},
            "order": {"order_id": "1", "x": 2},
        }

        assert compact_result(result, settings) == {"status": "ok", "order": {"order_id": "1"}}

    def test_drop_keys_apply_at_every_depth(self) -> None:
        """Dropped keys are removed wherever they appear, even without result_keys."""
        settings = TraceSettings(drop_keys=["Listing"])

        assert compact_result({"data": {"listing": [1], "id": 5}}, settings) == {"data": {"id": 5}}

    def test_result_filters_search_json_strings_and_ignore_case(self) -> None:
        """Matches inside JSON-encoded strings survive, matching ignores case, and unmatched scalars go."""
        settings = TraceSettings(result_keys="order_id")
        result = {
            "body": json.dumps({"Order_ID": 5, "note": "x"}),
            "tags": ["a", "b"],
            "items": [{"order_id": 1}],
        }

        assert compact_result(result, settings) == {"body": {"Order_ID": 5}, "items": [{"order_id": 1}]}

    def test_top_level_scalars_are_kept(self) -> None:
        """A result that is not an object is kept even when filters are set."""
        settings = TraceSettings(result_keys="status")

        assert compact_result("Order cancelled", settings) == "Order cancelled"
        assert compact_result(["a", "b"], settings) == ["a", "b"]

    def test_result_without_filters_is_bounded_only(self) -> None:
        """With no filters, a tool result is compacted like any other value."""
        assert compact_result({"a": 1}, TraceSettings()) == {"a": 1}


class TestViews:
    def test_episode_view_has_no_feedback(self) -> None:
        """The episode view carries the transcript and runtime but never feedback."""
        view = episode_view(make_record("r1", labeled=True, route="orders"), TraceSettings())

        assert set(view) == {"record_id", "route", "task_type", "transcript", "runtime"}
        assert view["route"] == "orders"

    def test_model_visible_context(self) -> None:
        """The case context serializes messages, tool context, and runtime."""
        context = model_visible_context(make_record("r1", labeled=False))

        assert json.loads(context["messages_json"]) == [
            {"role": "user", "content": "Please change order r1."}
        ]
        assert set(context) == {"messages_json", "tool_context_json", "runtime_json"}
