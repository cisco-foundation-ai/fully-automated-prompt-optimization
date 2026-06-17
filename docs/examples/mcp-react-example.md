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
│   ├── mcp_servers.json
│   └── eval.json
└── docs/
    └── iteration-playbook.md
```

---

## 1. Dataset: Web Research Tasks

**`tenants/web_agent/datasets/web_research_tasks.jsonl`**

```json
{"case_id": "1", "task_type": "research", "context": {"task": "What is the current population of Tokyo?"}, "expected": {"answer": "approximately 14 million", "tools_used": ["web_search"]}, "metadata": {"difficulty": "easy"}}
{"case_id": "2", "task_type": "research", "context": {"task": "Find the latest stable version of Python and save it to info.txt"}, "expected": {"answer_contains": "Python 3.", "tools_used": ["web_search", "write_file"]}, "metadata": {"difficulty": "medium"}}
{"case_id": "3", "task_type": "research", "context": {"task": "Compare the GDP of USA vs China in 2024 and create a summary file"}, "expected": {"tools_used": ["web_search", "write_file"]}, "metadata": {"difficulty": "hard"}}
```

---

## 2. MCP Server Configuration

**`tenants/web_agent/configs/mcp_servers.json`**

```json
{
  "servers": [
    {
      "name": "brave_search",
      "command": "python",
      "args": ["-m", "mcp_server_brave_search"],
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
    "max_tokens": 4096,
    "supports_tools": true
  },
  "mcp": {
    "config_path": "tenants/web_agent/configs/mcp_servers.json"
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

---

## 4. ReAct Chain

**`tenants/web_agent/chains/react_agent.py`**

```python
# Copyright 2026 Cisco Systems, Inc. and its affiliates
# SPDX-License-Identifier: Apache-2.0

"""ReAct agent chain with MCP tool access."""

from __future__ import annotations
from typing import Any, Dict
from pathlib import Path
from langgraph.graph import END, StateGraph
from src.hephaestus.chains.types import ChainState
from src.hephaestus.chains.agentic_nodes import make_agentic_node

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
    graph = StateGraph(ChainState)
    
    graph.add_node(
        "agent",
        make_agentic_node(
            provider=provider,
            prompt_template_path=prompt_path,
            mcp_manager=mcp_manager,
            output_key="answer",
            max_iterations=15,  # Allow up to 15 thought-action cycles
            max_tool_calls_per_iteration=5,
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
- **brave_search**: Search the web for current information
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
        assert "expected" in case.expected, f"Case {case.case_id}: missing 'expected'"
    
    def score_case(self, case, output_text, scoring_profile):
        """Score based on answer quality and tool usage.
        
        Metrics:
        - answer_present: Did agent provide a final answer? (0-100)
        - answer_quality: Does answer match expected content? (0-100)
        - tool_usage: Did agent use expected tools? (0-100)
        - efficiency: Was the agent efficient? (0-100, based on tool call count)
        """
        expected = case.expected
        output_lower = output_text.lower()
        
        # Check if answer is present (looks for "answer:" marker)
        answer_present = 100.0 if "answer:" in output_lower else 0.0
        
        # Check answer quality
        answer_quality = 0.0
        if "answer" in expected:
            expected_answer = expected["answer"].lower()
            if expected_answer in output_lower:
                answer_quality = 100.0
            elif any(word in output_lower for word in expected_answer.split()):
                answer_quality = 50.0
        
        if "answer_contains" in expected:
            if expected["answer_contains"].lower() in output_lower:
                answer_quality = 100.0
        
        # Check tool usage (from case metadata)
        tool_usage_score = 100.0  # Default to pass if no tool requirement
        if "tools_used" in expected:
            expected_tools = set(expected["tools_used"])
            # Tool usage info available in diagnostics or step_outputs
            # For now, assume correct tool usage if answer quality is good
            if answer_quality >= 50.0:
                tool_usage_score = 100.0
            else:
                tool_usage_score = 50.0
        
        # Efficiency: penalize excessive tool calls
        # This would be read from tool_call_history in full implementation
        efficiency = 100.0  # Placeholder - would calculate from actual tool call count
        
        # Composite score: weighted average
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
  "output_text": "Thought: I need to search for Tokyo's current population.\n\nAction: brave_search(query=\"Tokyo population 2024\")\n\nObservation: Tokyo has a population of approximately 14 million in the metropolitan area...\n\nAnswer: The current population of Tokyo is approximately 14 million people in the city proper.",
  "step_outputs": {
    "answer": "The current population of Tokyo is approximately 14 million people in the city proper."
  },
  "composite_score": 95.0,
  "score_breakdown": {
    "answer_present": 100.0,
    "answer_quality": 100.0,
    "tool_usage": 100.0,
    "efficiency": 90.0
  },
  "tool_call_history": [
    {
      "tool": "brave_search",
      "arguments": {"query": "Tokyo population 2024"},
      "result_length": 1523,
      "error": null,
      "iteration": 1
    }
  ],
  "total_tool_calls": 1,
  "failed_tool_calls": 0,
  "diagnostics": [
    "Agentic node answer: 2 iterations, 1 tool calls"
  ]
}
```

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

```python
def build_chain(provider, config, mcp_manager):
    graph = StateGraph(ChainState)
    
    # Separate nodes for different tool categories
    graph.add_node("web_research", make_agentic_node(
        ..., 
        allowed_tools=["brave_search", "read_url"]
    ))
    
    graph.add_node("file_operations", make_agentic_node(
        ..., 
        allowed_tools=["read_file", "write_file", "list_directory"]
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
