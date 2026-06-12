# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Agentic node factories for chains with tool calling support."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict

from src.hephaestus.chains.nodes import build_node_context
from src.hephaestus.engine.prompt_renderer import render_prompt
from src.hephaestus.mcp.executor import MCPToolExecutor
from src.hephaestus.mcp.manager import MCPServerManager
from src.hephaestus.mcp.schema_converter import convert_mcp_tools_to_openai
from src.hephaestus.providers.base import ProviderClient

logger = logging.getLogger(__name__)


def make_agentic_node(
    provider: ProviderClient,
    prompt_template_path: Path,
    mcp_manager: MCPServerManager,
    output_key: str = "output_text",
    max_iterations: int = 10,
    max_tool_calls_per_iteration: int = 5,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Create a LangGraph node that supports iterative tool use (ReAct pattern).

    The node implements a thought-action-observation loop:
    1. Thought: LLM reasons about what information is needed
    2. Action: LLM requests tool calls
    3. Observation: Tools are executed and results returned to LLM
    4. Repeat until LLM returns final answer or max_iterations reached

    This enables agentic workflows where the LLM can:
    - Search the web for information
    - Read/write files
    - Query databases
    - Execute code
    - Call any MCP-compatible tool

    Args:
        provider: LLM provider with tool calling support
        prompt_template_path: Path to prompt template
        mcp_manager: MCP server manager for tool discovery and execution
        output_key: Key to store final output in step_outputs
        max_iterations: Maximum ReAct loop iterations (safety limit)
        max_tool_calls_per_iteration: Maximum parallel tool calls per iteration

    Returns:
        A callable(state) -> state_update suitable for StateGraph.add_node()

    Example:
        graph.add_node(
            "agent",
            make_agentic_node(
                provider=provider,
                prompt_template_path=Path("prompts/agent.md"),
                mcp_manager=mcp_manager,
                max_iterations=15,
            )
        )
    """
    template_text = prompt_template_path.read_text(encoding="utf-8")
    tools = mcp_manager.list_tools()
    tool_schemas = convert_mcp_tools_to_openai(tools) if tools else None

    # The per-case tool-call ceiling. A generous default of max_iterations *
    # max_tool_calls_per_iteration so a well-behaved case never trips it; the
    # real per-iteration cap is enforced separately below.
    max_tool_calls_per_case = max_iterations * max_tool_calls_per_iteration

    if not tool_schemas:
        logger.warning(
            f"Agentic node '{output_key}' has no tools available. "
            "Will behave like standard LLM node."
        )

    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Agentic node implementation - executes ReAct loop."""
        context = build_node_context(state)
        render_result = render_prompt(template_text, context)

        # Create a fresh executor PER CASE so the tool-call limit is per-case
        # (not cumulative across the whole eval run) and thread-safe under
        # max_workers > 1.
        executor = MCPToolExecutor(mcp_manager, max_tool_calls=max_tool_calls_per_case)

        messages = render_result.prompt_messages.copy()
        tool_call_history = list(state.get("tool_call_history", []))
        iterations = 0
        # Monotonic per-case counter so scorers can reconstruct call ordering
        # across iterations (the list order already implies this, but an
        # explicit index survives any later filtering/reordering).
        call_index = len(tool_call_history)

        while iterations < max_iterations:
            iterations += 1

            # Generate with tools
            response = provider.generate_with_tools(messages, tools=tool_schemas)

            # If no tool calls, we have final answer
            if not response.tool_calls or response.finish_reason == "stop":
                step_outputs = dict(state.get("step_outputs", {}))
                step_outputs[output_key] = response.content

                diagnostics = list(state.get("diagnostics", []))
                diagnostics.extend(render_result.diagnostics)
                diagnostics.append(
                    f"Agentic node '{output_key}': {iterations} iterations, "
                    f"{len(tool_call_history)} tool calls total"
                )

                return {
                    "output_text": response.content,
                    "step_outputs": step_outputs,
                    "diagnostics": diagnostics,
                    "tool_call_history": tool_call_history,
                }

            # Execute tool calls
            tool_calls_to_execute = response.tool_calls[:max_tool_calls_per_iteration]
            if len(response.tool_calls) > max_tool_calls_per_iteration:
                logger.warning(
                    f"Agentic node '{output_key}': LLM requested "
                    f"{len(response.tool_calls)} tool calls, limiting to "
                    f"{max_tool_calls_per_iteration}"
                )

            # Execute each call individually so per-call latency is captured.
            # This is the same sequential semantics as execute_batch (which is
            # itself a sequential loop) and preserves the per-case call limit.
            tool_results = []
            tool_latencies_ms = []
            for tc in tool_calls_to_execute:
                t_call = time.monotonic()
                result = executor.execute(tc)
                tool_latencies_ms.append(round((time.monotonic() - t_call) * 1000, 1))
                tool_results.append(result)

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in tool_calls_to_execute
                ]
            })

            # Add tool results as messages and to history
            for tc, result, latency_ms in zip(
                tool_calls_to_execute, tool_results, tool_latencies_ms
            ):
                messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.content if not result.error else f"Error: {result.error}"
                })

                tool_call_history.append({
                    "tool": tc.name,
                    "arguments": tc.arguments,
                    # Full tool output so LLM-judge / trajectory scorers can
                    # inspect what the tool actually returned, not just its size.
                    "result": result.content,
                    "result_length": len(result.content),
                    "error": result.error,
                    "iteration": iterations,
                    "call_index": call_index,
                    # The assistant's reasoning that produced this batch of
                    # calls (same for all calls in one iteration).
                    "llm_thought": response.content or "",
                    "latency_ms": latency_ms,
                    "node": output_key,
                })
                call_index += 1

        # Max iterations reached without final answer
        diagnostics = list(state.get("diagnostics", []))
        diagnostics.extend(render_result.diagnostics)
        diagnostics.append(
            f"Agentic node '{output_key}': hit max_iterations={max_iterations}, "
            f"returning last response"
        )

        # Extract final content from last message or response
        final_content = response.content or ""
        if not final_content and messages:
            # Try to get content from last assistant message
            for msg in reversed(messages):
                if msg.get("role") == "assistant" and msg.get("content"):
                    final_content = msg["content"]
                    break

        step_outputs = dict(state.get("step_outputs", {}))
        step_outputs[output_key] = final_content

        return {
            "output_text": final_content,
            "step_outputs": step_outputs,
            "diagnostics": diagnostics,
            "tool_call_history": tool_call_history,
        }

    return node
