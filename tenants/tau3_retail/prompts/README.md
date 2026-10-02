<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Prompt Lineages

These files preserve the exact Tau agent instructions evaluated in the recorded
FAFO experiment. Every variant includes repository license metadata; the Tau
launchers remove that exact header before sending the instruction to the model.

| Arm | Sequence | Winner |
|---|---|---|
| Trusted only | `v3/trusted/variant-t001.txt` through `variant-t011.txt` | `variant-t008.txt` |
| Full mixed | `v3/mixed/m000.txt` through `m007.txt` | `m004.txt` |
| Staged inferred | `v3/staged/inferred/s000.txt` through `s016.txt` | `s015.txt`; S016 was interrupted |
| Staged trusted | `v3/staged/trusted/t000.txt` through `t004.txt` | `t001.txt` |

The recorded hashes cover the license-header-stripped prompt bodies, so they
remain comparable to the original experiment artifacts. Each file is immutable
experiment evidence. Start a new lineage for a new Tau revision, model, rubric
asset, or dataset membership. See
[`docs/prompt-contract.md`](../docs/prompt-contract.md) and
[`docs/iteration-memory.jsonl`](../docs/iteration-memory.jsonl) for provenance.
