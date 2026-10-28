<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Model

A tenant is one optimization project. Each tenant lives in `tenants/<tenant_id>/`
with this layout:

| Path | Contents |
|---|---|
| `README.md` | Tenant landing page and quick links |
| `docs/` | Tenant-specific operating docs; checked in. See the [tenant docs contract](tenant-docs-contract.md). |
| `chains/` | Tenant chains; structural variants go in `chains/variants/` (see [chain variant conventions](processes/chain-variant-conventions.md)) |
| `prompts/` | Tenant prompt variants, in `prompts/variants/` or per module in `prompts/modules/<module>/` |
| `skills/<skill-name>/` | Agent skill files for agentic tenants. Optional; optimized as a textual level co-equal with prompts. |
| `code/` | Tenant-specific conversion logic that produces unified JSONL datasets |
| `tests/` | Tenant-specific tests that validate conversion and data assumptions |
| `examples/` | Tenant-scoped helper scripts and one-off runnable examples |
| `storage/config.json` | Tracked storage config for `customer-data` operations |
| `source_artifacts/` | Local cache of raw customer artifacts, hydrated from GCS |
| `datasets/` | Local cache of derived artifacts, hydrated from GCS, including synthetic example payloads and generated synthetic JSONL datasets. Not checked in. |
| `configs/` | Local, ephemeral eval configs. Git-ignored except a few tracked files, such as `eval.json`, `train.json`, and `test.json`. |
| `evals/tmp`, `evals/archive` | Local eval outputs; not committed |
| `reports/` | Local-only, point-in-time analysis notes. Git-ignored and non-authoritative; drift is allowed, and they must not be treated as a source of truth. |

Core eval accepts unified JSONL only. Implement tenant-specific adapters as
offline conversion scripts under `code/`, not as runtime eval plugins.
