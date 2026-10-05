# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Privacy-safe persisted identities for per-case execution failures."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal, TypedDict, cast

ExecutionPhase = Literal["chain", "scorer", "mcp"]
ExecutionErrorCategory = Literal[
    "timeout",
    "connection",
    "permission",
    "invalid_response",
    "runtime",
]


class ExecutionError(TypedDict):
    """Allowlisted error identity safe to persist in a run result."""

    phase: ExecutionPhase
    category: ExecutionErrorCategory
    summary: str


_PHASES = frozenset({"chain", "scorer", "mcp"})
_CATEGORIES = frozenset(
    {"timeout", "connection", "permission", "invalid_response", "runtime"}
)
_SUMMARIES: dict[str, dict[str, str]] = {
    "chain": {
        "timeout": "Chain execution timed out.",
        "connection": "Chain dependency connection failed.",
        "permission": "Chain execution was denied.",
        "invalid_response": "Chain returned an invalid response.",
        "runtime": "Chain execution failed.",
    },
    "scorer": {
        "timeout": "Scorer execution timed out.",
        "connection": "Scorer dependency connection failed.",
        "permission": "Scorer execution was denied.",
        "invalid_response": "Scorer returned an invalid response.",
        "runtime": "Scorer execution failed.",
    },
    "mcp": {
        "timeout": "MCP startup timed out.",
        "connection": "MCP server connection failed.",
        "permission": "MCP startup was denied.",
        "invalid_response": "MCP server returned an invalid response.",
        "runtime": "MCP startup failed.",
    },
}

_TIMEOUT_NAMES = frozenset({"timeout", "timeouterror", "connecttimeout", "readtimeout"})
_CONNECTION_NAMES = frozenset(
    {
        "connectionerror",
        "connecterror",
        "networkerror",
        "serviceunavailable",
        "transporterror",
    }
)
_PERMISSION_NAMES = frozenset(
    {
        "accessdenied",
        "authenticationerror",
        "authorizationerror",
        "forbidden",
        "permissionerror",
        "unauthorized",
    }
)
_INVALID_RESPONSE_NAMES = frozenset(
    {
        "decodeerror",
        "jsondecodeerror",
        "parseerror",
        "protocolerror",
        "responseerror",
        "unicodeerror",
        "validationerror",
    }
)


def build_execution_error(phase: str, category: str) -> ExecutionError:
    """Build one fixed, allowlisted error record.

    Dynamic exception types and messages are deliberately excluded because they
    can contain credentials, protected examples, provider payloads, or paths.
    """
    if phase not in _PHASES:
        raise ValueError(f"unsupported execution error phase: {phase!r}")
    if category not in _CATEGORIES:
        raise ValueError(f"unsupported execution error category: {category!r}")
    return {
        "phase": cast(ExecutionPhase, phase),
        "category": cast(ExecutionErrorCategory, category),
        "summary": _SUMMARIES[phase][category],
    }


def sanitize_execution_error(exc: BaseException, *, phase: str) -> ExecutionError:
    """Classify an exception chain without persisting any dynamic exception data."""
    return build_execution_error(phase, _classify_exception_chain(exc))


def validate_execution_error(value: Mapping[str, object]) -> ExecutionError:
    """Validate and canonicalize an already-sanitized persisted error record."""
    if set(value) != {"phase", "category", "summary"}:
        raise ValueError("execution_error must contain only phase, category, and summary")
    phase = value.get("phase")
    category = value.get("category")
    summary = value.get("summary")
    if not isinstance(phase, str) or not isinstance(category, str):
        raise ValueError("execution_error phase and category must be strings")
    expected = build_execution_error(phase, category)
    if summary != expected["summary"]:
        raise ValueError("execution_error summary must match its fixed safe summary")
    return expected


def _classify_exception_chain(exc: BaseException) -> str:
    seen: set[int] = set()
    current: BaseException | None = exc
    categories: list[str] = []
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        categories.append(_classify_exception(current))
        current = current.__cause__ or current.__context__
    for category in ("timeout", "connection", "permission", "invalid_response"):
        if category in categories:
            return category
    return "runtime"


def _classify_exception(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    if isinstance(exc, TimeoutError) or name in _TIMEOUT_NAMES or "timeout" in name:
        return "timeout"
    if isinstance(exc, ConnectionError) or name in _CONNECTION_NAMES:
        return "connection"
    if isinstance(exc, PermissionError) or name in _PERMISSION_NAMES:
        return "permission"
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)) or name in _INVALID_RESPONSE_NAMES:
        return "invalid_response"
    return "runtime"
