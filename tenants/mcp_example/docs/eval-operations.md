<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Eval Operations

## Config Matrix
| Config | Prompt Variant | Dataset | Model | MCP Server | Scorer |
|--------|---------------|---------|-------|------------|--------|
| `configs/eval.json` | `variant-001.md` | `tool_tasks.jsonl` | gpt-4o | mock (`tests/fixtures/mock_mcp_server.py`) | `CompositeScorer` |

## Scorers
- `code/scorers/trajectory_scorer.py` (`TrajectoryScorer`) — deterministic, order- and argument-aware. Reads an optional ordered `expected_trajectory` (`[{"tool", "arguments"}]`) from `case.expected`, falling back to `tools_used` when absent. Scores tool selection, call ordering, argument correctness, and non-redundancy.
- `code/scorers/llm_judge_scorer.py` (`LLMJudgeScorer`) — LangSmith-style LLM-as-judge for answer correctness. Configured via `scoring_profile.judge` (`provider`, `provider_settings`, `rubric`, `fallback_score`). A failed/unparseable judge call degrades to `fallback_score` with a diagnostic — it never crashes the run.
- `code/scorers/composite_scorer.py` (`CompositeScorer`) — **the default scorer**. Weighted aggregate of judge (`answer_correct`, 60%) + `trajectory` (40%). Weights configurable via `scoring_profile.composite_weights` (normalized; need not sum to 1.0). Child sub-metrics are flattened into `score_breakdown` with `traj_`/`judge_` prefixes.

### Enriched tool-call trace
Each `tool_call_history` entry now also carries `result` (full tool output), `latency_ms`, `call_index` (per-case monotonic order), and `llm_thought` (the assistant reasoning that produced the call). Existing fields (`tool`, `arguments`, `result_length`, `error`, `iteration`, `node`) are unchanged, so legacy scorers keep working.

## Standard Eval Commands
- Preferred: `/project:eval-runner` with `tenants/mcp_example/configs/eval.json`.
- Direct: `python -m hephaestus.cli eval --config tenants/mcp_example/configs/eval.json`
- Requires `OPENAI_API_KEY` in the environment. No other credentials are needed — the mock MCP server is launched locally as a subprocess.
- Integration tests for the MCP layer: `pytest -m integration tests/integration/test_mcp_integration.py -v`

## Success Criteria
- Composite score >= 80% across all 30 cases.
- Tool-use cases call the expected tools (visible in `tool_call_history`); reasoning cases call no tools.
- No "Exceeded max_tool_calls limit" errors during a normal run (limit is per-case = `max_iterations * max_tool_calls_per_iteration`).
- MCP server starts, discovers 3 tools (`echo`, `add`, `fail`), and shuts down cleanly.

## Failure Triage
- **All cases after ~N fail with tool-limit errors**: ensure a fresh executor is created per case (per-case limit, not cumulative). See `chains/agentic_nodes.py`.
- **"Tool execution timed out"**: raise `mcp.tool_execution.timeout_seconds` in the config, or confirm the mock server is responding.
- **"Failed to discover tools"**: confirm the mock server runs under the configured interpreter and speaks MCP (it is SDK-based).
- **Cancel-scope / asyncio errors on shutdown**: all MCP calls must route through the manager's lifecycle task (`MCPToolExecutor` → `manager.run_coro`); never call `session.call_tool` directly.
- **Low `traj_tool_selection` score**: the agent is computing mentally instead of calling `add`, or using tools on reasoning cases — adjust the prompt variant.
- **Low `judge_answer_correct` / `answer_correct` score**: the final answer is wrong or omits the expected value. Check the judge's rationale; if the judge itself is failing, look for `judge_unavailable` in diagnostics (degrades to `fallback_score`).

## Output Management
- Eval outputs are written to `evals/<run_id>/` and are local-only (gitignored via `tenants/*/evals/`).
- Each run produces `summary.md`, `results.jsonl` (with `tool_call_history`), `run_config.json`, and `progress.json`.
- Material findings are summarized in `docs/change-log.md`.
