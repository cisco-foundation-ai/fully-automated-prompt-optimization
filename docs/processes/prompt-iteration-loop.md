<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Optimization Loop

Reference for the agent-driven optimization loop: its components, which controls
the runtime enforces, and how tenant playbooks, scope constraints, and iteration
memory work. The `optimization` agent drives the loop autonomously.

## Components

| Component | Claude Code | Codex | Role |
|---|---|---|---|
| Optimization agent | `.claude/agents/optimization.md` | `.codex/agents/optimization.md` | Orchestrator: analyzes results, creates variants, runs evals, and iterates until targets are met |
| Step attribution | `.claude/agents/step-attribution.md` | `.codex/agents/step-attribution.md` | Internal failure-attribution phase after each eval run |
| Variant reviewer | `.claude/agents/variant-reviewer.md` | `.codex/agents/variant-reviewer.md` | Independent guardrail check on each proposed variant before eval |
| Eval runner | `.claude/commands/eval-runner.md` | `.codex/commands/eval-runner.md` | Runs evals and returns score summaries |
| Evaluation asset assistant | `.claude/agents/evaluation-asset-creator.md` | `.codex/agents/evaluation-asset-creator.md` | Triggers and monitors the shared core evaluation-asset pipeline, validates its eight checkpointed stages and artifacts, diagnoses failures, and explains review decisions |
| Synthetic samples | `.claude/commands/synthetic-samples.md` | `.codex/commands/synthetic-samples.md` | Creates synthetic examples for dataset augmentation |
| Synthetic pruner | `.claude/commands/synthetic-pruner.md` | `.codex/commands/synthetic-pruner.md` | Validates and cleans synthetic data |
| Reset tenant | `.claude/commands/reset-tenant.md` | `.codex/commands/reset-tenant.md` | Resets generated tenant optimization and eval artifacts when explicitly requested |

The synthetic-samples and synthetic-pruner commands are generic tenant-level
synthetic-data helpers, not evaluation-asset pipeline Stage 7. Stage 7 is a
receipt-backed core-pipeline stage with its own homogeneous-cluster,
mechanical-filter, dependency-fingerprint, and review/finalization rules.

## Prompt sets by tool

- **Claude Code:** use the `.claude/` agents and commands. Do not redirect
  Claude Code runs to `.codex/`; those prompts are written for Codex sessions.
- **Codex:** use the matching `.codex/` agents and commands. To run an eval, use
  `.codex/commands/eval-runner.md` or
  `python scripts/eval/run_eval_and_summarize.py --config tenants/<tenant_id>/configs/<config>.json`.
- **Automation wrappers:** `scripts/optimize-loop.sh` invokes Claude Code and
  should stay Claude Code-specific. Codex automation should use a separate
  wrapper or an explicit Codex session.
- **No coding agent:** `python -m hephaestus.cli optimize --policy <policy>.json`
  runs prompt- and parameter-level optimization with only API credentials. See
  [headless optimization](headless-optimization.md) for its scope and policy
  format.

Unless a tool-specific prompt says otherwise, both tools share the tenant
playbooks, scope constraints, eval configs, iteration memory, and manual
fallback. Both must follow the tenant playbook, protect tenant source
artifacts, write iteration memory under the tenant docs directory, and not
commit unless the user asks.

## Evaluation datasets

Evaluation asset preparation precedes the optimization loop. The shared core,
not the assistant prompt, owns normalization, evaluation-guideline creation,
clustering metadata, case-specific rubric generation, synthetic coverage, and
dataset splitting. The resulting versioned splits are the inputs to
optimization and evaluation.

| Reference | Covers |
|---|---|
| [Evaluation input contract](evaluation-input-contract.md) | The vendor-neutral labeled and unlabeled JSONL boundary required before asset creation |
| [Feedback and unlabeled trace dataset flow](feedback-dataset-flow.md) | Converting trusted feedback plus unlabeled trace distributions into versioned train, validation, test, and regression datasets |

## Enforcement Boundary

This is the canonical list of the controls the current implementation
enforces. Agent-enforced controls are useful protocol checks, but a user or any
other process with checkout access can bypass them. They are not runtime or
operating-system security boundaries.

| Category | Controls |
|---|---|
| **Runtime-enforced** | config/schema validation; duplicate physical `case_id` rejection; exclusive output reservation; per-case execution status; successful-only aggregates; manifest authentication; and run-identity comparison controls. |
| **Agent-enforced / bypassable** | tenant playbook and scope; training-only authoring; independent variant review; clone-new-variant; fixed scorer; validation-only selection; and iteration memory. |
| **Recommended conventions** | one focused edit; smallest useful/prompt-first escalation; repeated trials; scorer/judge calibration; and untouched future validation. |

The headless optimizer enforces several agent-enforced controls in code; see
[its enforcement section](headless-optimization.md#enforcement).

## Tenant playbooks

Each tenant sets its own rules in `tenants/<tenant_id>/docs/iteration-playbook.md`.
The playbook is authoritative: it sets the scope, success criteria, and rules
the optimization agent must follow.

### Scope constraints

A playbook can restrict which files the optimization agent may create or
modify. Three layers apply the restriction:

1. **Playbook definition:** the playbook has a `### Scope Constraint` section
   with an `**Allowed pattern**` glob and a list of forbidden categories.
2. **Agent self-check:** on startup, the optimization agent extracts the scope
   constraint and checks every file it creates or modifies against the allowed
   pattern before proceeding. Violations are blocking.
3. **Variant reviewer:** the variant reviewer independently reads the playbook,
   extracts the same constraint, and checks the variant path and any other
   modified files in its Scope Compliance check. This catches anything the
   optimization agent missed.

Eval configs, iteration memory (`iteration-memory.jsonl`), and change logs
(`change-log.md`) are exempt because the loop itself needs them. If a playbook
has no `### Scope Constraint` section, no scope restrictions are enforced.

## Iteration memory

Structured history lives in `tenants/<tenant_id>/docs/iteration-memory.jsonl`,
one JSON record per cycle, with the human-readable `change-log.md` alongside
it. Together they let the agent tell persistent failures from new ones and
avoid re-proposing reverted approaches.

## Manual fallback

When agents are unavailable:

1. Clone a new variant from the latest; never edit in place.
2. Make targeted changes tied to identified failure clusters.
3. Re-run evals after each edit set and compare against the baseline.
4. Keep changes with a measured net improvement; otherwise revert or narrow the
   scope.
