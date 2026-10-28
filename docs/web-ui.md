<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Web UI

FAFO Explorer browses the artifacts a tenant accumulates during optimization:
eval runs, per-case outputs, iteration history, prompt variants and agent
skills, datasets, and tenant docs. Evaluation-asset creation and review are
CLI/API workflows and have no web frontend.

Explorer is intentionally zero-dependency: the server is built on Python's
standard-library `http.server`, and the frontend is one self-contained HTML
document (inline CSS and vanilla JS, no build step, no external CDN). There is
nothing to install beyond the `hephaestus` package itself.

## Starting the UI

From the repository root, with the project installed (`python -m pip install -e .`):

```bash
python -m hephaestus.cli ui
```

This serves Explorer at <http://127.0.0.1:8765/>, reading from the `tenants/`
directory by default. Open the printed URL in a browser; press `Ctrl+C` to stop.

| Flag | Default | Description |
|---|---|---|
| `--tenants-root` | `tenants` | Path to the tenants directory to browse |
| `--host` | `127.0.0.1` | Loopback bind host (`localhost`, `127.0.0.0/8`, or `::1`) |
| `--port` | `8765` | Bind port |

For example, to serve a tenants root on a custom port:

```bash
python -m hephaestus.cli ui --tenants-root tenants --host 127.0.0.1 --port 9000
```

## What the UI shows

The UI opens on a cross-tenant **dashboard**. From there you drill into a
tenant, then a run, then a case.

### Dashboard

Aggregate stats across all tenants (or a filtered subset): total tenants, eval
runs, variants tried, and prompt templates, plus the average of each tenant's
latest run score. The dashboard also lists the most recent runs and shows one
card per tenant with its latest run (status, score, model, timestamp). Select a
card to open that tenant.

### Tenant tabs

| Tab | Source | Contents |
|---|---|---|
| **Runs** | Any run directory under `evals/` (also probes `runs/`, `eval_outputs/`, `outputs/`) | Eval runs, newest first, with status, completion, and composite score. A run shows its config, a Markdown-rendered `summary.md`, and a sortable, filterable per-case table. A case shows its full output, score breakdown, tool calls with an aligned expected-vs-actual trajectory diff, and joined ground truth. |
| **Datasets** | `datasets/**/*.jsonl` | Dataset files with row counts. Expand a file to page through its rows (offset/limit); individual rows stay expanded across auto-refresh. |
| **Iterations** | `docs/iteration-memory.jsonl` | The optimization iteration history recorded for the tenant. |
| **Prompts** | `prompts/**/*.md` and `skills/**/*.md` | Prompt variant files, plus agent **skill** files (agentic tenants) grouped into their own section. Each entry is tagged by kind (prompt/skill) and group (its parent directory). |
| **Config** | `config/**/*` and `configs/**/*` | Tenant configuration files. |
| **Docs** | `README.md` + `docs/**/*.md` | The tenant README and tenant-specific Markdown docs. |

### Run authority

A run directory is recognized recursively under the probed output roots when it
contains any of `results.jsonl`, `run_config.json`, `summary.md`, `progress.json`, or
`run_manifest.json`. The API labels each run:

| Label | Meaning |
|---|---|
| `authoritative` | Valid manifest-authenticated bundle |
| `invalid_unverified` | Manifest present but invalid |
| `legacy_unverified` | Terminal legacy progress record without a manifest |
| `live_unverified` | Every other in-progress or loose directory |

### Ground truth

For an `authoritative` run, ground truth is authenticated only when the bundle's
dataset path agrees with its run identity, and:

- the validated `run_manifest.json` has authenticated the bundle,
- the resolved dataset remains inside the tenant dataset root, and
- the dataset bytes match the recorded fingerprint.

The UI then joins the exact recorded dataset by `case_id`. Evaluation-asset
dataset ground truth is not joined from a fallback path.

Legacy and live-unverified directories can expose only a best-effort join from
`run_config.json`'s `dataset_path` (or the tenant's one ordinary dataset when no
evaluation-asset catalog exists). That join is not authority.

## Interactive features

- **Live refresh.** The current view re-polls and re-renders every five seconds,
  so an in-progress run updates without a manual reload. Refresh pauses while
  the tenant filter dropdown is open, the browser tab is hidden, or you are
  typing in an input field.
- **Shareable URLs.** The URL hash encodes the tenant, tab, open run, and open
  case. Reloading, bookmarking, sharing the link, or using back/forward restores
  the same view.
- **Sortable cases.** Click a column header in a run's per-case table to sort;
  click again to reverse. An arrow marks the active column and direction.
  Sorting by composite score ascending surfaces the worst cases first.
- **Case navigation.** Inside a case, use the **prev**/**next** buttons or the
  `j`/`k` (or arrow) keys. Navigation follows the case table's current sort
  order, and a position indicator shows where you are.
- **List filtering.** The Runs, Prompts, Datasets, and per-case tables each have
  a filter box with a case-insensitive substring match and a live result count.
  Filter text and sort order persist across live refresh.
- **Expand and collapse.** In Datasets and Prompts, click a file to expand it and
  click again to collapse. The open file is highlighted.
- **JSON syntax highlighting.** JSON content (config files, dataset rows, and
  per-case ground truth) is rendered with color-coded keys, strings, numbers,
  booleans, and nulls. Non-JSON content falls back to plain text.
- **Markdown rendering.** A run's `summary.md` and the tenant docs render as
  Markdown (headings, lists, tables, code, emphasis, links).
- **Trajectory diff.** A case's expected and actual tool-call sequences are
  aligned, and each step is color-coded: match, same tool with different
  arguments, missing (expected but not called), or extra (called but not
  expected). A legend explains the colors.
- **Copy buttons.** Hovering over any code or text block (config, ground truth,
  prompt, diagnostics, judge rationale, case input, and output) reveals a
  **Copy** button that copies the raw content to the clipboard.

## How it works

Three small modules under `src/hephaestus/webui/`:

- **`server.py`**: a stdlib `ThreadingHTTPServer` that serves Explorer at `/`
  and the JSON APIs. Evaluation-asset endpoints remain available to programmatic
  clients, but no evaluation-asset HTML route is served.
- **`data.py`**: `TenantStore`, the constrained filesystem layer that walks the
  tenants root and surfaces artifacts. All paths are resolved relative to the
  tenants root and validated to stay inside it (and inside the expected
  subtree), so the HTTP layer cannot read arbitrary files on disk.
- **`frontend.py`**: the single-page `INDEX_HTML` document that calls the JSON
  API to render Explorer.

### Explorer API

Explorer uses these read endpoints:

| Endpoint | Returns |
|---|---|
| `GET /api/overview?tenants=<a,b>` | Dashboard aggregates (optionally filtered) |
| `GET /api/tenants` | Tenant summaries |
| `GET /api/tenants/<t>/runs` | Run summaries |
| `GET /api/tenants/<t>/runs/<run>` | Run detail + case list |
| `GET /api/tenants/<t>/runs/<run>/cases/<i>` | Single case detail |
| `GET /api/tenants/<t>/iterations` | Iteration history |
| `GET /api/tenants/<t>/prompts` | Prompt **and** skill files (each tagged with `kind` and `group`) |
| `GET /api/tenants/<t>/prompt?path=<rel>` | Prompt or skill content (serves the `prompts/` and `skills/` subtrees) |
| `GET /api/tenants/<t>/configs` | Config files |
| `GET /api/tenants/<t>/config?path=<rel>` | Config content |
| `GET /api/tenants/<t>/datasets` | Dataset files |
| `GET /api/tenants/<t>/dataset?path=<rel>&offset=&limit=` | Dataset rows (paged) |
| `GET /api/tenants/<t>/docs` | Doc files |
| `GET /api/tenants/<t>/doc?path=<rel>` | Doc content (markdown) |

### Evaluation-asset API

These endpoints are retained for CLI/API automation; there is no corresponding
frontend.

| Endpoint | Returns |
|---|---|
| `GET /api/tenants/<t>/evaluation-assets` | Asset configuration, stage status, directory summaries, and safe `review_authority_revision` for polling |
| `GET /api/evaluation-assets/input-contract` | Versioned canonical field, message, tool-call, and feedback requirements |
| `GET /api/tenants/<t>/evaluation-assets/<a>/stages/<s>` | One stage's status, metrics, artifact list, and bounded example previews |
| `GET /api/tenants/<t>/evaluation-assets/<a>/reviews?status=&offset=&limit=` | Current receipt-verified safe page; exposes both fingerprints, revision, and safe current finalization; filters `pending`, `approved`, `rejected`, or `held`, accepts a limit from 1 through 100, and returns at most that many combined eligible-plus-held rows |
| `POST /api/evaluation-assets/start` | Copy inputs and start a core pipeline run |
| `POST /api/evaluation-assets/extend` | Create and run an immutable child version with reused or refreshed clustering |
| `POST /api/tenants/<t>/evaluation-assets/<a>/resume` | Optionally revise pipeline decisions, invalidate dependent stages, and resume an asset |
| `POST /api/tenants/<t>/evaluation-assets/<a>/adopt` | Synchronously verify an exact legacy completion and return its terminal released `PipelineState`; HTTP `202` is retained compatibility semantics, stable asset/runtime rejections return `409`, and malformed input/filesystem-value errors return `400` |
| `POST /api/tenants/<t>/evaluation-assets/<a>/reviews/<fingerprint>/approve` | Append one immutable approval for the exact current `case_id`, item fingerprint, and review-set fingerprint |
| `POST /api/tenants/<t>/evaluation-assets/<a>/reviews/<fingerprint>/reject` | Append one immutable rejection for the exact current `case_id`, item fingerprint, and review-set fingerprint |
| `POST /api/tenants/<t>/evaluation-assets/<a>/reviews/finalize` | Require `expected_review_set_fingerprint` and `expected_decision_set_fingerprint`, freeze that exact current authority, and start Stage 8; pending/rejected/held derived cases are excluded |

## Access and write boundaries

### Network

- **Loopback only.** The server rejects non-loopback bind hosts.
- Evaluation-asset APIs also require a loopback `Host`. Mutation requests
  require an absent `Origin` or an HTTP origin matching `Host`. Their JSON
  responses use `Cache-Control: no-store`.
- Explorer's generic dataset list/read endpoints and case details inherit the
  loopback-Host and no-store policy whenever they can expose a published
  `datasets/evaluation_assets/` file.

### Dataset exposure

- Dataset discovery lists ordinary files plus only the four files from each
  evaluation asset's strictly resolved `release.json`. It never recursively
  exposes old generations, hidden temporaries, or legacy top-level copies.
- An explicit immutable historical generation path remains readable only after
  its complete generation manifest and file hashes validate.
- Corrupt pointers or generations fail closed without hiding ordinary datasets.

### Evaluation-asset writes

- **Narrow writes.** Evaluation-asset APIs only create, extend, resume, adopt,
  decide exact current review items, or finalize evaluation assets. All other
  tenant views remain read-only.
- **Input files.** Inputs must be regular `.jsonl` files beneath the selected
  tenant's `source_artifacts/` or ordinary `datasets/` directory. Generated
  evaluation-asset datasets and symlink escapes are rejected before the input
  contract is validated and files are copied.
- **Audited resume edits.** The resume endpoint accepts a JSON object containing
  any editable pipeline decision, including model and batch settings, embedding
  and clustering settings, trusted-coverage thresholds, synthetic settings, and
  the split seed. Revisions are recorded in `config_history.jsonl` and
  `events.jsonl`. Because trusted assignment now precedes authoring, a
  split-seed change rebuilds from Stage 2.
- **Fingerprint-bound review.** List, approve, reject, and finalize operations
  verify the current Stage 7 receipt, complete dependency authority, and
  item/hold fingerprints while holding the same asset lock as pipeline
  execution. Approve and reject require the optimistic review-set token;
  finalization also requires the decision-set token over every resolved
  eligible status and decision ID. Decisions and finalizations are append-only,
  and an exact released-finalization replay is idempotent.
- **Review polling.** Asset summaries contain only the safe
  `review_authority_revision`, not review bodies. It changes when the resolved
  decisions or current finalization identity changes, telling API clients to
  fetch a fresh bounded review page.

### Local evaluation-asset state

Copied inputs, checkpoints, state, events, and stage artifacts under
`evaluation_assets/` are local-only. Published Stage 8 generations and their
sole `release.json` authority under `datasets/evaluation_assets/` are ordinary
local derived datasets; only a separate tenant-configured
`customer-data --scope derived` operation can sync them.
