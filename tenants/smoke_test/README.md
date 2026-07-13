<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# smoke_test tenant

Minimal tenant used for integration smoke testing. Contains trivially easy yes/no
questions so the eval pipeline can be verified end-to-end without domain expertise.

- **variant-001** (bad): No format constraint — LLM gives verbose answers — exact-match fails.
- **variant-002** (good): Strict "yes or no" constraint — exact-match passes.

## Running the smoke test

```bash
OPENAI_API_KEY="<your-openai-api-key>" pytest -m integration -v
```
