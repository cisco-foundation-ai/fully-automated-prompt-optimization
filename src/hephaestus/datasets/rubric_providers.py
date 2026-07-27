# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Rubric-generation providers for evaluation asset creation."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Mapping, Optional

DEFAULT_OPENAI_RUBRIC_MODEL = "gpt-5.5"
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 2
DEFAULT_MAX_OUTPUT_TOKENS = 4096


class OpenAIRubricProvider:
    """OpenAI JSON generator for rubric extraction and inferred-label rubrics."""

    def __init__(
        self,
        model: str = DEFAULT_OPENAI_RUBRIC_MODEL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_seconds: int = DEFAULT_RETRY_BACKOFF_SECONDS,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        client: Optional[Any] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.max_output_tokens = max_output_tokens
        self._client = client
        self._sleep_fn = sleep_fn

    def generate_json(
        self,
        system_prompt: str,
        payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Generate one JSON object from a system prompt and JSON payload."""
        client = self._get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(dict(payload), sort_keys=True)},
        ]
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.chat.completions.create(**self._completion_kwargs(messages))
                return _extract_json_object(_extract_response_text(response))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self.max_retries:
                    break
                self._sleep_fn(self.retry_backoff_seconds)
        raise RuntimeError("OpenAI rubric generation failed after retries") from last_error

    def _completion_kwargs(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        if _is_reasoning_model(self.model):
            kwargs["max_completion_tokens"] = self.max_output_tokens
        else:
            kwargs["max_tokens"] = self.max_output_tokens
            kwargs["temperature"] = 0.0
        return kwargs

    def _create_client(self) -> Any:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        # try:
        #     import truststore
        #     truststore.inject_into_ssl()
        # except ImportError:
        #     pass
        return OpenAI(
            api_key=api_key,
            timeout=self.timeout_seconds,
        )

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._create_client()
        return self._client


def _is_reasoning_model(model: str) -> bool:
    model_lower = model.lower()
    if any(model_lower.startswith(prefix) for prefix in ("o1", "o3", "o4")):
        return True
    return any(model_lower.startswith(prefix) for prefix in ("gpt-5", "gpt5"))


def _extract_response_text(response: Any) -> str:
    choices = _value(response, "choices", None)
    if isinstance(choices, list) and choices:
        message = _value(choices[0], "message", None)
        content = _value(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                else:
                    text = _value(item, "text", "")
                    if text:
                        parts.append(str(text))
            return "".join(parts)
    output_text = _value(response, "output_text", "")
    if output_text:
        return str(output_text)
    raise ValueError("OpenAI rubric response missing text content")


def _extract_json_object(text: str) -> Dict[str, Any]:
    cleaned = _strip_json_fence(text.strip())
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if match is None:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI rubric response must be a JSON object")
    return parsed


def _strip_json_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def _value(item: Any, key: str, default: Any) -> Any:
    if item is None:
        return default
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)
