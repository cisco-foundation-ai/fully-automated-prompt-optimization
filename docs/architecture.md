<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Architecture

## Contributor Quickstart

```
load_eval_config(path) → EvalConfig(chain=ChainConfig(path, fn, config))

run_evaluation(config)
  ├── Deep-copy caller config and validate the copied paths
  ├── Single complete-dataset byte snapshot and duplicate physical `case_id` rejection
  ├── Reserve an absent output directory and initialize progress
  ├── Before callbacks, snapshot copied execution config; chain/scorer package
  │   `.py` files; declared prompts, skills, and case prompts; and runtime facts
  ├── Resolve provider settings/facts → load and validate scorer → start MCP
  │   and discover tools → build provider → load chain factory
  ├── Stream each case with `chain.stream` → score → record per-case outcome
  ├── Tear down MCP while the input snapshot remains live
  ├── Build safe identity/config, results, successful-only aggregates, summary,
  │   and in-memory attribution
  ├── Exit and clean up the temporary snapshot
  └── Publish terminal artifacts, with `run_manifest.json` installed last, then
      return immediately
```

## Overview

FAPO has two layers:
1. Core (`src/hephaestus`): dataset loading, prompt rendering, skill loading, provider invocation, scoring, and eval run output writing.
2. Tenant (`tenants/<tenant_id>`): prompt variants, agent skill files (for agentic tenants), tenant conversion code, local data caches, and run outputs.

Customer raw and derived artifacts are managed through `python -m hephaestus.cli customer-data` and
stored canonically in GCS. Local tenant runtime assumes datasets are already in unified JSONL format.

Repository layout rule:
- Tenant-specific docs live under `tenants/<tenant_id>/docs/` and are checked in.
- Tenant directories are an organizational boundary, not an operating-system sandbox.

## Chain Execution Model

The primary evaluation target is a **LangGraph chain** — a compiled `StateGraph` that defines the evaluation workflow.

### Execution Flow

```
load_eval_config(path) → EvalConfig(chain=ChainConfig(path, fn, config))

run_evaluation(config)
  ├── Deep-copy caller config and validate the copied paths
  ├── Single complete-dataset byte snapshot and duplicate physical `case_id` rejection
  ├── Reserve an absent output directory and initialize progress
  ├── Before callbacks, snapshot copied execution config; chain/scorer package
  │   `.py` files; declared prompts, skills, and case prompts; and runtime facts
  ├── Resolve provider settings/facts → load and validate scorer → start MCP
  │   and discover tools → build provider → load chain factory
  ├── Stream each case with `chain.stream` → score → record per-case outcome
  ├── Tear down MCP while the input snapshot remains live
  ├── Build safe identity/config, results, successful-only aggregates, summary,
  │   and in-memory attribution
  ├── Exit and clean up the temporary snapshot
  └── Publish terminal artifacts, with `run_manifest.json` installed last, then
      return immediately
```

### Chain State

Every chain operates on a state dict with these protocol fields:

| Field | Type | Description |
|---|---|---|
| `context` | `Dict[str, str]` | Input from `case.context` — populated by the eval runner |
| `output_text` | `str` | Final output — read by the eval runner for scoring |
| `step_outputs` | `Dict[str, str]` | Intermediate outputs — available to pipeline-aware scorers |

Chain authors can extend the state with additional domain-specific fields.

### Chain Infrastructure

| Module | Purpose |
|---|---|
| `src/hephaestus/chains/types.py` | `ChainState` TypedDict |
| `src/hephaestus/chains/loader.py` | Dynamic import of chain factory functions from tenant `.py` files |
| `src/hephaestus/chains/nodes.py` | `make_llm_node` and `build_node_context` utilities for LLM-calling nodes |
| `src/hephaestus/chains/agentic_nodes.py` | `make_agentic_node` — ReAct tool-calling node with MCP support and runtime skill injection |
| `src/hephaestus/engine/skills.py` | Tenant-owned skill-file loading + runtime `<available_skills>` context-message injection (agentic tenants; the skill body is not inlined into the authored prompt) |
| `src/hephaestus/types.py` | `ChainConfig` dataclass and `EvalConfig.chain` field |

`chain.config.skill_paths` is inventory and validation input, not automatic
chain mutation: it does not itself inject a skill into a tenant chain. An
agentic tenant factory must call `render_skills_block` over those paths and
pass its ordered output as `skills_text` to the selected node factory. The node
is then responsible for the one runtime `<available_skills>` message. Runtime
input capture preserves each configured skill-directory name as a distinct
heading after snapshotting and preserves configured order.

### Scoring

All chains are scored via `scorer.score_pipeline_case`. The runner always
passes final `output_text` and passes `tool_call_history` only when the scorer
signature accepts it; the default implementation forwards final `output_text`
to `score_case`; tenant scorers can override `score_pipeline_case` to inspect
intermediate step outputs and agentic trajectory data.

## Run Artifacts and Attribution Boundary

An authoritative terminal run is a reserved output directory containing
`progress.json`, `results.jsonl`, `run_config.json`, `run_identity.json`,
`summary.md`, and a final `run_manifest.json` that authenticates the inventory.
The terminal bundle status is `completed`, `degraded`, or `failed`. Results have
per-case execution statuses; summaries and progress averages use successful
results only and report infrastructure failures separately.

`results.jsonl` does not serialize raw dataset `context` or `expected` fields
by default, but it is still a tenant artifact rather than a privacy boundary:
output, step output, diagnostics, and agentic trajectory data can repeat
model-visible input or expected data. Runtime step attribution is deterministic and rule-based. Any later
semantic interpretation by an optimization agent is a separate, tenant-governed
activity rather than an output of the runtime attribution pass.
