<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Format exemplars

One raw per-case output file per method, showing the on-disk format of the full
per-case outputs, which are otherwise not part of this tree. Each file comes
from a single representative cell: it illustrates the format and is not
score-representative. Read aggregate results from the per-cell artifacts under
`experiments/fafo/` and `experiments/gepa/` instead.

| File | Source cell | What it is |
|------|-------------|------------|
| `fafo/hotpotqa-gpt-4.1-mini-trial-1.chain-best-test.results.sample.jsonl` | FAFO `hotpotqa / gpt-4.1-mini / trial-1`, run `chain-best-test` | The per-case detail behind a FAFO `evals/<run>/summary.md` |
| `gepa/aime2025-gpt-4.1-mini-trial-1.test.sample.jsonl` | GEPA `aime2025 / gpt-4.1-mini / trial-1`, `metric_logs/test.jsonl` | GEPA's per-case scored-prediction log, its analog of the FAFO `results.jsonl` |

Both files have one JSON object per line:

- **FAFO** (300 lines): `case_id`, `task_type`, `diagnostics`,
  `score_breakdown`, `composite_score`, `output_text`, `step_outputs`,
  `step_timings`.
- **GEPA**: `prediction`, `metric_output`, `metric_call_count`, `step_counter`,
  split counters, `idx_in_split`.
