<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Evaluation Asset Reference

> This page describes the eight-stage pipeline, which will be removed. New
> assets use `assets build`; see the [data pipeline reference](data-pipeline.md).

Reference for operating and reviewing evaluation assets: the workspace layout,
the eight stages, lifecycle and durability guarantees, publication,
provenance, and the full CLI. For the concepts, trust model, split semantics,
and end-to-end flow, start with the
[FAFO data pipeline guide](../processes/feedback-dataset-flow.md).

The CLI, service API, and evaluation-asset assistants all trigger and monitor
the same core implementation under `src/hephaestus/evaluation_assets/`. Agents
do not implement the data transformations themselves.

- [Inputs and workspace](#inputs-and-workspace)
- [Eight-stage workflow](#eight-stage-workflow)
- [Lifecycle, receipts, and released assets](#lifecycle-receipts-and-released-assets)
- [Recovery journal and locking](#recovery-journal-and-locking)
- [Publication](#publication)
- [Provider-call provenance](#provider-call-provenance)
- [CLI](#cli)

## Inputs and workspace

Both input files must already use the vendor-neutral
[`fafo-evaluation-input-v1`](../processes/evaluation-input-contract.md)
JSONL contract.

- Each source must be a regular `.jsonl` file beneath the selected tenant's
  `source_artifacts/` or ordinary `datasets/` directory.
- Generated `datasets/evaluation_assets/` outputs, other tenants, external
  paths, and symlink escapes are rejected.

FAFO validates the source contract, then copies the inputs into a
self-contained workspace:

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

- After creation, every stage reads from this workspace, not the original
  files or other tenant resources.
- Each stage owns only its outputs and reads inputs from earlier stage folders.
- The evaluation-asset runtime, copied inputs, checkpoints, events, and stage
  artifacts in `evaluation_assets/` are local-only. The pipeline has no remote
  persistence backend for this workspace.

## Eight-stage workflow

| Stage | Purpose |
|---|---|
| 1. Validate raw inputs | Validate the canonical contract and record source counts and hashes. |
| 2. Prepare inputs | Redact sensitive values, apply canonical defaults, assign connected trusted groups to train, validation, test, or regression from the split seed, record minimum correctness-evidence eligibility, and build intent text without renaming fields. |
| 3. Create evaluation guidelines | Correlate eligible trusted feedback with messages, tool activity, outcomes, and runtime; recognize supported mistake/success patterns; and compile the reusable training-only guideline library. Keep held-out guidance protected and case-local. |
| 4. Cluster intents | Optionally embed unlabeled intent records and build route-aware clusters for sampling, analysis, and synthetic coverage. Set `--clusters 0` to skip. |
| 5. Record sampling context | Optionally persist cluster membership, representatives, routes, and task types. Skipped with Stage 4. |
| 6. Build episode rubrics | For every feedback and unlabeled episode, give the model the complete split-permitted guideline catalog and trace analysis in one call. Select zero, one, or many guidelines and create one scoreable case rubric; if none applies, infer the rubric from the trace and available constraints. |
| 7. Expand coverage and prepare review | Optionally synthesize only from clusters whose episodes share one identical guideline-grounded rubric, apply the documented mechanical filters, fingerprint every eligible derived case and its complete dependencies, build exact-context duplicate/conflict families, and pause at `awaiting_review`. |
| 8. Build splits after finalization | After explicit review finalization, publish trusted cases plus exact-fingerprint-approved derived cases only. Pending, rejected, and held cases remain auditable but unpublished. |

### Stage 2: groups and evidence eligibility

- Stage 2 preserves each source `group_id` and adds a derived `split_group_id`
  that connects supplied groups sharing exact canonical model-visible context.
- It assigns those components to splits before any guideline call.
- A valid rating without a rationale, correction, or declared check can still
  produce guidelines and a trusted case rubric. The rating supplies only a
  coarse episode-level signal, so the model must ground specific requirements
  in the user request and observable trace without inventing a reason for the
  rating.

### Stage 3: guideline evidence

- Stage 3 uses one shared producer/verification contract.
- Its public evidence, candidate, and guideline inventories contain eligible
  training feedback only.
- When feedback supports a claimed mistake or success, the extractor must link
  it to both the feedback and an observable trace location, distinguish agent
  behavior from environment failure, and preserve uncertainty when causality
  is not supported.
- Validation, test, and regression evidence is compiled separately within its
  assigned split, `split_group_id`, original `group_id`, and route. Those
  protected guidelines are visible only while generating the corresponding
  held-out episode rubric. They never enter reusable training guidance or
  other episodes' provider payloads.

### Stage 6: rubric dependencies

Stage 6 persists one rubric and one self-authenticating dependency descriptor
per episode. The dependency covers:

- the full permitted guideline catalog;
- the episode evidence;
- the selected guideline IDs (possibly empty);
- provider/model/settings;
- prompt identity; and
- algorithm revision.

Cluster identity is excluded from rubric correctness and remains available only
for sampling and optional synthesis. Extension reuse requires exact dependency
equality, and any changed dependency produces a new pending review
fingerprint.

## Lifecycle, receipts, and released assets

### Status

The top-level lifecycle is exactly `draft`, `queued`, `running`,
`awaiting_review`, `released`, or `failed`. Assets from older builds may carry
the legacy `completed` status; see [Adopt a legacy asset](#adopt-a-legacy-asset).

### Receipts and resume

- Each completed stage has an atomic receipt commit marker under `receipts/`.
  `pipeline_state.json` references its hash, and `events.jsonl` retains the
  append-only history.
- Resume verifies the completed receipt prefix and rebuilds from its first
  invalid boundary.
- Missing or corrupt immutable raw snapshots require repair or a new asset.
- Presence-only raw validation is limited to a coherent Stage 1 lifecycle that
  has never claimed receipt or completion authority, including safe retry after
  a failure or process death before the first receipt.
- Once a completed-stage status, state receipt hash, receipt file, or
  completion event claims Stage 1 authority, revision and resume require a
  completed stage, the exact state-bound receipt hash, and receipt records that
  authenticate both copied raw files.

### Released assets

- A released asset is read-only.
- Verification binds the exact v2 control state, persisted configuration
  history, receipt chain, and required artifact hashes, while treating
  historical code identity as audit evidence.
- The final stage receipt also binds the exact configuration-history bytes,
  whose versioned row schemas, UTC timestamps, revision operations, and
  changed-field boundaries are verified.
- Any mismatch fails closed, and changes require a child version.

### Review and finalization

- After the Stage 7 receipt commits, an ordinary run stops at
  `awaiting_review`. Stage 8 has no authorization yet.
- Review decisions are append-only `approved` or `rejected` terminal rows bound
  to the complete current case, its scoring and generation dependencies, and
  source provenance.
- A missing, stale, or mismatched decision resolves to pending.
- Malformed decision authority blocks further decisions, finalization, and
  publication until it is repaired.
- Finalization requires two exact fingerprints, both revalidated under the
  asset lock before the snapshot is frozen:
  - the review-set fingerprint, which binds the current items, dependencies,
    and holds; and
  - the decision-set fingerprint, which binds every resolved eligible status
    and decision ID.
- Finalization may leave items pending. Stage 8 then publishes trusted cases
  and approved derived cases only.

### Exact-context duplicates

- Exact canonical model-visible-context duplicates are transitively united with
  supplied groups for splitting.
- An exact context with conflicting expected/scoring truth is held in full,
  not resolved by source, confidence, or order.
- This mechanism does not claim paraphrase or semantic-duplicate detection.

## Recovery journal and locking

### Recovery journal

Configuration revisions and checkpoint rebuilds use a write-ahead order:

1. Append a durable prepared record to `recovery_journal.jsonl`.
2. Make stale stage state nonauthoritative.
3. Only then remove stale files.

A later run rolls any prepared operation forward idempotently before it
evaluates the receipt chain. Before writing, recovery authenticates:

- the journal schema, operation, and tenant/asset identity;
- the complete pre-operation config/state snapshot;
- exact nested target semantics;
- byte-exact before/target prefixes for configuration history and events;
- prepare-before-commit order;
- before/target hashes; and
- only operation-reachable intermediate control pairs.

Journal rules:

- Version 2 operations form strict contiguous prepare/commit pairs with at most
  one trailing prepare.
- Consecutive operations also authenticate writer chronology through mutation
  identity, configuration history, and monotonic event prefixes, while
  allowing ordinary stage events between mutations.
- A committed legacy adoption is terminal and must retain its exact target
  config, state, receipts, and audit prefixes.
- When no operation remains outstanding, a final committed configuration
  revision or checkpoint rebuild must retain its exact target configuration
  and complete target configuration history. Its state and event log may
  continue through ordinary pipeline lifecycle and stage progress after the
  commit.
- Standalone candidate and released verification use this same complete
  journal validator.
- Pre-WAL history compatibility comes only from the final validated adoption
  transaction whose target hashes match the semantically replayed receipts,
  not from receipt origin labels.
- Version 1 or mixed-version journals require explicit repair because they
  lack the complete before-state evidence needed for safe roll-forward.

### Per-asset lock

- One cross-process per-asset hard lock protects create, run/resume, revision,
  adoption, and extension mutations across library, CLI, and service callers.
- `filelock` supplies bounded acquisition and reentrancy over the already
  identity-bound handle: POSIX uses `flock`, while Windows uses `LockFileEx`.
- Process-global exact-identity ownership distinguishes same-thread recursion
  from other threads that share one native handle.
- Bound handles record their opening process and fail closed if inherited
  across `fork`. Child work must reopen the literal path and revalidate its
  identity.
- Missing native hard-lock or atomic-CAS support fails explicitly instead of
  selecting a soft lock or check-then-replace fallback.

### Directory creation

Every evaluation-asset authority-root, authority-ancestor, stage, receipt,
publication-catalog, generation, and generation-staging directory creator also
locks the already-open parent and uses the same platform adapter with private
names, no-follow POSIX descriptors or reparse-rejecting Windows handles, exact
identity rechecks, and native no-replace installation.

- Windows retains the complete no-share-delete, reparse-checked ancestor handle
  chain until the bound directory closes.
- Darwin and Windows reject Unicode-normalized case-fold aliases in authority
  names.
- A movable Windows private directory is closed immediately before its
  exact-identity rename, and the installed name is reopened with stable
  no-share-delete guards.
- The reentrant parent lock also spans each complete single-file
  observe/create/CAS/sync/reclaim and generation
  collision/stage/install/sync/reclaim transaction.
- The finite production guard rejects other `Path.mkdir`, `os.mkdir`, and
  `os.makedirs` spellings, including literal persistence attributes
  constructed through `operator.attrgetter` or `operator.methodcaller`.
  Unresolved dynamic attribute names are outside this finite claim. Its
  authority adapter audits only named native create, write, CAS, and
  exact-owned reclamation functions.
- The remaining directory-creation compatibility seams are the generic parent
  bootstraps in `_atomic_write_text` and `_atomic_write_binary`, and the
  deprecated non-pipeline `assemble_dataset_bundle`. A live release check
  verifies that these three never bootstrap the authority or generation
  directories listed above.
- This boundary fails closed on preexisting or detectably substituted nodes.

### Limits of the locking model

- POSIX provides neither an atomic `mkdirat`-and-return-descriptor operation
  nor handle-conditional `unlink`/`rmdir`. Windows uses an identity-keyed
  parent mutex around create/open/install.
- Exact-owned POSIX reclamation is therefore safe against cooperating
  evaluation-asset writers that honor the same parent lock, not against an
  arbitrary noncooperating same-identity namespace swap.
- The workspace must not be concurrently mutated by an unaudited process
  running as the same OS identity during authority mutation. Use an exclusive
  trusted OS identity and filesystem permissions for the evaluation-asset
  workspace.

### Providers and service jobs

- Default providers are constructed only after the lock, recovery, lifecycle
  and immutable raw-snapshot checks, revision, and configuration reload.
- Injected providers must pass the strict provider/model/settings allowlists
  and secret-shaped-value rejection used by persisted provenance.
- Complete prospective call rows, stage provenance, and receipts validate in
  memory before calls or mutable writes. Receipts identify the provider
  instance and model actually used instead of substituting configured
  defaults.
- Service jobs persist `queued`, then return acceptance only after separate
  lock and preflight decisions from the live worker, without abandoning a
  lock-owning worker on a fixed timeout.
- A verified recovery that itself reaches `released` is accepted as a
  completed terminal resume before the worker exits.

## Publication

After Stage 8 succeeds, the authoritative split artifacts remain inside the
asset workspace, and a content-addressed consumer generation is installed at:

```text
tenants/<tenant_id>/datasets/evaluation_assets/<asset_id>/
├── release.json
└── generations/
    └── sha256-<generation-descriptor-hash>/
        ├── generation_manifest.json
        ├── train.jsonl
        ├── validation.jsonl
        ├── test.jsonl
        └── regression_trusted.jsonl
```

### Installing a generation

- The generation descriptor hashes all four files and the deterministic build
  fingerprint.
- A same-filesystem hidden temporary directory is validated and synced before
  one native no-replace operation installs the immutable generation.
- Exact content is reused, while an address collision fails without overwrite.
- Exact operation-owned staging, displaced, and quarantine nodes are reclaimed
  after success, ordinary Python exceptions, and recoverable retry paths.
- Raced foreign nodes and ambiguous durability failures are retained and fail
  closed. Hard process termination can therefore leave an unproven hidden node
  for explicit inspection; the next process does not scavenge by name.
- Immutable final generations are never garbage-collected. Old generations are
  retained; invalidation does not delete them or the release pointer.

### Release pointer

- `release.json` is the sole mutable catalog authority. It is replaced
  atomically only after the generation, Stage 8 receipt, build provenance,
  manifests, and hashes agree.
- Released state and its event follow the pointer under the recovery journal.
  Recovery therefore accepts only the reachable pointer/state/event phases and
  rolls an interrupted publication forward without rerunning providers.

### Consuming a release

- `asset_manifest.json` and the Stage 8 manifest expose the current generation
  ID, release pointer, hashes, and literal immutable paths.
- Evaluation configs do not interpret `release.json`. Set `dataset.path` to
  the exact generation file path recorded in a manifest.
- These paths are relative to the explicit repository/invocation base. CLI and
  service entry points reject a tenants root outside that base or traversing
  an intermediate symlink before writing.
- The pipeline does not upload these local derived files. A separate
  `customer-data --scope derived` operation can sync them only when the tenant
  storage configuration includes `datasets/` in its configured `derived_local`
  tree.

### Review block

Both manifests also contain an authenticated `review` block. It binds the
review-set fingerprint, finalization ID, Stage 7 receipt, exact
trusted/approved/pending/rejected/held counts, and canonical per-case
fingerprint inventory:

| Entry | Fingerprint |
|---|---|
| Trusted | Complete case-content fingerprint |
| Derived | Complete review fingerprint |
| Held | Exact fingerprint and reason |

Released verification recomputes this inventory from the persisted
finalization snapshot and fails closed on any count, identity, or fingerprint
mismatch.

## Provider-call provenance

- Stages 3–7 persist receipt-backed `provider_calls.jsonl` ledgers, including
  an empty ledger when a stage makes no call.
- `build_provenance.json` aggregates their body-free request/response hashes
  and separates deterministic identity from audit-only data:
  - **Identity** covers the complete declared source inventory, resolved
    configuration/defaults, runtime dependencies, copied input hashes, lineage,
    provider/model/settings, prompt revisions and hashes, seeds, and
    algorithms.
  - **Audit-only** data covers timestamps, Git commit/tree and dirt, request
    IDs, token usage, and retries.
- Optional transport metadata is strictly allowlisted. Custom providers
  without the metadata protocol record an explicit unavailable marker.
- Full prompts, requests, responses, headers, exceptions, and credentials are
  never serialized for provenance.

Stages 6 and 7 also persist full-content dependency authority. The Stage 7
review fingerprint binds the complete pre-publication case, its dependency
descriptor, and source provenance. A child may inherit a parent approval or
rejection only when both that fingerprint and the canonical case bytes are
identical; changed content or dependencies return the child item to pending.

## CLI

### Create and run

Set the relevant provider credential, then create and run the asset:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"

python -m hephaestus.cli assets create \
  --tenant <tenant_id> \
  --asset-id v1 \
  --feedback <labeled_feedback.jsonl> \
  --unlabeled <unlabeled.jsonl> \
  --rubric-model gpt-6-luna \
  --embedding-model text-embedding-3-small \
  --clusters 20

python -m hephaestus.cli assets run \
  --tenant <tenant_id> \
  --asset-id v1

python -m hephaestus.cli assets status \
  --tenant <tenant_id> \
  --asset-id v1
```

| Option | Effect |
|---|---|
| `--enable-synthetic-coverage --synthetic-cases-per-cluster <count>` | Enable Stage 7 synthesis. Requires `--clusters` greater than zero. |
| `--embedding-model tfidf` | Deterministic local vectorization without an embedding API call. |
| `--clusters <count>` | Intent cluster count; the default is 50. |
| `--clusters 0` | Skip Stages 4 and 5. Their receipts and empty artifacts remain in the eight-stage workspace, but no embedding or cluster sampling work is performed. Stage 6 still builds every episode rubric from its trace and split-permitted guidelines. |

FAFO never silently changes providers after a failure.

### Review and finalize

The first `assets run` returns after Stage 7 with `status: awaiting_review`.
Scoreable inferred cases and mechanically accepted synthetic cases are
automatically approved by the FAFO data pipeline. List the bounded review
snapshot to inspect approvals and holds, and keep its `review_set_fingerprint`
and `decision_set_fingerprint`:

```bash
python -m hephaestus.cli assets reviews list \
  --tenant <tenant_id> \
  --asset-id v1
```

- The page applies `--offset` and `--limit` to one combined, deterministic
  projection of eligible and held rows. The sum of returned `items` and `held`
  never exceeds `--limit`.
- `--limit` must be from 1 through 100.
- `--status` accepts `pending`, `approved`, `rejected`, or `held`, and filters
  that projection before pagination.

The `approve` and `reject` commands remain available for pending items in
compatible or historical workflows. Each decision must use both the item's
exact case fingerprint and the current review-set fingerprint:

```bash
python -m hephaestus.cli assets reviews approve \
  --tenant <tenant_id> \
  --asset-id v1 \
  --case-id <case_id> \
  --fingerprint <sha256:fingerprint> \
  --reviewer <reviewer_name> \
  --review-set <sha256:review_set_fingerprint>
```

Use `assets reviews reject` with the same arguments for a rejection.

For normal FAFO runs, inspect the automatic decisions and holds, then finalize.
Finalization explicitly freezes the exact item/dependency and resolved-decision
snapshot and synchronously builds and publishes Stage 8:

```bash
python -m hephaestus.cli assets reviews finalize \
  --tenant <tenant_id> \
  --asset-id v1 \
  --reviewer <reviewer_name> \
  --review-set <sha256:review_set_fingerprint> \
  --decision-set <sha256:decision_set_fingerprint>
```

- Finalization does not implicitly approve pending items.
- A pending-only finalization is valid and publishes zero derived cases.
- Replaying finalization for a released asset is idempotent only with both
  exact current fingerprints.

### Revise settings on resume

To change decisions while resuming, pass only the settings that should change:

```bash
python -m hephaestus.cli assets run \
  --tenant <tenant_id> \
  --asset-id v1 \
  --clusters 12 \
  --embedding-model tfidf
```

| Changed setting | Restarts at |
|---|---|
| Split seed (trusted assignment precedes authoring) | Stage 2 |
| Guideline model | Stage 3 |
| Embedding model or cluster count | Stage 4 |
| Synthetic settings | Stage 7 |

- Legacy matching/support options remain readable for older configurations but
  do not drive rubric generation.
- Each revision is prepared in the recovery journal, then applied to
  `config.json`, `pipeline_state.json`, `config_history.jsonl`, and
  `events.jsonl`.
- Stale downstream outputs are cleaned only after their state and receipt
  references are nonauthoritative.

### Extend a released asset

Extend a verified released version:

```bash
python -m hephaestus.cli assets extend \
  --tenant <tenant_id> \
  --parent-asset-id v1 \
  --asset-id v2 \
  --additional-feedback <additional_feedback.jsonl> \
  --clustering-mode keep
```

Use `--additional-unlabeled <additional_unlabeled.jsonl>
--clustering-mode refresh` when the intent landscape must be rebuilt.

### Adopt a legacy asset

Assets created by an older build may retain the pre-v2 top-level status
`completed`. It is a legacy sentinel, not an alias for `released`. Verify and
adopt it explicitly before extension:

```bash
python -m hephaestus.cli assets adopt \
  --tenant <tenant_id> \
  --asset-id <legacy_asset_id>
```

Adoption accepts only pre-v2 `completed`. It:

- validates all eight stages, raw source hashes, strict finite artifact
  schemas, deterministic Stage 7 filter outputs, both manifests, and the
  current four catalog copies;
- records unavailable historical prompt/provider/code facts honestly;
- materializes an immutable generation; and
- publishes it with receipts, pointer, released state, event, and commit as
  one terminal `legacy_adoption` operation.

After adoption, the old top-level catalog copies become nonauthoritative.

On failure, adoption leaves legacy authority unchanged or rolls the prepared
adoption forward; it requires repair or a new asset only when authenticated
evidence is inconsistent.

A v2 released checkpoint without `release.json` is an unpublished interim
build. Repair it from a verified backup or rebuild it as a new asset version;
adoption is not a migration path.
