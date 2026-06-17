<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Fully Autonomous Prompt Optimization (FAPO)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![CI](https://github.com/cisco-foundation-ai/fully-automated-prompt-optimization/actions/workflows/ci.yml/badge.svg)](https://github.com/cisco-foundation-ai/fully-automated-prompt-optimization/actions/workflows/ci.yml)

An optimization framework for LLM-powered chains. Iteratively improve prompts, parameters, and chain architecture using built-in evaluation, failure analysis, and a structured variant system.

FAPO provides the full loop: **evaluate** a chain against a dataset, **analyze** what went wrong using step attribution, **create** a better variant, and **measure** whether it improved. The evaluation infrastructure exists to drive and measure optimization — not as an end in itself.

## Quick start

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### 2. Set up a tenant

A tenant is a self-contained optimization project. You need four things: a dataset, a chain, a scorer, and a config that wires them together.

**Dataset** — a JSONL file with test cases (`my_dataset.jsonl`):
```json
{"case_id": "1", "task_type": "qa", "context": {"question": "What is the capital of France?"}, "expected": {"answer": "Paris"}, "metadata": {}}
{"case_id": "2", "task_type": "qa", "context": {"question": "What is 2 + 2?"}, "expected": {"answer": "4"}, "metadata": {}}
```

**Chain** — a LangGraph pipeline that processes each case (`my_chain.py`):
```python
from langgraph.graph import StateGraph, END
from hephaestus.chains.types import ChainState
from hephaestus.chains.nodes import make_llm_node

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
from hephaestus.scoring.scorer import Scorer as BaseScorer

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
export OPENAI_API_KEY="sk-..."
python -m hephaestus.cli eval --config eval.json
cat eval_output/summary.md
```

### 4. Optimize

Open [Claude Code](https://docs.anthropic.com/en/docs/claude-code) in your project directory and run the optimization agent:

```
> /optimization
  → Tenant: my_project
  → Config: eval.json
  → Success criteria: composite_score >= 90
```

The agent autonomously analyzes failures, creates improved prompt variants, evaluates them, and iterates until your target score is reached. See [Optimization loop](#optimization-loop) for the full details.

---

## How it works

The core workflow is an **optimization loop** — evaluate, analyze failures, create a better variant, repeat:

```
  ┌───────────────────────────────────────────────────────────────┐
  │                       OPTIMIZATION LOOP                       │
  │                                                               │
  │  Dataset ──> Chain ──> Scorer ──> Results                     │
  │  (JSONL)     (LangGraph)          (summary.md, results.jsonl) │
  │                                       │                       │
  │                                       ▼                       │
  │                               Step attribution                │
  │                         (classify failure causes)             │
  │                                       │                       │
  │                                       ▼                       │
  │                            Create new variant                 │
  │                     (prompt / parameter / chain)              │
  │                                       │                       │
  │                                       ▼                       │
  │           ┌── Accept ◄── Compare to previous best             │
  │           │                      │                            │
  │           ▼                 Reject ──┐                        │
  │      Update best                     │                        │
  │           │                          │                        │
  │           └───────────► Next cycle ◄─┘                        │
  └───────────────────────────────────────────────────────────────┘
```

You wire them together with a **config file** and run `python -m hephaestus.cli eval --config <config>.json`. Once you have results, use failure analysis and the variant system to iterate.

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

### Scorers

A scorer compares the chain output to the expected answer. Implement the `Scorer` base class:

```python
# my_scorer.py
from hephaestus.scoring.scorer import Scorer as BaseScorer

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

The engine calls `validate_case` (to catch bad data early) then `score_case` for each test case, and aggregates the results.

For multi-step chains, you can also implement `score_pipeline_case` to score based on intermediate step outputs, not just the final output.

### Providers

FAPO supports three LLM providers out of the box:

| Provider | Config value | Auth env variable | Notes |
|----------|-------------|-------------------|-------|
| **OpenAI** | `"openai"` | `OPENAI_API_KEY` | GPT-4o, GPT-4.1, o1/o3 reasoning models |
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

Evaluation tells you *how well* your chain performs. Optimization tells you *what to change* to make it better. FAPO includes a structured optimization loop that works at three levels of increasing cost. (For the full architecture, see [docs/processes/prompt-iteration-loop.md](docs/processes/prompt-iteration-loop.md).)

### Running it

The optimization loop is driven by [Claude Code](https://docs.anthropic.com/en/docs/claude-code) agents. From within your project directory:

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

The `/optimization` agent takes over from there. It will:
1. Read the tenant's `docs/iteration-playbook.md` to understand what it's allowed to change (the **scope contract**)
2. Run failure analysis on the eval results
3. Create new prompt/parameter/chain variants targeting the top failure patterns
4. Validate each variant through an independent guardrail review
5. Run eval on the new variant and compare to the previous best
6. Repeat until success criteria are met or all allowed optimization levels are exhausted

The agent manages three internal subagents automatically — you don't invoke these directly:
- **step-attribution** — classifies failures by root cause after each eval
- **variant-reviewer** — checks proposed variants for leakage, placeholder drift, and scope violations before eval

You can also run evals and optimization steps manually via the CLI (see [CLI reference](#cli-reference) below), but the agent handles the full loop autonomously.

### The three optimization levels

| Level | What changes | Example |
|-------|-------------|---------|
| **Prompt** (lowest cost) | Prompt template text only | Add "answer in one word" to reduce verbosity |
| **Parameter** (medium cost) | Config values only | Change `retrieval_k` from 7 to 10, or `temperature` from 1.0 to 0.5 |
| **Structural** (highest cost) | Chain topology / new nodes | Add a self-reflection node, switch from linear to ReAct pattern |

The system works through these levels in order. When performance plateaus at one level, it escalates to the next.

### Step attribution (failure analysis)

After an eval run, step attribution automatically classifies each failure by root cause:

- **Retrieval failures** — the retrieval step returned empty or irrelevant content
- **Cascading failures** — an early step produced empty output, causing everything downstream to fail
- **Format failures** — the correct answer is in the output but surrounded by extra text the scorer can't parse
- **Reasoning failures** — all inputs were good but the model reached the wrong conclusion

Each failure is also tagged by which optimization level can address it:
- Format and reasoning failures → **prompt-addressable**
- Retrieval and cascade failures → **structural-addressable**

This tells you where to focus effort before you start writing new variants.

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

## Claude Code skills

FAPO ships with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills that automate common workflows. Run these as slash commands inside Claude Code:

### User-invocable skills

| Skill | Command | What it does |
|-------|---------|-------------|
| **Optimization** | `/optimization` | Autonomous optimization loop — analyzes failures, creates variants, runs evals, iterates until target score is reached. See [Optimization loop](#optimization-loop). |
| **Eval Runner** | `/eval-runner` | Runs a tenant evaluation and returns a score summary. |
| **Synthetic Samples** | `/synthetic-samples` | Creates realistic synthetic test cases to augment eval datasets with edge cases. |
| **Synthetic Pruner** | `/synthetic-pruner` | Prunes noncompliant synthetic examples and normalizes placeholder data. |
| **Reset Tenant** | `/reset-tenant` | Resets a tenant to baseline (variant-001), removing all optimization artifacts. |
| **PR Lifecycle** | `/pr-lifecycle` | Creates, self-reviews, simplifies, and addresses review comments on a PR until it's merge-ready. |
| **K8s Manager** | `/k8s-manager` | Inspects K8s resources, tracks usage, cleans up stale pods, and launches eval workloads. |

### Internal subagents

These are invoked automatically by the optimization agent — you don't run them directly:

| Subagent | Purpose |
|----------|---------|
| **Step Attribution** | Post-eval failure analysis. Classifies failures by root cause and optimization level. |
| **Variant Reviewer** | Independent guardrail check on proposed variants (catches leakage, placeholder drift, scope violations). |

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
| `provider` | yes | `"openai"`, `"baseten"`, or `"sagemaker"` |
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

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

Copyright 2025 Cisco Systems, Inc. and/or its affiliates.
