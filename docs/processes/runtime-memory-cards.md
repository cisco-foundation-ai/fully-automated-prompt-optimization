<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Runtime memory card construction

The runtime-memory pipeline is an optional downstream step after a FAFO
evaluation asset is released. It does not modify the evaluation asset and is
separate from FAFO prompt optimization.

The initial contract is intentionally small:

1. Read the reusable evaluation guidelines created from trusted training
   feedback.
2. Join each guideline to a bounded sample of its supporting trusted traces.
3. Ask one JSON-generation model call to turn the guideline and traces into a
   procedural memory card.
4. Reject any instruction that does not cite a real criterion from the source
   guideline.
5. Write the cards and a source-hash manifest under the tenant's
   `memory_assets/` directory.

There is no episode pairing, reward-model training, learned re-ranking, or
online memory promotion. Trusted-only construction is the final default. An
explicit additive mode can use approved inferred training traces to broaden
procedural coverage while keeping the trusted guideline and trusted card as the
only normative sources.

## Build a memory asset

First release the source evaluation asset through the normal FAFO review and
finalization flow. Then run:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"

python -m hephaestus.cli memory build \
  --tenant <tenant_id> \
  --asset-id <released_evaluation_asset_id> \
  --memory-id <memory_asset_id>
```

This command always uses trusted guidelines and trusted feedback traces. It
does not read the inferred split. The generation model defaults to the source
asset's rubric model. Override it
with `--model <model>`. At most five trusted traces are supplied to each call by
default; use `--max-source-traces <count>` to change that bound.

The command writes:

```text
tenants/<tenant_id>/memory_assets/<memory_asset_id>/
├── manifest.json
├── memory_cards.jsonl
└── provider_calls.jsonl
```

The command refuses to replace an existing memory asset. Use a new memory ID for
a new generation.

### Explicitly add approved inferred training evidence

The additive builder is the scalable alternative to placing a larger raw-trace
sample into one card-generation call:

```bash
python -m hephaestus.cli memory build-additive \
  --tenant <tenant_id> \
  --asset-id <released_evaluation_asset_id> \
  --base-memory-id <trusted_only_memory_asset_id> \
  --memory-id <additive_memory_asset_id> \
  --include-approved-inferred \
  --batch-size 8 \
  --max-additions-per-card 3
```

The required `--include-approved-inferred` flag makes this a deliberate opt-in.
Without it, the command does not run. The builder processes every row in the
released inferred training split exactly
once. It interleaves source clusters across bounded batches and asks the model
to mine only procedures, avoidances, tool guidance, and examples that are both
new relative to the trusted card and grounded in trusted guideline criteria.
Exact duplicate patterns are merged with their supporting trace and cluster
counts. A second model pass per guideline selects at most the configured number
of additions.

The trusted card is a frozen spine: its title, summary, applicability,
instructions, avoidances, tool guidance, and examples are copied unchanged.
Selected inferred additions are appended, never substituted. The output also
contains `evidence_patterns.jsonl`, `card_additions.jsonl`, and
`trace_index.jsonl` so every addition can be traced through a mined pattern to
approved training records without republishing raw trace content.

## Card contract

One card is produced for each reusable trusted guideline. A card contains:

- conditional `when_to_use` and `when_not_to_use` descriptions;
- ordered procedural instructions;
- behaviors to avoid;
- optional tool guidance;
- optional abstract example steps;
- an agent-ready `injection_text` rendering;
- source guideline, criterion, and record provenance;
- model and prompt revision metadata.

Every instruction, avoidance, and tool-guidance item must cite at least one
criterion ID from its source guideline. Example steps must cite one of the
trusted traces actually supplied to the model. These citations remain in the
JSON artifact for auditability and are omitted from `injection_text`.

## Trust and split isolation

By default, only guidelines from
`stages/03_evaluation_guidelines/evaluation_guidelines.jsonl` are compiled.
Their supporting records must be both `evidence_eligible: true` and assigned to
the trusted `train` split. The builder fails closed if a guideline refers to a
validation, test, regression, ineligible, or missing feedback record.

This keeps runtime memory and evaluation ground truth separated. The optional
additive mode expands evidence from the released inferred training split only;
validation, test, regression, held, rejected, and pending cases remain
unavailable to the builder.

## Intended experiment

Keep the agent prompt, model, temperature, policy, tools, user simulator, and
task split fixed. Compare two runtime conditions:

1. Retrieve and inject the applicable source FAFO guideline.
2. Retrieve and inject the corresponding memory card's `injection_text`.

Evaluate both with the same native benchmark scorer. Log the retrieved artifact
ID, retrieval score, injected text hash, token count, latency, and native task
result so the effect of proceduralization can be measured independently from
retrieval changes.
