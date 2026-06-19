<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Format exemplars

One raw per-case output file per method, included to show the on-disk format of
the full per-case outputs (which are otherwise not part of this tree). Each file
is a single representative cell — it illustrates the format and is not
score-representative; read aggregate results from the per-cell artifacts under
`fapo/` and `gepa/` instead.

| File | Source cell | Format |
|------|-------------|--------|
| `fapo/hotpotqa-gpt-4.1-mini-trial-1.chain-best-test.results.sample.jsonl` | FAPO `hotpotqa / gpt-4.1-mini / trial-1`, run `chain-best-test` | one JSON object per line (300 lines); keys: `case_id`, `task_type`, `diagnostics`, `score_breakdown`, `composite_score`, `output_text`, `step_outputs`, `step_timings`. This is the per-case detail behind a FAPO `evals/<run>/summary.md`. |
| `gepa/aime2025-gpt-4.1-mini-trial-1.test.sample.jsonl` | GEPA `aime2025 / gpt-4.1-mini / trial-1`, `metric_logs/test.jsonl` | one JSON object per line; keys: `prediction`, `metric_output`, `metric_call_count`, `step_counter`, split counters, `idx_in_split`. This is GEPA's per-case scored-prediction log — its analog of the FAPO `results.jsonl`. |
