<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Architecture

## Contributor Quickstart

```
load_eval_config(path) → EvalConfig(chain=ChainConfig(path, fn, config))

run_evaluation(config)
  ├── Load dataset, scorer, provider
  ├── _ensure_chain → load_chain_factory → factory(provider, config)
  └── For each case: chain.invoke → scorer.score_pipeline_case → collect results
```

## Overview

FAPO has two layers:
1. Core (`src/hephaestus`): dataset loading, prompt rendering, skill loading, provider invocation, scoring, and eval run output writing.
2. Tenant (`tenants/<tenant_id>`): prompt variants, agent skill files (for agentic tenants), tenant conversion code, local data caches, and run outputs.

Customer raw and derived artifacts are managed through `python -m hephaestus.cli customer-data` and
stored canonically in GCS. Local tenant runtime assumes datasets are already in unified JSONL format.

Repository layout rule:
- Tenant-specific docs live under `tenants/<tenant_id>/docs/` and are checked in.

## Chain Execution Model

The primary evaluation target is a **LangGraph chain** — a compiled `StateGraph` that defines the evaluation workflow.

### Execution Flow

```
load_eval_config(path) → EvalConfig(chain=ChainConfig(path, fn, config))

run_evaluation(config)
  ├── Load dataset, scorer
  ├── Build provider
  ├── _ensure_chain(config, provider)
  │     └── load_chain_factory(path, fn) → factory(provider, config)
  └── For each case:
        ├── chain.invoke({"context": case.context, ...})
        ├── Extract output_text, step_outputs from final state
        ├── scorer.score_pipeline_case(case, step_outputs, scoring_profile)
        └── Collect results
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
| `src/hephaestus/engine/skills.py` | Skill file loading + runtime `<available_skills>` context-message injection (agentic tenants) |
| `src/hephaestus/types.py` | `ChainConfig` dataclass and `EvalConfig.chain` field |

### Scoring

All chains are scored via `scorer.score_pipeline_case(case, step_outputs, scoring_profile)`. The default implementation calls `score_case` with the final `output_text`. Tenant scorers can override `score_pipeline_case` to inspect intermediate step outputs.
