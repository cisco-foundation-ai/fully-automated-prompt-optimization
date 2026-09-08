<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Profile

## Organization Profile

- External agentic benchmark tenant based on Tau-3 Retail.
- Evaluates a tool-using customer-service agent interacting with a simulated
  user and a stateful Retail environment.
- Uses FAFO V3 to author evaluation guidelines and case rubrics from sparse
  trusted feedback plus unlabeled traffic, then uses FAPO for prompt-only
  optimization.

## Security Environment Assumptions

- Tau is installed in a pinned sibling checkout and isolated virtual
  environment; it is not vendored into FAPO.
- Runtime credentials are supplied through environment variables or Tau's
  ignored `.env` file.
- Raw episodes, feedback, evaluation assets, datasets, and eval outputs are
  local-only.
- Only outbound text-mode model calls are required. Tau servers, LiteLLM proxy,
  voice, and LiveKit services are outside this recipe.

## Threat Model Focus

- Leakage of native rewards, expected actions, hidden scenarios, assertions, or
  final-holdout contents into FAFO inputs or prompt authoring.
- Treating historical assistant behavior or tool output as correctness without
  trusted feedback support.
- Cross-split leakage through repeated trials or related task variants.
- Claiming tool success from agent wording rather than the tool result.
- Reward hacking against the FAFO judge without native Tau improvement.

## Known Safe Patterns

- Keep the external final holdout outside the FAFO asset.
- Use one complete episode per FAFO record and one scenario family per
  `group_id`.
- Sample feedback without native outcomes, then require explicit human trust.
- Freeze policy, tools, models, temperatures, task IDs, and seeds across prompt
  comparisons.
- Judge full fresh trajectories and verify state-changing outcomes from tool
  results.

## Tenant Terminology

- **Tau episode**: one agent–user simulation with messages, tools, and a fresh
  environment state.
- **Native score**: Tau's environment/evaluator result, kept outside FAFO input.
- **Trusted case**: an episode with manually reviewed user feedback.
- **Inferred case**: an unlabeled episode with a V3 case-specific rubric.
- **Scenario family**: experiment-created leakage-control grouping; not a native
  Tau field.
- **Mixed arm**: prompt optimization over trusted and approved inferred cases
  together.
- **Staged arm**: inferred-only optimization followed by trusted-only refinement.
