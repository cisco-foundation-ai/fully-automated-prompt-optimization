<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Eval Output Paths

Where an eval run writes its bundle, what each file holds, and when the bundle
becomes authoritative.

## Output directory

- `output_dir` in your local eval config (for example,
  `tenants/<tenant_id>/configs/local-<run-name>.json`) sets the path.
- Working runs typically use `tenants/<tenant_id>/evals/tmp/<run-name>/`;
  archived runs use `tenants/<tenant_id>/evals/archive/<run-name>/`.
- A run atomically reserves a new, previously absent output directory. Reusing
  an existing directory is rejected, never overwritten; choose a distinct
  `run_id`/`output_dir` for another attempt.

## Lifecycle

During execution, `progress.json` is the mutable live-progress record. At
terminal publication, the runtime writes and verifies the full artifact set and
installs `run_manifest.json` last; only then is the bundle authoritative.

A fatal setup or runtime failure can leave only an unverified `progress.json`
(or other loose pre-manifest files), even if that progress record says
`failed`. A directory with only loose files is not an authoritative run until
`run_manifest.json` validates the complete inventory, hashes, run identity, and
cross-file status/counts.

The terminal bundle status is `completed`, `degraded`, or `failed`, derived from
the ordered result rows' `succeeded`/`failed` execution status.

## Bundle files

| File | Contents |
|---|---|
| `progress.json` | Terminal status, attempted/successful/failed case IDs, and successful-only aggregates |
| `results.jsonl` | One result object for each attempted case, including `execution_status` |
| `run_config.json` | The safe, resolved projection of the run configuration and provenance facts |
| `run_identity.json` | Privacy-safe identity fingerprints and comparison controls |
| `summary.md` | Human-readable successful-only score summary plus infrastructure diagnostics |
| `run_manifest.json` | Installed last; authenticates the exact artifact inventory and hashes |

## What the bundle persists

- `results.jsonl` does not persist raw dataset `context` or `expected` fields by
  default, but outputs, step outputs, diagnostics, tool arguments, and tool
  results can repeat tenant data, so it is not a privacy boundary.
- `run_config.json` does not serialize credentials, raw `chain.config`, full MCP
  command paths, argument values, or environment values, but it does record each
  command basename, argument count, and environment variable names.
