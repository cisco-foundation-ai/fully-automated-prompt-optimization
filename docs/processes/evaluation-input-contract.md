<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Evaluation Input Contract

`fafo-evaluation-input-v1` is the vendor-neutral JSONL format for both input
files of the evaluation-asset pipeline: labeled feedback and unlabeled traces.
Read it if you write an exporter or adapter that converts source data into
pipeline inputs.

Both files must conform before asset creation. The core never contains
field-name mappings for observability vendors, products, or tenants.
Source-specific exporters or adapters convert external records into this
contract before the evaluation-asset workflow runs:

```text
Vendor or application export
        ↓
Source-specific conversion
        ↓
FAFO Evaluation Input v1 JSONL
        ↓
Eight-stage evaluation-asset pipeline
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
- The core also unites supplied groups that share exact canonical
  model-visible context into a derived `split_group_id` for split safety. It
  does not use embeddings, case-folding, whitespace folding, token overlap, or
  paraphrase similarity for that identity.

### Routing identity

The effective routing identity is exact and shared by Stage 1 preflight,
prepared records, clustering, and coverage matching:

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

## Intent Text

The pipeline builds canonical intent text for clustering from user messages
only:

- **With an episode that contains user messages:** every such message
  contributes, in event order. Episode messages are authoritative over the
  backward-compatible flat message fields. Repeated user messages are
  retained.
- **Without an `episode`:** every prior `conversation_context` message whose
  role is exactly `user`, followed by the current `user_input`.
- Canonical user messages are separated by newlines in the text supplied for
  clustering.
- Assistant messages and tool activity do not enter the intent text. Prepared
  intent records retain deduplicated tool names as structural trajectory
  metadata, but tool names are not included in intent-embedding text.

Clusters are sampling and analysis metadata; they do not select guidelines or
determine rubric correctness.

## Labeled Records

Labeled rows additionally require:

- `assistant_output`, as a string. It may be empty when the observed failure
  produced no response.
- `feedback`, as an object containing `polarity`: `positive`, `negative`, or
  `mixed`.

Optional `feedback` fields:

| Field | Contents |
|---|---|
| `rationale` | A string or `null`. It may be omitted when only categorical feedback exists. Stage 2 normalizes an absent or null value to an empty string. |
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

Stage 1 validates every record and stops on the first precise
`file:row:field` error. Blank lines are not records, but diagnostics retain the
physical JSONL line number across source validation, copied-input validation,
and normalized-identity checks.

Stage 1 runs the checks below against the copied Stage 1 files, before any
evaluation-guideline or embedding provider call. It rejects:

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
- When clustering is enabled, a requested cluster count greater than the
  copied unlabeled row count.
- When clustering is enabled, a requested cluster count smaller than the
  number of distinct effective routes, using the exact
  [routing identity](#routing-identity). A count of zero skips Stages 4 and 5.

Adapters can fetch the contract from the FAFO Explorer server
(`python -m hephaestus.cli ui`) at:

```text
GET /api/evaluation-assets/input-contract
```

## What Stage 2 Preserves and Adds

Stage 2 consumes and preserves the canonical names above:

- It applies schema-aware redaction only to content-bearing fields, including
  every nested string below an explicitly content-bearing mapping or list.
- It applies documented defaults and may add derived fields.
- It does not rename or rewrite source identity, routing, role, or structural
  tool-name fields. `schema_version`, `record_id`, `group_id`, `request_id`,
  `task_type`, `route`, intent labels, message roles, and tool names remain
  byte-for-byte unchanged at their defined structural paths.
- It rechecks normalized `record_id` uniqueness and reports both physical
  source rows and source IDs if a transformation creates a collision.
- It derives a `split_group_id`, assigns connected trusted groups to a split
  before guideline authoring, and records whether each feedback row has
  minimum usable correctness evidence. These are internal derived fields; the
  supplied `group_id` remains unchanged.

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

Adapters must not implement evaluation-guideline creation, clustering,
case-specific rubric generation, synthetic generation, or dataset splitting.
Those operations remain in the shared core after the contract boundary.
