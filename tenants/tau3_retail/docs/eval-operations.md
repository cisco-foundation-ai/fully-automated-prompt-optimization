<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Evaluation Operations

## Config Matrix

| Config | Role |
|---|---|
| `configs/train.json` | Conventional full mixed training entry point |
| `configs/eval.json` | Mixed validation with recorded M004 prompt |
| `configs/test.json` | Mixed test with recorded M004 prompt |
| `recipe/configs/trusted-train.json` | Trusted-only training |
| `recipe/configs/inferred-train.json` | Staged inferred phase |
| `recipe/configs/mixed-train.json` | Full mixed training |
| `recipe/configs/regression.json` | Trusted regression gate |

All configs assume a sibling Tau checkout at `../tau2-bench` and a local FAFO
asset named `fafo-v3-luna-v1`.

## Standard Eval Commands

Validate the external runtime:

```bash
python tenants/tau3_retail/scripts/setup_tau_runtime.py --dry-run
../tau2-bench/.venv/bin/tau2 check-data
```

Run a FAFO-guided evaluation:

```bash
.venv/bin/python scripts/eval/run_eval_and_summarize.py \
  --config tenants/tau3_retail/configs/train.json
```

Run the native final holdout only after prompt selection:

```bash
python tenants/tau3_retail/scripts/run_tau.py \
  --partition final_holdout \
  --prompt tenants/tau3_retail/prompts/v3/mixed/m004.txt \
  --save-to fafo_v3_mixed_m004_final_holdout
```

## Success Criteria

- Primary external outcome: native Tau pass count and `pass^1` on the fixed
  22-task × 4-trial holdout matrix.
- Reliability outcomes: `pass^2`, `pass^3`, and `pass^4`.
- Diagnostics: database match, read/write action match, and natural-language
  assertion completion.
- Internal variant ranking: more guideline passes, then fewer critical
  violations, then higher mean guideline score.
- A FAFO-judge gain alone is not sufficient; the selected prompt must be
  evaluated natively against the unchanged baseline.

## Failure Triage

- Treat Tau process failures, timeouts, missing outputs, malformed judge JSON,
  and provider errors as infrastructure failures, not behavioral failures.
- Retry a failed judge against the preserved episode without rerunning the
  agent; count an agent inference only when Tau runs a fresh episode.
- Use only training-case traces and rubric verdicts to design prompts.
- Inspect tool-result evidence before accepting a judge claim about action
  success.
- Keep validation/test/regression and native holdout case contents sealed; use
  only their allowed aggregate metrics.

## Output Management

- Tau outputs remain under the sibling checkout's `data/simulations/`.
- FAFO outputs remain under `tenants/tau3_retail/evals/`.
- FAFO workspaces remain under `tenants/tau3_retail/evaluation_assets/`.
- All are ignored and must not be committed.
- Commit only aggregate reports, prompt text, configs, code, iteration memory,
  changelog, and public split metadata.
