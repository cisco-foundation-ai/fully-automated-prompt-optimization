<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Optimization Loop

## Purpose

Architecture reference for the optimization system. The `optimization` agent drives the loop autonomously; this document describes the components it uses.

Claude Code and Codex use parallel prompt sets. Users running Claude Code should continue to use the `.claude/` agents and commands. Users running Codex should use the matching `.codex/` agents and commands. The tenant playbooks, scope constraints, eval configs, iteration memory, and manual fallback workflow are shared unless a tool-specific prompt says otherwise.

## Architecture

### Orchestrator

| Component | Claude Code File | Codex File | Role |
|-----------|------------------|------------|------|
| Optimization Agent | `.claude/agents/optimization.md` | `.codex/agents/optimization.md` | Goal-oriented optimizer — analyzes results, creates variants, runs evals, iterates until targets are met |

### Execution Components

| Component | Claude Code File | Codex File | Role |
|-----------|------------------|------------|------|
| Step Attribution | `.claude/agents/step-attribution.md` | `.codex/agents/step-attribution.md` | Internal failure attribution phase after eval runs |
| Variant Reviewer | `.claude/agents/variant-reviewer.md` | `.codex/agents/variant-reviewer.md` | Independent guardrail check on proposed variants before eval |
| Eval Runner | `.claude/commands/eval-runner.md` | `.codex/commands/eval-runner.md` | Runs evaluations and returns score summaries |

### Data Tools

| Component | Claude Code File | Codex File | Role |
|-----------|------------------|------------|------|
| Synthetic Samples | `.claude/commands/synthetic-samples.md` | `.codex/commands/synthetic-samples.md` | Creates synthetic examples for dataset augmentation |
| Synthetic Pruner | `.claude/commands/synthetic-pruner.md` | `.codex/commands/synthetic-pruner.md` | Validates and cleans synthetic data |

### Operational Tools

| Component | Claude Code File | Codex File | Role |
|-----------|------------------|------------|------|
| Reset Tenant | `.claude/commands/reset-tenant.md` | `.codex/commands/reset-tenant.md` | Resets generated tenant optimization and eval artifacts when explicitly requested |

## Tool-Specific Usage

Use the prompt set that matches the tool running the workflow:

1. **Claude Code**: follow the existing `.claude/` agents and commands. Do not redirect Claude Code runs to `.codex/`; those prompts are written for Codex sessions.
2. **Codex**: follow the matching `.codex/` agents and commands. For eval execution, use `.codex/commands/eval-runner.md` or run `python scripts/eval/run_eval_and_summarize.py --config tenants/<tenant_id>/configs/<config>.json`.
3. **Automation wrappers**: `scripts/optimize-loop.sh` invokes Claude Code and should remain Claude Code-specific. Codex automation should use a separate wrapper or an explicit Codex session.
4. **Shared behavior**: both tools must follow the tenant playbook, protect tenant source artifacts, write iteration memory under the tenant docs directory, and avoid committing unless the user asks.

## Iteration Memory

Structured history lives in `tenants/<tenant_id>/docs/iteration-memory.jsonl` (one JSON record per cycle). The human-readable `change-log.md` sits alongside it. Together they give the agent cross-cycle awareness — distinguishing persistent vs new failures and avoiding re-proposing reverted approaches.

## Tenant Playbooks

Each tenant defines its own constraints in `tenants/<tenant_id>/docs/iteration-playbook.md`. Playbooks are authoritative — they set scope, success criteria, and rules that the optimization agent must follow.

## Scope Constraints

Tenant playbooks can restrict which files the optimization agent is allowed to create or modify. The mechanism has three layers:

1. **Playbook definition**: the tenant playbook includes a `### Scope Constraint` section with an `**Allowed pattern**` glob and a list of forbidden categories.
2. **Optimization agent self-check**: on startup, the agent extracts the scope constraint and verifies every file it creates or modifies against the allowed pattern before proceeding. Violations are blocking.
3. **Variant reviewer validation**: the variant-reviewer independently reads the playbook, extracts the same constraint, and verifies the variant path and any other modified files as Check 7 (Scope Compliance). This catches anything the optimization agent missed.

**Exempt operational files**: eval configs, iteration memory (`iteration-memory.jsonl`), and change logs (`change-log.md`) are not subject to scope constraints — they are necessary for the optimization loop itself.

If no `### Scope Constraint` section exists in a tenant playbook, no scope restrictions are enforced.

## Manual Fallback

When agents are unavailable:
1. Clone a new variant from the latest — never edit in-place.
2. Make targeted changes tied to identified failure clusters.
3. Re-run evals after each edit set and compare against baseline.
4. Keep changes with measured net improvement; revert or narrow scope otherwise.
