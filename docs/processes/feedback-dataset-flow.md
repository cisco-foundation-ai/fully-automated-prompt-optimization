<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Data Pipeline

The FAFO data pipeline turns agent traces and a small amount of user
feedback into evaluation datasets with case-specific rubrics. The
optimization loop then trains, selects, and tests on those datasets, so an
agent can improve from its own production traffic.

This guide explains the concepts and the trust model. For the steps, config,
outputs, and case format, see the
[data pipeline reference](../references/data-pipeline.md). For the input
format, see the
[`fafo-evaluation-input-v1` contract](evaluation-input-contract.md).

## Where it fits

```text
 ┌─► agent traces + user feedback
 │          │
 │          ▼   data pipeline: python -m hephaestus.cli assets build
 │   evaluation datasets with case-specific rubrics
 │          │
 │          ▼   optimization loop (coding agent or headless)
 │   improved agent
 │          │
 └──────────┘   deploy, then collect new traces
```

A deployed agent rarely has labeled data. It has many unlabeled
conversations, a few with feedback, and no ground-truth answers. The pipeline
turns those into datasets the optimization loop can use under its usual
held-out rules. No chain or prompt is needed, so it can also be a new
tenant's first step.

## Two sources

| Source | What it contributes |
|---|---|
| **Trusted feedback**: episodes a person rated, optionally with a rationale or a correction | Reusable lessons about right and wrong behavior, and trusted cases |
| **Unlabeled traces**: episodes without feedback | Real traffic to evaluate, and inferred cases |

Both become cases. A feedback episode becomes a trusted case
(`trust_tier: trusted_feedback`), and an unlabeled episode becomes an
inferred case (`inferred_from_trusted_feedback`). Eval summaries report
scores per trust tier, and each split also has trusted-only and
inferred-only views.

## The method

The pipeline follows three judgment steps. Plain code handles everything
else.

1. **Observe.** For each train episode, a model extracts *lessons*: what the
   agent did wrong, did right, or could do better, each backed by quotes
   copied from the feedback or the trace. A lesson also says whether the
   agent could have known better when it acted. Lessons that need hindsight
   are dropped, as are lessons whose quotes don't appear in the episode.
2. **Synthesize.** For each route, a model groups lessons by cause and finds
   the dividing line between right and wrong behavior. It tests that line
   against both kinds of episode, then writes checkable criteria. The result
   is the *guideline catalog*. Code counts how many distinct episodes support
   each guideline, and a guideline is *strong* with three or more.
3. **Rubric.** For each episode, in every split, a model chooses the catalog
   guidelines that apply and adds case-specific criteria grounded in the
   user's request and tool-backed facts. Code copies the chosen guidelines'
   criteria into the case verbatim.

A judge later scores a *new* episode from the agent under test against these
criteria. The recorded assistant response is evidence for writing the rubric,
never the answer to optimize toward.

## Trust model

Each control below protects held-out evaluation or keeps the rubric honest.

| Control | Why |
|---|---|
| Splits are assigned before any model call | Nothing written later can depend on which split a record lands in |
| Records that share a `group_id`, or have an identical model-visible context, stay in one split | Near-copies of a test case cannot appear in train |
| Only train episodes are observed, and the build fails otherwise | Validation and test feedback can never shape the catalog the optimizer learns from |
| A held-out record's own feedback is used only for its own rubric | Held-out cases still get good rubrics without leaking into shared criteria |
| Evidence quotes are verified in code | A lesson cannot cite text the episode doesn't contain |
| Catalog criteria are copied verbatim into cases | The rubric step cannot quietly rewrite policy |
| The regression split is optional and trusted-only | A regression gate uses human-rated cases only |

What is not guaranteed: lesson, guideline, and rubric quality are model
judgment. Redaction covers email and IPv4 addresses only; it is not full PII
removal.

## Reviewing an asset

Each build writes `review.md`. It is the review step, with no approval
ceremony. Before optimizing against an asset, read:

- each guideline's support and strength, its dividing line, and its
  criteria, watching for criteria too specific to reuse;
- lessons that were set aside, marked `cannot_fix`, or dropped, with reasons;
- routes with no guideline, whose cases are all trace-inferred;
- low-confidence rubrics, and excluded records.

If the asset is not good enough, build a new version with different inputs
or settings. A finished asset is never rewritten.

## Using the asset with FAFO

Point eval configs at the asset's datasets:

```json
"dataset": {"path": "tenants/<tenant_id>/evaluation_assets/<asset_id>/datasets/train.jsonl"}
```

- Train on `train`, select variants on `validation`, and test once on
  `test`.
- Use `<split>_trusted.jsonl` or `<split>_inferred.jsonl` to optimize on one
  trust tier.
- Score cases with a judge scorer that reads
  `expected.evaluation_guidelines[].criteria[]` and evaluates the new
  episode.

The guideline catalog can also feed the agent directly as
[runtime memory cards](runtime-memory-cards.md).

## Related documentation

- [Data pipeline reference](../references/data-pipeline.md): steps, config,
  outputs, case format, resume.
- [`fafo-evaluation-input-v1` contract](evaluation-input-contract.md): input
  fields.
- [Runtime memory cards](runtime-memory-cards.md): procedural cards from the
  catalog.
- [Headless optimization](headless-optimization.md): the API-only
  optimization loop.
