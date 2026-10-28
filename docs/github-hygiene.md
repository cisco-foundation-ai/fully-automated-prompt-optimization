<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO GitHub hygiene guide

Rules for commits, branches, and pull requests in FAFO, taken from the
project's commit history and branch patterns.

## Commits

- **Conventional Commits format:** `type: description` or
  `type(scope): description`.
  - **Types:** `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `style`, `ci`
  - Examples from this repo:
    - `feat: add structured logging to JCVD script (#901)`
    - `feat: scorer and eval runner chain support (#899)`
    - `fix: tenant scorer package import collisions (#887)`
- **Imperative mood**, start uppercase, no trailing period.
- **Include the PR number** in merge commits: `feat: add chain support (#899)`.
- **Atomic commits:** one logical change per commit.
- **Co-Authored-By footer** when Claude contributes:

  ```text
  Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
  ```

## Branches

- **Naming:** `{author}/{feature-with-hyphens}` (for example, `pk/chain-tenants`).
- **Branch from `main`** and keep branches short-lived.
- **Rebase onto `main`** before merging to keep history linear.

## Pull requests

- **Title:** Conventional Commits format.
- **Body** must include:
  - **Summary:** 1–3 bullet points on what changed.
  - **Context:** why the change is needed.
  - **Test plan:** a checklist of how to verify it.

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

- **One concern per PR.** Keep PRs small and focused.
- **Keep PRs under 1,000 lines of change.** Split a larger change into chained
  PRs that each stand alone and build on the previous one.
- **Self-review before requesting review:** check the diff and run the tests
  locally.

## Review

- Push and request review only after CI passes.
- Address all review comments before merging.
- Resolve conversations after addressing the feedback.
- **Squash-merge to `main`** for a clean history.

## Claude-specific rules

- Always run `python -m pytest` before opening a PR.
- Include the `Co-Authored-By` footer on all commits.
- Never modify tenant `source_artifacts/` without explicit approval.
