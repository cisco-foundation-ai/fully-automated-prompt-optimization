<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Profile

## Organization Profile

This tenant supports the FAPO Software Name Categorization Challenge. The
workflow optimizes a single-prompt `gpt-4o-mini` classifier that maps real
software names to domains of security concern.

## Security Environment Assumptions

- Inputs contain only `context.software_name`.
- Labels represent defender-oriented concern domains, not vendor product
  categories.
- The chain should not use vendor descriptions, URLs, inventories, or external
  lookup fields as model input.
- The scorer expects one label per case.

## Threat Model Focus

The task represents software inventory triage. A defender sees a software name
and needs to classify why that software may matter from a security operations
perspective: remote access, exposure testing, data movement, runtime services,
endpoint clients, sensitive material handling, posture changes, or unrelated
utilities.

## Known Safe Patterns

- Use the train split for prompt iteration and failure attribution.
- Use eval and test only to score prompt variants.
- Keep outputs to one exact label.
- Keep tenant datasets local under `tenants/software_name_categorization/datasets/`.

## Tenant Terminology

- **software name**: The only model-visible input field.
- **category**: The expected security-concern label.
- **variant**: A candidate prompt under `prompts/modules/classify/`.
- **F1**: For this one-label-per-case task, reported per-case F1 is equivalent
  to exact-match correctness and aggregates like micro-F1.

