<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Synthetic Pruner for Codex

Use this when the user wants to clean synthetic examples, remove bad samples, normalize placeholder hashes, validate synthetic data quality, or align review CSVs.

## Workflow

1. Read tenant requirements and `docs/references/synthetic-requirements.md`.
2. Identify severe violations, such as too-short email bodies without intentional missing-body rationale.
3. Prefer deterministic cleanup with:

```bash
python scripts/synthetic/prune_synthetics.py \
  --examples-dir tenants/<tenant_id>/datasets/synthetic_artifacts \
  --max-words 10
```

4. Use `--apply` only after inspecting the dry-run output.
5. Update review CSVs so they reference only existing examples.
6. Replace placeholder hashes with realistic 64-hex synthetic values when examples are otherwise valid.

## Guardrails

- Do not modify `tenants/*/source_artifacts/`.
- Keep changes scoped to synthetic example folders and their review CSVs.
- Do not delete examples merely because they are hard; delete only requirement violations.
