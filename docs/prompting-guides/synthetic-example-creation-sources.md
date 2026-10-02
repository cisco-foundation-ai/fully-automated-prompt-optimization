<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Synthetic Example Creation Sources

## Purpose
This guide curates external sources for creating high-quality synthetic examples for eval datasets.

Use this when you:
- add new synthetic cases,
- expand coverage for recurring failures,
- or tighten synthetic-data quality controls before running evals.

## Selection Criteria
- Prefer primary sources (official docs, standards, original papers).
- Prefer sources with actionable generation/evaluation workflows.
- Prefer guidance that supports realistic, diverse, and auditable examples.
- Track source freshness with provider "last updated" dates when available.

## Curated Sources

### 1) OpenAI: Evaluation best practices
- Link: https://developers.openai.com/api/docs/guides/evaluation-best-practices
- Why it matters:
  - Recommends including synthetic eval data as one dataset type.
  - Emphasizes continuous expansion with typical, edge, and adversarial cases.
  - Frames evaluation as an iterative engineering loop, not one-time scoring.
- How to apply in FAFO:
  - Maintain synthetic splits as living datasets.
  - Add explicit edge/adversarial coverage for recurring tenant-defined scoring failures.

### 2) OpenAI: Getting started with datasets
- Link: https://developers.openai.com/api/docs/guides/evaluation-getting-started
- Why it matters:
  - Treats datasets as a dynamic artifact that grows over time.
  - Encourages adding blind spots and new edge cases as they are found.
- How to apply in FAFO:
  - Treat `cases_synthetic.jsonl` as continuously updated, not static.
  - Add synthetic cases immediately after failure-pattern discovery.

### 3) OpenAI Cookbook: Synthetic data generation (Part 1)
- Link: https://cookbook.openai.com/examples/sdg1
- Why it matters:
  - Provides concrete prompt patterns for structured synthetic generation.
  - Highlights privacy, sparsity, and class-imbalance motivations for synthetic data.
  - Shows scaling patterns (direct generation vs code-based generation).
- How to apply in FAFO:
  - Use structured templates for synthetic artifact fields.
  - Explicitly balance underrepresented scenario types in synthetic sets.

### 4) OpenAI Cookbook: Developing hallucination guardrails
- Link: https://developers.openai.com/cookbook/examples/developing_hallucination_guardrails
- Why it matters:
  - Demonstrates eval-set-first guardrail development.
  - Calls out building a strong eval set and synthetic data workflows.
- How to apply in FAFO:
  - For each new synthetic cluster, define measurable check criteria before generation.
  - Validate generated examples against explicit guardrail checks.

### 5) Google Cloud Vertex AI: Gen AI evaluation service overview
- Link: https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview
- Why it matters:
  - Explicitly includes synthetic data generation as a path for evaluation dataset creation.
  - Emphasizes rubric-driven evaluation for actionable debugging.
- How to apply in FAFO:
  - Pair each synthetic case family with clear pass/fail expectations.
  - Keep evaluation criteria specific enough to localize failure causes.

### 6) Microsoft Learn: Generate synthetic and simulated data for evaluation
- Link: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/simulator-interaction-data
- Why it matters:
  - Documents simulator-driven dataset generation for non-adversarial and adversarial testing.
  - Shows how to generate scenario-varied interaction data when production data is limited.
- How to apply in FAFO:
  - Create scenario matrices (benign, malicious, ambiguous, conflicting signals).
  - Add adversarial-like cases for robustness and regression prevention.

### 7) Anthropic: Reduce hallucinations
- Link: https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
- Why it matters:
  - Gives concrete grounding techniques (`I don't know`, quotes, citations, verification).
  - Reinforces auditable outputs in high-stakes workflows.
- How to apply in FAFO:
  - Ensure synthetic contexts support evidence-grounded decisions.
  - Add examples that test uncertainty handling and citation-like evidence use.

### 8) MITRE ATT&CK: T1566 Phishing
- Link: https://attack.mitre.org/techniques/T1566/
- Why it matters:
  - Provides structured, current phishing tradecraft and sub-techniques.
  - Helps ground synthetic phishing/BEC examples in realistic attacker behavior.
- How to apply in FAFO:
  - Map synthetic scenarios to relevant ATT&CK techniques.
  - Avoid unrealistic indicator combinations that do not reflect known TTPs.

### 9) Self-Instruct (Wang et al., 2022/2023)
- Link: https://arxiv.org/abs/2212.10560
- Why it matters:
  - Establishes generate-then-filter as a practical synthetic-data pipeline.
  - Shows quality gains from filtering invalid or near-duplicate generations.
- How to apply in FAFO:
  - Add deterministic dedupe and quality filtering before adding new synthetic cases.
  - Reject examples that are too similar or internally inconsistent.

### 10) WizardLM / Evol-Instruct (Xu et al., 2023/2025)
- Link: https://arxiv.org/abs/2304.12244
- Why it matters:
  - Introduces stepwise complexity evolution for synthetic instructions/examples.
  - Supports deliberate construction of harder examples beyond easy baseline cases.
- How to apply in FAFO:
  - Escalate synthetic-case difficulty in controlled tiers.
  - Add "hard" variants with conflicting but plausible signals to test robustness.

## FAFO Synthetic Quality Checklist
Before committing new synthetic examples:
- Coverage:
  - Include typical, edge, and adversarial-style cases for the target failure cluster.
- Realism:
  - Keep scenario details plausible for the domain and tactic family.
- Diversity:
  - Avoid near-duplicate phrasings and repeated indicator bundles.
- Ground-truth quality:
  - Ensure label decisions are supported by evidence in context fields.
- Contract fit:
  - Verify case schema and expected checks align with active eval contracts.
- Overfitting control:
  - Avoid tenant-unique brittle strings as primary classification rules.
- Regression safety:
  - Re-run relevant baseline configs after synthetic-set updates.

## Source Metadata
- Retrieval date: February 10, 2026
- Source update dates observed during retrieval:
  - Google Vertex AI evaluation overview: Last updated February 5, 2026 (UTC)
  - Microsoft synthetic/simulated data guide: Last updated December 23, 2025
  - MITRE ATT&CK T1566: Last modified October 24, 2025
  - OpenAI Cookbook synthetic data generation (Part 1): published April 10, 2024
  - OpenAI Cookbook hallucination guardrails: published May 29, 2024
  - Self-Instruct arXiv: submitted December 20, 2022; revised May 25, 2023
  - WizardLM arXiv: submitted April 24, 2023; revised May 27, 2025
