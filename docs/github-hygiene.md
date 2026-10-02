<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO GitHub Hygiene Guide

Standards for commits, branches, and pull requests in the FAFO project. These conventions are derived from actual commit history and branch patterns.

## Commit Discipline

- **Conventional Commits** format: `type: description` or `type(scope): description`
  - **Types:** `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `style`, `ci`
  - Examples from this repo:
    - `feat: add structured logging to JCVD script (#901)`
    - `feat: scorer and eval runner chain support (#899)`
    - `fix: tenant scorer package import collisions (#887)`
- **Imperative mood**, start uppercase, no trailing period
- **Include PR number** in merge commits: `feat: add chain support (#899)`
- **Atomic commits** — one logical change per commit
- **Co-Authored-By footer** when Claude contributes:
  ```
  Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
  ```

## Branch Workflow

- **Branch naming:** `{author}/{feature-with-hyphens}` (e.g., `pk/chain-tenants`)
- **Branch from `main`**, keep branches short-lived
- **Rebase onto `main`** before merging to keep linear history

## PR Structure

- **PR title** uses conventional commit format
- **PR body** must include:
  - **Summary** — 1–3 bullet points of what changed
  - **Context** — why this change is needed
  - **Test plan** — checklist of how to verify

```markdown
## Summary
- Added chain loader for dynamic LangGraph pipeline construction
- Wired chain execution into eval runner

## Context
The eval runner needed support for multi-step LLM chains to enable
multi-hop reasoning evaluations.

## Test plan
- [ ] `python -m pytest` passes
- [ ] New chain loader tests cover happy path and error cases
```

- **One concern per PR** — keep PRs small and focused
- **Keep PRs under 1,000 lines of change** — if a change exceeds this, break it into chained PRs that each stand alone and build on the previous one
- **Self-review before requesting review** — check the diff, run tests locally

## Review Workflow

- Push and request review only after CI passes
- Address all review comments before merging
- Resolve conversations after addressing feedback
- **Squash-merge to `main`** for clean history

## Claude-Specific Rules

- Always run `python -m pytest` before opening a PR
- Include the `Co-Authored-By` footer on all commits
- Never modify tenant `source_artifacts/` without explicit approval
