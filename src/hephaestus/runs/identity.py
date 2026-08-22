# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Privacy-safe, deterministic identities for evaluation runs.

The identity separates facts that must remain fixed in a controlled comparison
from the dimensions that an evaluation explicitly declares as variants. Raw
configuration, prompt content, dataset content, credentials, environment
values, and arbitrary metadata are deliberately outside this serialization.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

RUN_IDENTITY_SCHEMA_VERSION = "fapo-run-identity-v1"

ALLOWED_VARIANT_DIMENSIONS = (
    "prompts",
    "skills",
    "chain_parameters",
    "chain_structure",
    "provider",
    "model",
    "sampling",
    "mcp_capabilities",
)

_PERMANENT_CONTROL_NAMES = ("dataset", "split", "scorer", "metric")
_RESOLVED_FACT_DIMENSIONS = frozenset({"provider", "model", "sampling", "mcp_capabilities"})
_SAMPLING_FACT_FIELDS = frozenset({"temperature", "top_p", "max_tokens", "seed", "reasoning_effort"})
_MCP_FACT_FIELDS = frozenset({"server_names", "tool_names", "supports_tool_calling"})
_CANONICAL_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_json_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 JSON representation of a JSON value."""

    def normalize(item: Any) -> Any:
        if item is None or isinstance(item, (str, bool, int, float)):
            return item
        if isinstance(item, Mapping):
            if not all(isinstance(key, str) for key in item):
                raise ValueError("value must have a canonical JSON representation")
            return {key: normalize(child) for key, child in item.items()}
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            return [normalize(child) for child in item]
        raise ValueError("value must have a canonical JSON representation")

    try:
        return json.dumps(
            normalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("value must have a canonical JSON representation") from exc


def fingerprint_value(value: Any) -> str:
    """Return a canonical, prefixed SHA-256 fingerprint for a JSON value."""
    return "sha256:" + hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _validate_fingerprint(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or _CANONICAL_SHA256.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical sha256 fingerprint")
    return value


def _fingerprint_fact(
    fingerprint: object,
    *,
    field_name: str,
    resolved: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if fingerprint is None:
        fact: dict[str, Any] = {"status": "unavailable"}
        if resolved is not None:
            if resolved["status"] != "unavailable":
                raise ValueError(f"resolved {field_name} is available while its fingerprint is unavailable")
            fact["resolved"] = resolved
        return fact

    fact = {
        "status": "available",
        "fingerprint": _validate_fingerprint(fingerprint, field_name=field_name),
    }
    if resolved is not None:
        fact["resolved"] = resolved
    return fact


def _safe_name_fact(value: object, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {"status": "unavailable"}
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or len(value) > 256
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(f"resolved {field_name} must be a non-empty safe identifier")
    return {"status": "available", "name": value}


def _safe_sampling_fact(value: object) -> dict[str, Any]:
    if value is None:
        return {"status": "unavailable"}
    if not isinstance(value, Mapping):
        raise ValueError("resolved sampling facts must be an object")

    unsupported = sorted(set(value) - _SAMPLING_FACT_FIELDS)
    if unsupported:
        raise ValueError(f"unsupported resolved sampling fields: {unsupported}")
    if not value:
        raise ValueError("resolved sampling facts must not be empty")

    normalized: dict[str, Any] = {"status": "available"}
    for name in sorted(value):
        item = value[name]
        if name in {"max_tokens", "seed"}:
            if item is not None and (not isinstance(item, int) or isinstance(item, bool)):
                raise ValueError(f"resolved sampling field {name!r} must be an integer or null")
        elif name in {"temperature", "top_p"}:
            if item is not None and (not isinstance(item, (int, float)) or isinstance(item, bool)):
                raise ValueError(f"resolved sampling field {name!r} must be numeric or null")
            if item is not None:
                _canonical_json_bytes(item)
        else:
            if item is not None and (
                not isinstance(item, str) or not item.strip() or item != item.strip() or len(item) > 128
            ):
                raise ValueError(
                    "resolved sampling field 'reasoning_effort' must be a safe " "identifier or null"
                )
        normalized[name] = item
    return normalized


def _safe_string_set(value: object, *, field_name: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"resolved MCP field {field_name!r} must be an array of names")
    names: list[str] = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            or len(item) > 256
            or any(ord(character) < 32 for character in item)
        ):
            raise ValueError(f"resolved MCP field {field_name!r} must contain safe names")
        names.append(item)
    if len(names) != len(set(names)):
        raise ValueError(f"resolved MCP field {field_name!r} contains duplicate names")
    return sorted(names)


def _safe_mcp_fact(value: object) -> dict[str, Any]:
    if value is None:
        return {"status": "unavailable"}
    if not isinstance(value, Mapping):
        raise ValueError("resolved MCP capabilities must be an object")

    unsupported = sorted(set(value) - _MCP_FACT_FIELDS)
    if unsupported:
        raise ValueError(f"unsupported resolved MCP fields: {unsupported}")
    if not value:
        raise ValueError("resolved MCP capabilities must not be empty")

    normalized: dict[str, Any] = {"status": "available"}
    for name in sorted(value):
        item = value[name]
        if name == "supports_tool_calling":
            if not isinstance(item, bool):
                raise ValueError("resolved MCP field 'supports_tool_calling' must be a boolean")
            normalized[name] = item
        else:
            normalized[name] = _safe_string_set(item, field_name=name)
    return normalized


def _validate_case_ids(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("ordered case IDs must be an array")
    case_ids: list[str] = []
    seen: set[str] = set()
    for case_id in value:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case IDs must be non-empty strings")
        if case_id in seen:
            raise ValueError(f"duplicate case_id {case_id!r} in run identity")
        case_ids.append(case_id)
        seen.add(case_id)
    return tuple(case_ids)


def _validate_dataset_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or len(value) > 4096
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("dataset_path must be a non-empty string")
    return value


def _case_control_fingerprints(case_ids: tuple[str, ...]) -> tuple[str, str]:
    ordered = fingerprint_value({"kind": "ordered_case_ids", "value": list(case_ids)})
    case_set = fingerprint_value({"kind": "case_id_set", "value": sorted(case_ids)})
    return ordered, case_set


def _validate_variant_dimensions(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("variant_dimensions must be an array")
    requested: list[str] = []
    seen: set[str] = set()
    for dimension in value:
        if not isinstance(dimension, str):
            raise ValueError("variant dimensions must be strings")
        if dimension in seen:
            raise ValueError(f"duplicate variant dimension {dimension!r}")
        requested.append(dimension)
        seen.add(dimension)

    unsupported = sorted(set(requested) - set(ALLOWED_VARIANT_DIMENSIONS))
    if unsupported:
        raise ValueError(f"unsupported variant dimensions: {unsupported}")
    return tuple(dimension for dimension in ALLOWED_VARIANT_DIMENSIONS if dimension in seen)


@dataclass(frozen=True)
class RunIdentity:
    """An immutable canonical evaluation identity.

    Instances are constructed with :func:`build_run_identity` or validated
    from serialized data with :meth:`from_dict`. The private canonical JSON
    representation prevents callers from mutating identity state after its
    fingerprint has been observed.
    """

    _core_json: str = field(repr=False)

    @property
    def schema_version(self) -> str:
        """Return the identity schema version."""
        return RUN_IDENTITY_SCHEMA_VERSION

    @property
    def fingerprint(self) -> str:
        """Return the fingerprint authenticating the complete identity."""
        return fingerprint_value(json.loads(self._core_json))

    @property
    def always_controls(self) -> dict[str, Any]:
        """Return a copy of the controls that can never be variants."""
        return dict(json.loads(self._core_json)["always_controls"])

    @property
    def control_dimensions(self) -> dict[str, Any]:
        """Return a copy of the undeclared dimensions held fixed."""
        return dict(json.loads(self._core_json)["control_dimensions"])

    @property
    def variants(self) -> dict[str, Any]:
        """Return a copy of the explicitly declared variant dimensions."""
        return dict(json.loads(self._core_json)["variants"])

    @property
    def declared_variant_dimensions(self) -> tuple[str, ...]:
        """Return the canonical tuple of declared dimensions."""
        return tuple(json.loads(self._core_json)["declared_variant_dimensions"])

    def to_dict(self) -> dict[str, Any]:
        """Serialize the identity with its authenticating fingerprint."""
        payload = json.loads(self._core_json)
        payload["identity_fingerprint"] = self.fingerprint
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RunIdentity:
        """Validate and load a serialized run identity."""
        return validate_run_identity_payload(payload)


def _identity_from_core(core: Mapping[str, Any]) -> RunIdentity:
    core_json = _canonical_json_bytes(core).decode("utf-8")
    return RunIdentity(_core_json=core_json)


def build_run_identity(
    *,
    ordered_case_ids: Sequence[str],
    dataset_path: str,
    dataset_fingerprint: str | None,
    split_fingerprint: str | None,
    scorer_fingerprint: str | None,
    metric_fingerprint: str | None,
    dimension_fingerprints: Mapping[str, str | None] | None = None,
    variant_dimensions: Sequence[str] = (),
    resolved_provider: str | None = None,
    resolved_model: str | None = None,
    resolved_sampling: Mapping[str, Any] | None = None,
    resolved_mcp_capabilities: Mapping[str, Any] | None = None,
) -> RunIdentity:
    """Build a run identity from fingerprints and safe resolved facts.

    Missing component fingerprints become explicit unavailable markers. A
    safe resolved fact is accepted only when the corresponding component
    fingerprint is available, preventing a human-readable label from being
    mistaken for reproducibility evidence.
    """
    case_ids = _validate_case_ids(ordered_case_ids)
    literal_dataset_path = _validate_dataset_path(dataset_path)
    declared = _validate_variant_dimensions(variant_dimensions)
    supplied_dimensions = dict(dimension_fingerprints or {})
    unsupported = sorted(set(supplied_dimensions) - set(ALLOWED_VARIANT_DIMENSIONS))
    if unsupported:
        raise ValueError(f"unsupported identity dimensions: {unsupported}")

    ordered_fingerprint, set_fingerprint = _case_control_fingerprints(case_ids)
    permanent_fingerprints = {
        "dataset": dataset_fingerprint,
        "split": split_fingerprint,
        "scorer": scorer_fingerprint,
        "metric": metric_fingerprint,
    }
    always_controls: dict[str, Any] = {
        "ordered_case_ids": list(case_ids),
        "ordered_case_ids_fingerprint": ordered_fingerprint,
        "case_id_set_fingerprint": set_fingerprint,
        "dataset_path": literal_dataset_path,
    }
    for name in _PERMANENT_CONTROL_NAMES:
        always_controls[name] = _fingerprint_fact(permanent_fingerprints[name], field_name=name)

    resolved_facts = {
        "provider": _safe_name_fact(resolved_provider, field_name="provider"),
        "model": _safe_name_fact(resolved_model, field_name="model"),
        "sampling": _safe_sampling_fact(resolved_sampling),
        "mcp_capabilities": _safe_mcp_fact(resolved_mcp_capabilities),
    }
    components: dict[str, dict[str, Any]] = {}
    for dimension in ALLOWED_VARIANT_DIMENSIONS:
        components[dimension] = _fingerprint_fact(
            supplied_dimensions.get(dimension),
            field_name=dimension,
            resolved=(resolved_facts[dimension] if dimension in _RESOLVED_FACT_DIMENSIONS else None),
        )

    declared_set = set(declared)
    core = {
        "schema_version": RUN_IDENTITY_SCHEMA_VERSION,
        "declared_variant_dimensions": list(declared),
        "always_controls": always_controls,
        "control_dimensions": {
            name: components[name] for name in ALLOWED_VARIANT_DIMENSIONS if name not in declared_set
        },
        "variants": {name: components[name] for name in declared},
    }
    return _identity_from_core(core)


def _require_exact_fields(
    value: object,
    *,
    expected: set[str],
    field_name: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{field_name} fields do not match schema; missing={missing}, extra={extra}")
    return value


def _validate_plain_fingerprint_fact(value: object, *, field_name: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    status = value.get("status")
    if status == "available":
        _require_exact_fields(
            value,
            expected={"status", "fingerprint"},
            field_name=field_name,
        )
        _validate_fingerprint(value["fingerprint"], field_name=field_name)
        return
    if status == "unavailable":
        _require_exact_fields(value, expected={"status"}, field_name=field_name)
        return
    raise ValueError(f"{field_name}.status must be 'available' or 'unavailable'")


def _validated_resolved_fact(dimension: str, value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"resolved {dimension} must be an object")
    status = value.get("status")
    if status == "unavailable":
        _require_exact_fields(
            value,
            expected={"status"},
            field_name=f"resolved {dimension}",
        )
        return {"status": "unavailable"}
    if status != "available":
        raise ValueError(f"resolved {dimension}.status must be 'available' or 'unavailable'")

    raw = dict(value)
    raw.pop("status")
    if dimension in {"provider", "model"}:
        unsupported = sorted(set(raw) - {"name"})
        if unsupported:
            raise ValueError(f"unsupported resolved {dimension} fields: {unsupported}")
        if set(raw) != {"name"}:
            raise ValueError(f"resolved {dimension} must include only name")
        return _safe_name_fact(raw["name"], field_name=dimension)
    if dimension == "sampling":
        return _safe_sampling_fact(raw)
    return _safe_mcp_fact(raw)


def _validate_dimension_fact(value: object, *, dimension: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"identity dimension {dimension} must be an object")
    resolved_dimension = dimension in _RESOLVED_FACT_DIMENSIONS
    status = value.get("status")
    expected = {"status", "resolved"} if resolved_dimension else {"status"}
    if status == "available":
        expected.add("fingerprint")
    elif status != "unavailable":
        raise ValueError(f"identity dimension {dimension}.status must be 'available' or 'unavailable'")
    _require_exact_fields(
        value,
        expected=expected,
        field_name=f"identity dimension {dimension}",
    )
    if status == "available":
        _validate_fingerprint(value["fingerprint"], field_name=dimension)
    if resolved_dimension:
        normalized = _validated_resolved_fact(dimension, value["resolved"])
        if dict(value["resolved"]) != normalized:
            raise ValueError(f"resolved {dimension} facts are not canonical")
        if status == "unavailable" and normalized["status"] != "unavailable":
            raise ValueError(f"resolved {dimension} is available while its fingerprint is unavailable")


def validate_run_identity_payload(payload: Mapping[str, Any]) -> RunIdentity:
    """Validate a serialized identity and return its immutable representation."""
    top = _require_exact_fields(
        payload,
        expected={
            "schema_version",
            "declared_variant_dimensions",
            "always_controls",
            "control_dimensions",
            "variants",
            "identity_fingerprint",
        },
        field_name="run identity",
    )
    if top["schema_version"] != RUN_IDENTITY_SCHEMA_VERSION:
        raise ValueError(f"unsupported run identity schema {top['schema_version']!r}")

    declared = _validate_variant_dimensions(top["declared_variant_dimensions"])
    if list(declared) != list(top["declared_variant_dimensions"]):
        raise ValueError("declared variant dimensions are not in canonical order")

    always = _require_exact_fields(
        top["always_controls"],
        expected={
            "ordered_case_ids",
            "ordered_case_ids_fingerprint",
            "case_id_set_fingerprint",
            "dataset_path",
            "dataset",
            "split",
            "scorer",
            "metric",
        },
        field_name="always_controls",
    )
    case_ids = _validate_case_ids(always["ordered_case_ids"])
    _validate_dataset_path(always["dataset_path"])
    expected_ordered, expected_set = _case_control_fingerprints(case_ids)
    _validate_fingerprint(
        always["ordered_case_ids_fingerprint"],
        field_name="ordered_case_ids_fingerprint",
    )
    _validate_fingerprint(always["case_id_set_fingerprint"], field_name="case_id_set_fingerprint")
    if always["ordered_case_ids_fingerprint"] != expected_ordered:
        raise ValueError("ordered_case_ids_fingerprint does not match ordered case IDs")
    if always["case_id_set_fingerprint"] != expected_set:
        raise ValueError("case_id_set_fingerprint does not match the case ID set")
    for name in _PERMANENT_CONTROL_NAMES:
        _validate_plain_fingerprint_fact(always[name], field_name=name)

    controls = top["control_dimensions"]
    variants = top["variants"]
    if not isinstance(controls, Mapping) or not isinstance(variants, Mapping):
        raise ValueError("control_dimensions and variants must be objects")
    declared_set = set(declared)
    if set(variants) != declared_set:
        raise ValueError("variant fields do not match declared variant dimensions")
    expected_controls = set(ALLOWED_VARIANT_DIMENSIONS) - declared_set
    if set(controls) != expected_controls:
        raise ValueError("control dimensions do not contain every undeclared dimension")
    for dimension in ALLOWED_VARIANT_DIMENSIONS:
        source = variants if dimension in declared_set else controls
        _validate_dimension_fact(source[dimension], dimension=dimension)

    supplied_fingerprint = _validate_fingerprint(
        top["identity_fingerprint"], field_name="identity_fingerprint"
    )
    core = {key: value for key, value in top.items() if key != "identity_fingerprint"}
    identity = _identity_from_core(core)
    if supplied_fingerprint != identity.fingerprint:
        raise ValueError("identity_fingerprint does not match the identity payload")
    return identity
