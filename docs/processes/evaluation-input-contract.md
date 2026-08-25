<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Evaluation Input Contract

## Purpose

`fapo-evaluation-input-v1` is the vendor-neutral boundary between source data
systems and the evaluation-asset pipeline. Both labeled and unlabeled JSONL
files must conform before asset creation. The core never contains field-name
mappings for observability vendors, products, or tenants.

Source-specific exporters or adapters may convert external records into this
contract, but they run before the evaluation-asset workflow:

```text
Vendor or application export
        ↓
Source-specific conversion
        ↓
FAPO Evaluation Input v1 JSONL
        ↓
Eight-stage evaluation-asset pipeline
```

Stage 1 validates every record and stops on the first precise
`file:row:field` error. Blank lines are not records, but diagnostics retain the
physical JSONL line number across source validation, copied-input validation,
and normalized-identity checks. Stage 2 consumes and preserves the canonical
names below. It applies schema-aware redaction only to content-bearing fields,
including every nested string below an explicitly content-bearing mapping or
list, applies documented defaults, and may add derived fields, but it does not
rename or rewrite source identity, routing, role, or structural tool-name
fields. In particular, `schema_version`, `record_id`, `group_id`, `request_id`,
`task_type`, `route`, intent labels, message roles, and tool names remain
byte-for-byte unchanged at their defined structural paths. Stage 2 rechecks
normalized `record_id` uniqueness and reports both physical source rows and
source IDs if a transformation creates a collision. It then derives a
`split_group_id`, assigns connected trusted groups to a split before guideline
authoring, and records whether each feedback row has minimum usable correctness
evidence. These are internal derived fields; the supplied `group_id` remains
unchanged.

## Common Record

Every labeled and unlabeled row is one JSON object with these required fields:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Must equal `fapo-evaluation-input-v1` |
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

`record_id` values must be unique within each file. `group_id` is mandatory;
for a genuinely independent record, use its `record_id`. The core additionally
unites supplied groups that share exact canonical model-visible context into a
derived `split_group_id` for split safety. It does not use embeddings,
case-folding, whitespace folding, token overlap, or paraphrase similarity for
that identity.

The effective routing identity is exact and shared by Stage 1 preflight,
prepared records, clustering, and coverage matching. When `route` is present,
its string is used byte-for-byte, including leading or trailing whitespace;
only an absent `route` falls back to the exact `task_type`. Adapters should
canonicalize routes before this boundary if whitespace distinctions are not
meaningful in their source system.

## Conversation Messages

Every `conversation_context` item requires:

```json
{
  "role": "user",
  "content": "Earlier conversation content"
}
```

Both fields are nonempty strings. Additional vendor-neutral message metadata
may be retained. Downstream canonical intent text includes every prior message
whose role is exactly `user`, in conversation order; assistant messages are
not included.

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

The clustering representation retains deduplicated tool names. Rubric
extraction may inspect the full redacted tool-call objects.

## Labeled Records

Labeled rows additionally require:

- `assistant_output`, as a string. It may be empty when the observed failure
  produced no response.
- `feedback`, as an object containing:
  - `polarity`: `positive`, `negative`, or `mixed`.
  - `rationale`: a string, which may be empty when only categorical feedback
    exists.

Optional feedback fields include:

- `correction`: corrected output or structured correction evidence.
- `source`: nonempty source category such as `user`, `annotator`, or `sme`.
- `correctness_signals`: an array of closed objects requiring `kind`
  (`deterministic` or `executable`), a nonempty `check_id`, and boolean
  `passed`. An optional `content` field may carry arbitrary content-bearing
  evidence and is redacted by the core. The core treats the signal as evidence
  that an external check ran; it does not infer the check's meaning or
  trustworthiness.
- Additional provenance that does not change the meaning of the canonical
  fields.

A labeled row remains contract-valid when `rationale` is empty and both
`correction` and `correctness_signals` are absent. Stage 2 handles that separate
semantic boundary: the row remains auditable but is marked
`insufficient_correctness_evidence`, causes no guideline provider call when it
is the only evidence in its visibility unit, and creates no active trusted
case. A nonempty rationale, a material correction, or a well-formed declared
correctness signal satisfies only this minimum eligibility gate; it does not
prove factual correctness, safety, privacy, or absence of contradiction.

Example:

```json
{
  "schema_version": "fapo-evaluation-input-v1",
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
correctness.

Example:

```json
{
  "schema_version": "fapo-evaluation-input-v1",
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

An `assistant_output` may be retained on an unlabeled row for provenance, but
it does not become correctness evidence.

## Validation Rules

Stage 1 rejects:

- Missing required fields.
- A missing or unsupported `schema_version`.
- Empty identifier, grouping, task, or user-input strings.
- Duplicate `record_id` values within one file.
- Incorrect array or object types.
- Malformed conversation messages or tool calls.
- Labeled records without `assistant_output` or canonical feedback.
- Feedback polarities outside the three canonical values.
- Malformed `correctness_signals`, including unsupported kinds, blank check
  IDs, non-boolean outcomes, or unsupported fields; `content` is the only
  optional field.
- Unlabeled records containing feedback.
- A requested cluster count greater than the copied unlabeled row count.
- A requested cluster count smaller than the number of distinct effective
  routes, using the exact routing identity defined above.

Stage 1 performs these checks against the copied Stage 1 files before any
evaluation-guideline or embedding provider call.

The contract endpoint used by the Studio and adapters is:

```text
GET /api/evaluation-assets/input-contract
```

## Adapter Responsibility

An external adapter is responsible for joining vendor-specific trace and
feedback resources, traversing child spans, extracting messages, standardizing
tool calls, assigning stable groups, and mapping feedback into canonical
polarity and rationale. If an adapter emits `correctness_signals`, it is also
responsible for assigning a stable `check_id` and ensuring that the recorded
boolean is the actual outcome of that deterministic or executable check.

Because the shared core intentionally preserves identifiers and routing fields,
an adapter must replace identifiers with stable pseudonyms before this boundary
when organizational privacy policy prohibits retaining source identifiers. The
adapter must preserve equality and grouping relationships while doing so; core
content redaction is not identifier pseudonymization.

Adapters must not implement evaluation-guideline creation, clustering,
coverage decisions, label inference, synthetic generation, or dataset
splitting. Those operations remain in the shared core after the contract
boundary.
