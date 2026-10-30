<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAFO Web UI

FAFO Explorer browses the artifacts a tenant accumulates during optimization:
eval runs, per-case outputs, iteration history, prompt variants and agent
skills, datasets, and tenant docs. It is read-only. Evaluation assets are built
with `python -m hephaestus.cli assets build`; their dataset splits appear with
the tenant's other datasets.

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
| **Datasets** | `datasets/**/*.jsonl` and `evaluation_assets/<asset_id>/datasets/**/*.jsonl` | Dataset files with row counts, including the splits built by `assets build` (for example `evaluation_assets/v1/datasets/train.jsonl`). Expand a file to page through its rows (offset/limit); individual rows stay expanded across auto-refresh. |
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
- the resolved dataset remains inside a tenant dataset root (`datasets/` or an
  asset's `evaluation_assets/<asset_id>/datasets/`), and
- the dataset bytes and case order match the recorded fingerprint and case IDs.

The UI then joins the exact recorded dataset by `case_id`, so runs against
splits built by `assets build` show their ground truth too.

Legacy and live-unverified directories can expose only a best-effort join from
`run_config.json`'s `dataset_path` (or the tenant's only dataset file). That
join is not authority.

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
  and its read-only JSON API.
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

## Access boundaries

- **Loopback only.** The server rejects non-loopback bind hosts.
- **Read-only.** The server serves only `GET` requests and never writes tenant
  data.
- **Constrained paths.** Every read stays inside the requested tenant. Each
  path component must be a real directory (no symlinks or `..`), and the leaf
  must be a regular file.
- **Dataset roots.** Dataset listing and reads cover `*.jsonl` files under
  `datasets/` and each `evaluation_assets/<asset_id>/datasets/`. Other files in
  an asset directory, such as `inputs/`, `cache/`, `lessons.jsonl`, rubrics, and
  `catalog.json`, are never listed or served as datasets.
