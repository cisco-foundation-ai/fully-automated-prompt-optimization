<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Prompt Contract

## Output Format Contract
- The agent must emit its final answer after an `Answer:` marker so the scorer's `answer_present` check passes.
- The final answer must contain the expected substring for the case (e.g. the computed sum, or the echoed message).
- Intermediate reasoning and tool calls are allowed and expected; only the final answer is scored for correctness.

## Decision Policy
- Use tools when they help complete the task:
  - Arithmetic → call the `add` tool (do not compute mentally).
  - Echo/repeat requests → call the `echo` tool.
  - Multi-step calculations → call `add` repeatedly, chaining results.
- Answer simple knowledge questions directly, without any tool call.
- Never call the `fail` tool; it exists only for infrastructure error-handling tests.

## Defang and Safety Rules
- No defanging needed — inputs are plain-text tasks with no sensitive content.
- No PII or secrets appear in the dataset.
- Tool arguments must be well-formed per each tool's input schema (discovered from the MCP server).

## Variant Strategy
- Prompts stored in `prompts/modules/agent/variant-NNN.md`.
- `variant-001.md`: baseline ReAct prompt with guidance on when to use vs. avoid tools.
- New variants clone the latest and adjust tool-selection guidance, answer formatting, or stopping criteria. Never edit a variant in place.

## Non-Goals
- Domain-specific reasoning beyond trivial arithmetic and general knowledge.
- Adding tools beyond what the mock MCP server exposes.
- Structural chain changes (the chain is a fixed single-node ReAct agent).
- Optimization that overfits to individual dataset cases.
