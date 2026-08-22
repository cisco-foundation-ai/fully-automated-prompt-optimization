# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Privacy-safe MCP configuration and capability provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePath, PureWindowsPath
from typing import Any, Mapping

from src.hephaestus.mcp.types import MCPConfig, MCPTool


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unavailable() -> dict[str, str]:
    return {"status": "unavailable"}


def _command_basename(command: str) -> str:
    """Extract a command basename across POSIX and Windows configurations."""
    if "\\" in command:
        return PureWindowsPath(command).name
    return PurePath(command).name


def safe_mcp_facts(
    config: MCPConfig | None,
    discovered_tools: Mapping[str, MCPTool] | None,
) -> dict[str, Any]:
    """Project MCP state without command paths, argument values, or env values."""

    if config is None:
        return {
            "status": "not_configured",
            "servers": [],
            "tool_execution": {"status": "not_configured"},
            "discovered_capabilities": [],
            "capability_discovery": {"status": "not_applicable"},
            "implementation_revision": _unavailable(),
        }

    servers = []
    for server in sorted(config.servers, key=lambda item: item.name):
        servers.append(
            {
                "name": server.name,
                "enabled": bool(server.enabled),
                "timeout_seconds": int(server.timeout_seconds),
                "command_name": _command_basename(server.command),
                "argument_count": len(server.args),
                "environment_variable_names": sorted(server.env),
            }
        )

    capabilities = []
    if discovered_tools is not None:
        for tool in sorted(
            discovered_tools.values(),
            key=lambda item: (item.server_name, item.name),
        ):
            capabilities.append(
                {
                    "name": tool.name,
                    "server_name": tool.server_name,
                    "input_schema_sha256": _canonical_sha256(tool.input_schema),
                }
            )

    return {
        "status": "configured",
        "servers": servers,
        "tool_execution": {
            "max_iterations": int(config.max_iterations),
            "max_tool_calls_per_iteration": int(
                config.max_tool_calls_per_iteration
            ),
            "timeout_seconds": int(config.timeout_seconds),
        },
        "discovered_capabilities": capabilities,
        "capability_discovery": (
            {"status": "available"}
            if discovered_tools is not None
            else _unavailable()
        ),
        "implementation_revision": _unavailable(),
    }
