# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the vendor-neutral evaluation input contract."""

from pathlib import Path

import pytest

from src.hephaestus.evaluation_assets.input_contract import (
    SCHEMA_VERSION,
    canonical_user_intent_text,
    episode_tool_names,
    episode_user_messages,
    input_contract_document,
    record_user_messages,
    redact_correctness_signals,
    validate_input_records,
)


def _record(record_id: str = "record-1") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "group_id": "conversation-1",
        "task_type": "general_assistant",
        "user_input": "Process the supplied input.",
        "conversation_context": [],
        "tool_calls": [],
        "runtime": {},
        "metadata": {},
    }


def test_canonical_labeled_and_unlabeled_records_validate() -> None:
    labeled = {
        **_record(),
        "assistant_output": "The input was processed.",
        "feedback": {
            "polarity": "positive",
            "rationale": "The response satisfied the stated requirement.",
        },
    }

    validate_input_records(
        [labeled],
        labeled=True,
        path=Path("labeled.jsonl"),
    )
    validate_input_records(
        [_record("record-2")],
        labeled=False,
        path=Path("unlabeled.jsonl"),
    )


def test_contract_accepts_an_ordered_episode() -> None:
    """A full episode can supplement the backward-compatible flat fields."""
    episode = {
        "episode_id": "episode-1",
        "termination_reason": "completed",
        "events": [
            {
                "sequence": 0,
                "type": "message",
                "role": "user",
                "content": "Find the order.",
            },
            {
                "sequence": 1,
                "type": "tool_call",
                "call_id": "call-1",
                "name": "lookup_order",
                "arguments": {"order_id": "123"},
            },
            {
                "sequence": 2,
                "type": "tool_result",
                "call_id": "call-1",
                "result": {"status": "shipped"},
            },
            {
                "sequence": 3,
                "type": "message",
                "role": "assistant",
                "content": "The order shipped.",
            },
        ],
    }
    record = {**_record(), "episode": episode}

    validate_input_records(
        [record],
        labeled=False,
        path=Path("unlabeled.jsonl"),
    )

    assert episode_user_messages(episode) == ["Find the order."]
    assert episode_tool_names(episode) == ["lookup_order"]


def test_user_intent_text_uses_all_episode_messages_without_tools() -> None:
    """Episode user turns are authoritative and repeated turns are retained."""
    record = {
        **_record(),
        "user_input": "Flat request",
        "conversation_context": [
            {"role": "user", "content": "Flat prior request"}
        ],
        "tool_calls": [{"name": "flat_tool", "arguments": {}}],
        "episode": {
            "events": [
                {
                    "sequence": 0,
                    "type": "message",
                    "role": "user",
                    "content": "Episode request",
                },
                {
                    "sequence": 1,
                    "type": "message",
                    "role": "assistant",
                    "content": "Assistant response",
                },
                {
                    "sequence": 2,
                    "type": "message",
                    "role": "user",
                    "content": "Episode request",
                },
                {
                    "sequence": 3,
                    "type": "tool_call",
                    "call_id": "call-1",
                    "name": "episode_tool",
                    "arguments": {},
                },
            ]
        },
    }

    assert record_user_messages(record) == [
        "Episode request",
        "Episode request",
    ]
    assert canonical_user_intent_text(record) == (
        "Episode request\nEpisode request"
    )


def test_user_intent_text_falls_back_to_legacy_user_fields() -> None:
    """Legacy records preserve prior-to-current user-message chronology."""
    record = {
        **_record(),
        "user_input": "Current request",
        "conversation_context": [
            {"role": "user", "content": "Earlier request"},
            {"role": "assistant", "content": "Assistant response"},
        ],
    }

    assert record_user_messages(record) == [
        "Earlier request",
        "Current request",
    ]
    assert canonical_user_intent_text(record) == (
        "Earlier request\nCurrent request"
    )


@pytest.mark.parametrize(
    ("episode", "message"),
    [
        ([], "episode.*object"),
        ({"events": []}, "episode.events.*must not be empty"),
        (
            {
                "events": [
                    {
                        "sequence": 0,
                        "type": "message",
                        "role": "user",
                        "content": "Request",
                    },
                    {
                        "sequence": 0,
                        "type": "message",
                        "role": "assistant",
                        "content": "Response",
                    },
                ]
            },
            "sequence.*strictly increasing",
        ),
        (
            {"events": [{"sequence": 0, "type": "observation"}]},
            "type.*message.*tool_call.*tool_result",
        ),
        (
            {
                "events": [
                    {
                        "sequence": 0,
                        "type": "tool_call",
                        "call_id": "call-1",
                        "name": "lookup",
                        "arguments": [],
                    }
                ]
            },
            "arguments.*object",
        ),
        (
            {
                "events": [
                    {
                        "sequence": 0,
                        "type": "tool_result",
                        "call_id": "missing-call",
                        "result": {},
                    }
                ]
            },
            "call_id.*prior tool call",
        ),
    ],
)
def test_contract_rejects_malformed_episodes(
    episode: object,
    message: str,
) -> None:
    """Episode ordering and tool-call links are enforced at ingestion."""
    with pytest.raises(ValueError, match=message):
        validate_input_records(
            [{**_record(), "episode": episode}],
            labeled=False,
            path=Path("unlabeled.jsonl"),
        )


def test_contract_rejects_vendor_shaped_or_ambiguous_records() -> None:
    with pytest.raises(ValueError, match="missing required field 'schema_version'"):
        validate_input_records(
            [{"id": "run-1", "inputs": {}, "outputs": {}}],
            labeled=False,
            path=Path("unlabeled.jsonl"),
        )

    invalid_feedback = {
        **_record(),
        "assistant_output": "A response",
        "feedback": {"polarity": "thumbs_down", "rationale": "Incorrect"},
    }
    with pytest.raises(ValueError, match="feedback.polarity"):
        validate_input_records(
            [invalid_feedback],
            labeled=True,
            path=Path("labeled.jsonl"),
        )


def test_contract_document_is_versioned_and_explicit() -> None:
    contract = input_contract_document()

    assert contract["schema_version"] == SCHEMA_VERSION
    assert "group_id" in contract["common_required_fields"]
    assert contract["labeled_required_fields"] == [
        "assistant_output",
        "feedback",
    ]
    assert contract["feedback"]["optional"] == [
        "correction",
        "source",
        "correctness_signals",
    ]
    assert contract["correctness_signal"] == {
        "required": ["kind", "check_id", "passed"],
        "types": {
            "kind": "string",
            "check_id": "string",
            "passed": "boolean",
        },
        "optional": ["content"],
        "kinds": ["deterministic", "executable"],
    }
    assert "episode" in contract["optional_fields"]
    assert contract["episode"] == {
        "required": ["events"],
        "types": {"events": "array"},
        "optional": ["episode_id", "termination_reason"],
        "event_types": ["message", "tool_call", "tool_result"],
        "event_common_required": ["sequence", "type"],
        "message_required": ["role", "content"],
        "tool_call_required": ["call_id", "name", "arguments"],
        "tool_result_required": ["call_id"],
        "tool_result_content": ["result", "error"],
    }


def test_contract_accepts_structured_correctness_signals() -> None:
    labeled = {
        **_record(),
        "assistant_output": "The input was processed.",
        "feedback": {
            "polarity": "mixed",
            "rationale": "",
            "correctness_signals": [
                {
                    "kind": "deterministic",
                    "check_id": "schema-check",
                    "passed": True,
                    "content": {"observed": "valid"},
                },
                {
                    "kind": "executable",
                    "check_id": "exit-status",
                    "passed": False,
                },
            ],
        },
    }

    validate_input_records([labeled], labeled=True, path=Path("labeled.jsonl"))


@pytest.mark.parametrize(
    ("signals", "message"),
    [
        ({}, "correctness_signals.*array"),
        (["failed"], r"correctness_signals\[0\].*object"),
        (
            [{"check_id": "check", "passed": True}],
            r"correctness_signals\[0\]\.kind.*required",
        ),
        (
            [{"kind": "heuristic", "check_id": "check", "passed": True}],
            r"correctness_signals\[0\]\.kind.*deterministic.*executable",
        ),
        (
            [{"kind": [], "check_id": "check", "passed": True}],
            r"correctness_signals\[0\]\.kind.*deterministic.*executable",
        ),
        (
            [{"kind": "deterministic", "check_id": "  ", "passed": True}],
            r"correctness_signals\[0\]\.check_id.*non-empty",
        ),
        (
            [{"kind": "executable", "check_id": "check", "passed": 0}],
            r"correctness_signals\[0\]\.passed.*boolean",
        ),
        (
            [
                {
                    "kind": "executable",
                    "check_id": "check",
                    "passed": False,
                    "vendor_error": "ordinary tool error",
                }
            ],
            r"correctness_signals\[0\].*unsupported field.*vendor_error",
        ),
    ],
)
def test_contract_rejects_malformed_correctness_signals(
    signals: object,
    message: str,
) -> None:
    labeled = {
        **_record(),
        "assistant_output": "The input was processed.",
        "feedback": {
            "polarity": "negative",
            "rationale": "",
            "correctness_signals": signals,
        },
    }

    with pytest.raises(ValueError, match=message):
        validate_input_records(
            [labeled],
            labeled=True,
            path=Path("labeled.jsonl"),
        )


def test_correctness_signal_redaction_preserves_structure_only() -> None:
    seen_content: list[object] = []

    def redact_content(value: object) -> object:
        seen_content.append(value)
        return {"detail": "<email>"}

    redacted = redact_correctness_signals(
        [
            {
                "kind": "executable",
                "check_id": "owner@example.com",
                "passed": False,
                "content": {"detail": "owner@example.com"},
            }
        ],
        redact_content=redact_content,
    )

    assert redacted == [
        {
            "kind": "executable",
            "check_id": "owner@example.com",
            "passed": False,
            "content": {"detail": "<email>"},
        }
    ]
    assert seen_content == [{"detail": "owner@example.com"}]
