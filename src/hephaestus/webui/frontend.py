# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Single-page UI shell.

The entire frontend is one self-contained HTML document (inline CSS + vanilla
JS, no build step and no external CDN) served at ``/``. It calls the read-only
JSON API in :mod:`server` to navigate tenants, eval runs, iterations, prompts,
and per-case outputs.
"""

from __future__ import annotations

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>FAPO Explorer</title>
<style>
  :root {
    --bg: #0f1117; --panel: #171a23; --panel-2: #1e222e; --border: #2a2f3d;
    --text: #e6e9ef; --muted: #8b93a7; --accent: #5b8cff; --good: #3fb950;
    --warn: #d29922; --bad: #f85149; --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: var(--bg); color: var(--text); height: 100vh; overflow: hidden; }
  #app { display: grid; grid-template-columns: 240px 1fr; height: 100vh; }
  #sidebar { background: var(--panel); border-right: 1px solid var(--border);
    overflow-y: auto; padding: 16px 0; }
  .brand { display: flex; align-items: center; gap: 10px; margin: 0 16px 16px;
    color: var(--text); cursor: pointer; }
  .brand-logo { width: 36px; height: 36px; border-radius: 8px; object-fit: cover; flex: none;
    border: 1px solid var(--border); background: var(--panel-2); }
  .brand h1 { font-size: 15px; margin: 0 0 2px; letter-spacing: .5px; line-height: 1.15; }
  .brand .sub { font-size: 11px; color: var(--muted); margin: 0; }
  .brand:hover h1 { color: var(--accent); }
  .tenant { padding: 10px 16px; cursor: pointer; border-left: 3px solid transparent; }
  .tenant:hover { background: var(--panel-2); }
  .tenant.active { background: var(--panel-2); border-left-color: var(--accent); }
  .tenant .name { font-weight: 600; font-size: 14px; }
  .tenant .meta { font-size: 11px; color: var(--muted); margin-top: 3px; }
  #main { overflow-y: auto; padding: 24px 32px; }
  .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border);
    margin-bottom: 20px; }
  .tab { padding: 8px 14px; cursor: pointer; color: var(--muted); font-size: 14px;
    border-bottom: 2px solid transparent; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--text); border-bottom-color: var(--accent); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase;
    letter-spacing: .4px; }
  tr.clickable { cursor: pointer; }
  tr.clickable:hover td { background: var(--panel-2); }
  tr.clickable.active td { background: var(--panel-2); }
  tr.clickable.active td:first-child { box-shadow: inset 3px 0 0 var(--accent); }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px;
    background: var(--panel-2); border: 1px solid var(--border); }
  .score { font-family: var(--mono); font-weight: 600; }
  .s-good { color: var(--good); } .s-warn { color: var(--warn); } .s-bad { color: var(--bad); }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
    padding: 16px; margin-bottom: 16px; }
  .card h3 { margin: 0 0 12px; font-size: 14px; }
  pre { background: var(--panel-2); border: 1px solid var(--border); border-radius: 6px;
    padding: 12px; overflow-x: auto; font-family: var(--mono); font-size: 12px;
    white-space: pre-wrap; word-break: break-word; line-height: 1.5; margin: 0; }
  .tok-key { color: #79c0ff; }
  .tok-str { color: #7ee787; }
  .tok-num { color: #f0883e; }
  .tok-bool { color: #d2a8ff; }
  .tok-null { color: var(--muted); font-style: italic; }
  .tok-punct { color: var(--muted); }
  .muted { color: var(--muted); }
  .empty { color: var(--muted); padding: 40px; text-align: center; }
  a.back { color: var(--accent); cursor: pointer; font-size: 13px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .kv { font-size: 13px; } .kv b { color: var(--muted); font-weight: 500; }
  .barwrap { background: var(--panel-2); border-radius: 4px; height: 16px; width: 120px;
    display: inline-block; vertical-align: middle; overflow: hidden; }
  .bar { height: 100%; background: var(--accent); }
  .tool { font-family: var(--mono); font-size: 12px; padding: 6px 0;
    border-bottom: 1px dashed var(--border); }
  .crumb { font-size: 13px; color: var(--muted); margin-bottom: 14px; }
  .crumb a { color: var(--accent); cursor: pointer; }
  th.sortable { cursor: pointer; user-select: none; }
  th.sortable:hover { color: var(--text); }
  th.sortable .arrow { opacity: .5; font-size: 9px; margin-left: 3px; }
  .filter-box { margin-bottom: 12px; }
  .filter-box input { background: var(--panel-2); color: var(--text);
    border: 1px solid var(--border); border-radius: 5px; padding: 6px 10px;
    font-size: 13px; width: 260px; max-width: 100%; }
  .filter-box input:focus { outline: none; border-color: var(--accent); }
  .filter-count { color: var(--muted); font-size: 12px; margin-left: 10px; }
  .pre-wrap { position: relative; }
  .copy-btn { position: absolute; top: 6px; right: 6px; padding: 3px 9px;
    font-size: 11px; opacity: 0; transition: opacity .12s; z-index: 1; }
  .pre-wrap:hover .copy-btn { opacity: 1; }
  .copy-btn.copied { color: var(--good); border-color: var(--good); }
  .case-nav { display: flex; gap: 8px; align-items: center; margin-left: auto; }
  .case-nav .hint { color: var(--muted); font-size: 11px; }
  .tool.t-match { border-left: 3px solid var(--good); padding-left: 8px; }
  .tool.t-mismatch { border-left: 3px solid var(--warn); padding-left: 8px; }
  .tool.t-missing { border-left: 3px solid var(--bad); padding-left: 8px; opacity: .85; }
  .tool.t-extra { border-left: 3px solid var(--accent); padding-left: 8px; }
  .traj-tag { font-size: 10px; text-transform: uppercase; letter-spacing: .4px;
    margin-left: 6px; font-weight: 600; }
  .traj-tag.match { color: var(--good); } .traj-tag.mismatch { color: var(--warn); }
  .traj-tag.missing { color: var(--bad); } .traj-tag.extra { color: var(--accent); }
  .traj-legend { font-size: 11px; color: var(--muted); margin-bottom: 8px; display: flex; gap: 14px; flex-wrap: wrap; }
  .traj-legend span::before { content: '■'; margin-right: 4px; }
  .traj-legend .l-match::before { color: var(--good); }
  .traj-legend .l-mismatch::before { color: var(--warn); }
  .traj-legend .l-missing::before { color: var(--bad); }
  .traj-legend .l-extra::before { color: var(--accent); }
  .traj-row { margin-bottom: 4px; }
  .traj-empty { color: var(--border); font-family: var(--mono); font-size: 12px; padding: 6px 0; }
  details { border-bottom: 1px solid var(--border); padding: 8px 0; }
  summary { cursor: pointer; font-size: 13px; }
  details pre { margin-top: 8px; }
  button { background: var(--panel-2); color: var(--text); border: 1px solid var(--border);
    border-radius: 5px; padding: 5px 12px; font-size: 13px; cursor: pointer; }
  button:hover:not(:disabled) { border-color: var(--accent); }
  button:disabled { opacity: .4; cursor: default; }
  .docs-layout { display: grid; grid-template-columns: 240px 1fr; gap: 16px; }
  .doc-list .doc-item { padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 13px;
    border: 1px solid transparent; }
  .doc-list .doc-item:hover { background: var(--panel-2); }
  .doc-list .doc-item.active { background: var(--panel-2); border-color: var(--accent); }
  .doc-list .doc-item .path { font-size: 11px; color: var(--muted); }
  .md { font-size: 14px; line-height: 1.6; }
  .md h1, .md h2, .md h3 { line-height: 1.3; margin: 18px 0 10px; }
  .md h1 { font-size: 22px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
  .md h2 { font-size: 18px; } .md h3 { font-size: 15px; }
  .md code { background: var(--panel-2); padding: 1px 5px; border-radius: 4px;
    font-family: var(--mono); font-size: 12px; }
  .md pre { margin: 12px 0; } .md pre code { background: none; padding: 0; }
  .md ul, .md ol { padding-left: 22px; } .md li { margin: 3px 0; }
  .md a { color: var(--accent); } .md table { margin: 12px 0; }
  .md blockquote { border-left: 3px solid var(--border); margin: 12px 0; padding: 2px 14px;
    color: var(--muted); }
  #home-link { cursor: pointer; }
  .ms { position: relative; display: inline-block; }
  .ms-btn { background: var(--panel-2); color: var(--text); border: 1px solid var(--border);
    border-radius: 7px; padding: 7px 12px; font-size: 13px; cursor: pointer; min-width: 200px;
    text-align: left; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .ms-btn:hover { border-color: var(--accent); }
  .ms-btn .caret { color: var(--muted); font-size: 10px; }
  .ms-panel { position: absolute; top: calc(100% + 4px); left: 0; z-index: 20; min-width: 240px;
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 6px;
    box-shadow: 0 8px 24px rgba(0,0,0,.4); max-height: 320px; overflow-y: auto; }
  .ms-panel.hidden { display: none; }
  .ms-actions { display: flex; gap: 6px; padding: 4px 6px 8px; border-bottom: 1px solid var(--border);
    margin-bottom: 4px; }
  .ms-actions a { color: var(--accent); cursor: pointer; font-size: 12px; }
  .ms-opt { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 5px;
    cursor: pointer; font-size: 13px; }
  .ms-opt:hover { background: var(--panel-2); }
  .ms-opt input { accent-color: var(--accent); cursor: pointer; }
  .dash-hero { margin-bottom: 24px; }
  .dash-hero h2 { margin: 0 0 4px; font-size: 22px; }
  .dash-hero .sub2 { color: var(--muted); font-size: 13px; }
  .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }
  .stat { background: linear-gradient(135deg, var(--panel) 0%, var(--panel-2) 100%);
    border: 1px solid var(--border); border-radius: 10px; padding: 18px; }
  .stat .num { font-size: 30px; font-weight: 700; font-family: var(--mono); line-height: 1; }
  .stat .lbl { color: var(--muted); font-size: 12px; margin-top: 8px; text-transform: uppercase;
    letter-spacing: .5px; }
  .stat .accent { color: var(--accent); }
  .section-title { font-size: 13px; text-transform: uppercase; letter-spacing: .5px;
    color: var(--muted); margin: 0 0 12px; }
  .tenant-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px; margin-bottom: 28px; }
  .tcard { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px; cursor: pointer; transition: border-color .12s, transform .12s; }
  .tcard:hover { border-color: var(--accent); transform: translateY(-2px); }
  .tcard .tname { font-size: 15px; font-weight: 600; display: flex; justify-content: space-between;
    align-items: center; }
  .tcard .counts { color: var(--muted); font-size: 12px; margin: 10px 0; }
  .tcard .latest { font-size: 12px; border-top: 1px solid var(--border); padding-top: 10px;
    margin-top: 4px; }
  .tcard .latest .none { color: var(--muted); }
  .ring { --p: 0; width: 46px; height: 46px; border-radius: 50%; flex: none;
    background: conic-gradient(var(--ring-c) calc(var(--p) * 1%), var(--panel-2) 0);
    display: grid; place-items: center; font-size: 12px; font-weight: 700; font-family: var(--mono); }
  .ring span { width: 34px; height: 34px; border-radius: 50%; background: var(--panel);
    display: grid; place-items: center; }
  .recent-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px;
    border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; cursor: pointer;
    background: var(--panel); }
  .recent-row:hover { border-color: var(--accent); }
  .recent-row .rt { font-weight: 600; font-size: 13px; min-width: 130px; }
  .recent-row .rn { color: var(--muted); font-size: 12px; flex: 1; }
  .recent-row .rscore { font-family: var(--mono); font-weight: 700; min-width: 54px; text-align: right; }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .dot.completed { background: var(--good); } .dot.running { background: var(--warn); }
  .dot.failed, .dot.error { background: var(--bad); } .dot.unknown { background: var(--muted); }
  .chart-card { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px 10px; margin-bottom: 24px; }
  .chart { display: flex; align-items: flex-end; gap: 8px; height: 120px;
    padding: 18px 4px 0; position: relative; border-bottom: 1px solid var(--border); }
  .chart .gridline { position: absolute; left: 0; right: 0; border-top: 1px dashed var(--border);
    font-size: 9px; color: var(--muted); }
  .chart .gridline span { position: absolute; left: -2px; top: -7px; background: var(--panel);
    padding-right: 4px; }
  .chart-col { flex: 1; display: flex; flex-direction: column; align-items: center;
    justify-content: flex-end; height: 100%; min-width: 0; cursor: pointer; }
  .chart-col .barv { width: 80%; max-width: 32px; border-radius: 4px 4px 0 0; position: relative;
    transition: filter .12s; min-height: 2px; }
  .chart-col:hover .barv { filter: brightness(1.25); }
  .chart-col .barval { position: absolute; top: -15px; left: 50%; transform: translateX(-50%);
    font-size: 10px; font-family: var(--mono); font-weight: 700; white-space: nowrap; }
  .chart-labels { display: flex; gap: 8px; padding: 5px 4px 0; }
  .chart-labels .cl { flex: 1; text-align: center; font-size: 9px; color: var(--muted);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
</style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div id="home-link" class="brand" title="Back to dashboard" role="button" tabindex="0">
      <img class="brand-logo" src="/assets/fapo-explorer-logo.webp" alt="" aria-hidden="true" />
      <div>
        <h1>FAPO Explorer</h1>
        <div class="sub">tenant outputs &amp; iterations</div>
      </div>
    </div>
    <div id="tenant-list"></div>
  </div>
  <div id="main"></div>
</div>
<script>
const S = { tenant: null, tab: 'runs', run: null, caseIndex: null, caseOrder: [] };
// Dashboard tenant filter: null = not yet initialized (treated as "all"),
// otherwise a Set of selected tenant ids. allTenants is the full universe.
const DASH = { allTenants: [], selected: null, open: false };
const AUTO = { intervalMs: 5000, refreshing: false, inFlight: false, timer: null };

function scoreClass(v) {
  if (v === null || v === undefined) return '';
  if (v >= 80) return 's-good'; if (v >= 50) return 's-warn'; return 's-bad';
}
function fmtScore(v) {
  return (v === null || v === undefined) ? '–' : Number(v).toFixed(1);
}
// Filter text persists by input id so auto-refresh re-renders don't lose it.
const FILTERS = {};
// HTML for a filter input above a table; pre-filled from the persisted value.
function filterBox(id, placeholder) {
  return `<div class="filter-box">
    <input id="${id}" type="text" placeholder="${esc(placeholder)}" autocomplete="off"
      value="${esc(FILTERS[id] || '')}">
    <span class="filter-count" id="${id}-count"></span>
  </div>`;
}
// Live-filter table rows by their text content (case-insensitive substring).
// The query is stored in FILTERS[inputId] and re-applied after every render.
function wireTableFilter(inputId, tableSelector) {
  const input = el(inputId), count = el(inputId + '-count');
  if (!input) return;
  const rows = () => Array.from(document.querySelectorAll(tableSelector + ' tbody tr'));
  const apply = () => {
    const q = input.value.trim().toLowerCase();
    FILTERS[inputId] = input.value;
    const all = rows(); let shown = 0;
    all.forEach(tr => {
      const hit = !q || tr.textContent.toLowerCase().includes(q);
      tr.style.display = hit ? '' : 'none';
      if (hit) shown++;
    });
    if (count) count.textContent = q ? `${shown} of ${all.length}` : '';
  };
  input.oninput = apply;
  apply(); // restore filtering immediately on (re-)render
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
// Syntax-highlight JSON: tokenize the pretty-printed string and wrap each token
// in a class span. Falls back to a plain escaped string if parsing fails.
function hljson(text) {
  let pretty;
  try { pretty = JSON.stringify(JSON.parse(text), null, 2); }
  catch (e) { return esc(text); }
  const re = /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;
  return pretty.replace(re, (m, str, colon, bool) => {
    if (str !== undefined) {
      const cls = colon ? 'tok-key' : 'tok-str';
      return `<span class="${cls}">${esc(str)}</span>${colon ? '<span class="tok-punct">'+esc(colon)+'</span>' : ''}`;
    }
    if (bool !== undefined) return `<span class="tok-bool">${m}</span>`;
    if (m === 'null') return `<span class="tok-null">null</span>`;
    return `<span class="tok-num">${m}</span>`;
  });
}
// Wrap a <pre> with a hover copy button. `inner` is the (already-escaped/
// highlighted) HTML to show; `raw` is the plain text placed on the clipboard.
function copyablePre(inner, raw, attrs) {
  return `<div class="pre-wrap">
    <button class="copy-btn" type="button" data-copy="${esc(raw)}">Copy</button>
    <pre${attrs ? ' ' + attrs : ''}>${inner}</pre>
  </div>`;
}
// Render JSON content into a copyable <pre>, highlighting if it parses.
function jsonPre(text, attrs) {
  return copyablePre(hljson(text), String(text == null ? '' : text), attrs);
}
// Render plain text into a copyable <pre>.
function textPre(text, attrs) {
  const raw = String(text == null ? '' : text);
  return copyablePre(esc(raw), raw, attrs);
}
async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
const el = (id) => document.getElementById(id);
const main = () => el('main');
function showLoading(target, html) {
  if (!AUTO.refreshing) target.innerHTML = html;
}

async function loadTenants() {
  const tenants = await api('/api/tenants');
  const box = el('tenant-list');
  if (!tenants.length) { box.innerHTML = '<div class="sub">No tenants found.</div>'; return; }
  box.innerHTML = tenants.map(t => `
    <div class="tenant" data-id="${esc(t.tenant_id)}">
      <div class="name">${esc(t.tenant_id)}</div>
      <div class="meta">${t.run_count} runs · ${t.iteration_count} iters · ${t.prompt_count} prompts · ${t.config_count} configs · ${t.dataset_count} datasets · ${t.doc_count} docs</div>
    </div>`).join('');
  box.querySelectorAll('.tenant').forEach(node => {
    node.classList.toggle('active', node.dataset.id === S.tenant);
    node.onclick = () => selectTenant(node.dataset.id);
  });
}

function selectTenant(id) {
  S.tenant = id; S.run = null; S.caseIndex = null; S.tab = 'runs'; DASH.open = false;
  document.querySelectorAll('.tenant').forEach(n =>
    n.classList.toggle('active', n.dataset.id === id));
  renderTabs();
}

function goHome() {
  S.tenant = null; S.run = null; S.caseIndex = null;
  document.querySelectorAll('.tenant').forEach(n => n.classList.remove('active'));
  syncHash();
  renderDashboard();
}

const scoreColorVar = (v) =>
  v == null ? 'var(--muted)' : v >= 80 ? 'var(--good)' : v >= 50 ? 'var(--warn)' : 'var(--bad)';

function dashFilterQuery() {
  // Send the filter only when it's a strict subset; "all selected" sends nothing.
  if (!DASH.selected) return '';
  if (DASH.selected.size === DASH.allTenants.length) return '';
  return '?tenants=' + encodeURIComponent([...DASH.selected].join(','));
}

function msLabel() {
  const n = DASH.selected ? DASH.selected.size : DASH.allTenants.length;
  const total = DASH.allTenants.length;
  if (n === total) return `All tenants (${total})`;
  if (n === 0) return 'No tenants';
  if (n === 1) return [...DASH.selected][0];
  return `${n} of ${total} tenants`;
}

async function renderDashboard() {
  showLoading(main(), '<div class="muted">Loading dashboard…</div>');
  let o;
  try { o = await api('/api/overview' + dashFilterQuery()); }
  catch (e) {
    if (!AUTO.refreshing) {
      main().innerHTML = '<div class="empty">Failed to load: '+esc(e.message)+'</div>';
      return;
    }
    throw e;
  }
  // Initialize the filter universe on first load; default = all selected.
  DASH.allTenants = o.all_tenants || [];
  if (DASH.selected === null) DASH.selected = new Set(DASH.allTenants);
  const t = o.totals || {};
  const tenants = o.tenants || [];
  const recent = o.recent_runs || [];
  const stat = (num, lbl, cls='') => `
    <div class="stat"><div class="num ${cls}">${num}</div><div class="lbl">${lbl}</div></div>`;

  // Chart: recent scored runs in chronological order (oldest left → newest right).
  const scored = recent.filter(r => r.avg_composite_score != null).slice().reverse();
  const gridlines = [0, 25, 50, 75, 100].map(g => `
    <div class="gridline" style="bottom:${g}%"><span>${g}</span></div>`).join('');
  const chartHtml = scored.length ? `
    <div class="chart-card">
      <div class="section-title" style="margin-bottom:8px">Recent run scores</div>
      <div class="chart">${gridlines}
        ${scored.map(r => {
          const v = Math.max(0, Math.min(100, r.avg_composite_score));
          return `<div class="chart-col" data-id="${esc(r.tenant_id)}" data-run="${esc(r.run_dir)}"
            title="${esc(r.tenant_id)} / ${esc(r.name)}: ${fmtScore(r.avg_composite_score)}">
            <div class="barv" style="height:${v}%;background:${scoreColorVar(r.avg_composite_score)}">
              <span class="barval">${fmtScore(r.avg_composite_score)}</span>
            </div></div>`;
        }).join('')}
      </div>
      <div class="chart-labels">${scored.map(r =>
        `<div class="cl" title="${esc(r.tenant_id)} / ${esc(r.name)}">${esc(r.name)}</div>`
      ).join('')}</div>
    </div>` : '';

  main().innerHTML = `
    <div class="dash-hero" style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px">
      <div>
        <h2>Overview</h2>
        <div class="sub2">Eval runs, iterations, and prompt assets across selected tenants.</div>
      </div>
      <div class="ms">
        <button class="ms-btn" id="ms-btn"><span id="ms-label">${esc(msLabel())}</span><span class="caret">▼</span></button>
        <div class="ms-panel ${DASH.open?'':'hidden'}" id="ms-panel">
          <div class="ms-actions"><a id="ms-all">Select all</a><a id="ms-none">Clear</a></div>
          ${DASH.allTenants.map(id => `
            <label class="ms-opt">
              <input type="checkbox" value="${esc(id)}" ${DASH.selected.has(id)?'checked':''}>
              ${esc(id)}
            </label>`).join('')}
        </div>
      </div>
    </div>
    <div class="stat-grid">
      ${stat(t.tenants ?? 0, 'Tenants')}
      ${stat(t.runs ?? 0, 'Eval runs', 'accent')}
      ${stat(t.prompt_templates ?? 0, 'Prompt templates')}
      ${stat(t.avg_latest_score == null ? '–' : Number(t.avg_latest_score).toFixed(1),
             'Avg latest score')}
    </div>

    <div class="section-title">Tenants</div>
    <div class="tenant-grid">${tenants.map(tc => {
      const lr = tc.latest_run;
      const sc = lr ? lr.avg_composite_score : null;
      return `<div class="tcard" data-id="${esc(tc.tenant_id)}">
        <div class="tname"><span>${esc(tc.tenant_id)}</span>
          ${lr ? `<div class="ring" style="--p:${Math.max(0,Math.min(100,sc||0))};--ring-c:${scoreColorVar(sc)}">
            <span>${fmtScore(sc)}</span></div>` : ''}
        </div>
        <div class="counts">${tc.run_count} runs · ${tc.variant_count} variants · ${tc.prompt_count} prompts · ${tc.config_count} configs · ${tc.dataset_count} datasets</div>
        <div class="latest">${lr
          ? `<span class="dot ${esc(lr.status||'unknown')}"></span> latest: <b>${esc(lr.name)}</b>
             <span class="muted">· ${esc(lr.model||'—')} · ${esc((lr.updated_at||'').replace('T',' ').slice(0,16))}</span>`
          : `<span class="none">no eval runs yet</span>`}</div>
      </div>`;
    }).join('')}</div>

    ${recent.length ? `<div class="section-title">Recent runs</div>
    <div>${recent.map(r => `
      <div class="recent-row" data-id="${esc(r.tenant_id)}" data-run="${esc(r.run_dir)}">
        <span class="dot ${esc(r.status||'unknown')}"></span>
        <span class="rt">${esc(r.tenant_id)}</span>
        <span class="rn">${esc(r.name)} · ${esc(r.model||'—')} · ${esc((r.updated_at||'').replace('T',' ').slice(0,16))}</span>
        <span class="rscore" style="color:${scoreColorVar(r.avg_composite_score)}">${fmtScore(r.avg_composite_score)}</span>
      </div>`).join('')}</div>` : ''}

    ${chartHtml}`;

  // Multiselect dropdown wiring.
  const btn = el('ms-btn'), panel = el('ms-panel');
  btn.onclick = (e) => { e.stopPropagation(); DASH.open = !DASH.open; panel.classList.toggle('hidden', !DASH.open); };
  panel.onclick = (e) => e.stopPropagation();
  panel.querySelectorAll('.ms-opt input').forEach(input =>
    input.onchange = () => {
      if (input.checked) DASH.selected.add(input.value); else DASH.selected.delete(input.value);
      el('ms-label').textContent = msLabel();
      reloadDashboardKeepingOpen();
    });
  el('ms-all').onclick = () => { DASH.selected = new Set(DASH.allTenants); reloadDashboardKeepingOpen(); };
  el('ms-none').onclick = () => { DASH.selected = new Set(); reloadDashboardKeepingOpen(); };

  main().querySelectorAll('.chart-col').forEach(node =>
    node.onclick = () => { selectTenant(node.dataset.id); S.run = node.dataset.run; S.caseIndex = null; renderRunDetail(); });
  main().querySelectorAll('.tcard').forEach(node =>
    node.onclick = () => selectTenant(node.dataset.id));
  main().querySelectorAll('.recent-row').forEach(node =>
    node.onclick = () => { selectTenant(node.dataset.id); S.run = node.dataset.run; S.caseIndex = null; renderRunDetail(); });
}

// Re-fetch + re-render the dashboard while keeping the dropdown open so the
// user can adjust multiple tenants without it collapsing each time.
function reloadDashboardKeepingOpen() {
  DASH.open = true;
  renderDashboard();
}

function renderTabs() {
  const tabs = [
    ['runs', 'Runs'],
    ['datasets', 'Datasets'],
    ['iterations', 'Iterations'],
    ['prompts', 'Prompts'],
    ['config', 'Config'],
    ['docs', 'Docs'],
  ];
  main().innerHTML = `
    <div class="tabs">${tabs.map(([id, label]) =>
      `<div class="tab ${id===S.tab?'active':''}" data-tab="${id}">${label}</div>`).join('')}</div>
    <div id="view"></div>`;
  main().querySelectorAll('.tab').forEach(node =>
    node.onclick = () => { S.tab = node.dataset.tab; S.run = null; S.caseIndex = null; renderTabs(); });
  syncHash();
  if (S.tab === 'runs') {
    if (S.run && S.caseIndex !== null) renderCase(S.caseIndex);
    else S.run ? renderRunDetail() : renderRuns();
  }
  else if (S.tab === 'datasets') renderDatasets();
  else if (S.tab === 'iterations') renderIterations();
  else if (S.tab === 'prompts') renderPrompts();
  else if (S.tab === 'config') renderConfig();
  else renderDocs();
}

async function renderRuns() {
  const view = el('view');
  showLoading(view, '<div class="muted">Loading runs…</div>');
  const runs = await api(`/api/tenants/${S.tenant}/runs`);
  if (!runs.length) { view.innerHTML = '<div class="empty">No eval runs for this tenant.</div>'; return; }
  view.innerHTML = `${filterBox('runs-filter', 'Filter runs by name, model, status…')}
    <table id="runs-table"><thead><tr>
      <th>Run</th><th>Status</th><th>Model</th><th>Cases</th><th>Avg score</th><th>Updated</th>
    </tr></thead><tbody>${runs.map(r => `
      <tr class="clickable" data-run="${esc(r.run_dir)}">
        <td><b>${esc(r.name)}</b><div class="muted" style="font-size:11px">${esc(r.run_id)}</div></td>
        <td><span class="pill">${esc(r.status || '—')}</span></td>
        <td>${esc(r.model || '—')}</td>
        <td>${r.completed_cases ?? '—'}/${r.total_cases ?? '—'}</td>
        <td class="score ${scoreClass(r.avg_composite_score)}">${fmtScore(r.avg_composite_score)}</td>
        <td class="muted">${esc((r.updated_at||'').replace('T',' ').slice(0,19))}</td>
      </tr>`).join('')}</tbody></table>`;
  view.querySelectorAll('tr.clickable').forEach(node =>
    node.onclick = () => { S.run = node.dataset.run; S.caseIndex = null; renderRunDetail(); });
  wireTableFilter('runs-filter', '#runs-table');
}

async function renderRunDetail() {
  S.caseIndex = null;
  syncHash();
  const view = el('view');
  showLoading(view, '<div class="muted">Loading run…</div>');
  const d = await api(`/api/tenants/${S.tenant}/runs/${encodeURIComponent(S.run)}`);
  const cfg = d.run_config || {}; const ps = cfg.provider_settings || {};
  const cases = d.cases || [];
  view.innerHTML = `
    <div class="crumb"><a id="back">← runs</a> / ${esc(d.run_dir)}</div>
    <div class="grid2">
      <div class="card"><h3>Configuration</h3>
        <div class="kv"><b>provider:</b> ${esc(cfg.provider||'—')} · ${esc(ps.model||'—')}</div>
        <div class="kv"><b>temperature:</b> ${esc(ps.temperature)} · <b>max_tokens:</b> ${esc(ps.max_tokens)}</div>
        <div class="kv"><b>dataset:</b> ${esc(cfg.dataset_path||'—')}</div>
        <div class="kv"><b>chain:</b> ${esc((cfg.chain||{}).path||'—')}</div>
      </div>
      <div class="card"><h3>Summary</h3>
        <div class="md" style="max-height:180px;overflow:auto">${d.summary_md ? renderMarkdown(d.summary_md) : '<span class="muted">(no summary.md)</span>'}</div>
      </div>
    </div>
    <div class="card"><h3>Cases (${cases.length})</h3>
      ${filterBox('cases-filter', 'Filter cases by id or type…')}
      <div id="cases-table-wrap"></div>
    </div>`;
  el('back').onclick = () => { S.run = null; renderTabs(); };
  CASES.rows = cases;
  renderCasesTable();
}

// Cases table state: the raw rows plus the active sort column/direction.
const CASES = { rows: [], sortKey: null, sortDir: 1 };
const CASE_COLS = [
  { key: 'index', label: '#', get: c => c.index, num: true },
  { key: 'case_id', label: 'Case', get: c => c.case_id },
  { key: 'task_type', label: 'Type', get: c => c.task_type || '' },
  { key: 'composite_score', label: 'Composite', get: c => c.composite_score, num: true },
  { key: 'total_tool_calls', label: 'Tools', get: c => c.total_tool_calls ?? 0, num: true },
];

function sortedCases() {
  const rows = CASES.rows.slice();
  if (!CASES.sortKey) return rows;
  const col = CASE_COLS.find(c => c.key === CASES.sortKey);
  if (!col) return rows;
  rows.sort((a, b) => {
    let va = col.get(a), vb = col.get(b);
    if (col.num) { va = va == null ? -Infinity : va; vb = vb == null ? -Infinity : vb; return (va - vb) * CASES.sortDir; }
    return String(va).localeCompare(String(vb)) * CASES.sortDir;
  });
  return rows;
}

function renderCasesTable() {
  const wrap = el('cases-table-wrap');
  if (!wrap) return;
  const rows = sortedCases();
  // Remember the visible order so prev/next case navigation follows the sort.
  S.caseOrder = rows.map(c => c.index);
  const arrow = (k) => CASES.sortKey === k ? `<span class="arrow">${CASES.sortDir > 0 ? '▲' : '▼'}</span>` : '<span class="arrow">↕</span>';
  wrap.innerHTML = `<table id="cases-table"><thead><tr>
      ${CASE_COLS.map(c => `<th class="sortable" data-key="${c.key}">${c.label}${arrow(c.key)}</th>`).join('')}
      <th></th>
    </tr></thead><tbody>${rows.map(c => `
      <tr class="clickable" data-idx="${c.index}">
        <td class="muted">${c.index}</td>
        <td>${esc(c.case_id)}</td>
        <td><span class="pill">${esc(c.task_type||'—')}</span></td>
        <td class="score ${scoreClass(c.composite_score)}">${fmtScore(c.composite_score)}</td>
        <td class="muted">${c.total_tool_calls ?? 0}${c.failed_tool_calls ? ' ('+c.failed_tool_calls+' failed)' : ''}</td>
        <td><div class="barwrap"><div class="bar" style="width:${Math.max(0,Math.min(100,c.composite_score||0))}%"></div></div></td>
      </tr>`).join('')}</tbody></table>`;
  wrap.querySelectorAll('th.sortable').forEach(th =>
    th.onclick = () => {
      const k = th.dataset.key;
      // Toggle direction when re-clicking the same column; default depends on type.
      if (CASES.sortKey === k) CASES.sortDir = -CASES.sortDir;
      else { CASES.sortKey = k; CASES.sortDir = 1; }
      renderCasesTable();
    });
  wrap.querySelectorAll('tr.clickable').forEach(node =>
    node.onclick = () => renderCase(parseInt(node.dataset.idx, 10)));
  wireTableFilter('cases-filter', '#cases-table');
}

// Move to the previous/next case following the current (possibly sorted) order.
function navCase(delta) {
  const order = S.caseOrder || [];
  const pos = order.indexOf(S.caseIndex);
  if (pos === -1) return;
  const next = pos + delta;
  if (next < 0 || next >= order.length) return;
  renderCase(order[next]);
}

// Align expected vs actual tool sequences with an LCS over tool names, so
// matched calls line up and gaps reveal missing (expected-only) / extra
// (actual-only) steps. Returns rows of {exp, act, status}.
function alignTrajectory(expTraj, tools) {
  const n = expTraj.length, m = tools.length;
  const dp = Array.from({length: n + 1}, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = (expTraj[i].tool === tools[j].tool)
        ? dp[i + 1][j + 1] + 1
        : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const rows = []; let i = 0, j = 0;
  const sameArgs = (a, b) =>
    JSON.stringify(a && a.arguments || {}) === JSON.stringify(b && b.arguments || {});
  while (i < n && j < m) {
    if (expTraj[i].tool === tools[j].tool) {
      rows.push({ exp: expTraj[i], act: tools[j],
        status: sameArgs(expTraj[i], tools[j]) ? 'match' : 'mismatch' });
      i++; j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      rows.push({ exp: expTraj[i], act: null, status: 'missing' }); i++;
    } else {
      rows.push({ exp: null, act: tools[j], status: 'extra' }); j++;
    }
  }
  while (i < n) rows.push({ exp: expTraj[i++], act: null, status: 'missing' });
  while (j < m) rows.push({ exp: null, act: tools[j++], status: 'extra' });
  return rows;
}

const TRAJ_TAG = { match: 'match', mismatch: 'args≠', missing: 'missing', extra: 'extra' };

async function renderCase(index) {
  S.caseIndex = index;
  syncHash();
  const view = el('view');
  showLoading(view, '<div class="muted">Loading case…</div>');
  const d = await api(`/api/tenants/${S.tenant}/runs/${encodeURIComponent(S.run)}/cases/${index}`);
  const c = d.case || {};
  const gt = d.ground_truth || {};
  const expected = gt.expected;
  const breakdown = c.score_breakdown || {};
  const allDiags = c.diagnostics || [];
  // The LLM judge emits its rationale as a diagnostic prefixed "judge[":
  // surface those distinctly from any other (chain) diagnostics.
  const judgeDiags = allDiags.filter(x => /^judge\[/.test(x));
  const otherDiags = allDiags.filter(x => !/^judge\[/.test(x));
  const tools = c.tool_call_history || [];
  const expTraj = (expected && expected.expected_trajectory) || [];
  const trajRows = alignTrajectory(expTraj, tools);
  const ctx = gt.context;
  const meta = gt.metadata;
  const ctxEntries = ctx && typeof ctx === 'object' ? Object.entries(ctx) : [];
  const pos = (S.caseOrder || []).indexOf(index);
  const hasPrev = pos > 0, hasNext = pos !== -1 && pos < S.caseOrder.length - 1;
  view.innerHTML = `
    <div class="crumb" style="display:flex;align-items:center">
      <span><a id="back">← run</a> / case ${esc(c.case_id)} (#${index})</span>
      <span class="case-nav">
        ${pos !== -1 ? `<span class="hint">${pos + 1} of ${S.caseOrder.length}</span>` : ''}
        <button id="case-prev" ${hasPrev ? '' : 'disabled'} title="Previous case (k / ←)">← prev</button>
        <button id="case-next" ${hasNext ? '' : 'disabled'} title="Next case (j / →)">next →</button>
      </span>
    </div>
    <div class="card"><h3>Input ${gt.dataset ? `<span class="muted" style="font-weight:400;font-size:11px">· ${esc(gt.dataset)}</span>` : ''}</h3>
      ${ctxEntries.length ? ctxEntries.map(([k,v]) => `
        <div class="kv" style="margin-bottom:8px"><b>${esc(k)}</b>
        ${typeof v==='string' ? textPre(v, 'style="margin-top:4px"') : jsonPre(JSON.stringify(v,null,2), 'style="margin-top:4px"')}</div>`).join('')
        : `<div class="muted">No input found${gt.dataset ? ' for this case_id' : ' (dataset not available locally)'}.</div>`}
      ${meta && Object.keys(meta).length ? `<div class="kv muted" style="margin-top:6px">metadata: ${esc(JSON.stringify(meta))}</div>` : ''}
    </div>
    <div class="grid2">
      <div class="card"><h3>Score breakdown</h3>
        <table>${Object.entries(breakdown).map(([k,v]) => `
          <tr><td>${esc(k)}</td>
          <td class="score ${k.includes('chars')?'':scoreClass(v)}">${typeof v==='number'?v.toFixed(2):esc(v)}</td></tr>`).join('')}</table>
      </div>
      <div class="card"><h3>LLM judge rationale</h3>
        ${textPre(judgeDiags.join('\n') || '(none)')}
      </div>
    </div>
    ${otherDiags.length ? `<div class="card"><h3>Diagnostics</h3>
      ${textPre(otherDiags.join('\n'))}
    </div>` : ''}
    <div class="card"><h3>Ground truth ${gt.dataset ? `<span class="muted" style="font-weight:400;font-size:11px">· ${esc(gt.dataset)}</span>` : ''}</h3>
      ${expected ? jsonPre(JSON.stringify(expected, null, 2))
        : `<div class="muted">No matching dataset row found${gt.dataset ? '' : ' (dataset not available locally)'}.</div>`}
    </div>
    <div class="card"><h3>Trajectory: expected vs actual</h3>
      ${(expTraj.length || tools.length) ? `
      <div class="traj-legend">
        <span class="l-match">match</span>
        <span class="l-mismatch">same tool, different args</span>
        <span class="l-missing">missing (expected, not called)</span>
        <span class="l-extra">extra (called, not expected)</span>
      </div>
      <div class="grid2">
        <div><div class="kv muted" style="margin-bottom:6px">Expected (${expTraj.length})</div>
          ${trajRows.map(r => r.exp
            ? `<div class="tool traj-row t-${r.status}"><b>${esc(r.exp.tool)}</b>
               <span class="traj-tag ${r.status}">${esc(TRAJ_TAG[r.status])}</span>
               <div class="muted">${esc(JSON.stringify(r.exp.arguments||{}))}</div></div>`
            : `<div class="traj-empty">· (no expected step)</div>`).join('')}
        </div>
        <div><div class="kv muted" style="margin-bottom:6px">Actual (${tools.length})</div>
          ${trajRows.map(r => r.act
            ? `<div class="tool traj-row t-${r.status}"><b>${esc(r.act.tool)}</b>${r.act.error?' <span class="s-bad">ERROR</span>':''}
               <span class="traj-tag ${r.status}">${esc(TRAJ_TAG[r.status])}</span>
               <div class="muted">${esc(JSON.stringify(r.act.arguments||{}))}</div></div>`
            : `<div class="traj-empty">· (no actual call)</div>`).join('')}
        </div>
      </div>` : '<div class="muted">No trajectory data.</div>'}
    </div>
    <div class="card"><h3>Output</h3>${textPre(c.output_text || '(empty)')}</div>`;
  el('back').onclick = () => { S.caseIndex = null; renderRunDetail(); };
  const prevBtn = el('case-prev'), nextBtn = el('case-next');
  if (prevBtn) prevBtn.onclick = () => navCase(-1);
  if (nextBtn) nextBtn.onclick = () => navCase(1);
}

async function renderIterations() {
  const view = el('view');
  showLoading(view, '<div class="muted">Loading iterations…</div>');
  const rows = await api(`/api/tenants/${S.tenant}/iterations`);
  if (!rows.length) { view.innerHTML = '<div class="empty">No iteration history.</div>'; return; }
  view.innerHTML = rows.map(renderIterationCard).join('');
}

// Iteration records have no fixed schema — they vary widely by tenant
// (per-variant trial logs, end-of-session summaries, EM/F1 metrics, etc.).
// Rather than hardcode field names, pick a label/date/score/note from known
// aliases for the header, then render every remaining field generically by
// value type so nothing is ever silently dropped.
const ITER_LABEL_KEYS = ['best_variant', 'variant', 'name', 'iteration'];
const ITER_DATE_KEYS = ['date', 'ts', 'timestamp'];
const ITER_SCORE_KEYS = ['final_score', 'composite', 'composite_score', 'score',
                         'train_score', 'val_f1', 'train_f1'];
const ITER_NOTE_KEYS = ['notes', 'note', 'description', 'hypothesis'];
const ITER_HEADER_KEYS = new Set([...ITER_LABEL_KEYS, ...ITER_DATE_KEYS,
  ...ITER_SCORE_KEYS, ...ITER_NOTE_KEYS, 'level', '_index']);
const PROMPT = { path: null };
const CONFIG = { path: null };

function firstKey(obj, keys) {
  for (const k of keys) if (obj[k] != null && obj[k] !== '') return obj[k];
  return undefined;
}

function renderIterationCard(r) {
  const label = firstKey(r, ITER_LABEL_KEYS);
  const date = firstKey(r, ITER_DATE_KEYS);
  const score = firstKey(r, ITER_SCORE_KEYS);
  const note = firstKey(r, ITER_NOTE_KEYS);
  const isNum = typeof score === 'number';

  // Everything not consumed by the header, rendered by value type.
  const scalars = [], blocks = [];
  for (const [k, v] of Object.entries(r)) {
    if (ITER_HEADER_KEYS.has(k) || v == null || v === '') continue;
    if (Array.isArray(v)) {
      blocks.push([k, v.map(x => typeof x === 'object' ? JSON.stringify(x) : String(x)).join('\n')]);
    } else if (typeof v === 'object') {
      blocks.push([k, JSON.stringify(v, null, 2)]);
    } else if (typeof v === 'string' && v.length > 80) {
      blocks.push([k, v]);
    } else {
      scalars.push([k, v]);
    }
  }
  return `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
        <div><span class="pill">${esc(r.level || 'iteration')}</span>
          ${label != null ? `<b style="margin-left:8px">${esc(label)}</b>` : ''}
          ${date != null ? `<span class="muted"> · ${esc(date)}</span>` : ''}</div>
        ${score != null ? `<div class="score ${isNum ? scoreClass(score) : ''}">${isNum ? fmtScore(score) : esc(score)}</div>` : ''}
      </div>
      ${scalars.length ? `<div class="kv" style="margin-top:8px">${scalars.map(([k, v]) =>
        `<b>${esc(k)}:</b> ${esc(typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(2)) : v)}`
      ).join(' · ')}</div>` : ''}
      ${blocks.map(([k, v]) =>
        `<div class="kv" style="margin-top:10px"><b>${esc(k)}</b><pre style="margin-top:4px">${esc(v)}</pre></div>`
      ).join('')}
      ${note != null ? `<pre style="margin-top:10px">${esc(note)}</pre>` : ''}
    </div>`;
}

async function renderPrompts() {
  const view = el('view');
  showLoading(view, '<div class="muted">Loading prompts…</div>');
  const prompts = await api(`/api/tenants/${S.tenant}/prompts`);
  if (!prompts.length) { view.innerHTML = '<div class="empty">No prompts found.</div>'; return; }
  if (!prompts.some(p => p.path === PROMPT.path)) PROMPT.path = null;
  view.innerHTML = `${filterBox('prompts-filter', 'Filter prompt files…')}
    <table id="prompts-table"><thead><tr><th>Prompt file</th><th>Size</th></tr></thead><tbody>
    ${prompts.map(p => `<tr class="clickable ${p.path===PROMPT.path?'active':''}" data-path="${esc(p.path)}">
      <td><b>${esc(p.name)}</b><div class="muted" style="font-size:11px">${esc(p.path)}</div></td>
      <td class="muted">${p.bytes} B</td></tr>`).join('')}</tbody></table>
    <div id="prompt-view"></div>`;
  view.querySelectorAll('tr.clickable').forEach(node =>
    node.onclick = async () => {
      const path = node.dataset.path;
      // Toggle: clicking the already-open prompt file collapses it.
      PROMPT.path = (PROMPT.path === path) ? null : path;
      view.querySelectorAll('tr.clickable').forEach(n =>
        n.classList.toggle('active', n.dataset.path === PROMPT.path));
      if (PROMPT.path) {
        await loadPromptBody();
        el('prompt-view').scrollIntoView({behavior:'smooth'});
      } else {
        el('prompt-view').innerHTML = '';
      }
    });
  wireTableFilter('prompts-filter', '#prompts-table');
  if (PROMPT.path) await loadPromptBody();
}

async function loadPromptBody() {
  const box = el('prompt-view');
  if (!box || !PROMPT.path) return;
  showLoading(box, '<div class="muted">Loading prompt…</div>');
  const d = await api(`/api/tenants/${S.tenant}/prompt?path=${encodeURIComponent(PROMPT.path)}`);
  box.innerHTML =
    `<div class="card"><h3>${esc(PROMPT.path)}</h3>${textPre(d.content||'')}</div>`;
}

async function renderConfig() {
  const view = el('view');
  showLoading(view, '<div class="muted">Loading config files…</div>');
  const configs = await api(`/api/tenants/${S.tenant}/configs`);
  if (!configs.length) {
    CONFIG.path = null;
    view.innerHTML = '<div class="empty">No config files found.</div>';
    return;
  }
  if (!configs.some(c => c.path === CONFIG.path)) CONFIG.path = configs[0].path;
  view.innerHTML = `<div class="docs-layout">
    <div class="doc-list">${configs.map(c => `
      <div class="doc-item ${c.path===CONFIG.path?'active':''}" data-path="${esc(c.path)}">
        <div><b>${esc(c.name)}</b></div>
        <div class="path">${esc(c.path)} · ${c.bytes} B</div>
      </div>`).join('')}</div>
    <div class="card"><div id="config-body"></div></div>
  </div>`;
  view.querySelectorAll('.doc-item').forEach(node =>
    node.onclick = () => { CONFIG.path = node.dataset.path; renderConfig(); });
  await loadConfigBody();
}

async function loadConfigBody() {
  const body = el('config-body');
  if (!body || !CONFIG.path) return;
  showLoading(body, '<div class="muted">Loading…</div>');
  const d = await api(`/api/tenants/${S.tenant}/config?path=${encodeURIComponent(CONFIG.path)}`);
  body.innerHTML = jsonPre(d.content || '');
}

const DS = { path: null, offset: 0, limit: 50, open: new Set() };

async function renderDatasets() {
  const view = el('view');
  showLoading(view, '<div class="muted">Loading datasets…</div>');
  const datasets = await api(`/api/tenants/${S.tenant}/datasets`);
  if (!datasets.length) {
    DS.path = null;
    view.innerHTML = '<div class="empty">No datasets found. (datasets/*.jsonl are gitignored — pull tenant data first.)</div>';
    return;
  }
  if (!datasets.some(ds => ds.path === DS.path)) DS.path = null;
  view.innerHTML = `${filterBox('datasets-filter', 'Filter dataset files…')}
    <table id="datasets-table"><thead><tr><th>Dataset file</th><th>Rows</th><th>Size</th></tr></thead><tbody>
    ${datasets.map(ds => `<tr class="clickable ${ds.path===DS.path?'active':''}" data-path="${esc(ds.path)}">
      <td><b>${esc(ds.name)}</b><div class="muted" style="font-size:11px">${esc(ds.path)}</div></td>
      <td>${ds.row_count}</td><td class="muted">${ds.bytes} B</td></tr>`).join('')}</tbody></table>
    <div id="dataset-view"></div>`;
  view.querySelectorAll('tr.clickable').forEach(node =>
    node.onclick = () => {
      const path = node.dataset.path;
      // Toggle: clicking the already-open dataset file collapses it.
      DS.path = (DS.path === path) ? null : path;
      DS.offset = 0; DS.open.clear();
      view.querySelectorAll('tr.clickable').forEach(n =>
        n.classList.toggle('active', n.dataset.path === DS.path));
      if (DS.path) renderDatasetRows(); else el('dataset-view').innerHTML = '';
    });
  wireTableFilter('datasets-filter', '#datasets-table');
  if (DS.path) await renderDatasetRows();
}

async function renderDatasetRows() {
  const box = el('dataset-view');
  if (!box || !DS.path) return;
  showLoading(box, '<div class="muted">Loading rows…</div>');
  const d = await api(`/api/tenants/${S.tenant}/dataset?path=${encodeURIComponent(DS.path)}&offset=${DS.offset}&limit=${DS.limit}`);
  const rows = d.rows || [];
  const end = Math.min(d.offset + DS.limit, d.total);
  box.innerHTML = `
    <div class="card"><h3>${esc(DS.path)}
      <span class="muted" style="font-weight:400;font-size:11px">· rows ${d.offset+1}–${end} of ${d.total}</span></h3>
      <div style="margin-bottom:10px">
        <button id="ds-prev" ${d.offset<=0?'disabled':''}>← prev</button>
        <button id="ds-next" ${end>=d.total?'disabled':''}>next →</button>
      </div>
      ${rows.map((r,i) => {
        const key = String(r.case_id ?? (d.offset+i));
        return `
        <details data-key="${esc(key)}" ${DS.open.has(key)?'open':''}><summary><b>${esc(key)}</b>
          ${r.task_type||r.scenario_type ? `<span class="pill" style="margin-left:8px">${esc(r.task_type||r.scenario_type)}</span>` : ''}</summary>
          ${jsonPre(JSON.stringify(r, null, 2))}
        </details>`;
      }).join('')}
    </div>`;
  // Persist expand/collapse state so auto-refresh re-renders don't close open rows.
  box.querySelectorAll('details[data-key]').forEach(node => {
    node.ontoggle = () => {
      const key = node.dataset.key;
      if (node.open) DS.open.add(key); else DS.open.delete(key);
    };
  });
  const prev = el('ds-prev'), next = el('ds-next');
  if (prev) prev.onclick = () => { DS.offset = Math.max(0, DS.offset - DS.limit); DS.open.clear(); renderDatasetRows(); };
  if (next) next.onclick = () => { DS.offset = DS.offset + DS.limit; DS.open.clear(); renderDatasetRows(); };
}

// Minimal, safe markdown renderer: HTML-escape first, then apply a small
// subset of GitHub markdown (headings, code, lists, tables, bold/italic,
// links, blockquotes). No external library — keeps the UI dependency-free.
function renderMarkdown(src) {
  src = String(src == null ? '' : src);
  const blocks = []; // stash fenced code so inline rules don't touch it
  src = src.replace(/```(\w*)\n([\s\S]*?)```/g, (m, lang, code) => {
    blocks.push('<pre><code>' + esc(code.replace(/\n$/, '')) + '</code></pre>');
    return '@@CODEBLOCK' + (blocks.length - 1) + '@@';
  });
  const lines = src.split('\n');
  let html = '', listType = null, inTable = false;
  const closeList = () => { if (listType) { html += '</' + listType + '>'; listType = null; } };
  const closeTable = () => { if (inTable) { html += '</tbody></table>'; inTable = false; } };
  const inline = (t) => esc(t)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/\*([^*]+)\*/g, '<i>$1</i>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  for (let raw of lines) {
    const stash = raw.match(/^@@CODEBLOCK(\d+)@@$/);
    if (stash) { closeList(); closeTable(); html += blocks[+stash[1]]; continue; }
    const line = raw.replace(/\s+$/, '');
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)$/))) {
      closeList(); closeTable();
      const lvl = m[1].length; html += `<h${lvl}>${inline(m[2])}</h${lvl}>`; continue;
    }
    if (/^\s*\|(.+)\|\s*$/.test(line)) {
      const cells = line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      if (/^\s*\|?[\s:\-|]+\|?\s*$/.test(line)) continue; // separator row
      if (!inTable) { closeList(); html += '<table><tbody>'; inTable = true; }
      html += '<tr>' + cells.map(c => `<td>${inline(c)}</td>`).join('') + '</tr>';
      continue;
    } else { closeTable(); }
    if ((m = line.match(/^\s*([-*+])\s+(.*)$/))) {
      if (listType !== 'ul') { closeList(); html += '<ul>'; listType = 'ul'; }
      html += `<li>${inline(m[2])}</li>`; continue;
    }
    if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) {
      if (listType !== 'ol') { closeList(); html += '<ol>'; listType = 'ol'; }
      html += `<li>${inline(m[1])}</li>`; continue;
    }
    closeList();
    if ((m = line.match(/^>\s?(.*)$/))) { html += `<blockquote>${inline(m[1])}</blockquote>`; continue; }
    if (line.trim() === '') { html += ''; continue; }
    html += `<p>${inline(line)}</p>`;
  }
  closeList(); closeTable();
  return html;
}

const DOC = { path: null };

async function renderDocs() {
  const view = el('view');
  showLoading(view, '<div class="muted">Loading docs…</div>');
  const docs = await api(`/api/tenants/${S.tenant}/docs`);
  if (!docs.length) { view.innerHTML = '<div class="empty">No docs found for this tenant.</div>'; return; }
  if (!docs.some(d => d.path === DOC.path)) DOC.path = docs[0].path;
  view.innerHTML = `<div class="docs-layout">
    <div class="doc-list">${docs.map(d => `
      <div class="doc-item ${d.path===DOC.path?'active':''}" data-path="${esc(d.path)}">
        <div><b>${esc(d.name)}</b></div><div class="path">${esc(d.path)}</div>
      </div>`).join('')}</div>
    <div class="card"><div id="doc-body" class="md"></div></div>
  </div>`;
  view.querySelectorAll('.doc-item').forEach(node =>
    node.onclick = () => { DOC.path = node.dataset.path; renderDocs(); });
  await loadDocBody();
}

async function loadDocBody() {
  const body = el('doc-body');
  if (!body) return;
  showLoading(body, '<div class="muted">Loading…</div>');
  const d = await api(`/api/tenants/${S.tenant}/doc?path=${encodeURIComponent(DOC.path)}`);
  body.innerHTML = renderMarkdown(d.content || '');
}

async function renderCurrentView() {
  if (!S.tenant) return renderDashboard();
  if (!el('view')) { renderTabs(); return; }
  if (S.tab === 'runs') {
    if (S.run && S.caseIndex !== null) return renderCase(S.caseIndex);
    if (S.run) return renderRunDetail();
    return renderRuns();
  }
  if (S.tab === 'datasets') return renderDatasets();
  if (S.tab === 'iterations') return renderIterations();
  if (S.tab === 'prompts') return renderPrompts();
  if (S.tab === 'config') return renderConfig();
  return renderDocs();
}

function shouldSkipAutoRefresh() {
  if (DASH.open || document.hidden) return true;
  const active = document.activeElement;
  if (!active) return false;
  const editingTags = new Set(['INPUT', 'SELECT', 'TEXTAREA']);
  return editingTags.has(active.tagName);
}

async function autoRefresh() {
  if (AUTO.inFlight || shouldSkipAutoRefresh()) return;
  AUTO.inFlight = true;
  AUTO.refreshing = true;
  const scrollTop = main().scrollTop;
  try {
    await loadTenants();
    await renderCurrentView();
    main().scrollTop = scrollTop;
  } catch (e) {
    console.warn('Auto-refresh failed:', e);
  } finally {
    AUTO.refreshing = false;
    AUTO.inFlight = false;
  }
}

function startAutoRefresh() {
  if (!AUTO.timer) AUTO.timer = window.setInterval(autoRefresh, AUTO.intervalMs);
}

// ---- Deep-linkable URL state ----------------------------------------------
// Encode the current location (tenant / tab / run / case) in the URL hash so
// reload, bookmark, back/forward, and share all restore the same view.
let HASH_WRITING = false;
function syncHash() {
  const p = new URLSearchParams();
  if (S.tenant) p.set('t', S.tenant);
  if (S.tenant && S.tab && S.tab !== 'runs') p.set('tab', S.tab);
  if (S.run) p.set('run', S.run);
  if (S.caseIndex !== null) p.set('case', String(S.caseIndex));
  const next = p.toString();
  if (next === location.hash.slice(1)) return;
  HASH_WRITING = true;
  location.hash = next;
  // hashchange fires async; clear the guard on the next tick.
  window.setTimeout(() => { HASH_WRITING = false; }, 0);
}
async function applyHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const tenant = p.get('t');
  S.tenant = tenant || null;
  S.tab = p.get('tab') || 'runs';
  S.run = p.get('run') || null;
  const cs = p.get('case');
  S.caseIndex = (cs !== null && cs !== '') ? parseInt(cs, 10) : null;
  document.querySelectorAll('.tenant').forEach(n =>
    n.classList.toggle('active', n.dataset.id === S.tenant));
  if (!S.tenant) return renderDashboard();
  renderTabs();
}
window.addEventListener('hashchange', () => { if (!HASH_WRITING) applyHash(); });

const homeLink = el('home-link');
homeLink.onclick = goHome;
homeLink.onkeydown = (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    goHome();
  }
};
// Close the tenant dropdown when clicking outside it.
document.addEventListener('click', () => {
  if (DASH.open) { DASH.open = false; const p = el('ms-panel'); if (p) p.classList.add('hidden'); }
});
// Delegated copy-to-clipboard for any .copy-btn (config, ground truth, prompt,
// diagnostics, dataset rows, output, etc.).
document.addEventListener('click', async (e) => {
  const btn = e.target.closest && e.target.closest('.copy-btn');
  if (!btn) return;
  e.stopPropagation();
  try {
    await navigator.clipboard.writeText(btn.dataset.copy || '');
    const prev = btn.textContent;
    btn.textContent = 'Copied'; btn.classList.add('copied');
    window.setTimeout(() => { btn.textContent = prev; btn.classList.remove('copied'); }, 1200);
  } catch (err) { console.warn('Copy failed:', err); }
});
// Keyboard navigation between cases (j/k or arrow keys) while viewing a case.
document.addEventListener('keydown', (e) => {
  if (S.caseIndex === null || S.run === null) return;
  const tag = document.activeElement && document.activeElement.tagName;
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
  if (e.key === 'j' || e.key === 'ArrowRight') { e.preventDefault(); navCase(1); }
  else if (e.key === 'k' || e.key === 'ArrowLeft') { e.preventDefault(); navCase(-1); }
});
loadTenants()
  .then(() => location.hash.slice(1) ? applyHash() : renderDashboard())
  .then(startAutoRefresh)
  .catch(e => el('tenant-list').innerHTML = '<div class="sub">Error: '+esc(e.message)+'</div>');
</script>
</body>
</html>
"""
