<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Data Contract

## Dataset Inventory
- `datasets/tool_tasks.jsonl` — 30 cases mixing tool-use tasks (echo, add, multi-step) with reasoning tasks the agent should answer without tools.

## Case Schema
```json
{
  "case_id": "<string>",
  "task_type": "tool_use | reasoning",
  "context": {"task": "<natural-language instruction>"},
  "expected": {
    "answer_contains": "<substring the final answer must contain>",
    "tools_used": ["echo" | "add", "..."]
  },
  "metadata": {"difficulty": "easy | medium | hard", "note": "<optional>"}
}
```

## Label Taxonomy
- `task_type`:
  - `tool_use` — the agent is expected to call one or more tools (`tools_used` non-empty).
  - `reasoning` — the agent should answer directly (`tools_used` is `[]`).
- `expected.tools_used` — the set of tool names that should fire for a correct run (order not enforced).
- `expected.answer_contains` — case-insensitive substring the final answer must contain.
- `metadata.difficulty` — `easy` (single tool call), `medium` (two-tool combo / larger numbers), `hard` (multi-step chained calls).

## Check Expectations
- Scorer: `code/scorers/task_scorer.py::TaskScorer`
- `composite_score`: weighted blend (0–100) of:
  - `answer_present` (15%) — output contains an `Answer:` marker
  - `answer_correct` (50%) — output contains `expected.answer_contains`
  - `tool_usage` (25%) — tools actually called (from `tool_call_history`) match `expected.tools_used`
  - `tool_efficiency` (10%) — penalizes failed and excessive tool calls
- `score_breakdown` keys: `answer_present`, `answer_correct`, `tool_usage`, `tool_efficiency`.

## Dataset Update Procedure
- The dataset is static and committed locally (no GCS backing for this demo tenant).
- To add cases, append JSONL lines to `datasets/tool_tasks.jsonl` following the case schema above. Keep `case_id` unique and ensure the file has no trailing blank line.
- When adding tool-use cases, only reference tools the mock server provides (`echo`, `add`); the `fail` tool is reserved for error-handling tests and should not appear in `expected.tools_used`.
