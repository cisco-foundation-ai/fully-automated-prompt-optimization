<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Fully Automated Prompt Optimization (FAPO)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/cisco-foundation-ai/fully-automated-prompt-optimization/actions/workflows/ci.yml/badge.svg)](https://github.com/cisco-foundation-ai/fully-automated-prompt-optimization/actions/workflows/ci.yml)
[![arXiv](https://img.shields.io/badge/arXiv-2606.19605-b31b1b.svg)](https://arxiv.org/abs/2606.19605)

Demo video link: https://youtu.be/QG5mFbypNaI

An optimization framework for multi-step LLM pipelines. FAPO uses [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as an autonomous optimizer that iteratively improves prompts, agent skills, parameters, and chain architecture — guided by built-in evaluation, step-level failure analysis, and a structured variant system.

FAPO provides the full loop: **evaluate** a chain against a dataset, **analyze** what went wrong using step attribution, **create** a better variant, and **measure** whether it improved. The evaluation infrastructure exists to drive and measure optimization — not as an end in itself.

## Why pipeline-aware optimization

Multi-step LLM pipelines fail through interactions among retrieval, reasoning, and formatting steps, so optimizing the *prompt* alone can miss the real bottleneck. FAPO treats a pipeline as an **inspectable workflow**: instead of scoring only the final answer, it records every intermediate step output, then localizes each failure to a prompt, an upstream evidence source (such as retrieval), or the chain structure itself. It edits prompts when failures are prompt-addressable, and **escalates** to chain parameters or chain structure when attribution shows that prompts alone can no longer help.

Concretely, FAPO is a reusable evaluation engine (`src/hephaestus/`), a set of isolated tenant workspaces (`tenants/<id>/`), [LangGraph](https://langchain-ai.github.io/langgraph/) to represent each pipeline as a stateful graph, and Claude Code as the optimization orchestrator. The orchestrator is a layer **separate from the task model being optimized** — see [The optimizer vs. the task model](#the-optimizer-vs-the-task-model).

### How FAPO relates to GEPA

FAPO's baseline is **GEPA**, a prompt optimizer. FAPO builds on GEPA's evaluation setup but widens the action space and changes how candidates are chosen:

| | GEPA (baseline) | FAPO |
|---|---|---|
| **Action space** | Instruction string inside a **fixed** chain | Prompt text **+** agent skills **+** chain parameters **+** chain structure |
| **Search** | Evolutionary search (MIPROv2-Heavy) over prompts | Attribution-driven scoped edits, escalating only when evidence requires it |
| **Failure signal** | Final-score feedback | Step-level attribution over recorded intermediate outputs |

When the two are compared, both start from the same pipeline and the same baseline prompts; the only difference is the optimizer. FAPO does **not** depend on GEPA or DSPy as libraries — they are points of comparison, and some tenants merely reuse DSPy-style prompt *text* for parity. For benchmark results across six tasks and three task models, see the FAPO paper.

## Quick start

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

# For MCP support (agentic workflows with tool calling)
pip install -e ".[mcp]"
```

### 2. Set up a tenant

A tenant is a self-contained optimization project. You need four entities: a dataset, a chain, a scorer, and a config that wires them together.

**Dataset** — a JSONL file with test cases (`my_dataset.jsonl`):
```json
{"case_id": "1", "task_type": "qa", "context": {"question": "What is the capital of France?"}, "expected": {"answer": "Paris"}, "metadata": {}}
{"case_id": "2", "task_type": "qa", "context": {"question": "What is 2 + 2?"}, "expected": {"answer": "4"}, "metadata": {}}
```

**Chain** — a LangGraph pipeline that processes each case (`my_chain.py`):
```python
from langgraph.graph import StateGraph, END
from src.hephaestus.chains.types import ChainState
from src.hephaestus.chains.nodes import make_llm_node

def build_chain(provider, config):
    graph = StateGraph(ChainState)
    graph.add_node("answer", make_llm_node(
        provider=provider,
        prompt_template_path=config["prompt_paths"]["answer"],
        output_key="answer",
    ))
    graph.set_entry_point("answer")
    graph.add_edge("answer", END)
    return graph.compile()
```

**Scorer** — compares chain output to expected answers (`my_scorer.py`):
```python
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        assert "answer" in case.expected, "Missing 'answer' in expected"

    def score_case(self, case, output_text, scoring_profile):
        expected = case.expected["answer"].strip().lower()
        predicted = output_text.strip().lower()
        em = 100.0 if predicted == expected else 0.0
        return {"composite_score": em, "score_breakdown": {"exact_match": em}}
```

**Prompt template** — the LLM instructions with placeholders (`prompt.md`):
```
System: You are a helpful assistant. Answer concisely in as few words as possible.

User: ${question}
```

**Config** — ties everything together (`eval.json`):
```json
{
  "tenant_id": "my_project",
  "provider": "openai",
  "provider_settings": { "model": "gpt-4o", "temperature": 0.0, "max_tokens": 1024 },
  "dataset": { "path": "my_dataset.jsonl" },
  "chain": {
    "path": "my_chain.py",
    "fn": "build_chain",
    "config": { "prompt_paths": { "answer": "prompt.md" } }
  },
  "scoring_profile": { "scorer": { "module_path": "my_scorer.py", "class_name": "Scorer" } },
  "output_dir": "eval_output/"
}
```

### 3. Run a baseline eval

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
python -m hephaestus.cli eval --config eval.json
cat eval_output/summary.md
```

### 4. Optimize

Run the optimization loop with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) or Codex from your project directory.

With Claude Code, run the optimization agent:

```
> /optimization
  → Tenant: my_project
  → Config: eval.json
  → Success criteria: composite_score >= 90
```

With Codex, ask it to run the FAPO optimization workflow:

```
Optimize eval quality for tenant "my_project".
Config: eval.json
Success criteria: composite_score >= 90
Follow .codex/agents/optimization.md.
```

The agent autonomously analyzes failures, creates improved prompt variants, evaluates them, and iterates until your target score is reached. See [Optimization loop](#optimization-loop) for the full details.

> **Note:** `/optimization` runs inside Claude Code, which acts as the optimizer. The model it optimizes is whatever you set under `provider` / `provider_settings.model` (here, GPT-4o) — the two are independent.

---

## Create an evaluation asset

An evaluation asset turns a small set of trusted, feedback-labeled traces and a
larger set of unlabeled traces into versioned datasets for evaluation and
optimization. It can be the first step in creating a tenant: the pipeline does
not require an existing chain, prompt, config, adapter, or legacy
`tenants/<tenant_id>/datasets/` directory.

Both input files must already use the vendor-neutral
[`fapo-evaluation-input-v1`](docs/processes/evaluation-input-contract.md)
JSONL contract. FAPO copies them into a self-contained workspace at:

```text
tenants/<tenant_id>/evaluation_assets/<asset_id>/
├── config.json
├── config_history.jsonl
├── pipeline_state.json
├── events.jsonl
├── lineage.json                 # extended versions only
├── reuse_manifest.json          # extended versions only
├── asset_manifest.json
└── stages/
    ├── 01_raw_inputs/
    ├── 02_prepared_inputs/
    ├── 03_rubric_extraction/
    ├── 04_intent_clustering/
    ├── 05_coverage_decisions/
    │   └── review_queue/
    ├── 06_label_inference/
    ├── 07_synthetic_coverage/
    └── 08_dataset_splits/
```

After creation, every stage reads from this workspace rather than the original
files or other tenant resources. Each stage owns only its outputs and reads
inputs from earlier stage folders.

### Eight-stage workflow

| Stage | Purpose |
|---|---|
| 1. Validate raw inputs | Validate the canonical contract and record source counts and hashes. |
| 2. Prepare inputs | Redact sensitive values, apply canonical defaults, and build intent text without renaming fields. |
| 3. Extract rubrics | Use the selected LLM to turn trusted feedback into scoreable rubrics, trusted intents, and trusted cases. |
| 4. Cluster intents | Embed unlabeled intent records and build the requested number of route-aware clusters. |
| 5. Decide coverage | Match clusters to trusted intents and sample representative traces from coverage gaps into a labeling queue. |
| 6. Infer labels | Infer rubrics and evaluation cases only for clusters supported by trusted evidence. |
| 7. Expand coverage | Optionally generate and filter a configured number of synthetic cases per supported cluster. |
| 8. Build splits | Create group-safe train, validation, and test splits plus an automatic, trusted-only 20% regression gate. |

Stages are checkpointed in `pipeline_state.json`, with an append-only history in
`events.jsonl`. If a run fails, fix the input, credential, model-access, or core
error and run it again; completed stages are skipped.

### Use the Evaluation Asset Studio

Start the shared FAPO UI:

```bash
python -m hephaestus.cli ui --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/evaluation-assets/`. The Studio lets you choose:

- Tenant and asset IDs.
- Canonical labeled and unlabeled JSONL files.
- The rubric extraction and inference model.
- An OpenAI embedding model or the local `tfidf` fallback.
- The exact cluster count.
- The Stage 5 intent-match threshold (default `0.6`).
- Whether Stage 7 synthetic coverage is enabled and how many candidates to
  request per supported cluster.

The tenant pipeline view shows the status, inputs, processing, outputs, and a
bounded example for every stage, including cluster exploration and the rendered
coverage report. Its artifact guide groups stable technical files into **Key
outputs**, **Needs attention**, **Supporting data**, and **Diagnostics**, with a
friendly name and purpose beside every filename. If a run stops, the Studio
can resume with the existing decisions or edit them first. FAPO automatically
reruns from the earliest affected stage and preserves earlier checkpoints.

Completed assets also expose **Extend asset**, which creates a new immutable
version from additional canonical data:

- **Keep original clustering** accepts labeled additions only. It reuses the
  parent's Stage 4 inventory and extracts Stage 3 rubrics only for the new
  feedback.
- **Rerun clustering** accepts new unlabeled records, rebuilds Stage 4 over the
  combined traffic, and writes `cluster_lineage.jsonl` to relate previous and
  current clusters.

Both modes recalculate coverage, inferred labels, optional synthesis, and
complete dataset splits in the new version. The parent asset is never changed.

### Use the CLI

Set the relevant provider credential, then create and run the asset:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"

python -m hephaestus.cli assets create \
  --tenant <tenant_id> \
  --asset-id v1 \
  --feedback <labeled_feedback.jsonl> \
  --unlabeled <unlabeled.jsonl> \
  --rubric-model gpt-5.5 \
  --embedding-model text-embedding-3-small \
  --clusters 20 \
  --match-threshold 0.6

python -m hephaestus.cli assets run \
  --tenant <tenant_id> \
  --asset-id v1

python -m hephaestus.cli assets status \
  --tenant <tenant_id> \
  --asset-id v1
```

Extend a completed version from the CLI:

```bash
python -m hephaestus.cli assets extend \
  --tenant <tenant_id> \
  --parent-asset-id v1 \
  --asset-id v2 \
  --additional-feedback <additional_feedback.jsonl> \
  --clustering-mode keep
```

Use `--additional-unlabeled <additional_unlabeled.jsonl>
--clustering-mode refresh` when the intent landscape must be rebuilt.

Add `--enable-synthetic-coverage --synthetic-cases-per-cluster <count>` to
enable Stage 7. Use `--embedding-model tfidf` for deterministic local
vectorization without an embedding API call. FAPO never silently changes
providers after a failure.

To change decisions while resuming, pass only the settings that should change:

```bash
python -m hephaestus.cli assets run \
  --tenant <tenant_id> \
  --asset-id v1 \
  --clusters 12 \
  --match-threshold 0.5 \
  --embedding-model tfidf
```

Rubric changes restart at Stage 3; embedding or cluster-count changes at Stage
4; matching changes at Stage 5; synthetic settings at Stage 7; and split
settings at Stage 8. Each revision is appended to `config_history.jsonl` and
`events.jsonl` before stale downstream outputs are removed and rebuilt.

### Troubleshoot OpenAI SSL connections

If an OpenAI request fails because TLS/SSL certificate verification is blocked,
upgrade the OpenAI HTTP and certificate packages in the Python environment that
runs FAPO:

```bash
python3 -m pip install --upgrade openai httpx certifi truststore
```

Then uncomment the `try`/`import truststore`/
`truststore.inject_into_ssl()`/`except ImportError` block at:

- `src/hephaestus/providers/openai.py`, lines 50–54.
- `src/hephaestus/datasets/rubric_providers.py`, lines 85–89.
- `src/hephaestus/datasets/embedding_providers.py`, lines 61–65.

Restart the FAPO UI or CLI process after changing the environment or source,
then resume the failed asset run.
Use this procedure only for an SSL/certificate error; it does not fix
an invalid API key, unavailable model, rate limit, or malformed response.

The UI, CLI, and evaluation-asset assistants all trigger and monitor the same
core implementation under `src/hephaestus/evaluation_assets/`; agents do not
implement the data transformations themselves. See the full
[feedback and unlabeled trace flow](docs/processes/feedback-dataset-flow.md)
for artifact details, trust boundaries, and split semantics.

---

## How it works

The core workflow is an **optimization loop**. Each pass runs the same six stages — the labels below are reused throughout this README:

```
      ┌────────────────────────────────────────────────┐
      │                 OPTIMIZATION LOOP              │
      └────────────────────────────────────────────────┘

  1. Evaluate    Dataset ─> Chain ─> Scorer ─> Results
                 (JSONL)    (LangGraph)        (summary.md, results.jsonl)
                      │
                      ▼
  2. Attribute   classify failures by pipeline step and fix type
                      │
                      ▼
  3. Propose     generate one scoped variant (prompt / skill / parameter / chain)
                      │
                      ▼
  4. Review      independent guardrail check (scope, leakage, placeholders)
                      │
                      ▼
  5. Compare     re-run the variant; compare to the previous best
                      │
                      ▼
  6. Iterate or escalate
                 keep improved variants; iterate at this level, or
                 escalate to the next level when attribution requires it
                      │
                      └──────────► back to step 1 (next cycle)
```

You wire the dataset, chain, and scorer together with a **config file** and run `python -m hephaestus.cli eval --config <config>.json` to perform a single **Evaluate** stage. The remaining stages are driven by the Claude Code optimizer (see [Optimization loop](#optimization-loop)). A separate reviewer checks every proposed change before it is re-evaluated, and accepted variants are compared on aggregate validation scores only.

---

## Concepts

### Datasets

A dataset is a JSONL file. Each line is one test case:

```json
{
  "case_id": "unique-id",
  "task_type": "qa",
  "context": {
    "question": "Your input field(s) here"
  },
  "expected": {
    "answer": "The correct output"
  },
  "metadata": {
    "difficulty": "hard",
    "source": "manual"
  }
}
```

- **`case_id`** — unique identifier for the case (required)
- **`task_type`** — label for the kind of task, e.g. `"qa"`, `"summarization"` (required)
- **`context`** — key-value pairs passed into your chain as input variables (required)
- **`expected`** — ground truth used by your scorer (required; the schema inside `expected` is up to your scorer -- the engine does not inspect it)
- **`metadata`** — arbitrary key-value pairs for filtering and analysis (required, may be `{}`)

### Chains

A chain is a [LangGraph](https://langchain-ai.github.io/langgraph/) state graph that processes each test case. You define it as a Python module with a `build_chain` function (see the [Quick start](#quick-start) for a minimal single-node example).

**`make_llm_node`** reads a prompt template, substitutes `${variables}` from the chain state, calls the LLM, and writes the response back to state.

For multi-step chains, add more nodes and edges:

```python
def build_chain(provider, config):
    graph = StateGraph(ChainState)

    graph.add_node("retrieve", my_retrieval_node)
    graph.add_node("summarize", make_llm_node(
        provider=provider,
        prompt_template_path=config["prompt_paths"]["summarize"],
        output_key="summary",
    ))
    graph.add_node("answer", make_llm_node(
        provider=provider,
        prompt_template_path=config["prompt_paths"]["answer"],
        output_key="answer",
    ))

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "summarize")
    graph.add_edge("summarize", "answer")
    graph.add_edge("answer", END)

    return graph.compile()
```

Later nodes can reference earlier outputs in their prompts using `${steps.summarize.output}`.

### Chain state

Every chain operates on a shared **state** with four protocol fields:

| Field | Type | Description |
|-------|------|-------------|
| `context` | `Dict[str, str]` | Input from the dataset case (`case.context`) |
| `output_text` | `str` | The final output, read by the scorer |
| `step_outputs` | `Dict[str, str]` | Intermediate outputs, **keyed by node name** |
| `diagnostics` | `List[str]` | Debug traces and warnings (e.g. missing placeholders) |

`make_llm_node` ties this together: it merges `context` with prior `step_outputs` (exposed under keys like `steps.<name>.output`), renders the `${...}` placeholders, splits the `System:` / `User:` sections into chat messages, calls `provider.generate`, and writes its result into both `output_text` and `step_outputs[output_key]`. Because every node writes a **named** output, the pipeline is inspectable as a sequence of intermediate artifacts rather than a single opaque final string — this is what makes step attribution possible.

### Prompt templates

Prompts are Markdown files with a simple format:

```
System: You are a helpful assistant.

User: Answer the following question concisely.

Question: ${question}
Context: ${steps.retrieve.output}
```

- `${question}` is replaced by `context.question` from the dataset case
- `${steps.<node_name>.output}` is replaced by the output of a previous chain node
- Missing variables are logged as diagnostics (not hard errors)

### Skills

**Skills** are reusable units of procedural knowledge for **agentic** (tool-using) tenants — e.g. "how to handle a ranking question" or "how to sequence these tools". They live as markdown files at `tenants/<tenant_id>/skills/<skill-name>/variant-NNN.md`, each with YAML frontmatter (`name`, `description`) and a body of instructions, and are optimized exactly like prompts (clone-to-new-variant, eval, attribution, review).

A skill is **loaded at the agentic layer**: the chain node injects the configured skills into the conversation as a distinct `<available_skills>` context message right after the system prompt — mimicking an agent that discovered and loaded skills into its environment, rather than inlining them into the authored prompt template. The skills stay fully in context for every model call (deterministic), keeping the base prompt lean while the reusable know-how is factored out and iterated independently.

Skills are opt-in per tenant via two `chain.config` fields:

```json
{
  "chain": {
    "config": {
      "prompt_paths": { "agent": "tenants/my_project/prompts/modules/agent/variant-001.md" },
      "skill_paths": [
        "tenants/my_project/skills/ranking-questions/variant-001.md",
        "tenants/my_project/skills/answer-formatting/variant-001.md"
      ],
      "optimization_target": "both"
    }
  }
}
```

- **`skill_paths`** — the skill files to load (injected in order). Omit it and the tenant behaves exactly as before; skills are a no-op.
- **`optimization_target`** — `"prompt"`, `"skill"`, or `"both"` (default `"both"`). Selects which textual artifacts the optimizer iterates. When set to `"skill"` or `"both"`, the tenant must be agentic (an `mcp` section configured); the eval runner validates this.

Prompt and skill are **co-equal textual levels**: when both are available the optimizer treats them as one textual surface, routing each failure cluster to whichever artifact owns it (broad scaffold/format → base prompt; reusable task-specific procedure → a skill). See `tenants/skill_example/` for a complete worked example. In the **FAPO Explorer** UI, skills appear under the **Prompts** tab in their own section.

### Scorers

A scorer compares the chain output to the expected answer. Implement the `Scorer` base class:

```python
# my_scorer.py
from src.hephaestus.scoring.scorer import Scorer as BaseScorer

class Scorer(BaseScorer):
    def validate_case(self, case, scoring_profile):
        """Check that each case has the fields this scorer needs."""
        assert "answer" in case.expected, f"Case {case.case_id}: missing 'answer'"

    def score_case(self, case, output_text, scoring_profile):
        expected = case.expected["answer"].strip().lower()
        predicted = output_text.strip().lower()

        exact_match = 100.0 if predicted == expected else 0.0
        contains = 100.0 if expected in predicted else 0.0
        composite = 0.6 * exact_match + 0.4 * contains

        return {
            "composite_score": composite,     # 0-100, required
            "score_breakdown": {              # required dict — track individual metrics
                "exact_match": exact_match,
                "contains_answer": contains,
            },
        }
```

The engine calls `validate_case` (to catch bad data early) then `score_case` for each test case, and aggregates the results. Every scorer must return a finite `composite_score` in `[0, 100]` plus a numeric `score_breakdown` — the breakdown can expose as many task-specific metrics as you like (exact match, F1, format validity, …) while `composite_score` stays the single objective the optimizer drives.

**Pipeline-aware scoring.** Because each node writes a named output into `step_outputs` (see [Chain state](#chain-state)), a scorer for a multi-step chain can override `score_pipeline_case(case, step_outputs, scoring_profile, output_text)` and score against intermediate outputs, not just the final string. The default implementation simply scores `output_text`; the HotpotQA scorer, for example, scores the `answer` step explicitly. This is what lets optimization reason about *where* in the pipeline a case went wrong.

### Providers

FAPO supports three LLM providers out of the box:

| Provider | Config value | Auth env variable | Notes |
|----------|-------------|-------------------|-------|
| **OpenAI** | `"openai"` | `OPENAI_API_KEY` | GPT models |
| **Baseten** | `"baseten"` | `BASETEN_API_KEY` | Custom model deployments |
| **SageMaker** | `"sagemaker"` | Configurable via `api_key_env` | AWS-hosted endpoints |

Provider settings go in the config file:

```json
{
  "provider": "openai",
  "provider_settings": {
    "model": "gpt-4o",
    "temperature": 0.0,
    "max_tokens": 4096,
    "timeout_seconds": 300,
    "max_retries": 3,
    "retry_backoff_seconds": 5
  }
}
```

---

## Optimization loop

Evaluation tells you *how well* your chain performs. Optimization tells you *what to change* to make it better. FAPO includes a structured optimization loop that works at levels of increasing cost — from textual edits (prompt and agent skills) up through chain parameters and chain structure. (For the full architecture, see [docs/processes/prompt-iteration-loop.md](docs/processes/prompt-iteration-loop.md).)

### The optimizer vs. the task model

FAPO has two models, and keeping them straight avoids most confusion:

- **The optimizer** is Claude Code. It reads the playbook, runs evals, dispatches subagents, writes variants, compares results, and decides when to escalate. It never appears in your config.
- **The task model** is whatever you set under `provider` / `provider_settings.model` (e.g. `gpt-4o`, `gemma-3-12b`). It is the model *being optimized*, reached through a small `ProviderClient.generate(messages)` interface.

The two are independent — you can optimize a Gemma pipeline using Claude as the optimizer. Only the task model changes when you swap providers; the optimization machinery stays the same.

### Running it

The optimization loop can be driven by [Claude Code](https://docs.anthropic.com/en/docs/claude-code) or Codex. Use the prompt set that matches the tool you are running: `.claude/` for Claude Code and `.codex/` for Codex.

For Claude Code, use the slash commands from within your project directory:

```
# 1. Run a baseline eval first
> /eval-runner
  → Tenant: my_project
  → Config: tenants/my_project/configs/eval.json

# 2. Start the autonomous optimization loop
> /optimization
  → Tenant: my_project
  → Config: tenants/my_project/configs/eval.json
  → Success criteria: composite_score >= 80
```

For Codex, provide the same tenant, config, and success criteria in the prompt:

```
Run the FAPO eval runner.
Tenant: my_project
Config: tenants/my_project/configs/eval.json
Follow .codex/commands/eval-runner.md.

Then optimize eval quality for tenant "my_project".
Config: tenants/my_project/configs/eval.json
Success criteria: composite_score >= 80
Follow .codex/agents/optimization.md.
```

The `/optimization` agent takes over from there. It will:
1. Read the tenant's `docs/iteration-playbook.md` to understand what it's allowed to change (the **scope contract**)
2. Run failure analysis on the eval results
3. Create new prompt/skill/parameter/chain variants targeting the top failure patterns
4. Validate each variant through an independent guardrail review
5. Run eval on the new variant and compare to the previous best
6. Repeat until success criteria are met or all allowed optimization levels are exhausted

The `/optimization` agent is the orchestrator; it manages two internal subagents automatically — you don't invoke these directly:
- **step-attribution** — classifies failures by root cause after each eval
- **variant-reviewer** — checks proposed variants for leakage, placeholder drift, and scope violations before eval

You can also run evals and optimization steps manually via the CLI (see [CLI reference](#cli-reference) below), but the agent handles the full loop autonomously.

### The optimization levels

| Level | What changes | Example |
|-------|-------------|---------|
| **Prompt** (lowest cost) | Prompt template text only | Add "answer in one word" to reduce verbosity |
| **Skill** (lowest cost) | Agent skill file text only (agentic tenants) | Refine a reusable "how to handle ranking questions" procedure |
| **Parameter** (medium cost) | Config values only | Change `retrieval_k` from 7 to 10, or `temperature` from 1.0 to 0.5 |
| **Structural** (highest cost) | Chain topology / new nodes | Add a self-reflection node, switch from linear to ReAct pattern |

Prompt and **skill** are co-equal *textual* levels — both edit instruction text and carry the same cost. Skills apply only to agentic (tool-using) tenants; see [Skills](#skills) below.

The system follows a **prompt-first policy**: it prefers textual changes (prompt and/or skill) when the evidence is ambiguous, and escalates to parameters or structure only after textual search has exposed a bottleneck that text can't fix. This is the "prefer the smallest useful change" principle — cheaper levels first, and a higher level only when attribution justifies it.

### Step attribution (failure analysis)

After an eval run, step attribution classifies each failure by root cause. It runs in **two phases**: first a fast, deterministic pass of rule-based heuristics over the recorded `step_outputs`, then deeper LLM analysis on the cases the heuristics can't classify confidently. The heuristics cover categories such as:

- **Retrieval failures** — a retrieval step returned empty content, or its output overlaps the query too little (scored as hit / partial / miss)
- **Cascading failures** — an early step produced empty output, causing everything downstream to fail
- **Format failures** — the correct answer is in the output but surrounded by extra text the scorer can't parse
- **Reasoning failures** — all inputs were good but the model reached the wrong conclusion

Each failure is also tagged by which optimization level can address it:
- Format and reasoning failures → **textual** (prompt-addressable, and skill-addressable on agentic tenants)
- Retrieval and cascade failures → **structural-addressable**

This partition tells the optimizer (and you) where to focus before writing new variants — and it is what signals when a level is exhausted and escalation is warranted. The deterministic table appears automatically in each run's `summary.md`.

### Prompt variants

Prompts live at `tenants/<tenant_id>/prompts/modules/<module>/variant-NNN.md`. Each variant is a new file — you never edit in place:

```
prompts/modules/generate_answer/
├── variant-001.md    # Baseline (minimal instructions)
├── variant-002.md    # Added answer brevity rules
└── variant-003.md    # Added must-always-answer constraint
```

To test a new variant, create a config that points to it:

```json
{
  "chain": {
    "config": {
      "prompt_paths": {
        "generate_answer": "tenants/my_project/prompts/modules/generate_answer/variant-002.md"
      }
    }
  }
}
```

Then run eval with that config. Each variant gets its own eval output — no collisions.

### Tracking what you tried

Each tenant tracks optimization history in two places:

**`docs/iteration-memory.jsonl`** — structured, one record per cycle:
```json
{
  "iteration": 1,
  "variant": "variant-002",
  "modules_changed": ["generate_answer", "summarize1"],
  "hypothesis": "Answer brevity rules will improve exact match",
  "train_em": 74.67,
  "val_em": 65.67,
  "delta_val": 26.34,
  "accepted": true
}
```

**`docs/change-log.md`** — human-readable narrative of what changed and why.

Together these prevent rework (you won't re-try something that already failed) and provide an audit trail of how scores improved over time.

### Guardrails

Autonomous optimization can overfit or drift out of scope, so FAPO bounds every loop with four guardrails:

1. **Split access controls** — the optimizer sees individual *training* cases; validation and test expose **aggregate scores only**. Candidates are accepted on validation, never by inspecting test cases.
2. **Scope constraints** — the tenant's `iteration-playbook.md` defines which optimization levels are allowed and which are forbidden. The optimizer and the variant-reviewer enforce this **independently**.
3. **Iteration memory** — a structured log of variants, scores, and exhaustion reasons (see [Tracking what you tried](#tracking-what-you-tried) above).
4. **Variant immutability** — every attempt, accepted or rejected, becomes a new numbered file; structural variants are cloned, never edited in place.

This isolation is a **workspace boundary** — enforced by directory layout, config-local paths, and independent reviewer validation — not an operating-system sandbox.

### Example: optimizing a multi-hop QA chain

Starting from a baseline with 39% exact match on the validation set:

| Iteration | Change | Val EM | Delta |
|-----------|--------|--------|-------|
| Baseline (variant-001) | Minimal DSPy-format prompts | 39.3% | — |
| Iteration 1 (variant-002) | Added task-specific rules: answer brevity, no explanations | 65.7% | +26.4pp |
| Iteration 2 (variant-003) | Added must-always-answer, singular form guidance | 70.3% | +4.6pp |

After iteration 2, failure analysis showed remaining failures were mostly retrieval-limited (the right documents weren't being retrieved) — a structural problem that prompt changes alone can't fix. This is the kind of signal that tells you when to stop iterating at one level and move to the next.

---

## CLI reference

### `eval` — Run an evaluation

```bash
python -m hephaestus.cli eval --config path/to/config.json
```

Runs the chain on every case in the dataset, scores each output, and writes results to `output_dir`.

**Outputs:**
| File | Contents |
|------|----------|
| `summary.md` | Human-readable score summary with breakdowns and step timings |
| `results.jsonl` | Per-case results (input, output, scores, diagnostics) |
| `run_config.json` | Snapshot of the config used for this run |
| `progress.json` | Real-time progress (useful for long-running evals) |

### `eval-progress` — Check a running evaluation

```bash
python -m hephaestus.cli eval-progress --output-dir path/to/output/
python -m hephaestus.cli eval-progress --output-dir path/to/output/ --json
```

Shows run status, progress (completed/total), and current average score.

### `customer-data` — Sync datasets with GCS

```bash
# Pull datasets from GCS
python -m hephaestus.cli customer-data pull --tenant my_project --scope derived

# Push local datasets to GCS
python -m hephaestus.cli customer-data push --tenant my_project --scope derived

# Remove local copies
python -m hephaestus.cli customer-data remove-local --tenant my_project --scope raw --yes
```

Scopes: `raw` (source artifacts), `derived` (processed datasets), `all`.

---

## FAPO UI

FAPO includes a local, read-only web UI called **FAPO Explorer** for browsing tenant artifacts after evals and optimization runs. It shows cross-tenant run summaries, per-case eval outputs, score breakdowns, prompt variants (and agent skills, under the Prompts tab), datasets, iteration history, and tenant docs. It refreshes live as runs progress, supports shareable URLs, sortable/filterable case tables, expected-vs-actual trajectory diffs, JSON syntax highlighting, and Markdown-rendered summaries.

Start it from the repository root:

```bash
python -m hephaestus.cli ui
```

By default, the UI serves `tenants/` at <http://127.0.0.1:8765/>. See [docs/web-ui.md](docs/web-ui.md) for options such as `--tenants-root`, `--host`, and `--port`.

---

## Claude Code skills

FAPO ships as a set of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) agents and commands. The optimization *method* is the three core agents; the rest support evaluation, data augmentation, and repository operations around them.

### Core optimization agents

These three agents are the optimization loop. You invoke `/optimization`; it dispatches the other two automatically.

| Agent | Command | Role |
|-------|---------|------|
| **Optimization** | `/optimization` | Orchestrator. Reads the playbook, emits the scope contract, creates variants, runs evals, records outcomes, and manages level transitions. See [Optimization loop](#optimization-loop). |
| **Step Attribution** | *(dispatched)* | Post-eval failure analysis — classifies failures by root cause and recommends the next optimization level. |
| **Variant Reviewer** | *(dispatched)* | Independent guardrail check on proposed variants (catches leakage, placeholder drift, scope violations). |

### Supporting commands

| Command | What it does |
|---------|-------------|
| `/eval-runner` | Runs a tenant evaluation and returns a score summary plus the output directory. |
| `/synthetic-samples` | Creates realistic synthetic test cases to augment eval datasets with edge cases. |
| `/synthetic-pruner` | Prunes noncompliant synthetic examples and normalizes placeholder data. |
| `/reset-tenant` | Resets a tenant to baseline (variant-001), removing optimization artifacts from the working tree (history is preserved). |

`CLAUDE.md` at the repo root provides repository-wide guidance (project purpose, eval workflow, code style, tenant data-safety rules) that all of the above respect.

### Repository operations

Not part of the optimization method — general repo tooling that happens to ship as Claude Code agents:

| Command | What it does |
|---------|-------------|
| `/pr-lifecycle` | Creates, self-reviews, simplifies, and addresses review comments on a PR until it's merge-ready. |
| `/k8s-manager` | Inspects K8s resources, tracks usage, cleans up stale pods, and launches eval workloads. |

---

## Codex workflows

FAPO also ships Codex prompt files for the same core optimization workflows. These are not Claude Code slash commands; use them only when working in Codex.

### User-invocable workflows

| Workflow | Codex prompt file | How to invoke |
|----------|-------------------|---------------|
| **Optimization** | `.codex/agents/optimization.md` | Ask Codex to optimize eval quality for a tenant and provide the eval config plus success criteria. |
| **Eval Runner** | `.codex/commands/eval-runner.md` | Ask Codex to run an eval for a tenant config and summarize the output directory, score, and failures. |
| **Synthetic Samples** | `.codex/commands/synthetic-samples.md` | Ask Codex to create synthetic examples for a tenant dataset. |
| **Synthetic Pruner** | `.codex/commands/synthetic-pruner.md` | Ask Codex to validate and clean synthetic examples. |
| **Reset Tenant** | `.codex/commands/reset-tenant.md` | Ask Codex to reset generated tenant optimization and eval artifacts. |

### Internal Codex phases

These are used by the Codex optimization workflow — you don't run them directly:

| Phase | Codex prompt file | Purpose |
|-------|-------------------|---------|
| **Step Attribution** | `.codex/agents/step-attribution.md` | Post-eval failure analysis. Classifies failures by root cause and optimization level. |
| **Variant Reviewer** | `.codex/agents/variant-reviewer.md` | Independent guardrail check on proposed variants before eval. |

---

## Project structure

```
hephaestus/
├── src/hephaestus/        # Core engine (provider-agnostic)
│   ├── chains/            #   LangGraph chain infrastructure
│   ├── providers/         #   LLM provider clients (OpenAI, Baseten, SageMaker)
│   ├── scoring/           #   Scorer base class and runtime
│   ├── datasets/          #   JSONL dataset loader
│   ├── engine/            #   Prompt template renderer
│   ├── runs/              #   Eval runner, progress tracker, output writer
│   ├── storage/           #   GCS data sync
│   ├── analysis/          #   Step attribution and failure analysis
│   └── types.py           #   Core dataclasses (EvalCase, EvalConfig, etc.)
├── tenants/               # Tenant-specific implementations
│   └── <tenant_id>/
│       ├── chains/        #   Chain definitions
│       ├── prompts/       #   Prompt templates (with variants)
│       ├── skills/        #   Agent skill files (agentic tenants; optional)
│       ├── datasets/      #   Local dataset cache
│       ├── code/          #   Scorers, data processors, utilities
│       ├── configs/       #   Eval config files
│       └── evals/         #   Eval output directory
├── tests/                 # Automated tests
├── docs/                  # Architecture and usage documentation
└── deploy/                # K8s deployment scripts
```

The key design principle: **everything in `src/hephaestus/` is generic**. Everything tenant-specific lives under `tenants/<tenant_id>/`.

---

## Creating a new tenant

A tenant is a self-contained optimization project. Create the directory structure, then add the same four components shown in [Quick start](#quick-start) (dataset, chain, scorer, config):

```bash
mkdir -p tenants/my_project/{chains,prompts/modules,datasets,code/scorers,configs,evals,docs}
```

Additionally, create an **iteration playbook** at `tenants/my_project/docs/iteration-playbook.md` that defines which optimization levels are allowed (prompt, parameter, structural) and success criteria. The optimization agent reads this to determine its scope. See [docs/tenant-docs-contract.md](docs/tenant-docs-contract.md) for the full list of required tenant docs, and [docs/templates/tenant-docs/](docs/templates/tenant-docs/) for templates.

See `tenants/hotpotqa/` for a complete working example (multi-hop question answering with BM25 retrieval and a multi-node chain).

---

## Eval config reference

Full config schema with all fields (see [docs/config-schema.md](docs/config-schema.md) for the complete specification):

```json
{
  "tenant_id": "my_project",

  "provider": "openai",
  "provider_settings": {
    "model": "gpt-4o",
    "temperature": 0.0,
    "top_p": 0.95,
    "max_tokens": 4096,
    "timeout_seconds": 300,
    "max_retries": 3,
    "retry_backoff_seconds": 5
  },

  "dataset": {
    "path": "tenants/my_project/datasets/eval.jsonl"
  },

  "chain": {
    "path": "tenants/my_project/chains/my_chain.py",
    "fn": "build_chain",
    "config": {
      "prompt_paths": {
        "answer": "tenants/my_project/prompts/answer/variant-001.md"
      }
    }
  },

  "scoring_profile": {
    "scorer": {
      "module_path": "tenants/my_project/code/scorers/my_scorer.py",
      "class_name": "Scorer"
    }
  },

  "output_dir": "tenants/my_project/evals/run-001",
  "max_workers": 4,
  "run_id": "run-001"
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `tenant_id` | yes | Tenant identifier |
| `provider` | yes | `"openai"`, `"baseten"` (alias `"base10"`), or `"sagemaker"` |
| `provider_settings` | no | Model name, temperature, timeouts, retries |
| `dataset.path` | yes | Path to JSONL dataset |
| `chain.path` | yes | Path to chain module |
| `chain.fn` | no | Factory function name (default: `"build_chain"`) |
| `chain.config` | no | Arbitrary config passed to the chain factory |
| `scoring_profile.scorer.module_path` | yes | Path to scorer module |
| `scoring_profile.scorer.class_name` | yes | Scorer class name |
| `output_dir` | yes | Where to write results |
| `max_workers` | no | Parallel threads for concurrent case evaluation (default: sequential). Progress is tracked thread-safely in `progress.json`. |
| `run_id` | no | Custom run ID (auto-generated if omitted) |

---

## Requirements

- Python 3.10+
- Core: `openai`, `langgraph`, `requests`, `datasets`, `pytest`
- Optional extras:
  - `pip install -e ".[hotpotqa]"` — BM25 retrieval dependencies
  - `pip install -e ".[cti_rcm]"` — [FAITH](https://github.com/cisco-foundation-ai/faith) test harness for CTI benchmarks
  - `pip install -e ".[local-models]"` — Local model support (llama-cpp)

---

## Running tests

```bash
# Unit tests (no API keys needed)
python -m pytest

# Integration tests (requires API keys and GCS access)
python -m pytest -m integration
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, commit conventions, and PR guidelines.

---

## Further reading

The companion paper is the canonical reference for the concepts, the GEPA comparison, and benchmark results — see [Citation](#citation) for the full reference and BibTeX entry. The repository docs below cover implementation and contribution details.

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture and evaluation pipeline overview |
| [docs/config-schema.md](docs/config-schema.md) | Full eval config JSON schema reference |
| [docs/tenant-model.md](docs/tenant-model.md) | Tenant directory structure and lifecycle |
| [docs/tenant-docs-contract.md](docs/tenant-docs-contract.md) | Required documentation for each tenant |
| [docs/style-guide.md](docs/style-guide.md) | Coding standards (Python 3.10+, pytest, type hints) |
| [docs/github-hygiene.md](docs/github-hygiene.md) | Commit, branch, and PR conventions |
| [docs/processes/prompt-iteration-loop.md](docs/processes/prompt-iteration-loop.md) | Optimization system architecture reference |
| [docs/processes/chain-variant-conventions.md](docs/processes/chain-variant-conventions.md) | Standards for creating and naming chain variants |
| [docs/prompting-guides/](docs/prompting-guides/) | Prompting best practices, agentic chain patterns, and evaluation benchmarks |

---

## Citation

**FAPO: Fully Automated Prompt Optimization of Multi-Step LLM Pipelines**<br>
Paul Kassianik, Baturay Saglam, Huaibo Zhao, Blaine Nelson, Supriti Vijay, Aman Priyanshu, Amin Karbasi · [arXiv:2606.19605](https://arxiv.org/abs/2606.19605)

If you use FAPO in your research, please cite the paper:

```bibtex
@misc{kassianik2026fapofullyautonomousprompt,
      title={FAPO: Fully Automated Prompt Optimization of Multi-Step LLM Pipelines},
      author={Paul Kassianik and Baturay Saglam and Huaibo Zhao and Blaine Nelson and Supriti Vijay and Aman Priyanshu and Amin Karbasi},
      year={2026},
      eprint={2606.19605},
      archivePrefix={arXiv},
      primaryClass={cs.SE},
      url={https://arxiv.org/abs/2606.19605},
}
```

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2026 Cisco Systems, Inc. and/or its affiliates.
