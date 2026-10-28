<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Documentation Contract

Every tenant under `tenants/<tenant_id>/` must include a minimum set of
tenant-specific docs, so skills and operators can run and iterate evals without
guessing. Start from the [templates](templates/tenant-docs/).

## Required files

- `tenants/<tenant_id>/README.md`
- `tenants/<tenant_id>/docs/tenant-profile.md`
- `tenants/<tenant_id>/docs/data-contract.md`
- `tenants/<tenant_id>/docs/prompt-contract.md`
- `tenants/<tenant_id>/docs/eval-operations.md`
- `tenants/<tenant_id>/docs/iteration-playbook.md`
- `tenants/<tenant_id>/docs/change-log.md`
- `tenants/<tenant_id>/docs/docs-index.yaml`

## Canonical lookup

- Skills should resolve tenant docs from `docs/docs-index.yaml` first. If it
  is unavailable, they may fall back to the default filenames.
- Only files under `tenants/<tenant_id>/docs/` are canonical for tenant policy
  and operations.
- `tenants/<tenant_id>/reports/` is reserved for local-only, point-in-time
  analysis notes that may drift. Reports are non-authoritative and must not be
  used as source-of-truth inputs for automation or policy decisions.

## Validation

```bash
python scripts/check_tenant_docs.py                       # all tenants
python scripts/check_tenant_docs.py --tenant <tenant_id>  # one tenant
```

The check fails when:

- A required file is missing.
- The tenant profile, data contract, prompt contract, eval operations, or
  iteration playbook is missing a `##` section heading from its template.
- `docs-index.yaml` lacks `version`, `tenant_id`, `canonical_docs`, or
  `last_validated`, or its `tenant_id` differs from the tenant directory name.
- `canonical_docs` does not map each of `tenant_profile`, `data_contract`,
  `prompt_contract`, `eval_operations`, `iteration_playbook`, and `change_log`
  to an existing path inside the tenant directory.
