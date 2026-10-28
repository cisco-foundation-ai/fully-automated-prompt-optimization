<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# MCP Quick Start Guide

FAFO evaluates agentic chains whose model calls tools exposed by
[Model Context Protocol](https://modelcontextprotocol.io/) servers, using a real
ReAct loop. The protocol is implemented with the official `mcp` Python SDK;
nothing is stubbed. This guide runs the example tenant, then builds a new
agentic tenant.

What FAFO provides:

- MCP server lifecycle management (start, tool discovery, execution, clean shutdown)
- A ReAct agentic node (`make_agentic_node`) with iterative tool calling
- Per-case tool-call limits and per-tool timeouts
- Full tool-call tracking in eval results (`tool_call_history`, `total_tool_calls`, `failed_tool_calls`)
- Tool-failure attribution in step analysis

## Prerequisites

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .          # installs mcp>=1.0.0 and httpx as core deps
export OPENAI_API_KEY="<your-openai-api-key>"
```

## Run the example tenant after supplying its dataset

An implementation scaffold lives at `tenants/mcp_example/`. The checkout does
not include `tenants/mcp_example/datasets/tool_tasks.jsonl`, so that tenant is
not a self-contained runnable fixture until you supply a contract-valid JSONL
dataset at the configured path.

First supply that file using the schema in
`tenants/mcp_example/docs/data-contract.md`. Without it, the command below
intentionally fails dataset-path preflight. Once it exists, run:

```bash
python3 -m hephaestus.cli eval --config tenants/mcp_example/configs/eval.json
```

The tenant uses a bundled mock MCP server (`tests/fixtures/mock_mcp_server.py`,
built on the MCP SDK) that exposes three tools: `echo`, `add`, and `fail` (for
exercising error handling). A supplied dataset can mix tool-use tasks with
reasoning tasks the agent should answer *without* tools.

Expected behavior:

- The mock MCP server starts and 3 tools are discovered.
- Each case runs through the ReAct agentic node.
- Tool calls are executed for real and tracked.
- Results include `tool_call_history`.
- The MCP server shuts down cleanly at the end.

Check the results:

```bash
cat tenants/mcp_example/evals/run-001/summary.md
head -n 1 tenants/mcp_example/evals/run-001/results.jsonl | python3 -m json.tool
```

`results.jsonl` holds one JSON object per line, so `python3 -m json.tool` must
receive one selected line rather than the whole multi-row file.

## Building your own agentic tenant

### 1. Add an `mcp` section to the eval config

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
      "prompt_paths": {"agent": "tenants/my_agent/prompts/agent.md"},
      "agent_limits": {
        "max_iterations": 10,
        "max_tool_calls_per_iteration": 5
      }
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

| `mcp` field | Meaning |
|-------|---------|
| `servers[].name` | Unique server identifier |
| `servers[].command` / `args` | How to launch the server (stdio transport) |
| `servers[].env` | Env vars for the server process. Supports `${VAR_NAME}` substitution from your environment (e.g. `{"BRAVE_API_KEY": "${BRAVE_API_KEY}"}`) |
| `servers[].enabled` | Set `false` to skip a server without deleting its config |
| `servers[].timeout_seconds` | Contributes to the manager's aggregate startup-ready wait ceiling; it is not a per-server connection deadline |
| `tool_execution.max_iterations` | Parsed MCP configuration/provenance fact; not automatically a node limit |
| `tool_execution.max_tool_calls_per_iteration` | Parsed MCP configuration/provenance fact; not automatically a node limit |
| `tool_execution.timeout_seconds` | Parsed MCP configuration/provenance fact; not automatically an executor timeout |

The `agent_limits` block in the example is ordinary tenant chain config; the
chain in step 2 passes it explicitly to `make_agentic_node`.

Tool support also depends on the configured provider: OpenAI non-reasoning
models forward tool schemas, while `o1`, `o3`, `o4`, `gpt-5`, `gpt5`, Baseten,
and SageMaker currently follow the text-only path. See the
[tool-calling matrix](config-schema.md#tool-calling-matrix).

#### Limits and timeouts

Top-level `mcp.tool_execution` is recorded but not applied to a tenant node or
executor. The current runner does not automatically wire `mcp.tool_execution`
into a generic tenant factory, `make_agentic_node`, or `MCPToolExecutor`;
explicit `make_agentic_node` arguments control the ReAct limits.
**Do not change top-level `mcp.tool_execution` to alter a node or executor**.

- **Per-case tool calls.** The node derives its per-case executor ceiling as
  `max_iterations * max_tool_calls_per_iteration`. A fresh executor makes that
  ceiling per-case rather than cumulative across the run. A top-level
  `max_tool_calls` is not wired into the MCP executor.
- **Server startup.** The manager uses one aggregate startup-ready wait ceiling
  equal to the maximum enabled-server value plus 30 seconds (or 60 seconds when
  no enabled-server value is available). It does not enforce a per-server
  connection deadline.
- **Tool-call timeout.** The standard `make_agentic_node` always uses the
  executor's 30-second default because that node has no executor-timeout
  argument. Changing the executor timeout requires a custom agentic node that
  constructs `MCPToolExecutor(timeout_seconds=...)` (or a future factory
  interface that exposes the timeout). Creating a separate `MCPToolExecutor`
  does not affect the executor constructed inside the standard node.

`mcp.tool_execution.timeout_seconds` does not change either timeout boundary.

### 2. Write the chain

Your `build_chain` factory must accept an optional `mcp_manager` parameter. When
it is present, use `make_agentic_node`; otherwise fall back to a plain LLM node
so the chain still works without MCP.

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
    limits = config["agent_limits"]
    graph = StateGraph(ChainState)

    if mcp_manager:
        graph.add_node(
            "agent",
            make_agentic_node(
                provider=provider,
                prompt_template_path=prompt_path,
                mcp_manager=mcp_manager,
                output_key="answer",
                max_iterations=limits["max_iterations"],
                max_tool_calls_per_iteration=limits["max_tool_calls_per_iteration"],
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

The eval runner inspects the factory signature and passes `mcp_manager` only if
the parameter exists, so existing non-MCP chains keep working unchanged. See
`tenants/mcp_example/chains/react_agent.py` for the working reference.

### 3. Write the agent prompt

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

Tool schemas are discovered from the MCP server automatically; you do not list
them in config. They are forwarded to the model only when the selected
provider/model tool-calling capability supports it; unsupported models take the
text-only fallback. The prompt only guides *when* to use them.

### 4. Score with tool awareness (optional)

To score actual tool usage, override `score_pipeline_case`, which receives
`tool_call_history`:

```python
def score_pipeline_case(self, case, step_outputs, scoring_profile,
                        output_text=None, tool_call_history=None):
    actual_tools = [tc["tool"] for tc in (tool_call_history or [])
                    if not tc.get("error")]
    # ... compare against case.expected["tools_used"], etc.
```

`tenants/mcp_example/code/scorers/` has a full example: a `TrajectoryScorer`
(order/argument-aware tool checks), an `LLMJudgeScorer` (LLM-as-judge answer
correctness), and a `CompositeScorer` that combines them with configurable
weights.

### 5. Run it

```bash
python3 -m hephaestus.cli eval --config tenants/my_agent/configs/eval.json
```

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

Failed tool calls are surfaced in deterministic runtime attribution
(`src/hephaestus/analysis/step_attribution.py`) under a small safe category
allowlist. A later optimizer may perform semantic failure analysis, but that is
not a runtime tool-error judgment.

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

## How it works internally

MCP sessions (via the SDK's `anyio` cancel scopes) must be opened, used, and
closed on the **same asyncio task**. `MCPServerManager` guarantees this by
running the entire MCP lifecycle inside one long-lived task on a dedicated
background thread:

- `start_servers()` starts the thread and lifecycle task and blocks until ready.
- Tool calls are dispatched onto that task via `manager.run_coro(...)`, so every
  `session.call_tool` runs on the task that owns the session.
- `stop_servers()` signals shutdown; teardown (closing the `AsyncExitStack`)
  happens inside the same lifecycle task, then the thread joins.

Always call tools through the executor (`MCPToolExecutor`), not
`session.call_tool` directly. The executor routes through `run_coro` and adds
timeout, per-case limits, and error isolation.

## Troubleshooting

### Server fails to start

- Check the command exists: `which npx` / `which python3`.
- Check required env vars (referenced via `${VAR_NAME}`) are set.
- Read the run logs; startup failures are logged per server.

### Tools not discovered

- Confirm the server actually speaks MCP. The bundled mock uses the SDK; ad-hoc
  JSON-RPC scripts will fail SDK validation.
- Enable debug logging: `logging.getLogger("src.hephaestus.mcp").setLevel(logging.DEBUG)`

### "Tool execution timed out"

- The standard node uses a 30-second per-call timeout. To change it, implement a
  custom agentic node that constructs `MCPToolExecutor(timeout_seconds=...)`;
  the top-level `mcp.tool_execution.timeout_seconds` is not wired into that
  executor. See [Limits and timeouts](#limits-and-timeouts).
- Check the server isn't blocking on something external.

### "Exceeded max_tool_calls limit"

- The per-case ceiling is `max_iterations * max_tool_calls_per_iteration`. If a
  legitimately complex task needs more calls, raise either explicit
  `make_agentic_node` argument in the tenant chain. The limit is per-case; it
  does not accumulate across the run.

### Eval hangs

- Lower the explicit `make_agentic_node(max_iterations=...)` setting to bound
  the ReAct loop.
- Verify the server reads stdin and responds. A server that never replies hits
  the standard node's 30-second per-tool timeout rather than hanging
  indefinitely.

## Reference

| Resource | Location |
|----------|----------|
| Example tenant (scaffold; supply its dataset) | `tenants/mcp_example/` |
| Agentic node factory | `src/hephaestus/chains/agentic_nodes.py` |
| MCP server manager | `src/hephaestus/mcp/manager.py` |
| Tool executor | `src/hephaestus/mcp/executor.py` |
| Mock MCP server (tests) | `tests/fixtures/mock_mcp_server.py` |
| End-to-end example doc | [`docs/examples/mcp-react-example.md`](examples/mcp-react-example.md) |
