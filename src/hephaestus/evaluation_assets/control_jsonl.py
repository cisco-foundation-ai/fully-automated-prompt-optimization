# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Strict, cycle-free JSONL parsing for durable control authority."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_strict_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    """Read strict standard-JSON object rows without skipping blank authority."""
    if not path.is_file():
        return []
    return parse_strict_jsonl_objects(path.read_bytes())


def parse_strict_jsonl_objects(raw: bytes) -> list[dict[str, Any]]:
    """Parse exact UTF-8 JSONL, rejecting blanks, duplicates, and constants."""
    text = raw.decode("utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            raise ValueError("control log contains a blank row")
        value = json.loads(
            line,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("control log row is not an object")
        rows.append(value)
    return rows


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("control log contains a duplicate key")
        result[key] = value
    return result


def _reject_nonstandard_constant(value: str) -> Any:
    del value
    raise ValueError("control log contains a non-standard numeric constant")
