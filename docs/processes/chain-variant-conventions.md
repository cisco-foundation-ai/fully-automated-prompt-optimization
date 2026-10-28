<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Chain Variant Conventions

Rules for creating, naming, and evaluating chain variants. A chain variant
changes a tenant chain's structure or parameters; a prompt variant changes only
prompt text.

## Directory layout

```text
tenants/<tenant_id>/
  chains/
    <baseline>.py                       # Baseline chain (read-only during optimization)
    variants/
      <base_chain>-<pattern>-<NNN>.py   # Structural variants
  configs/
    config-<variant-name>.json          # Eval config per variant
```

## Naming

Chain variant files follow the pattern `<base_chain>-<pattern>-<NNN>.py`:

| Part | Meaning |
|---|---|
| `<base_chain>` | Name of the parent chain file, without `.py` |
| `<pattern>` | The optimization pattern applied, from [`agentic-chain-patterns.md`](../prompting-guides/agentic-chain-patterns.md) |
| `<NNN>` | Zero-padded sequence number |

Examples:

- `answer-self-refine-001.py`: first self-refine variant of the answer chain
- `multi_hop-reflexion-001.py`: first reflexion variant of multi_hop
- `multi_hop-reflexion-002.py`: second iteration on the reflexion approach

## Metadata docstring

Every chain variant must include a module-level metadata docstring:

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

## Eval configs

Each chain variant gets its own eval config in `tenants/<tenant_id>/configs/`:

- The filename is `config-<variant-name>.json`.
- `chain.path` points to the variant file.
- All other fields (dataset, scoring, provider) stay the same as the baseline
  unless the variant requires different parameters.

A parameter-only variant has no new `.py` file: the config is the variant. It
overrides config values such as `chain.config.retrieval_k` or
`provider_settings.temperature`.

## Prompts for new nodes

Chain variants may reference prompt variants. When a chain variant adds a node,
that node's prompt goes in `prompts/modules/<node_name>/variant-001.md`,
following the normal prompt variant conventions.

## Rules

1. **Never modify the baseline chain.** Always create a new variant file.
2. **Never edit an existing variant in place.** Create a new sequence number.
3. **Use `make_llm_node`** from `src.hephaestus.chains.nodes` for new LLM nodes.
4. **Preserve the `ChainState` protocol.** Every variant must set `context`,
   `output_text`, `step_outputs`, and `diagnostics` correctly.
5. **Preserve scorer compatibility.** The variant's output format must match
   what the active scorer expects.
6. **No dataset leakage.** Chain code has no case-specific conditionals.
7. **Take all prompt paths from config.** Use `config["prompt_paths"]` for
   template paths; never hardcode them.
8. **Pattern allowlist.** Structural patterns must come from
   `agentic-chain-patterns.md`; novel patterns require user approval.
