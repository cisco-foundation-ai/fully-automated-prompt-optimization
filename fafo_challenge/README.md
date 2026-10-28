<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO challenge assets

Reusable public challenge datasets and instructions, kept outside `tenants/` on
purpose.

Tenant directories are runtime workspaces: their `datasets/` and
`source_artifacts/` payloads are local and not tracked by git. Challenge
packages are generic public datasets and instructions that you copy into an
example tenant or a tenant you create.

## Available challenges

| Challenge | Task |
|---|---|
| [`software_name_categorization/`](software_name_categorization/) | Classify real software names into broad, defender-oriented software-nature categories. |

## Using a challenge dataset

Copy the challenge JSONL files into a tenant dataset directory:

```bash
mkdir -p tenants/<tenant_id>/datasets/datasets
cp fafo_challenge/software_name_categorization/data/*.jsonl \
  tenants/<tenant_id>/datasets/datasets/
```

Then point the tenant's FAFO eval configs at the copied files.
