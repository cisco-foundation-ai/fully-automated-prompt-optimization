<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Iteration Playbook: MCP Example

## Purpose

Demonstrate and test MCP integration with agentic workflows. This tenant is primarily for validation and examples, not production optimization.

## Iteration Loop

This tenant uses the standard optimization loop from `docs/processes/prompt-iteration-loop.md` with MCP-specific considerations.

## Success Criteria

- Composite score >= 80% on tool_tasks.jsonl
- All tool-based tasks correctly use available tools
- No hallucinated calculations (must use add tool)
- Reasoning tasks answered directly without unnecessary tool calls

## Data Hygiene

All 5 cases are treated as training data for this example tenant. No train/val split needed.

## Optimization Scope

### Chain-Level Optimization Scope

- **Prompt changes**: IN-SCOPE
  - Improve tool selection reasoning
  - Add clarity on when to use vs not use tools
  - Improve answer formatting
  
- **Parameter changes**: IN-SCOPE
  - Adjust max_iterations if agent gets stuck in loops
  - Adjust max_tool_calls_per_iteration for complex tasks
  
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

1. **Calculation tasks** → Use `add` tool
2. **Echo tasks** → Use `echo` tool
3. **Knowledge questions** → Answer directly without tools
4. **Multi-step calculations** → Multiple `add` tool calls

### Common Failure Patterns

1. **Tool avoidance**: Agent calculates mentally instead of using `add`
2. **Tool overuse**: Agent uses tools for simple knowledge questions
3. **Incomplete answers**: Agent stops after tool call without synthesizing answer
4. **Loop failures**: Agent gets stuck retrying failed tool calls

## Lessons Logging

Record optimization outcomes in `docs/change-log.md`:
- Which prompt changes improved tool selection
- Impact of instruction clarity on tool usage
- Any cases where agent behavior was unexpected
