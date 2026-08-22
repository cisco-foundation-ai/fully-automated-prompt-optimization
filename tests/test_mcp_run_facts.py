# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Privacy-safe MCP configuration and discovered-capability facts."""

from __future__ import annotations

import json

from src.hephaestus.mcp.types import MCPConfig, MCPServerConfig, MCPTool
from src.hephaestus.runs.mcp_facts import safe_mcp_facts


def test_safe_mcp_facts_never_persist_environment_or_argument_values() -> None:
    secret = "mcp-secret-sentinel"
    config = MCPConfig(
        servers=[
            MCPServerConfig(
                name="retrieval",
                command="/private/bin/server",
                args=[f"--{secret}", "--token", secret],
                env={"MCP_TOKEN": secret},
                enabled=True,
                timeout_seconds=17,
            )
        ],
        max_iterations=4,
        max_tool_calls_per_iteration=3,
        timeout_seconds=11,
    )
    tools = {
        "lookup": MCPTool(
            name="lookup",
            description="protected description",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            server_name="retrieval",
        )
    }

    facts = safe_mcp_facts(config, tools)
    serialized = json.dumps(facts, sort_keys=True)

    assert facts["status"] == "configured"
    assert facts["servers"][0]["name"] == "retrieval"
    assert facts["servers"][0]["environment_variable_names"] == ["MCP_TOKEN"]
    assert facts["servers"][0]["argument_count"] == 3
    assert "argument_flags" not in facts["servers"][0]
    assert facts["tool_execution"] == {
        "max_iterations": 4,
        "max_tool_calls_per_iteration": 3,
        "timeout_seconds": 11,
    }
    assert facts["discovered_capabilities"][0]["name"] == "lookup"
    assert len(facts["discovered_capabilities"][0]["input_schema_sha256"]) == 64
    assert facts["implementation_revision"] == {"status": "unavailable"}
    assert secret not in serialized
    assert "/private/bin/server" not in serialized
    assert "protected description" not in serialized


def test_safe_mcp_facts_uses_the_basename_of_windows_commands() -> None:
    """A platform-neutral provenance record must not retain a Windows path."""
    facts = safe_mcp_facts(
        MCPConfig(
            servers=[
                MCPServerConfig(
                    name="retrieval",
                    command=r"C:\\private\\bin\\mcp-server.exe",
                )
            ]
        ),
        None,
    )

    assert facts["servers"][0]["command_name"] == "mcp-server.exe"


def test_safe_mcp_facts_distinguishes_not_configured_from_unavailable_discovery() -> None:
    assert safe_mcp_facts(None, None) == {
        "status": "not_configured",
        "servers": [],
        "tool_execution": {"status": "not_configured"},
        "discovered_capabilities": [],
        "capability_discovery": {"status": "not_applicable"},
        "implementation_revision": {"status": "unavailable"},
    }

    configured = safe_mcp_facts(MCPConfig(), None)
    assert configured["status"] == "configured"
    assert configured["capability_discovery"] == {"status": "unavailable"}
