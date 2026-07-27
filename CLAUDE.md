<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Repository Guidelines

## Repository Purpose
FAPO (Fully Autonomous Prompt Optimization) is an LLM chain optimization framework. It provides structured tooling for iteratively improving LLM-powered pipelines through evaluation, failure analysis, and prompt/chain iteration.
The repo separates reusable optimization and evaluation core logic from tenant-specific prompts, datasets, and historical artifacts.

## Project Structure
- `src/hephaestus/` — core optimization engine, evaluation runner, and provider interfaces
- `hephaestus/` — public package shim for `python -m hephaestus.cli`
- `tenants/<tenant_id>/` — tenant-specific prompts, datasets, source artifacts, local eval outputs, and tenant docs
- `docs/` — product-level architecture, usage docs, and process documentation
- `tests/` — automated tests for core modules

## Build, Test, and Development
- `python -m venv .venv && source .venv/bin/activate && pip install --upgrade pip`
- `python -m pip install -e .`
- `python -m pytest`
- `python -m hephaestus.cli --help`

## Troubleshooting
- If a command fails, hangs, or behavior is unexpected, check auto-memory notes for relevant workaround notes before retrying.
- When the user gives you feedback that may be repeatable in the future (e.g. environment setup steps, workaround patterns, tooling preferences), save it to your auto-memory notes so it persists across sessions.

## Evaluation Workflow
- Preferred: use the `eval-runner` slash command for running evaluations and summarizing results.
  - Slash command: `/project:eval-runner`
- Direct command (when needed):
  - `python -m hephaestus.cli eval --config tenants/<tenant_id>/configs/<config>.json`

## Code Style
- Follow the project style guide: `docs/style-guide.md`
- When writing inline code to files in tests (e.g. scorers, chains), use triple-quoted strings (`"""\..."""`) instead of concatenated string literals (`"line1\n" "line2\n"`).

## Tenant Data Safety
- Major rule: tenant-specific information must never appear outside `tenants/<tenant_id>/`. Do not place tenant identifiers, tenant migration history, tenant paths, or tenant-specific examples in shared repo locations such as `docs/`, `tests/`, `src/`, or top-level files.
- Treat `tenants/*/source_artifacts/` as protected.
- Do not modify or delete tenant source artifacts unless explicitly requested.
- Keep secrets out of committed files.

## GitHub Workflow
- Follow the GitHub hygiene guide: `docs/github-hygiene.md`
- Commits must use Conventional Commits format: `type: description`
- Branch naming: `{author}/{feature-with-hyphens}`
- PRs must include Summary, Context, and Test Plan sections
- PR lifecycle agent: `.claude/agents/pr-lifecycle.md` (creates, reviews, simplifies, addresses review comments, and loops until PR is merge-ready)
- Optimization agent: `.claude/agents/optimization.md` (optimizes eval scores across all granularities: prompt text, chain parameters, and chain structure)
- Evaluation asset assistant: `.claude/agents/evaluation-asset-creator.md`
  (creates and monitors self-contained evaluation assets through the shared
  eight-stage core pipeline)
