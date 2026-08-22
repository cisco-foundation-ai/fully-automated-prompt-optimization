# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Closed dependency identities for derived evaluation-asset generation."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

STAGE_SIX_DEPENDENCY_SCHEMA_VERSION = "fapo-stage-six-dependency-v1"
STAGE_SEVEN_DEPENDENCY_SCHEMA_VERSION = "fapo-stage-seven-dependency-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STAGE_SIX_FIELDS = frozenset(
    {
        "cluster",
        "match",
        "guideline",
        "source_members",
        "provider",
        "prompt",
        "algorithm_revision",
    }
)
_STAGE_SEVEN_FIELDS = frozenset(
    {
        "cluster",
        "rubric",
        "stage_six_dependency",
        "comparison_members",
        "provider",
        "prompt",
        "settings",
        "algorithm_revision",
    }
)


def build_stage_six_dependency(
    *,
    cluster: Mapping[str, Any],
    match: Mapping[str, Any],
    guideline: Mapping[str, Any],
    source_members: Sequence[Mapping[str, Any]],
    provider: Mapping[str, Any],
    prompt: Mapping[str, Any],
    algorithm_revision: str,
) -> dict[str, Any]:
    """Bind every Stage 6 provider-visible and reuse-relevant dependency."""
    descriptor = {
        "cluster": _json_copy(cluster),
        "match": _json_copy(match),
        "guideline": _json_copy(guideline),
        "source_members": _normalized_members(source_members),
        "provider": _json_copy(provider),
        "prompt": _json_copy(prompt),
        "algorithm_revision": _required_text(
            algorithm_revision,
            "algorithm_revision",
        ),
    }
    return _build_dependency(STAGE_SIX_DEPENDENCY_SCHEMA_VERSION, descriptor)


def build_stage_seven_dependency(
    *,
    cluster: Mapping[str, Any],
    rubric: Mapping[str, Any],
    stage_six_dependency: Mapping[str, Any],
    comparison_members: Sequence[Mapping[str, Any]],
    provider: Mapping[str, Any],
    prompt: Mapping[str, Any],
    settings: Mapping[str, Any],
    algorithm_revision: str,
) -> dict[str, Any]:
    """Bind Stage 7 generation plus its complete mechanical filter evidence."""
    if not _valid_dependency(
        stage_six_dependency,
        expected_schema=STAGE_SIX_DEPENDENCY_SCHEMA_VERSION,
    ):
        raise ValueError("stage_six_dependency is not an authentic dependency")
    descriptor = {
        "cluster": _json_copy(cluster),
        "rubric": _json_copy(rubric),
        "stage_six_dependency": _json_copy(stage_six_dependency),
        "comparison_members": _normalized_members(comparison_members),
        "provider": _json_copy(provider),
        "prompt": _json_copy(prompt),
        "settings": _json_copy(settings),
        "algorithm_revision": _required_text(
            algorithm_revision,
            "algorithm_revision",
        ),
    }
    return _build_dependency(STAGE_SEVEN_DEPENDENCY_SCHEMA_VERSION, descriptor)


def dependency_matches(
    persisted: Mapping[str, Any],
    current: Mapping[str, Any],
) -> bool:
    """Return true only for two authentic, byte-equivalent dependencies."""
    schema = current.get("schema_version")
    if schema not in {
        STAGE_SIX_DEPENDENCY_SCHEMA_VERSION,
        STAGE_SEVEN_DEPENDENCY_SCHEMA_VERSION,
    }:
        return False
    return (
        _valid_dependency(current, expected_schema=str(schema))
        and _valid_dependency(persisted, expected_schema=str(schema))
        and _canonical_bytes(persisted) == _canonical_bytes(current)
    )


def fingerprinted_members(
    rows: Sequence[Mapping[str, Any]],
    *,
    identity_key: str,
) -> list[dict[str, str]]:
    """Represent complete member content by a safe identity and canonical hash."""
    members: list[dict[str, str]] = []
    seen: set[str] = set()
    for position, row in enumerate(rows, start=1):
        identity = _required_text(row.get(identity_key), identity_key)
        if identity in seen:
            raise ValueError(
                f"duplicate {identity_key} {identity!r} at member {position}"
            )
        seen.add(identity)
        members.append(
            {
                "identity": identity,
                "content_sha256": hashlib.sha256(_canonical_bytes(row)).hexdigest(),
            }
        )
    return sorted(members, key=lambda item: item["identity"])


def _build_dependency(
    schema_version: str,
    descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema_version": schema_version,
        "descriptor": _json_copy(descriptor),
    }
    payload["dependency_sha256"] = hashlib.sha256(
        _canonical_bytes(payload)
    ).hexdigest()
    return payload


def _valid_dependency(
    payload: Mapping[str, Any],
    *,
    expected_schema: str,
) -> bool:
    if set(payload) != {"schema_version", "descriptor", "dependency_sha256"}:
        return False
    if payload.get("schema_version") != expected_schema:
        return False
    descriptor = payload.get("descriptor")
    if not isinstance(descriptor, Mapping):
        return False
    expected_fields = (
        _STAGE_SIX_FIELDS
        if expected_schema == STAGE_SIX_DEPENDENCY_SCHEMA_VERSION
        else _STAGE_SEVEN_FIELDS
    )
    if set(descriptor) != expected_fields:
        return False
    digest = payload.get("dependency_sha256")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        return False
    if expected_schema == STAGE_SEVEN_DEPENDENCY_SCHEMA_VERSION:
        nested = descriptor.get("stage_six_dependency")
        if not isinstance(nested, Mapping) or not _valid_dependency(
            nested,
            expected_schema=STAGE_SIX_DEPENDENCY_SCHEMA_VERSION,
        ):
            return False
    try:
        expected = hashlib.sha256(
            _canonical_bytes(
                {
                    "schema_version": expected_schema,
                    "descriptor": descriptor,
                }
            )
        ).hexdigest()
    except (TypeError, ValueError):
        return False
    return digest == expected


def _normalized_members(
    members: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for position, member in enumerate(members, start=1):
        if set(member) != {"identity", "content_sha256"}:
            raise ValueError(f"dependency member {position} has unexpected fields")
        identity = _required_text(member.get("identity"), "identity")
        digest = member.get("content_sha256")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ValueError(
                f"dependency member {identity!r} has invalid content_sha256"
            )
        if identity in seen:
            raise ValueError(f"duplicate dependency member identity {identity!r}")
        seen.add(identity)
        normalized.append({"identity": identity, "content_sha256": digest})
    return sorted(normalized, key=lambda item: item["identity"])


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _json_copy(value: Any) -> Any:
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
