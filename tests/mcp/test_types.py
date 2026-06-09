# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for MCP types."""

from src.hephaestus.mcp.types import MCPConfig, MCPServerConfig, MCPTool


def test_mcp_server_config_creation():
    """Test MCPServerConfig dataclass creation."""
    config = MCPServerConfig(
        name="test_server",
        command="python",
        args=["-m", "test"],
        env={"TEST": "value"},
        enabled=True,
        timeout_seconds=30,
    )
    assert config.name == "test_server"
    assert config.command == "python"
    assert config.args == ["-m", "test"]
    assert config.env == {"TEST": "value"}
    assert config.enabled is True
    assert config.timeout_seconds == 30


def test_mcp_server_config_defaults():
    """Test MCPServerConfig with default values."""
    config = MCPServerConfig(name="test", command="test_cmd")
    assert config.args == []
    assert config.env == {}
    assert config.enabled is True
    assert config.timeout_seconds == 30


def test_mcp_tool_creation():
    """Test MCPTool dataclass creation."""
    tool = MCPTool(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        server_name="brave_search",
    )
    assert tool.name == "web_search"
    assert tool.description == "Search the web"
    assert "query" in tool.input_schema["properties"]
    assert tool.server_name == "brave_search"


def test_mcp_config_creation():
    """Test MCPConfig dataclass creation."""
    servers = [
        MCPServerConfig(name="server1", command="cmd1"),
        MCPServerConfig(name="server2", command="cmd2"),
    ]
    config = MCPConfig(
        servers=servers,
        max_iterations=15,
        max_tool_calls_per_iteration=3,
        timeout_seconds=60,
    )
    assert len(config.servers) == 2
    assert config.max_iterations == 15
    assert config.max_tool_calls_per_iteration == 3
    assert config.timeout_seconds == 60


def test_mcp_config_defaults():
    """Test MCPConfig with default values."""
    config = MCPConfig()
    assert config.servers == []
    assert config.max_iterations == 10
    assert config.max_tool_calls_per_iteration == 5
    assert config.timeout_seconds == 30
