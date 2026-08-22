<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Example: ReAct Agent with MCP Tools

This example demonstrates a complete agentic workflow using FAPO with MCP integration.

## Scenario

Build an agent that can:
- Search the web for information
- Read/write files
- Answer complex questions requiring tool use

## Directory Structure

```
tenants/web_agent/
├── chains/
│   └── react_agent.py
├── prompts/
│   └── modules/
│       └── agent/
│           └── variant-001.md
├── datasets/
│   └── web_research_tasks.jsonl
├── code/
│   └── scorers/
│       └── task_scorer.py
├── configs/
│   └── eval.json
└── docs/
    └── iteration-playbook.md
```

---

## 1. Dataset: Web Research Tasks

**`tenants/web_agent/datasets/web_research_tasks.jsonl`**

```json
{"case_id": "1", "task_type": "research", "context": {"task": "What is the current population of Tokyo?"}, "expected": {"answer": "approximately 14 million", "tools_used": ["brave_web_search"]}, "metadata": {"difficulty": "easy"}}
{"case_id": "2", "task_type": "research", "context": {"task": "Find the latest stable version of Python and save it to info.txt"}, "expected": {"answer_contains": "Python 3.", "tools_used": ["brave_web_search", "write_file"]}, "metadata": {"difficulty": "medium"}}
{"case_id": "3", "task_type": "research", "context": {"task": "Compare the GDP of USA vs China in 2024 and create a summary file"}, "expected": {"answer_contains": "summary", "tools_used": ["brave_web_search", "write_file"]}, "metadata": {"difficulty": "hard"}}
```

---

## 2. MCP Server Configuration

The current config loader reads servers and tool execution settings directly
from the eval config; it does not load an MCP `config_path` indirection.
The following `mcp` object is embedded in `eval.json` below:

```json
{
  "servers": [
    {
      "name": "brave_search",
      "command": "npx",
      "args": ["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      },
      "enabled": true,
      "timeout_seconds": 30
    },
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/agent_workspace"],
      "env": {},
      "enabled": true,
      "timeout_seconds": 30
    }
  ],
  "tool_execution": {
    "max_iterations": 15,
    "max_tool_calls_per_iteration": 5,
    "timeout_seconds": 60
  }
}
```

This uses Brave's current official stdio package and tool naming:
[`@brave/brave-search-mcp-server` exposes `brave_web_search`](https://github.com/brave/brave-search-mcp-server/blob/main/README.md).
Install a current Node.js/npm runtime so `npx` is available.

---

## 3. Eval Configuration

**`tenants/web_agent/configs/eval.json`**

```json
{
  "tenant_id": "web_agent",
  "provider": "openai",
  "provider_settings": {
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": 4096
  },
  "mcp": {
    "servers": [
      {
        "name": "brave_search",
        "command": "npx",
        "args": ["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"],
        "env": {"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
        "enabled": true,
        "timeout_seconds": 30
      },
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/agent_workspace"],
        "env": {},
        "enabled": true,
        "timeout_seconds": 30
      }
    ],
    "tool_execution": {
      "max_iterations": 15,
      "max_tool_calls_per_iteration": 5,
      "timeout_seconds": 60
    }
  },
  "dataset": {
    "path": "tenants/web_agent/datasets/web_research_tasks.jsonl"
  },
  "chain": {
    "path": "tenants/web_agent/chains/react_agent.py",
    "fn": "build_chain",
    "config": {
      "prompt_paths": {
        "agent": "tenants/web_agent/prompts/modules/agent/variant-001.md"
      },
      "agent_limits": {
        "max_iterations": 15,
        "max_tool_calls_per_iteration": 5
      }
    }
  },
  "scoring_profile": {
    "scorer": {
      "module_path": "tenants/web_agent/code/scorers/task_scorer.py",
      "class_name": "TaskScorer"
    }
  },
  "output_dir": "tenants/web_agent/evals/run-001",
  "max_workers": 1
}
```

`mcp.tool_execution` is parsed and recorded, but is not automatically wired
into this tenant chain. `agent_limits` below is the explicit node configuration
that controls this example's ReAct limit.

---

## 4. ReAct Chain

**`tenants/web_agent/chains/react_agent.py`**

```python
# Copyright 2026 Cisco Systems, Inc. and its affiliates
# SPDX-License-Identifier: Apache-2.0

"""ReAct agent chain with MCP tool access."""

from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, StateGraph

from src.hephaestus.chains.agentic_nodes import make_agentic_node
from src.hephaestus.chains.types import ChainState


def build_chain(provider, config, mcp_manager=None):
    """Build a single-node ReAct agent with access to web search and filesystem tools.
    
    The agent uses a thought-action-observation loop:
    1. Thought: reason about what information is needed
    2. Action: call appropriate tool(s)
    3. Observation: analyze tool results
    4. Repeat until task is complete
    """
    if mcp_manager is None:
        raise ValueError(
            "This chain requires MCP support. "
            "Add 'mcp' section to your eval config."
        )
    
    prompt_path = Path(config["prompt_paths"]["agent"])
    limits = config["agent_limits"]
    graph = StateGraph(ChainState)
    
    graph.add_node(
        "agent",
        make_agentic_node(
            provider=provider,
            prompt_template_path=prompt_path,
            mcp_manager=mcp_manager,
            output_key="answer",
            max_iterations=limits["max_iterations"],
            max_tool_calls_per_iteration=limits["max_tool_calls_per_iteration"],
        )
    )
    
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    
    return graph.compile()
```

---

## 5. Agent Prompt

**`tenants/web_agent/prompts/modules/agent/variant-001.md`**

```markdown
System: You are a helpful research assistant with access to web search and file system tools.

Follow the ReAct (Reasoning + Acting) pattern:
1. **Thought**: Reason about what information you need
2. **Action**: Use available tools to gather information or complete tasks
3. **Observation**: Analyze the results
4. Repeat until you can answer the question

Available tools:
- **brave_web_search**: Search the web for current information
- **write_file**: Save information to a file
- **read_file**: Read contents of a file
- **list_directory**: List files in a directory

Guidelines:
- Always search for current information rather than relying on training data
- Break complex tasks into smaller steps
- Verify information from multiple sources when possible
- Save important findings to files when the task requires it
- Provide your final answer after the word "Answer:"

User: ${task}

Think step-by-step and use tools as needed to complete this task.
```

---

## 6. Scorer

**`tenants/web_agent/code/scorers/task_scorer.py`**

```python
# Copyright 2026 Cisco Systems, Inc. and its affiliates
# SPDX-License-Identifier: Apache-2.0

from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class TaskScorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        """Verify case has required fields."""
        assert "task" in case.context, f"Case {case.case_id}: missing 'task'"
        assert "answer" in case.expected or "answer_contains" in case.expected
        tools_used = case.expected.get("tools_used", [])
        assert isinstance(tools_used, list) and all(isinstance(name, str) for name in tools_used)
    
    def score_case(self, case, output_text, scoring_profile):
        """Fallback for non-agentic use; no tool trajectory is available."""
        return self._score(case.expected, output_text.lower(), [])

    def score_pipeline_case(
        self, case, step_outputs, scoring_profile, output_text=None, tool_call_history=None
    ):
        output_lower = (output_text or "").lower()
        return self._score(case.expected, output_lower, tool_call_history or [])

    def _score(self, expected, output_lower, tool_call_history):
        answer_present = 100.0 if "answer:" in output_lower else 0.0
        answer_quality = 0.0
        if "answer" in expected and expected["answer"].lower() in output_lower:
            answer_quality = 100.0
        elif "answer_contains" in expected and expected["answer_contains"].lower() in output_lower:
            answer_quality = 100.0

        actual_tools = {item["tool"] for item in tool_call_history if not item.get("error")}
        required_tools = set(expected.get("tools_used", []))
        tool_usage_score = (
            100.0 if required_tools <= actual_tools else 0.0
        )
        efficiency = max(0.0, 100.0 - 10.0 * max(0, len(tool_call_history) - len(required_tools)))

        # This scorer does not assume tool usage from answer quality; it reads
        # the actual recorded trajectory supplied by score_pipeline_case.
        composite = (
            0.2 * answer_present +
            0.5 * answer_quality +
            0.2 * tool_usage_score +
            0.1 * efficiency
        )
        
        return {
            "composite_score": composite,
            "score_breakdown": {
                "answer_present": answer_present,
                "answer_quality": answer_quality,
                "tool_usage": tool_usage_score,
                "efficiency": efficiency,
            }
        }
```

---

## 7. Running the Evaluation

```bash
# Set up environment
export BRAVE_API_KEY="your_brave_api_key"
export OPENAI_API_KEY="your_openai_key"

# Create workspace directory for filesystem tool
mkdir -p /tmp/agent_workspace

# Run evaluation
python -m hephaestus.cli eval --config tenants/web_agent/configs/eval.json

# Check results
cat tenants/web_agent/evals/run-001/summary.md
```

---

## 8. Expected Output Structure

**`tenants/web_agent/evals/run-001/results.jsonl`** (excerpt):

```json
{
  "case_id": "1",
  "task_type": "research",
  "output_text": "Answer: The current population of Tokyo is approximately 14 million people in the city proper.",
  "step_outputs": {
    "answer": "Answer: The current population of Tokyo is approximately 14 million people in the city proper."
  },
  "composite_score": 100.0,
  "execution_status": "succeeded",
  "score_breakdown": {
    "answer_present": 100.0,
    "answer_quality": 100.0,
    "tool_usage": 100.0,
    "efficiency": 100.0
  },
  "tool_call_history": [
    {
      "tool": "brave_web_search",
      "arguments": {"query": "Tokyo population 2024"},
      "result_length": 1523,
      "error": null,
      "iteration": 1
    }
  ],
  "total_tool_calls": 1,
  "failed_tool_calls": 0,
  "diagnostics": [
    "Agentic node 'answer': 2 iterations, 1 tool calls total"
  ]
}
```

The standard agentic node stores the final model response in both
`output_text` and `step_outputs["answer"]`. Earlier reasoning and observations
remain available in `tool_call_history`; the node does not concatenate them
into the final response.

---

## 9. Optimization Loop

Once you have baseline results, run the optimization agent:

```bash
# In Claude Code
> /optimization
  → Tenant: web_agent
  → Config: tenants/web_agent/configs/eval.json
  → Success criteria: composite_score >= 90
```

The agent will:
1. Analyze failures (missing tool calls, inefficient searches, poor answers)
2. Create variant-002 with improved ReAct prompting
3. Run eval and compare
4. Iterate until target score reached

Example iterations:
- **variant-001** (baseline): Generic ReAct prompt → 72% composite
- **variant-002**: Add tool selection guidance → 85% composite
- **variant-003**: Add answer formatting rules → 92% composite ✓

---

## 10. Advanced Patterns

### Multi-Step with Verification

```python
def build_chain(provider, config, mcp_manager):
    graph = StateGraph(ChainState)
    
    # Main agent loop
    graph.add_node("research", make_agentic_node(...))
    
    # Verification step (no tools, just LLM)
    graph.add_node("verify", make_llm_node(...))
    
    # Conditional routing
    def should_retry(state):
        return "retry" if "uncertain" in state["output_text"].lower() else "done"
    
    graph.set_entry_point("research")
    graph.add_edge("research", "verify")
    graph.add_conditional_edges("verify", should_retry, {
        "retry": "research",
        "done": END
    })
    
    return graph.compile()
```

### Tool-Specific Nodes

`make_agentic_node` currently exposes all tools discovered through its supplied
MCP manager. It does not accept an `allowed_tools` argument. Use separate MCP
manager/configuration instances or implement a chain-level policy before
constructing a node when a tenant needs tool restriction.

```python
def build_chain(provider, config, mcp_manager):
    graph = StateGraph(ChainState)
    
    # Separate nodes can use separately configured MCP managers.
    graph.add_node("web_research", make_agentic_node(
        ...
    ))
    
    graph.add_node("file_operations", make_agentic_node(
        ...
    ))
    
    graph.add_node("synthesize", make_llm_node(...))
    
    # Linear flow
    graph.set_entry_point("web_research")
    graph.add_edge("web_research", "file_operations")
    graph.add_edge("file_operations", "synthesize")
    graph.add_edge("synthesize", END)
    
    return graph.compile()
```

---

## Summary

This example demonstrates:
- ✅ MCP server configuration and lifecycle management
- ✅ ReAct-style agentic node with tool calling loop
- ✅ Tool call tracking in evaluation results
- ✅ Scoring that considers tool usage and efficiency
- ✅ Optimization loop for improving agentic prompts
- ✅ Conditional routing for advanced patterns

The same patterns apply to any MCP-enabled workflow: code execution, database queries, API calls, etc.
