<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Profile

## Organization Profile
mcp_example is a reference/demonstration tenant for FAPO's Model Context Protocol (MCP) integration. It exercises the agentic evaluation path end-to-end — a ReAct agent that calls tools exposed by an MCP server — using a bundled mock server so no external credentials or services are required. It exists to validate the agentic infrastructure and to serve as a copy-paste template for building real MCP-backed tenants.

## Security Environment Assumptions
- Input: short natural-language tasks (echo requests, arithmetic, simple knowledge questions). No sensitive content.
- Output: a final answer string, optionally produced after one or more tool calls.
- Tool access: limited to a local mock MCP server (`tests/fixtures/mock_mcp_server.py`) exposing `echo`, `add`, and `fail`. The mock runs as a local subprocess over stdio and has no network or filesystem side effects.
- No real provider credentials are stored in the tenant; `OPENAI_API_KEY` is read from the environment at runtime.

## Threat Model Focus
- Not a security-analysis tenant. It exists for infrastructure validation of the agentic/MCP path.
- The only adversarial surface intentionally exercised is tool-failure handling, via the `fail` tool, to confirm errors are isolated and attributed rather than crashing the eval.

## Known Safe Patterns
- Tool-use tasks resolve to a deterministic expected substring (e.g. `add(42, 17)` → contains `59`).
- Reasoning tasks (e.g. "capital of France") should be answered directly, with no tool calls.
- The agent must emit a final answer after the `Answer:` marker.
- `tool_call_history` in results reflects exactly which tools fired, so tool usage is verifiable rather than inferred.

## Tenant Terminology
- **agent**: The single ReAct node in the chain (`chains/react_agent.py`); the only prompt module.
- **variant-001**: Baseline agent prompt — generic ReAct instructions with guidance on when to use vs. avoid tools.
- **echo / add / fail**: The three tools provided by the mock MCP server. `fail` always errors and is used only to test error handling.
- **mock MCP server**: SDK-based stdio MCP server at `tests/fixtures/mock_mcp_server.py`, launched per eval run.
