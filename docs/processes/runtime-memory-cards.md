<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Runtime memory card construction

Runtime memory cards turn the guideline catalog of an evaluation asset into
compact procedural cards that an agent reads at runtime. This optional
downstream step does not modify the asset and is separate from FAFO prompt
optimization.

The contract is intentionally small:

1. Read the catalog guidelines of a finished asset (one with
   `manifest.json`), built by `assets build`.
2. Join each guideline to a bounded sample of its supporting train feedback
   episodes.
3. Ask one JSON-generation model call to turn the guideline and episodes into
   a procedural memory card.
4. Reject any instruction that does not cite a real criterion from the
   guideline.
5. Write the cards and a source-hash manifest under the tenant's
   `memory_assets/` directory.

There is no episode pairing, reward-model training, learned re-ranking, or
online memory promotion. Trusted-only construction is the default. An
explicit additive mode can use inferred training cases to broaden procedural
coverage, while the guideline and the trusted card stay the only normative
sources.

## Build a memory asset

Build the source asset first (see the
[data pipeline reference](../references/data-pipeline.md)), then run:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"

python -m hephaestus.cli memory build \
  --tenant <tenant_id> \
  --asset-id <evaluation_asset_id> \
  --memory-id <memory_asset_id>
```

This command uses only guidelines backed by train feedback and only those
feedback episodes; it does not read the inferred cases.

| Option | Default |
|---|---|
| `--model <model>` | The model the source asset was built with |
| `--max-source-traces <count>` | At most five feedback episodes per call, leading with one positive and one negative |

The command writes:

```text
tenants/<tenant_id>/memory_assets/<memory_asset_id>/
├── manifest.json
├── memory_cards.jsonl
└── provider_calls.jsonl
```

It refuses to replace an existing memory asset. Use a new memory ID for a new
generation.

### Explicitly add inferred training evidence

The additive builder is the scalable alternative to putting a larger raw-trace
sample into one card-generation call:

```bash
python -m hephaestus.cli memory build-additive \
  --tenant <tenant_id> \
  --asset-id <evaluation_asset_id> \
  --base-memory-id <trusted_only_memory_asset_id> \
  --memory-id <additive_memory_asset_id> \
  --include-inferred \
  --batch-size 8 \
  --max-additions-per-card 3
```

The `--include-inferred` flag is required, which makes this a deliberate
opt-in. The builder then:

- processes every inferred `train` case that applied at least one guideline,
  exactly once; trace-inferred cases, which applied none, are skipped;
- interleaves `group_id`s across bounded batches;
- asks the model to mine only procedures, avoidances, tool guidance, and
  examples that are new relative to the trusted card and grounded in the
  guideline's criteria;
- merges exact duplicate patterns, with their supporting trace and group
  counts; and
- runs a second model pass per guideline that selects at most the configured
  number of additions.

The trusted card is a frozen spine: its title, summary, applicability,
instructions, avoidances, tool guidance, and examples are copied unchanged.
Selected additions are appended, never substituted. The output also contains
`evidence_patterns.jsonl`, `card_additions.jsonl`, and `trace_index.jsonl`, so
every addition can be traced through a mined pattern to training records
without republishing raw trace content.

## Card contract

One card is produced for each catalog guideline backed by train feedback. A
card contains:

- conditional `when_to_use` and `when_not_to_use` descriptions;
- ordered procedural instructions;
- behaviors to avoid;
- optional tool guidance;
- optional abstract example steps;
- an agent-ready `injection_text` rendering;
- source guideline, criterion, and record provenance; and
- model and prompt revision metadata.

Citation rules:

- Every instruction, avoidance, and tool-guidance item must cite at least one
  criterion ID from its source guideline.
- Example steps must cite one of the feedback episodes actually supplied to
  the model.
- Citations stay in the JSON artifact for auditability and are omitted from
  `injection_text`.

## Trust and split isolation

Only guidelines that entered the catalog are compiled. Their supporting
records come from the guideline's lessons, and each must be a `train` record
in `splits.jsonl`; the builder fails closed otherwise. A guideline whose
lessons all came from unlabeled traces is skipped and listed in the
manifest's `skipped_guideline_ids`.

Episodes are redacted the same way the asset build redacted them, and the
model sees them only under aliases, never by record ID.

This keeps runtime memory and evaluation ground truth separate. The additive
mode reads only inferred `train` cases; validation, test, and regression
cases remain unavailable to both builders.

## Intended experiment

Keep the agent prompt, model, temperature, policy, tools, user simulator, and
task split fixed. Compare two runtime conditions:

1. Retrieve and inject the applicable source guideline.
2. Retrieve and inject the corresponding memory card's `injection_text`.

Evaluate both with the same native benchmark scorer. Log the retrieved
artifact ID, retrieval score, injected text hash, token count, latency, and
native task result, so the effect of proceduralization can be measured
independently from retrieval changes.
