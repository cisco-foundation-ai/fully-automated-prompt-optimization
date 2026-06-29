<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Iteration Playbook: Skill Example

## Purpose
Optimize a ReAct agent that performs Splunk operations through the Splunk MCP
Server, where the reusable procedural knowledge lives in **skill files**. The
agent must pick the right tools, sequence them sensibly, pass well-formed
arguments, and ground its answers in tool results — with that know-how supplied
by the injected skills rather than baked into the base prompt.

## Prerequisites
- Global reference: `docs/processes/prompt-iteration-loop.md`.
- `OPENAI_API_KEY`, `SPLUNK_MCP_URL`, and `SPLUNK_MCP_TOKEN` exported.
- `npx` (Node.js) on PATH for the `mcp-remote` bridge.
- Baseline eval completed with `variant-001` prompt + `variant-001` skills
  (`configs/eval.json`).

## Iteration Loop
1. Follow the global iteration loop from `docs/processes/prompt-iteration-loop.md`.
2. Optimize the `agent` prompt module **and/or** the skill files over
   `splunk_ops_tasks.jsonl`. All cases are training data — no split.
3. After each change, re-run the full eval and compare composite score and
   `score_breakdown` (especially `trajectory`, its sub-metrics, and
   `answer_correct`) against the previous best.
4. Iterate until success criteria are met.

## Optimization Scope

### Chain-Level Optimization Scope
- **Prompt changes**: IN-SCOPE — refine the base scaffold (ReAct framing, tool
  catalog presentation, core grounding, where/how skills are introduced).
- **Skill changes**: IN-SCOPE — refine the reusable procedures
  (`skills/<name>/variant-NNN.md`): tool selection/sequencing, the
  superlative-index drill-in, SPL search guidance, answer formatting. This is the
  primary lever for this tenant.
- **Parameter changes**: IN-SCOPE — tune `max_iterations` /
  `max_tool_calls_per_iteration` / `timeout_seconds` in `configs/eval.json` if the
  agent loops or truncates.
- **Structural changes**: NOT IN-SCOPE — the chain is a fixed single ReAct node,
  and the Splunk MCP server set / transport is fixed.

### Scope Constraint
**Allowed**: prompt-text edits under `prompts/modules/*/variant-*.md`, skill-text
edits under `skills/*/variant-*.md`, **and** parameter edits in `configs/eval.json`
(tool-execution limits / chain config). The optimization agent must not change
chain structure, swap the MCP server, change the model or judge without approval,
or modify scorer logic.

> Prompt and skill are co-equal textual levels here (`optimization_target: both`).
> Route each textual-failure cluster to whichever artifact owns the concern: broad
> scaffold/format → base prompt; a reusable task-specific procedure → the matching
> skill. Narrow to a single artifact only if a task explicitly says so.

## Tool Usage Patterns

### Expected Behaviors
1. **Index inventory** → `splunk_get_indexes` → `splunk_get_index_info`.
2. **User lookup** → `splunk_get_user_list` (current account → `splunk_get_user_info`).
3. **Search / event data** → `splunk_run_query` (agent writes SPL directly).
4. **Metadata / knowledge objects** → `splunk_get_metadata` / `splunk_get_knowledge_objects`.
5. **Instance health** → `splunk_get_info`.

### Common Failure Patterns (and the owning skill)
1. **Skipped drill-in** on superlative index questions → `superlative-index-questions`.
2. **Wrong tool / bad sequencing** → `tool-selection`.
3. **Invalid SPL or ignored time range** → `spl-search`.
4. **Punting, non-exhaustive lists, hedged yes/no, wrong structure** → `answer-formatting`.
5. **Hallucinated data** → base prompt's core grounding rule (and the relevant skill).
6. **Loop/truncation** on multi-step cases → tune parameters.

## Stop Criteria
- Composite score >= 80% sustained across the full case set, OR
- Three consecutive variants show no improvement (plateau) after exhausting
  skill-text, prompt-text, and parameter techniques.

## Regression Prevention
- Run the full eval after every change — never accept a variant on a
  partial run.
- Watch trajectory sub-metrics: a higher composite that comes with degraded
  `traj_tool_selection`, `traj_call_ordering`, or `traj_argument_correctness` is a
  regression, not a win — especially given trajectory's 0.6 weight.

## Lessons Logging
Record optimization outcomes in `docs/change-log.md`:
- Which skill or prompt changes improved tool selection / sequencing / formatting.
- Parameter changes and their effect on multi-step cases.
- Any cases where agent behavior was unexpected.
