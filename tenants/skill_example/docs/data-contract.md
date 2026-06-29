<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Data Contract

## Dataset Inventory
- `datasets/splunk_ops_tasks.jsonl` — Splunk-operations tasks across three
  patterns: index inventory, user lookup, and SPL search (NL→SPL→run), plus a
  couple of instance-info cases.
- The dataset is **not committed** (`tenants/*/datasets/*` is gitignored; only
  `datasets/.gitkeep` is tracked). Author it locally following the case schema
  and example below before running an eval.

## Case Schema
```json
{
  "case_id": "<string>",
  "task_type": "tool_use | reasoning",
  "context": {"task": "<natural-language Splunk question>"},
  "expected": {
    "answer_contains": "<reference answer used by the LLM judge>",
    "tools_used": ["splunk_get_indexes", "splunk_get_index_info"],
    "expected_trajectory": [
      {"tool": "splunk_get_indexes"},
      {"tool": "splunk_get_index_info", "arguments": {"index_name": "_internal"}}
    ]
  },
  "metadata": {"difficulty": "easy | medium | hard", "pattern": "<pattern>", "note": "<optional>"}
}
```

## Example Case
A single JSONL line (formatted here for readability — store it as one line). The
`index_name` argument is intentionally omitted because the agent must first
*discover* the largest index via `splunk_get_indexes` before drilling in:
```json
{
  "case_id": "splunk-001",
  "task_type": "tool_use",
  "context": {"task": "What is most of my data stored in Splunk?"},
  "expected": {
    "answer_contains": "The largest indexes by data volume, with the index holding roughly most of the data identified and what it contains.",
    "tools_used": ["splunk_get_indexes", "splunk_get_index_info"],
    "expected_trajectory": [
      {"tool": "splunk_get_indexes"},
      {"tool": "splunk_get_index_info"}
    ]
  },
  "metadata": {"difficulty": "medium", "pattern": "index_inventory", "note": "list indexes then drill into the largest"}
}
```

## Label Taxonomy
- `task_type`:
  - `tool_use` — the agent must call one or more Splunk MCP tools (`tools_used`
    non-empty). Every case in this dataset is `tool_use` — Splunk operations
    require live data.
  - `reasoning` — the agent should answer directly (`tools_used` is `[]`,
    `expected_trajectory` is `[]`). Reserved for future cases; none currently.
- `expected.answer_contains` — the reference answer handed to the LLM judge. The
  judge grades whether the agent's final answer is correct relative to this
  reference; it is **not** a literal substring check.
- `expected.tools_used` — the set of tool names that should fire (order not
  enforced). Used as the fallback when `expected_trajectory` is absent.
- `expected.expected_trajectory` — **the preferred, ordered specification** of
  tool calls. A list of `{"tool", "arguments"}` steps in the order they should
  occur. Drives ordering and argument scoring:
  - `tool` (required) — the tool name for this step.
  - `arguments` (optional) — expected arguments. Matching is **subset-based and
    type-tolerant**: every listed key must be present with an equal value
    (compared as strings, so `5` matches `"5"`); extra actual arguments are
    ignored. **Omit `arguments`** when the value is non-deterministic from the
    task text — e.g. an `index_name` the agent must first *discover* via
    `splunk_get_indexes`, or the SPL `query` the agent composes itself.
  - Specify `arguments` only when the value is literal in the task.
- `metadata.pattern` — `index_inventory`, `user_lookup`, `spl_search`, `metadata`,
  `knowledge_objects`, or `instance_info`.
- `metadata.difficulty` — `easy` (single tool call), `medium` (two-tool combo),
  `hard` (multi-step / chained search with a time range).

## Check Expectations
- Scorer: `code/scorers/composite_scorer.py::CompositeScorer`
- `composite_score`: weighted, normalized blend (0–100). Weights are set in
  `configs/eval.json` under `scoring_profile.composite_weights`:
  - `trajectory` (0.60) — deterministic tool-trajectory score
    (`code/scorers/trajectory_scorer.py`).
  - `answer_correct` (0.40) — LLM-as-judge grade of the final answer vs.
    `expected.answer_contains` (`code/scorers/llm_judge_scorer.py`).
- The trajectory sub-score is itself a blend of `tool_selection` (35%),
  `call_ordering` (20%), `argument_correctness` (30%), and `non_redundancy` (15%).
- `score_breakdown` keys: `answer_correct`, `trajectory`, `traj_tool_selection`,
  `traj_call_ordering`, `traj_argument_correctness`, `traj_non_redundancy`,
  `judge_answer_correct`, and `judge_judge_reason_chars`.
- `diagnostics` includes the agent node summary plus the LLM judge rationale as
  `judge[<score>]: <reason>`.

## Dataset Update Procedure
- The dataset is local-only and not committed (gitignored); author it under
  `datasets/splunk_ops_tasks.jsonl` following the case schema above.
- To add cases, append JSONL lines following the case schema above. Keep `case_id`
  unique and ensure the file has no trailing blank line.
- Only reference tools the Splunk MCP Server actually exposes (see
  `docs/tenant-profile.md` for the catalog). Prefer specifying `expected_trajectory`
  for new cases, and only set `arguments` for steps whose inputs are literal in the
  task text.
