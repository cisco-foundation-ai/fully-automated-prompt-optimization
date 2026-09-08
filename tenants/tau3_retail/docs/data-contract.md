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

- `evaluation_assets/<asset_id>/stages/08_dataset_splits/train.jsonl`
- `validation.jsonl`, `test.jsonl`, and `regression_trusted.jsonl`
- trust-tier views such as `train_trusted.jsonl` and `train_inferred.jsonl`
- `triage_hold.jsonl`

The repository tracks only the split metadata in `recipe/retail-split.json`.

## Case Schema

Input records follow `fapo-evaluation-input-v1`:

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

Published evaluation cases use FAPO's `EvalCase` schema and contain the Tau
task/seed runtime context plus FAFO evaluation guidelines, rubric, tool
expectations, provenance, confidence, and trust tier.

## Label Taxonomy

- Feedback polarity: `positive`, `negative`, or `mixed`.
- Feedback trust: explicitly reviewed `yes`; anything else is rejected.
- Rubric provenance: `guideline_grounded` or `trace_inferred`.
- Dataset trust tier: `trusted_feedback`, `inferred_from_trusted_feedback`, or
  optional `synthetic`.
- Review state: approved, rejected, pending, or held.
- Evaluation criterion status: satisfied, partial, violated, or not applicable.

## Check Expectations

- Labeled and unlabeled IDs are unique, disjoint, and reconstruct the full
  development export.
- Tool calls have unique IDs and exactly one linked result.
- Protected Tau correctness keys never appear in FAFO inputs.
- Every trusted feedback record has a rationale and explicit human trust.
- FAPO split families do not cross partitions; derived cases never enter
  `regression_trusted`.
- `GuidelineJudgeScorer` returns `guideline_score`, `guideline_pass`,
  `critical_violations`, and `applicable_criteria`.
- The pass rule is score at least 90 with zero critical violations.

## Dataset Update Procedure

1. Pin a Tau revision and hash its Retail tasks/policy.
2. Create a new scenario-family split or explicitly reuse the recorded split.
3. Generate new baseline episodes under fixed controls.
4. Export, sample, manually annotate, and join using the tenant code.
5. Create a new immutable FAFO asset ID; never overwrite a released asset.
6. Inspect holds and rubric samples before fingerprint-bound finalization.
7. Record counts, model/settings, hashes, and split seed in the changelog.

Never commit the resulting episode or evaluation-asset payloads.
