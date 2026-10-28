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

The loop stops when any of these holds:

- `budget.max_iterations` is reached.
- `budget.target_score` is reached on the selection split.
- Every allowed level has `budget.plateau_patience` consecutive rejections
  since the last acceptance.
- No failing training cases remain.

## Roles

| Role | Input | Output |
|------|-------|--------|
| Analyst | current best prompts, the training overview, sampled failing **train** cases with metadata, attribution summary, run history with per-case flips, techniques tried since the last improvement, tenant guidance, scorer source | failure clusters and one plan |
| Prompt proposer | one module's prompt body, its placeholders, the plan, the analyst's clusters, the targeted train cases, the training overview, tenant guidance, scorer source | full new prompt body |
| Reviewer | previous and proposed prompt, plan scope and hypothesis, the targeted train cases | verdict and issues |

The **training overview** lists every training case (inputs, expected output,
metadata, and whether the current best passes it) when the train split has at
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
  "acceptance": {"min_train_delta": 0.0, "min_val_delta": 1.0, "val_repeats": 1, "train_tiebreak": true},
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
| `acceptance.train_tiebreak` | Accept a candidate whose val gain is below `min_val_delta` but not negative when its train score strictly improves. Small val splits tie often; without this, real train gains are discarded. |
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
| `<workspace>/ledger.jsonl` | One record per baseline, iteration, and stop: plan, clusters, review issues, train/val scores and deltas, decision reason, candidate config, and per-role token usage |
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
  train split only. Val and test contribute aggregate scores only.
- **Validation-only selection:** candidates are accepted on the val split.
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
