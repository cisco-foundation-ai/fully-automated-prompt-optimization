<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Feedback and Unlabeled Trace Dataset Flow

## Purpose

Use this flow when production, dogfood, or annotation traces include a small amount of trusted feedback and a larger amount of unlabeled application traffic.

The goal is to convert those inputs into versioned FAPO datasets that can support continuous prompt and skill optimization without pretending that previous assistant outputs are ground truth.

The workflow keeps three ideas separate:

- Trusted feedback defines what correctness means.
- Unlabeled traces define what users actually ask for.
- Matched unlabeled traces may receive inferred labels from trusted feedback,
  but only after an intent coverage gate passes.
- Synthetic examples expand coverage only when their intent matches trusted labeled evidence.

## Product and Execution Model

Evaluation asset creation is a tenant-bootstrap workflow implemented by shared
core code under `src/hephaestus/evaluation_assets/`. It does not require an
existing tenant chain, prompt, config, adapter, dataset, or documentation.

The workflow has three entry points backed by the same persisted state:

| Entry point | Use |
|---|---|
| Evaluation Asset Studio at `/evaluation-assets/` | Create assets, choose models, cluster count, and match threshold, inspect every pipeline stage, preview artifacts, monitor progress, and resume failures |
| `python -m hephaestus.cli assets ...` | Scriptable create, run, status, and resume-compatible execution |
| Evaluation Asset Assistant (`.claude/agents/` or `.codex/agents/`) | Trigger the core workflow, poll state, validate artifacts, diagnose failures, and explain human review decisions |

FAPO Explorer remains at `/`. It shows a read-only evaluation-asset summary and
links into the Studio; it does not contain asset-creation inputs.

The core pipeline—not the UI or subagent—owns all record transformation, LLM
calls, vectorization, clustering, coverage decisions, synthesis, and splitting.
The subagent is an operator and reviewer, not an alternate implementation.

## Inputs

Both JSONL files must follow the vendor-neutral
[`fapo-evaluation-input-v1`](evaluation-input-contract.md) contract before
asset creation. Vendor or application exports are converted outside the
pipeline; the core has no downstream field-name mappings.

Canonical JSONL files may begin anywhere inside the local FAPO workspace. The
core pipeline immediately copies them into the self-contained asset workspace:

`tenants/<tenant_id>/evaluation_assets/<asset_id>/raw_inputs/`

Every later stage reads only this copied input. Asset creation therefore does
not require tenant docs, prompts, chains, configs, adapters, or a legacy
`datasets/` directory.

- Trusted feedback traces:
  - Conversation or request trace.
  - Final assistant response.
  - Intermediate tool calls and tool results, when available.
  - Feedback polarity: `positive`, `negative`, or `mixed`.
  - Feedback rationale, if available.
  - Optional corrected answer, edited query, accepted tool output, or follow-up outcome.
  - Human or SME review state, if available.
- Unlabeled production traces:
  - High-volume application logs without correctness labels.
  - Tool trajectories and tool results, when available.
  - Runtime metadata needed for grouping and deduplication, such as thread ID, request ID, app version, model, and enabled tool set.

Shared repo docs and tests must not include tenant-specific trace content, tenant IDs, or real customer examples.

## Step-by-Step Flow

Asset creation has exactly eight ordered stages. Creating the asset workspace
copies the two source files into `raw_inputs/`; Stage 1 then validates those
copies. FAPO evaluation, optimization, and prompt promotion happen only after
this pipeline completes and are not additional evaluation-asset stages.

| Stage | Inputs | What happens | Outputs |
|---|---|---|---|
| 1. `raw_inputs` — Validate raw inputs | Copied `labeled_feedback.jsonl` and `unlabeled.jsonl` | Reject empty inputs; validate every record against `fapo-evaluation-input-v1`; require feedback only on labeled records; count rows and calculate source hashes | `raw_inputs/input_manifest.json`; validated copied inputs remain in `raw_inputs/` |
| 2. `prepared_inputs` — Prepare canonical inputs | Validated raw input files | Redact sensitive values; preserve the vendor-neutral field names; default `request_id` to `record_id` and `route` to `task_type`; create canonical intent text for clustering | `prepared_inputs/normalized_feedback.jsonl`, `prepared_inputs/intent_records.jsonl` |
| 3. `rubric_extraction` — Extract trusted rubrics | `normalized_feedback.jsonl`; configured rubric model | Use the configured LLM to extract scoreable `must`, `must_not`, `should`, tool expectations, deterministic checks, and intent labels from each trusted feedback record; build trusted intents and trusted FAPO cases directly from those rubrics | `decision_assets/feedback_rubrics.jsonl`, `prepared_inputs/trusted_intents.jsonl`, `prepared_inputs/trusted_cases.jsonl` |
| 4. `intent_clustering` — Mine intent clusters | `intent_records.jsonl`; configured embedding provider/model; exact cluster count | Vectorize canonical intent text with the selected OpenAI embedding model or local TF-IDF; allocate the configured cluster count across routes; cluster deterministically within each route; retain representative record IDs and top terms | `decision_assets/intent_inventory.jsonl` |
| 5. `coverage_decisions` — Apply coverage decisions | `intent_inventory.jsonl`, `intent_records.jsonl`, `trusted_intents.jsonl`; configured embedding provider/model and coverage parameters | Compare each mined cluster with trusted intents; apply the match threshold (default `0.6`) and trusted-support constraints; classify each cluster as `matched_trusted_intent`, `needs_more_trusted_examples`, or `missing_or_weak_labels` | `decision_assets/intent_matches.jsonl`, `decision_assets/coverage_report.md` |
| 6. `label_inference` — Infer reviewable labels | Intent clusters and matches; canonical unlabeled records; normalized feedback; trusted rubrics; configured rubric model | For matched clusters only, use the configured LLM and matched trusted evidence to infer a cluster rubric, attach inferred labels to the real unlabeled records, and build inferred FAPO cases; separately report every unsupported cluster | `decision_assets/inferred_unlabeled_cluster_rubrics.jsonl`, `decision_assets/inferred_unlabeled_labels.jsonl`, `decision_assets/missing_labeled_feedback_clusters.jsonl`, `decision_assets/missing_labeled_feedback_report.md`, `prepared_inputs/inferred_cases.jsonl` |
| 7. `synthetic_coverage` — Optional synthetic coverage | Supported clusters, representative requests, inferred cluster rubrics; enable flag and candidates-per-cluster setting | When enabled, use the configured LLM to generate exactly the requested candidates per supported cluster, then filter invalid, duplicate, inconsistent, leaky, or unsolvable candidates. When disabled, make no model call and write empty artifacts | `decision_assets/synthetic_candidates.jsonl`, `decision_assets/rejected_synthetic.jsonl`, `decision_assets/synthetic_filter_issues.jsonl`, `prepared_inputs/synthetic_cases.jsonl` |
| 8. `dataset_splits` — Build dataset splits | Trusted, inferred, and accepted synthetic cases; split seed | Reserve an approximately 20%, deterministic, group-safe trusted-only regression holdout; send inferred or synthetic cases that share its groups to `triage_hold`; globally assign every remaining group across train, validation, and test; write combined and provenance-specific splits and manifests | `dataset_splits/train*.jsonl`, `dataset_splits/validation*.jsonl`, `dataset_splits/test*.jsonl`, `dataset_splits/regression_trusted.jsonl`, `dataset_splits/triage_hold.jsonl`, `dataset_splits/dataset_manifest.json`, `asset_manifest.json` |

Every stage persists `pending`, `running`, `completed`, or `failed`, timestamps,
a human-readable message, and cumulative counts. `events.jsonl` provides an
append-only operational history. A failure preserves completed checkpoints;
after its cause is corrected, rerunning resumes from the first incomplete
stage.

## Evaluation Asset Studio

The universal Studio is served on the same port as FAPO Explorer with its own
index at `/evaluation-assets/`. Its creation form accepts:

- Tenant ID and asset version.
- Labeled feedback and unlabeled JSONL workspace paths.
- Rubric extraction model.
- OpenAI embedding model or explicit local TF-IDF fallback.
- Exact requested cluster count.
- Stage 5 intent match threshold, defaulting to `0.6`.
- Whether to enable Stage 7 synthetic coverage; it is disabled by default.
- Synthetic candidates per supported cluster when Stage 7 is enabled.

Selecting a tenant and asset shows the eight-stage strip. Selecting a stage
opens its inputs, processing operations, outputs, counts, artifact list, and
one syntax-highlighted example per artifact. The Intent Mining stage also
shows the projection-style cluster explorer with route filters, cluster sizes,
representative requests, and observed tools. Visualization data is separate
from artifact examples; the example panel never loads an entire JSONL file.

The Studio refreshes running state every five seconds and calls the same core
start/resume service used by CLI-driven workflows.

## Provider Selection

Rubric extraction and label inference use the configured OpenAI model. The
Studio currently offers GPT-5.x, GPT-4.1 variants, GPT-4o variants, `o3`, and
`o4-mini`; availability still depends on the caller's OpenAI account.

Intent clustering and coverage matching support:

- `text-embedding-3-small` (default)
- `text-embedding-3-large`
- `text-embedding-ada-002` (legacy)
- `tfidf` (dependency-free local fallback)

TF-IDF is a provider choice, not an OpenAI model alias. When selected, persist
`embedding_provider: tfidf` and `embedding_model: tfidf`; the pipeline must not
create an OpenAI embedding client or make embedding API calls. Never silently
switch providers after an embedding failure. Surface the failure and let the
operator explicitly choose a new asset configuration.

## Dataset Splits

Each evaluation asset produces the fixed FAPO JSONL split files below:

| Split | Contents | Primary Use |
|---|---|---|
| `train_trusted` | Trusted feedback cases selected for optimization | Optimization and failure discovery |
| `train_inferred` | Unlabeled traces with inferred labels from matched trusted feedback | Optimization coverage |
| `train_synthetic` | Filtered synthetic coverage cases for matched trusted intents | Optimization coverage |
| `validation_trusted` | Held-out trusted examples | Candidate selection |
| `validation_inferred` | Inferred unlabeled labels assigned to validation for this dataset version | Coverage-oriented validation |
| `validation_synthetic` | Filtered synthetic examples assigned to validation for this dataset version | Coverage-oriented validation |
| `test_trusted` | Held-out trusted examples used for release-candidate testing | Final release check |
| `test_inferred` | Inferred unlabeled labels assigned to test for this dataset version | Coverage-oriented final check |
| `test_synthetic` | Filtered synthetic examples assigned to test for this dataset version | Coverage-oriented final check |
| `regression_trusted` | Automatic 20% holdout sampled only from trusted feedback cases | Tight non-regression gate |
| `triage_hold` | Ambiguous, conflicting, or under-specified feedback | Review queue only |

`regression_trusted` is created automatically. The pipeline deterministically
shuffles trusted feedback groups using the split seed, reserves approximately
20% as the regression gate, and excludes those cases from train, validation,
and test. Whole `group_id` values remain together, so the exact percentage may
vary slightly when groups contain multiple cases. Inferred and synthetic cases
never enter this split. If either shares a `group_id` selected for regression,
the conflicting case is written to `triage_hold`.

## Intent Coverage Gate

Unlabeled traces are not labels. They should be used to discover high-volume intents and coverage gaps.

For each mined intent cluster:

- If the intent matches the trusted labeled pool and passes statistical coverage thresholds, use that trusted evidence to synthesize coverage cases.
- If the semantic match is good but trusted support is too thin, request more trusted examples before relying on synthetic expansion.
- If the intent has missing or weak labels, do not synthesize labels for it yet. Route representative examples to application feedback prompts, annotation queues, or SME review.

This prevents the workflow from inventing correctness criteria for intents where the application only knows that users ask the question, not what a good answer should look like.

The generic gate emits these statuses:

| Status | Meaning | Next Action |
|---|---|---|
| `matched_trusted_intent` | The unlabeled cluster matches trusted labeled evidence and meets support thresholds | Proceed to label inference and, when enabled, optional synthetic coverage |
| `needs_more_trusted_examples` | The cluster appears to match an intent, but trusted examples are statistically thin for the cluster volume | Request targeted feedback or SME review for representative examples |
| `missing_or_weak_labels` | No trusted intent match is strong enough | Request feedback or SME review before synthesis |

Coverage thresholds are tenant-configurable. Useful knobs include:

- Minimum semantic match score. Evaluation assets default to `0.6`, and the
  Studio and `assets create` CLI both persist the selected value.
- Minimum trusted examples for any matched intent.
- Minimum trusted groups or conversations for any matched intent.
- Higher trusted-example minimum for large unlabeled clusters.
- Maximum unlabeled-to-trusted ratio, such as requiring at least one trusted example for every 20 unlabeled examples in a high-volume intent.

Trusted intent records may carry support statistics in `metadata`:

```json
{
  "intent_id": "intent-family-id",
  "label": "human readable intent label",
  "texts": ["trusted example or rubric summary"],
  "route": "task_family",
  "metadata": {
    "trusted_example_count": 12,
    "trusted_group_count": 5
  }
}
```

If those counts are absent, the shared utility uses `len(texts)` as the trusted-example count and treats trusted group count as `0`.

## Stage 4 Clustering and Stage 5 Matching

The core uses the following deterministic mechanics:

1. Stage 2 builds `canonical_intent_text` from `user_input`, the latest
   conversation-context text, and observed tool names. It preserves the
   supplied `route`, defaulting it to `task_type` only when omitted.
2. Stage 4 vectorizes that canonical text with the configured OpenAI embedding
   model or the explicit local TF-IDF fallback.
3. The requested cluster count is allocated across routes, with at least one
   cluster per distinct route. The count must not exceed the number of records
   and must be at least the number of routes.
4. Deterministic cosine k-means clusters records within each route and records
   member IDs, representative IDs, and top terms in `intent_inventory.jsonl`.
5. Stage 5 builds comparable text for clusters and trusted intents, vectorizes
   it with the same configured provider, chooses the best same-route trusted
   match by cosine similarity, and applies the configured coverage policy.

Stage 5 does not call an LLM and has no manual review checkpoint. Its output is
the persisted coverage decision. Stage 6 uses the configured rubric LLM only
for clusters whose Stage 5 status is `matched_trusted_intent`.

This asset creation step is not a FAPO eval run. It produces versioned datasets and coverage reports that the FAPO optimization loop consumes afterward.

Recommended generic artifacts:

| Artifact | Purpose |
|---|---|
| `intent_inventory.jsonl` | Cluster records with representative IDs, top terms, route, and size |
| `intent_matches.jsonl` | Coverage decisions: matched trusted intent or missing/weak labels |
| `coverage_report.md` | Human-readable summary of high-volume clusters, trusted coverage, and feedback requests |
| `dataset_manifest.json` | Dataset version, split files, oracle version, and generation settings |
| FAPO JSONL split files | Versioned train, validation, test, and regression datasets |

## Core Pipeline Contract

The shared pipeline parses `fapo-evaluation-input-v1` directly. No source field
mappings are stored in the asset configuration and no tenant code is imported.
The core owns contract validation, redaction, rubric extraction, exact-count
clustering, coverage decisions, inferred labels, group-safe splits, manifests,
checkpoints, and progress events.

Each asset contains:

| Directory | Contents |
|---|---|
| `raw_inputs/` | Immutable copied labeled and unlabeled JSONL plus source hashes |
| `prepared_inputs/` | Normalized feedback, canonical intents, trusted cases, inferred cases |
| `decision_assets/` | Rubrics, clusters, match decisions, coverage and missing-label reports |
| `dataset_splits/` | Component and combined train, validation, test, regression, and triage files |

## CLI Workflow

Create a self-contained workspace:

```bash
python -m hephaestus.cli assets create \
  --tenant <tenant_id> \
  --asset-id <asset_id> \
  --feedback <feedback.jsonl> \
  --unlabeled <unlabeled.jsonl> \
  --rubric-model gpt-5.5 \
  --embedding-model text-embedding-3-small \
  --clusters 50 \
  --match-threshold 0.6 \
  --enable-synthetic-coverage \
  --synthetic-cases-per-cluster 2
```

Omit `--enable-synthetic-coverage` to use only trusted and inferred real cases.
The per-cluster count is persisted but ignored while Stage 7 is disabled.

For a local embedding fallback, set `--embedding-model tfidf`. Asset creation
will persist both the TF-IDF provider and model selection:

```bash
python -m hephaestus.cli assets create \
  --tenant <tenant_id> \
  --asset-id <asset_id> \
  --feedback <feedback.jsonl> \
  --unlabeled <unlabeled.jsonl> \
  --rubric-model gpt-5.5 \
  --embedding-model tfidf \
  --clusters 50 \
  --match-threshold 0.6 \
  --enable-synthetic-coverage \
  --synthetic-cases-per-cluster 2
```

Run or resume the core stages:

```bash
python -m hephaestus.cli assets run \
  --tenant <tenant_id> \
  --asset-id <asset_id>
```

Read progress while a CLI or Explorer-triggered run is active:

```bash
python -m hephaestus.cli assets status \
  --tenant <tenant_id> \
  --asset-id <asset_id>
```

The Explorer UI calls the same core service. Completed stages are persisted and
skipped on resume; model settings and the fixed cluster count are recorded in
the asset manifest.

## Synthetic Coverage Cases

Synthetic examples should expand known, trusted intents rather than define new unlabeled intents.

Generation should use:

- Trusted rubrics or deterministic checks for correctness criteria.
- Unlabeled intent clusters for realistic phrasing, context shape, workflow frequency, and tool-use patterns.

Filtering should remove synthetic cases that are:

- Invalid FAPO JSONL.
- Missing concrete, scoreable criteria.
- Inconsistent with tenant domain, tool context, or available fields.
- Near-duplicates of existing cases.
- Leaky, meaning expected answers or feedback rationale appear in runtime `context`.
- Unsolvable from the provided context.

Filtered synthetic examples may be assigned to training, validation, and test
splits for the dataset version. They are never added to
`regression_trusted`, which is sourced automatically from trusted feedback.

## Prepared Feedback Record

Stage 2 converts the fixed evaluation input contract into an internal,
redacted feedback record. It preserves the canonical identity fields
`record_id` and `group_id`; no internal aliases are introduced:

```json
{
  "schema_version": "fapo-evaluation-input-v1",
  "record_id": "stable-id",
  "group_id": "stable-group-id",
  "request_id": "stable-request-id",
  "task_type": "tenant-defined-task-type",
  "route": "tenant-defined-task-type",
  "user_input": "...",
  "conversation_context": [],
  "assistant_output": "...",
  "tool_calls": [],
  "feedback": {
    "polarity": "positive",
    "rationale": "...",
    "correction": null,
    "source": "user"
  },
  "runtime": {
    "application_version": "...",
    "model": "...",
    "tools_available": []
  },
  "metadata": {}
}
```

The prepared record is not the eval dataset yet. It is an internal redacted
format used for rubric extraction, adjudication, and auditability.

## Oracle Construction

Construct `expected` from the strongest available source:

1. **Human correction**: Use a corrected answer, accepted edited query, or SME-approved artifact as the highest-trust reference.
2. **Deterministic oracle**: Use tool schema constraints, parser checks, policy checks, syntax checks, and output format checks when they can decide correctness without another model.
3. **Feedback rationale rubric**: Convert user rationale into explicit pass/fail criteria. The evaluation-asset pipeline accepts this extraction directly as trusted feedback evidence without a separate review gate.
4. **Positive exemplar**: For positive feedback, preserve behavior as a non-regression expectation only after checking that the response is safe, grounded, and not merely pleasant.
5. **LLM judge**: Use only as a calibrated scorer component. The judge should compare a new response to the rubric and evidence, not to the previous assistant output alone.

Avoid exact-answer labels when the task has many valid outputs. Prefer rubric, invariants, and tool-behavior expectations.

## FAPO Case Shape

Write unified JSONL cases using the existing FAPO schema:

```json
{
  "case_id": "feedback-000001",
  "task_type": "tenant-defined-task-type",
  "context": {
    "messages_json": "...",
    "tool_context_json": "...",
    "runtime_json": "..."
  },
  "expected": {
    "label_source": "human_feedback",
    "confidence": 0.9,
    "feedback_polarity": "negative",
    "failure_modes": ["wrong_tool_behavior"],
    "rubric": {
      "must": [],
      "must_not": [],
      "should": []
    },
    "reference_output": null,
    "tool_expectations": {},
    "deterministic_checks": []
  },
  "metadata": {
    "source": "feedback_trace",
    "split": "validation_trusted",
    "dataset_version": "v1",
    "group_id": "stable-group-id",
    "request_id": "stable-request-id",
    "oracle_version": "v1"
  }
}
```

Do not put the feedback rationale in `context` unless the production chain will also receive that rationale at runtime. Feedback belongs in `expected` and `metadata`, where the scorer can use it but the optimized chain cannot see it.

## Filtering Rules

Reject or hold cases when:

- Feedback polarity conflicts with the written rationale.
- The user reports a problem but gives no actionable reason and there is no deterministic failure signal.
- The trace lacks enough context to reproduce the request.
- The assistant output contains private data that cannot be redacted without changing the task.
- The previous response is positively rated but violates safety, policy, grounding, or tool constraints.
- Multiple turns in the same thread would leak nearly identical context across train and validation/test.

## Splitting Rules

- Assign train, validation, and test globally by canonical `group_id`, not
  separately by provenance or individual row.
- Deduplicate semantically before splitting.
- Keep corrected negative cases in train only after the oracle is clear enough to score.
- Keep validation and test examples out of prompt/skill authoring context during optimization.
- Assign filtered synthetic examples to training, validation, and test as part of a named dataset version.
- Automatically reserve a deterministic, group-safe 20% of trusted feedback
  cases for `regression_trusted` before splitting the remaining trusted pool.
- Route inferred or synthetic cases whose `group_id` is reserved for regression
  to `triage_hold`.
- Record dataset version and split membership so eval scores are compared only within compatible dataset versions.

## Scoring Pattern

Tenant scorers should combine:

- Deterministic checks for schema, parser validity, required fields, unsafe patterns, and tool-call invariants.
- Tool-trajectory checks for agentic chains, using `tool_call_history` when available.
- Reference or rubric scoring for the final response.
- Optional calibrated LLM judge scoring for criteria that cannot be checked mechanically.

Each scorer must still return numeric `score_breakdown` values from 0 to 100 and a 0 to 100 `composite_score`.

Recommended score keys:

- `task_success`
- `feedback_issue_resolved`
- `tool_behavior`
- `grounding`
- `format`
- `safety`

## Downstream Use and Refresh

The eight-stage pipeline ends when the evaluation asset and its dataset splits
are complete. FAPO can then consume the asset in a separate lifecycle:

1. Run baseline evaluations against the new dataset version.
2. Optimize prompts or skills using its training split.
3. Apply validation, regression, and test gates before promotion.
4. Record the asset version and promotion decision with the optimization run.
5. When new trusted feedback or unlabeled traffic should be incorporated,
   create a new evaluation-asset version and run the same eight stages again.

## Guardrails

- Do not optimize directly against unresolved user complaints.
- Do not use old assistant output as the sole target.
- Do not leak feedback rationale into runtime context.
- Do not mix rows from the same thread across train, validation, and test.
- Do not synthesize labels for intents that do not match trusted labeled evidence.
- Keep inferred and synthetic cases out of `regression_trusted`; the core
  selects that gate automatically from trusted feedback.
- Do not commit raw feedback traces or local generated datasets unless the tenant workflow explicitly allows it.
