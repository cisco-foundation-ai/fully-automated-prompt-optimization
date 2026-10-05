<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Evaluation and Benchmarks

## Purpose

Evaluation methods, metrics, benchmarks, and failure modes for prompt and chain optimization.

Use this when:
- Designing metrics or scoring profiles for a new eval config.
- Diagnosing why an optimization loop is not converging.
- Understanding failure modes that automated optimization can introduce.
- Selecting benchmarks or evaluation strategies for a new task domain.

Related:
- For prompt-writing principles, see `external-prompting-guides.md`.
- For chain structure patterns, see `agentic-chain-patterns.md`.
- For synthetic data creation, see `synthetic-example-creation-sources.md`.

## Metrics Taxonomy

A robust optimization system uses vector-valued scores and applies either weighted sums or constrained optimization (e.g., maximize quality subject to safety and latency budgets).

| Category | Concrete metrics | How to evaluate | Notes for optimization |
|---|---|---|---|
| Task performance | Accuracy, exact match, pass@k, rubric-based grading | Gold labels when available; otherwise LLM judge with calibration | LLM judges are scalable but have biases; calibrate against human labels. |
| Robustness | Perturbation tests, adversarial prompts, injection attempts | Adversarial eval sets + prompt injection tests | Must be measured continuously because attackers adapt. |
| Calibration | ECE, Brier score, selective prediction curves | Compare predicted confidence to actual accuracy | Useful when optimizing certainty language and refusal behavior. |
| Cost | Tokens in/out, number of model calls, tool-call cost | Track usage fields per run; sum across chain steps | Multi-step chains often explode in calls; optimize calls-per-task and caching. |
| Latency | End-to-end p50/p95, calls-in-series, tool latency | Measure wall-clock time; identify serial dependencies | Chain structure is the main driver; parallelize independent steps. |
| Factuality | Factual precision, contradiction rate, self-consistency divergence | FActScore (atomic fact checking), SelfCheckGPT (sampling consistency) | Require improvements not to increase hallucination (hard constraint). |
| Safety | Toxicity rate, harmful content rate, jailbreak success rate | Adversarial testing + human review for high stakes | Optimization loops can inadvertently discover jailbreak-y prompts; enforce safety gates. |

## Benchmark Datasets

| Benchmark | Primary sources | What it measures | Relevance to chain optimization |
|---|---|---|---|
| MT-Bench / Chatbot Arena | Zheng et al. 2023 | Multi-turn chat quality via LLM-as-judge | Evaluating conversational agents; scalable judging with documented bias mitigations. |
| HELM | Liang et al. 2022 | Multi-metric evaluation: calibration, robustness, fairness, toxicity, efficiency | Directly supports multi-objective optimization beyond accuracy alone. |
| BIG-bench | Srivastava et al. 2022 | Broad task suite probing diverse capabilities | Detects overfitting to narrow dev sets; stress-tests prompt strategies. |
| PromptBench | Microsoft | Prompt engineering methods + adversarial prompt attacks | Evaluating prompt optimization algorithms and robustness to prompt attacks. |
| AgentBench | Liu et al. 2023 (ICLR 2024) | Agent performance in interactive environments | Targets long-horizon planning, tool use, and multi-turn control. |
| SWE-bench | Jimenez et al. 2023/2024 | Real-world GitHub issue resolution | Exposes brittleness in tool-execution and patch-application steps. |
| TruthfulQA | Lin et al. 2021/2022 | Truthfulness against common misconceptions | Detects "confident hallucination" regressions from style-focused optimization. |
| SelfCheckGPT | Manakul et al. 2023 | Hallucination via sampling consistency | Zero-resource factuality check; useful as an automated metric. |
| FActScore | Min et al. 2023 | Atomic factual precision against sources | Fine-grained factuality measurement for generation tasks. |

## LLM-as-Judge

LLM-based evaluation is the most scalable approach for open-ended tasks but has known biases.

**Capabilities:**
- Scales to thousands of evaluations without human labelers.
- Can evaluate subjective dimensions (helpfulness, coherence, safety).
- Agreement with human judges is often 80%+ on well-defined rubrics (MT-Bench findings).

**Known biases (from MT-Bench research):**
- Position bias: prefers the first response in pairwise comparisons.
- Verbosity bias: favors longer, more detailed responses regardless of accuracy.
- Self-enhancement bias: favors outputs from the same model family.
- Authority bias: favors responses that cite sources or use confident language.

**Mitigations:**
- Swap position of candidates and average scores.
- Use rubric-based scoring with explicit criteria rather than open-ended preference.
- Calibrate judge against human-labeled gold sets (train/validation/test split for the judge itself).
- Use multiple judge models and aggregate.
- Track TPR and TNR of the judge separately — a judge that always passes is useless.

## Reproducible Experiment Recipes

### Baseline Prompt + Chain Optimization

Use this as the default template regardless of task domain:

1. **Define task contract**: Specify input schema, output schema, must-have constraints (citation requirements, refusal rules, safety boundaries). Use structured outputs where possible to reduce parsing brittleness.

2. **Build datasets**: Start with ~50 failure traces for manual coding and taxonomy building. Formalize as graders, then split into train/validation/test + adversarial sets.

3. **Implement eval harness**: Define scoring checks that cover task performance, format compliance, and safety. In FAFO, this means a scoring profile with check functions.

4. **Select optimization algorithm**: Start with cheap black-box search (APE-style candidate generation + selection). Graduate to evolutionary or Bayesian methods if the search space is large and noisy. Consider DSPy when the workflow is multi-module.

5. **Record traces and costs**: Track token usage and call counts per run. Store full traces for qualitative analysis.

### RAG Pipeline Optimization

1. Start from standard RAG design (retriever + generator).
2. Evaluate retrieval and response separately (retrieval recall/precision vs answer quality).
3. Optimize in stages: retrieval parameters (chunking, top-k, embedding model) → grounding prompt (citation rules, how to use passages) → fallback strategy (insufficient retrieval handling).
4. Add prompt-injection adversarial tests against retrieved content — indirect injection via retrieved documents is a known attack vector.

### Tool-Using Agent Optimization

1. Define tools with strict schemas (explicit parameter types, descriptions, constraints).
2. Add tool-choice evaluator: measure unnecessary tool calls, wrong tool selection, invalid arguments.
3. Optimize tool instruction prompt and error recovery policy.
4. Include safety tests for tool misuse (data exfiltration, unsafe actions).

## Common Failure Modes in Automated Optimization

| Failure mode | Description | How to detect |
|---|---|---|
| Overfitting to judge | Optimizer exploits judge biases (verbosity, position, style) to inflate scores without real quality gains. | Compare judge scores to human evaluation on a held-out set; track divergence over iterations. |
| Narrow dev set overfitting | Prompt improves on curated benchmark while harming real-world distribution. | Evaluate on broad test sets (BIG-bench, HELM-style); monitor production performance separately. |
| Formatting brittleness | Small prompt changes break downstream parsers despite appearing to improve content quality. | Include format/schema compliance checks in every eval run; use structured outputs where possible. |
| Hallucination regression | Better style masks increased factual errors. | Include factuality metrics (FActScore, SelfCheckGPT, TruthfulQA-style checks) as hard constraints. |
| Prompt injection vulnerability | Optimized prompts inadvertently weaken injection defenses, or optimizer discovers prompts that bypass safeguards. | Run injection test suites on every candidate; treat injection failures as disqualifying. |
| Cost/latency blowup | Multi-step chains or increased sampling inflate costs beyond budget. | Track tokens and call counts per optimization iteration; set hard cost ceilings. |

## Framework-Level Mitigations

These belong in the optimization framework, not as ad-hoc fixes:

1. **Hard safety gates during search**: Disqualify candidates that violate safety checks before measuring quality gains. Never trade safety for quality.

2. **Defense-in-depth for prompt injection**: Treat retrieved/web content as untrusted; isolate and sanitize; run injection classifiers; constrain tool permissions. Follows OWASP guidance and provider-specific layered defense strategies.

3. **Judge calibration and gold sets**: Split judge development into train/validation/test. Measure both TPR and TNR so the judge isn't trivially "always pass."

4. **Multi-objective optimization**: Do not optimize accuracy alone. Track calibration, robustness, factuality, and efficiency alongside task performance.

5. **Version pinning and regression testing**: Store prompts/chains as versioned artifacts. Re-run eval suites on every change. Integrate into CI/CD when possible.

## FAFO Mapping

| Concept | FAFO equivalent | How to apply |
|---|---|---|
| Scoring profile | `scoring_profile` in eval config | Each eval config specifies which checks to run. Map metric categories to check functions. |
| Multi-metric evaluation | `score_breakdown` in `results.jsonl` | Per-check scores already provide vector-valued evaluation. Use composite score for ranking but inspect individual checks for regression. |
| LLM-as-judge | LLM-based check functions in scoring profiles | Calibrate judge checks against human-labeled cases. Track TPR/TNR per check. |
| Eval harness | `run_eval_and_summarize.py` / eval-runner skill | Existing harness supports reproducible eval runs with summary output. |
| Dataset splits | `cases_synthetic.jsonl` + production cases | Maintain separate synthetic (adversarial/edge) and production-derived datasets. Use `/project:synthetic-samples` for creation and `/project:synthetic-pruner` for validation. |
| Versioned prompts | Variant files in `tenants/<id>/prompts/variants/` | Each iteration creates a new variant file. Config points to the active variant. |
| Regression testing | Baseline configs + before/after comparison | Re-run baseline configs after every prompt change. Compare per-check scores. |
| Iteration loop | `docs/processes/prompt-iteration-loop.md` | Existing iteration process with stop criteria and planning template. |

## Source Links

- MT-Bench / Chatbot Arena: https://arxiv.org/abs/2306.05685
- HELM: https://arxiv.org/abs/2211.09110
- BIG-bench: https://arxiv.org/abs/2206.04615
- PromptBench: https://arxiv.org/abs/2306.04528
- AgentBench: https://arxiv.org/abs/2308.03688
- SWE-bench: https://arxiv.org/abs/2310.06770
- TruthfulQA: https://arxiv.org/abs/2109.07958
- SelfCheckGPT: https://arxiv.org/abs/2303.08896
- FActScore: https://arxiv.org/abs/2305.14251
- OpenAI evaluation flywheel: https://cookbook.openai.com/examples/evaluation/getting_started_with_openai_evals
- OWASP LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- lm-evaluation-harness: https://github.com/EleutherAI/lm-evaluation-harness

Retrieval date for this source set: March 6, 2026.
