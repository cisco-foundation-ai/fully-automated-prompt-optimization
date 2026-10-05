<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tau-3 Retail FAFO Data Pipeline Recipe

## Goal

Use sparse manual feedback and a larger set of unlabeled Tau agent episodes to
create case-specific evaluation rubrics, optimize only the agent instruction
prompt, and measure the selected prompt with Tau's native evaluator on a sealed
task-family-disjoint holdout.

This is a recipe, not a prebuilt dataset. It deliberately regenerates traces,
feedback, FAFO assets, and eval outputs locally.

## 1. Create Side-by-Side Environments

Use this layout:

```text
workspace/
├── fafo/
└── tau2-bench/
```

The FAFO and Tau environments stay independent. From the FAFO root:

Install Git and [`uv`](https://docs.astral.sh/uv/) first. Tau `v1.0.1`
requires Python 3.12 or 3.13; `uv sync` selects a compatible interpreter.

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .

python tenants/tau3_retail/scripts/setup_tau_runtime.py
```

The setup command clones Tau, checks out commit
`fc0055dc4e0a316c3f83133267fbd6faaa770992` in detached-HEAD state, installs
from its `uv.lock`, and runs `tau2 check-data`.

If TLS verification fails only because a managed network requires the operating
system certificate store, recreate or clean the Tau checkout and run:

```bash
python tenants/tau3_retail/scripts/setup_tau_runtime.py \
  --use-system-truststore
```

That flag applies the checked-in patch for this exact Tau commit. It adds
`truststore==0.10.4` and injects the OS store before LiteLLM creates clients.
Do not apply it blindly to another Tau revision. The pinned lock resolves
LiteLLM `1.81.11`; verify the lock and package inventory again if you update
Tau or regenerate its lock.

Supply credentials at execution time:

```bash
export OPENAI_API_KEY="<your-key>"
```

Do not write the key into configs, prompts, scripts, result manifests, or Git.
Tau may also load a git-ignored `.env` from its own checkout.

## 2. Freeze the Experimental Controls

The included [`retail-split.json`](../recipe/retail-split.json) assigns all 114
Retail `base` tasks to 73 manually reviewed scenario families. It uses whole
families for a 92-task development partition and a 22-task external final
holdout. Scenario families are experiment metadata, not a native Tau field.

The recorded recipe fixes:

| Control | Value |
|---|---|
| Tau release/commit | `v1.0.1` / `fc0055d...` |
| Domain/task split | `retail` / `base` |
| Development/final holdout | 92 / 22 tasks |
| Trials | 4 per task |
| Base seed | `300` |
| Agent/user simulator | `gpt-4.1-2025-04-14` |
| Temperatures | `0.0` / `0.0` |
| Max concurrency | `3` |
| Optimization scope | prompt only |

Do not change policy, tools, task IDs, simulator, model, temperature, or seeds
between candidate comparisons. Record intentional changes as a new experiment.

## 3. Generate Baseline Development Traces

```bash
python tenants/tau3_retail/scripts/run_tau.py \
  --partition development \
  --num-trials 4 \
  --seed 300 \
  --max-concurrency 3 \
  --save-to fafo_v3_development_4trials
```

This creates 368 episodes under the sibling Tau checkout. Tau owns its policy,
tools, simulator, fresh per-episode database, and native score. Keep the
unaltered result as the protected research source; the FAFO adapter reads only
the model-visible trajectory fields it needs.

Use `--dry-run` to inspect the command without making model calls. A prompt file
can be supplied with `--prompt`; omit it for Tau's baseline instruction.

## 4. Convert Complete Episodes to FAFO Records

```bash
python tenants/tau3_retail/code/export_fafo_traces.py \
  --results ../tau2-bench/data/simulations/fafo_v3_development_4trials/results.json \
  --output tenants/tau3_retail/source_artifacts/all_unlabeled.jsonl
```

Each complete Tau episode becomes exactly one `fafo-evaluation-input-v1`
record. The adapter preserves:

- ordered user and assistant messages;
- ordered tool calls, arguments, results, and errors;
- task, trial, seed, model, termination, and benchmark provenance; and
- the predeclared scenario-family `group_id`.

It explicitly omits native reward, reward components, expected actions,
database assertions, natural-language assertions, hidden task state, and all
other Tau correctness-oracle fields. The exported file contains no feedback.

The full episode is important: FAFO guideline extraction correlates feedback with
assistant behavior, tool calls, tool results, and runtime evidence. Clustering,
however, embeds only the ordered user messages.

## 5. Select Traces Without Looking at Outcomes

The recorded study selected 37 of 368 episodes, approximately 10%:

```bash
python tenants/tau3_retail/code/feedback_workflow.py select \
  --count 37 \
  --seed tau3-fafo-feedback-v1
```

Selection uses only observable episode-shape features: group, task, trial, tool
names, tool-error presence, interaction length, and operation category. It does
not use Tau reward, assertions, expected actions, or the content of tool
results. It reserves operation/shape coverage, balances trials, and prefers
distinct tasks and groups.

The generated selection and manifest stay under `source_artifacts/` and are
not published.

## 6. Add Manual Trusted Feedback

Render conversation-only review files:

```bash
python tenants/tau3_retail/code/feedback_workflow.py render
```

For each file in `source_artifacts/feedback-review/`, fill in:

```text
**Polarity** (`positive`, `negative`, or `mixed`): mixed
**Rationale**: The agent correctly identified the order but claimed success before a tool result confirmed it.
**Correction** (optional): Report the tool error and explain the unresolved action.
**Reviewed as trusted** (`yes` or `no`): yes
```

Write feedback from the user's perspective in natural language. Cover both good
behavior and mistakes when the episode is mixed. Judge the whole interaction,
including whether the final statement is supported by tool outcomes, but do not
show annotators hidden native rewards, expected actions, or FAFO guidelines.

The final `yes` is an explicit trust decision. Do not classify generated or
unreviewed rationales as manual trusted feedback.

Join the completed feedback while keeping the outputs disjoint:

```bash
python tenants/tau3_retail/code/feedback_workflow.py join
```

The command writes `labeled_feedback.jsonl` and `unlabeled_traffic.jsonl` under
`source_artifacts/`, validates both against the FAFO contract, and rejects
missing trust decisions, missing rationales, altered selected records, overlap,
and protected native scoring fields.

## 7. Run the FAFO Data Pipeline

```bash
python -m hephaestus.cli assets create \
  --tenant tau3_retail \
  --asset-id fafo-v3-luna-v1 \
  --feedback tenants/tau3_retail/source_artifacts/labeled_feedback.jsonl \
  --unlabeled tenants/tau3_retail/source_artifacts/unlabeled_traffic.jsonl \
  --rubric-model gpt-5.6-luna \
  --embedding-model text-embedding-3-small \
  --clusters 50 \
  --match-threshold 0.65

python -m hephaestus.cli assets run \
  --tenant tau3_retail \
  --asset-id fafo-v3-luna-v1 \
  --rubric-model gpt-5.6-luna \
  --embedding-model text-embedding-3-small \
  --clusters 50 \
  --batch-size 3 \
  --match-threshold 0.65 \
  --min-trusted-examples 1 \
  --min-trusted-groups 1 \
  --max-unlabeled-to-trusted-ratio 20 \
  --no-synthetic-coverage \
  --split-seed 42
```

The FAFO data pipeline performs these relevant operations:

1. Validate, redact, and split trusted connected groups before authoring.
2. Correlate eligible training feedback with full trace/tool evidence.
3. Consolidate supported mistake and success patterns into reusable guidelines.
4. Cluster all-user-message intent text as sampling metadata only.
5. Make one full-catalog rubric-generation call per episode. The model selects
   zero, one, or many applicable guidelines; with none, it writes a
   `trace_inferred` rubric from explicit trace evidence and available constraints.
6. Fingerprint cases and dependencies, automatically approve scoreable inferred
   cases, hold conflicts or protected-regression derivatives, and pause.

The recorded run disabled synthetic coverage. Keep it disabled for direct
replication. Its other explicit controls were batch size 3, match threshold
0.65, split seed 42, minimum one trusted example and group, and a maximum
unlabeled-to-trusted ratio of 20.

Inspect the review snapshot:

```bash
python -m hephaestus.cli assets reviews list \
  --tenant tau3_retail \
  --asset-id fafo-v3-luna-v1
```

Sample guidelines and both rubric provenances, inspect all holds, and retain the
returned fingerprints. Then publish exactly that snapshot:

```bash
python -m hephaestus.cli assets reviews finalize \
  --tenant tau3_retail \
  --asset-id fafo-v3-luna-v1 \
  --reviewer <reviewer_name> \
  --review-set <sha256:review_set_fingerprint> \
  --decision-set <sha256:decision_set_fingerprint>
```

## 8. Run FAFO-Guided Evaluation

The evaluation chain starts one fresh Tau environment for every FAFO case. The
case context supplies only task ID and seed; Tau supplies policy, tools, user
simulator, and fresh database. The scorer gives the resulting episode and its
case-specific FAFO rubric to the fixed judge and aggregates criterion statuses
deterministically.

Example views are under `recipe/configs/`:

| Config | Dataset view | Purpose |
|---|---|---|
| `trusted-train.json` | `train_trusted.jsonl` | Trusted-only optimization |
| `inferred-train.json` | `train_inferred.jsonl` | First stage of staged optimization |
| `mixed-train.json` | `train.jsonl` | Joint trusted + inferred optimization |
| `validation.json` | `validation.jsonl` | Prompt selection |
| `test.json` | `test.jsonl` | Final in-asset evaluation |
| `regression.json` | `regression_trusted.jsonl` | Trusted regression gate |

Run one evaluation:

```bash
.venv/bin/python scripts/eval/run_eval_and_summarize.py \
  --config tenants/tau3_retail/recipe/configs/mixed-train.json
```

The root `configs/train.json`, `configs/eval.json`, and `configs/test.json`
provide conventional entry points. Copy a recipe config to a new file and
change only `prompt_paths.agent`, `run_id`, and `output_dir` when evaluating a
new prompt against the same split.

## 9. Optimize the Prompt

The recorded experiment used three arms:

- Trusted only: run each candidate on all 20 trusted training cases until
  plateau; select with trusted validation.
- Mixed: run each candidate on the full 236-case train set, containing 20
  trusted and 216 approved inferred cases, until plateau.
- Staged: optimize on all 216 inferred cases, then start from that winner and
  optimize on all 20 trusted cases until plateau.

Follow [`iteration-playbook.md`](iteration-playbook.md). One training agent
inference means one fresh Tau episode for one case under one candidate prompt.
Judge retries over an already preserved episode do not count as another agent
inference; episode retries do.

The exact generated prompts and their rejected branches are retained under
`prompts/v3/`. Never use validation, test, regression, or external native
holdout case details to author prompt text.

## 10. Run the Native Tau Holdout

After selecting and freezing a prompt, use Tau's own evaluator on the untouched
22-task final holdout:

```bash
python tenants/tau3_retail/scripts/run_tau.py \
  --partition final_holdout \
  --num-trials 4 \
  --seed 300 \
  --prompt tenants/tau3_retail/prompts/v3/mixed/m004.txt \
  --save-to fafo_v3_mixed_m004_final_holdout
```

Run the unchanged baseline on the identical task/seed matrix. Report Tau native
passes, `pass^1` through `pass^4`, database match, action diagnostics, and
natural-language assertions. Keep task-level held-out conversations and
failures sealed after the run; do not use them to revise the selected prompt.

The recorded one-matrix result improved from 63/88 baseline passes to 71/88 for
trusted-only T008, 73/88 for mixed M004, and 71/88 for staged T001. These are
promising descriptive results, not a statistically conclusive replication.

## 11. What to Commit

Commit code, configs, split metadata, prompt text, aggregate experiment reports,
iteration memory, and changelog. Never commit:

- Tau runtime or native task data;
- raw or converted episodes;
- annotation review files or feedback;
- FAFO evaluation-asset workspaces or published dataset payloads;
- FAFO/Tau eval output directories; or
- `.env` files, API keys, or provider request logs.
