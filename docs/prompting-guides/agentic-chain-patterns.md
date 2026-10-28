<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Agentic chain patterns

Reusable chain patterns for multi-step LLM workflows: what each one is for and
what you can tune. Use this catalog when failure analysis shows that the chain
structure, not just the prompt text, needs to change, or when you choose a
reasoning and control strategy for a new chain.

This catalog is also the pattern allowlist for structural variants. The
optimization agent uses only these patterns; a novel pattern needs user
approval. See [chain variant conventions](../processes/chain-variant-conventions.md).

Related: [prompting principles](external-prompting-guides.md) and
[evaluation methods](evaluation-and-benchmarks.md).

## Pattern catalog

### ReAct (Reason + Act)

Interleaves reasoning with tool actions in a loop.

```text
Loop:
  Thought: reasoning about next step
  Action: tool_name(args)
  Observation: tool_result
Until confident → Final answer
```

- **Use when:** the task needs external information or tool interaction during
  reasoning. Grounding reasoning in tool output reduces hallucination.
- **Tunable:** step budget (max iterations before a forced stop); tool schema
  instructions and descriptions; thought format (brief or detailed); stop
  conditions and confidence criteria; error recovery for failed tool calls.
- **Source:** [Yao et al. 2022](https://arxiv.org/abs/2210.03629)

### Reflexion

Adds self-reflection memory so later attempts learn from failures, a form of
"verbal reinforcement learning".

```text
Attempt → Evaluate → If fail:
  Reflect: describe mistake + plan to avoid
  Store reflection in memory
  Retry with reflection context appended
```

- **Use when:** first attempts often fail and a retry with learned lessons does
  better. Works best when attempt quality can be evaluated automatically.
- **Tunable:** reflection prompt (what to look for in a failure); memory format
  and capacity (how many reflections to keep); retry budget and escalation
  rules; criteria that trigger reflection.
- **Source:** [Shinn et al. 2023](https://arxiv.org/abs/2303.11366)

### Tree of Thoughts (ToT)

Generalizes chain-of-thought into a search over "thoughts", with lookahead and
backtracking.

```text
Generate K candidate thoughts →
Score/evaluate each thought →
Expand best thoughts (BFS or DFS) →
Backtrack if dead end →
Final answer from best path
```

- **Use when:** the task needs exploration (planning, puzzle-solving, creative
  generation) and one reasoning path is not enough.
- **Tunable:** branching factor (K candidates per step); search strategy (BFS or
  DFS); scoring heuristic for thoughts; depth limit and backtracking criteria;
  how the final answer is aggregated.
- **Source:** [Yao et al. 2023](https://arxiv.org/abs/2305.10601)

### Self-Refine

Generates, critiques, and revises its own output, without external training
data.

```text
Generate initial output →
Loop:
  Critique: identify specific flaws
  Refine: address flaws while preserving strengths
Until critique finds no major issues or budget exhausted
```

- **Use when:** output improves with polishing (writing, code generation,
  structured data extraction) and the model can reliably spot its own errors.
- **Tunable:** critique prompt (dimensions to evaluate); refinement prompt (how
  to apply feedback); iteration budget; stop criteria (quality threshold or
  diminishing returns).
- **Source:** [Madaan et al. 2023](https://arxiv.org/abs/2303.17651)

### Least-to-Most Prompting

Breaks a complex problem into simpler subproblems, solves them in order, and
feeds earlier solutions into later ones.

```text
Decompose: break problem into ordered subproblems →
For each subproblem (easy to hard):
  Solve using prior solutions as context →
Combine into final answer
```

- **Use when:** there is an easy-to-hard generalization gap: direct prompting
  fails on complex instances but succeeds on their simpler parts.
- **Tunable:** decomposition prompt (subproblem granularity); context passing
  (which prior solutions to include); composition rules for the final answer.
- **Source:** [Zhou et al. 2022](https://arxiv.org/abs/2205.10625)

### Plan-and-Solve

Separates planning from execution to reduce missing-step and calculation
errors.

```text
Plan: enumerate steps needed to solve the task →
Execute: carry out each step sequentially →
Verify: check plan completion and answer consistency
```

- **Use when:** in multi-step reasoning the model skips steps or loses track of
  the overall strategy. Especially effective for math and logic problems.
- **Tunable:** planning prompt (detail level, format); execution prompt (how it
  references the plan); verification criteria; re-planning triggers (when to
  revise the plan mid-execution).
- **Source:** [Wang et al. 2023](https://arxiv.org/abs/2305.04091)

### Tool-Augmented Generation

Trains or prompts the model to decide when and how to call external APIs or
tools during generation.

```text
Generate tokens →
When tool call is needed:
  Select tool + construct arguments →
  Execute tool →
  Incorporate result into generation →
Continue generation
```

- **Use when:** the task needs data, computation, or actions the model cannot
  perform itself (search, calculation, database queries).
- **Tunable:** tool definitions and schemas (descriptions, parameter
  constraints); tool selection (when to call a tool versus answer directly);
  error recovery (retry with corrected arguments, fall back to another tool);
  tool permission boundaries (which tools are allowed in which contexts).
- **Source:** [Schick et al. 2023 (Toolformer)](https://arxiv.org/abs/2302.04761)

## Pattern selection guide

| Failure mode | Suggested pattern | Why |
|---|---|---|
| Hallucination / ungrounded claims | ReAct | Grounds reasoning in retrieved or tool evidence |
| Repeated mistakes on similar tasks | Reflexion | Learns from past failures through memory |
| Single reasoning path insufficient | Tree of Thoughts | Explores multiple paths with backtracking |
| Output quality improves with revision | Self-Refine | Iterative critique and refinement |
| Complex tasks with missing steps | Plan-and-Solve | Explicit planning prevents skipped steps |
| Hard tasks decomposable into easy parts | Least-to-Most | Solves subproblems incrementally |
| External data or computation needed | Tool-Augmented / ReAct | Routes to tools when internal knowledge is insufficient |
| Multi-turn interaction drift | Reflexion + Plan-and-Solve | Reflection catches drift; the plan keeps coherence |

## Combining patterns

Patterns compose. Common combinations:

- **ReAct + Self-Refine:** gather evidence with tools, then refine the answer.
- **Plan-and-Solve + ReAct:** plan the approach, then execute steps with tool
  access.
- **Reflexion + any pattern:** add reflection memory to improve retries.
- **Least-to-Most + Tool-Augmented:** decompose, then use tools for each
  subproblem.

## FAFO mapping

| Pattern | Current chain support | How to apply |
|---|---|---|
| Direct prompting (baseline) | Single-prompt chains in `tenants/<id>/prompts/variants/` | Default starting point for all tenants. |
| Plan-and-Solve | Multi-step chains with planner + executor modules | Structure prompt modules as plan → execute → verify steps. |
| Self-Refine | Multi-step chains with draft + critique + refine modules | Add critique and refinement steps to existing chains. |
| ReAct | Multi-step chains with tool integration | Requires a tool-calling chain module; add a reasoning + tool loop. |
| Reflexion | Not directly supported | Needs memory that persists across eval cases, or retry logic within a chain. Flag for future infra work. |
| Tree of Thoughts | Not directly supported | Needs branching or sampling within a chain step. Flag for future infra work. |

When a failure mode suggests a pattern change (see the
[selection guide](#pattern-selection-guide)), the optimization agent implements
it directly if the tenant playbook allows structural changes. Otherwise it flags
the change in the "Recommendations" section of its report.

## Source links

Pattern papers are linked in each entry above. Background papers:

- Chain-of-thought: https://arxiv.org/abs/2201.11903
- Self-consistency: https://arxiv.org/abs/2203.11171

Retrieval date for this source set: March 6, 2026.
