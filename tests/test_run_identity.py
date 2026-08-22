# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for privacy-safe, deterministic evaluation run identities."""

from __future__ import annotations

import copy
import json

import pytest

from src.hephaestus.runs.identity import (
    ALLOWED_VARIANT_DIMENSIONS,
    build_run_identity,
    fingerprint_value,
    validate_run_identity_payload,
)


def _dimension_fingerprints() -> dict[str, str]:
    """Return distinct literal component fingerprints."""
    return {name: f"sha256:{index:064x}" for index, name in enumerate(ALLOWED_VARIANT_DIMENSIONS, start=1)}


def _build_identity(**overrides: object):
    """Build one complete identity with literal, non-sensitive facts."""
    arguments: dict[str, object] = {
        "ordered_case_ids": ("case-b", "case-a"),
        "dataset_path": "datasets/releases/example/test.jsonl",
        "dataset_fingerprint": "sha256:" + "a" * 64,
        "split_fingerprint": "sha256:" + "b" * 64,
        "scorer_fingerprint": "sha256:" + "c" * 64,
        "metric_fingerprint": "sha256:" + "d" * 64,
        "dimension_fingerprints": _dimension_fingerprints(),
        "variant_dimensions": ("skills", "prompts"),
        "resolved_provider": "openai",
        "resolved_model": "gpt-example",
        "resolved_sampling": {
            "max_tokens": 4096,
            "temperature": 0.0,
            "top_p": 0.95,
        },
        "resolved_mcp_capabilities": {
            "server_names": ["retrieval"],
            "supports_tool_calling": True,
            "tool_names": ["lookup", "search"],
        },
    }
    arguments.update(overrides)
    return build_run_identity(**arguments)


def test_builder_separates_permanent_controls_from_declared_variants() -> None:
    """Declared dimensions are variants while every other dimension is controlled."""
    payload = _build_identity().to_dict()

    assert payload["schema_version"] == "fapo-run-identity-v1"
    assert payload["declared_variant_dimensions"] == ["prompts", "skills"]
    assert list(payload["variants"]) == ["prompts", "skills"]
    assert set(payload["control_dimensions"]) == set(ALLOWED_VARIANT_DIMENSIONS) - {"prompts", "skills"}
    assert set(payload["always_controls"]) == {
        "case_id_set_fingerprint",
        "dataset",
        "dataset_path",
        "metric",
        "ordered_case_ids",
        "ordered_case_ids_fingerprint",
        "scorer",
        "split",
    }
    assert payload["always_controls"]["ordered_case_ids"] == ["case-b", "case-a"]
    assert payload["always_controls"]["dataset_path"] == ("datasets/releases/example/test.jsonl")
    assert payload["always_controls"]["ordered_case_ids_fingerprint"] == (
        "sha256:2e0c2205181cc1690bb960a1398918ab2682c77a6d5e2b287ef746ca84329eff"
    )
    assert payload["always_controls"]["case_id_set_fingerprint"] == (
        "sha256:b141effbf110e78d6de66cc74098227a0d4e98f133504b1308312a095016de01"
    )


def test_safe_resolved_facts_stay_bound_to_their_dimensions() -> None:
    """Safe provider, model, sampling, and MCP facts are part of dimension identity."""
    payload = _build_identity(variant_dimensions=("model", "sampling")).to_dict()

    assert payload["control_dimensions"]["provider"]["resolved"] == {
        "status": "available",
        "name": "openai",
    }
    assert payload["variants"]["model"]["resolved"] == {
        "status": "available",
        "name": "gpt-example",
    }
    assert payload["variants"]["sampling"]["resolved"] == {
        "status": "available",
        "max_tokens": 4096,
        "temperature": 0.0,
        "top_p": 0.95,
    }
    assert payload["control_dimensions"]["mcp_capabilities"]["resolved"] == {
        "status": "available",
        "server_names": ["retrieval"],
        "supports_tool_calling": True,
        "tool_names": ["lookup", "search"],
    }


def test_order_and_set_case_fingerprints_encode_distinct_controls() -> None:
    """Reordering cases changes only the order-sensitive case control."""
    first = _build_identity().to_dict()["always_controls"]
    reversed_ids = _build_identity(ordered_case_ids=("case-a", "case-b")).to_dict()["always_controls"]

    assert first["ordered_case_ids_fingerprint"] != reversed_ids["ordered_case_ids_fingerprint"]
    assert reversed_ids["ordered_case_ids_fingerprint"] == (
        "sha256:2c14d9ffb6e2b8dbeeb263f268f919daf14fcdfc5c312869b980da9ed5a91262"
    )
    assert first["case_id_set_fingerprint"] == reversed_ids["case_id_set_fingerprint"]


def test_missing_component_facts_are_explicitly_unavailable() -> None:
    """Unknown component and resolved facts serialize as explicit markers."""
    payload = _build_identity(
        dimension_fingerprints={"prompts": "sha256:" + "1" * 64},
        variant_dimensions=("prompts", "model"),
        resolved_provider=None,
        resolved_model=None,
        resolved_sampling=None,
        resolved_mcp_capabilities=None,
    ).to_dict()

    assert payload["variants"]["model"] == {
        "status": "unavailable",
        "resolved": {"status": "unavailable"},
    }
    assert payload["control_dimensions"]["provider"] == {
        "status": "unavailable",
        "resolved": {"status": "unavailable"},
    }
    assert payload["control_dimensions"]["chain_structure"] == {"status": "unavailable"}


def test_unknown_or_duplicate_variant_declarations_are_rejected() -> None:
    """Only the eight explicit dimensions can be declared exactly once."""
    with pytest.raises(ValueError, match="unsupported variant dimensions.*model_alias"):
        _build_identity(variant_dimensions=("model_alias",))

    with pytest.raises(ValueError, match="duplicate variant dimension.*model"):
        _build_identity(variant_dimensions=("model", "model"))


def test_duplicate_or_invalid_case_ids_are_rejected() -> None:
    """Order/set controls cannot hide duplicate or malformed case identities."""
    with pytest.raises(ValueError, match="duplicate case_id.*case-a"):
        _build_identity(ordered_case_ids=("case-a", "case-a"))

    with pytest.raises(ValueError, match="case IDs must be non-empty strings"):
        _build_identity(ordered_case_ids=("case-a", " "))


def test_dataset_path_is_a_required_literal_control() -> None:
    """A run cannot replace its literal dataset path with an absent label."""
    with pytest.raises(ValueError, match="dataset_path must be a non-empty string"):
        _build_identity(dataset_path=" ")


def test_raw_provider_and_mcp_secret_fields_cannot_enter_resolved_facts() -> None:
    """Resolved projections reject arbitrary provider settings and MCP environments."""
    with pytest.raises(ValueError, match="unsupported resolved sampling fields.*api_key"):
        _build_identity(resolved_sampling={"temperature": 0.0, "api_key": "secret"})

    with pytest.raises(ValueError, match="unsupported resolved MCP fields.*env"):
        _build_identity(
            resolved_mcp_capabilities={
                "server_names": ["retrieval"],
                "tool_names": ["search"],
                "env": {"TOKEN": "secret"},
            }
        )


def test_resolved_fact_requires_a_component_fingerprint() -> None:
    """A resolved label cannot fabricate identity when its fingerprint is unknown."""
    dimensions = _dimension_fingerprints()
    dimensions["model"] = None  # type: ignore[assignment]

    with pytest.raises(ValueError, match="resolved model.*fingerprint is unavailable"):
        _build_identity(dimension_fingerprints=dimensions)


def test_identity_is_deterministic_across_mapping_and_declaration_order() -> None:
    """Equivalent inputs produce byte-equivalent payloads and fingerprints."""
    dimensions = _dimension_fingerprints()
    reverse_dimensions = dict(reversed(list(dimensions.items())))
    first = _build_identity(
        dimension_fingerprints=dimensions,
        variant_dimensions=("skills", "prompts"),
    ).to_dict()
    second = _build_identity(
        dimension_fingerprints=reverse_dimensions,
        variant_dimensions=("prompts", "skills"),
        resolved_sampling={"top_p": 0.95, "temperature": 0.0, "max_tokens": 4096},
        resolved_mcp_capabilities={
            "tool_names": ["search", "lookup"],
            "supports_tool_calling": True,
            "server_names": ["retrieval"],
        },
    ).to_dict()

    assert first == second
    assert first["identity_fingerprint"].startswith("sha256:")


def test_validation_round_trips_and_rejects_tampering() -> None:
    """Serialized identity validation authenticates every control and variant field."""
    payload = _build_identity().to_dict()
    restored = validate_run_identity_payload(json.loads(json.dumps(payload)))

    assert restored.to_dict() == payload

    tampered = copy.deepcopy(payload)
    tampered["always_controls"]["dataset"]["fingerprint"] = "sha256:" + "e" * 64
    with pytest.raises(ValueError, match="identity_fingerprint does not match"):
        validate_run_identity_payload(tampered)

    path_tampered = copy.deepcopy(payload)
    path_tampered["always_controls"]["dataset_path"] = "datasets/other/test.jsonl"
    with pytest.raises(ValueError, match="identity_fingerprint does not match"):
        validate_run_identity_payload(path_tampered)


def test_validation_rejects_noncanonical_or_extra_fields() -> None:
    """Malformed fingerprints and undeclared payload fields fail closed."""
    payload = _build_identity().to_dict()
    malformed = copy.deepcopy(payload)
    malformed["always_controls"]["dataset"]["fingerprint"] = "a" * 64
    with pytest.raises(ValueError, match="canonical sha256 fingerprint"):
        validate_run_identity_payload(malformed)

    extra = copy.deepcopy(payload)
    extra["control_dimensions"]["provider"]["resolved"]["api_key"] = "secret"
    with pytest.raises(ValueError, match="unsupported resolved provider fields.*api_key"):
        validate_run_identity_payload(extra)


def test_fingerprint_value_uses_canonical_json_and_rejects_non_json_numbers() -> None:
    """Canonical JSON hashing is stable and never accepts NaN payloads."""
    assert fingerprint_value({"b": 2, "a": 1}) == (
        "sha256:43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )
    assert fingerprint_value({"a": 1, "b": 2}) == fingerprint_value({"b": 2, "a": 1})

    with pytest.raises(ValueError, match="canonical JSON"):
        fingerprint_value({"score": float("nan")})

    with pytest.raises(ValueError, match="canonical JSON"):
        fingerprint_value({1: "integer key", "1": "string key"})
