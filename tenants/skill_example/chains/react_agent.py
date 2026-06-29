# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""ReAct agent chain with Splunk MCP tools + injected skill files (skill_example).

This is the agentic-skills demonstration tenant. It runs a Splunk-operations
ReAct chain but keeps the base prompt deliberately lean: the reusable procedural
knowledge (how to handle superlative-index questions, how to format answers,
etc.) lives in separate **skill files** under ``skills/``. The skills are
loaded at the agentic layer — ``make_agentic_node`` injects them into the
conversation as a distinct ``<available_skills>`` context message — rather than
inlined into the authored prompt, mimicking an agent that discovered and loaded
skills into its environment at session start.

Skills are a textual optimization granularity co-equal with the prompt: the
optimization agent can clone and eval skill variants the same way it does prompt
variants, gated by ``chain.config.optimization_target``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from src.hephaestus.chains.agentic_nodes import make_agentic_node
from src.hephaestus.chains.nodes import make_llm_node
from src.hephaestus.chains.types import ChainState
from src.hephaestus.engine.skills import render_skills_block


def build_chain(provider, config: Dict[str, Any], mcp_manager=None):
    """Build a ReAct agent chain with Splunk MCP tools and injected skills.

    If mcp_manager is provided, uses an agentic node with tool calling against
    the Splunk MCP server. Otherwise falls back to a standard LLM node (for
    backward compatibility / tool-free smoke tests). In both cases the
    configured skill files are loaded at the agentic layer and injected into the
    conversation as a runtime ``<available_skills>`` context message.

    Args:
        provider: LLM provider client
        config: Chain configuration with prompt_paths, skill_paths, and optional
            tool limits
        mcp_manager: Optional MCP server manager for tool access

    Returns:
        Compiled LangGraph chain
    """
    prompt_path = Path(config["prompt_paths"]["agent"])
    # Tool-execution limits are parameter-level optimization knobs. They are
    # read from the chain config so the optimization agent can tune them
    # without editing code; defaults mirror the agentic node defaults.
    max_iterations = int(config.get("max_iterations", 10))
    max_tool_calls_per_iteration = int(config.get("max_tool_calls_per_iteration", 5))
    # Skills are a textual optimization granularity, co-equal with the prompt.
    # Their bodies are concatenated here and handed to the node, which injects
    # them at runtime as a loaded-skills context message. Empty when no
    # skill_paths are configured.
    skills_text = render_skills_block(config.get("skill_paths", []))
    graph = StateGraph(ChainState)

    if mcp_manager:
        # Use agentic node with Splunk MCP tools
        graph.add_node(
            "agent",
            make_agentic_node(
                provider=provider,
                prompt_template_path=prompt_path,
                mcp_manager=mcp_manager,
                output_key="answer",
                max_iterations=max_iterations,
                max_tool_calls_per_iteration=max_tool_calls_per_iteration,
                skills_text=skills_text,
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
                skills_text=skills_text,
            ),
        )

    graph.set_entry_point("agent")
    graph.add_edge("agent", END)

    return graph.compile()
