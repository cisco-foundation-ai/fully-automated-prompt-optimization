# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.hephaestus.datasets.rubric_providers import (
    DEFAULT_OPENAI_RUBRIC_MODEL,
    OpenAIRubricProvider,
)


def test_openai_rubric_provider_defaults_to_gpt_5_5_and_json_mode() -> None:
    completions = _DummyCompletions()
    provider = OpenAIRubricProvider(client=_DummyClient(completions), sleep_fn=lambda _: None)

    result = provider.generate_json("return json", {"task": "extract_feedback_rubric"})

    assert result == {"ok": True}
    assert provider.model == DEFAULT_OPENAI_RUBRIC_MODEL == "gpt-5.5"
    assert completions.called_with["model"] == "gpt-5.5"
    assert completions.called_with["response_format"] == {"type": "json_object"}
    assert completions.called_with["max_completion_tokens"] == 4096
    assert "temperature" not in completions.called_with
    assert "max_tokens" not in completions.called_with


def test_openai_rubric_metadata_drains_allowlisted_success_facts() -> None:
    """Successful rubric calls expose only allowlisted transport metadata once."""
    response = SimpleNamespace(
        id="response-1",
        _request_id="request-1",
        model="gpt-revision",
        system_fingerprint="fingerprint-1",
        usage=SimpleNamespace(
            prompt_tokens=3,
            completion_tokens=4,
            total_tokens=7,
            secret="sk-not-persisted",
        ),
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        headers={"authorization": "sk-not-persisted"},
    )
    create = MagicMock(side_effect=[RuntimeError("retry canary"), response])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    provider = OpenAIRubricProvider(
        client=client,
        max_retries=1,
        retry_backoff_seconds=0,
    )

    assert provider.generate_json("system canary", {"secret": "request canary"}) == {
        "ok": True
    }
    assert provider.drain_call_metadata() == [
        {
            "transport_ordinal": 1,
            "response_id": "response-1",
            "request_id": "request-1",
            "model": "gpt-revision",
            "system_fingerprint": "fingerprint-1",
            "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            "retry_count": 1,
        }
    ]
    assert provider.drain_call_metadata() == []


def test_rubric_metadata_drain_returns_nested_defensive_copy() -> None:
    """Caller mutation cannot alter the nested provider metadata record."""
    provider = OpenAIRubricProvider(client=object())
    buffered = {"transport_ordinal": 1, "usage": {"input_tokens": 3}}
    provider._call_metadata = [buffered]

    drained = provider.drain_call_metadata()
    drained[0]["usage"]["input_tokens"] = 999

    assert buffered["usage"]["input_tokens"] == 3


class _DummyCompletions:
    def __init__(self) -> None:
        self.called_with = {}

    def create(self, **kwargs):
        self.called_with = kwargs
        message = SimpleNamespace(content='{"ok": true}')
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class _DummyChat:
    def __init__(self, completions: _DummyCompletions) -> None:
        self.completions = completions


class _DummyClient:
    def __init__(self, completions: _DummyCompletions) -> None:
        self.chat = _DummyChat(completions)
