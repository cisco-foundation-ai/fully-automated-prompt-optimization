<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Prompt Contract

## Output Format Contract

- Output exactly one label.
- The output label must be one of the labels in `labels.md`.
- Do not include explanations, markdown, bullets, punctuation, or confidence.

## Decision Policy

- Classify from the software name alone.
- Prefer the domain of security concern a defender would care about when the
  software appears in an endpoint, proxy, asset, or inventory log.
- Use `general_utility_other` only when the software name does not primarily
  belong to another security-concern domain.
- Make a best-effort choice even for niche or ambiguous software names.

## Defang and Safety Rules

- Do not execute software, browse vendor pages, call tools, or use external
  enrichment in the classification chain.
- Do not include operational instructions for offensive tools.
- The response should contain only the selected label.

## Variant Strategy

- Optimize prompt variants under `prompts/modules/classify/`.
- Conduct failure attribution only on `train.jsonl`.
- Score candidate variants on `eval.jsonl` and `test.jsonl`.
- Avoid hand-tuning directly from eval or test failures.

## Non-Goals

- Multi-step retrieval or web lookup.
- Tool-assisted software enrichment.
- Explanatory classification output.
- Adding extra input fields beyond `context.software_name`.

