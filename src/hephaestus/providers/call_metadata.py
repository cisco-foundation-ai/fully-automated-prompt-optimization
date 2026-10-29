# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Privacy-safe projection of provider SDK responses into call metadata.

Providers record one sanitized row per successful SDK call: response and
request IDs, model, system fingerprint, token usage, and retry count. Unknown
fields are discarded, and values that look like secrets are replaced by a
marker.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_SECRET = re.compile(r"(?i)(?:\bsk-[a-z0-9_-]+|bearer\s+|api[_-]?key)")


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "unavailable", "reason": reason}


def _not_applicable(reason: str) -> dict[str, str]:
    return {"status": "not_applicable", "reason": reason}


def sanitize_call_metadata(value: Any) -> list[dict[str, Any]]:
    """Validate provider transport metadata and discard every unknown field."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("provider call metadata must be a sequence")
    if not value:
        raise ValueError("provider call metadata must not be empty")
    rows: list[dict[str, Any]] = []
    for expected_ordinal, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            raise ValueError("provider call metadata row must be an object")
        ordinal = raw.get("transport_ordinal")
        if (
            not isinstance(ordinal, int)
            or isinstance(ordinal, bool)
            or ordinal != expected_ordinal
        ):
            raise ValueError("provider transport ordinals must be contiguous")
        usage = raw.get("usage")
        usage_row = usage if isinstance(usage, Mapping) else {}
        rows.append(
            {
                "transport_ordinal": expected_ordinal,
                "response_id": _metadata_string(raw, "response_id"),
                "request_id": _metadata_string(raw, "request_id"),
                "model": _metadata_string(raw, "model"),
                "system_fingerprint": _metadata_string(
                    raw,
                    "system_fingerprint",
                ),
                "usage": {
                    "input_tokens": _metadata_integer(usage_row, "input_tokens"),
                    "output_tokens": _metadata_integer(
                        usage_row,
                        "output_tokens",
                        not_applicable_when_missing=True,
                    ),
                    "total_tokens": _metadata_integer(usage_row, "total_tokens"),
                },
                "retry_count": _metadata_integer(raw, "retry_count"),
            }
        )
    return rows


def provider_response_metadata(
    response: Any,
    *,
    transport_ordinal: int,
    retry_count: int,
    output_tokens_not_applicable: bool,
) -> dict[str, Any]:
    """Project one SDK response into the optional metadata protocol."""
    if (
        not isinstance(transport_ordinal, int)
        or isinstance(transport_ordinal, bool)
        or transport_ordinal < 1
        or not isinstance(retry_count, int)
        or isinstance(retry_count, bool)
        or retry_count < 0
    ):
        raise ValueError("provider transport metadata ordinal or retry is invalid")
    usage = _value(response, "usage", None)
    prompt_tokens = _value(usage, "prompt_tokens", _value(usage, "input_tokens", None))
    completion_tokens = _value(
        usage,
        "completion_tokens",
        _value(usage, "output_tokens", None),
    )
    row = {
        "transport_ordinal": 1,
        "response_id": _value(response, "id", None),
        "request_id": _value(response, "_request_id", None),
        "model": _value(response, "model", None),
        "system_fingerprint": _value(response, "system_fingerprint", None),
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": _value(usage, "total_tokens", None),
        },
        "retry_count": retry_count,
    }
    sanitized = sanitize_call_metadata([row])[0]
    sanitized["transport_ordinal"] = transport_ordinal
    if output_tokens_not_applicable and completion_tokens is None:
        sanitized["usage"]["output_tokens"] = _not_applicable(
            "provider_does_not_expose_field"
        )
    return sanitized


def _metadata_string(value: Mapping[str, Any], field: str) -> Any:
    if field not in value or value[field] is None:
        return _unavailable("provider_does_not_expose_field")
    item = value[field]
    if (
        not isinstance(item, str)
        or not item
        or len(item) > 256
        or any(ord(character) < 32 for character in item)
        or _SECRET.search(item)
    ):
        return _unavailable("metadata_failed_validation")
    return item


def _metadata_integer(
    value: Mapping[str, Any],
    field: str,
    *,
    not_applicable_when_missing: bool = False,
) -> Any:
    if field not in value or value[field] is None:
        if not_applicable_when_missing:
            return _not_applicable("provider_does_not_expose_field")
        return _unavailable("provider_does_not_expose_field")
    item = value[field]
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        return _unavailable("metadata_failed_validation")
    return item


def _value(item: Any, key: str, default: Any) -> Any:
    if item is None:
        return default
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)
