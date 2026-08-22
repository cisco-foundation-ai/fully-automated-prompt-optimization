<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Eval Output Paths

- Output path is controlled by `output_dir` in your local eval config (for example, `tenants/<tenant_id>/configs/local-<run-name>.json`).
- Typical working runs use `tenants/<tenant_id>/evals/tmp/<run-name>/`.
- Typical archived runs use `tenants/<tenant_id>/evals/archive/<run-name>/`.
- A run reserves a new, previously absent output directory. Reusing any existing
  directory is rejected rather than overwritten; choose a distinct
  `run_id`/`output_dir` for another attempt.

## Files Written Per Run

The runtime atomically reserves a previously absent output directory. During
execution, `progress.json` is the mutable live-progress record. When evaluation
reaches terminal publication, it writes and verifies the full artifact set and
installs `run_manifest.json` last; only then is the bundle authoritative. A
fatal setup or runtime failure can leave only an unverified `progress.json` (or
other loose pre-manifest files), even if that progress record says `failed`.

An authoritative terminal bundle contains:

- `progress.json`: terminal status, attempted/successful/failed case IDs, and successful-only aggregates
- `results.jsonl`: one result object for each attempted case, including `execution_status`; it does not persist raw dataset `context` or `expected` fields by default, but outputs, step outputs, diagnostics, tool arguments, and tool results can repeat tenant data, so it is not a privacy boundary
- `run_config.json`: safe, resolved projection of the run configuration and provenance facts; it does not serialize credentials, raw `chain.config`, full MCP command paths, argument values, or environment values, but it does record each command basename, argument count, and environment variable names
- `run_identity.json`: privacy-safe identity fingerprints and comparison controls
- `summary.md`: human-readable successful-only score summary plus infrastructure diagnostics
- `run_manifest.json`: manifest installed last; authenticates the exact artifact inventory and hashes

The terminal bundle status is `completed`, `degraded`, or `failed`, derived from
the ordered result rows' `succeeded`/`failed` execution status. A directory with
only loose files is not an authoritative run until `run_manifest.json` validates
the complete inventory, hashes, run identity, and cross-file status/counts.
