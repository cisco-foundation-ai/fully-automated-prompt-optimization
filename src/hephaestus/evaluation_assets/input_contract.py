# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Vendor-neutral input contract for the evaluation asset pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

SCHEMA_VERSION = "fapo-evaluation-input-v1"
FEEDBACK_POLARITIES = frozenset({"positive", "negative", "mixed"})

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


def validate_input_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    labeled: bool,
    path: Path,
) -> None:
    """Validate canonical records and raise one precise contract error."""
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=1):
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
        "optional_fields": ["request_id", "route", "assistant_output"],
        "labeled_required_fields": ["assistant_output", "feedback"],
        "feedback": {
            "required": ["polarity", "rationale"],
            "types": {"polarity": "string", "rationale": "string"},
            "optional": ["correction", "source"],
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
        "notes": [
            "group_id is required for leakage-safe dataset splitting",
            "route defaults to task_type when omitted",
            "request_id defaults to record_id when omitted",
            "unlabeled records must not contain feedback",
        ],
    }


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


def _require_nonempty_string(value: Any, location: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location}: '{field}' must be a non-empty string")
