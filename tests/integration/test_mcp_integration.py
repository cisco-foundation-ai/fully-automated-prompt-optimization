# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for MCP functionality.

These tests require the MCP Python SDK and test the full MCP integration
including server lifecycle, tool discovery, and tool execution.
"""

import sys
from pathlib import Path

import pytest

from src.hephaestus.mcp.executor import MCPToolExecutor
from src.hephaestus.mcp.manager import MCPServerManager
from src.hephaestus.mcp.types import MCPConfig, MCPServerConfig
from src.hephaestus.providers.tool_types import ToolCall


@pytest.fixture
def mock_server_config():
    """Configuration for mock MCP server."""
    # Get path to mock server script
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    server_script = fixtures_dir / "mock_mcp_server.py"

    return MCPConfig(
        servers=[
            MCPServerConfig(
                name="mock_server",
                command=sys.executable,  # Use current Python interpreter
                args=[str(server_script)],
                enabled=True,
                timeout_seconds=10,
            )
        ],
        max_iterations=5,
        max_tool_calls_per_iteration=3,
        timeout_seconds=5,
    )


@pytest.mark.integration
def test_mcp_server_lifecycle(mock_server_config):
    """Test starting and stopping MCP servers."""
    manager = MCPServerManager("test_tenant", config=mock_server_config)

    # Start servers
    manager.start_servers()

    # Verify server is running and session exists
    assert len(manager._sessions) == 1
    assert "mock_server" in manager._sessions

    # Stop servers
    manager.stop_servers()

    # Verify cleanup
    assert len(manager._sessions) == 0
    assert len(manager.tools) == 0


@pytest.mark.integration
def test_mcp_tool_discovery(mock_server_config):
    """Test tool discovery from MCP server."""
    manager = MCPServerManager("test_tenant", config=mock_server_config)

    try:
        manager.start_servers()

        # Verify tools were discovered
        tools = manager.list_tools()
        assert len(tools) >= 2  # Should have at least echo and add

        # Check specific tools
        tool_names = {t.name for t in tools}
        assert "echo" in tool_names
        assert "add" in tool_names

        # Verify tool schemas
        echo_tool = manager.get_tool("echo")
        assert echo_tool is not None
        assert echo_tool.description == "Echo the input message"
        assert "inputSchema" in echo_tool.input_schema or "properties" in echo_tool.input_schema

    finally:
        manager.stop_servers()


@pytest.mark.integration
def test_mcp_tool_execution(mock_server_config):
    """Test executing tools via MCP protocol."""
    manager = MCPServerManager("test_tenant", config=mock_server_config)
    executor = MCPToolExecutor(manager, max_tool_calls=10, timeout_seconds=5)

    try:
        manager.start_servers()

        # Test echo tool
        echo_call = ToolCall(
            id="call_1",
            name="echo",
            arguments={"message": "Hello, MCP!"}
        )
        result = executor.execute(echo_call)

        assert result.tool_call_id == "call_1"
        assert result.error is None
        assert "Hello, MCP!" in result.content

        # Test add tool
        add_call = ToolCall(
            id="call_2",
            name="add",
            arguments={"a": 10, "b": 32}
        )
        result = executor.execute(add_call)

        assert result.tool_call_id == "call_2"
        assert result.error is None
        assert "42" in result.content

    finally:
        manager.stop_servers()


@pytest.mark.integration
def test_mcp_tool_error_handling(mock_server_config):
    """Test error handling in tool execution."""
    manager = MCPServerManager("test_tenant", config=mock_server_config)
    executor = MCPToolExecutor(manager, max_tool_calls=10, timeout_seconds=5)

    try:
        manager.start_servers()

        # Test calling non-existent tool
        bad_call = ToolCall(
            id="call_bad",
            name="nonexistent_tool",
            arguments={}
        )
        result = executor.execute(bad_call)

        assert result.tool_call_id == "call_bad"
        assert result.error is not None
        assert "not found" in result.error.lower()

    finally:
        manager.stop_servers()


@pytest.mark.integration
def test_mcp_batch_execution(mock_server_config):
    """Test executing multiple tools in batch."""
    manager = MCPServerManager("test_tenant", config=mock_server_config)
    executor = MCPToolExecutor(manager, max_tool_calls=10, timeout_seconds=5)

    try:
        manager.start_servers()

        # Execute multiple tool calls
        tool_calls = [
            ToolCall(id="call_1", name="echo", arguments={"message": "First"}),
            ToolCall(id="call_2", name="echo", arguments={"message": "Second"}),
            ToolCall(id="call_3", name="add", arguments={"a": 5, "b": 7}),
        ]

        results = executor.execute_batch(tool_calls)

        assert len(results) == 3
        assert all(r.error is None for r in results)
        assert "First" in results[0].content
        assert "Second" in results[1].content
        assert "12" in results[2].content

    finally:
        manager.stop_servers()


@pytest.mark.integration
def test_mcp_max_tool_calls_limit(mock_server_config):
    """Test that max_tool_calls limit is enforced."""
    manager = MCPServerManager("test_tenant", config=mock_server_config)
    executor = MCPToolExecutor(manager, max_tool_calls=2, timeout_seconds=5)

    try:
        manager.start_servers()

        # Execute calls up to limit
        for i in range(2):
            call = ToolCall(id=f"call_{i}", name="echo", arguments={"message": f"Call {i}"})
            result = executor.execute(call)
            assert result.error is None

        # Next call should fail due to limit
        call = ToolCall(id="call_over_limit", name="echo", arguments={"message": "Too many"})
        result = executor.execute(call)

        assert result.error is not None
        assert "max_tool_calls" in result.error

    finally:
        manager.stop_servers()
