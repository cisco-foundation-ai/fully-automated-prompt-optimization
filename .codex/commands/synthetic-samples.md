<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Synthetic Samples for Codex

Use this when the user wants to create synthetic test cases, add edge cases, augment eval datasets, expand test coverage, or generate hard examples.

## Scope

- Create examples under a tenant synthetic examples root, such as `tenants/<tenant_id>/datasets/synthetic_artifacts/`.
- Never touch `tenants/*/source_artifacts/`.
- Keep examples synthetic and non-attributable. Do not use real customer names, domains, IPs, or secrets.
- Produce or update review CSVs when the tenant workflow expects them.

## Workflow

1. Read tenant-specific dataset requirements and `docs/references/synthetic-requirements.md`.
2. Pick a scenario type and naming pattern.
3. Create the example directory and required context files.
4. Write explicit labels in `Summary.pdf.txt` or the tenant equivalent.
5. Add or refresh `labels_review.csv` or `hard_labels_review.csv`.
6. Verify labels, filenames, and expected heuristics stay aligned.

## Guardrails

- Use placeholder internal domains such as `<internal_domain>`.
- Use synthetic external indicators only.
- Keep telemetry realistic for the tenant's domain.
- For hard cases, include conflicting but plausible signals.
