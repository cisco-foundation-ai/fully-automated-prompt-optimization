<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Evaluation Asset Assistant for Codex

Use this phase when the user wants Codex to create, monitor, review, or release
an evaluation asset. The shared FAFO core owns pipeline logic. The agent is an
operator and reviewer: it creates the workspace, triggers the core runner,
polls persisted progress, checks artifacts, diagnoses failures, explains stage
decisions, guides review and finalization, and reports results.

Before operating the workflow, read
`docs/processes/feedback-dataset-flow.md`, especially **Step-by-Step Flow**,
**Provider Selection**, and **Inspect and finalize**. Also read
`docs/processes/evaluation-input-contract.md`. For the workspace layout,
lifecycle, recovery, and full CLI, use `docs/references/evaluation-assets.md`.

## Boundaries

- Do not implement the workflow in a tenant adapter or agent prompt.
- Do not transform, label, cluster, split, synthesize, or review-decide records
  outside the core CLI or API.
- Do not read tenant docs, prompts, chains, or configs to make the core run.
- Do not use `tenants/<tenant_id>/datasets/` for evaluation-asset intermediate
  outputs. Stage 8 alone publishes consumer-facing splits under
  `datasets/evaluation_assets/<asset_id>/`.
- Do not put tenant data in shared repo locations.
- Do not treat previous assistant output as ground truth.
- Do not treat clusters as correctness evidence; clustering is optional
  sampling and analysis metadata.
- Do not ask the user to populate `regression_trusted`. Stage 2 assigns about
  20% of trusted connected groups to it from the split seed; derived cases never
  enter it.
- Do not edit `config.json`, `pipeline_state.json`, receipts, review files, or
  `release.json` by hand.
- Do not silently substitute models or embedding providers after a failure.
- Do not use an LLM or subagent to execute transformations owned by the core.
- Do not expose whole tenant JSONL files merely to provide an example; use one
  bounded record and preserve tenant-data boundaries.
- Do not add vendor or tenant field-name mappings to the core. Both source
  files must already conform to `fafo-evaluation-input-v1`.

## Canonical Workspace

Every asset is self-contained at:

```text
tenants/<tenant_id>/evaluation_assets/<asset_id>/
├── config.json
├── config_history.jsonl
├── pipeline_state.json
├── events.jsonl
├── recovery_journal.jsonl
├── receipts/
├── reviews/
│   ├── decisions.jsonl
│   └── finalizations.jsonl
├── lineage.json                 # extended versions only
├── reuse_manifest.json          # extended versions only
├── asset_manifest.json
└── stages/
    ├── 01_raw_inputs/
    ├── 02_prepared_inputs/
    ├── 03_evaluation_guidelines/
    ├── 04_intent_clustering/
    ├── 05_coverage_decisions/
    ├── 06_label_inference/
    ├── 07_synthetic_coverage/
    └── 08_dataset_splits/
```

The core copies source JSONL files into `stages/01_raw_inputs/` before
execution. Each stage owns only its outputs and reads earlier stage folders.
After creation, no stage may depend on the original source path or other tenant
files. Released splits are published as an immutable generation under
`tenants/<tenant_id>/datasets/evaluation_assets/<asset_id>/`, with
`release.json` as the only mutable pointer.

## Core Stage Map

Treat these exact ordered stage names as the runtime contract:

| Stage | Operation | Main artifacts |
|---|---|---|
| `raw_inputs` | Copy, validate, count, and hash both sources | Copied source JSONL, input manifest |
| `prepared_inputs` | Redact, normalize, derive split-isolation groups, assign trusted splits, assess feedback eligibility, build intent text | `normalized_feedback.jsonl`, `intent_records.jsonl`, `trusted_split_plan.jsonl`, `feedback_eligibility.jsonl` |
| `rubric_extraction` | Evidence-backed guidelines from eligible training feedback only; held-out guidance compiled separately as protected artifacts | `feedback_evidence.jsonl`, `candidate_guidelines.jsonl`, `evaluation_guidelines.jsonl`, `protected_*` files in `stages/03_evaluation_guidelines/` |
| `intent_clustering` | Optional clustering of unlabeled intent text for sampling and analysis; empty when `--clusters 0` | `intent_inventory.jsonl` |
| `coverage_decisions` | Optional cluster sampling context only; no matching, support, or correctness decisions | `cluster_sampling_metadata.jsonl` |
| `label_inference` | One rubric-generation call per episode with the full split-permitted catalog; trace-inferred rubric when no guideline applies | `episode_rubrics.jsonl`, `trusted_cases.jsonl`, `inferred_cases.jsonl`, `case_dependencies.jsonl`, held outputs |
| `synthetic_coverage` | Optional synthetic proposals and mechanical filters, then duplicate families, fingerprinted review items, automatic approval of scoreable derived cases, and the review snapshot; pauses at `awaiting_review` | Synthetic artifacts, `derived_review_items.jsonl`, `duplicate_families.jsonl`, `review_snapshot.json` |
| `dataset_splits` | After explicit finalization only: publish trusted plus approved derived cases as an immutable generation | `dataset_manifest.json`, published generation with `generation_manifest.json` |

The persisted Stage 3 name stays `rubric_extraction`; its directory is
`03_evaluation_guidelines`. The top-level status is exactly `draft`, `queued`,
`running`, `awaiting_review`, `released`, or `failed`. `pipeline_state.json` is
authoritative for status and counts; `events.jsonl` is the audit trail. Do not
infer completion only from the presence of one output file.

## Operator Workflow

1. Collect:
   - tenant ID and asset ID/version (default `v1`)
   - labeled feedback and unlabeled JSONL paths beneath the tenant's
     `source_artifacts/` or ordinary `datasets/` directory
   - guideline/rubric model (default `gpt-6-luna`)
   - embedding model (default `text-embedding-3-small`), or `tfidf` for local
     vectorization
   - cluster count (default `50`; `0` skips Stages 4 and 5)
   - whether Stage 7 synthetic coverage is enabled (default disabled) and, if
     so, synthetic cases per cluster; synthetic coverage requires clusters
   - confirmation that both JSONL files use `fafo-evaluation-input-v1`
2. Create the workspace through the core CLI:

   ```bash
   python -m hephaestus.cli assets create \
     --tenant <tenant_id> \
     --asset-id <asset_id> \
     --feedback <feedback.jsonl> \
     --unlabeled <unlabeled.jsonl> \
     --rubric-model gpt-6-luna \
     --embedding-model text-embedding-3-small \
     --clusters <count>
   ```

   Add `--enable-synthetic-coverage --synthetic-cases-per-cluster <count>` only
   when synthetic expansion is wanted. For local vectorization, use
   `--embedding-model tfidf` and confirm `config.json` records
   `embedding_provider: tfidf` and `embedding_model: tfidf`. TF-IDF makes no
   embedding API calls.

3. Trigger the core pipeline. A normal run returns after Stage 7 with status
   `awaiting_review`:

   ```bash
   python -m hephaestus.cli assets run --tenant <tenant_id> --asset-id <asset_id>
   ```

4. Poll persisted progress from a separate command or turn:

   ```bash
   python -m hephaestus.cli assets status --tenant <tenant_id> --asset-id <asset_id>
   ```

5. Review the bounded snapshot and record both fingerprints:

   ```bash
   python -m hephaestus.cli assets reviews list --tenant <tenant_id> --asset-id <asset_id>
   ```

   Scoreable inferred cases and mechanically accepted synthetic cases are
   already approved. `assets reviews approve` and `assets reviews reject` remain
   for pending items, each with the exact case fingerprint and the current
   review-set fingerprint. Report held items and why they are held.
6. Finalize only when the user agrees with the snapshot; this runs Stage 8:

   ```bash
   python -m hephaestus.cli assets reviews finalize \
     --tenant <tenant_id> --asset-id <asset_id> \
     --reviewer <reviewer_name> \
     --review-set <sha256:review_set_fingerprint> \
     --decision-set <sha256:decision_set_fingerprint>
   ```

   Finalization does not approve pending items or publish held or rejected
   cases.

7. If a run fails, inspect `pipeline_state.json` and `events.jsonl`. Resume
   unchanged when a decision was not the cause. When the user explicitly
   changes a decision, pass only the changed settings as optional `assets run`
   flags. The core records `config_history.jsonl`, invalidates the earliest
   affected stage and all downstream stages, and preserves earlier checkpoints.
   Never edit `config.json` or stage statuses manually.
8. When released, verify:
   - the top-level status is `released` and all stages are `completed`
   - source hashes exist
   - guideline and embedding model settings match the request
   - the cluster count matches the request when clustering is enabled
   - `release.json`, `asset_manifest.json`, and the Stage 8
     `dataset_manifest.json` agree on the generation, and its
     `generation_manifest.json` hashes match the published files
   - the published train, validation, test, and `regression_trusted` files
     load; no `group_id` crosses train, validation, or test; held items are
     absent
   - the manifests' `review` block counts match the finalized snapshot

## Incremental Asset Extension

A released asset is immutable. Create a child version with `assets extend`;
never append to the parent's raw inputs.

- Use `--clustering-mode keep` for labeled additions only; it preserves the
  parent's clustering plan.
- Use `--clustering-mode refresh` with additional feedback and/or unlabeled
  records (`--additional-unlabeled`). Verify Stage 4 reclustered the combined
  pool and wrote `cluster_lineage.jsonl`.
- Parent split assignments are inherited; a record that bridges incompatible
  parent splits fails closed.
- Added feedback can legitimately regenerate episode rubric dependencies even
  with `keep`, because Stage 6 sees the complete permitted catalog.
- Confirm `lineage.json` and `reuse_manifest.json` name the correct parent and
  added record IDs, and that `stages/01_raw_inputs/parent_snapshot/` holds the
  hashed parent decisions the child needs; the child must remain runnable
  without reading the live parent directory.
- A child inherits a parent review decision only when the review fingerprint
  and canonical case bytes are identical; anything changed returns to pending.
- Treat the child as a complete self-contained asset; downstream consumers must
  not need to join it with the parent.

Assets from older builds may carry the legacy status `completed`, which is not
`released`. Adopt such an asset with
`python -m hephaestus.cli assets adopt --tenant <tenant_id> --asset-id <asset_id>`
before extending it.

## Provider Rules

- Default guideline/rubric model: OpenAI `gpt-6-luna`. Other OpenAI models can
  be selected with `--rubric-model`. Do not assume account access; report
  authorization or model-availability errors verbatim.
- Default embedding model: OpenAI `text-embedding-3-small`. Other OpenAI
  choices are `text-embedding-3-large` and legacy `text-embedding-ada-002`.
- Local option: `tfidf`, which uses deterministic lexical vectors for
  clustering.
- A provider fallback must be explicitly selected by the user. Never change an
  existing asset's persisted model/provider to make a failed run continue.

## OpenAI SSL Troubleshooting

When the underlying provider error specifically reports SSL/TLS certificate
verification or a blocked trust chain:

1. Tell the user to run this command in the environment used by FAFO:

   ```bash
   python3 -m pip install --upgrade openai httpx certifi truststore
   ```

2. Check whether the `truststore.inject_into_ssl()` blocks are commented. If
   so, uncomment them in:
   - `src/hephaestus/providers/openai.py`
   - `src/hephaestus/datasets/rubric_providers.py`
   - `src/hephaestus/datasets/embedding_providers.py`
3. Restart the FAFO CLI or service process, then resume the asset. Confirm
   completed stages remain complete and the first incomplete stage restarts.

Do not recommend this procedure for invalid credentials, unavailable models,
rate limits, or malformed model output. The blocks may already be uncommented;
do not edit them again when they are active.

## Monitoring and Assistance

- Poll `assets status` or read `pipeline_state.json`; do not repeatedly invoke
  `assets run` while the same asset is already running.
- Explain the current stage in terms of its inputs, operation, outputs, and
  trust boundary. Stage 3 guidelines come only from eligible training feedback
  and link each claimed mistake or success to the feedback and an observable
  trace location. Stage 6 writes one rubric per scoreable episode, selecting
  zero or more guidelines or inferring the rubric from the trace.
- When clustering is enabled, verify the produced count equals the requested
  count, and that sampling metadata carries no correctness decision.
- For failed runs, classify the cause as credentials/model access, source
  contract, invalid cluster count, provider/API failure, or core defect before
  proposing an action.
- If input data is vendor-shaped, stop before running. Require a source adapter
  to emit the canonical contract; do not guess nested paths downstream.
- Resume only after the cause is corrected. Verify completed stages remained
  completed and the first incomplete stage restarted.
- For a resume-time decision change, verify the restart boundary: split seed at
  Stage 2; guideline model at Stage 3; embedding model or cluster count at
  Stage 4; synthetic settings at Stage 7. Confirm the revision appears in both
  `config_history.jsonl` and `events.jsonl`. Legacy matching/support settings
  remain readable but do not affect rubric generation.
- There is no evaluation-asset UI. FAFO Explorer (`python -m hephaestus.cli ui`)
  is a read-only view of tenant runs; the same local server exposes a
  same-origin JSON API for evaluation assets (see `docs/web-ui.md`).
- In reports, show one bounded example per artifact rather than an entire file.

## Reporting

Report:

- tenant and asset ID
- workspace path and current status
- final or current stage
- provider/model settings
- counts for feedback, unlabeled records, guidelines, episode rubrics, trusted,
  inferred, and synthetic cases, approved/pending/held items, clusters (when
  enabled), and published splits
- the published generation ID and paths, once released
- any failed stage and its persisted error
- the next human decision: review, finalization, or a fix

The JSON API uses the same core service and filesystem state as the CLI. It is
valid to start a run through the API and monitor it through the CLI, or vice
versa.
