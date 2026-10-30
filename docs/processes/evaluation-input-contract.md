<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Evaluation Input Contract

`fafo-evaluation-input-v1` is the vendor-neutral JSONL format for both input
files of the FAFO data pipeline: labeled feedback and unlabeled traces.
Read it if you write an exporter or adapter that converts source data into
pipeline inputs.

Both files must conform before `assets build` runs. The core never contains
field-name mappings for observability vendors, products, or tenants.
Source-specific exporters or adapters convert external records into this
contract first:

```text
Vendor or application export
        ↓
Source-specific conversion
        ↓
FAFO Evaluation Input v1 JSONL
        ↓
FAFO data pipeline (assets build)
```

## Common Record

Every labeled and unlabeled row is one JSON object with these required fields:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Must equal `fafo-evaluation-input-v1` |
| `record_id` | nonempty string | Stable unique identifier within the file |
| `group_id` | nonempty string | Conversation or leakage-boundary group used for splitting |
| `task_type` | nonempty string | Application-defined task family |
| `user_input` | nonempty string | Current request being represented |
| `conversation_context` | array of message objects | Prior messages only; exclude the current `user_input` |
| `tool_calls` | array of tool-call objects | Tools observed while handling this request |
| `runtime` | object | Model, application, deployment, or tool-set runtime facts |
| `metadata` | object | Non-runtime provenance and source metadata |

Optional common fields:

| Field | Type | Default |
|---|---|---|
| `request_id` | nonempty string | `record_id` |
| `route` | nonempty string | `task_type` |
| `assistant_output` | string | Omitted for unlabeled records when unavailable |
| `episode` | object | Omitted when the source has no complete event stream |

### Groups

- `group_id` is mandatory. For a genuinely independent record, use its
  `record_id`.
- The core also joins records that share an exact model-visible context
  (messages, tool context, and runtime) into one connected group, so they
  land in the same split. It does not use embeddings, case-folding,
  whitespace folding, token overlap, or paraphrase similarity for that.

### Routing identity

The effective routing identity is exact. The pipeline builds one guideline
catalog section per route:

- When `route` is present, its string is used byte-for-byte, including leading
  or trailing whitespace.
- Only an absent `route` falls back to the exact `task_type`.

Adapters should canonicalize routes before this boundary if whitespace
distinctions are not meaningful in their source system.

## Conversation Messages

Every `conversation_context` item requires:

```json
{
  "role": "user",
  "content": "Earlier conversation content"
}
```

Both fields are nonempty strings. Additional vendor-neutral message metadata
may be retained.

## Tool Calls

Every `tool_calls` item requires:

```json
{
  "name": "lookup_records",
  "arguments": {
    "query": "..."
  },
  "result": null,
  "error": null
}
```

- `name` is a nonempty string.
- `arguments` is an object, including when empty.
- `result` is optional and may contain any JSON value.
- `error` is optional and must be a string or `null`.

Rubric extraction may inspect the full redacted tool-call objects.

## Episodes

An optional `episode` preserves a complete, ordered interaction without
overloading `conversation_context`, `assistant_output`, or flat `tool_calls`:

```json
{
  "episode_id": "episode-000001",
  "termination_reason": "completed",
  "events": [
    {
      "sequence": 0,
      "type": "message",
      "role": "user",
      "content": "Find my order."
    },
    {
      "sequence": 1,
      "type": "tool_call",
      "call_id": "call-000001",
      "name": "lookup_order",
      "arguments": {"order_id": "..."}
    },
    {
      "sequence": 2,
      "type": "tool_result",
      "call_id": "call-000001",
      "result": {"status": "shipped"}
    },
    {
      "sequence": 3,
      "type": "message",
      "role": "assistant",
      "content": "Your order has shipped."
    }
  ]
}
```

- `episode_id` and `termination_reason` are optional nonempty strings.
- `episode.events` must be a nonempty array.
- Every event requires a unique, strictly increasing nonnegative integer
  `sequence` and one of these types:

| `type` | Requires | Rules |
|---|---|---|
| `message` | Nonempty `role` and `content` strings | |
| `tool_call` | A nonempty `call_id`, a nonempty `name`, and an `arguments` object | Call IDs may not be reused within the episode |
| `tool_result` | A `call_id` that references an earlier tool call, and at least one of `result` or `error` | A call may have only one result event; `error`, when present, must be a string or `null` |

The pipeline preserves event order and call/result links, redacts
content-bearing fields, and exposes the redacted episode to feedback-evidence
extraction.

The flat fields remain required for backward compatibility. Adapters should
populate `user_input`, `conversation_context`, `tool_calls`, and, when
applicable, `assistant_output` with their conventional summary view of the
same interaction.

An episode is observed context, not correctness evidence or an answer key.
Only the canonical feedback on a labeled record supports evaluation-guideline
claims. An unlabeled episode remains usage evidence even when it contains tool
results or a successful termination reason.

## Labeled Records

Labeled rows additionally require:

- `assistant_output`, as a string. It may be empty when the observed failure
  produced no response.
- `feedback`, as an object containing `polarity`: `positive`, `negative`, or
  `mixed`.

Optional `feedback` fields:

| Field | Contents |
|---|---|
| `rationale` | A string or `null`. It may be omitted when only categorical feedback exists. |
| `correction` | Corrected output or structured correction evidence. |
| `source` | Nonempty source category such as `user`, `annotator`, or `sme`. |
| `correctness_signals` | An array of closed objects requiring `kind` (`deterministic` or `executable`), a nonempty `check_id`, and boolean `passed`. An optional `content` field may carry arbitrary content-bearing evidence and is redacted by the core. |

Feedback may also carry additional provenance that does not change the meaning
of the canonical fields.

How the core weighs this evidence:

- A labeled row with only a valid polarity remains eligible for guideline and
  rubric creation.
- Polarity is a coarse assessment of the episode. It does not identify a
  particular mistake, correct tool choice, or reference answer. Guidelines and
  case rubrics must use the explicit request and observable trace without
  inventing the missing rationale.
- A rationale, material correction, or declared check supplies more specific
  evidence when available.
- The core treats a correctness signal as evidence that an external check ran;
  it does not infer the check's meaning or trustworthiness.
- None of these signals alone proves factual correctness, safety, privacy, or
  absence of contradiction.

Example:

```json
{
  "schema_version": "fafo-evaluation-input-v1",
  "record_id": "feedback-000001",
  "group_id": "conversation-000001",
  "request_id": "request-000001",
  "task_type": "general_assistant",
  "route": "general_assistant",
  "user_input": "Process the supplied input.",
  "conversation_context": [],
  "assistant_output": "A previous response.",
  "tool_calls": [],
  "runtime": {
    "model": "model-name",
    "application_version": "version"
  },
  "metadata": {
    "source_system": "application-export"
  },
  "feedback": {
    "polarity": "negative",
    "rationale": "The response omitted a required qualification.",
    "correction": null,
    "source": "user"
  }
}
```

The previous assistant output is context for evaluation-guideline creation,
not an answer key.

## Unlabeled Records

Unlabeled rows must not contain `feedback`. They describe usage, not
correctness. An `assistant_output` may be retained for provenance, but it does
not become correctness evidence.

Example:

```json
{
  "schema_version": "fafo-evaluation-input-v1",
  "record_id": "trace-000001",
  "group_id": "conversation-000002",
  "request_id": "request-000002",
  "task_type": "general_assistant",
  "user_input": "Compare the two available options.",
  "conversation_context": [
    {
      "role": "user",
      "content": "Earlier conversation content"
    }
  ],
  "tool_calls": [
    {
      "name": "lookup_records",
      "arguments": {},
      "result": null,
      "error": null
    }
  ],
  "runtime": {},
  "metadata": {}
}
```

## Validation Rules

`assets build` validates every record before any model call and stops on
the first precise `file:row:field` error. Blank lines are not records, but
diagnostics keep the physical JSONL line number. It rejects:

- Missing required fields.
- A missing or unsupported `schema_version`.
- Empty identifier, grouping, task, or user-input strings.
- Duplicate `record_id` values within one file.
- Incorrect array or object types.
- Malformed conversation messages, tool calls, or episode events.
- Episode events with invalid ordering, reused call IDs, tool results without
  a prior call, or multiple results for one call.
- Labeled records without `assistant_output` or canonical feedback.
- Feedback polarities outside the three canonical values.
- Malformed `correctness_signals`, including unsupported kinds, blank check
  IDs, non-boolean outcomes, or unsupported fields; `content` is the only
  optional field.
- Unlabeled records containing feedback.
- A `record_id` that appears in both files.
- An empty feedback file.

A failed validation starts nothing, so the build can rerun once the input is
fixed. Adapters can validate their output with `validate_input_records` and
read a machine-readable summary from `input_contract_document()`, both in
`src/hephaestus/data_pipeline/contract.py`.

## What the Pipeline Preserves and Adds

- Redaction replaces email and IPv4 addresses in every string and object key
  except the identity fields `schema_version`, `record_id`, `group_id`,
  `request_id`, `task_type`, and `route`. Set `redact: false` in the build
  config when replay needs exact values.
- No field is renamed, and identity fields stay byte-for-byte unchanged.
- Connected groups are assigned to splits before any model call. The split
  and group of each record are written to the asset's `splits.jsonl`; the
  supplied `group_id` is unchanged.

## Adapter Responsibility

An external adapter is responsible for:

- joining vendor-specific trace and feedback resources;
- traversing child spans, extracting messages, and standardizing tool calls;
- constructing an ordered episode when the source provides one;
- assigning stable groups;
- mapping feedback into canonical polarity and any available rationale; and
- if it emits `correctness_signals`, assigning a stable `check_id` and ensuring
  that the recorded boolean is the actual outcome of that deterministic or
  executable check.

The shared core intentionally preserves identifiers and routing fields. When
organizational privacy policy prohibits retaining source identifiers, the
adapter must replace them with stable pseudonyms before this boundary,
preserving equality and grouping relationships. Core content redaction is not
identifier pseudonymization.

Adapters must not implement guideline creation, case-specific rubric
generation, or dataset splitting.
Those operations remain in the shared core after the contract boundary.
