<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Iteration Playbook: MCP Example

## Purpose

Demonstrate and test MCP integration with agentic workflows. This tenant is primarily for validation and as a template, not production optimization.

## Prerequisites
- Global reference: `docs/processes/prompt-iteration-loop.md`.
- `OPENAI_API_KEY` set in the environment.
- The bundled mock MCP server (`tests/fixtures/mock_mcp_server.py`) is reachable via the configured interpreter; no external services or credentials are required.
- Baseline eval completed with `variant-001` (`configs/eval.json`).

## Iteration Loop
1. Follow the global iteration loop from `docs/processes/prompt-iteration-loop.md`.
2. Optimize the single `agent` prompt module over `tool_tasks.jsonl` (30 cases). All cases are treated as training data — there is no train/val/test split for this demo tenant.
3. After each prompt change, re-run the full eval and compare composite score and `score_breakdown` (especially `tool_usage` and `tool_efficiency`) against the previous best.
4. Iterate until success criteria are met.

## Success Criteria
- Composite score >= 80% across all 30 cases.
- Tool-use tasks call the expected tools (verified via `tool_call_history`).
- No hallucinated calculations (arithmetic must go through the `add` tool).
- Reasoning tasks answered directly, with no tool calls.

## Optimization Scope

### Chain-Level Optimization Scope

- **Prompt changes**: IN-SCOPE
  - Improve tool-selection reasoning
  - Add clarity on when to use vs. avoid tools
  - Improve answer formatting (e.g. the `Answer:` marker)
- **Parameter changes**: IN-SCOPE
  - Adjust `max_iterations` if the agent gets stuck in loops
  - Adjust `max_tool_calls_per_iteration` for complex tasks
- **Structural changes**: NOT IN-SCOPE
  - Chain architecture is fixed (single ReAct node)
  - MCP server configuration is fixed (mock tools only)

### Scope Constraint

**Allowed pattern**: `prompts/modules/*/variant-*.md`

The optimization agent may only modify prompt template files. It must not:
- Change chain structure (always single-node ReAct)
- Modify MCP server configuration
- Change model parameters without approval
- Modify scorer logic

## Tool Usage Patterns

### Expected Behaviors
1. **Calculation tasks** → use the `add` tool
2. **Echo tasks** → use the `echo` tool
3. **Knowledge questions** → answer directly without tools
4. **Multi-step calculations** → multiple chained `add` calls

### Common Failure Patterns
1. **Tool avoidance**: agent calculates mentally instead of using `add`
2. **Tool overuse**: agent uses tools for simple knowledge questions
3. **Incomplete answers**: agent stops after a tool call without synthesizing a final answer
4. **Loop failures**: agent gets stuck retrying after a tool error

## Stop Criteria
- Composite score >= 80% sustained across the full 30-case set, OR
- Three consecutive prompt variants show no improvement (plateau) after exhausting tool-selection, formatting, and stopping-criteria techniques.

## Regression Prevention
- Run the full 30-case eval after every prompt change — never accept a variant on a partial run.
- Compare composite score and per-check breakdown against the previous best before accepting a new variant.
- Watch `tool_usage` and `tool_efficiency` specifically: a higher composite score that comes with degraded tool behavior (e.g. tool overuse on reasoning cases) is a regression, not a win.

## Lessons Logging
Record optimization outcomes in `docs/change-log.md`:
- Which prompt changes improved tool selection
- Impact of instruction clarity on tool usage
- Any cases where agent behavior was unexpected
