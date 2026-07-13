<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Software Name Categorization Tenant

This example tenant is for the FAPO Software Name Categorization Challenge.
Participants classify software names into domains of security concern using
`gpt-4o-mini`.

## Challenge Task

You will be provided training, eval, and test datasets that categorize software
names to domains of security concern. Use FAPO to build an LLM prompt for
`gpt-4o-mini` that achieves F1 > 95 on both eval and test.

## Prerequisites

- An OpenAI API key.
- Access to `gpt-4o-mini`.
- A working FAPO development environment.

## Load Challenge Data

The challenge JSONLs live under `fapo_challenge/` so they can be tracked as
public challenge assets. Copy them into this tenant locally before running evals:

```bash
mkdir -p tenants/software_name_categorization/datasets/datasets
cp fapo_challenge/software_name_categorization/data/*.jsonl \
  tenants/software_name_categorization/datasets/datasets/
```

The copied files under `tenants/*/datasets/` are local runtime artifacts and
should not be tracked by git.

## Eval Commands

```bash
python -m hephaestus.cli eval --config tenants/software_name_categorization/configs/train.json
python -m hephaestus.cli eval --config tenants/software_name_categorization/configs/eval.json
python -m hephaestus.cli eval --config tenants/software_name_categorization/configs/test.json
```

## Rules

- You can use this example tenant, or prompt FAPO to create a tenant with your
  own optimization strategies.
- Only conduct error attribution over the training dataset.
- Evaluate each variant using eval and test datasets.
- Use only `context.software_name` as model-visible input.
- The model must output exactly one label from `labels.md`.

## Challenge Period

The challenge runs from August 4, 2026 through August 6, 2026 EOD.

Leaderboard results will be displayed at the Black Hat 2026 booth.

