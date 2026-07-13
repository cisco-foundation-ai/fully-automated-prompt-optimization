<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Challenge Assets

This directory contains reusable public challenge assets that are intentionally
kept outside `tenants/`.

Tenant directories are runtime workspaces. Their `datasets/` and
`source_artifacts/` payloads are local artifacts and are not tracked by git.
Challenge packages in this directory are different: they are generic public
datasets and instructions that can be copied into an example tenant or into a
participant-created tenant.

## Available Challenges

- `software_name_categorization/` - classify real software names into broad
  defender-oriented software-nature categories.

## Using a Challenge Dataset

Copy the selected challenge JSONL files into a tenant dataset directory:

```bash
mkdir -p tenants/<tenant_id>/datasets/datasets
cp fapo_challenge/software_name_categorization/data/*.jsonl \
  tenants/<tenant_id>/datasets/datasets/
```

Then point the tenant's FAPO eval configs at the copied files.
