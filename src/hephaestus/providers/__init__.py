# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
from typing import Any, Dict, Mapping

from .base import ProviderClient
from .baseten import (
    DEFAULT_BASE_URL as BASETEN_DEFAULT_BASE_URL,
)
from .baseten import (
    DEFAULT_MAX_RETRIES as BASETEN_DEFAULT_MAX_RETRIES,
)
from .baseten import (
    DEFAULT_MODEL as BASETEN_DEFAULT_MODEL,
)
from .baseten import (
    DEFAULT_RETRY_BACKOFF_SECONDS as BASETEN_DEFAULT_RETRY_BACKOFF_SECONDS,
)
from .baseten import (
    DEFAULT_TIMEOUT_SECONDS as BASETEN_DEFAULT_TIMEOUT_SECONDS,
)
from .baseten import (
    build_baseten_client,
)
from .openai import (
    DEFAULT_MAX_RETRIES as OPENAI_DEFAULT_MAX_RETRIES,
)
from .openai import (
    DEFAULT_MODEL as OPENAI_DEFAULT_MODEL,
)
from .openai import (
    DEFAULT_RETRY_BACKOFF_SECONDS as OPENAI_DEFAULT_RETRY_BACKOFF_SECONDS,
)
from .openai import (
    DEFAULT_TIMEOUT_SECONDS as OPENAI_DEFAULT_TIMEOUT_SECONDS,
)
from .openai import (
    build_openai_client,
)
from .sagemaker import (
    DEFAULT_API_KEY_ENV as SAGEMAKER_DEFAULT_API_KEY_ENV,
)
from .sagemaker import (
    DEFAULT_API_URL as SAGEMAKER_DEFAULT_API_URL,
)
from .sagemaker import (
    DEFAULT_MAX_RETRIES as SAGEMAKER_DEFAULT_MAX_RETRIES,
)
from .sagemaker import (
    DEFAULT_RETRY_BACKOFF_SECONDS as SAGEMAKER_DEFAULT_RETRY_BACKOFF_SECONDS,
)
from .sagemaker import (
    DEFAULT_TIMEOUT_SECONDS as SAGEMAKER_DEFAULT_TIMEOUT_SECONDS,
)
from .sagemaker import (
    build_sagemaker_client,
)


def _canonical_provider(provider_name: str) -> str:
    provider = provider_name.strip().lower()
    if provider in {"baseten", "base10"}:
        return "baseten"
    if provider in {"sagemaker", "openai"}:
        return provider
    raise ValueError(f"Unsupported provider '{provider_name}'")


def resolve_provider_settings(
    provider_name: str,
    settings: Mapping[str, object],
) -> Dict[str, object]:
    """Resolve provider defaults once for both construction and provenance.

    Unknown keys are deliberately omitted. In particular, callers cannot cause
    credentials or arbitrary provider metadata to enter a persisted resolved
    configuration merely by placing them in ``provider_settings``.
    """

    provider = _canonical_provider(provider_name)
    if provider == "baseten":
        return {
            "base_url": str(settings.get("base_url", BASETEN_DEFAULT_BASE_URL)),
            "model": str(settings.get("model", BASETEN_DEFAULT_MODEL)),
            "timeout_seconds": int(
                settings.get("timeout_seconds", BASETEN_DEFAULT_TIMEOUT_SECONDS)
            ),
            "max_retries": int(settings.get("max_retries", BASETEN_DEFAULT_MAX_RETRIES)),
            "retry_backoff_seconds": int(
                settings.get(
                    "retry_backoff_seconds",
                    BASETEN_DEFAULT_RETRY_BACKOFF_SECONDS,
                )
            ),
            "temperature": float(settings.get("temperature", 0.0)),
            "top_p": float(settings.get("top_p", 0.95)),
            "max_tokens": int(settings.get("max_tokens", 16000)),
        }
    if provider == "sagemaker":
        return {
            "api_url": str(settings.get("api_url", SAGEMAKER_DEFAULT_API_URL)),
            "api_key_env": str(
                settings.get("api_key_env", SAGEMAKER_DEFAULT_API_KEY_ENV)
            ),
            "timeout_seconds": int(
                settings.get("timeout_seconds", SAGEMAKER_DEFAULT_TIMEOUT_SECONDS)
            ),
            "max_retries": int(
                settings.get("max_retries", SAGEMAKER_DEFAULT_MAX_RETRIES)
            ),
            "retry_backoff_seconds": int(
                settings.get(
                    "retry_backoff_seconds",
                    SAGEMAKER_DEFAULT_RETRY_BACKOFF_SECONDS,
                )
            ),
            "temperature": float(settings.get("temperature", 0.0)),
            "top_p": float(settings.get("top_p", 0.95)),
            "max_tokens": int(settings.get("max_tokens", 16000)),
        }
    return {
        "model": str(settings.get("model", OPENAI_DEFAULT_MODEL)),
        "timeout_seconds": int(
            settings.get("timeout_seconds", OPENAI_DEFAULT_TIMEOUT_SECONDS)
        ),
        "max_retries": int(settings.get("max_retries", OPENAI_DEFAULT_MAX_RETRIES)),
        "retry_backoff_seconds": int(
            settings.get(
                "retry_backoff_seconds",
                OPENAI_DEFAULT_RETRY_BACKOFF_SECONDS,
            )
        ),
        "temperature": float(settings.get("temperature", 0.0)),
        "top_p": (
            float(settings["top_p"])
            if settings.get("top_p") is not None
            else None
        ),
        "max_tokens": int(settings.get("max_tokens", 16000)),
    }


def _unavailable() -> Dict[str, str]:
    return {"status": "unavailable"}


def _fingerprinted(value: str) -> Dict[str, str]:
    return {
        "status": "fingerprinted",
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
    }


def safe_provider_facts(
    provider_name: str,
    resolved_settings: Mapping[str, object],
) -> Dict[str, Any]:
    """Return an allowlisted, credential-free provider provenance projection."""

    provider = _canonical_provider(provider_name)
    endpoint_key = "api_url" if provider == "sagemaker" else "base_url"
    endpoint = resolved_settings.get(endpoint_key)
    if isinstance(endpoint, str):
        endpoint_fact: Dict[str, str] = _fingerprinted(endpoint)
    else:
        endpoint_fact = _unavailable()

    model = resolved_settings.get("model")
    model_fact: object = model if isinstance(model, str) and model else _unavailable()
    credential_env_names = {
        "baseten": ["BASETEN_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "sagemaker": [
            str(resolved_settings.get("api_key_env", SAGEMAKER_DEFAULT_API_KEY_ENV))
        ],
    }[provider]
    return {
        "provider": provider,
        "model": model_fact,
        "sampling": {
            "temperature": resolved_settings.get("temperature"),
            "top_p": resolved_settings.get("top_p"),
            "max_tokens": resolved_settings.get("max_tokens"),
        },
        "limits": {
            "timeout_seconds": resolved_settings.get("timeout_seconds"),
            "max_retries": resolved_settings.get("max_retries"),
            "retry_backoff_seconds": resolved_settings.get("retry_backoff_seconds"),
        },
        "credential_env_names": credential_env_names,
        "endpoint": endpoint_fact,
        "provider_revision": _unavailable(),
        "model_revision": _unavailable(),
        "api_revision": _unavailable(),
        "provider_request_id": _unavailable(),
        "provider_response_id": _unavailable(),
    }


def build_provider_client(provider_name: str, settings: Dict[str, object]) -> ProviderClient:
    provider = _canonical_provider(provider_name)
    resolved = resolve_provider_settings(provider, settings)
    if provider == "baseten":
        return build_baseten_client(resolved)
    if provider == "sagemaker":
        return build_sagemaker_client(resolved)
    if provider == "openai":
        return build_openai_client(resolved)
    raise AssertionError(f"unreachable provider: {provider}")
