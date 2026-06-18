<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Reset Tenant for Codex

Use this when the user explicitly wants to reset a tenant to baseline, clear optimization history, remove non-baseline variants, or start fresh.

## Required Input

- `tenant_id`

## Safety

This workflow is destructive. Inventory the planned changes and ask for explicit user confirmation before deleting or truncating anything.

Never touch:

- `variant-001.md`
- Baseline chain files directly under `chains/`
- `source_artifacts/`
- `code/`, `datasets/`, `tests/`, `examples/`, `storage/`, `docker/`, or `scripts/`
- `.gitkeep` files
- Files outside `tenants/<tenant_id>/`

## Procedure

1. Validate `tenants/<tenant_id>/` exists.
2. Inventory non-baseline prompt variants, chain variants, configs referencing variant-002+, `iteration-memory.jsonl`, changelog entries, and local eval/report outputs.
3. Ask for confirmation with the inventory.
4. Remove non-baseline prompt variants and chain variants.
5. Rewrite or remove configs that reference non-baseline variants.
6. Truncate `docs/iteration-memory.jsonl` if present.
7. Clean only optimization-related sections from `docs/change-log.md`.
8. Clean ignored local eval/report outputs for that tenant.
9. Report counts for every category changed.
