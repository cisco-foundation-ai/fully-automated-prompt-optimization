<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Prompt & Skill Contract

## Artifact Layout
- **Base prompt**: `prompts/modules/agent/variant-NNN.md` — the ReAct loop, Splunk
  MCP tool catalog, and core grounding rules. It does **not** reference or inline
  skills; a reader sees a clean prompt.
- **Skill files**: `skills/<skill-name>/variant-NNN.md` — one reusable procedure
  each, with YAML frontmatter (`name`, `description`). Loaded at the agentic layer
  into a runtime `<available_skills>` context message, not into the prompt.

## Output Format Contract
- The agent must emit its final answer after an `Answer:` marker so the final
  response is unambiguous in `output_text`.
- For multi-part questions (e.g. "indexing failures **and** skipped searches"),
  the answer should use Markdown sections (e.g. `## Indexing Failures`,
  `## Skipped Searches`).
- The final answer must be correct relative to the case's
  `expected.answer_contains` reference and grounded in tool results.
- Intermediate reasoning and tool calls are expected; only the final answer is
  scored for correctness (by the judge), while the tool trajectory is scored
  deterministically.

## Decision Policy
The decision policy lives in the **skill files** (so it can be optimized
independently of the base scaffold):
- **Index inventory / superlative** → `tool-selection` and
  `superlative-index-questions` skills (list → drill-in; mandatory
  `splunk_get_index_info` before answering a size/count/contents question).
- **User lookup** → `tool-selection` skill (`splunk_get_user_list` for other
  users; `splunk_get_user_info` only for the current account).
- **Event-data / search** → `spl-search` skill (write SPL, run `splunk_run_query`,
  honor the time range; the `rest` command is blocked; `saia_*` tools unavailable).
- **Answer shape** → `answer-formatting` skill (decisive, exhaustive lists, direct
  yes/no, match requested structure).
- Never invent data: index names, users, counts, and events must come from tool
  results, not from the model's prior knowledge.

## Defang and Safety Rules
- No defanging needed — inputs are plain-text operations questions.
- Do not issue destructive or unbounded SPL; respect each question's time range.
  The Splunk MCP Server also enforces its own guardrails on unsafe/oversized
  searches. These constraints live in the `spl-search` skill.
- Tool arguments must be well-formed per each tool's input schema (discovered from
  the MCP server at runtime).

## Skill Authoring Rules
- One skill captures a single reusable, general procedure — never case-specific
  logic, case IDs, or train-set answers.
- Preserve frontmatter: `name` must match the skill directory; refine
  `description` whenever you refine the body.
- Skill bodies are injected verbatim — do **not** introduce `${...}` placeholders
  in a skill body.

## Variant Strategy
- New variants (prompt or skill) clone the latest and adjust guidance; never edit
  a variant in place.
- Point the eval config's `prompt_paths` / `skill_paths` at the new variant.
- `optimization_target` controls which textual artifacts are in scope
  (`"both"` by default).

## Non-Goals
- Adding tools beyond what the Splunk MCP Server exposes.
- Structural chain changes (the chain is a fixed single-node ReAct agent).
- Optimization that overfits to individual dataset cases or to a specific Splunk
  deployment's data.
