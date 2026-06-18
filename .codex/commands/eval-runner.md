<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Eval Runner for Codex

Use this when the user wants to run an eval, test a prompt variant, check scores, execute an eval config, compare variants, or see evaluation results.

## Workflow

1. Confirm the eval config path.
2. Ensure provider credentials are present for the configured provider.
3. Run:

```bash
python scripts/eval/run_eval_and_summarize.py --config tenants/<tenant_id>/configs/<run-name>.json
```

4. Report the output directory, run ID when present, composite score, key breakdowns, and any obvious failures.

## Variations

Override output directory without editing the config:

```bash
python scripts/eval/run_eval_and_summarize.py \
  --config tenants/<tenant_id>/configs/<run-name>.json \
  --output-dir tenants/<tenant_id>/evals/tmp/<run-name>
```

Direct fallback:

```bash
python -m hephaestus.cli eval --config tenants/<tenant_id>/configs/<run-name>.json
```

Eval configs should remain local-only under `tenants/<tenant_id>/configs/` unless a tracked fixture is intentional.
