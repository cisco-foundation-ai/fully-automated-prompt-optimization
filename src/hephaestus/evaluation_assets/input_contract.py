# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Vendor-neutral input contract for the evaluation asset pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

SCHEMA_VERSION = "fapo-evaluation-input-v1"
FEEDBACK_POLARITIES = frozenset({"positive", "negative", "mixed"})
CORRECTNESS_SIGNAL_KINDS = frozenset({"deterministic", "executable"})
CORRECTNESS_SIGNAL_REQUIRED_FIELDS = ("kind", "check_id", "passed")
CORRECTNESS_SIGNAL_OPTIONAL_FIELDS = ("content",)
EPISODE_EVENT_TYPES = frozenset({"message", "tool_call", "tool_result"})

COMMON_REQUIRED_FIELDS = (
    "schema_version",
    "record_id",
    "group_id",
    "task_type",
    "user_input",
    "conversation_context",
    "tool_calls",
    "runtime",
    "metadata",
)


def effective_route(row: Mapping[str, Any]) -> str:
    """Return the exact routing identity, falling back only when route is absent."""
    value = row["route"] if "route" in row else row["task_type"]
    return str(value)


def validate_input_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    labeled: bool,
    path: Path,
    row_numbers: Optional[Sequence[int]] = None,
) -> None:
    """Validate canonical records and raise one precise contract error."""
    if row_numbers is not None and len(row_numbers) != len(rows):
        raise ValueError("row_numbers must identify every input record")
    seen_ids: set[str] = set()
    for logical_index, row in enumerate(rows):
        row_number = (
            row_numbers[logical_index]
            if row_numbers is not None
            else logical_index + 1
        )
        location = f"{path}:{row_number}"
        for field in COMMON_REQUIRED_FIELDS:
            if field not in row:
                raise ValueError(f"{location}: missing required field '{field}'")
        if row["schema_version"] != SCHEMA_VERSION:
            raise ValueError(
                f"{location}: schema_version must be '{SCHEMA_VERSION}'"
            )
        for field in ("record_id", "group_id", "task_type", "user_input"):
            _require_nonempty_string(row[field], location, field)
        record_id = str(row["record_id"])
        if record_id in seen_ids:
            raise ValueError(f"{location}: duplicate record_id '{record_id}'")
        seen_ids.add(record_id)

        if "request_id" in row:
            _require_nonempty_string(row["request_id"], location, "request_id")
        if "route" in row:
            _require_nonempty_string(row["route"], location, "route")
        if "assistant_output" in row and not isinstance(
            row["assistant_output"], str
        ):
            raise ValueError(f"{location}: 'assistant_output' must be a string")
        if labeled and "assistant_output" not in row:
            raise ValueError(
                f"{location}: labeled records require 'assistant_output'"
            )

        _validate_messages(row["conversation_context"], location)
        _validate_tool_calls(row["tool_calls"], location)
        if "episode" in row:
            _validate_episode(row["episode"], location)
        for field in ("runtime", "metadata"):
            if not isinstance(row[field], Mapping):
                raise ValueError(f"{location}: '{field}' must be an object")

        if labeled:
            _validate_feedback(row.get("feedback"), location)
        elif "feedback" in row:
            raise ValueError(
                f"{location}: unlabeled records must not contain 'feedback'"
            )


def input_contract_document() -> Dict[str, Any]:
    """Return an API-safe summary used by the Studio and source adapters."""
    return {
        "schema_version": SCHEMA_VERSION,
        "common_required_fields": list(COMMON_REQUIRED_FIELDS),
        "common_types": {
            "schema_version": "string",
            "record_id": "string",
            "group_id": "string",
            "task_type": "string",
            "user_input": "string",
            "conversation_context": "array",
            "tool_calls": "array",
            "runtime": "object",
            "metadata": "object",
        },
        "optional_fields": [
            "request_id",
            "route",
            "assistant_output",
            "episode",
        ],
        "labeled_required_fields": ["assistant_output", "feedback"],
        "feedback": {
            "required": ["polarity", "rationale"],
            "types": {"polarity": "string", "rationale": "string"},
            "optional": ["correction", "source", "correctness_signals"],
        },
        "correctness_signal": {
            "required": list(CORRECTNESS_SIGNAL_REQUIRED_FIELDS),
            "types": {
                "kind": "string",
                "check_id": "string",
                "passed": "boolean",
            },
            "optional": list(CORRECTNESS_SIGNAL_OPTIONAL_FIELDS),
            "kinds": sorted(CORRECTNESS_SIGNAL_KINDS),
        },
        "feedback_polarities": sorted(FEEDBACK_POLARITIES),
        "conversation_message": {
            "required": ["role", "content"],
            "types": {"role": "string", "content": "string"},
        },
        "tool_call": {
            "required": ["name", "arguments"],
            "types": {"name": "string", "arguments": "object"},
            "optional": ["result", "error"],
        },
        "episode": {
            "required": ["events"],
            "types": {"events": "array"},
            "optional": ["episode_id", "termination_reason"],
            "event_types": sorted(EPISODE_EVENT_TYPES),
            "event_common_required": ["sequence", "type"],
            "message_required": ["role", "content"],
            "tool_call_required": ["call_id", "name", "arguments"],
            "tool_result_required": ["call_id"],
            "tool_result_content": ["result", "error"],
        },
        "notes": [
            "group_id is required for leakage-safe dataset splitting",
            "route defaults to task_type when omitted",
            "request_id defaults to record_id when omitted",
            "unlabeled records must not contain feedback",
        ],
    }


def redact_correctness_signals(
    value: Sequence[Mapping[str, Any]],
    *,
    redact_content: Callable[[Any], Any],
) -> list[dict[str, Any]]:
    """Redact optional signal content while preserving audited structure."""
    _validate_correctness_signals(value, "correctness_signals")
    redacted = []
    for signal in value:
        item = dict(signal)
        if "content" in item:
            item["content"] = redact_content(item["content"])
        redacted.append(item)
    return redacted


def episode_user_messages(value: Any) -> list[str]:
    """Return ordered user-message content from a canonical episode."""
    if not isinstance(value, Mapping):
        return []
    events = value.get("events")
    if not isinstance(events, list):
        return []
    return [
        str(event["content"]).strip()
        for event in events
        if isinstance(event, Mapping)
        and event.get("type") == "message"
        and event.get("role") == "user"
        and event.get("content")
    ]


def record_user_messages(row: Mapping[str, Any]) -> list[str]:
    """Return the user-authored intent stream in chronological order."""
    episode_messages = episode_user_messages(row.get("episode"))
    if episode_messages:
        return episode_messages

    messages: list[str] = []
    context = row.get("conversation_context")
    if isinstance(context, list):
        messages.extend(
            str(message["content"]).strip()
            for message in context
            if isinstance(message, Mapping)
            and message.get("role") == "user"
            and message.get("content")
        )
    user_input = str(row.get("user_input") or "").strip()
    if user_input:
        messages.append(user_input)
    return messages


def canonical_user_intent_text(row: Mapping[str, Any]) -> str:
    """Build embedding text from only the record's ordered user messages."""
    return "\n".join(record_user_messages(row))


def episode_tool_names(value: Any) -> list[str]:
    """Return sorted unique tool names observed in a canonical episode."""
    if not isinstance(value, Mapping):
        return []
    events = value.get("events")
    if not isinstance(events, list):
        return []
    return sorted(
        {
            str(event["name"])
            for event in events
            if isinstance(event, Mapping)
            and event.get("type") == "tool_call"
            and event.get("name")
        }
    )


def _validate_messages(value: Any, location: str) -> None:
    if not isinstance(value, list):
        raise ValueError(
            f"{location}: 'conversation_context' must be an array"
        )
    for index, message in enumerate(value):
        field = f"conversation_context[{index}]"
        if not isinstance(message, Mapping):
            raise ValueError(f"{location}: '{field}' must be an object")
        for name in ("role", "content"):
            if name not in message:
                raise ValueError(f"{location}: '{field}.{name}' is required")
            _require_nonempty_string(message[name], location, f"{field}.{name}")


def _validate_tool_calls(value: Any, location: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{location}: 'tool_calls' must be an array")
    for index, call in enumerate(value):
        field = f"tool_calls[{index}]"
        if not isinstance(call, Mapping):
            raise ValueError(f"{location}: '{field}' must be an object")
        if "name" not in call:
            raise ValueError(f"{location}: '{field}.name' is required")
        _require_nonempty_string(call["name"], location, f"{field}.name")
        if "arguments" not in call or not isinstance(call["arguments"], Mapping):
            raise ValueError(
                f"{location}: '{field}.arguments' must be an object"
            )
        if "error" in call and call["error"] is not None and not isinstance(
            call["error"], str
        ):
            raise ValueError(
                f"{location}: '{field}.error' must be a string or null"
            )


def _validate_episode(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{location}: 'episode' must be an object")
    events = value.get("events")
    if not isinstance(events, list):
        raise ValueError(f"{location}: 'episode.events' must be an array")
    if not events:
        raise ValueError(f"{location}: 'episode.events' must not be empty")
    for field in ("episode_id", "termination_reason"):
        if field in value:
            _require_nonempty_string(value[field], location, f"episode.{field}")

    previous_sequence = -1
    pending_calls: set[str] = set()
    completed_calls: set[str] = set()
    for index, event in enumerate(events):
        field = f"episode.events[{index}]"
        if not isinstance(event, Mapping):
            raise ValueError(f"{location}: '{field}' must be an object")
        sequence = event.get("sequence")
        if (
            not isinstance(sequence, int)
            or isinstance(sequence, bool)
            or sequence < 0
        ):
            raise ValueError(
                f"{location}: '{field}.sequence' must be a non-negative integer"
            )
        if sequence <= previous_sequence:
            raise ValueError(
                f"{location}: '{field}.sequence' must be strictly increasing"
            )
        previous_sequence = sequence

        event_type = event.get("type")
        if event_type not in EPISODE_EVENT_TYPES:
            allowed = ", ".join(sorted(EPISODE_EVENT_TYPES))
            raise ValueError(
                f"{location}: '{field}.type' must be one of: {allowed}"
            )
        if event_type == "message":
            for name in ("role", "content"):
                if name not in event:
                    raise ValueError(
                        f"{location}: '{field}.{name}' is required"
                    )
                _require_nonempty_string(
                    event[name],
                    location,
                    f"{field}.{name}",
                )
            continue

        if "call_id" not in event:
            raise ValueError(f"{location}: '{field}.call_id' is required")
        _require_nonempty_string(
            event["call_id"],
            location,
            f"{field}.call_id",
        )
        call_id = str(event["call_id"])
        if event_type == "tool_call":
            if call_id in pending_calls or call_id in completed_calls:
                raise ValueError(
                    f"{location}: '{field}.call_id' duplicates '{call_id}'"
                )
            if "name" not in event:
                raise ValueError(f"{location}: '{field}.name' is required")
            _require_nonempty_string(
                event["name"],
                location,
                f"{field}.name",
            )
            if "arguments" not in event or not isinstance(
                event["arguments"], Mapping
            ):
                raise ValueError(
                    f"{location}: '{field}.arguments' must be an object"
                )
            pending_calls.add(call_id)
            continue

        if call_id not in pending_calls:
            raise ValueError(
                f"{location}: '{field}.call_id' must reference a prior tool call"
            )
        if call_id in completed_calls:
            raise ValueError(
                f"{location}: '{field}.call_id' already has a result"
            )
        if "result" not in event and "error" not in event:
            raise ValueError(
                f"{location}: '{field}' requires 'result' or 'error'"
            )
        if (
            "error" in event
            and event["error"] is not None
            and not isinstance(event["error"], str)
        ):
            raise ValueError(
                f"{location}: '{field}.error' must be a string or null"
            )
        completed_calls.add(call_id)


def _validate_feedback(value: Any, location: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{location}: labeled records require a 'feedback' object")
    for field in ("polarity", "rationale"):
        if field not in value:
            raise ValueError(f"{location}: 'feedback.{field}' is required")
    if value["polarity"] not in FEEDBACK_POLARITIES:
        allowed = ", ".join(sorted(FEEDBACK_POLARITIES))
        raise ValueError(
            f"{location}: 'feedback.polarity' must be one of: {allowed}"
        )
    if not isinstance(value["rationale"], str):
        raise ValueError(f"{location}: 'feedback.rationale' must be a string")
    if "source" in value:
        _require_nonempty_string(value["source"], location, "feedback.source")
    if "correctness_signals" in value:
        _validate_correctness_signals(
            value["correctness_signals"],
            location,
        )


def _validate_correctness_signals(value: Any, location: str) -> None:
    field = "feedback.correctness_signals"
    if not isinstance(value, list):
        raise ValueError(f"{location}: '{field}' must be an array")
    allowed_fields = set(CORRECTNESS_SIGNAL_REQUIRED_FIELDS) | set(
        CORRECTNESS_SIGNAL_OPTIONAL_FIELDS
    )
    for index, signal in enumerate(value):
        item_field = f"{field}[{index}]"
        if not isinstance(signal, Mapping):
            raise ValueError(f"{location}: '{item_field}' must be an object")
        for name in CORRECTNESS_SIGNAL_REQUIRED_FIELDS:
            if name not in signal:
                raise ValueError(
                    f"{location}: '{item_field}.{name}' is required"
                )
        unexpected_fields = sorted(set(signal) - allowed_fields)
        if unexpected_fields:
            unexpected = ", ".join(str(name) for name in unexpected_fields)
            raise ValueError(
                f"{location}: '{item_field}' has unsupported field(s): "
                f"{unexpected}"
            )
        if (
            not isinstance(signal["kind"], str)
            or signal["kind"] not in CORRECTNESS_SIGNAL_KINDS
        ):
            allowed = ", ".join(sorted(CORRECTNESS_SIGNAL_KINDS))
            raise ValueError(
                f"{location}: '{item_field}.kind' must be one of: {allowed}"
            )
        _require_nonempty_string(
            signal["check_id"],
            location,
            f"{item_field}.check_id",
        )
        if not isinstance(signal["passed"], bool):
            raise ValueError(
                f"{location}: '{item_field}.passed' must be a boolean"
            )


def _require_nonempty_string(value: Any, location: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location}: '{field}' must be a non-empty string")
