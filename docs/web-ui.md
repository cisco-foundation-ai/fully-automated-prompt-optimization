<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Web UI

FAPO Explorer browses the artifacts a tenant accumulates during optimization:
eval runs, per-case outputs, iteration history, prompt variants and agent
skills, datasets, and tenant docs. Evaluation-asset creation and review are
CLI/API workflows in V3 and have no web frontend.

It is intentionally zero-dependency — the server is built on Python's standard
library `http.server`, and the frontend is a single self-contained HTML
document (inline CSS + vanilla JS, no build step and no external CDN). There is
nothing to install beyond the `hephaestus` package itself.

## Starting the UI

From the repository root, with the project installed (`python -m pip install -e .`):

```bash
python -m hephaestus.cli ui
```

This serves FAPO Explorer at <http://127.0.0.1:8765/> and reads from the
`tenants/` directory by default. Press `Ctrl+C` to stop.

### Options

| Flag | Default | Description |
|---|---|---|
| `--tenants-root` | `tenants` | Path to the tenants directory to browse |
| `--host` | `127.0.0.1` | Loopback bind host (`localhost`, `127.0.0.0/8`, or `::1`) |
| `--port` | `8765` | Bind port |

Example — serve a different tenants root on a custom port:

```bash
python -m hephaestus.cli ui --tenants-root tenants --host 127.0.0.1 --port 9000
```

Once it is running, open the printed URL in a browser.

## What the UI shows

The UI opens on a cross-tenant **dashboard** and lets you drill into a single
tenant and then a single eval run and case.

### Dashboard

The landing view aggregates stats across all tenants (or a filtered subset):
total tenants, eval runs, variants tried, and prompt templates, plus the
average of each tenant's latest run score. It also lists the most recent runs
and a per-tenant card showing that tenant's latest run (status, score, model,
timestamp). Selecting a tenant card opens that tenant.

### Tenant tabs

Inside a tenant, content is organized into tabs:

| Tab | Source | Contents |
|---|---|---|
| **Runs** | Any run directory under `evals/` (also probes `runs/`, `eval_outputs/`, `outputs/`) | Eval runs sorted newest-first, with status, completion, and composite score. A search box filters the run list. Click a run for its config, a Markdown-rendered `summary.md`, and a sortable/filterable per-case table; click a case for its full output, score breakdown, tool calls with an aligned expected-vs-actual trajectory diff, and joined ground truth. |
| **Datasets** | `datasets/**/*.jsonl` | Dataset files with row counts; click a file to expand its rows (offset/limit paging), click again to collapse. The open file is highlighted, and individual rows stay expanded across auto-refresh. JSON is syntax-highlighted. A search box filters the file list. |
| **Iterations** | `docs/iteration-memory.jsonl` | The optimization iteration history recorded for the tenant. |
| **Prompts** | `prompts/**/*.md` and `skills/**/*.md` | Prompt variant files, plus agent **skill** files (for agentic tenants) grouped into their own section. Each entry is tagged by kind (prompt/skill) and group (its parent directory). Click a file to expand its content, click again to collapse; the open file is highlighted. A search box filters the combined list. |
| **Config** | `config/**/*` and `configs/**/*` | Tenant configuration files, with JSON syntax-highlighted. |
| **Docs** | `README.md` + `docs/**/*.md` | The tenant README and tenant-specific markdown docs. |

A run directory is recognized recursively under the probed output roots when it
contains any of `results.jsonl`, `run_config.json`, `summary.md`, `progress.json`, or
`run_manifest.json`. The API labels a valid manifest-authenticated bundle
`authoritative`; a present but invalid manifest `invalid_unverified`; a terminal
legacy progress record without a manifest `legacy_unverified`; and every other
in-progress or loose directory `live_unverified`.

For an `authoritative` run, ground truth is authenticated only when the bundle's
dataset path agrees with its run identity, the validated `run_manifest.json`
has authenticated the bundle, the resolved dataset remains inside the tenant
dataset root, and the dataset bytes match the recorded fingerprint. The UI then
joins the exact recorded dataset by `case_id`. Evaluation-asset dataset ground
truth is not joined from a fallback path. Legacy and live-unverified directories can
expose only a best-effort join from `run_config.json`'s `dataset_path` (or the
tenant's one ordinary dataset when no evaluation-asset catalog exists); that join is not
authority.

## Interactive features

These behaviors apply across the views above:

- **Live refresh.** The UI re-polls and re-renders the current view every five
  seconds, so an in-progress run updates without a manual reload. Refresh is
  paused automatically while the tenant filter dropdown is open, while the
  browser tab is hidden, or while you are typing in an input field.
- **Shareable URLs.** The current location — tenant, tab, open run, and open
  case — is encoded in the URL hash. Reloading, bookmarking, sharing the link,
  or using the browser back/forward buttons restores the same view.
- **Sortable cases.** In a run's per-case table, click any column header to sort
  (click again to reverse); the arrow shows the active column and direction.
  Sorting by composite score ascending surfaces the worst cases first.
- **Case navigation.** Inside a case, use the **prev**/**next** buttons or the
  `j`/`k` (or arrow) keys to move between cases. Navigation follows the current
  sort order of the case table, and a position indicator shows where you are.
- **List filtering.** The Runs, Prompts, Datasets, and per-case tables each have
  a filter box that narrows rows by a case-insensitive substring match, with a
  live result count. Filter text and sort order persist across the live refresh.
- **JSON syntax highlighting.** JSON content — config files, dataset rows, and
  per-case ground truth — is rendered with color-coded keys, strings, numbers,
  booleans, and nulls. Non-JSON content falls back to plain text.
- **Markdown rendering.** A run's `summary.md` and the tenant docs are rendered
  as Markdown (headings, lists, tables, code, emphasis, links).
- **Trajectory diff.** A case's expected and actual tool-call sequences are
  aligned, and each step is color-coded: match, same tool with different
  arguments, missing (expected but not called), or extra (called but not
  expected). A legend explains the colors.
- **Copy buttons.** Hovering over any code/text block (config, ground truth,
  prompt, diagnostics, judge rationale, case input, and output) reveals a
  **Copy** button that copies the raw content to the clipboard.

## How it works

The UI has three small modules under `src/hephaestus/webui/`:

- **`server.py`** — a stdlib `ThreadingHTTPServer` that serves Explorer at `/`
  and JSON APIs. Evaluation-asset endpoints remain available to programmatic
  clients, but no evaluation-asset HTML route is served.
- **`data.py`** — `TenantStore`, the constrained filesystem layer that walks the
  tenants root and surfaces artifacts. All paths are resolved relative to the
  tenants root and validated to stay inside it (and inside the expected
  subtree), so the HTTP layer cannot read arbitrary files on disk.
- **`frontend.py`** — the single-page `INDEX_HTML` document that calls the JSON
  API to render Explorer.

### JSON API

The Explorer uses the read endpoints below. Evaluation-asset endpoints are
retained for CLI/API automation even though V3 has no corresponding frontend.

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

## Notes

- **Narrow writes:** evaluation-asset APIs only create, extend, resume, adopt,
  decide exact current review items, or finalize evaluation assets. All other
  tenant views remain read-only. Inputs must be regular `.jsonl` files beneath
  the selected tenant's `source_artifacts/` or ordinary `datasets/` directory;
  generated evaluation-asset datasets and symlink escapes are rejected before
  the input contract is validated and files are copied.
- **Audited resume edits:** the resume endpoint accepts a JSON object containing
  any editable pipeline decision, including model and batch settings,
  embedding and clustering settings, trusted-coverage thresholds, synthetic
  settings, and the split seed. The failed-stage view shows only the parameters
  relevant to that stage. Revisions are recorded in `config_history.jsonl` and
  `events.jsonl`. Because trusted assignment now precedes authoring, a split-seed
  change rebuilds from Stage 2.
- **Fingerprint-bound review:** list, approve, reject, and finalize operations
  verify the current Stage 7 receipt, complete dependency authority, and
  item/hold fingerprints while holding the same asset lock as pipeline
  execution. Approve and reject require the optimistic review-set token;
  finalization additionally requires the decision-set token over every resolved
  eligible status and decision ID. Decisions and finalizations are append-only,
  and an exact released-finalization replay is idempotent.
- **Review polling:** asset summaries contain only the safe
  `review_authority_revision`, not review bodies. It changes when the resolved
  decisions or current finalization identity changes, telling API clients to
  fetch a fresh bounded review page.
- **Loopback only:** the server rejects non-loopback bind hosts.
  Evaluation-asset APIs also require a loopback `Host`; mutation requests
  require an absent `Origin` or an HTTP origin matching `Host`. Their JSON
  responses use `Cache-Control: no-store`. Explorer's generic dataset list/read
  endpoints and
  case details inherit the loopback-Host and no-store policy whenever they can
  expose a published `datasets/evaluation_assets/` file. Dataset discovery
  lists ordinary files plus only the four files from each evaluation asset's
  strictly resolved `release.json`; it never recursively exposes old
  generations, hidden temporaries, or legacy top-level copies. An explicit
  immutable historical generation path remains readable only after its complete
  generation manifest and file hashes validate. Corrupt pointers or generations
  fail closed without hiding ordinary datasets.
- **Local evaluation-asset state:** copied inputs, checkpoints, state, events, and stage
  artifacts under `evaluation_assets/` are local-only. Published Stage 8
  generations and their sole `release.json` authority under
  `datasets/evaluation_assets/` are ordinary local derived datasets; only
  a separate tenant-configured `customer-data --scope derived` operation can
  sync them.
- **No external dependencies:** standard-library server, no frontend build step.
