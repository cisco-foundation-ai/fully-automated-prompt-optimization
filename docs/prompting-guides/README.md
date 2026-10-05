<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Prompting Guides

This folder contains distilled prompting, optimization, and evaluation guidance used by FAFO operators during prompt iteration.

## Documents

| Document | What it covers | When to read |
|---|---|---|
| `external-prompting-guides.md` | What makes a good prompt — 9 unified principles, failure-cluster-to-fix mapping | Optional reference for prompting principles |
| `agentic-chain-patterns.md` | What chain structures to use — ReAct, Reflexion, Tree of Thoughts, Self-Refine, Plan-and-Solve | When failure analysis suggests a chain structure change, not just a prompt edit |
| `evaluation-and-benchmarks.md` | How to measure quality — metrics taxonomy, benchmarks, LLM-as-judge, failure modes, mitigations | When designing scoring profiles, diagnosing convergence issues, or understanding optimization pitfalls |
| `synthetic-example-creation-sources.md` | How to create test data — synthetic data sources, quality checklist | When adding or revising synthetic eval cases |

## How to Use

1. Consult `external-prompting-guides.md` when you want a quick reference for prompting principles.
2. If failures suggest the chain structure is wrong (not just the prompt text), consult `agentic-chain-patterns.md`.
3. When designing or debugging evaluation, read `evaluation-and-benchmarks.md`.
4. When creating synthetic test data, follow `synthetic-example-creation-sources.md`.

## Maintenance

- Revisit this folder when major provider prompting docs are updated.
- Refresh the top-5 prompt optimization source set in `external-prompting-guides.md` at least quarterly or when one of the canonical provider docs materially changes.
- Check retrieval dates in each document and refresh source links when stale.
- Keep summaries actionable and paraphrased; keep links to source docs current.
