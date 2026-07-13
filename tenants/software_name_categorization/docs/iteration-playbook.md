<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Iteration Playbook

## Prerequisites

- Set an OpenAI API key in the environment expected by the OpenAI provider.
- Confirm access to `gpt-4o-mini`.
- Copy challenge JSONLs into `tenants/software_name_categorization/datasets/datasets/`.
- Run the train config once to confirm the chain and scorer work locally.

## Iteration Loop

1. Run `configs/train.json`.
2. Inspect training failures and group them by confusion pattern.
3. Update the prompt variant using only training-set attribution.
4. Run `configs/eval.json` and `configs/test.json` for aggregate scoring.
5. Keep the variant only if eval and test both improve or hold steady.

## Stop Criteria

- Stop when eval and test both exceed F1 95.
- Stop if prompt changes improve train but regress eval or test repeatedly.
- Stop when remaining train failures require lookup knowledge unavailable from
  the software name alone.

## Regression Prevention

- Keep the output contract short and explicit.
- Avoid adding examples from eval or test cases.
- Re-run train, eval, and test after every material prompt change.
- Preserve one-label output format while adding classification guidance.

## Lessons Logging

Record useful lessons in `docs/iteration-memory.jsonl` if running a longer
optimization loop. Each line should capture the split, failure pattern, prompt
change, and observed score impact.

