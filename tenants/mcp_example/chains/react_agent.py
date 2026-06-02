# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""ReAct agent chain with MCP tool access for mcp_example tenant."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from src.hephaestus.chains.agentic_nodes import make_agentic_node
from src.hephaestus.chains.nodes import make_llm_node
from src.hephaestus.chains.types import ChainState


def build_chain(provider, config: Dict[str, Any], mcp_manager=None):
    """Build a ReAct agent chain with optional MCP tool support.

    If mcp_manager is provided, uses agentic node with tool calling.
    Otherwise falls back to standard LLM node (for backward compatibility).

    Args:
        provider: LLM provider client
        config: Chain configuration with prompt_paths
        mcp_manager: Optional MCP server manager for tool access

    Returns:
        Compiled LangGraph chain
    """
    prompt_path = Path(config["prompt_paths"]["agent"])
    graph = StateGraph(ChainState)

    if mcp_manager:
        # Use agentic node with MCP tools
        graph.add_node(
            "agent",
            make_agentic_node(
                provider=provider,
                prompt_template_path=prompt_path,
                mcp_manager=mcp_manager,
                output_key="answer",
                max_iterations=10,
                max_tool_calls_per_iteration=5,
            ),
        )
    else:
        # Fall back to standard LLM node (no tools)
        graph.add_node(
            "agent",
            make_llm_node(
                provider=provider,
                prompt_template_path=prompt_path,
                output_key="answer",
            ),
        )

    graph.set_entry_point("agent")
    graph.add_edge("agent", END)

    return graph.compile()
