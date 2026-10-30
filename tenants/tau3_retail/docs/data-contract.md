<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Data Contract

## Dataset Inventory

Local, ignored source artifacts:

- `source_artifacts/all_unlabeled.jsonl`: every development Tau episode mapped
  to an unlabeled FAFO record.
- `source_artifacts/feedback-selection.jsonl`: outcome-blind manual review
  sample.
- `source_artifacts/feedback-review/`: conversation-only annotation files.
- `source_artifacts/labeled_feedback.jsonl`: selected episodes with trusted
  feedback.
- `source_artifacts/unlabeled_traffic.jsonl`: disjoint remainder.

Local, ignored FAFO output:

- `evaluation_assets/<asset_id>/datasets/train.jsonl`
- `validation.jsonl`, `test.jsonl`, and `regression.jsonl`
- trust-tier views such as `train_trusted.jsonl` and `train_inferred.jsonl`
- `review.md`, the asset's review report

The repository tracks only the split metadata in `recipe/retail-split.json`
and the build config in `recipe/asset-build.json`.

## Case Schema

Input records follow `fafo-evaluation-input-v1`:

- `record_id`: `tau3-retail-task-<task>-trial-<trial>`.
- `request_id`: same stable episode-level ID.
- `group_id`: predeclared scenario-family ID.
- `task_type`: `retail_customer_support`.
- `route`: `tau3_retail`.
- `user_input`: first user message.
- `conversation_context`: messages before that first request.
- `assistant_output`: final textual assistant response.
- `tool_calls`: ordered calls with linked result or error.
- `episode.events`: complete ordered messages, calls, and results.
- `runtime`: Tau revision, domain, task, trial, seed, models, and temperatures.
- `metadata`: source run, source simulation, split, and grouping provenance.
- `feedback`: trusted records only; polarity, rationale, optional correction,
  and `human_review` source.

Evaluation cases use FAFO's `EvalCase` schema and contain the Tau task/seed
runtime context plus the case's evaluation criteria
(`expected.evaluation_guidelines`), tool expectations, provenance, confidence,
and trust tier.

## Label Taxonomy

- Feedback polarity: `positive`, `negative`, or `mixed`.
- Feedback trust: explicitly reviewed `yes`; anything else is rejected.
- Rubric provenance: `guideline_grounded` or `trace_inferred`.
- Dataset trust tier: `trusted_feedback` or `inferred_from_trusted_feedback`.
- Evaluation criterion status: satisfied, partial, violated, or not applicable.

## Check Expectations

- Labeled and unlabeled IDs are unique, disjoint, and reconstruct the full
  development export.
- Tool calls have unique IDs and exactly one linked result.
- Protected Tau correctness keys never appear in FAFO inputs.
- Every trusted feedback record has a rationale and explicit human trust.
- FAFO split families do not cross partitions; inferred cases never enter
  `regression`.
- `GuidelineJudgeScorer` returns `guideline_score`, `guideline_pass`,
  `critical_violations`, and `applicable_criteria`.
- The pass rule is score at least 90 with zero critical violations.

## Dataset Update Procedure

1. Pin a Tau revision and hash its Retail tasks/policy.
2. Create a new scenario-family split or explicitly reuse the recorded split.
3. Generate new baseline episodes under fixed controls.
4. Export, sample, manually annotate, and join using the tenant code.
5. Build a new asset ID with `assets build`; a finished asset is never
   rewritten.
6. Read the asset's `review.md`: guidelines, set-aside lessons, excluded
   records, and low-confidence rubrics.
7. Record counts, model/settings, hashes, and split seed in the changelog.

Never commit the resulting episode or evaluation-asset payloads.
