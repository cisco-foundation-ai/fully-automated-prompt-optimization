<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Headless Optimization

## Purpose

`python -m hephaestus.cli optimize` runs the prompt- and parameter-level
optimization loop with nothing but provider credentials. No Claude Code or
Codex session is involved: a plain-code coordinator runs the loop, and each
judgment step is one JSON call to an LLM role.

Scope is deliberately narrower than the agent loop in
[`prompt-iteration-loop.md`](prompt-iteration-loop.md): only **prompt text**
and **declared parameters** change. Chain-structure variants, skills, web
research, and synthetic-data generation remain agent-only.

## Loop

```
baseline: eval train (+ val)
repeat until a stop condition:
  1. attribute   rule-based step attribution over the current best's train results
  2. plan        analyst role: study the training overview, cluster train failures, pick ONE
                 change (level, module, scope "edit" or "rewrite", technique)
  3. propose     prompt proposer writes one module   |   parameter plan sets declared knobs
  4. review      static checks (code) + reviewer role; one revision, then reject
  5. screen      eval train; reject if train delta < min_train_delta
  6. select      eval val (val_repeats times); accept if val delta > 0 and >= min_val_delta,
                 or (train_tiebreak) if val does not drop and train strictly improves
  7. record      append to ledger.jsonl; accepted candidate becomes the new best
optional: eval baseline and best once on test
```

Stop conditions: `budget.max_iterations` reached, `budget.target_score`
reached on the selection split, every allowed level has
`budget.plateau_patience` consecutive rejections since the last acceptance, or
no failing training cases remain.

| Role | Input | Output |
|------|-------|--------|
| Analyst | current best prompts, the training overview, sampled failing **train** cases with metadata, attribution summary, run history with per-case flips, techniques tried since the last improvement, tenant guidance, scorer source | failure clusters and one plan |
| Prompt proposer | one module's prompt body, its placeholders, the plan, the analyst's clusters, the targeted train cases, the training overview | full new prompt body |
| Reviewer | previous and proposed prompt, plan scope and hypothesis, the targeted train cases | verdict and issues |

The **training overview** lists every training case (inputs, expected output,
metadata, and whether the current best passes it) when the train split has at
most `train_overview_limit` cases. It lets the roles induce the structure of the
task, for example which kinds of inputs map to each output, instead of patching
individual failures. A **rewrite** plan restructures the whole prompt from that
overview; an **edit** plan makes one focused change. Each history entry records
which training cases the attempt fixed and broke, so stateless role calls can
learn from rejected attempts.

Every role response is validated in code. An invalid response is retried once
with the validation errors attached; a second failure records the iteration as
`role_error`. Parameter plans are validated against the policy's parameter
space before they can be evaluated.

## Policy

The policy is the machine-readable counterpart of the tenant playbook's scope
section. Translating the playbook into a policy is a human step; the
coordinator enforces only what the policy says.

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
  "acceptance": {"min_train_delta": 0.0, "min_val_delta": 1.0, "val_repeats": 1, "train_tiebreak": true},
  "budget": {"max_iterations": 10, "plateau_patience": 3, "target_score": null},
  "roles": {"model": "<openai-model>", "llm_review": true},
  "guidance_paths": ["tenants/<tenant_id>/docs/iteration-playbook.md"],
  "failure_threshold": 100.0,
  "max_failures_shown": 20,
  "train_overview_limit": 200
}
```

- `levels`: any of `prompt` and `parameter`. `parameter` requires a
  `parameter_space`.
- `prompt_modules`: optional allowlist of `chain.config.prompt_paths` keys;
  defaults to every module.
- `parameter_space`: dotted paths into the eval config with `int`, `float`,
  `choice`, or `bool` specs. Allowed paths are `provider_settings.model`,
  `temperature`, `top_p`, `max_tokens`, and top-level `chain.config.<key>` keys
  other than `prompt_paths`, `skill_paths`, and `optimization_target`.
- `datasets.val`: strongly recommended. Without it, selection falls back to the
  train split and `train_tiebreak` does not apply.
- `acceptance.train_tiebreak`: accept a candidate whose val gain is below
  `min_val_delta` but not negative when its train score strictly improves.
  Small val splits tie often; without this, real train gains are discarded.
- `train_overview_limit`: show the full training overview when the train split
  has at most this many cases (`0` disables it). Larger splits get only the
  `max_failures_shown` sampled failing cases.
- `roles.model`: defaults to the same OpenAI model the evaluation-asset
  pipeline uses.

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
| `<workspace>/ledger.jsonl` | One record per baseline, iteration, and stop: plan, clusters, review issues, train/val scores and deltas, decision reason, candidate config, and per-role token usage |
| `<workspace>/configs/` | The exact eval config used for every eval run |
| `<workspace>/evals/<candidate>-<split>/` | Standard eval run bundles |
| `<workspace>/best-config.json` | Runnable eval config for the best candidate |
| `prompts/.../variant-NNN.md` | New prompt variants, written next to their parent with the next free number and the parent's license header |

Selection scores count failed executions as 0, so a candidate cannot gain by
causing infrastructure failures. Run summaries keep reporting successful-only
averages.

## Enforcement in this mode

These controls are agent-enforced in the agent loop. Here the coordinator
enforces them in code, within the limits of the policy:

- **Training-only authoring**: role payloads contain per-case data from the
  train split only. Val and test contribute aggregate scores only.
- **Validation-only selection**: candidates are accepted on the val split.
- **Single test evaluation**: test runs only with `--final-test`, after
  optimization stops. A workspace with a test result cannot be resumed.
- **Scope**: only declared levels, modules, and parameter bounds can change.
- **Clone-new-variant**: prompts are written to new files with exclusive
  creation, and existing variants are never edited.
- **Held-out naming check**: a strong role model can name val or test inputs
  from its own knowledge, for example the best-known product of a kind, which
  inflates held-out scores without any data access. The static review blocks
  prompts that name a val or test input, with a message that does not reveal
  which input matched.
- **Mechanical review checks**: placeholder integrity, `System:`/`User:`
  section markers, training case-ID references, short training inputs (such as
  a product or entity name) named verbatim, and 8-word spans copied from
  training cases block a variant before any eval.

These are not enforced:
- The reviewer role's semantic checks (example-specific hints, paraphrased
  leakage) are model judgment.
- Policy files and the checkout itself can be edited by anyone with access.
  This is not an operating-system sandbox.
