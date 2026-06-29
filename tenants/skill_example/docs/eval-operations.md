<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Eval Operations

## Config Matrix
| Config | Prompt Variant | Skills | Dataset | Model | Judge | MCP Server | Scorer |
|--------|---------------|--------|---------|-------|-------|------------|--------|
| `configs/eval.json` | `variant-001.md` | `tool-selection`, `superlative-index-questions`, `spl-search`, `answer-formatting` (each `variant-001`) | `splunk_ops_tasks.jsonl` | gpt-4o | gpt-5.5 | Splunk MCP (via `npx mcp-remote`) | `CompositeScorer` (trajectory 0.6 / answer 0.4) |

`chain.config` declares `skill_paths` (the injected skill files) and
`optimization_target: "both"` (prompt + skill are co-equal textual levels).

## Environment
The eval connects to the **real** Splunk MCP Server. Set before running:
- `OPENAI_API_KEY` — agent (`gpt-4o`) and judge (`gpt-5.5`).
- `SPLUNK_MCP_URL` — Splunk MCP Server endpoint URL.
- `SPLUNK_MCP_TOKEN` — Splunk auth token, sent as `Authorization: Bearer ...`.
- `npx` (Node.js) must be on PATH — the config launches `npx -y mcp-remote` as a
  stdio↔HTTP bridge to the Splunk MCP Server.

The config invokes the bridge via
`sh -c "exec npx -y mcp-remote \"$SPLUNK_MCP_URL\" --header \"Authorization: Bearer $SPLUNK_MCP_TOKEN\""`
so the shell expands the credential env vars (the manager does not expand `${VAR}`
inside `args`).

## Skills Loading (agentic layer)
- The chain (`chains/react_agent.py`) reads `chain.config.skill_paths` and renders
  them with `render_skills_block`. The agentic node then injects the result into
  the conversation as a distinct `<available_skills>` system context message
  (`build_skills_message` / `inject_skills_message`), placed right after the
  authored system prompt. This is static for the run — the skills do not
  re-render per case — and stays fully in context for every model call.
- The skills are **not** inlined into the authored prompt template, mimicking an
  agent that loaded skills into its environment at session start.
- A config with no `skill_paths` is a no-op — the agent behaves like a plain
  ReAct agent driven by the base prompt alone.
- `optimization_target` including `skill` or `both` requires an `mcp` section;
  the eval runner validates this at config load.

## Scorers
- `code/scorers/trajectory_scorer.py` (`TrajectoryScorer`) — deterministic, order-
  and argument-aware. Scores tool selection, call ordering, argument correctness,
  and non-redundancy.
- `code/scorers/llm_judge_scorer.py` (`LLMJudgeScorer`) — LLM-as-judge for answer
  correctness, configured via `scoring_profile.judge`. A failed/unparseable judge
  call degrades to `fallback_score` with a diagnostic — it never crashes the run.
- `code/scorers/composite_scorer.py` (`CompositeScorer`) — **the default scorer**.
  Weighted aggregate of `trajectory` (0.60) + judge `answer_correct` (0.40).

### Enriched tool-call trace
Each `tool_call_history` entry carries `result` (full tool output), `latency_ms`,
`call_index` (per-case monotonic order), and `llm_thought`, in addition to `tool`,
`arguments`, `result_length`, `error`, `iteration`, and `node`.

## Standard Eval Commands
- Preferred: `/project:eval-runner` with `tenants/skill_example/configs/eval.json`.
- Direct: `python -m hephaestus.cli eval --config tenants/skill_example/configs/eval.json`

## Success Criteria
- Composite score >= 80% across all cases.
- Tool-use cases call the expected Splunk tools in a sensible order (visible in
  `tool_call_history`).
- No "Exceeded max_tool_calls limit" errors during a normal run.
- Splunk MCP bridge connects, discovers the Splunk tools, and shuts down cleanly.

## Failure Triage
- **"Failed to discover tools" / connection refused**: confirm `SPLUNK_MCP_URL` and
  `SPLUNK_MCP_TOKEN` are exported and valid, and that `npx`/Node is installed.
- **401/403 from Splunk**: the token lacks RBAC permission for the requested tool.
- **"Tool execution timed out"**: raise `mcp.tool_execution.timeout_seconds`.
- **Skill not taking effect**: confirm the config's `skill_paths` point at existing
  files (the eval runner errors on a missing skill file). The skills are loaded by
  the node, so no `${skills}` placeholder is needed in the prompt — inspect a
  result's messages for the `<available_skills>` context block to confirm injection.
- **Low `traj_tool_selection` / `traj_call_ordering`**: the agent is skipping the
  list→drill-in step or answering without SPL — adjust the relevant skill
  (`tool-selection` / `superlative-index-questions` / `spl-search`).
- **Low `judge_answer_correct`**: the final answer omits or misstates the findings —
  adjust the `answer-formatting` skill.

## Output Management
- Eval outputs are written to `evals/<run_id>/` and are local-only (gitignored via
  `tenants/*/evals/`).
- Each run produces `summary.md`, `results.jsonl`, `run_config.json`, and
  `progress.json`. Material findings are summarized in `docs/change-log.md`.
