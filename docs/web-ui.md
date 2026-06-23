<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# FAPO Web UI

The FAPO Web UI (the **FAPO Explorer**) is a local, read-only dashboard for
browsing the artifacts a tenant accumulates during optimization: eval runs,
per-case outputs, iteration history, prompt variants, datasets, and tenant docs.

It is intentionally zero-dependency — the server is built on Python's standard
library `http.server`, and the frontend is a single self-contained HTML
document (inline CSS + vanilla JS, no build step and no external CDN). There is
nothing to install beyond the `hephaestus` package itself.

## Starting the UI

From the repository root, with the project installed (`python -m pip install -e .`):

```bash
python -m hephaestus.cli ui
```

This serves the UI at <http://127.0.0.1:8765/> and reads from the `tenants/`
directory by default. Press `Ctrl+C` to stop.

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

### Tenant tabs

Inside a tenant, content is organized into tabs:

| Tab | Source | Contents |
|---|---|---|
| **Runs** | Any run directory under `evals/` (also probes `runs/`, `eval_outputs/`, `outputs/`) | Eval runs sorted newest-first, with status, completion, and composite score. Click a run for its config, progress, `summary.md`, and per-case table; click a case for its full output, score breakdown, tool calls, and joined ground truth. |
| **Datasets** | `datasets/**/*.jsonl` | Dataset files with row counts; rows are viewable with offset/limit paging. |
| **Iterations** | `docs/iteration-memory.jsonl` | The optimization iteration history recorded for the tenant. |
| **Prompts** | `prompts/**/*.md` | Prompt variant markdown files, rendered as content. |
| **Config** | `config/**/*` and `configs/**/*` | Tenant configuration files, rendered as raw text. |
| **Docs** | `README.md` + `docs/**/*.md` | The tenant README and tenant-specific markdown docs. |

A run directory is recognized recursively under the probed output roots when it
contains any of `results.jsonl`, `run_config.json`, `summary.md`, or
`progress.json`. Per-case ground truth is joined from the run's dataset (via
`run_config.json`'s `dataset_path`, falling back to the tenant's only dataset)
by matching on `case_id`.

## How it works

The UI has three small modules under `src/hephaestus/webui/`:

- **`server.py`** — a stdlib `ThreadingHTTPServer` that serves the SPA shell at
  `/` and a read-only JSON API under `/api/`.
- **`data.py`** — `TenantStore`, the read-only filesystem layer that walks the
  tenants root and surfaces artifacts. All paths are resolved relative to the
  tenants root and validated to stay inside it (and inside the expected
  subtree), so the HTTP layer cannot read arbitrary files on disk.
- **`frontend.py`** — the single-page `INDEX_HTML` document that calls the JSON
  API to render the views above.

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
| `GET /api/tenants/<t>/prompts` | Prompt files |
| `GET /api/tenants/<t>/prompt?path=<rel>` | Prompt content |
| `GET /api/tenants/<t>/configs` | Config files |
| `GET /api/tenants/<t>/config?path=<rel>` | Config content |
| `GET /api/tenants/<t>/datasets` | Dataset files |
| `GET /api/tenants/<t>/dataset?path=<rel>&offset=&limit=` | Dataset rows (paged) |
| `GET /api/tenants/<t>/docs` | Doc files |
| `GET /api/tenants/<t>/doc?path=<rel>` | Doc content (markdown) |

## Notes

- **Read-only:** the UI never mutates tenant data — it only reads artifacts.
- **Local by default:** it binds to `127.0.0.1`. Change `--host` only if you
  understand the exposure, since it serves whatever is under the tenants root.
- **No external dependencies:** standard-library server, no frontend build step.
