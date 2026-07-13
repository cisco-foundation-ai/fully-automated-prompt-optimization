<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Eval Operations

## Config Matrix

| Config | Dataset | Purpose |
|---|---|---|
| `configs/train.json` | `datasets/datasets/train.jsonl` | Prompt iteration and error attribution |
| `configs/eval.json` | `datasets/datasets/eval.jsonl` | Variant evaluation |
| `configs/test.json` | `datasets/datasets/test.jsonl` | Variant evaluation and leaderboard reporting |

All configs use `gpt-4o-mini` with the same chain, scorer, and starter prompt.

## Standard Eval Commands

```bash
python -m hephaestus.cli eval --config tenants/software_name_categorization/configs/train.json
python -m hephaestus.cli eval --config tenants/software_name_categorization/configs/eval.json
python -m hephaestus.cli eval --config tenants/software_name_categorization/configs/test.json
```

## Success Criteria

- Challenge target: F1 > 95 on eval and test.
- `composite_score` is equivalent to per-case exact match.
- For this single-label task, micro-F1 is equivalent to accuracy.
- Final answers should also maintain high `valid_label` and `strict_format`
  scores.

## Failure Triage

- Attribute failures only on the training split.
- Do not inspect eval or test misses to tune label-specific prompt rules.
- Use eval and test only for aggregate variant comparison.
- Watch for confusion between remote access, data transfer, runtime services,
  sensitive material, and security posture tooling.

## Output Management

- Train outputs are written under `evals/train`.
- Eval outputs are written under `evals/eval`.
- Test outputs are written under `evals/test`.
- Treat output directories as local run artifacts.

