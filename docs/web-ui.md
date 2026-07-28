<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Web UI

The FAPO Web UI has two focused surfaces on one local server:

- **FAPO Explorer** browses the artifacts a tenant accumulates during
  optimization: eval runs, per-case outputs, iteration history, prompt variants
  and agent skills, datasets, and tenant docs.
- **Evaluation Asset Studio** creates and monitors the self-contained data
  preparation assets that can bootstrap a tenant.

It is intentionally zero-dependency — the server is built on Python's standard
library `http.server`, and the frontend is a single self-contained HTML
document (inline CSS + vanilla JS, no build step and no external CDN). There is
nothing to install beyond the `hephaestus` package itself.

## Starting the UI

From the repository root, with the project installed (`python -m pip install -e .`):

```bash
python -m hephaestus.cli ui
```

This serves FAPO Explorer at <http://127.0.0.1:8765/> and Evaluation Asset
Studio at <http://127.0.0.1:8765/evaluation-assets/>. Both surfaces use the
same server and read from the `tenants/` directory by default. Press `Ctrl+C`
to stop.

### Options

| Flag | Default | Description |
|---|---|---|
| `--tenants-root` | `tenants` | Path to the tenants directory to browse |
| `--host` | `127.0.0.1` | Bind host |
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

The dashboard also shows the latest evaluation-asset stage for every tenant.
Its **Open Evaluation Asset Studio** action moves data-preparation work to the
separate Studio; the Explorer overview has no asset input form.

### Evaluation Asset Studio

The Studio has its own tenant index and creation screen. It accepts labeled and
unlabeled JSONL paths, the rubric extraction model, embedding model, exact
number of intent clusters, and the Stage 5 intent match threshold. The
threshold defaults to `0.6` and is persisted with the asset. Stage 7 synthetic
coverage is separately enabled or disabled and accepts an exact data-point
count per supported cluster; it is disabled by default. Both JSONL files must
already conform to the
vendor-neutral `fapo-evaluation-input-v1` contract; the creation screen links
to its machine-readable definition. The model menus include multiple GPT extraction
models, current and legacy OpenAI embedding models, and a dependency-free local
TF-IDF fallback. Selecting TF-IDF records `embedding_provider: tfidf` in the
asset config and makes no embedding API calls. Starting a pipeline copies both
source files into an independent
`evaluation_assets/<asset_id>/stages/01_raw_inputs/` workspace before
background processing begins.

Selecting a tenant visualizes all eight preparation stages, live status,
selected models, requested clusters, match threshold, synthetic settings,
pipeline counts, and the eight numbered stage directories. Each stage is clickable
and opens a focused view with its
inputs, processing steps, outputs, stage metrics, and bounded previews of the
real files created there. Artifact inspection intentionally returns one
syntax-highlighted example per file rather than rendering entire datasets. The
Intent Mining stage also includes the projection-style interactive cluster
browser from the original workflow mock, backed by the asset's real routes,
cluster sizes, representative requests, and observed tools. Failed or
interrupted pipelines can be resumed from this surface with current decisions
or an edited model, embedding, cluster count, match threshold, or synthetic
coverage configuration. The Studio shows which stage each setting affects;
the core preserves earlier checkpoints and rebuilds the affected stage and all
downstream artifacts.

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
contains any of `results.jsonl`, `run_config.json`, `summary.md`, or
`progress.json`. Per-case ground truth is joined from the run's dataset (via
`run_config.json`'s `dataset_path`, falling back to the tenant's only dataset)
by matching on `case_id`.

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

The UI has four small modules under `src/hephaestus/webui/`:

- **`server.py`** — a stdlib `ThreadingHTTPServer` that serves Explorer at `/`,
  Evaluation Asset Studio at `/evaluation-assets/`, read APIs, and narrow
  evaluation-asset start/resume endpoints.
- **`data.py`** — `TenantStore`, the constrained filesystem layer that walks the
  tenants root and surfaces artifacts. All paths are resolved relative to the
  tenants root and validated to stay inside it (and inside the expected
  subtree), so the HTTP layer cannot read arbitrary files on disk.
- **`frontend.py`** — the single-page `INDEX_HTML` document that calls the JSON
  API to render Explorer.
- **`evaluation_assets_frontend.py`** — the separate
  `EVALUATION_ASSET_HTML` document that renders creation and pipeline progress.

### JSON API

The frontend is backed by these read-only endpoints (useful for scripting too):

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
| `GET /api/tenants/<t>/evaluation-assets` | Asset configuration, stage status, and directory summaries |
| `GET /api/evaluation-assets/input-contract` | Versioned canonical field, message, tool-call, and feedback requirements |
| `GET /api/tenants/<t>/evaluation-assets/<a>/stages/<s>` | One stage's status, metrics, artifact list, and bounded example previews |
| `POST /api/evaluation-assets/start` | Copy inputs and start a core pipeline run |
| `POST /api/tenants/<t>/evaluation-assets/<a>/resume` | Optionally revise pipeline decisions, invalidate dependent stages, and resume an asset |

## Notes

- **Narrow writes:** the UI only creates/resumes evaluation assets. All other
  tenant views remain read-only. Input paths must resolve inside the FAPO
  workspace and are copied into `stages/01_raw_inputs/` before processing.
- **Audited resume edits:** the resume endpoint accepts a JSON object containing
  any editable pipeline decision, including model and batch settings,
  embedding and clustering settings, trusted-coverage thresholds, synthetic
  settings, and the split seed. The failed-stage view shows only the parameters
  relevant to that stage. Revisions are recorded in `config_history.jsonl` and
  `events.jsonl`.
- **Local by default:** it binds to `127.0.0.1`. Change `--host` only if you
  understand the exposure, since it serves whatever is under the tenants root.
- **No external dependencies:** standard-library server, no frontend build step.
