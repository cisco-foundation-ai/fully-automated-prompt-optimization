<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Profile

## Organization Profile
`skill_example` is the **agentic-skills demonstration tenant**. It evaluates a
Splunk-operations ReAct agent — answering operator
questions about indexes, users, instance health, and event data through the
[Splunk MCP Server](https://help.splunk.com/en/splunk-cloud-platform/mcp-server-for-splunk-platform/1.2/about-mcp-server-for-splunk-platform)
— but its reusable procedural knowledge is factored out of the base prompt into
**skill files**. A single-node ReAct agent reasons about the question, selects
and sequences Splunk MCP tools, and synthesizes a grounded answer.

## Skills Architecture
- **Skill files**: `skills/<skill-name>/variant-NNN.md` — markdown with YAML
  frontmatter (`name`, `description`) and a body of reusable instructions.
- **Loading at the agentic layer**: the chain renders the configured skills with
  `src/hephaestus/engine/skills.py::render_skills_block`, and the agentic node
  injects them into the conversation as a distinct `<available_skills>` context
  message (via `build_skills_message` / `inject_skills_message`) right after the
  authored system prompt — mimicking an agent that discovered and loaded skills
  into its environment. The skills stay fully in context for every model call
  (deterministic, static for the run), but are **not** inlined into the prompt
  template a human authors and reads.
- **Config**: `chain.config.skill_paths` lists the loaded skill files;
  `chain.config.optimization_target` (`"prompt" | "skill" | "both"`, default
  `"both"`) selects which textual artifacts the optimization agent iterates.
- **Scope**: skills are only supported for agentic (MCP-enabled) chains. The base
  prompt holds the ReAct loop, tool catalog, and core grounding; each skill holds
  one reusable procedure (tool selection, superlative-index handling, SPL search,
  answer formatting).

## Splunk MCP Server Integration
- **Transport**: The Splunk MCP Server is a streamable-HTTP service behind token
  auth and RBAC. The framework's MCP manager only spawns stdio subprocesses, so
  the config launches a local `npx mcp-remote` bridge that proxies stdio↔HTTP.
- **Tool catalog used by this tenant**:
  - `splunk_get_info` — instance version, hardware, and operational status (no args).
  - `splunk_get_indexes` — list indexes (data repositories); optional `row_limit`.
  - `splunk_get_index_info` — config/usage details for one index (`index_name`).
  - `splunk_get_user_list` — list users with roles, email, and lock status; optional
    `row_limit`. Used for any "other user" / "who are the admins" question.
  - `splunk_get_user_info` — details for the **currently authenticated user only**
    (no args; cannot look up an arbitrary user).
  - `splunk_run_query` — run an SPL search (`query`; optional `earliest_time`,
    `latest_time`, `row_limit`). Primary tool for event-data questions.
  - `splunk_get_metadata` — list `hosts`/`sources`/`sourcetypes` (`type`; optional
    `index`, time window).
  - `splunk_get_knowledge_objects` — retrieve knowledge objects by `type`
    (saved searches, lookups, macros, data models, etc.).
- The agent discovers the live tool schemas from the server at runtime; the names
  above are the contract the dataset's `expected_trajectory` is written against.
- **Unavailable on this deployment**: the `saia_*` Splunk AI Assistant tools are
  discoverable but return HTTP 400. Search cases therefore have the agent write
  SPL directly and run it with `splunk_run_query`. The server also blocks the
  `rest` SPL command and caps oversized/long-running searches.

## Security Environment Assumptions
- Input: natural-language Splunk-operations questions. No sensitive content in the
  dataset itself.
- Output: a final answer summarizing Splunk findings, after an `Answer:` marker.
- Tool access: the **real** Splunk MCP Server, scoped by the supplied token's RBAC.
  The server enforces its own guardrails (rejects unsafe/destructive SPL, caps
  long-running or oversized searches).
- Credentials are read from the environment at runtime (`OPENAI_API_KEY`,
  `SPLUNK_MCP_URL`, `SPLUNK_MCP_TOKEN`) and never committed.

## Threat Model Focus
- This is an operations-assistant tenant, not a security-analysis tenant. The
  optimization target is correct tool selection/sequencing and grounded answers.
- The agent must never hallucinate index names, users, counts, or events — every
  factual claim must trace to a tool result visible in `tool_call_history`.

## Known Safe Patterns
- **Index inventory** questions → `splunk_get_indexes` then `splunk_get_index_info`
  for the index(es) of interest (a single named index skips the listing step).
  Codified in the `tool-selection` and `superlative-index-questions` skills.
- **User lookup** questions → `splunk_get_user_list` (returns roles, email, and lock
  status for every user). `splunk_get_user_info` is reserved for the current
  authenticated account. Codified in the `tool-selection` skill.
- **Event-data / search** questions → the agent writes SPL and runs it with
  `splunk_run_query`, respecting the asked time range (avoid the blocked `rest`
  command; search `_internal`/`_audit`). Codified in the `spl-search` skill.
- **Metadata / knowledge objects** → `splunk_get_metadata` (hosts/sources/
  sourcetypes) and `splunk_get_knowledge_objects` (saved searches, lookups, etc.).
- **Instance health** → `splunk_get_info`.

## Tenant Terminology
- **agent**: the single ReAct node in the chain (`chains/react_agent.py`); the only
  prompt module.
- **skill**: a reusable procedure in `skills/<skill-name>/variant-NNN.md`, loaded at
  the agentic layer into the runtime `<available_skills>` context message.
- **variant-001**: baseline of either the agent prompt or a skill file.
- **mcp-remote bridge**: the `npx mcp-remote` subprocess that connects the stdio
  MCP client to the Splunk MCP Server's HTTP endpoint.
