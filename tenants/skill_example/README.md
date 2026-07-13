<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Skill Example Tenant

This tenant demonstrates **agentic skills**: reusable procedural knowledge stored
in separate **skill files** and injected into an agent prompt, optimized as a
textual granularity co-equal with the prompt itself. It runs a ReAct agent that
performs Splunk operations through the
[Splunk MCP Server](https://help.splunk.com/en/splunk-cloud-platform/mcp-server-for-splunk-platform/1.2/about-mcp-server-for-splunk-platform).

## What makes this the "skills" example

- **Lean base prompt** (`prompts/modules/agent/variant-001.md`): the ReAct loop,
  the Splunk MCP tool catalog, and core grounding rules — and nothing about
  skills. A reader of the authored prompt never sees the skill content.
- **Skill files** (`skills/<skill-name>/variant-NNN.md`): the reusable procedures
  the agent applies, each a markdown file with YAML frontmatter (`name`,
  `description`). They are **loaded at the agentic layer** — the node injects
  them into the conversation as a distinct `<available_skills>` context message,
  mimicking an agent that discovered and loaded skills into its environment.
  They stay fully in context for every model call (deterministic), but are not
  baked into the prompt template.
- **Config switch** (`chain.config`): `skill_paths` lists the skill files to
  load; `optimization_target: "both"` tells the optimization agent to iterate
  the prompt **and** the skills as one textual level. Skills are only supported
  for agentic (MCP-enabled) chains.

### Skills shipped

| Skill | When it applies |
|-------|-----------------|
| `tool-selection` | Picking/sequencing the right Splunk tool for index, user, metadata, knowledge-object, and health questions |
| `superlative-index-questions` | "Which index has the most data / highest event count / is largest" — mandatory list→drill-in + tie-break designation |
| `spl-search` | Event-data questions answered by writing SPL and running `splunk_run_query` |
| `answer-formatting` | Being decisive, exhaustive on lists, direct on yes/no, and matching the requested structure |

## Prerequisites

The Splunk MCP Server speaks streamable HTTP; the framework's MCP layer launches
stdio subprocesses. The config bridges the two with `npx mcp-remote`, so you need:

- **Node.js / `npx`** on the eval host (provides `mcp-remote`).
- **`OPENAI_API_KEY`** — for the agent (`gpt-4o`) and judge (`gpt-5.5`).
- **`SPLUNK_MCP_URL`** — your Splunk MCP Server endpoint URL.
- **`SPLUNK_MCP_TOKEN`** — a Splunk auth token (sent as `Authorization: Bearer ...`).

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
export SPLUNK_MCP_URL="https://<your-splunk-host>/.../mcp"
export SPLUNK_MCP_TOKEN="<your-splunk-token>"
```

Secrets are read from the environment only — never commit them.

## Quick Start

```bash
# Run evaluation against the real Splunk MCP Server (skills injected from config)
python -m hephaestus.cli eval --config tenants/skill_example/configs/eval.json

# Check results
cat tenants/skill_example/evals/run-001/summary.md
cat tenants/skill_example/evals/run-001/results.jsonl | jq '.tool_call_history'
```

## What's Tested

The evaluation tests the agent's ability to:
1. Pick the correct Splunk MCP tools for an operations question (guided by the
   injected skills).
2. Sequence them sensibly (e.g. list indexes → drill into one; search directly).
3. Pass well-formed arguments (`index_name`, SPL `query`, time ranges, `type`).
4. Ground its final answer in tool results rather than hallucinating.

## Optimizing skills

With `optimization_target: "both"`, the optimization agent treats prompt and
skill files as one textual surface. To iterate a skill, clone it to a new variant
(`skills/<name>/variant-002.md`), point the config's `skill_paths` at it, and
re-run the eval — exactly the prompt-variant loop, applied to skills.

## Files

- `chains/react_agent.py` — ReAct agent with Splunk MCP tools + agentic-layer skill loading
- `prompts/modules/agent/variant-001.md` — lean base prompt (no skill content inlined)
- `skills/<skill-name>/variant-001.md` — reusable procedural-knowledge skill files
- `datasets/splunk_ops_tasks.jsonl` — Splunk-operations tasks (local-only, not committed; see `docs/data-contract.md`)
- `code/scorers/composite_scorer.py` — weighted trajectory (0.6) + LLM-judge (0.4)
- `code/scorers/trajectory_scorer.py` — deterministic order/argument-aware tool-trajectory scorer
- `code/scorers/llm_judge_scorer.py` — LLM-as-judge answer-correctness scorer
- `configs/eval.json` — eval config with Splunk MCP settings + `skill_paths` / `optimization_target`
- `docs/` — tenant docs (profile, data/prompt contracts, eval operations, iteration playbook, change log, docs index)
