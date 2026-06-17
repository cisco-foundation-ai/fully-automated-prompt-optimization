<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# MCP Example Tenant

This tenant demonstrates agentic workflows using Model Context Protocol (MCP) integration.

## Features

- **ReAct agent** with iterative tool use
- **Mock MCP tools**: echo, add, and intentional failure tool
- **Complete eval setup**: dataset, chain, scorer, config
- **Tool tracking**: Full visibility into tool calls and results

## Quick Start

```bash
# Run evaluation with mock MCP server
python -m hephaestus.cli eval --config tenants/mcp_example/configs/eval.json

# Check results
cat tenants/mcp_example/evals/run-001/summary.md
cat tenants/mcp_example/evals/run-001/results.jsonl | jq '.tool_call_history'
```

## What's Tested

The evaluation tests the agent's ability to:
1. Use tools when needed (not hallucinate answers)
2. Choose appropriate tools for tasks
3. Handle tool errors gracefully
4. Iterate with multiple tool calls
5. Synthesize final answers from tool results

## Files

- `chains/react_agent.py` - ReAct agent with MCP tools
- `prompts/modules/agent/variant-001.md` - Agent system prompt
- `datasets/tool_tasks.jsonl` - 30 tool-use and reasoning tasks
- `code/scorers/composite_scorer.py` - Weighted scorer combining LLM-as-judge answer correctness + trajectory
- `code/scorers/trajectory_scorer.py` - Deterministic order/argument-aware tool-trajectory scorer
- `code/scorers/llm_judge_scorer.py` - LLM-as-judge answer-correctness scorer
- `configs/eval.json` - Eval configuration with MCP settings
- `docs/` - Tenant docs (profile, data/prompt contracts, eval operations, iteration playbook, change log, docs index)

## Tools Available

The mock MCP server provides:
- **echo**: Echo back the input message
- **add**: Add two numbers together
- **fail**: Intentionally fails (for testing error handling)
