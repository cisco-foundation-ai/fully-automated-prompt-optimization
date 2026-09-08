<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# V3 Prompt Lineages

These are the exact Tau agent instructions evaluated in the recorded FAFO V3
experiment. Files use `.txt` so a repository comment is never injected into the
model prompt.

| Arm | Sequence | Winner |
|---|---|---|
| Trusted only | `v3/trusted/variant-t001.txt` through `variant-t011.txt` | `variant-t008.txt` |
| Full mixed | `v3/mixed/m000.txt` through `m007.txt` | `m004.txt` |
| Staged inferred | `v3/staged/inferred/s000.txt` through `s016.txt` | `s015.txt`; S016 was interrupted |
| Staged trusted | `v3/staged/trusted/t000.txt` through `t004.txt` | `t001.txt` |

Each file is immutable experiment evidence. Start a new lineage for a new Tau
revision, model, rubric asset, or dataset membership. See
[`docs/prompt-contract.md`](../docs/prompt-contract.md) and
[`docs/iteration-memory.jsonl`](../docs/iteration-memory.jsonl) for provenance.
