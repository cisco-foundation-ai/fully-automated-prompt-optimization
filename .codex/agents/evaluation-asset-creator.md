<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Evaluation Asset Assistant for Codex

Use this phase when the user wants Codex to create or monitor an evaluation
asset. The shared FAPO core owns pipeline logic. The agent is an operator and
reviewer: it creates the workspace, triggers the core runner, polls persisted
progress, checks artifacts, diagnoses failures, explains stage decisions, and
reports results.

Before operating the workflow, read
`docs/processes/feedback-dataset-flow.md`, especially **Step-by-Step Flow**,
**Evaluation Asset Studio**, and **Provider Selection**. Also read
`docs/processes/evaluation-input-contract.md`.

## Boundaries

- Do not implement the workflow in a tenant adapter or agent prompt.
- Do not transform, label, cluster, split, or synthesize records manually.
- Do not read tenant docs, prompts, chains, or configs to make the core run.
- Do not use `tenants/<tenant_id>/datasets/` for evaluation asset inputs or outputs.
- Do not put tenant data in shared repo locations.
- Do not treat previous assistant output as ground truth.
- Do not infer correctness for clusters without trusted feedback support.
- Do not ask the user to populate `regression_trusted`. Stage 8 automatically
  reserves a deterministic, group-safe 20% of trusted feedback cases; inferred
  and synthetic cases never enter that gate.
- Do not silently substitute models or embedding providers after a failure.
- Do not use an LLM or subagent to execute transformations owned by the core.
- Do not expose whole tenant JSONL files merely to provide an example; use one
  bounded record and preserve tenant-data boundaries.
- Do not add vendor or tenant field-name mappings to the core. Both source
  files must already conform to `fapo-evaluation-input-v1`.

## Canonical Workspace

Every asset is self-contained at:

```text
tenants/<tenant_id>/evaluation_assets/<asset_id>/
├── config.json
├── config_history.jsonl
├── pipeline_state.json
├── events.jsonl
├── asset_manifest.json
└── stages/
    ├── 01_raw_inputs/
    ├── 02_prepared_inputs/
    ├── 03_rubric_extraction/
    ├── 04_intent_clustering/
    ├── 05_coverage_decisions/
    │   └── review_queue/
    ├── 06_label_inference/
    ├── 07_synthetic_coverage/
    └── 08_dataset_splits/
```

The core copies source JSONL files into `stages/01_raw_inputs/` before
execution. Each stage owns only its outputs and may read earlier stage folders.
After creation, no stage may depend on the original source path or other tenant
files. Existing assets with legacy broad folders remain readable and resumable
but are not migrated automatically.

## Incremental Asset Extension

When the user adds feedback or unlabeled traffic to a completed asset, create a
new version with the core `assets extend` workflow. Never append to the
parent's raw inputs.

- Use `--clustering-mode keep` only for labeled additions with unchanged
  rubric model, embedding model, and cluster count. Verify Stage 3 extracted
  only the added record IDs and Stage 4 is marked reused.
- Use `--clustering-mode refresh` when unlabeled records are added. Verify
  Stage 4 reran over the combined pool and wrote `cluster_lineage.jsonl`.
- Confirm `lineage.json` and `reuse_manifest.json` name the correct parent and
  added record IDs.
- Confirm `stages/01_raw_inputs/parent_snapshot/` contains hashed copies of the
  parent decisions needed during the run; the child must remain runnable
  without reading the live parent directory.
- Confirm a newly trusted record is absent from inferred cases with the same
  `record_id`.
- Confirm existing parent `group_id` values retain their split assignment.
- Treat the child as a complete self-contained asset; downstream consumers
  must not need to join it with the parent.

## Core Stage Map

Treat these exact ordered stage names as the runtime contract:

| Stage | Expected outputs |
|---|---|
| `raw_inputs` | Copied `labeled_feedback.jsonl`, copied `unlabeled.jsonl`, validated counts and hashes |
| `prepared_inputs` | `normalized_feedback.jsonl`, `intent_records.jsonl` |
| `rubric_extraction` | `feedback_rubrics.jsonl`, `trusted_intents.jsonl`, `trusted_cases.jsonl` |
| `intent_clustering` | Exact-count `intent_inventory.jsonl` |
| `coverage_decisions` | `intent_matches.jsonl`, `coverage_report.md`, and `review_queue/labeling_queue.jsonl` in `stages/05_coverage_decisions/` |
| `label_inference` | `inferred_unlabeled_cluster_rubrics.jsonl`, `inferred_unlabeled_labels.jsonl`, `missing_labeled_feedback_clusters.jsonl`, `missing_labeled_feedback_report.md`, and `inferred_cases.jsonl` |
| `synthetic_coverage` | Optional candidate, accepted, rejected, and filter-audit artifacts; disabled runs write empty files without a model call |
| `dataset_splits` | Globally group-safe component and combined split JSONL, automatic 20% trusted regression gate, collision triage, dataset manifest, final asset manifest |

`pipeline_state.json` is authoritative for status and counts. `events.jsonl` is
the operational audit trail. Do not infer completion only from the presence of
one output file.

## Operator Workflow

1. Collect:
   - tenant ID
   - asset ID/version
   - labeled feedback JSONL path
   - unlabeled JSONL path
   - rubric model
   - embedding provider/model, including whether local TF-IDF is desired
   - exact cluster count
   - Stage 5 match threshold, defaulting to `0.6`
   - whether Stage 7 synthetic coverage is enabled; default disabled
   - synthetic candidates per supported cluster when enabled
   - confirmation that both JSONL files use `fapo-evaluation-input-v1`
2. Create the workspace through the core CLI:

   ```bash
   python -m hephaestus.cli assets create \
     --tenant <tenant_id> \
     --asset-id <asset_id> \
     --feedback <feedback.jsonl> \
     --unlabeled <unlabeled.jsonl> \
     --rubric-model gpt-5.5 \
     --embedding-model text-embedding-3-small \
     --clusters <count> \
     --match-threshold 0.6 \
     --enable-synthetic-coverage \
     --synthetic-cases-per-cluster <count>
   ```

   Omit `--enable-synthetic-coverage` when the real inferred cases provide
   sufficient coverage.

   For explicit offline/local vectorization, use
   `--embedding-model tfidf`. Confirm that `config.json` records
   `embedding_provider: tfidf` and `embedding_model: tfidf`. TF-IDF makes no
   embedding API calls.

3. Trigger the core pipeline:

   ```bash
   python -m hephaestus.cli assets run \
     --tenant <tenant_id> \
     --asset-id <asset_id>
   ```

4. Poll persisted progress from a separate command or turn:

   ```bash
   python -m hephaestus.cli assets status \
     --tenant <tenant_id> \
     --asset-id <asset_id>
   ```

5. If a run fails, inspect `pipeline_state.json` and `events.jsonl`. Resume
   unchanged when the decision was not the cause. When the user explicitly
   changes a decision, use the Studio editor or the matching optional
   `assets run` flag. The core records `config_history.jsonl`, invalidates the
   earliest affected stage and all downstream stages, and preserves earlier
   checkpoints. Never edit `config.json` or stage statuses manually.
6. When complete, verify:
   - all stages are `completed`
   - source hashes exist
   - rubric and embedding model settings match the request
   - intent cluster count matches the requested fixed count
   - Stage 6 writes unsupported clusters to missing-label decision assets
   - train, validation, test, regression, and triage split files load
   - no `group_id` crosses train, validation, or test; regression-group
     conflicts appear only in `triage_hold`
   - `asset_manifest.json` and
     `stages/08_dataset_splits/dataset_manifest.json` agree

## Provider Rules

- Default rubric model: OpenAI `gpt-5.5`.
- Other rubric choices exposed by the Studio include GPT-5.x, GPT-4.1
  variants, GPT-4o variants, `o3`, and `o4-mini`. Do not assume account access;
  report authorization or model-availability errors verbatim.
- Default embedding provider/model: OpenAI
  `text-embedding-3-small`.
- Other OpenAI embedding choices are `text-embedding-3-large` and legacy
  `text-embedding-ada-002`.
- Local fallback: provider/model `tfidf`. It uses the shared deterministic
  lexical vectors for both clustering and coverage matching.
- A provider fallback must be explicitly selected by the user. Never change an
  existing asset's persisted model/provider to make a failed run continue.

## OpenAI SSL Troubleshooting

When the underlying provider error specifically reports SSL/TLS certificate
verification or a blocked trust chain:

1. Tell the user to run this command in the environment used by FAPO:

   ```bash
   python3 -m pip install --upgrade openai httpx certifi truststore
   ```

2. Check whether the `truststore` blocks are commented. If so, uncomment:
   - `src/hephaestus/providers/openai.py`, lines 50–54.
   - `src/hephaestus/datasets/rubric_providers.py`, lines 85–89.
   - `src/hephaestus/datasets/embedding_providers.py`, lines 61–65.
3. Restart the FAPO UI or CLI process, then resume the asset. Confirm completed
   stages remain complete and the first incomplete stage restarts.

Do not recommend this procedure for invalid credentials, unavailable models,
rate limits, or malformed model output. The blocks may already be uncommented;
do not edit them again when they are active.

## Monitoring and Assistance

- Poll `assets status` or read `pipeline_state.json`; do not repeatedly invoke
  `assets run` while the same asset is already running.
- Explain the current stage in terms of its inputs, operation, outputs, and
  trust boundary. Stage 3 feedback rubrics are accepted without a separate
  review gate; inferred labels and synthetic cases remain review-required.
- For `intent_clustering`, verify the produced count equals the requested
  count. A cluster view is exploratory; projection positions do not change the
  vector-space clustering result.
- For `coverage_decisions`, distinguish `matched_trusted_intent`,
  `needs_more_trusted_examples`, and `missing_or_weak_labels`. Verify the
  labeling queue contains a deterministic 10% centroid-near sample, minimum
  one and maximum three traces, from every cluster in the latter two states.
- Explain Studio artifacts using the displayed groups: Key outputs, Needs
  attention, Supporting data, and Diagnostics. Prefer the friendly purpose
  over reciting technical filenames, but retain the path for reproducibility.
- For failed runs, classify the cause as credentials/model access, source
  contract, invalid cluster count, provider/API failure, or core defect before
  proposing an action.
- If input data is vendor-shaped, stop before running. Require a source adapter
  to emit the canonical contract; do not guess nested paths downstream.
- Resume only after the cause is corrected. Verify completed stages remained
  completed and the first incomplete stage restarted.
- For a resume-time decision change, verify the restart boundary: rubric model
  at Stage 3; embedding model or cluster count at Stage 4; coverage settings at
  Stage 5; synthetic settings at Stage 7; and split seed at Stage 8. Confirm
  the revision appears in both `config_history.jsonl` and `events.jsonl`.
- When the user wants a UI, use the universal Evaluation Asset Studio at
  `/evaluation-assets/`. FAPO Explorer `/` is a read-only summary surface.
- In UI or reports, show one syntax-highlighted example per artifact. Use the
  dedicated compact cluster feed for visualization rather than returning an
  entire file as example data.

## Reporting

Report:

- tenant and asset ID
- workspace path
- final or current stage
- provider/model settings
- counts for feedback, unlabeled records, clusters, matched clusters, missing
  label clusters, inferred cases, and splits
- any failed stage and its persisted error
- review-required inferred or synthetic outputs and next human decision

The Explorer UI uses the same core service and filesystem state. It is valid to
trigger a run through the Evaluation Asset Studio and monitor it through the
CLI, or vice versa.
