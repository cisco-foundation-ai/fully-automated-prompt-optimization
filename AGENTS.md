<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Repository Guidelines

## Repository Purpose

FAPO (Fully Autonomous Prompt Optimization) is an LLM chain optimization framework. It provides structured tooling for iteratively improving LLM-powered pipelines through evaluation, failure analysis, and prompt/chain iteration.

The repo separates reusable optimization and evaluation core logic from tenant-specific prompts, datasets, and historical artifacts.

## Project Structure

- `src/hephaestus/` - core optimization engine, evaluation runner, and provider interfaces
- `hephaestus/` - public package shim for `python -m hephaestus.cli`
- `tenants/<tenant_id>/` - tenant-specific prompts, datasets, source artifacts, local eval outputs, and tenant docs
- `docs/` - product-level architecture, usage docs, and process documentation
- `tests/` - automated tests for core modules
- `.codex/` - Codex workflow prompts that replace the previous Claude Code slash-command assets

## Build, Test, and Development

- `python -m venv .venv && source .venv/bin/activate && pip install --upgrade pip`
- `python -m pip install -e .`
- `python -m pytest`
- `python -m hephaestus.cli --help`

## Codex Workflows

Codex does not use Claude Code slash commands directly. When a user asks for a FAPO workflow, follow the local prompt files under `.codex/`:

- Optimization loop: `.codex/agents/optimization.md`
- Eval runner: `.codex/commands/eval-runner.md`
- Synthetic samples: `.codex/commands/synthetic-samples.md`
- Synthetic pruner: `.codex/commands/synthetic-pruner.md`
- Reset tenant: `.codex/commands/reset-tenant.md`
- Internal failure attribution phase: `.codex/agents/step-attribution.md`
- Internal variant review phase: `.codex/agents/variant-reviewer.md`

For repeated autonomous optimization rounds, use:

```bash
scripts/optimize-loop-codex.sh --tenant <tenant_id> --config tenants/<tenant_id>/configs/<config>.json
```

## Evaluation Workflow

- Preferred Codex workflow: follow `.codex/commands/eval-runner.md`.
- Direct command when needed:
  - `python -m hephaestus.cli eval --config tenants/<tenant_id>/configs/<config>.json`

## Code Style

- Follow the project style guide: `docs/style-guide.md`.
- When writing inline code to files in tests (for example, scorers or chains), use triple-quoted strings (`"""\..."""`) instead of concatenated string literals (`"line1\n" "line2\n"`).

## Tenant Data Safety

- Major rule: tenant-specific information must never appear outside `tenants/<tenant_id>/`. Do not place tenant identifiers, tenant migration history, tenant paths, or tenant-specific examples in shared repo locations such as `docs/`, `tests/`, `src/`, or top-level files.
- Treat `tenants/*/source_artifacts/` as protected.
- Do not modify or delete tenant source artifacts unless explicitly requested.
- Keep secrets out of committed files.

## GitHub Workflow

- Follow the GitHub hygiene guide: `docs/github-hygiene.md`.
- Commits must use Conventional Commits format: `type: description`.
- Branch naming in the original project is `{author}/{feature-with-hyphens}`. In Codex Desktop threads, use the configured `codex/` prefix unless the user asks otherwise.
- PRs must include Summary, Context, and Test Plan sections.
- Do not commit unless the user asks.