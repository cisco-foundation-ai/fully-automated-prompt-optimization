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
  but only after an intent coverage gate passes. Scoreable inferred and
  mechanically accepted synthetic cases are approved automatically.
- Synthetic examples are proposed only for intents matched to trusted labeled
  evidence. Synthetic coverage is disabled by default; when enabled, cases
  that pass Stage 7's mechanical checks are automatically approved.

## Product and Execution Model

Evaluation asset creation is a tenant-bootstrap workflow implemented by shared
core code under `src/hephaestus/evaluation_assets/`. It does not require an
existing tenant chain, prompt, config, adapter, dataset, or documentation.

The workflow has three entry points backed by the same persisted state:

| Entry point | Use |
|---|---|
| Evaluation Asset Studio at `/evaluation-assets/` | Create assets, choose models, cluster count, and match threshold, inspect every pipeline stage, preview safe artifacts, monitor progress, review derived cases, finalize publication, and resume failures |
| `python -m hephaestus.cli assets ...` | Scriptable create, run/resume, status, fingerprint-bound review, finalization, verified extension, and explicit legacy adoption |
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

Canonical JSONL files must be regular files beneath the selected tenant's
`source_artifacts/` or ordinary `datasets/` directory. The core rejects other
tenants, workspace-external files, symlink escapes, non-JSONL inputs, and
generated `datasets/evaluation_assets/` outputs before it creates an asset
workspace. It validates the input contract before copying the files into:

`tenants/<tenant_id>/evaluation_assets/<asset_id>/stages/01_raw_inputs/`

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
  - Optional declared deterministic/executable correctness signals with stable
    check IDs and boolean outcomes.
  - Human or SME review state, if available.
- Unlabeled production traces:
  - High-volume application logs without correctness labels.
  - Tool trajectories and tool results, when available.
  - Runtime metadata needed for grouping and deduplication, such as thread ID, request ID, app version, model, and enabled tool set.

Shared repo docs and tests must not include tenant-specific trace content, tenant IDs, or real customer examples.

## Step-by-Step Flow

Asset creation has exactly eight ordered stages. Each numbered folder owns the
outputs of its corresponding stage and reads inputs from earlier folders.
Creating the asset workspace copies the two source files into
`stages/01_raw_inputs/`; Stage 1 then validates those copies. FAPO evaluation,
optimization, and prompt promotion happen only after this pipeline completes
and are not additional evaluation-asset stages.

| Stage | Inputs | What happens | Outputs |
|---|---|---|---|
| 1. `raw_inputs` — Validate raw inputs | Copied `labeled_feedback.jsonl` and `unlabeled.jsonl` | Reject empty inputs; revalidate every copied record against `fapo-evaluation-input-v1` while retaining physical JSONL line numbers across blank lines; require feedback only on labeled records; reject cluster counts that exceed unlabeled rows or cannot allocate at least one cluster to every exact effective route; count rows and calculate source hashes. These checks finish before any provider call | `stages/01_raw_inputs/` |
| 2. `prepared_inputs` — Prepare canonical inputs and trusted split plan | Validated raw input files; split seed; verified parent plan for extensions | Redact every descendant of content-bearing values, including nested tool arguments/results and named runtime/metadata content; preserve identity, exact routing, message-role, and tool-name fields byte-for-byte only at their structural paths; default `request_id` to `record_id` and an absent `route` to the exact `task_type`; recheck normalized record-ID uniqueness using physical source rows; derive exact-context-connected `split_group_id` values without changing `group_id`; assign trusted components to train, validation, test, or regression before authoring; record minimum correctness-evidence eligibility; create canonical intent text for clustering | `stages/02_prepared_inputs/`, including `trusted_split_plan.jsonl` and `feedback_eligibility.jsonl` |
| 3. `rubric_extraction` — Create evaluation guidelines | Eligible training rows from `normalized_feedback.jsonl`; protected eligible held-out units; configured guideline model | Extract and synthesize the reusable guideline library from eligible training feedback only. Build trusted-intent matching text from source request/context semantics and observed tools, not normative criteria. Separately compile validation/test/regression evidence within its assigned split, `split_group_id`, original `group_id`, and route for that held-out trusted case only; never expose protected criteria to Stages 5–7, later provider payloads, or UI previews | Public training-only and protected held-out artifacts under `stages/03_evaluation_guidelines/` |
| 4. `intent_clustering` — Mine intent clusters | `intent_records.jsonl`; configured embedding provider/model; exact cluster count | Vectorize canonical intent text with the selected OpenAI embedding model or local TF-IDF; allocate the configured cluster count across routes; cluster deterministically within each route; retain representative record IDs and top terms | `stages/04_intent_clustering/` |
| 5. `coverage_decisions` — Apply coverage decisions | `intent_inventory.jsonl`, `intent_records.jsonl`, training-derived `trusted_intents.jsonl`; configured embedding provider/model and coverage parameters | Compare each mined cluster with trusted intents; apply the match threshold (default `0.6`) and trusted-support constraints; classify every cluster; deterministically select centroid-near traces from under-supported and unsupported clusters for correctness-label acquisition. Every queue row records `purpose`, `method`, and `sampling_semantics: non_probability`; it is not an unbiased sample or prevalence estimate | `stages/05_coverage_decisions/`, including `review_queue/` |
| 6. `label_inference` — Infer reviewable labels | Intent clusters and matches; canonical unlabeled records; training-visible trusted evaluation guidelines; configured guideline model | For matched clusters only, use the configured LLM and matched guideline to propose a case rubric and inferred cases. Persist a complete dependency fingerprint over the guideline, support, match/cluster/source membership, provider/model/settings, prompt, split plan, and algorithm. Hold an output with no scoreable rule/check/reference/tool expectation; it produces no cases or synthesis | `stages/06_label_inference/`, including inference dependencies and held outputs |
| 7. `synthetic_coverage` — Optional synthetic coverage and review preparation | Supported clusters, representative requests, scoreable inferred rubrics and Stage 6 dependencies; enable flag and candidates-per-cluster setting | When enabled, request the configured number of candidates and apply only the enforced schema, nonempty-context, substantive-scoreability, narrow literal-label-leakage, and token-overlap checks. Persist complete Stage 7 dependencies, exact review fingerprints, exact canonical-context duplicate families, and conflict/scoreability holds. Scoreable inferred and mechanically accepted synthetic cases receive an automatic pipeline approval; held cases remain excluded. When disabled, make no synthetic model call and write empty synthetic artifacts. After the Stage 7 receipt commits, transition to `awaiting_review` | `stages/07_synthetic_coverage/`, `reviews/decisions.jsonl`, and `reviews/finalizations.jsonl` |
| 8. `dataset_splits` — Finalize and build dataset splits | Trusted cases; one explicit current review finalization; exact duplicate-family authority; split seed | Publish non-held trusted cases plus pipeline-approved inferred/synthetic cases; held cases stay in triage. Preserve early trusted assignments, keep each exact-context/supplied-group family in one split, never put a derived case in regression, and publish the four immutable consumer files | `stages/08_dataset_splits/`, root `asset_manifest.json`, and `datasets/evaluation_assets/<asset_id>/` |

The persisted Stage 3 identifier remains `rubric_extraction` so existing
`pipeline_state.json`, CLI, and API clients stay compatible. Its product name,
canonical folder, and behavior are **Evaluation guideline creation**. Existing
`03_rubric_extraction` and `feedback_rubrics.jsonl` assets remain readable as a
legacy contract.

Every stage persists `pending`, `running`, `completed`, or `failed`, timestamps,
a human-readable message, cumulative counts, and the hash of its atomic receipt
commit marker. The top-level asset lifecycle is separately restricted to
`draft`, `queued`, `running`, `awaiting_review`, `released`, or `failed`.
`completed` is accepted only as a visible pre-v2 legacy sentinel and is never
written for a new build or silently treated as released. `events.jsonl`
provides append-only operational history. A mutable resume verifies the
completed receipt prefix and rebuilds from the first incomplete or invalid
stage; a released asset is immutable and fails closed on any receipt or
artifact mismatch. Released verification also authenticates the exact v2
control state and identities, replays configuration history to justify every
receipt's full resolved-config hash, requires each native configuration update
to have exactly one earlier byte-equivalent version 2 prepare and one later
matching commit in revision order, and
binds Stage 8 to the exact persisted configuration-history bytes and current
configuration without requiring the current checkout to equal historical code.
Before Stage 1 has ever claimed receipt or completion authority, coherent
pending, failed, and process-interrupted running states use the copied raw files
as the resumable floor. Once a completed-stage status, state receipt hash,
receipt file, or completion event claims authority, revision and resume require
completed state, an exact state-to-receipt hash match, and a strict receipt
inventory authenticating both copied raw files. Missing, malformed, incomplete,
or stale evidence—and rewritten raw/receipt bytes that no longer match the
recorded state hash—fails before revision writes or provider construction.

A native run stops after a verified Stage 7 receipt with top-level status
`awaiting_review`; Stage 8 remains pending and no release generation or pointer
exists. Listing and deciding reviews retain that state. An explicit
finalization requires both the exact review-set fingerprint over current
items/dependencies/holds and the exact decision-set fingerprint over resolved
eligible statuses and decision IDs. The core revalidates both under the asset
lock before authorizing Stage 8; it does not approve pending items. A Stage 8
failure preserves the current finalization so an ordinary resume can retry
publication without repeating provider calls or asking for another review
decision.

Provider transport plus semantic response validation and normalization share
one sanitized boundary. Failures retain their original exception as an
in-memory chained cause, but persisted state, stage messages, and events contain
only the stage, actual provider and model, fixed exception category, and an
allowlisted causal summary. Raw provider messages, request/response bodies,
credentials, and arbitrary payload text are never persisted.

Injected providers remain injected. Default providers are constructed lazily
under the asset lock only after recovery, lifecycle and immutable raw-snapshot
integrity checks, optional revision, and configuration reload. An injected
rubric or embedding provider must pass the strict provider/model/settings
allowlists and secret-shaped-value rejection before calls or mutable writes;
the configured identity is never substituted for missing observed identity.
The complete prospective call rows, stage provenance, and receipts validate in
memory. The actual identity is shared by safe errors, receipts, Stage 3/6/7
metadata, and the asset manifest, so a revision cannot call an old provider
while claiming a new one.

Individual Studio JSON, JSONL, Markdown/text, copied, event, and configuration
history files use same-directory temporary files and an identity-bound native
CAS adapter. POSIX uses no-follow descriptors, file and parent `fsync`, and
flagged rename; Windows uses reparse-rejecting handles, `FlushFileBuffers`,
`FileRenameInfo`/`ReplaceFileW`, and has no directory-`fsync` equivalent. A
failed producer, serializer, copy, or pre-replacement write leaves the previous
single file intact. Exact operation-owned temporary, displaced, and quarantined
nodes are reclaimed after success, ordinary Python exceptions, and recoverable
retry paths; raced foreign nodes and ambiguous failures are retained and fail
closed. Hard process termination can leave unproven hidden debris for explicit
inspection, and later processes do not scavenge it by name. One deterministic
collection-level hard file
lock per asset protects every high-level mutation across processes. `filelock`
supplies bounded acquisition over the exact POSIX `flock` or Windows
`LockFileEx` handle, never a soft-lock fallback. Process-global
exact-identity ownership permits only same-thread recursion when threads share
a native handle. Bound handles record their opening process and reject use
after `fork`; child work must reopen and revalidate the literal path. Configuration
revision, checkpoint rebuild, native release publication, and legacy adoption
use an append-only recovery journal whose prepared payload rolls forward
idempotently.

Directory creation has an explicit local concurrency boundary. Every
Evaluation Asset Studio authority-root, authority-ancestor, stage, receipt,
publication-catalog, generation, and generation-staging directory creator
reached through repository, CLI, or Studio entry points uses the same
bound-directory adapter while holding a same-thread-reentrant exclusive POSIX
parent lock or identity-keyed Windows mutex. That lock spans complete
single-file observe/create/CAS/sync/reclaim and generation
collision/stage/install/sync/reclaim transactions. POSIX opens
descriptor-relative nodes without following symlinks; Windows retains the
complete no-share-delete, reparse-checked ancestor handle chain until the bound
directory closes. Darwin and Windows reject Unicode-normalized case-fold
aliases in authority names. Movable Windows private directories close their
leaf handle immediately before exact-identity rename, then reopen the installed
name with stable no-share-delete guards. The finite production guard rejects other `Path.mkdir`,
`os.mkdir`, and `os.makedirs` spellings, including literal persistence
attributes constructed through `operator.attrgetter` or
`operator.methodcaller`; unresolved dynamic attribute names are outside this
finite claim. It admits only the audited native operations in
`local_authority_io`, the generic parent bootstraps in
`_atomic_write_text` and `_atomic_write_binary`, and the deprecated non-Studio
`assemble_dataset_bundle`; a live complete-release assertion proves that the
compatibility bootstraps do not create any directory in the authority or
generation boundary. Private names, no-follow opens, complete
parent-inventory checks, exact inode/type rechecks, and no-replace installation
fail closed for preexisting, linked, wrong-type, detectably substituted, or
competing cooperating-writer entries. POSIX neither atomically returns a
descriptor from `mkdirat` nor conditionally removes an inode by handle, so the
creation and reclamation guarantees apply to cooperating Studio writers that
honor the same parent lock. They are not a claim of safety against an arbitrary
noncooperating process running as the same OS identity that mutates the parent
namespace between identity check and mutation. Deployments must keep the
Studio workspace writable only by the Studio's trusted OS identity and must not
run unaudited same-identity filesystem writers concurrently.
When a repository/invocation base is explicit, every existing component from
that base through the tenants root is opened and type-checked before mutation;
an intermediate symlink cannot turn a lexically relative root into an external
write target. Persisted generation paths remain literal repository-relative
paths.

Before roll-forward, recovery validates the complete version 2 journal schema,
unique operation identity, authenticated raw pre-operation config/state,
tenant/asset-bound target config and state, exact nested request/result/history/
event schemas, changed-field and stage-suffix semantics, before/target hashes,
strict contiguous prepare/commit ordering, and byte-exact before/target prefix
descriptors for both append-only audit logs. Only writer-reachable on-disk
control and audit phases are accepted. Every later operation is chained to the
prior target mutation/config identity and audit chronology; ordinary pipeline
stage events may extend the event prefix between mutations. Native publication
admits only the reachable pointer/state/event phases: all before; pointer
target; pointer and state target; or pointer, state, and event target. A
committed release requires the exact pointer, configuration, configuration
history, released state, event prefix, commit, and no successor. A committed
legacy adoption is likewise terminal and requires exact target config/state,
every target receipt, pointer and generation/provenance link, exact audit
prefixes, and its commit. Standalone candidate
and persisted release verification call this same complete validator. With no
outstanding operation, a final committed configuration revision or checkpoint
rebuild requires its exact target configuration and complete target
configuration history; state and events may continue through normal pipeline
lifecycle and stage progress after commit. Legacy
history compatibility is authorized only by the final validated adoption
prepare—committed or the one legitimate outstanding crash state—whose target
receipt hashes match the verified receipts. The authenticated adoption
before-state is then replayed through the full native or historical semantic
validator; receipt origin labels alone convey no compatibility. Version 1 or
mixed-version journals require explicit repair because they do not contain
enough before-state evidence for safe automatic recovery. A parseable,
rehashed, but inconsistent journal therefore fails before any authority write.

Stage 8 installs the four consumer files in one immutable content-addressed
generation. It validates and syncs a same-filesystem hidden temporary directory
before native no-replace installation, reuses only exact existing content, and never overwrites a
collision. `release.json` is the sole mutable catalog authority and changes by
one atomic replacement only after the generation, manifests, build provenance,
and Stage 8 receipt agree. The journal then installs released state, appends
the event, and commits. Readers capture the pointer once and return a frozen,
fully validated snapshot, so they see the complete old or complete new
generation. Old immutable generations and the pointer survive invalidation and
have no garbage collection. Exact operation-owned staging/quarantine debris is
reclaimed on success, ordinary exceptions, and recoverable retry paths. Raced
foreign nodes, hard-termination debris without durable ownership proof, and
other ambiguous failures remain visible so closed-tree verification fails
rather than hiding them.

Stages 3–7 always write receipt-backed `provider_calls.jsonl`, including an
empty ledger for zero calls. Resume aggregates authenticated earlier ledgers
instead of rerunning providers. Stage-local provenance records provider
identity, prompt hashes/revisions, code inventory, calls, seeds, and algorithms.
`build_provenance.json` separates deterministic identity/fingerprint from
audit-only timestamp, Git commit/tree and dirt, request IDs, usage, and retries.
Identity covers every declared source member, resolved defaults, runtime
dependencies, copied input hashes, lineage, provider/model/settings, prompts,
seeds, and algorithms. Strict allowlists and explicit unavailable or
not-applicable markers exclude protected prompt/request/response bodies,
headers, secrets, and exceptions.

Stage 6 and Stage 7 also write one self-authenticating dependency descriptor
per supported cluster. The Stage 6 descriptor binds complete cluster and match
rows, complete guideline content and support, hashed current source members,
provider/model/settings, prompt identity, and algorithm revision. Stage 7 binds
the complete inferred rubric and Stage 6 dependency, comparison members,
provider/model/settings, prompt, mechanical filter settings, and generation
set. Reuse requires exact descriptor equality. Every derived review fingerprint
then binds that dependency, the complete pre-publication case, and source
provenance, so a changed case or dependency cannot inherit an old approval.

### Updating decisions on resume

A stopped pipeline can resume with its existing configuration or an updated
set of decisions. The Studio's **Edit decisions & resume** form and optional
`assets run` flags use the same core revision mechanism:

1. Validate the requested settings and compare them with `config.json`.
2. Select the earliest stage affected by an actual change.
3. Verify and preserve every earlier receipt-backed checkpoint.
4. Durably append a prepared recovery operation containing the complete target
   configuration, state, audit rows, and cleanup boundary.
5. Replace the configuration and state, marking the affected suffix `pending`
   and clearing its receipt references.
6. Append the old and new values plus the restart stage to
   `config_history.jsonl` and `events.jsonl`.
7. Remove stale suffix artifacts and receipts, then commit the journal operation.
8. Resume the normal core runner. An interruption first rolls the prepared
   operation forward without duplicating history or events.

| Changed decision | Earliest stage rebuilt |
|---|---|
| Split seed | Stage 2, `prepared_inputs` |
| Guideline provider/model or LLM batch size | Stage 3, `rubric_extraction` |
| Embedding provider/model or exact cluster count | Stage 4, `intent_clustering` |
| Match threshold or trusted-support constraints | Stage 5, `coverage_decisions` |
| Synthetic coverage enable flag or cases per cluster | Stage 7, `synthetic_coverage` |

An unchanged submitted value does not invalidate anything. Decision edits are
rejected while the same asset has an active background runner. If the pipeline
already has an incomplete stage earlier than the decision's dependency, the
audit records both boundaries and execution resumes at that earlier stage.

### Reviewing and finalizing derived cases

Stage 7 writes eligible inferred and synthetic proposals to
`derived_review_items.jsonl`. Each item binds the complete
case, its scoreable expected payload, Stage 6/7 dependency, and source
provenance to an exact SHA-256 fingerprint. Unscoreable cases and exact-context
truth conflicts are held outside the approvable queue. Exact canonical
model-visible contexts are transitively united with supplied groups in
`duplicate_families.jsonl`; the core does not use embeddings, normalization,
token overlap, edit distance, or paraphrase similarity for this split identity.

Review operations use the same asset lock and recompute the current Stage 7
receipt, dependencies, item fingerprints, holds, review-set fingerprint, and
decision-set fingerprint. The review set is stable across decision-only changes;
the decision set binds the canonical resolved `case_id`, item fingerprint,
status, and decision ID rows. An eligible item may append one immutable
`approved` or `rejected` decision for its exact fingerprint. Mechanically
accepted synthetic items and scoreable inferred items are automatically
approved by the pipeline. Missing, stale,
duplicate, malformed, or mismatched authority fails closed to pending or an
integrity error; there is no latest-write-wins reversal. Decisions and
historical finalizations remain append-only across invalidation.

Finalization is a separate explicit action. It accepts the displayed review-set
and decision-set fingerprints as preconditions and snapshots the exact current
items, effective decisions, holds, and Stage 7 receipt. It may leave any number
of items pending: Stage 8 always excludes pending, rejected, and held derived
cases. An exact replay against a released asset is idempotent, but a released
asset cannot revise the snapshot; create a child version. The Stage 8 and root
manifests report exact trusted, approved, pending, rejected, and held counts
plus the corresponding case-content or review fingerprints, the review-set
fingerprint, finalization ID, and Stage 7 receipt hash.

### Extending a released asset

Extension creates a complete new asset version without modifying or rerunning
the parent version. Under parent and child locks acquired by sorted absolute
lock path, the core first requires `released` and verifies the complete parent
receipt chain, raw source hashes, lineage/reuse metadata, and every artifact to
be copied. A legacy `completed` parent points to explicit adoption; corruption
leaves the child root absent. The child records `lineage.json`,
`reuse_manifest.json`, the parent Stage 8 receipt hash, released-state hash, and
source-lineage hash. Parent snapshot artifacts are copied into
`stages/01_raw_inputs/parent_snapshot/` with hashes, so the child has no runtime
dependency on the parent directory. Lineage and reuse documents use strict
schemas and must agree field-for-field on parent release evidence, seeded and
reused stages, counts, and the exact snapshot inventory. Stages 3–8 receipt the
lineage/reuse files and every snapshot they consume; Stage 8 also inventories
the two control documents as required outputs.

The Studio and `assets extend` CLI expose two modes:

| Mode | Allowed additions | Stage behavior |
|---|---|---|
| `keep` | Labeled feedback only | Merge and validate full inputs; preserve parent trusted assignments; prepare the current eligibility/split view; extend reusable evidence only with newly added eligible training feedback; rebuild training-only guidelines and protected held-out units; restore the exact Stage 4 inventory from the verified child snapshot on every run or rebuild; reuse Stage 6/7 outputs only for exact dependency matches; rebuild review authority and recalculate Stage 8 after finalization without reclustering |
| `refresh` | Labeled feedback, unlabeled records, or both | Merge and validate full inputs; preserve parent trusted assignments and assign only new components from the inherited seed; rebuild training-only guidelines and protected held-out units; rerun Stage 4 over the combined unlabeled pool; reuse Stage 6/7 outputs only for exact dependency matches; rebuild review authority and recalculate Stage 8 after finalization |

Keep mode requires the parent's producing embedding provider/model, cluster
count, and guideline provider/model. Refresh retains the producing guideline
identity but may select a complete new embedding provider/model pair and cluster
count. These comparisons use verified receipt evidence, not potentially stale
configured defaults. If producing embedding evidence differs from configuration,
refresh omission or a partial pair fails before the child root is created;
keep must explicitly select the producing pair. When legacy adoption records a
producing identity as historically unavailable, either mode requires a complete
explicit provider/model identity.

Feedback collected for a Stage 5 queue item may use the same `record_id` as its
original unlabeled trace. The trace remains in the intent inventory so traffic
frequency and cluster membership stay stable, but it is excluded from inferred
cases once its trusted feedback is added.

Stage 2 preserves the parent's trusted-group assignments before any guideline
call. Existing groups stay in their train, validation, test, or regression
location; new connected groups receive a deterministic assignment from the
inherited split seed. A new exact-context bridge between incompatible parent
splits fails closed instead of reshuffling either population. A child inherits
an approval or rejection only when the complete review fingerprint and
canonical case bytes are identical; dependency or case changes return the item
to pending.

Refresh mode writes
`stages/04_intent_clustering/cluster_lineage.jsonl`. Each row relates a previous
and current cluster by member overlap and classifies it as `continued`, `split`,
`merged`, `new`, or `retired`. Keep mode writes identity lineage with
relationship `reused`.

## Evaluation Asset Studio

The universal Studio is served on the same port as FAPO Explorer with its own
index at `/evaluation-assets/`. Its creation form accepts:

- Tenant ID and asset version.
- Labeled feedback and unlabeled JSONL workspace paths.
- Evaluation-guideline creation model.
- OpenAI embedding model or explicit local TF-IDF fallback.
- Exact requested cluster count.
- Stage 5 intent match threshold, defaulting to `0.6`.
- Whether to enable Stage 7 synthetic coverage; it is disabled by default.
- Synthetic candidates per supported cluster when Stage 7 is enabled.

Selecting a tenant and asset shows the eight-stage strip. Selecting a stage
opens its inputs, processing operations, outputs, counts, artifact list, and
one syntax-highlighted example per safe artifact. Protected held-out criteria,
inferred/synthetic case bodies, and dependency bodies have previews disabled;
metadata-only artifacts are projected through a fixed safe-field allowlist.
The Intent Mining stage also
shows the projection-style cluster explorer with route filters, cluster sizes,
representative requests, and observed tools. Visualization data is separate
from artifact examples; the example panel never loads an entire JSONL file.

The artifact guide keeps stable machine-readable filenames while presenting
friendly names, descriptions, and four usage groups:

- **Key outputs** are the files most users consume next.
- **Needs attention** contains labeling and triage work queues.
- **Supporting data** explains or decomposes a key output.
- **Diagnostics** contains manifests, rejection reasons, and audits.

The Studio refreshes running state every five seconds and calls the same core
start/resume service used by CLI-driven workflows. A failed asset retains a
**Resume with current decisions** action and places an always-visible parameter
editor directly on the failed stage. The editor shows only stage-relevant
settings and explains when changing one rebuilds from an earlier stage. Raw
inputs remain immutable within an asset; a Stage 1 source correction requires
a new asset version.

At `awaiting_review`, the Studio renders a dedicated review panel before Stage
8. It shows the exact review-set and decision-set fingerprints, safe paged item
metadata, and pending/approved/rejected/held counts. One offset and a
1-through-100 limit bound the combined deterministic eligible-plus-held
projection, and `held` is a supported status filter. Each eligible current
fingerprint has an individual approve or reject action; there is no bulk or
implicit approval. Decisions send the displayed review-set fingerprint;
finalization sends both fingerprints, so a stale auto-refreshed view fails
rather than freezing a different decision snapshot. Asset summaries expose a
safe `review_authority_revision` that changes after external decisions or
finalization and prompts the Studio to reload. The review payload exposes only
safe finalization identity/count metadata, including after release.
Finalization warns that pending, rejected, and held derived cases remain
unpublished.

Selecting **Extend asset** opens an execution-plan preview. Adding an unlabeled
path automatically selects refreshed clustering; keep mode disables embedding
and cluster-count edits. At least one additional labeled or unlabeled JSONL
file is required.

## Provider Selection

Evaluation-guideline creation and label inference use the configured OpenAI model. The
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

Every provider-backed embedding batch is validated before clustering or
matching. Raw indexed responses must contain each integer index exactly once in
`0..n-1`. Built-in and injected providers must return exactly one vector per
input, finite real numeric coordinates (booleans and numeric strings are not
accepted), one consistent positive dimension, and a nonzero vector for every
input.

## Troubleshooting OpenAI SSL Connections

Use this procedure when the in-memory chained provider exception or protected
operator log shows an SSL/TLS certificate verification or trust-chain error.
Persisted asset state deliberately contains only a sanitized failure category,
not the raw provider exception. Do not apply this procedure to authentication,
model-access, rate-limit, or response-format failures.

Install or upgrade the OpenAI client, HTTP client, certificate bundle, and
system-trust integration in the same Python environment used to run FAPO:

```bash
python3 -m pip install --upgrade openai httpx certifi truststore
```

If they are commented in the checkout, uncomment the five-line `truststore`
blocks at:

- `src/hephaestus/providers/openai.py`, lines 50–54.
- `src/hephaestus/datasets/rubric_providers.py`, lines 85–89.
- `src/hephaestus/datasets/embedding_providers.py`, lines 61–65.

Each block imports `truststore`, calls `truststore.inject_into_ssl()`, and
continues when the optional package is unavailable. The blocks may already be
active. Restart the FAPO UI or CLI process so it loads the updated environment
and source, then invoke `assets run` again. The checkpointed runner resumes at
the first incomplete stage.

## Dataset Splits

Each evaluation asset produces the fixed FAPO JSONL split files below:

| Split | Contents | Primary Use |
|---|---|---|
| `train_trusted` | Trusted feedback cases selected for optimization | Optimization and failure discovery |
| `train_inferred` | Exact-fingerprint-approved labels on real traces from matched trusted feedback | Optimization coverage |
| `train_synthetic` | Mechanically accepted and pipeline-approved synthetic cases | Optimization coverage |
| `validation_trusted` | Held-out trusted examples | Candidate selection |
| `validation_inferred` | Exact-fingerprint-approved inferred labels assigned to validation for this dataset version | Coverage-oriented validation |
| `validation_synthetic` | Mechanically accepted and pipeline-approved synthetic examples assigned to validation | Coverage-oriented validation |
| `test_trusted` | Held-out trusted examples used for release-candidate testing | Final release check |
| `test_inferred` | Exact-fingerprint-approved inferred labels assigned to test for this dataset version | Coverage-oriented final check |
| `test_synthetic` | Mechanically accepted and pipeline-approved synthetic examples assigned to test | Coverage-oriented final check |
| `regression_trusted` | Automatic 20% holdout sampled only from trusted feedback cases | Tight non-regression gate |
| `triage_hold` | Exact-truth conflicts, unscoreable derived cases, and approved derived cases attached to regression | Audit/repair queue only |

`regression_trusted` is created automatically from the early Stage 2 plan. A
stable hash of the split seed and each connected `split_group_id` assigns
approximately 20% of components to regression before guideline authoring and
excludes those cases from train, validation, and test. The original `group_id`
is preserved; exact canonical model-visible contexts and supplied groups are
transitively united only in the derived split identity. Inferred and synthetic
cases never enter regression. An approved derived case attached to a regression
component is written to `triage_hold` instead.

Before final splitting, the core builds exact duplicate families across trusted,
inferred, and synthetic pre-publication cases. If one exact context has
different expected/scoring truth, every case in that connected component is
held rather than selecting a preferred source. Otherwise, the complete family
stays in one split. This exact mechanism does not detect paraphrases or claim
semantic equivalence; the separate Stage 7 token-overlap heuristic is only a
candidate-rejection check.

The root `asset_manifest.json` and Stage 8 manifest carry the same authenticated
`review` authority: the review-set fingerprint, finalization ID, Stage 7 receipt,
exact trusted/approved/pending/rejected/held counts, and canonical per-case
fingerprints. Trusted rows are bound by complete case-content fingerprints;
derived rows by complete review fingerprints; held rows by their fingerprint
and reason. Released verification recomputes the inventory from the persisted
finalization snapshot, so a changed count, identity, fingerprint, or reason
fails closed.

## Intent Coverage Gate

Unlabeled traces are not labels. They should be used to discover high-volume intents and coverage gaps.

For each mined intent cluster:

- If the intent matches the training-visible trusted pool and passes the
  configured support thresholds, use that trusted evidence to propose coverage
  cases for fingerprint-bound review.
- If the semantic match is good but trusted support is too thin, request more trusted examples before relying on synthetic expansion.
- If the intent has missing or weak labels, do not synthesize labels for it yet. Route representative examples to application feedback prompts, annotation queues, or SME review.

This prevents the workflow from inventing correctness criteria for intents where the application only knows that users ask the question, not what a good answer should look like.

The generic gate emits these statuses:

| Status | Meaning | Next Action |
|---|---|---|
| `matched_trusted_intent` | The unlabeled cluster matches training-visible trusted labeled evidence and meets configured support thresholds | Proceed to label inference, optional synthetic proposal, and fingerprint-bound review |
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
  "texts": ["trusted example or evaluation guideline summary"],
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

1. Stage 2 builds `canonical_intent_text` from `user_input`, every prior
   user conversation-context message in order, and observed tool names. It preserves the
   supplied `route` byte-for-byte, defaulting it to the exact `task_type` only
   when `route` is absent. Present whitespace is significant routing identity.
2. Stage 4 vectorizes that canonical text with the configured OpenAI embedding
   model or the explicit local TF-IDF fallback.
3. The requested cluster count is allocated across routes, with at least one
   cluster per distinct route. The count must not exceed the number of records
   and must be at least the number of routes.
4. Deterministic cosine k-means clusters records within each route and records
   member IDs, representative IDs, and top terms in `intent_inventory.jsonl`.
   Legacy slug-based cluster IDs remain unchanged when route slugs are unique;
   routes whose exact values collide after slugging receive a stable digest of
   the exact route bytes so cluster IDs cannot overwrite one another.
5. Stage 5 builds comparable text for clusters and training-derived trusted
   intents, vectorizes it with the same configured provider, chooses the best
   same-route trusted match by cosine similarity, and applies the configured
   coverage policy. Trusted text uses source user requests, the latest
   conversation context, observed tool names, and the intent label; normative
   guideline criterion statements are not traffic semantics.
6. For each `needs_more_trusted_examples` or `missing_or_weak_labels` cluster,
   Stage 5 selects 10% of its records, with a minimum of one and a maximum of
   three. Selection uses the centroid-near representatives already calculated
   by Stage 4, so it is deterministic and favors typical traces over outliers.
   The selected redacted traces are written to
   `stages/05_coverage_decisions/review_queue/labeling_queue.jsonl` with their
   cluster status and reason. Each row also declares acquisition purpose
   `correctness_label_acquisition`, method
   `deterministic_centroid_nearest`, and
   `sampling_semantics: non_probability`.

Stage 5 does not call an LLM and has no manual review checkpoint. Its output is
the persisted coverage decision and an external labeling work queue. The queue
intentionally favors centroid-near representative traces; it is not an unbiased
sample and cannot estimate traffic prevalence. Stage 6 uses the configured
guideline LLM only for clusters whose Stage 5 status is
`matched_trusted_intent`.

This asset creation step is not a FAPO eval run. It produces versioned datasets and coverage reports that the FAPO optimization loop consumes afterward.

Recommended generic artifacts:

| Artifact | Purpose |
|---|---|
| `intent_inventory.jsonl` | Cluster records with representative IDs, top terms, route, and size |
| `intent_matches.jsonl` | Coverage decisions: matched trusted intent or missing/weak labels |
| `coverage_report.md` | Human-readable summary of high-volume clusters, trusted coverage, and feedback requests |
| `stages/05_coverage_decisions/review_queue/labeling_queue.jsonl` | Representative redacted traces that need new trusted labels |
| `dataset_manifest.json` | Dataset version, split files, oracle version, and generation settings |
| FAPO JSONL split files | Versioned train, validation, test, and regression datasets |

## Core Pipeline Contract

The shared pipeline parses `fapo-evaluation-input-v1` directly. No source field
mappings are stored in the asset configuration and no tenant code is imported.
The core owns contract validation, redaction, evaluation-guideline creation, exact-count
clustering, coverage decisions, inferred labels, group-safe splits, manifests,
checkpoints, and progress events.

Each new asset contains:

| Directory | Contents |
|---|---|
| `stages/01_raw_inputs/` | Immutable copied labeled and unlabeled JSONL plus source hashes |
| `stages/02_prepared_inputs/` | Normalized feedback, canonical intent records, early trusted split plan, and feedback-eligibility decisions |
| `stages/03_evaluation_guidelines/` | Public training-only evidence/guidelines/intents/cases plus protected split-local held-out evidence/guidelines/cases |
| `stages/04_intent_clustering/` | Intent cluster inventory |
| `stages/05_coverage_decisions/` | Match decisions, coverage report, and nested non-probability correctness-labeling queue |
| `stages/06_label_inference/` | Inferred rubrics/labels/cases, complete dependency descriptors, held unscoreable outputs, and unsupported-cluster reports |
| `stages/07_synthetic_coverage/` | Candidate, mechanically accepted/rejected, filter-audit, dependency, derived-review, exact-family, and held artifacts |
| `reviews/` | Append-only immutable exact-fingerprint decisions and finalization snapshots |
| `stages/08_dataset_splits/` | Final review snapshot and authoritative approved-only component/combined train, validation, test, regression, and triage files |
| `datasets/evaluation_assets/<asset_id>/release.json` | Sole mutable pointer to the current verified consumer generation |
| `datasets/evaluation_assets/<asset_id>/generations/sha256-<hash>/` | Immutable generation manifest and combined `train`, `validation`, `test`, and `regression_trusted` JSONL files |

The complete `evaluation_assets/<asset_id>/` runtime tree—including copied
inputs, checkpoints, state, events, and stage artifacts—is local-only and has
no Studio-managed remote backend. Stage 8 also writes local immutable consumer
generations under the ordinary tenant `datasets/` catalog. The Studio never
uploads them; they participate in a separate `customer-data --scope derived` sync
only when the tenant storage configuration places `datasets/` inside its
`derived_local` tree.

Assets created before the stage-oriented layout remain readable through the
compatibility mapper. Mutable legacy work rebuilds status-only checkpoints
because no receipt exists. A pre-v2 top-level `completed` asset is not usable as
a release until explicit adoption validates all eight stages, source hashes,
manifests, and current catalog copies, creates historical-unavailable
provenance, and publishes one immutable generation as its single terminal WAL
operation. Old catalog copies remain only as nonauthoritative historical bytes.
An interim v2 released asset without `release.json` is unpublished and must be
repaired from a verified backup or rebuilt as a new version; adoption is not a
migration. Existing `raw_inputs/`,
`prepared_inputs/`, `decision_assets/`, `review_queues/`, and
`dataset_splits/` directories are not moved.

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

Omit `--enable-synthetic-coverage` to propose only trusted and inferred real
cases. Inferred cases still require exact-fingerprint approval before
publication. The per-cluster count is persisted but ignored while Stage 7 is
disabled.

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
skipped only when their receipts verify on resume; model settings and the fixed
cluster count are recorded in the asset manifest.

A normal run stops at `awaiting_review` after Stage 7. List a bounded page and
copy its current `review_set_fingerprint` and `decision_set_fingerprint`:

```bash
python -m hephaestus.cli assets reviews list \
  --tenant <tenant_id> \
  --asset-id <asset_id>
```

The list command's `--status` option accepts `pending`, `approved`, `rejected`,
or `held`. It applies `--offset` and `--limit` to one combined, deterministic
eligible-plus-held projection, and returns no more than the requested limit
across `items` and `held`; `--limit` must be from 1 through 100.

Approve or reject one eligible current item by exact case and review-set
fingerprints:

```bash
python -m hephaestus.cli assets reviews approve \
  --tenant <tenant_id> \
  --asset-id <asset_id> \
  --case-id <case_id> \
  --fingerprint <sha256:item_fingerprint> \
  --reviewer <reviewer_name> \
  --review-set <sha256:review_set_fingerprint>
```

`assets reviews reject` accepts the same arguments. Re-list after the last
decision to obtain the current decision-set fingerprint. When that exact
snapshot is ready—including when every derived item should remain pending—freeze
it and synchronously run Stage 8:

```bash
python -m hephaestus.cli assets reviews finalize \
  --tenant <tenant_id> \
  --asset-id <asset_id> \
  --reviewer <reviewer_name> \
  --review-set <sha256:review_set_fingerprint> \
  --decision-set <sha256:decision_set_fingerprint>
```

Explicitly verify and adopt a legacy top-level `completed` asset:

```bash
python -m hephaestus.cli assets adopt \
  --tenant <tenant_id> \
  --asset-id <legacy_asset_id>
```

Successful adoption writes historical receipts with unavailable provenance for
facts the old build did not record, materializes a generation, and installs the
pointer, released state, event, and commit as one terminal operation. Before
preparing the WAL it strictly validates canonical source/prepared identity,
guidelines or legacy rubrics, clusters, coverage references,
inferred/synthetic provenance,
case schemas, finite numeric domains, exact deterministic synthetic
accepted/rejected/issue outputs (including an empty candidate set), group-safe
split partitions, trusted-only regression data, manifests, counts, and the four
catalog copies. Invalid adoption changes no authority; a valid prepared crash
rolls forward idempotently. The Studio exposes the same locked core operation.

Pass optional decision flags to revise and resume in one command:

```bash
python -m hephaestus.cli assets run \
  --tenant <tenant_id> \
  --asset-id <asset_id> \
  --rubric-model gpt-5.5 \
  --embedding-model text-embedding-3-small \
  --clusters 40 \
  --match-threshold 0.55 \
  --no-synthetic-coverage
```

Omitted settings retain their persisted values. Use
`--synthetic-coverage` to enable Stage 7 and
`--synthetic-cases-per-cluster <count>` to change its requested size.

## Synthetic Coverage Cases

Synthetic proposals are requested only for clusters with a scoreable inferred
rubric derived from a training-visible trusted-intent match. They do not define
new trusted intents or correctness criteria.

The persisted mechanical filter enforces only:

- the FAPO case schema;
- a nonempty `context` mapping;
- at least one substantive rubric rule, deterministic check, reference, label,
  answer, or tool expectation;
- absence of a narrow literal leakage match for selected expected strings of at
  least 24 characters; and
- token-set Jaccard overlap below the fixed `0.95` threshold against
  existing accepted cases.

Those checks do **not** establish factual correctness, safety, domain
consistency, tool feasibility or availability, real-world solvability,
realism, indirect-leakage absence, privacy beyond the separate redaction
contract, or calibrated semantic equivalence. The token-overlap heuristic is a
candidate-rejection mechanism, not the exact canonical-context family identity
used for split safety.

Mechanically accepted synthetic cases and scoreable inferred cases receive a
fingerprint-bound pipeline approval and may be assigned to training,
validation, or test for that dataset version. Held cases remain auditable but
unpublished; derived cases never enter `regression_trusted`.

## Prepared Feedback Record

Stage 2 converts the fixed evaluation input contract into an internal,
redacted feedback record. It preserves canonical identity, routing, role, and
tool-name fields byte-for-byte; no internal aliases are introduced. Adapters
must assign stable pseudonyms before the contract boundary when policy requires
identifier pseudonymization:

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
format used for evidence extraction, guideline creation, and auditability.
Stage 2 adds the derived `split_group_id`, `trusted_split`, and
`evidence_eligible` fields. An ineligible row also carries
`hold_reason: insufficient_correctness_evidence`. The original `group_id`
remains unchanged.
Redaction covers `user_input`, `assistant_output`, conversation content,
feedback rationale/correction, complete tool argument/result/error subtrees,
and explicitly content-bearing nested runtime/metadata values. Provider names,
model names, labels, provenance fields, and identifiers are not treated as free
text.

## Evaluation Guideline Creation

Stage 3 deliberately separates evidence from generalization:

1. `feedback_evidence.jsonl` records atomic claims, explicit corrections, and
   uncertainties for eligible training feedback only. The previous assistant
   output is context and never becomes an answer key. Evidence extraction sees
   complete redacted tool calls and, when present, the ordered episode with
   tool arguments, results, and errors. It uses that trajectory to ground which
   action or observed outcome the feedback refers to, while unresolved
   ambiguity becomes an uncertainty. Ineligible rows remain in Stage 2 audit
   artifacts and make no guideline call.
2. `candidate_guidelines.jsonl` contains model-proposed groupings of compatible
   eligible training evidence within a route. Guideline synthesis also receives
   compact `observed_tool_calls` for each source example: ordered tool names,
   redacted arguments, and whether a result, error, or no outcome was recorded.
   It uses this context for tool expectations, evaluator plans, evidence
   requirements, state-change criteria, and failure conditions. Full successful
   result payloads are not duplicated because they were already available to
   evidence extraction. Every eligible training `record_id` must be represented.
3. `evaluation_guidelines.jsonl` is the compiled contract used downstream.
   Each guideline has stable provenance and criteria with source record IDs,
   `kind`, `dimension`, `severity`, `applicability`, `scoring`,
   `evidence_required`, and an evaluator plan. Conflicts and uncertainties stay
   explicit.
4. `trusted_intents.jsonl` aggregates training support counts. Matching text is
   built from the source user request, every prior user conversation-context
   message in order, and observed
   tool names, and intent label; it excludes normative criterion statements.
   `trusted_cases.jsonl` embeds the applicable guideline IDs and complete
   guideline snapshots so training split files remain independently usable.
5. `protected_feedback_evidence.jsonl`,
   `protected_candidate_guidelines.jsonl`,
   `protected_evaluation_guidelines.jsonl`, and
   `protected_trusted_cases.jsonl` hold eligible validation, test, and
   regression units. Each unit is isolated by assigned split,
   `split_group_id`, original `group_id`, and route. These criteria produce only
   their corresponding held-out trusted cases; they never enter reusable
   guidelines, trusted-intent matching, Stage 6/7 prompts, or UI content
   previews.

The live writer and legacy-adoption verifier share this transformation
contract. Candidate criteria accept only `required`, `prohibited`, or
`preferred`; severities accept `critical`, `major`, or `minor`; evaluator type
and fallback accept `state_check`, `deterministic_check`,
`semantic_trajectory`, `llm_judge`, or `human_review`. Scoring remains a
nonempty producer-defined string, applicability is a string or JSON mapping,
and tool expectations are a finite JSON mapping. Adoption deterministically
replays candidate compilation and every derived guideline, trusted-intent, and
trusted-case field. Genuine pre-guideline rubric layouts are replayed against
their historical trusted intent/case writer rather than being coerced into the
native schema. The shared identity contract rejects exact duplicate canonical
candidates and duplicate or colliding guideline, criterion, trusted-intent, or
trusted-case IDs; it never silently deduplicates. The live writer performs this
check before any Stage 3 artifact or receipt write, and native/historical replay
uses the same check. Any mismatch fails before receipts, journal, state,
history, events, or catalog authority changes.

Observed tool execution is never independent correctness evidence. A returned
result does not prove that the tool choice, arguments, resulting state, or
overall behavior was correct. Normative criteria still require trusted feedback,
an explicit correction, or another declared correctness signal. Guidelines
prefer semantic tool expectations and allow alternate valid workflows; they use
literal tool names only when the evidence establishes an exact contract.

Evaluator plans use this preference order:

1. `state_check` for verifiable final environment state and collateral effects.
2. `deterministic_check` for schemas, policies, parsers, and exact invariants.
3. `semantic_trajectory` only when an abstract workflow subpath is itself
   required; literal tool names are avoided unless contractually mandatory.
4. `llm_judge` for qualitative criteria with multiple valid answers.
5. `human_review` when the available evidence cannot support an automated
   decision.

Reusable generated guidelines are active because their source is eligible
training feedback, but they are marked `uncalibrated`. Protected held-out
guidelines are local scoring material, not reusable authoring guidance. A later
eval lifecycle should compare automated grades with human or executable
outcomes before treating judge scores as a high-confidence release signal.
This is metadata, not a blocking Stage 3 review gate.

## Oracle Construction

Construct `expected` from the strongest available source:

1. **Human correction**: Use a corrected answer, accepted edited query, or SME-approved artifact as the highest-trust reference.
2. **Deterministic oracle**: Use tool schema constraints, parser checks, policy checks, syntax checks, and output format checks when they can decide correctness without another model.
3. **Evaluation guideline**: Compile repeated or compatible feedback evidence into explicit criteria while preserving source record IDs, conflicts, applicability, and uncertainty.
4. **Positive exemplar**: For positive feedback, preserve behavior as a non-regression expectation only after checking that the response is safe, grounded, and not merely pleasant.
5. **LLM judge**: Use only as a calibrated scorer component. The judge should compare a new response to the applicable guideline and evidence, not to the previous assistant output alone.

Avoid exact-answer labels when the task has many valid outputs. Prefer evaluation guidelines, invariants, and tool-behavior expectations.

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
    "label_source": "evaluation_guideline_from_trusted_feedback",
    "confidence": 0.9,
    "feedback_polarity": "negative",
    "evaluation_guideline_ids": ["guideline-task-family-identifier"],
    "evaluation_guidelines": [
      {
        "guideline_id": "guideline-task-family-identifier",
        "calibration_status": "uncalibrated",
        "criteria": []
      }
    ],
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

The current core enforces these publication holds:

- A feedback row with no nonempty rationale, material correction, or declared
  deterministic/executable correctness signal is retained with
  `insufficient_correctness_evidence` and activates no guideline or trusted
  case.
- An inferred rubric with no substantive rule, check, reference, or tool
  expectation is retained as `unscoreable_rubric` and produces no inferred or
  synthetic cases.
- A derived case with an unscoreable `expected` payload is held outside the
  approvable queue.
- Every case in an exact-context-connected family is held when that exact
  context has conflicting expected/scoring truth.
- An approved derived case connected to trusted regression is held rather than
  published in any split.

Contradiction, safety, policy, broader privacy, factual grounding, and
reproducibility checks remain separate scorer, executable-check, or human-review
responsibilities. Passing the minimum evidence gate or mechanical synthetic
filter is not evidence that those properties hold.

## Splitting Rules

- Preserve the source `group_id` and assign a derived `split_group_id` for the
  transitive union of supplied groups and exact canonical model-visible
  contexts.
- Assign trusted components to train, validation, test, or regression in Stage
  2, before guideline authoring. Extensions preserve verified parent
  assignments and use the inherited seed only for new components.
- Do not claim semantic/paraphrase deduplication. Exact canonical contexts are
  grouped; the token-overlap synthetic check is a separate rejection heuristic.
- Keep validation and test examples out of prompt/skill authoring context during optimization.
- Assign only pipeline-approved inferred and synthetic cases to train,
  validation, or test.
- Automatically assign approximately 20% of trusted connected groups to
  `regression_trusted` at the early boundary.
- Route a derived case connected to a regression family to `triage_hold`.
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

The eight-stage pipeline ends when the evaluation asset and its verified
dataset splits are `released`. FAPO can then consume the asset in a separate
lifecycle:

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
- Do not expose held-out protected guideline/evidence artifacts to authoring,
  downstream provider payloads, or UI previews.
- Do not mix one supplied/exact-context-connected family across splits.
- Do not synthesize labels for intents that do not match trusted labeled evidence.
- Do not publish an inferred or synthetic case without its exact current
  pipeline approval.
- Keep inferred and synthetic cases out of `regression_trusted`; the core
  selects that gate automatically from trusted feedback.
- Do not commit raw feedback traces or local generated datasets unless the tenant workflow explicitly allows it.
