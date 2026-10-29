# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Cached, validated JSON calls to the pipeline's model."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, TypeVar

from src.hephaestus.artifact_io import atomic_write_text

T = TypeVar("T")


class JsonGenerator(Protocol):
    """Provider interface: one JSON object per call."""

    def generate_json(self, system_prompt: str, payload: Mapping[str, Any]) -> Dict[str, Any]: ...


class StepError(RuntimeError):
    """The model kept returning output that failed validation."""


class JsonCalls:
    """Runs model calls with a disk cache, validation retries, and usage logging.

    The cache key is the SHA-256 of the model, system prompt, and payload. A
    rerun reuses every completed call; editing a prompt reruns only the calls
    that use it. Each worker thread gets its own provider from the factory.
    """

    def __init__(
        self,
        provider_factory: Callable[[], JsonGenerator],
        *,
        model: str,
        cache_dir: Path,
        calls_path: Path,
        max_attempts: int = 2,
    ) -> None:
        self._factory = provider_factory
        self._model = model
        self._cache_dir = cache_dir
        self._calls_path = calls_path
        self._max_attempts = max_attempts
        self._local = threading.local()
        self._lock = threading.Lock()
        self.stats: Dict[str, Dict[str, int]] = {}

    def call(
        self,
        step: str,
        system_prompt: str,
        payload: Mapping[str, Any],
        parse: Callable[[Dict[str, Any]], T],
    ) -> T:
        """Return ``parse`` applied to the model's response for ``payload``.

        Raises:
            StepError: If every attempt returned output that ``parse`` rejected.
        """
        key = _cache_key(self._model, system_prompt, payload)
        cached = self._cache_dir / f"{key}.json"
        if cached.is_file():
            try:
                result = parse(json.loads(cached.read_text(encoding="utf-8")))
            except (KeyError, TypeError, ValueError):
                pass
            else:
                self._count(step, cached=True)
                return result
        errors: List[str] = []
        for _ in range(self._max_attempts):
            request = dict(payload)
            if errors:
                request["previous_errors"] = list(errors)
            provider = self._provider()
            raw = provider.generate_json(system_prompt, request)
            try:
                if not isinstance(raw, dict):
                    raise ValueError("response must be a JSON object")
                result = parse(raw)
                text = json.dumps(raw, sort_keys=True, allow_nan=False)
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(str(exc))
                self._log(step, key, provider, rejected=str(exc))
                continue
            self._log(step, key, provider)
            atomic_write_text(cached, text + "\n")
            return result
        raise StepError(f"{step}: model output failed validation: {errors[-1]}")

    def _provider(self) -> JsonGenerator:
        provider = getattr(self._local, "provider", None)
        if provider is None:
            provider = self._local.provider = self._factory()
        return provider

    def _log(self, step: str, key: str, provider: Any, rejected: Optional[str] = None) -> None:
        drain = getattr(provider, "drain_call_metadata", None)
        rows = drain() if callable(drain) else []
        tokens = {"input_tokens": 0, "output_tokens": 0}
        for row in rows:
            usage = row.get("usage") or {}
            for name in tokens:
                if isinstance(usage.get(name), int):
                    tokens[name] += usage[name]
        record: Dict[str, Any] = {"step": step, "cache_key": key, "model": self._model, **tokens}
        if rejected is not None:
            record["rejected"] = rejected
        with self._lock:
            with self._calls_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        self._count(step, cached=False, **tokens)

    def _count(self, step: str, *, cached: bool, input_tokens: int = 0, output_tokens: int = 0) -> None:
        with self._lock:
            totals = self.stats.setdefault(
                step, {"calls": 0, "cached": 0, "input_tokens": 0, "output_tokens": 0}
            )
            totals["cached" if cached else "calls"] += 1
            totals["input_tokens"] += input_tokens
            totals["output_tokens"] += output_tokens


def _cache_key(model: str, system_prompt: str, payload: Mapping[str, Any]) -> str:
    material = json.dumps(
        {"model": model, "system_prompt": system_prompt, "payload": payload}, sort_keys=True
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
