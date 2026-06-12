# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Types for MCP server configuration and tool schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server.

    Attributes:
        name: Unique identifier for this server
        command: Command to execute (e.g., "npx", "python")
        args: Command-line arguments
        env: Environment variables to pass to the server process
        enabled: Whether this server should be started
        timeout_seconds: Maximum time to wait for server startup
    """
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout_seconds: int = 30


@dataclass
class MCPTool:
    """MCP tool schema.

    Represents a tool exposed by an MCP server, with its name, description,
    and JSON Schema for input parameters.

    Attributes:
        name: Unique tool name (e.g., "web_search", "read_file")
        description: Human-readable description of what the tool does
        input_schema: JSON Schema defining the tool's parameters
        server_name: Name of the MCP server that provides this tool
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str = ""


@dataclass
class MCPConfig:
    """MCP configuration section from eval config.

    Attributes:
        servers: List of MCP server configurations
        max_iterations: Maximum ReAct loop iterations for agentic nodes
        max_tool_calls_per_iteration: Safety limit on parallel tool calls
        timeout_seconds: Timeout for individual tool execution
    """
    servers: List[MCPServerConfig] = field(default_factory=list)
    max_iterations: int = 10
    max_tool_calls_per_iteration: int = 5
    timeout_seconds: int = 30
