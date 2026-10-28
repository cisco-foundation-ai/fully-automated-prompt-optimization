<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Evaluation and benchmarks

Metrics, benchmarks, judging methods, and failure modes for prompt and chain
optimization. Read it when you design metrics or a scoring profile for a new
eval config, debug a loop that does not converge, check for failure modes that
automated optimization introduces, or pick benchmarks and evaluation strategies
for a new task domain.

Related: [prompting principles](external-prompting-guides.md),
[chain patterns](agentic-chain-patterns.md), and
[synthetic data creation](synthetic-example-creation-sources.md).

## Metrics taxonomy

A robust optimization system uses vector-valued scores and combines them with a
weighted sum or with constrained optimization (for example, maximize quality
subject to safety and latency budgets).

| Category | Concrete metrics | How to evaluate | Notes for optimization |
|---|---|---|---|
| Task performance | Accuracy, exact match, pass@k, rubric-based grading | Gold labels when available; otherwise an LLM judge with calibration | LLM judges scale but have biases; calibrate them against human labels. |
| Robustness | Perturbation tests, adversarial prompts, injection attempts | Adversarial eval sets + prompt injection tests | Measure continuously, because attackers adapt. |
| Calibration | ECE, Brier score, selective prediction curves | Compare predicted confidence to actual accuracy | Useful when optimizing certainty language and refusal behavior. |
| Cost | Tokens in/out, number of model calls, tool-call cost | Track usage fields per run; sum across chain steps | Multi-step chains often explode in calls; optimize calls-per-task and caching. |
| Latency | End-to-end p50/p95, calls-in-series, tool latency | Measure wall-clock time; find serial dependencies | Chain structure is the main driver; parallelize independent steps. |
| Factuality | Factual precision, contradiction rate, self-consistency divergence | FActScore (atomic fact checking), SelfCheckGPT (sampling consistency) | Require that improvements do not increase hallucination (hard constraint). |
| Safety | Toxicity rate, harmful content rate, jailbreak success rate | Adversarial testing + human review for high stakes | Optimization loops can stumble onto jailbreak-like prompts; enforce safety gates. |

## Benchmark datasets

| Benchmark | Primary source | What it measures | Relevance to chain optimization |
|---|---|---|---|
| MT-Bench / Chatbot Arena | [Zheng et al. 2023](https://arxiv.org/abs/2306.05685) | Multi-turn chat quality via LLM-as-judge | Evaluating conversational agents; scalable judging with documented bias mitigations. |
| HELM | [Liang et al. 2022](https://arxiv.org/abs/2211.09110) | Multi-metric evaluation: calibration, robustness, fairness, toxicity, efficiency | Supports multi-objective optimization beyond accuracy. |
| BIG-bench | [Srivastava et al. 2022](https://arxiv.org/abs/2206.04615) | Broad task suite probing diverse capabilities | Detects overfitting to narrow dev sets; stress-tests prompt strategies. |
| PromptBench | [Microsoft](https://arxiv.org/abs/2306.04528) | Prompt engineering methods + adversarial prompt attacks | Evaluating prompt optimization algorithms and robustness to prompt attacks. |
| AgentBench | [Liu et al. 2023 (ICLR 2024)](https://arxiv.org/abs/2308.03688) | Agent performance in interactive environments | Targets long-horizon planning, tool use, and multi-turn control. |
| SWE-bench | [Jimenez et al. 2023/2024](https://arxiv.org/abs/2310.06770) | Real-world GitHub issue resolution | Exposes brittleness in tool-execution and patch-application steps. |
| TruthfulQA | [Lin et al. 2021/2022](https://arxiv.org/abs/2109.07958) | Truthfulness against common misconceptions | Detects "confident hallucination" regressions from style-focused optimization. |
| SelfCheckGPT | [Manakul et al. 2023](https://arxiv.org/abs/2303.08896) | Hallucination via sampling consistency | Zero-resource factuality check; useful as an automated metric. |
| FActScore | [Min et al. 2023](https://arxiv.org/abs/2305.14251) | Atomic factual precision against sources | Fine-grained factuality measurement for generation tasks. |

## LLM-as-judge

LLM judges are the most scalable way to evaluate open-ended tasks, but they
have known biases.

**Strengths:**

- Scale to thousands of evaluations without human labelers.
- Can evaluate subjective dimensions such as helpfulness, coherence, and safety.
- Often agree with human judges 80%+ of the time on well-defined rubrics
  (MT-Bench findings).

**Known biases** (from MT-Bench research):

| Bias | Effect |
|---|---|
| Position | Prefers the first response in pairwise comparisons |
| Verbosity | Favors longer, more detailed responses regardless of accuracy |
| Self-enhancement | Favors outputs from the same model family |
| Authority | Favors responses that cite sources or sound confident |

**Mitigations:**

- Swap the candidates' positions and average the scores.
- Score against a rubric with explicit criteria instead of open-ended
  preference.
- Calibrate the judge against human-labeled gold sets, with a
  train/validation/test split for the judge itself.
- Use multiple judge models and aggregate.
- Track the judge's TPR and TNR separately; a judge that always passes is
  useless.

## Reproducible experiment recipes

### Baseline prompt + chain optimization

The default template for any task domain:

1. **Define the task contract.** Specify the input schema, output schema, and
   must-have constraints (citation requirements, refusal rules, safety
   boundaries). Use structured outputs where possible to reduce parsing
   brittleness.
2. **Build datasets.** Start with about 50 failure traces for manual coding and
   taxonomy building. Formalize them as graders, then split into
   train/validation/test plus adversarial sets.
3. **Implement the eval harness.** Define scoring checks for task performance,
   format compliance, and safety. In FAFO this is a scoring profile with check
   functions.
4. **Select an optimization algorithm.** Start with cheap black-box search
   (APE-style candidate generation and selection). Move to evolutionary or
   Bayesian methods if the search space is large and noisy. Consider DSPy for
   multi-module workflows.
5. **Record traces and costs.** Track token usage and call counts per run. Store
   full traces for qualitative analysis.

### RAG pipeline optimization

1. Start from a standard RAG design (retriever + generator).
2. Evaluate retrieval and response separately (retrieval recall/precision versus
   answer quality).
3. Optimize in stages: retrieval parameters (chunking, top-k, embedding model) →
   grounding prompt (citation rules, how to use passages) → fallback strategy
   (handling insufficient retrieval).
4. Add prompt-injection tests against retrieved content; indirect injection via
   retrieved documents is a known attack vector.

### Tool-using agent optimization

1. Define tools with strict schemas (explicit parameter types, descriptions,
   constraints).
2. Add a tool-choice evaluator that measures unnecessary tool calls, wrong tool
   selection, and invalid arguments.
3. Optimize the tool instruction prompt and the error recovery policy.
4. Include safety tests for tool misuse (data exfiltration, unsafe actions).

## Common failure modes in automated optimization

| Failure mode | Description | How to detect |
|---|---|---|
| Overfitting to judge | The optimizer exploits judge biases (verbosity, position, style) to inflate scores without real quality gains. | Compare judge scores to human evaluation on a held-out set; track divergence over iterations. |
| Narrow dev set overfitting | The prompt improves on a curated benchmark but hurts the real-world distribution. | Evaluate on broad test sets (BIG-bench, HELM-style); monitor production performance separately. |
| Formatting brittleness | Small prompt changes break downstream parsers while content quality seems to improve. | Include format/schema compliance checks in every eval run; use structured outputs where possible. |
| Hallucination regression | Better style masks more factual errors. | Include factuality metrics (FActScore, SelfCheckGPT, TruthfulQA-style checks) as hard constraints. |
| Prompt injection vulnerability | Optimized prompts unintentionally weaken injection defenses, or the optimizer finds prompts that bypass safeguards. | Run injection test suites on every candidate; treat injection failures as disqualifying. |
| Cost/latency blowup | Multi-step chains or more sampling push costs past budget. | Track tokens and call counts per optimization iteration; set hard cost ceilings. |

## Framework-level mitigations

These belong in the optimization framework, not in ad-hoc fixes:

1. **Hard safety gates during search.** Disqualify candidates that fail safety
   checks before measuring quality gains. Never trade safety for quality.
2. **Defense-in-depth for prompt injection.** Treat retrieved and web content as
   untrusted; isolate and sanitize it; run injection classifiers; constrain tool
   permissions. This follows OWASP guidance and provider-specific layered
   defense strategies.
3. **Judge calibration and gold sets.** Split judge development into
   train/validation/test. Measure both TPR and TNR so the judge is not trivially
   "always pass".
4. **Multi-objective optimization.** Do not optimize accuracy alone. Track
   calibration, robustness, factuality, and efficiency alongside task
   performance.
5. **Version pinning and regression testing.** Store prompts and chains as
   versioned artifacts. Re-run eval suites on every change. Integrate into CI/CD
   when possible.

## FAFO mapping

| Concept | FAFO equivalent | How to apply |
|---|---|---|
| Scoring profile | `scoring_profile` in eval config | Each eval config specifies which checks to run. Map metric categories to check functions. |
| Multi-metric evaluation | `score_breakdown` in `results.jsonl` | Per-check scores already give vector-valued evaluation. Rank by composite score, but inspect individual checks for regressions. |
| LLM-as-judge | LLM-based check functions in scoring profiles | Calibrate judge checks against human-labeled cases. Track TPR/TNR per check. |
| Eval harness | `run_eval_and_summarize.py` / eval-runner skill | Supports reproducible eval runs with summary output. |
| Dataset splits | `cases_synthetic.jsonl` + production cases | Keep synthetic (adversarial/edge) and production-derived datasets separate. Use `/project:synthetic-samples` to create and `/project:synthetic-pruner` to validate. |
| Versioned prompts | Variant files in `tenants/<id>/prompts/variants/` | Each iteration creates a new variant file. The config points to the active variant. |
| Regression testing | Baseline configs + before/after comparison | Re-run baseline configs after every prompt change. Compare per-check scores. |
| Iteration loop | [`docs/processes/prompt-iteration-loop.md`](../processes/prompt-iteration-loop.md) | Iteration process with stop criteria and planning template. |

## Source links

Benchmark papers are linked in the [benchmark table](#benchmark-datasets).
Other sources:

- OpenAI evaluation flywheel: https://cookbook.openai.com/examples/evaluation/getting_started_with_openai_evals
- OWASP LLM Top 10: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- lm-evaluation-harness: https://github.com/EleutherAI/lm-evaluation-harness

Retrieval date for this source set: March 6, 2026.
