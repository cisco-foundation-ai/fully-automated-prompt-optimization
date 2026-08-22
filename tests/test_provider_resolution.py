# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Resolved provider settings and privacy-safe provenance facts."""

from __future__ import annotations

import json

import src.hephaestus.providers as providers


def test_provider_builder_consumes_the_shared_resolved_defaults(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _capture(settings: dict[str, object]):
        captured.update(settings)
        return object()

    monkeypatch.setattr(providers, "build_openai_client", _capture)

    providers.build_provider_client("openai", {})

    assert captured == providers.resolve_provider_settings("openai", {})
    assert captured == {
        "model": "gpt-4o",
        "timeout_seconds": 300,
        "max_retries": 10,
        "retry_backoff_seconds": 5,
        "temperature": 0.0,
        "top_p": None,
        "max_tokens": 16000,
    }


def test_openai_resolved_defaults_are_idempotent_for_runner_construction(
    monkeypatch,
) -> None:
    """Runner-resolved OpenAI defaults can be consumed without coercing null top_p."""
    captured: dict[str, object] = {}

    def _capture(settings: dict[str, object]):
        captured.update(settings)
        return object()

    monkeypatch.setattr(providers, "build_openai_client", _capture)
    resolved = providers.resolve_provider_settings("openai", {})

    providers.build_provider_client("openai", resolved)

    assert captured == resolved
    assert captured["top_p"] is None


def test_safe_provider_facts_are_resolved_and_never_persist_secrets_or_endpoint() -> None:
    secret = "provider-secret-sentinel"
    endpoint = "https://private.example.invalid/invoke"
    resolved = providers.resolve_provider_settings(
        "sagemaker",
        {
            "api_url": endpoint,
            "api_key_env": "PRIVATE_PROVIDER_TOKEN",
            "api_key": secret,
            "temperature": 0.25,
        },
    )

    facts = providers.safe_provider_facts("sagemaker", resolved)
    serialized = json.dumps(facts, sort_keys=True)

    assert facts["provider"] == "sagemaker"
    assert facts["sampling"] == {
        "temperature": 0.25,
        "top_p": 0.95,
        "max_tokens": 16000,
    }
    assert facts["limits"] == {
        "timeout_seconds": 300,
        "max_retries": 10,
        "retry_backoff_seconds": 5,
    }
    assert facts["credential_env_names"] == ["PRIVATE_PROVIDER_TOKEN"]
    assert facts["endpoint"]["status"] == "fingerprinted"
    assert len(facts["endpoint"]["sha256"]) == 64
    assert facts["model"] == {"status": "unavailable"}
    assert facts["provider_revision"] == {"status": "unavailable"}
    assert facts["model_revision"] == {"status": "unavailable"}
    assert facts["api_revision"] == {"status": "unavailable"}
    assert facts["provider_request_id"] == {"status": "unavailable"}
    assert facts["provider_response_id"] == {"status": "unavailable"}
    assert secret not in serialized
    assert endpoint not in serialized


def test_baseten_alias_resolves_to_one_canonical_provider_identity() -> None:
    settings = {"model": "demo", "top_p": 0.4}

    assert providers.safe_provider_facts(
        "base10", providers.resolve_provider_settings("base10", settings)
    )["provider"] == "baseten"
