<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Chain Variant Conventions

## Purpose

Standards for creating, naming, and evaluating chain variants in FAFO. Chain variants represent structural or parameter changes to a tenant's chain — as opposed to prompt variants, which only change prompt text.

## Directory Layout

```
tenants/<tenant_id>/
  chains/
    <baseline>.py              # Baseline chain (read-only during optimization)
    variants/
      <name>-<NNN>.py          # Structural variants
  configs/
    config-<variant-name>.json # Eval config per variant
```

## Naming Convention

Chain variant files follow the pattern: `<base_chain>-<pattern>-<NNN>.py`

- `<base_chain>`: Name of the parent chain file (without `.py`)
- `<pattern>`: The optimization pattern applied (from `agentic-chain-patterns.md`)
- `<NNN>`: Zero-padded sequence number

Examples:
- `answer-self-refine-001.py` — first self-refine variant of the answer chain
- `multi_hop-reflexion-001.py` — first reflexion variant of multi_hop
- `multi_hop-reflexion-002.py` — second iteration on the reflexion approach

## Metadata Docstring

Every chain variant must include a metadata docstring at the module level:

```python
"""Chain variant: answer-self-refine-001

Parent: chains/answer.py
Pattern: self-refine (from agentic-chain-patterns.md)
Hypothesis: Adding a self-critique step before final output will catch
            formatting errors that cause exact-match failures.
Created by: optimization agent
Created at: 2026-03-16
"""
```

## Eval Config Convention

Each chain variant gets its own eval config in `tenants/<tenant_id>/configs/`:

- Config filename: `config-<variant-name>.json`
- The config's `chain.path` points to the variant file
- All other config fields (dataset, scoring, provider) stay the same as baseline unless the variant specifically requires different parameters

For parameter-only variants (no new `.py` file), the config is the variant — it overrides `chain.config` values like `retrieval_k` or `temperature`.

## Relationship to Prompt Variants

Chain variants may reference prompt variants. When a chain variant introduces new nodes, each new node's prompt goes in `prompts/modules/<node_name>/variant-001.md` following normal prompt variant conventions.

## Rules

1. **Never modify the baseline chain** — always create a new variant file
2. **Never edit existing variants in-place** — create a new sequence number
3. **Use `make_llm_node`** from `src.hephaestus.chains.nodes` for new LLM nodes
4. **Preserve `ChainState` protocol** — all variants must set `context`, `output_text`, `step_outputs`, and `diagnostics` correctly
5. **Preserve scorer compatibility** — the variant's output format must match what the active scorer expects
6. **No dataset leakage** — no case-specific conditionals in chain code
7. **All prompt paths from config** — use `config["prompt_paths"]` for template paths, never hardcode
8. **Pattern allowlist** — structural patterns must come from `agentic-chain-patterns.md`; novel patterns require user approval
