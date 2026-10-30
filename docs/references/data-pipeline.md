<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Data Pipeline

`python -m hephaestus.cli assets build --config <asset.json>` turns agent
traces and feedback into evaluation datasets. Plain code prepares the inputs
and publishes the cases. Three model steps run in between:

```text
prepare     validate, redact, and assign connected groups to splits
observe     extract lessons with verbatim evidence from train episodes
synthesize  group lessons by cause into a guideline catalog, one route at a time
rubric      write a rubric for every episode: chosen guidelines plus case criteria
publish     write the dataset splits, the review report, and the manifest
```

The code is in `src/hephaestus/data_pipeline/`. For the concepts and trust
model, see the [data pipeline guide](../processes/feedback-dataset-flow.md).

## Inputs

| Input | Required | Content |
|---|---|---|
| Feedback | Yes, at least one record | Episodes with trusted feedback: a polarity, and optionally a rationale, a correction, and correctness signals |
| Unlabeled | No | Episodes without feedback |

Both files are JSONL in the
[`fafo-evaluation-input-v1`](../processes/evaluation-input-contract.md)
format. Both sources become cases: feedback episodes as trusted cases, and
unlabeled episodes as inferred cases.

## Steps

### Prepare

- Records that share a `group_id`, or have an identical model-visible context,
  form one connected group. A group never spans splits.
- Feedback groups and unlabeled-only groups are split separately, 60/20/20
  into train, validation, and test, so feedback lands in every split.
  Feedback groups are balanced by their number of feedback records, so a
  group's unlabeled records do not crowd feedback out of a split.
- With `regression_split`, feedback groups are split 48/16/16/20 into train,
  validation, test, and regression. Regression holds trusted cases only;
  unlabeled records in a regression group are excluded.
- Redaction replaces email and IPv4 addresses in every string and object key
  except the identity fields. Set `redact` to `false` when replay needs exact values.

### Observe

The model reads each train episode with its feedback, in batches of
`batch_size`, and returns lessons:

| Field | Meaning |
|---|---|
| `type` | `failure`, `success`, or `improvement` |
| `lesson` | The behavior and the situation it applies to, checkable in another episode |
| `evidence` | Quotes copied verbatim from the feedback or the trace |
| `signal` | `explicit` (the feedback states it), `clear` (a consequence in the trace shows it), or `weak` |
| `knowable` | Whether the agent could have known the right behavior when it acted |
| `confidence` | 0 to 1 |

Code drops a lesson when it is not well formed (`malformed`), when none of
its quotes appear in the episode (`unverified_evidence`), when it needs
hindsight (`needs_hindsight`), or when its confidence is below
`min_lesson_confidence` (`low_confidence`). A quote verifies when it has at
least 8 characters and appears within one text value of its source: the
feedback's rationale, correction, or signal content, or the transcript's
messages and tool data. Fragments around an ellipsis must appear in order.
Keys and fields such as `role` and `polarity` are never evidence. An
`explicit` signal without a verified feedback quote is lowered to `clear`.

Only train episodes are observed. With `observe_traces`, unlabeled train
episodes are observed too, and their lessons rely on consequences in the
trace.

### Synthesize

For each route, the model:

1. Groups lessons by underlying cause.
2. Finds the dividing line between episodes where a behavior is right and
   where it is wrong, and tests it against both. Contradicting lessons become
   counter-examples.
3. Writes checkable criteria: `kind` (`required`, `prohibited`, or
   `preferred`), `statement`, `applicability`, `severity` (`critical`,
   `major`, or `minor`), and `scoring`.
4. Places every lesson in at least one guideline, in `cannot_fix`, or in
   `set_aside`. Code sets aside any lesson the model leaves out.

Code assigns the IDs (`G001`, `G001.c1`) and computes each guideline's
support, the number of distinct episodes behind it. A guideline is `strong`
with at least three episodes, and it enters the catalog with at least
`min_guideline_support`. Routes with more than 60 lessons are synthesized in
chunks, each call updating the previous result.

### Rubric

One call per record, in every split. The model sees the catalog of every
route, the episode, and the record's own feedback when it has any. A
guideline's applicability, not its route, decides whether it applies. It chooses the guidelines that
apply and writes case criteria for what they do not cover. Code copies the
chosen guidelines' criteria verbatim. A record with no criteria is excluded
and listed in the review report.

## Config

```json
{
  "tenant_id": "<tenant_id>",
  "asset_id": "v1",
  "feedback": "tenants/<tenant_id>/source_artifacts/feedback.jsonl",
  "unlabeled": "tenants/<tenant_id>/source_artifacts/unlabeled.jsonl",
  "model": "<openai-model>",
  "split_seed": 0,
  "regression_split": false,
  "observe_traces": false,
  "redact": true,
  "batch_size": 5,
  "min_lesson_confidence": 0.3,
  "min_guideline_support": 1,
  "workers": 4,
  "trace": {"result_keys": null, "drop_keys": []}
}
```

| Field | Notes |
|---|---|
| `feedback`, `unlabeled` | Paths relative to the repository root. `unlabeled` is optional. |
| `model` | OpenAI model for all three steps. Defaults to `gpt-6-luna`. |
| `workers` | Concurrent model calls. With the input paths, the only setting that can change when a build resumes. |
| `trace.result_keys` | Optional regex, matched against object keys at every depth, ignoring case. A matching key keeps its whole value; other keys keep only the matches nested inside them. Values outside any object are kept. |
| `trace.drop_keys` | Tool-result keys to remove at every depth, such as bulky listings. |

Without trace filters, tool data is bounded generically: depth 4, 30 keys per
object, 20 items per list, and 500 characters per string.

## Outputs

`tenants/<tenant_id>/evaluation_assets/<asset_id>/` is git-ignored and holds:

| Path | Content |
|---|---|
| `datasets/<split>.jsonl` | Eval cases for `train`, `validation`, `test`, and `regression` when enabled |
| `datasets/<split>_trusted.jsonl`, `<split>_inferred.jsonl` | Trust-tier views of train, validation, and test, written when there is unlabeled input |
| `review.md`, `review.json` | The review report |
| `catalog.json` | Guidelines, `cannot_fix` and `set_aside` lessons, and environment facts |
| `lessons.jsonl`, `dropped_lessons.jsonl` | Kept lessons, and dropped lessons with their reason |
| `rubrics.jsonl` | One rubric per record |
| `splits.jsonl` | The split and connected group of every kept record |
| `inputs/` | Copies of the input files |
| `build.json` | Frozen settings and input hashes |
| `calls.jsonl` | One row per model call across every run, with token usage |
| `cache/` | Cached model responses |
| `manifest.json` | Written last: settings, input hashes, dataset counts, and file hashes |

Point an eval config's `dataset.path` at `datasets/<split>.jsonl`.

## Case format

```json
{
  "case_id": "feedback-<record_id>",
  "task_type": "<task_type>",
  "context": {"messages_json": "...", "tool_context_json": "...", "runtime_json": "..."},
  "expected": {
    "label_source": "trusted_feedback",
    "provenance": "guideline_grounded",
    "evaluation_guideline_ids": ["G001"],
    "evaluation_guidelines": [
      {"guideline_id": "G001", "title": "...", "criteria": [{"criterion_id": "G001.c1", "kind": "required", "statement": "...", "applicability": "...", "severity": "critical", "scoring": "..."}]},
      {"guideline_id": "case", "title": "Case-specific criteria", "criteria": [{"criterion_id": "case.c1", "...": "..."}]}
    ],
    "tool_expectations": {},
    "reference_output": null,
    "confidence": 0.8,
    "intent_label": "...",
    "feedback_polarity": "negative"
  },
  "metadata": {"trust_tier": "trusted_feedback", "split": "train", "route": "...", "group_id": "...", "record_id": "...", "request_id": "...", "source": "feedback_trace", "dataset_version": "v1"}
}
```

- Unlabeled episodes become `inferred-<record_id>` cases with trust tier
  `inferred_from_trusted_feedback` and no `feedback_polarity`.
- `provenance` is `trace_inferred` when no catalog guideline applies.
- `expected.evaluation_guidelines` holds every criterion a judge scores.
  Score the cases with a judge scorer that reads it. Eval summaries report
  scores per trust tier.

## Review report

`review.md` is the review step. There is no sign-off; read the report before
optimizing against the datasets. It shows:

- Cases per split and trust tier, and every excluded record with its reason.
- Each guideline: route, strength, support, signals, dividing line, criteria,
  supporting lessons, and counter-examples.
- Lessons that cannot be checked or were set aside, with reasons.
- Environment facts, and dropped-lesson counts by reason.
- Cases to check: trace-inferred cases, routes with no guideline, and
  rubrics with confidence below 0.5.
- Model calls and token usage per step, across every run of the build.

## Resume and immutability

- Rerunning `assets build` with the same config resumes the build. Model
  responses are cached under a key built from the model, system prompt, and
  payload, so finished calls are not repeated. Editing a prompt reruns the
  calls that use it, plus every later call whose input changes as a result.
- A started build cannot resume with different settings or input contents;
  use a new `asset_id`. Only `workers` and the input paths can change. A build
  rejected for invalid input is not started, so it can rerun with fixed input.
- An asset with `manifest.json` is finished and is never rewritten.
- One build per asset can run at a time.

## Guarantees and limits

Enforced in code:

- The catalog comes only from train episodes. Validation, test, and
  regression feedback is used only for each record's own rubric. The build
  fails before synthesis if a lesson comes from a held-out episode.
- No connected group spans two splits. The build fails if an input
  `group_id` does.
- Guideline criteria in a case are copied verbatim from the catalog.

Not enforced:

- Lesson, guideline, and rubric quality are model judgment. The quote check
  only confirms that the cited text exists in the episode.
- Redaction covers email and IPv4 addresses only. It is not full PII removal.
