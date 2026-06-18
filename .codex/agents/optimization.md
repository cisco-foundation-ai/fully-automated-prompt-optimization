<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Optimization Workflow for Codex

Use this workflow when the user wants to improve eval scores, analyze failures, iterate on prompt quality, optimize prompt variants, adjust chain parameters, or improve chain architecture.

## Inputs

Required:

- Tenant ID, for example `hotpotqa`, `smoke_test`, `aime2025`, or `cti_rcm`
- Eval config path under `tenants/<tenant_id>/configs/`

Optional:

- Success criteria, such as `composite_score >= 90`
- Existing eval output directory

If required input is missing in an interactive Codex session, ask before proceeding. In non-interactive `codex exec` mode, infer conservatively from tenant docs/configs when there is a single obvious candidate; otherwise stop with a clear blocker.

## Core Principles

1. Scope contract first. Before analysis or variant creation, read `tenants/<tenant_id>/docs/iteration-playbook.md` and produce a scope contract listing allowed optimization levels and forbidden optimization levels. The "Chain-Level Optimization Scope" section, when present, is authoritative.
2. Pre-variant scope check. Before creating any prompt, parameter, or structural variant, verify the proposed file changes only touch levels allowed by the scope contract.
3. Attribution-driven prioritization. Use `.codex/agents/step-attribution.md` as an explicit phase after each eval run. Run the Python attribution helper when results are available.
4. Cheapest viable level first. Prefer prompt changes on ties, then parameter changes, then structural changes, unless the scope contract or attribution evidence says otherwise.
5. Optimize against train split only. Use validation/test only for cross-validation when the playbook requires it.
6. Always branch from the current best variant. Do not diverge from older or parallel failed variants unless the user asks for an experiment.
7. Do not commit. Leave commits to the user.

## Workflow

1. Read project instructions in `AGENTS.md`, tenant docs, eval config, scorer code, chain code, prompt files, and previous `docs/iteration-memory.jsonl`.
2. Emit the scope contract before modifying any files.
3. Establish or locate a baseline eval result. If no result exists, run the configured eval.
4. Run failure attribution using `.codex/agents/step-attribution.md`.
5. Select the allowed optimization level with the most addressable failures.
6. Create exactly one focused variant at a time.
7. Review the variant using `.codex/agents/variant-reviewer.md`. In a single-agent Codex run, perform this as a fresh-eyes checklist phase before eval.
8. Run eval on the variant.
9. Compare against the previous best by reading `summary.md`/`results.jsonl` directly or by using `src.hephaestus.runs.compare.compare_runs` from a short Python helper.
10. Append a structured record to `tenants/<tenant_id>/docs/iteration-memory.jsonl` and update `docs/change-log.md`.
11. Continue until the success criteria are met or all allowed levels are exhausted.

## Prompt Variant Rules

- Never edit existing variants in place. Clone to a new `variant-NNN.md`.
- Do not add example-specific hints, case IDs, exact training answers, or train-set examples.
- Preserve `${placeholder}` names. Added placeholders must be provided by the chain.
- Match the scorer's output expectations exactly.
- Create a separate eval config for each variant.

## Parameter Variant Rules

- Create a new eval config such as `config-<description>.json`.
- Document the hypothesis in the config or in `iteration-memory.jsonl`.
- Only adjust parameters allowed by the scope contract.

## Chain Variant Rules

- Follow `docs/processes/chain-variant-conventions.md`.
- Put new chain files under `tenants/<tenant_id>/chains/variants/`.
- Preserve the `ChainState` protocol: `context`, `output_text`, `step_outputs`, and `diagnostics`.
- Use prompt paths from config, not hardcoded paths.
- Do not introduce dataset leakage or import-time side effects.

## Eval Execution

Read `tenants/<tenant_id>/docs/eval-operations.md` for the preferred method.

- Local/default: `python scripts/eval/run_eval_and_summarize.py --config <config>`
- Direct fallback: `python -m hephaestus.cli eval --config <config>`
- Remote/K8s tenants: use `deploy/scripts/run_eval.sh --config <config> --detach` when the tenant docs require it.

## Completion Status

When running under `scripts/optimize-loop-codex.sh`, the last response must include exactly one of:

- `<optimization_status>requirements met</optimization_status>`
- `<optimization_status>requirements not met</optimization_status>`

Use `requirements met` only when the target is achieved or all allowed levels are exhausted. Use `requirements not met` when another round should continue.

## Final Report

Report:

- Scope contract
- Metrics progression
- Best variant path and metrics
- Optimization level used
- Outstanding failure clusters
- Next recommended action within the allowed scope
