<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Change Log

## 2026-06-11
- Summary: Replaced the heuristic `TaskScorer` with a LangSmith-style scoring stack — a deterministic `TrajectoryScorer`, an LLM-as-judge `LLMJudgeScorer`, and a `CompositeScorer` that blends them (`answer_correct` 60% from the judge, `trajectory` 40%). Enriched the agentic tool-call trace and upgraded the dataset to drive trajectory scoring.
- Why: Substring-based answer matching was brittle for free-form answers, and tool-name set comparison ignored call ordering and argument correctness — both weak signals for agentic/MCP workflows.
- What changed: (a) Added `code/scorers/trajectory_scorer.py` (order/argument-aware: tool selection, call ordering, argument correctness, non-redundancy), `code/scorers/llm_judge_scorer.py` (rubric-graded answer correctness via `scoring_profile.judge`, degrades to `fallback_score` on judge failure), and `code/scorers/composite_scorer.py` (configurable `composite_weights`). (b) Removed `code/scorers/task_scorer.py`; repointed `configs/eval.json` and `configs/config-variant-002.json` to `CompositeScorer`. (c) Enriched `tool_call_history` in `src/hephaestus/chains/agentic_nodes.py` with `result`, `latency_ms`, `call_index`, and `llm_thought` (additive; legacy scorers unaffected). (d) Added `expected_trajectory` (ordered, argument-aware) to all 30 dataset cases and documented the schema in `docs/data-contract.md`.
- Eval impact: Scoring mechanism changed — prior composite scores are not comparable. `score_breakdown` keys are now `answer_correct`, `trajectory`, and flattened `traj_*`/`judge_*` sub-metrics. `eval.json` now invokes a live LLM judge (gpt-4o-mini) at eval time and requires `OPENAI_API_KEY`. No fresh eval run recorded yet.
- Optimization level: scoring/evaluation harness only (prompt, parameter, and structural levels untouched).
- Rollback notes: The scorers are additive new files; reverting the `scoring_profile` blocks in `configs/eval.json` and `configs/config-variant-002.json` (and restoring `task_scorer.py`) returns to the prior heuristic scoring. The `expected_trajectory` dataset fields are ignored by scorers that don't read them.

## 2026-06-10
- Summary: Added the full required tenant doc set (tenant-profile, data-contract, prompt-contract, eval-operations, change-log, docs-index) and restructured the iteration playbook to satisfy tenant-docs-contract checks.
- Why: mcp_example previously only had an iteration playbook; CI validates tenant doc alignment.
- Files/configs: docs/tenant-profile.md, docs/data-contract.md, docs/prompt-contract.md, docs/eval-operations.md, docs/change-log.md, docs/docs-index.yaml, docs/iteration-playbook.md.
- Eval impact: None — documentation only.
- Rollback notes: N/A.

## 2026-06-10
- Summary: Established mcp_example as the reference tenant for MCP/agentic evaluation — ReAct agent chain, 30-case tool/reasoning dataset, tool-aware scorer, and eval config wired to the bundled mock MCP server.
- Why: Provide a runnable, credential-free demonstration and template for MCP-backed tenants.
- Files/configs: chains/react_agent.py, prompts/modules/agent/variant-001.md, datasets/tool_tasks.jsonl, code/scorers/task_scorer.py, configs/eval.json.
- Eval impact: Baseline established with variant-001 on gpt-4o-mini.
- Rollback notes: N/A — initial tenant setup.
