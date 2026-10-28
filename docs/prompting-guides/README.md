<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Prompting guides

Distilled prompting, chain-design, and evaluation guidance for FAFO operators
during prompt iteration.

| Document | Covers | Read when |
|---|---|---|
| [`external-prompting-guides.md`](external-prompting-guides.md) | Nine prompting principles; failure-cluster-to-fix map | You want a quick reference for prompting principles (optional) |
| [`agentic-chain-patterns.md`](agentic-chain-patterns.md) | Chain structures: ReAct, Reflexion, Tree of Thoughts, Self-Refine, Least-to-Most, Plan-and-Solve, Tool-Augmented Generation | Failure analysis points to the chain structure, not just the prompt text |
| [`evaluation-and-benchmarks.md`](evaluation-and-benchmarks.md) | Metrics, benchmarks, LLM-as-judge, optimization failure modes and mitigations | You design scoring profiles, diagnose convergence problems, or check for optimization pitfalls |
| [`synthetic-example-creation-sources.md`](synthetic-example-creation-sources.md) | Sources for synthetic eval data; quality checklist | You add or revise synthetic eval cases |

## Maintenance

- Revisit these guides when major provider prompting docs are updated.
- Refresh the top-5 source set in `external-prompting-guides.md` at least
  quarterly, or sooner if a canonical provider doc changes materially.
- Check the retrieval date in each document and refresh stale source links.
- Keep summaries actionable and paraphrased, and keep source links current.
