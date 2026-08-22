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
JSONL contract. Each source must be a regular `.jsonl` file beneath the
selected tenant's `source_artifacts/` or ordinary `datasets/` directory.
Generated `datasets/evaluation_assets/` outputs, other tenants, external
paths, and symlink escapes are rejected. FAPO validates the source contract,
then copies the inputs into a self-contained workspace at:

```text
tenants/<tenant_id>/evaluation_assets/<asset_id>/
├── config.json
├── config_history.jsonl
├── pipeline_state.json
├── events.jsonl
├── recovery_journal.jsonl
├── receipts/
├── lineage.json                 # extended versions only
├── reuse_manifest.json          # extended versions only
├── asset_manifest.json
└── stages/
    ├── 01_raw_inputs/
    ├── 02_prepared_inputs/
    ├── 03_evaluation_guidelines/
    ├── 04_intent_clustering/
    ├── 05_coverage_decisions/
    │   └── review_queue/
    ├── 06_label_inference/
    ├── 07_synthetic_coverage/
    └── 08_dataset_splits/
```

After creation, every stage reads from this workspace rather than the original
files or other tenant resources. Each stage owns only its outputs and reads
inputs from earlier stage folders. The Studio runtime, copied inputs,
checkpoints, events, and stage artifacts in `evaluation_assets/` are local-only;
the Studio has no remote persistence backend for this workspace.

### Eight-stage workflow

| Stage | Purpose |
|---|---|
| 1. Validate raw inputs | Validate the canonical contract and record source counts and hashes. |
| 2. Prepare inputs | Redact sensitive values, apply canonical defaults, and build intent text without renaming fields. |
| 3. Create evaluation guidelines | Extract atomic evidence from feedback, synthesize reusable guidance across compatible examples, and compile criteria with provenance and evaluator plans. |
| 4. Cluster intents | Embed unlabeled intent records and build the requested number of route-aware clusters. |
| 5. Decide coverage | Match clusters to trusted intents and sample representative traces from coverage gaps into a labeling queue. |
| 6. Infer labels | Infer reviewable case rubrics and evaluation cases only for clusters supported by trusted evaluation guidelines. |
| 7. Expand coverage | Optionally generate and filter a configured number of synthetic cases per supported cluster. |
| 8. Build splits | Create group-safe train, validation, and test splits plus an automatic, trusted-only 20% regression gate, then publish those four datasets to the tenant dataset catalog. |

Stage 3 uses one shared producer/verification contract: supported candidate
domains are validated before persistence, compiled guidelines and their trusted
intent/case derivatives are deterministic, and legacy adoption replays the
exact native or historical transformation before accepting existing bytes.
Exact duplicate candidates and duplicate or colliding guideline, criterion,
trusted-intent, and trusted-case identifiers fail before any Stage 3 derivative
or receipt is persisted; live compilation and both adoption profiles apply the
same identity check.

The top-level lifecycle is exactly `draft`, `queued`, `running`,
`awaiting_review`, `released`, or `failed`. Each completed stage has an atomic
receipt commit marker under `receipts/`; `pipeline_state.json` references its
hash, and `events.jsonl` retains the append-only history. Resume verifies the
completed receipt prefix and rebuilds from its first invalid boundary. Missing
or corrupt immutable raw snapshots require repair or a new asset. Presence-only
raw validation is limited to a coherent Stage 1 lifecycle that has never
claimed receipt or completion authority, including safe retry after a failure
or process death before the first receipt. Once a completed-stage status, state
receipt hash, receipt file, or completion event claims Stage 1 authority,
revision and resume require a completed stage, the exact state-bound receipt
hash, and receipt records that authenticate both copied raw files. A released
asset is read-only: verification binds the exact v2 control state, persisted
configuration history, receipt chain, and required artifact hashes while
treating historical code identity as audit evidence. The final stage receipt
also binds the exact configuration-history bytes, whose versioned row schemas,
UTC timestamps, revision operations, and changed-field boundaries are verified.
Any mismatch fails closed, and changes require a child version.

Configuration revisions and checkpoint rebuilds first append a durable
prepared record to `recovery_journal.jsonl`, then make stale stage state
nonauthoritative, and only afterward remove stale files. A later run rolls any
prepared operation forward idempotently before it evaluates the receipt chain.
Recovery authenticates the journal schema, operation and tenant/asset identity,
the complete pre-operation config/state snapshot, exact nested target semantics,
byte-exact before/target prefixes for configuration history and events,
prepare-before-commit order, before/target hashes, and only operation-reachable
intermediate control pairs before writing. Version 2 operations form strict
contiguous prepare/commit pairs with at most one trailing prepare. Consecutive
operations also authenticate writer chronology through mutation identity,
configuration history, and monotonic event prefixes while allowing ordinary
stage events between mutations. A committed legacy adoption is terminal and
must retain its exact target config, state, receipts, and audit prefixes.
When no operation remains outstanding, a final committed configuration revision
or checkpoint rebuild must retain its exact target configuration and complete
target configuration history. Its state and event log may continue through
ordinary pipeline lifecycle and stage progress after the commit.
Standalone candidate and released verification use this same complete journal
validator. Pre-WAL history compatibility comes only from the final validated
adoption transaction whose target hashes match the semantically replayed
receipts, not from receipt origin labels. Version 1 or mixed-version journals
require explicit repair because they lack the complete before-state evidence
needed for safe roll-forward.
One cross-process per-asset hard lock protects create, run/resume, revision,
adoption, and extension mutations across library, CLI, and Studio callers.
`filelock` supplies bounded acquisition and reentrancy over the already
identity-bound handle: POSIX uses `flock`, while Windows uses `LockFileEx`.
Process-global exact-identity ownership distinguishes same-thread recursion
from other threads that share one native handle. Bound handles record their
opening process and fail closed if inherited across `fork`; child work must
reopen the literal path and revalidate its identity.
Missing native hard-lock or atomic-CAS support fails explicitly instead of
selecting a soft lock or check-then-replace fallback.
Every Evaluation Asset Studio authority-root, authority-ancestor, stage,
receipt, publication-catalog, generation, and generation-staging directory
creator also locks the already-open parent and uses the same platform adapter
with private names, no-follow POSIX descriptors or reparse-rejecting Windows
handles, exact identity rechecks, and native no-replace installation. Windows
retains the complete no-share-delete, reparse-checked ancestor handle chain
until the bound directory closes. Darwin and Windows reject
Unicode-normalized case-fold aliases in authority names. A movable Windows
private directory is closed immediately before its exact-identity rename and
the installed name is reopened with stable no-share-delete guards. The
reentrant parent
lock also spans each complete single-file observe/create/CAS/sync/reclaim and
generation collision/stage/install/sync/reclaim transaction. The finite
production guard
rejects other `Path.mkdir`, `os.mkdir`, and `os.makedirs` spellings, including
literal persistence attributes constructed through `operator.attrgetter` or
`operator.methodcaller`; unresolved dynamic attribute names are outside this
finite claim. Its authority adapter audits only named native create, write,
CAS, and exact-owned reclamation functions. The remaining directory-creation
compatibility seams are the generic parent bootstraps in
`_atomic_write_text` and `_atomic_write_binary`, and the deprecated non-Studio
`assemble_dataset_bundle`; a live release check verifies that the latter three
never bootstrap the authority or generation directories listed above.
This boundary fails closed on preexisting or detectably substituted nodes.
POSIX provides neither an atomic `mkdirat`-and-return-descriptor operation nor
handle-conditional `unlink`/`rmdir`; Windows uses an identity-keyed parent mutex
around create/open/install. Exact-owned POSIX reclamation is therefore safe
against cooperating Studio writers that honor the same parent lock, not an
arbitrary noncooperating same-identity namespace swap. The
workspace must not be concurrently mutated by an unaudited process running as
the same OS identity during authority mutation; use an exclusive trusted OS
identity and filesystem permissions for the Studio workspace.
Default providers are constructed only after that lock, recovery, lifecycle
and immutable raw-snapshot checks, revision, and configuration reload. Injected
providers must pass the strict provider/model/settings allowlists and
secret-shaped-value rejection used by persisted provenance. Complete
prospective call rows, stage provenance, and receipts validate in memory before
calls or mutable writes; receipts identify the provider instance and model
actually used instead of substituting configured defaults. Service jobs persist `queued`, then return
acceptance only after separate lock and preflight decisions from the live
worker, without abandoning a lock-owning worker on a fixed timeout. A verified
recovery that itself reaches `released` is accepted as a completed terminal
resume before the worker exits.

After Stage 8 succeeds, the authoritative split artifacts remain inside the
asset workspace and a content-addressed consumer generation is installed at:

```text
tenants/<tenant_id>/datasets/evaluation_assets/<asset_id>/
├── release.json
└── generations/
    └── sha256-<generation-descriptor-hash>/
        ├── generation_manifest.json
        ├── train.jsonl
        ├── validation.jsonl
        ├── test.jsonl
        └── regression_trusted.jsonl
```

The generation descriptor hashes all four files and the deterministic build
fingerprint. A same-filesystem hidden temporary directory is validated and
synced before one native no-replace operation installs the immutable
generation; exact content is reused, while an address collision fails without
overwrite. Exact operation-owned staging, displaced, and quarantine nodes are
reclaimed after success, ordinary Python exceptions, and recoverable retry
paths. Raced foreign nodes and ambiguous durability failures are retained and
fail closed. Hard process termination can therefore leave an unproven hidden
node for explicit inspection; the next process does not scavenge by name.
Immutable final generations are never garbage-collected. `release.json` is
the sole mutable catalog authority and is replaced atomically only after the
generation, Stage 8 receipt, build provenance, manifests, and hashes agree.
Released state and its event follow the pointer under the recovery journal, so
recovery accepts only the reachable pointer/state/event phases and rolls an
interrupted publication forward without rerunning providers. Old generations
are retained; invalidation does not delete them or the release pointer.

`asset_manifest.json` and the Stage 8 manifest expose the current generation
ID, release pointer, hashes, and literal immutable paths. Evaluation configs do
not interpret `release.json`; set `dataset.path` to the exact generation file
path recorded in a manifest. These paths are relative to the explicit
repository/invocation base; CLI and service entry points reject a tenants root
outside that base or traversing an intermediate symlink before writing. These local derived files are not uploaded by the
Studio. A separate `customer-data --scope derived` operation can sync them only
when the tenant storage configuration includes `datasets/` in its configured
`derived_local` tree.

Stages 3–7 persist receipt-backed `provider_calls.jsonl` ledgers, including an
empty ledger when a stage makes no call. `build_provenance.json` aggregates
their body-free request/response hashes and separates deterministic identity
from audit-only timestamps, Git commit/tree and dirt, request IDs, token usage,
and retries. The identity covers the complete declared source inventory,
resolved configuration/defaults, runtime dependencies, copied input hashes,
lineage, provider/model/settings, prompt revisions and hashes, seeds, and
algorithms. Optional transport metadata is strictly allowlisted; custom
providers without the metadata protocol record an explicit unavailable marker.
Full prompts, requests, responses, headers, exceptions, and credentials are
never serialized for provenance.

### Use the Evaluation Asset Studio

Start the shared FAPO UI:

```bash
python -m hephaestus.cli ui --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/evaluation-assets/`. The Studio lets you choose:

- Tenant and asset IDs.
- Canonical labeled and unlabeled JSONL files.
- The evaluation-guideline creation and label-inference model.
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

Released assets also expose **Extend asset**, which creates a new immutable
version from additional canonical data:

- **Keep original clustering** accepts labeled additions only. It reuses the
  parent's Stage 4 inventory from the child's verified self-contained snapshot,
  including after an earlier-stage resume, extracts evidence only for new
  feedback, and rebuilds Stage 3 guidelines across the complete trusted
  evidence pool. It never silently reclusters.
- **Rerun clustering** accepts new unlabeled records, rebuilds Stage 4 over the
  combined traffic, and writes `cluster_lineage.jsonl` to relate previous and
  current clusters.

Both modes recalculate coverage, inferred labels, optional synthesis, and
complete dataset splits in the new version. Parent and child locks are acquired
in deterministic order; the parent receipt and source-lineage evidence must
verify before the child root is created. Stages 3–8 receipt the exact lineage,
reuse, and parent-snapshot inputs they consume, and Stage 8 anchors the lineage
and reuse manifests as required outputs. Producing provider identities come
from verified parent receipts. Both modes retain the guideline identity, and
keep mode also retains the producing embedding identity. Refresh may choose a
complete new embedding provider/model pair; if receipt evidence differs from
stale configuration, omission or a partial pair is rejected instead of
inheriting that configuration. A historically unavailable identity likewise
requires an explicit complete child provider/model selection. The parent asset
is never changed.

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

Extend a verified released version from the CLI:

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

Assets created by an older build may retain the pre-v2 top-level status
`completed`. It is a legacy sentinel, not an alias for `released`. Verify and
adopt it explicitly before extension:

```bash
python -m hephaestus.cli assets adopt \
  --tenant <tenant_id> \
  --asset-id <legacy_asset_id>
```

Adoption accepts only pre-v2 `completed`, validates all eight stages, raw source
hashes, strict finite artifact schemas, deterministic Stage 7 filter outputs,
both manifests, and the current four catalog copies, records unavailable
historical prompt/provider/code facts honestly, materializes an immutable
generation, and publishes it with receipts, pointer, released state, event, and
commit as one terminal `legacy_adoption` operation. The old top-level catalog
copies become nonauthoritative. Failure leaves legacy authority unchanged or
rolls the prepared adoption forward and requires repair or a new asset only
when authenticated evidence is inconsistent. A v2 released checkpoint without
`release.json` is an unpublished interim build: repair it from a verified
backup or rebuild it as a new asset version; adoption is not a migration path.

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

Guideline-model changes restart at Stage 3; embedding or cluster-count changes
at Stage 4; matching changes at Stage 5; synthetic settings at Stage 7; and
split settings at Stage 8. Each revision is prepared in the recovery journal,
then applied to `config.json`, `pipeline_state.json`, `config_history.jsonl`,
and `events.jsonl`; stale downstream outputs are cleaned only after their state
and receipt references are nonauthoritative.

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

By default, the UI serves `tenants/` at <http://127.0.0.1:8765/>. The server
accepts loopback bind hosts only. See [docs/web-ui.md](docs/web-ui.md) for
options such as `--tenants-root`, `--host`, and `--port`.

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
