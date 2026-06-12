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
    "answer_contains": "<substring used as the LLM judge's reference answer>",
    "tools_used": ["echo" | "add", "..."],
    "expected_trajectory": [
      {"tool": "add", "arguments": {"a": 100, "b": 234}},
      {"tool": "echo"}
    ]
  },
  "metadata": {"difficulty": "easy | medium | hard", "note": "<optional>"}
}
```

## Label Taxonomy
- `task_type`:
  - `tool_use` — the agent is expected to call one or more tools (`tools_used` non-empty).
  - `reasoning` — the agent should answer directly (`tools_used` is `[]`, `expected_trajectory` is `[]`).
- `expected.answer_contains` — the reference answer handed to the LLM judge. The judge grades whether the agent's final answer is correct relative to this reference (it is no longer a literal substring check).
- `expected.tools_used` — the set of tool names that should fire (order not enforced). Used as the fallback when `expected_trajectory` is absent.
- `expected.expected_trajectory` — **the preferred, ordered specification** of tool calls. A list of `{"tool", "arguments"}` steps in the order they should occur. Drives ordering and argument scoring:
  - `tool` (required) — the tool name for this step.
  - `arguments` (optional) — expected arguments. Matching is **subset-based and type-tolerant**: every listed key must be present with an equal value (compared as strings, so `59` matches `"59"`); extra actual arguments are ignored. **Omit `arguments`** when the value is genuinely non-deterministic — e.g. echoing a previously computed result, or a chained `add` whose operands depend on a prior step's output. Such a step still counts toward tool-selection and ordering, but is skipped for argument scoring.
  - Reasoning cases set `expected_trajectory` to `[]` (no tools should fire).
- `metadata.difficulty` — `easy` (single tool call), `medium` (two-tool combo / larger numbers), `hard` (multi-step chained calls).

## Check Expectations
- Scorer: `code/scorers/composite_scorer.py::CompositeScorer`
- `composite_score`: weighted, normalized blend (0–100), default weights configurable via `scoring_profile.composite_weights`:
  - `answer_correct` (60%) — LLM-as-judge grade of the final answer vs. `expected.answer_contains` (`code/scorers/llm_judge_scorer.py`).
  - `trajectory` (40%) — deterministic tool-trajectory score (`code/scorers/trajectory_scorer.py`).
- The trajectory sub-score is itself a blend of `tool_selection` (35%), `call_ordering` (20%), `argument_correctness` (30%), and `non_redundancy` (15%).
- `score_breakdown` keys: `answer_correct`, `trajectory`, plus flattened child metrics prefixed `traj_*` (e.g. `traj_tool_selection`) and `judge_*`.

## Dataset Update Procedure
- The dataset is static and committed locally (no GCS backing for this demo tenant).
- To add cases, append JSONL lines to `datasets/tool_tasks.jsonl` following the case schema above. Keep `case_id` unique and ensure the file has no trailing blank line.
- When adding tool-use cases, only reference tools the mock server provides (`echo`, `add`); the `fail` tool is reserved for error-handling tests and should not appear in `expected.tools_used` or `expected_trajectory`.
- Prefer specifying `expected_trajectory` for new tool-use cases. Only specify `arguments` for steps whose inputs are deterministic from the task text (e.g. the first `add` of literal numbers, or an `echo` of a literal string).
