# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Convert MCP tool schemas to OpenAI function calling format."""

from __future__ import annotations

from typing import Any, Dict

from src.hephaestus.mcp.types import MCPTool


def convert_mcp_to_openai_schema(mcp_tool: MCPTool) -> Dict[str, Any]:
    """Convert MCP tool schema to OpenAI function calling format.

    MCP uses JSON Schema for input_schema. OpenAI function calling also uses
    JSON Schema, so the conversion is mostly straightforward.

    Args:
        mcp_tool: MCPTool with name, description, and input_schema

    Returns:
        Dict in OpenAI function calling format:
        {
            "type": "function",
            "function": {
                "name": str,
                "description": str,
                "parameters": {...}  # JSON Schema
            }
        }
    """
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.input_schema,
        },
    }


def convert_mcp_tools_to_openai(mcp_tools: list[MCPTool]) -> list[Dict[str, Any]]:
    """Convert a list of MCP tools to OpenAI format.

    Args:
        mcp_tools: List of MCPTool objects

    Returns:
        List of OpenAI function calling tool schemas
    """
    return [convert_mcp_to_openai_schema(tool) for tool in mcp_tools]
