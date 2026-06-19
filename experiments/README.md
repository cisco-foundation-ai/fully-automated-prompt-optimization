<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Reference experiment results

Reference results for the proposed method **FAPO** and the baseline **GEPA**,
showing what a complete optimization run produces and how its outputs are
organized on disk.

Both methods were run on the same matrix:

- **6 benchmarks** — `aime2025`, `hotpotqa`, `hover`, `ifbench`, `livebench_math`, `papillon`
- **3 task models** — `gpt-4.1-mini`, `gpt-5.4-mini`, `gemma-3-12b-it`
- **3 trials** — `trial-1`, `trial-2`, `trial-3`

giving **54 result cells per method** (6 × 3 × 3).

These cells hold the curated optimization artifacts — prompts, configs, scores,
optimized programs, and logs. The raw per-case model outputs are not included;
[`samples/`](samples/) carries one representative output file per method to show
that format.

## Directory layout

A single scaffold, `<method>/<benchmark>/<model>/trial-N/`, holds both methods
side by side. Inside each cell, each method keeps its own file layout (FAPO and
GEPA emit different artifacts).

```
experiments/
├── README.md
│
├── fapo/
│   └── <benchmark>/<model>/trial-N/                    ← FAPO cell:
│       ├── run-metadata.json       ← provenance: model, trial, created_at
│       ├── configs/*.json          ← eval / optimization configs for this cell
│       ├── prompts/                ← evolved prompt variants (variant-*.md)
│       │   ├── modules/<module>/   ←   multi-module chains: hotpotqa, hover, ifbench, papillon
│       │   └── variants/           ←   single-module (CoT) chains: aime2025, livebench_math
│       ├── evals/<run-name>/       ← one dir per evaluation run:
│       │   ├── summary.md          ←   scores, step timings, failure attribution
│       │   ├── progress.json       ←   avg_composite_score + score breakdown + case counts
│       │   └── run_config.json     ←   what was evaluated
│       └── optimize-loop/
│           └── progress.log[.<ts>] ← optimization-loop status (rounds, budget)
│
├── gepa/
│   └── <benchmark>/<model>/trial-N/                    ← GEPA cell:
│       ├── config.json             ← optimizer config (retains original "seed": 0|1|2)
│       ├── run_status.json         ← status + duration_s + final score
│       ├── timing.json             ← epochs, iterations, metric calls
│       ├── token_stats.json        ← task-LM and reflector-LM tokens + cost
│       ├── evaluation_results/
│       │   ├── results.json        ← final test score + optimizer cost/tokens
│       │   └── optimized_program_state.json  ← optimized DSPy program (instructions); API keys redacted
│       └── prog_candidates/<i>/
│           └── metadata.json       ← per-iteration candidate stamp (dspy/python versions)
│
└── samples/                        ← one raw-output exemplar per method (see samples/README.md)
    ├── README.md
    ├── fapo/…chain-best-test.results.sample.jsonl
    └── gepa/…test.sample.jsonl
```

Concrete cell examples: `experiments/fapo/hotpotqa/gpt-4.1-mini/trial-1/` and
`experiments/gepa/hotpotqa/gpt-4.1-mini/trial-1/`.

## Naming

The two methods used different naming conventions upstream; directory names are
normalized to a single canonical vocabulary across all three dimensions. The
original names are preserved inside each cell's own files (e.g. GEPA's
`config.json` keeps `model_name` and `seed`).

**Benchmarks** (canonical = lowercase snake, matching the repo's tenant ids):

| Canonical | FAPO native | GEPA native |
|-----------|-------------|-------------|
| `aime2025` | `aime2025` | `AIMEBench` |
| `hotpotqa` | `hotpotqa` | `HotpotQABench` |
| `hover` | `hover` | `hoverBench` |
| `ifbench` | `ifbench` | `IFBench` |
| `livebench_math` | `livebench_math` | `LiveBenchMathBench` |
| `papillon` | `papillon` | `Papillon` |

**Models** (canonical = the dotted API model string):

| Canonical | FAPO native | GEPA native | GEPA `task_model` |
|-----------|-------------|-------------|-------------------|
| `gpt-4.1-mini` | `gpt41mini` | `gpt-41-mini` | `openai/gpt-4.1-mini-2025-04-14` |
| `gpt-5.4-mini` | `gpt54mini` | `gpt-54-mini` | `openai/gpt-5.4-mini` |
| `gemma-3-12b-it` | `gemma12b` | `gemma3-12b-it` | (AWS Bedrock) |

**Trials** are 1-indexed; GEPA's upstream seeds are 0-indexed:

| Canonical | FAPO native | GEPA native | GEPA `config.json` `seed` |
|-----------|-------------|-------------|---------------------------|
| `trial-1` | `-t1` | `seed_0` | `0` |
| `trial-2` | `-t2` | `seed_1` | `1` |
| `trial-3` | `-t3` | `seed_2` | `2` |

**Reflector model.** Every GEPA `config.json` records
`reflector_model: bedrock/us.anthropic.claude-opus-4-6-v1` (Claude Opus 4.6) —
the model GEPA uses to propose new instructions during optimization, distinct
from the task model being evaluated.

## Reading the results

- **GEPA** — per cell, the final score is in `run_status.json` and
  `evaluation_results/results.json`; the optimized prompt text is in
  `evaluation_results/optimized_program_state.json` under each module's
  `…predict.signature.instructions`. Per-cell cost and token usage are in
  `token_stats.json`, and timing/budget in `timing.json`.
- **FAPO** — per run, the headline score is `progress.json` →
  `avg_composite_score` (with `summary.md` for a readable view, and
  `run_config.json` for what was evaluated); the optimized prompts are the
  highest-numbered `prompts/.../variant-*.md`. Within `evals/`, the
  `baseline-variant001-*` run is the un-optimized baseline and `chain-best-test`
  / `fapo-final-test*` are the selected optimized program (other run dirs are
  intermediate trajectory steps); the trailing token of a run name is its split
  (`train` / `val` / `test`). The number of eval runs per cell varies with how
  much each cell was iterated.
