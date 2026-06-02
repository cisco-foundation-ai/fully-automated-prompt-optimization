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
- `datasets/tool_tasks.jsonl` - Tasks requiring tool use
- `code/scorers/task_scorer.py` - Scorer for task completion
- `configs/eval.json` - Eval configuration with MCP settings
- `docs/iteration-playbook.md` - Optimization constraints

## Tools Available

The mock MCP server provides:
- **echo**: Echo back the input message
- **add**: Add two numbers together
- **fail**: Intentionally fails (for testing error handling)
