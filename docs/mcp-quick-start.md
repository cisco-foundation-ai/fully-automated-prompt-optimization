<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# MCP Quick Start Guide

## Status

MCP integration is **complete and working**. FAPO can evaluate agentic workflows
where the model calls tools exposed by [Model Context Protocol](https://modelcontextprotocol.io/)
servers, using a real ReAct loop. The protocol is implemented with the official
`mcp` Python SDK — there is nothing left to stub in.

A complete, runnable example lives at `tenants/mcp_example/`. This guide walks
through using it and building your own agentic tenant.

What you get out of the box:
- MCP server lifecycle management (start, tool discovery, execution, clean shutdown)
- A ReAct agentic node (`make_agentic_node`) with iterative tool calling
- Per-case tool-call limits and per-tool timeouts
- Full tool-call tracking in eval results (`tool_call_history`, `total_tool_calls`, `failed_tool_calls`)
- Tool-failure attribution in step analysis

---

## Prerequisites

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .          # installs mcp>=1.0.0 and httpx as core deps
export OPENAI_API_KEY="sk-..."
```

The `mcp` SDK ships as a core dependency, so no extra install step is needed.

---

## Run the example tenant

The fastest way to see it working end to end:

```bash
python3 -m hephaestus.cli eval --config tenants/mcp_example/configs/eval.json
```

This uses a bundled mock MCP server (`tests/fixtures/mock_mcp_server.py`, built on
the MCP SDK) that exposes three tools: `echo`, `add`, and `fail` (the last is for
exercising error handling). The dataset has 30 cases mixing tool-use tasks with
reasoning tasks the agent should answer *without* tools.

**Expected behavior:**
- ✅ The mock MCP server starts and 3 tools are discovered
- ✅ Each case runs through the ReAct agentic node
- ✅ Tool calls are executed for real and tracked
- ✅ Results include `tool_call_history`
- ✅ The MCP server shuts down cleanly at the end

Check results:

```bash
cat tenants/mcp_example/evals/run-001/summary.md
cat tenants/mcp_example/evals/run-001/results.jsonl | python3 -m json.tool | head -40
```

---

## Building your own agentic tenant

### Step 1: Add an `mcp` section to your eval config

```json
{
  "tenant_id": "my_agent",
  "provider": "openai",
  "provider_settings": {
    "model": "gpt-4o-mini",
    "temperature": 0.0,
    "max_tokens": 2048
  },
  "mcp": {
    "servers": [
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/workspace"],
        "env": {},
        "enabled": true,
        "timeout_seconds": 30
      }
    ],
    "tool_execution": {
      "max_iterations": 10,
      "max_tool_calls_per_iteration": 5,
      "timeout_seconds": 30
    }
  },
  "dataset": {"path": "tenants/my_agent/datasets/test.jsonl"},
  "chain": {
    "path": "tenants/my_agent/chains/agent.py",
    "fn": "build_chain",
    "config": {
      "prompt_paths": {"agent": "tenants/my_agent/prompts/agent.md"}
    }
  },
  "scoring_profile": {
    "scorer": {
      "module_path": "tenants/my_agent/code/scorer.py",
      "class_name": "Scorer"
    }
  },
  "output_dir": "tenants/my_agent/evals/run-001"
}
```

**`mcp` config fields:**

| Field | Meaning |
|-------|---------|
| `servers[].name` | Unique server identifier |
| `servers[].command` / `args` | How to launch the server (stdio transport) |
| `servers[].env` | Env vars for the server process. Supports `${VAR_NAME}` substitution from your environment (e.g. `{"BRAVE_API_KEY": "${BRAVE_API_KEY}"}`) |
| `servers[].enabled` | Set `false` to skip a server without deleting its config |
| `servers[].timeout_seconds` | Startup/connection allowance for this server |
| `tool_execution.max_iterations` | Max ReAct loop iterations per case |
| `tool_execution.max_tool_calls_per_iteration` | Max tool calls the model may issue in a single turn |
| `tool_execution.timeout_seconds` | Per-tool-call execution timeout |

> The per-case tool-call ceiling is derived automatically as
> `max_iterations * max_tool_calls_per_iteration`. A fresh executor is created
> for each case, so this limit is per-case (not cumulative across the run) and
> safe under `max_workers > 1`.

### Step 2: Write the chain

Your `build_chain` factory must accept an optional `mcp_manager` parameter. When
present, use `make_agentic_node`; otherwise fall back to a plain LLM node so the
chain still works without MCP.

```python
# tenants/my_agent/chains/agent.py
from pathlib import Path

from langgraph.graph import END, StateGraph

from src.hephaestus.chains.types import ChainState
from src.hephaestus.chains.agentic_nodes import make_agentic_node
from src.hephaestus.chains.nodes import make_llm_node


def build_chain(provider, config, mcp_manager=None):
    """Agentic chain with optional MCP support."""
    prompt_path = Path(config["prompt_paths"]["agent"])
    graph = StateGraph(ChainState)

    if mcp_manager:
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
```

The eval runner inspects your factory's signature and only passes `mcp_manager`
if the parameter exists — so existing non-MCP chains keep working unchanged.

See `tenants/mcp_example/chains/react_agent.py` for the working reference.

### Step 3: Write the agent prompt

```markdown
System: You are a helpful assistant with access to tools.

Available tools:
- echo: Echo back a message
- add: Add two numbers

Use tools when they help. For simple knowledge questions, answer directly
without tools. Provide your final answer after "Answer:".

User: ${task}

Think step by step and use tools as needed.
```

Tool schemas are discovered from the MCP server automatically and passed to the
model — you do not list them in config. The prompt is just guidance on *when* to
use them.

### Step 4: Score with tool awareness (optional)

To score based on actual tool usage, override `score_pipeline_case` — it receives
`tool_call_history`:

```python
def score_pipeline_case(self, case, step_outputs, scoring_profile,
                        output_text=None, tool_call_history=None):
    actual_tools = [tc["tool"] for tc in (tool_call_history or [])
                    if not tc.get("error")]
    # ... compare against case.expected["tools_used"], etc.
```

See `tenants/mcp_example/code/scorers/` for a full example: a `TrajectoryScorer`
(order/argument-aware tool checks), an `LLMJudgeScorer` (LLM-as-judge answer
correctness), and a `CompositeScorer` that combines them with configurable
weights.

### Step 5: Run it

```bash
python3 -m hephaestus.cli eval --config tenants/my_agent/configs/eval.json
```

---

## What results look like

Each case in `results.jsonl` includes tool-call tracking:

```json
{
  "case_id": "2",
  "output_text": "Answer: 59",
  "tool_call_history": [
    {
      "tool": "add",
      "arguments": {"a": 42, "b": 17},
      "result_length": 11,
      "error": null,
      "iteration": 1,
      "node": "answer"
    }
  ],
  "total_tool_calls": 1,
  "failed_tool_calls": 0,
  "diagnostics": ["Agentic node 'answer': 2 iterations, 1 tool calls total"]
}
```

Failed tool calls are also surfaced in step attribution
(`src/hephaestus/analysis/step_attribution.py`), which classifies tool errors by
type (`timeout`, `not_found`, `invalid_args`, `permission`, `other`) and counts
them under `tool_addressable` in the summary.

---

## Testing

```bash
# Unit tests (no API key needed)
python3 -m pytest tests/providers/test_tool_types.py tests/mcp/test_types.py -v

# Integration tests — start a real (mock) MCP server, discover & call tools
python3 -m pytest tests/integration/test_mcp_integration.py -v -m integration
```

The integration suite uses `tests/fixtures/mock_mcp_server.py` and covers server
lifecycle, tool discovery, execution, error handling, batch execution, and the
per-case tool-call limit.

---

## How it works internally

MCP sessions (via the SDK's `anyio` cancel scopes) must be opened, used, and
closed on the **same asyncio task**. To guarantee that, `MCPServerManager` runs
the entire MCP lifecycle inside a single long-lived task on a dedicated
background thread:

- `start_servers()` spins up the thread + lifecycle task and blocks until ready.
- Tool calls are dispatched onto that task via `manager.run_coro(...)`, so every
  `session.call_tool` runs on the task that owns the session.
- `stop_servers()` signals shutdown; teardown (closing the `AsyncExitStack`)
  happens inside the same lifecycle task, then the thread joins.

This design is why you should always call tools through the executor
(`MCPToolExecutor`) rather than touching `session.call_tool` directly — the
executor routes through `run_coro` for you and adds timeout, per-case limits, and
error isolation.

---

## Troubleshooting

### Server fails to start
- Check the command exists: `which npx` / `which python3`
- Check required env vars are set (referenced via `${VAR_NAME}`)
- Look at the run logs — startup failures are logged per server

### Tools not discovered
- Confirm the server actually speaks MCP (the bundled mock uses the SDK; ad-hoc
  JSON-RPC scripts will fail SDK validation)
- Enable debug logging: `logging.getLogger("src.hephaestus.mcp").setLevel(logging.DEBUG)`

### "Tool execution timed out"
- Increase `tool_execution.timeout_seconds`
- Check the server isn't blocking on something external

### "Exceeded max_tool_calls limit"
- The per-case ceiling is `max_iterations * max_tool_calls_per_iteration`. Raise
  either value in `tool_execution` if a legitimately complex task needs more
  calls. (This limit is per-case; it does not accumulate across the run.)

### Eval hangs
- Lower `max_iterations` to bound the ReAct loop
- Verify the server reads stdin and responds (a server that never replies will
  hit the per-tool timeout rather than hang indefinitely)

---

## Reference

| Resource | Location |
|----------|----------|
| Working example tenant | `tenants/mcp_example/` |
| Agentic node factory | `src/hephaestus/chains/agentic_nodes.py` |
| MCP server manager | `src/hephaestus/mcp/manager.py` |
| Tool executor | `src/hephaestus/mcp/executor.py` |
| Mock MCP server (tests) | `tests/fixtures/mock_mcp_server.py` |
| Architecture & design | `docs/mcp-integration-plan.md` |
| End-to-end example doc | `docs/examples/mcp-react-example.md` |
