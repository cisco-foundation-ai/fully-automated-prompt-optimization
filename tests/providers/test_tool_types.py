# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for tool calling types."""

import pytest

from src.hephaestus.providers.tool_types import GenerateResponse, ToolCall, ToolResult


def test_tool_call_creation():
    """Test ToolCall dataclass creation."""
    tc = ToolCall(id="call_123", name="web_search", arguments={"query": "test"})
    assert tc.id == "call_123"
    assert tc.name == "web_search"
    assert tc.arguments == {"query": "test"}


def test_tool_result_creation():
    """Test ToolResult dataclass creation."""
    tr = ToolResult(tool_call_id="call_123", content="result content")
    assert tr.tool_call_id == "call_123"
    assert tr.content == "result content"
    assert tr.error is None


def test_tool_result_with_error():
    """Test ToolResult with error."""
    tr = ToolResult(tool_call_id="call_123", content="", error="Tool execution failed")
    assert tr.error == "Tool execution failed"


def test_generate_response_text_only():
    """Test GenerateResponse for text-only generation."""
    resp = GenerateResponse(content="Hello world", finish_reason="stop")
    assert resp.content == "Hello world"
    assert resp.tool_calls is None
    assert resp.finish_reason == "stop"


def test_generate_response_with_tool_calls():
    """Test GenerateResponse with tool calls."""
    tool_calls = [
        ToolCall(id="call_1", name="search", arguments={"q": "test"}),
        ToolCall(id="call_2", name="read", arguments={"file": "test.txt"}),
    ]
    resp = GenerateResponse(
        content="", tool_calls=tool_calls, finish_reason="tool_calls"
    )
    assert resp.tool_calls == tool_calls
    assert resp.finish_reason == "tool_calls"


def test_generate_response_invalid_finish_reason():
    """Test GenerateResponse validation of finish_reason."""
    with pytest.raises(ValueError, match="finish_reason must be"):
        GenerateResponse(content="test", finish_reason="invalid")


def test_generate_response_tool_calls_finish_reason_requires_calls():
    """finish_reason='tool_calls' requires a non-empty tool_calls list."""
    with pytest.raises(ValueError, match="finish_reason='tool_calls' requires"):
        GenerateResponse(content="", tool_calls=None, finish_reason="tool_calls")


def test_generate_response_tool_calls_with_stop_is_allowed():
    """Carrying tool_calls alongside finish_reason='stop' is permitted.

    The provider sets finish_reason directly from the API response, so we do
    not force it to 'tool_calls' merely because tool_calls happen to be present.
    """
    tool_calls = [ToolCall(id="call_1", name="test", arguments={})]
    resp = GenerateResponse(content="", tool_calls=tool_calls, finish_reason="stop")
    assert resp.tool_calls == tool_calls
    assert resp.finish_reason == "stop"
