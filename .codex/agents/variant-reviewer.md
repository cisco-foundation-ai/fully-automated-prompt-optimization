<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Variant Review Phase for Codex

Use this as a fresh-eyes checklist before evaluating a new prompt, parameter, or chain variant.

## Inputs

- `variant_type`: `prompt`, `parameter`, or `chain`
- New variant path or config path
- Previous variant path or baseline chain path
- Eval config path
- Tenant ID
- Hypothesis or failure-analysis summary

## Checks

Universal:

- Scorer compatibility: final output and required step outputs still match the scorer.
- No dataset leakage: no hardcoded answers, case IDs, or case-specific branches.
- Placeholder integrity: `${...}` placeholders are preserved and provided by the chain.
- Tenant isolation: no paths, examples, imports, or labels from other tenants.
- Scope compliance: file changes are allowed by the tenant playbook.

Prompt-specific:

- No train examples in prompts.
- No overly narrow hints that only help one eval example.
- The edit addresses a single failure pattern where possible.

Parameter-specific:

- Only allowed config knobs changed.
- Output directory and run ID behavior avoid collisions.
- Hypothesis is recorded.

Chain-specific:

- New file lives under `tenants/<tenant_id>/chains/variants/`.
- File follows `docs/processes/chain-variant-conventions.md`.
- `ChainState` fields are preserved.
- New LLM nodes use `make_llm_node` or the documented node callable contract.
- Imports are safe and have no import-time side effects.

## Verdict

Return one of:

- `pass`: no issues
- `warn`: no blockers, but warnings should be reported
- `fail`: blocking issue found

For each issue, include `check_name`, `severity`, `description`, and a line or section reference.
