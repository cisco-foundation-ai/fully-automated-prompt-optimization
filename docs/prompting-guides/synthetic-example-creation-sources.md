<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Synthetic example creation sources

Curated external sources for creating high-quality synthetic examples for eval
datasets, plus a quality checklist. Use it when you add synthetic cases, expand
coverage for recurring failures, or tighten synthetic-data quality controls
before running evals.

## Selection criteria

- Prefer primary sources: official docs, standards, original papers.
- Prefer sources with actionable generation or evaluation workflows.
- Prefer guidance that supports realistic, diverse, and auditable examples.
- Track source freshness with provider "last updated" dates when available.

## Curated sources

| # | Source | Why it matters | How to apply in FAFO |
|---|---|---|---|
| 1 | [OpenAI: Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) | Recommends synthetic eval data as one dataset type. Stresses continuous expansion with typical, edge, and adversarial cases. Frames evaluation as an iterative engineering loop, not one-time scoring. | Maintain synthetic splits as living datasets. Add explicit edge and adversarial coverage for recurring tenant-defined scoring failures. |
| 2 | [OpenAI: Getting started with datasets](https://developers.openai.com/api/docs/guides/evaluation-getting-started) | Treats datasets as dynamic artifacts that grow over time. Encourages adding blind spots and new edge cases as they are found. | Treat `cases_synthetic.jsonl` as continuously updated, not static. Add synthetic cases right after a failure pattern is discovered. |
| 3 | [OpenAI Cookbook: Synthetic data generation (Part 1)](https://cookbook.openai.com/examples/sdg1) | Gives concrete prompt patterns for structured synthetic generation. Covers privacy, sparsity, and class imbalance as reasons for synthetic data. Shows scaling patterns (direct generation versus code-based generation). | Use structured templates for synthetic artifact fields. Explicitly balance underrepresented scenario types in synthetic sets. |
| 4 | [OpenAI Cookbook: Developing hallucination guardrails](https://developers.openai.com/cookbook/examples/developing_hallucination_guardrails) | Demonstrates eval-set-first guardrail development. Calls out building a strong eval set and synthetic data workflows. | For each new synthetic cluster, define measurable check criteria before generation. Validate generated examples against explicit guardrail checks. |
| 5 | [Google Cloud Vertex AI: Gen AI evaluation service overview](https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview) | Explicitly includes synthetic data generation as a way to create evaluation datasets. Emphasizes rubric-driven evaluation for actionable debugging. | Pair each synthetic case family with clear pass/fail expectations. Keep evaluation criteria specific enough to localize failure causes. |
| 6 | [Microsoft Learn: Generate synthetic and simulated data for evaluation](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/simulator-interaction-data) | Documents simulator-driven dataset generation for non-adversarial and adversarial testing. Shows how to generate scenario-varied interaction data when production data is limited. | Build scenario matrices (benign, malicious, ambiguous, conflicting signals). Add adversarial-like cases for robustness and regression prevention. |
| 7 | [Anthropic: Reduce hallucinations](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) | Gives concrete grounding techniques (`I don't know`, quotes, citations, verification). Reinforces auditable outputs in high-stakes workflows. | Make sure synthetic contexts support evidence-grounded decisions. Add examples that test uncertainty handling and citation-like use of evidence. |
| 8 | [MITRE ATT&CK: T1566 Phishing](https://attack.mitre.org/techniques/T1566/) | Provides structured, current phishing tradecraft and sub-techniques. Helps ground synthetic phishing/BEC examples in realistic attacker behavior. | Map synthetic scenarios to relevant ATT&CK techniques. Avoid unrealistic indicator combinations that do not reflect known TTPs. |
| 9 | [Self-Instruct (Wang et al., 2022/2023)](https://arxiv.org/abs/2212.10560) | Establishes generate-then-filter as a practical synthetic-data pipeline. Shows quality gains from filtering invalid or near-duplicate generations. | Apply deterministic deduplication and quality filtering before adding new synthetic cases. Reject examples that are too similar or internally inconsistent. |
| 10 | [WizardLM / Evol-Instruct (Xu et al., 2023/2025)](https://arxiv.org/abs/2304.12244) | Introduces stepwise complexity evolution for synthetic instructions and examples. Supports deliberately building harder examples beyond easy baseline cases. | Raise synthetic-case difficulty in controlled tiers. Add "hard" variants with conflicting but plausible signals to test robustness. |

## FAFO synthetic quality checklist

Before committing new synthetic examples, check:

| Check | Requirement |
|---|---|
| Coverage | Include typical, edge, and adversarial-style cases for the target failure cluster. |
| Realism | Keep scenario details plausible for the domain and tactic family. |
| Diversity | Avoid near-duplicate phrasings and repeated indicator bundles. |
| Ground-truth quality | Label decisions are supported by evidence in the context fields. |
| Contract fit | Case schema and expected checks align with the active eval contracts. |
| Overfitting control | Do not use brittle, tenant-unique strings as primary classification rules. |
| Regression safety | Re-run the relevant baseline configs after synthetic-set updates. |

## Source metadata

Retrieval date: February 10, 2026.

| Source | Date observed during retrieval |
|---|---|
| Google Vertex AI evaluation overview | Last updated February 5, 2026 (UTC) |
| Microsoft synthetic/simulated data guide | Last updated December 23, 2025 |
| MITRE ATT&CK T1566 | Last modified October 24, 2025 |
| OpenAI Cookbook synthetic data generation (Part 1) | Published April 10, 2024 |
| OpenAI Cookbook hallucination guardrails | Published May 29, 2024 |
| Self-Instruct arXiv | Submitted December 20, 2022; revised May 25, 2023 |
| WizardLM arXiv | Submitted April 24, 2023; revised May 27, 2025 |
