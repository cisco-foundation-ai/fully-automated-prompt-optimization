# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Redacted, bounded views of recorded episodes for model calls."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Mapping

from src.hephaestus.data_pipeline.config import TraceSettings
from src.hephaestus.data_pipeline.contract import effective_route

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

_IDENTITY_FIELDS = frozenset({"schema_version", "record_id", "group_id", "request_id", "task_type", "route"})
_MAX_DEPTH = 4
_MAX_KEYS = 30
_MAX_ITEMS = 20
_MAX_TEXT = 500
_NOTHING = object()


def redact_record(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Replace email and IPv4 addresses in every string and key except identity fields."""
    return {key: value if key in _IDENTITY_FIELDS else _redact(value) for key, value in row.items()}


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return IPV4_RE.sub("<ip_address>", EMAIL_RE.sub("<email>", value))
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, Mapping):
        return {_redact(key): _redact(item) for key, item in value.items()}
    return value


def model_visible_context(row: Mapping[str, Any]) -> Dict[str, str]:
    """Return the case ``context`` a chain replays: messages, tools, runtime."""
    messages = [*row["conversation_context"], {"role": "user", "content": row["user_input"]}]
    return {
        "messages_json": json.dumps(messages, sort_keys=True),
        "tool_context_json": json.dumps(row["tool_calls"], sort_keys=True),
        "runtime_json": json.dumps(row["runtime"], sort_keys=True),
    }


def episode_view(row: Mapping[str, Any], settings: TraceSettings) -> Dict[str, Any]:
    """Return the episode as the model sees it, without feedback."""
    return {
        "record_id": str(row["record_id"]),
        "route": effective_route(row),
        "task_type": str(row["task_type"]),
        "transcript": transcript(row, settings),
        "runtime": compact_value(row.get("runtime") or {}),
    }


def transcript(row: Mapping[str, Any], settings: TraceSettings) -> List[Dict[str, Any]]:
    """Return messages and tool calls in order, with bounded tool data.

    Uses ``episode.events`` when present, preceded by the prior conversation
    and user input if the events hold no user message. Otherwise the order is
    the prior conversation, the user input, the recorded tool calls, then the
    final assistant output.
    """
    entries: List[Dict[str, Any]] = []
    episode = row.get("episode")
    if isinstance(episode, Mapping) and isinstance(episode.get("events"), list):
        events = episode["events"]
        if not any(event.get("type") == "message" and event.get("role") == "user" for event in events):
            entries.extend(_request_messages(row))
        calls: Dict[str, Dict[str, Any]] = {}
        for event in events:
            kind = event.get("type")
            if kind == "message":
                entries.append({"role": event["role"], "content": event["content"]})
            elif kind == "tool_call":
                entry = _tool_entry(event)
                calls[str(event["call_id"])] = entry
                entries.append(entry)
            elif kind == "tool_result" and str(event.get("call_id")) in calls:
                _record_outcome(calls[str(event["call_id"])], event, settings)
    else:
        entries.extend(_request_messages(row))
        for call in row["tool_calls"]:
            entry = _tool_entry(call)
            _record_outcome(entry, call, settings)
            entries.append(entry)
    final = row.get("assistant_output")
    if final and not (
        entries and entries[-1].get("role") == "assistant" and entries[-1].get("content") == final
    ):
        entries.append({"role": "assistant", "content": final})
    return entries


def _request_messages(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    messages = [{"role": m["role"], "content": m["content"]} for m in row["conversation_context"]]
    return [*messages, {"role": "user", "content": row["user_input"]}]


def _tool_entry(call: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "tool": str(call.get("name") or ""),
        "arguments": compact_value(call.get("arguments")),
        "outcome": "not_recorded",
    }


def _record_outcome(entry: Dict[str, Any], source: Mapping[str, Any], settings: TraceSettings) -> None:
    if source.get("error") is not None:
        entry["outcome"] = "error_returned"
        entry["error"] = compact_value(source["error"])
    elif "result" in source:
        entry["outcome"] = "result_returned"
        entry["result"] = compact_result(source["result"], settings)


def compact_value(value: Any, depth: int = 0) -> Any:
    """Bound depth, width, and string length; parse JSON-encoded strings."""
    if depth > _MAX_DEPTH:
        return "<nested>"
    if isinstance(value, str):
        parsed = _parse_json(value)
        if parsed is not None:
            return compact_value(parsed, depth + 1)
        text = value.strip()
        return text if len(text) <= _MAX_TEXT else text[: _MAX_TEXT - 3] + "..."
    if isinstance(value, Mapping):
        return {str(key): compact_value(item, depth + 1) for key, item in list(value.items())[:_MAX_KEYS]}
    if isinstance(value, list):
        return [compact_value(item, depth + 1) for item in value[:_MAX_ITEMS]]
    return value


def compact_result(value: Any, settings: TraceSettings) -> Any:
    """Compact a tool result, applying the tenant's key filters at every depth.

    ``drop_keys`` are removed wherever they appear. With ``result_keys``, an
    object key that matches keeps its whole value, and a key that does not
    match keeps only the matches nested inside it. Values that are not inside
    any object are kept. Key matching ignores case.
    """
    if not settings.result_keys and not settings.drop_keys:
        return compact_value(value)
    keep = re.compile(settings.result_keys, re.I) if settings.result_keys else None
    dropped = {key.lower() for key in settings.drop_keys}

    def walk(item: Any, depth: int, state: str) -> Any:
        # state: "top" (not inside an object), "keep" (inside a matched key),
        # or "search" (inside an unmatched key, where only nested matches survive).
        if isinstance(item, str):
            parsed = _parse_json(item)
            if parsed is not None:
                return walk(parsed, depth + 1, state)
            return _NOTHING if state == "search" else compact_value(item, depth)
        if depth > _MAX_DEPTH:
            return _NOTHING if state == "search" else "<nested>"
        if isinstance(item, Mapping):
            output: Dict[str, Any] = {}
            for key, nested in item.items():
                name = str(key)
                if name.lower() in dropped:
                    continue
                matched = state == "keep" or keep is None or keep.search(name)
                kept = walk(nested, depth + 1, "keep" if matched else "search")
                if kept is not _NOTHING:
                    output[name] = kept
                if len(output) >= _MAX_KEYS:
                    break
            return _NOTHING if state == "search" and not output else output
        if isinstance(item, list):
            items = [walk(nested, depth + 1, state) for nested in item[:_MAX_ITEMS]]
            items = [kept for kept in items if kept is not _NOTHING]
            return _NOTHING if state == "search" and not items else items
        return _NOTHING if state == "search" else item

    return walk(value, 0, "top")


def _parse_json(text: str) -> Any:
    stripped = text.strip()
    if not stripped.startswith(("{", "[")):
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None
