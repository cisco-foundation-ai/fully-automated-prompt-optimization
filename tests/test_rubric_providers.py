# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from types import SimpleNamespace

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
