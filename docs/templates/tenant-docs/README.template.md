<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# <tenant_id>

## Purpose
- Describe the tenant, security domain, and current engagement scope.

## Status
- Lifecycle: active/inactive
- Last validated: YYYY-MM-DD
- Owner: <team or person>

## Quick Links
- Tenant profile: `docs/tenant-profile.md`
- Data contract: `docs/data-contract.md`
- Prompt contract: `docs/prompt-contract.md`
- Eval operations: `docs/eval-operations.md`
- Iteration playbook: `docs/iteration-playbook.md`
- Change log: `docs/change-log.md`

Link to the canonical global process docs instead of duplicating them in tenant docs.

## Quick Run
- `python scripts/eval/run_eval_and_summarize.py --config tenants/<tenant_id>/configs/local-<run-name>.json`

## Data Safety
- Do not modify `source_artifacts/` unless explicitly requested.
- Keep secrets out of committed files.
