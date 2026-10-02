<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Agentic Chain Patterns

## Purpose

Catalog of reusable agentic chain patterns — building blocks and optimization targets for multi-step LLM workflows.

Use this when:
- Failure analysis suggests the chain structure (not just prompt text) needs to change.
- You need to select a reasoning/control strategy for a new chain.
- You want to understand what's tunable in each pattern.

Related:
- For prompt-writing principles, see `external-prompting-guides.md`.
- For evaluation methods, see `evaluation-and-benchmarks.md`.

## Pattern Catalog

### ReAct (Reason + Act)

Interleaves reasoning traces with tool actions in a loop.

**Structure:**
```
Loop:
  Thought: reasoning about next step
  Action: tool_name(args)
  Observation: tool_result
Until confident → Final answer
```

**When to use:** Tasks requiring external information retrieval or tool interaction during reasoning. Reduces hallucination by grounding reasoning in tool outputs.

**What's tunable:**
- Step budget (max iterations before forced stop)
- Tool schema instructions and descriptions
- Thought format constraints (brief vs detailed)
- Stop conditions and confidence criteria
- Error recovery policy for failed tool calls

**Primary sources:** Yao et al. 2022

### Reflexion

Adds self-reflection memory to improve future attempts after failures. A form of "verbal reinforcement learning."

**Structure:**
```
Attempt → Evaluate → If fail:
  Reflect: describe mistake + plan to avoid
  Store reflection in memory
  Retry with reflection context appended
```

**When to use:** Tasks where first attempts frequently fail and retry with learned lessons improves outcomes. Useful when you can evaluate attempt quality automatically.

**What's tunable:**
- Reflection prompt (what to focus on when analyzing failure)
- Memory format and capacity (how many reflections to retain)
- Retry budget and escalation rules
- Evaluation criteria for triggering reflection

**Primary sources:** Shinn et al. 2023

### Tree of Thoughts (ToT)

Generalizes chain-of-thought to search over "thoughts" with lookahead and backtracking.

**Structure:**
```
Generate K candidate thoughts →
Score/evaluate each thought →
Expand best thoughts (BFS or DFS) →
Backtrack if dead end →
Final answer from best path
```

**When to use:** Tasks requiring exploration (e.g., planning, puzzle-solving, creative generation) where a single reasoning path is insufficient.

**What's tunable:**
- Branching factor (K candidates per step)
- Search strategy (BFS vs DFS)
- Scoring heuristic for thought evaluation
- Depth limit and backtracking criteria
- Aggregation method for final answer

**Primary sources:** Yao et al. 2023

### Self-Refine

Iteratively generates, critiques, and revises output without external training data.

**Structure:**
```
Generate initial output →
Loop:
  Critique: identify specific flaws
  Refine: address flaws while preserving strengths
Until critique finds no major issues or budget exhausted
```

**When to use:** Tasks where output quality improves with iterative polishing (writing, code generation, structured data extraction). Works when the model can reliably identify its own errors.

**What's tunable:**
- Critique prompt (what dimensions to evaluate)
- Refinement prompt (how to incorporate feedback)
- Iteration budget
- Stop criteria (quality threshold or diminishing returns)

**Primary sources:** Madaan et al. 2023

### Least-to-Most Prompting

Decomposes complex problems into simpler subproblems, solves them in order, and uses earlier solutions as context.

**Structure:**
```
Decompose: break problem into ordered subproblems →
For each subproblem (easy to hard):
  Solve using prior solutions as context →
Combine into final answer
```

**When to use:** Tasks with easy-to-hard generalization gaps where direct prompting fails on complex instances but succeeds on simpler components.

**What's tunable:**
- Decomposition prompt (granularity of subproblems)
- Context passing strategy (which prior solutions to include)
- Composition rules for final answer

**Primary sources:** Zhou et al. 2022

### Plan-and-Solve

Explicitly separates planning from execution to reduce missing-step and calculation errors.

**Structure:**
```
Plan: enumerate steps needed to solve the task →
Execute: carry out each step sequentially →
Verify: check plan completion and answer consistency
```

**When to use:** Multi-step reasoning tasks where the model skips steps or loses track of the overall strategy. Particularly effective for math and logic problems.

**What's tunable:**
- Planning prompt (level of detail, format)
- Execution prompt (how to reference the plan)
- Verification criteria
- Re-planning triggers (when to revise the plan mid-execution)

**Primary sources:** Wang et al. 2023

### Tool-Augmented Generation

Trains or prompts models to decide when and how to call external APIs/tools during generation.

**Structure:**
```
Generate tokens →
When tool call is needed:
  Select tool + construct arguments →
  Execute tool →
  Incorporate result into generation →
Continue generation
```

**When to use:** Tasks requiring access to external data, computation, or actions that the model cannot perform internally (search, calculation, database queries).

**What's tunable:**
- Tool definitions and schemas (descriptions, parameter constraints)
- Tool selection strategy (when to call vs answer directly)
- Error recovery policy (retry with corrected args, fallback to different tool)
- Tool permission boundaries (which tools are allowed in which contexts)

**Primary sources:** Schick et al. 2023 (Toolformer)

## Pattern Selection Guide

Match failure modes to patterns:

| Failure mode | Suggested pattern | Why |
|---|---|---|
| Hallucination / ungrounded claims | ReAct | Grounds reasoning in retrieved/tool evidence |
| Repeated mistakes on similar tasks | Reflexion | Learns from past failures via memory |
| Single reasoning path insufficient | Tree of Thoughts | Explores multiple paths with backtracking |
| Output quality improves with revision | Self-Refine | Iterative critique and refinement |
| Complex tasks with missing steps | Plan-and-Solve | Explicit planning prevents step-skipping |
| Hard tasks decomposable into easy parts | Least-to-Most | Solves subproblems incrementally |
| External data/computation needed | Tool-Augmented / ReAct | Routes to tools when internal knowledge is insufficient |
| Multi-turn interaction drift | Reflexion + Plan-and-Solve | Reflection catches drift; plan maintains coherence |

## Combining Patterns

Patterns are composable. Common combinations:
- **ReAct + Self-Refine**: Use tools to gather evidence, then iteratively refine the answer.
- **Plan-and-Solve + ReAct**: Plan the approach, then execute steps with tool access.
- **Reflexion + any pattern**: Add reflection memory to any pattern for retry improvement.
- **Least-to-Most + Tool-Augmented**: Decompose, then use tools for each subproblem.

## FAFO Mapping

| Pattern | Current chain support | How to apply |
|---|---|---|
| Direct prompting (baseline) | Single-prompt chains in `tenants/<id>/prompts/variants/` | Default starting point for all tenants. |
| Plan-and-Solve | Multi-step chains with planner + executor modules | Structure prompt modules as plan → execute → verify steps. |
| Self-Refine | Multi-step chains with draft + critique + refine modules | Add critique and refinement steps to existing chains. |
| ReAct | Multi-step chains with tool integration | Requires tool-calling chain module; add reasoning + tool loop. |
| Reflexion | Not directly supported | Would need memory persistence across eval cases or retry logic within a chain. Flag for future infra work. |
| Tree of Thoughts | Not directly supported | Would need branching/sampling within a chain step. Flag for future infra work. |

When the optimization agent identifies a failure mode that suggests a pattern change (see Pattern Selection Guide above), it can implement the change directly when the tenant playbook allows structural changes, or flag it in the "Recommendations" section of its report otherwise.

## Source Links

- ReAct: https://arxiv.org/abs/2210.03629
- Reflexion: https://arxiv.org/abs/2303.11366
- Tree of Thoughts: https://arxiv.org/abs/2305.10601
- Self-Refine: https://arxiv.org/abs/2303.17651
- Least-to-Most: https://arxiv.org/abs/2205.10625
- Plan-and-Solve: https://arxiv.org/abs/2305.04091
- Toolformer: https://arxiv.org/abs/2302.04761
- Chain-of-thought: https://arxiv.org/abs/2201.11903
- Self-consistency: https://arxiv.org/abs/2203.11171

Retrieval date for this source set: March 6, 2026.
