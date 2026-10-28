<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# External prompting guides

Optional reference for prompting principles and their canonical sources.
Consult it when a specific technique seems relevant to a failure pattern. For
synthetic dataset sources and a quality checklist, see
[`synthetic-example-creation-sources.md`](synthetic-example-creation-sources.md).

## Canonical top-5 sources

- OpenAI Prompt Engineering Guide: https://platform.openai.com/docs/guides/prompt-engineering
- Anthropic Prompt Engineering Overview: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview
- Google Vertex AI Prompt Design Strategies: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/prompt-design-strategies
- Microsoft Azure OpenAI Prompt Engineering: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/prompt-engineering
- OPRO (ICLR 2024): Large Language Models as Optimizers: https://arxiv.org/abs/2309.03409

Retrieval date for this source set: February 17, 2026.

## Unified principles

1. **Be explicit about the task and success conditions.** State the model's job
   and what counts as correct.
2. **Specify a strict output contract.** Define required sections, ordering,
   allowed fields, and prohibited formats.
3. **Structure context with delimiters and hierarchy.** Separate system rules,
   case context, and output instructions.
4. **Use examples strategically.** Add few-shot examples only for patterns that
   persist after instruction-clarity fixes.
5. **Define ambiguity and abstention behavior.** Say how to handle uncertain or
   conflicting evidence.
6. **Break complex tasks into ordered reasoning steps.** Sequence the evaluation
   while keeping the output format strict.
7. **Iterate with eval-driven loops.** Baseline, eval, cluster failures, apply
   targeted changes, re-test.
8. **Minimize overfitting.** Favor generalizable rules over one-off,
   artifact-specific heuristics.
9. **Optimize against explicit objectives and budgets.** Define targets before
   editing, track against them, and escalate when small edits fail.

## Failure cluster to fix

| Failure cluster | Fix |
|---|---|
| Classification accuracy | Tighten decision criteria and precedence rules. Add explicit uncertainty handling. If still unstable, add one representative few-shot example. |
| Response shape | Enforce exact heading names and order. Ban optional extra sections when checks require a strict shape. |
| Plain text / format | State plain-text-only output explicitly. Ban markdown bullets, tables, fenced code blocks, and rich formatting. |
| Defang-related | Add strict URL/IOC normalization rules and clear positive and negative examples. |
| Mixed regression after a fix | Reduce the scope of the last change. Prefer explicit rule precedence over broad rewrites. |
