<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Headless Optimization

`python -m hephaestus.cli optimize` runs the prompt- and parameter-level
optimization loop with nothing but provider credentials. A plain-code
coordinator runs the loop, and each judgment step is one JSON call to an LLM
role. No Claude Code or Codex session is involved.

The scope is deliberately narrower than the
[agent loop](prompt-iteration-loop.md): only **prompt text** and **declared
parameters** change. Chain-structure variants, skills, web research, and
synthetic-data generation remain agent-only.

## Loop

```text
baseline: eval train (+ val); the pool starts with the baseline
repeat until a stop condition:
  1. parent      sample a pool member by the train cases it does best on (or take the best)
  2. attribute   rule-based step attribution over the parent's train results
  3. plan        analyst role: study the training overview, cluster train failures, and pick
                 up to `search.candidates` distinct changes (level, module, scope, technique)
  4. propose     prompt proposer writes one module per prompt plan | parameter plans set knobs
  5. review      static checks (code) + reviewer role; one revision, then reject
  6. merge       optionally add the combination of two pool members that changed different
                 settings since their common ancestor (no model call)
  7. screen      eval every candidate on train; reject if train delta < min_train_delta
  8. select      eval the best-screened candidate on val (val_repeats times); accept when the
                 paired test against its parent passes, or by train tie-break
  9. record      append to ledger.jsonl; an accepted candidate joins the pool
after the loop: re-evaluate the top pool members on val and keep the best fresh score
optional: eval baseline and the chosen best once on test
```

### Acceptance

A candidate is compared with its parent case by case on the same val cases. The
coordinator computes the mean gain and a paired bootstrap probability that it is real:
the share of resamples of the cases whose mean gain is strictly positive. Each case's gain
includes the sampling noise of both runs; `val_repeats` averages it down. A candidate is
accepted when the gain is positive, at least `min_val_delta`, and the probability is at
least `acceptance.confidence`. A single improved case among many stays below 0.8, so one
lucky flip is not enough. With `train_tiebreak`, a candidate whose val score does not drop
is also accepted when its train gain passes the same probability test. Without a val
split, the test runs on train.

On 300 val cases with 20% flaky cases, a simulation gave these acceptance rates:

| Rule | No real change | +3 points | +5 points |
|---|---|---|---|
| Accept any positive gain (previous behavior) | 48% | 93% | 100% |
| `confidence` 0.8 (default) | 17% | 67% | 93% |
| `confidence` 0.9 | 9% | 45% | 83% |

### Pool, parents, and merges

Accepted candidates form a pool. Each iteration's parent is sampled from the pool with
weight equal to the number of train cases where that member reaches the top score
(GEPA-style Pareto selection), so members that solve different cases keep being explored.
`search.parent_selection: "best"` always branches from the current best.

When two pool members changed different prompt modules or parameters since their common
ancestor, the coordinator also screens their combination. This finds gains that need two
modules to change together, which one-module plans cannot reach. All candidates run on the
same train cases, so the best-screened candidate is the one with the highest train score,
whatever it branched from.

### Final selection

A single best score is biased upward, because it was chosen as the maximum of many noisy
scores. When the loop stops, the top `selection.finalists` pool members are re-evaluated on
val (train without a val split) `selection.repeats` times, and the best fresh score is the
final pick. A resumed run reuses an earlier selection only when its finalists are still
the top pool members.

The loop stops when any of these holds:

- `budget.max_iterations` is reached.
- `budget.target_score` is reached on the selection split.
- Every allowed level has `budget.plateau_patience` consecutive rejections
  since the last acceptance.
- No failing training cases remain.

## Roles

| Role | Input | Output |
|------|-------|--------|
| Analyst | the parent's prompts, the training overview, sampled failing **train** cases with metadata, attribution summary, run history with per-case flips for every screened candidate, techniques tried since the last improvement, tenant guidance, scorer source | failure clusters and up to `max_plans` distinct plans |
| Prompt proposer | one module's prompt body, its placeholders, the plan, the analyst's clusters, the targeted train cases, the training overview, tenant guidance, scorer source | full new prompt body |
| Reviewer | previous and proposed prompt, plan scope and hypothesis, the targeted train cases | verdict and issues |

The **training overview** lists every training case (inputs, expected output,
metadata, and whether the parent passes it) when the train split has at
most `train_overview_limit` cases. It lets the roles induce the structure of
the task, such as which kinds of inputs map to each output, instead of
patching individual failures.

A **rewrite** plan restructures the whole prompt from that overview; an
**edit** plan makes one focused change.

Each history entry records which training cases the attempt fixed and broke,
so stateless role calls can learn from rejected attempts.

Code validates every role response. An invalid response is retried once with
the validation errors attached; a second failure records the iteration as
`role_error`. Parameter plans are validated against the policy's parameter
space before they can be evaluated.

## Policy

The policy is the machine-readable counterpart of the tenant playbook's scope
section. A human translates the playbook into a policy; the coordinator
enforces only what the policy says.

```json
{
  "base_config": "tenants/<tenant_id>/configs/<config>.json",
  "datasets": {
    "train": "tenants/<tenant_id>/datasets/train.jsonl",
    "val": "tenants/<tenant_id>/datasets/val.jsonl",
    "test": "tenants/<tenant_id>/datasets/test.jsonl"
  },
  "levels": ["prompt", "parameter"],
  "prompt_modules": ["answer"],
  "parameter_space": {
    "provider_settings.temperature": {"type": "float", "min": 0.0, "max": 1.0},
    "chain.config.retrieval_k": {"type": "int", "min": 3, "max": 20}
  },
  "acceptance": {"min_train_delta": 0.0, "min_val_delta": 0.0, "confidence": 0.8,
                 "val_repeats": 1, "train_tiebreak": true},
  "search": {"candidates": 3, "parent_selection": "pareto", "merge": true},
  "selection": {"finalists": 3, "repeats": 1},
  "budget": {"max_iterations": 10, "plateau_patience": 3, "target_score": null},
  "roles": {"model": "<openai-model>", "llm_review": true},
  "guidance_paths": ["tenants/<tenant_id>/docs/iteration-playbook.md"],
  "failure_threshold": 100.0,
  "max_failures_shown": 20,
  "train_overview_limit": 200
}
```

| Field | Notes |
|---|---|
| `levels` | Any of `prompt` and `parameter`. `parameter` requires a `parameter_space`. |
| `prompt_modules` | Optional allowlist of `chain.config.prompt_paths` keys. Defaults to every module. |
| `parameter_space` | Dotted paths into the eval config, each with an `int`, `float`, `choice`, or `bool` spec. Allowed paths are `provider_settings.<key>` for `model`, `temperature`, `top_p`, and `max_tokens`, and top-level `chain.config.<key>` keys other than `prompt_paths`, `skill_paths`, and `optimization_target`. |
| `datasets.val` | Strongly recommended. Without it, selection falls back to the train split and `train_tiebreak` does not apply. |
| `acceptance.confidence` | Minimum paired bootstrap probability that a candidate's gain over its parent is real. Default 0.8. |
| `acceptance.min_val_delta` | Optional minimum mean val gain, in score points. Default 0. |
| `acceptance.train_tiebreak` | Accept a candidate whose val score does not drop when its train gain passes the confidence test. Small val splits tie often; without this, real train gains are discarded. |
| `search.candidates` | Plans the analyst proposes per iteration, each screened on train. Default 3. Train eval cost scales with it; val cost does not. |
| `search.parent_selection` | `"pareto"` (default) samples parents from the pool; `"best"` always uses the current best. |
| `search.merge` | Also screen combinations of pool members with disjoint changes. Default true. |
| `selection.finalists`, `selection.repeats` | Pool members re-evaluated after the loop, and val runs each. `finalists: 1` skips re-evaluation. |
| `train_overview_limit` | Show the full training overview when the train split has at most this many cases (`0` disables it). Larger splits get only the `max_failures_shown` sampled failing cases. |
| `roles.model` | Defaults to the same OpenAI model the evaluation-asset pipeline uses. |

## Running

```bash
python -m hephaestus.cli optimize --policy tenants/<tenant_id>/configs/<policy>.json
python -m hephaestus.cli optimize --policy <policy>.json --resume           # continue after interruption
python -m hephaestus.cli optimize --policy <policy>.json --resume --final-test
```

`--workspace` defaults to `tenants/<tenant_id>/evals/optimize/<policy-name>/`,
which is git-ignored. `--max-iterations` and `--role-model` override the
policy. The command prints a JSON summary when the loop stops.

## Outputs

| Path | Content |
|------|---------|
| `<workspace>/ledger.jsonl` | One record per baseline, iteration, final selection, and stop. An iteration record holds the selected candidate (plan, clusters, review issues, train/val scores and deltas, `p_improve`, decision reason, config, per-role token usage) and its `alternatives`: every other candidate tried that iteration, with the reason it was not selected (for example `not_selected`, `train_screen`, `review_failed`, or `duplicate_config`) |
| `<workspace>/configs/` | The exact eval config used for every eval run |
| `<workspace>/evals/<candidate>-<split>/` | Standard eval run bundles |
| `<workspace>/best-config.json` | Runnable eval config for the best candidate |
| `prompts/.../variant-NNN.md` | New prompt variants, written next to their parent with the next free number and the parent's license header |

Selection scores count failed executions as 0, so a candidate cannot gain by
causing infrastructure failures. Run summaries still report successful-only
averages.

## Enforcement

In the agent loop these controls are agent-enforced. Here the coordinator
enforces them in code, within the limits of the policy:

- **Training-only authoring:** role payloads contain per-case data from the
  train split only. Val and test reach roles as aggregate scores only. Per-case
  val scores are used in code for the paired test and never enter a payload or
  the ledger.
- **Validation-only selection:** candidates are accepted, and the final pick is
  made, on the val split.
- **Single test evaluation:** test runs only with `--final-test`, after
  optimization stops. A workspace with a test result cannot be resumed.
- **Scope:** only declared levels, modules, and parameter bounds can change.
- **Clone-new-variant:** prompts are written to new files with exclusive
  creation; existing variants are never edited.
- **Held-out naming check:** a strong role model can name val or test inputs
  from its own knowledge (for example, the best-known product of a kind), which
  inflates held-out scores without any data access. The static review blocks
  prompts that name a val or test input, with a message that does not reveal
  which input matched.
- **Mechanical review checks:** placeholder integrity, `System:`/`User:`
  section markers, training case-ID references, short training inputs (such as
  a product or entity name) named verbatim, and 8-word spans copied from
  training cases block a variant before any eval.

Not enforced:

- The reviewer role's semantic checks (example-specific hints, paraphrased
  leakage) are model judgment.
- Anyone with access can edit policy files and the checkout itself. This is
  not an operating-system sandbox.
