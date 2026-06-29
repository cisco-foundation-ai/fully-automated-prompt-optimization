<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Model

Each tenant lives in `tenants/<tenant_id>/`:
- `source_artifacts/` local raw customer artifact cache hydrated from GCS
- `datasets/` local derived artifact cache hydrated from GCS (including synthetic example payloads and generated synthetic JSONL datasets)
- `code/` tenant-specific conversion logic that produces unified JSONL datasets
- `tests/` tenant-specific tests that validate tenant conversion/data assumptions
- `prompts/variants/` tenant prompt variants
- `skills/<skill-name>/` agent skill files for agentic tenants (optional; optimized as a textual level co-equal with prompts)
- `evals/tmp` and `evals/archive` local eval outputs (not committed)
- `configs/` local ephemeral eval configs (ignored, not committed)
- `storage/config.json` tracked storage config for `customer-data` operations
- `docs/` tenant-specific operating docs (see `docs/tenant-docs-contract.md`)
- `reports/` local-only point-in-time analysis notes (ignored, non-authoritative, drift allowed)
- `examples/` tenant-scoped helper scripts and one-off runnable examples
- `README.md` tenant landing page and quick links

Core eval remains unified-JSONL only. Tenant-specific adapters should be implemented as offline
conversion scripts under `code/`, not runtime eval plugins.

Tenant-specific documentation belongs under `tenants/<tenant_id>/docs/` and should be checked in.
Point-in-time analysis in `tenants/<tenant_id>/reports/` is local-only and must not be treated as source of truth.
Synthetic examples and dataset payloads under `tenants/<tenant_id>/datasets/` are local cache and should not be checked in.
