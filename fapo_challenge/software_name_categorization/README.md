<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Software Name Categorization Challenge

## Task

You will be provided training, eval, and test datasets that categorize software
names into domains of security concern. Use FAPO to build an LLM prompt for
`gpt-4o-mini` that achieves `F1 > 90` on both the test dataset.

Each dataset case contains only a software name as model-visible input. The
model should output exactly one label from `labels.md`.

## Prerequisites

- An OpenAI API key.
- Access to `gpt-4o-mini`.
- A working FAPO setup.

## Dataset Files

- `data/train.jsonl` - training cases for prompt iteration and error attribution.
- `data/eval.jsonl` - evaluation cases for variant evaluation.
- `data/test.jsonl` - test cases for variant evaluation and leaderboard results.

Each line is a FAPO-compatible JSON object with `context.software_name` and
`expected.category`.

## Quick Start With Example Tenant

An example tenant is available at
`tenants/software_name_categorization/`.

Copy the challenge datasets into that tenant's local dataset directory:

```bash
mkdir -p tenants/software_name_categorization/datasets/datasets
cp fapo_challenge/software_name_categorization/data/*.jsonl \
  tenants/software_name_categorization/datasets/datasets/
```

Then prompt FAPO to optimize the example tenant. For example:

```text
Optimize the software_name_categorization tenant until composite score on test set reaches 90.
```

## Mini Challenge

A standalone manual prompt-tuning mini challenge is available at
`mini_challenge/`.

It includes a 10-case test subset, a command-line evaluator, a training dataset
viewer, easy/medium/difficult level selection, and a local UI that compares a
manually tuned prompt against bundled FAPO v006 results. The mini challenge is
decoupled from FAPO and can be run directly from that folder.

## Rules

- You can use the provided example tenant, or prompt FAPO to create a tenant
  with your own optimization strategies.
- Only conduct error attribution over the training dataset.
- Evaluate each variant using the eval and test datasets.
- Do not use vendor, description, URL, or other external fields as model input.

## Data Hygiene

Only conduct error attribution over the training dataset. Eval and test datasets
are for scoring variants, not for failure attribution or manual label-specific
prompt tuning.

## Challenge Period

The challenge runs from August 4, 2026 through August 6, 2026 EOD.

Leaderboard results will be displayed at the Black Hat 2026 booth.
