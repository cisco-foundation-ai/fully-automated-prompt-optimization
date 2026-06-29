<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Change Log

## 2026-06-29
- Summary: Established `skill_example` as the **agentic-skills demonstration
  tenant**. It runs a Splunk-operations ReAct agent over the Splunk MCP Server
  but factors the reusable procedural
  knowledge out of the base prompt into separate **skill files** loaded at the
  agentic layer (injected as a runtime `<available_skills>` context message).
- Why: Provide a worked example of the skills feature — skill files as a textual
  optimization granularity co-equal with prompt text — alongside `mcp_example`
  (which demonstrates MCP tool use).
- Structure:
  - `prompts/modules/agent/variant-001.md` — lean base prompt: ReAct loop, Splunk
    MCP tool catalog, and core grounding rules (no skill content inlined).
  - `skills/tool-selection/variant-001.md` — tool routing/sequencing.
  - `skills/superlative-index-questions/variant-001.md` — mandatory list→drill-in
    and tie-break designation for "largest/most" index questions.
  - `skills/spl-search/variant-001.md` — write SPL and run `splunk_run_query`,
    honoring the time range.
  - `skills/answer-formatting/variant-001.md` — decisive, exhaustive, direct
    yes/no, requested structure.
  - `configs/eval.json` — declares `chain.config.skill_paths` (the four skills) and
    `optimization_target: "both"`.
- Key decisions:
  - **Skill content** distilled from a prior Splunk-agent optimization pass that
    had accreted this procedural knowledge inline in the
    prompt. Here it is generalized and split into focused skills — no case-specific
    hints or train-set examples.
  - **Loaded at the agentic layer**: `render_skills_block` concatenates skill
    bodies and the node injects them as a runtime `<available_skills>` context
    message after the system prompt — implicit (not inlined in the authored
    prompt), static for the run, and fully in context for every model call. This
    keeps eval attribution deterministic (skills always present), unlike
    on-demand progressive disclosure.
  - **Scope**: `optimization_target: both` — prompt and skills are co-equal textual
    levels; structural and MCP-server changes remain out of scope.
- Eval impact: No scored eval run recorded yet (requires live Splunk credentials
  and `npx`). The base prompt + skills are designed to reproduce the behavior a
  fully-inlined Splunk-agent baseline prompt achieved, now via injected skills.
- Rollback notes: N/A — initial tenant setup.
