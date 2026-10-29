# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest

from src.hephaestus.data_pipeline.llm import JsonCalls, StepError


class _Replies:
    def __init__(self, replies: List[Any]) -> None:
        self.replies = list(replies)
        self.payloads: List[Dict[str, Any]] = []

    def generate_json(self, system_prompt: str, payload: Mapping[str, Any]) -> Any:
        self.payloads.append(dict(payload))
        return self.replies.pop(0)

    def drain_call_metadata(self) -> List[Dict[str, Any]]:
        return [{"usage": {"input_tokens": 10, "output_tokens": 4}}]


def _parse(raw: Dict[str, Any]) -> int:
    if not isinstance(raw.get("value"), int):
        raise ValueError("value must be an integer")
    return raw["value"]


def _calls(tmp_path: Path, provider: _Replies, model: str = "m") -> JsonCalls:
    return JsonCalls(
        lambda: provider, model=model, cache_dir=tmp_path / "cache", calls_path=tmp_path / "calls.jsonl"
    )


class TestJsonCalls:
    def test_caches_valid_responses(self, tmp_path: Path) -> None:
        """A repeated call with the same inputs is served from the cache."""
        provider = _Replies([{"value": 3}])

        assert _calls(tmp_path, provider).call("step", "prompt", {"a": 1}, _parse) == 3
        rerun = _calls(tmp_path, provider)

        assert rerun.call("step", "prompt", {"a": 1}, _parse) == 3
        assert len(provider.payloads) == 1
        assert rerun.stats["step"]["cached"] == 1

    def test_prompt_or_model_change_misses_cache(self, tmp_path: Path) -> None:
        """Changing the prompt or model makes a new call."""
        provider = _Replies([{"value": 1}, {"value": 2}, {"value": 3}])

        _calls(tmp_path, provider).call("step", "prompt", {}, _parse)
        _calls(tmp_path, provider).call("step", "edited prompt", {}, _parse)
        _calls(tmp_path, provider, model="other").call("step", "prompt", {}, _parse)

        assert len(provider.payloads) == 3

    def test_retries_with_validation_errors(self, tmp_path: Path) -> None:
        """An invalid response is retried once with the errors attached."""
        provider = _Replies([{"value": "x"}, {"value": 5}])

        assert _calls(tmp_path, provider).call("step", "prompt", {"a": 1}, _parse) == 5
        assert provider.payloads[1]["previous_errors"] == ["value must be an integer"]
        rows = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
        assert [row.get("rejected") for row in rows] == ["value must be an integer", None]

    def test_raises_after_repeated_invalid_output(self, tmp_path: Path) -> None:
        """Two invalid responses raise and leave nothing cached."""
        provider = _Replies([[], {"value": None}])

        with pytest.raises(StepError, match="step: model output failed validation"):
            _calls(tmp_path, provider).call("step", "prompt", {}, _parse)
        assert not list((tmp_path / "cache").glob("*.json"))

    def test_unserializable_response_is_retried(self, tmp_path: Path) -> None:
        """A response that cannot be cached as strict JSON (such as NaN) is treated as invalid."""
        provider = _Replies([{"value": 1, "extra": float("nan")}, {"value": 2}])

        assert _calls(tmp_path, provider).call("step", "prompt", {}, _parse) == 2

    def test_unpaired_surrogate_in_payload(self, tmp_path: Path) -> None:
        """A payload with an unpaired surrogate still gets a cache key."""
        provider = _Replies([{"value": 1}])

        assert _calls(tmp_path, provider).call("step", "prompt", {"text": "\ud800"}, _parse) == 1

    def test_logs_usage(self, tmp_path: Path) -> None:
        """Every model call is logged with its token usage."""
        calls = _calls(tmp_path, _Replies([{"value": 1}]))

        calls.call("observe", "prompt", {}, _parse)

        [row] = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
        assert (row["step"], row["input_tokens"], row["output_tokens"]) == ("observe", 10, 4)
        assert calls.stats["observe"] == {"calls": 1, "cached": 0, "input_tokens": 10, "output_tokens": 4}
