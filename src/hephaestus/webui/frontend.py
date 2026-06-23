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
  #sidebar h1 { font-size: 15px; margin: 0 16px 4px; letter-spacing: .5px; }
  #sidebar .sub { font-size: 11px; color: var(--muted); margin: 0 16px 16px; }
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
  #home-link:hover { color: var(--accent); }
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
    <h1 id="home-link" title="Back to dashboard">⚒ FAPO Explorer</h1>
    <div class="sub">tenant outputs &amp; iterations</div>
    <div id="tenant-list"></div>
  </div>
  <div id="main"></div>
</div>
<script>
const S = { tenant: null, tab: 'runs', run: null };
// Dashboard tenant filter: null = not yet initialized (treated as "all"),
// otherwise a Set of selected tenant ids. allTenants is the full universe.
const DASH = { allTenants: [], selected: null, open: false };

function scoreClass(v) {
  if (v === null || v === undefined) return '';
  if (v >= 80) return 's-good'; if (v >= 50) return 's-warn'; return 's-bad';
}
function fmtScore(v) {
  return (v === null || v === undefined) ? '–' : Number(v).toFixed(1);
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"]/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
const el = (id) => document.getElementById(id);
const main = () => el('main');

async function loadTenants() {
  const tenants = await api('/api/tenants');
  const box = el('tenant-list');
  if (!tenants.length) { box.innerHTML = '<div class="sub">No tenants found.</div>'; return; }
  box.innerHTML = tenants.map(t => `
    <div class="tenant" data-id="${esc(t.tenant_id)}">
      <div class="name">${esc(t.tenant_id)}</div>
      <div class="meta">${t.run_count} runs · ${t.iteration_count} iters · ${t.prompt_count} prompts · ${t.dataset_count} datasets · ${t.doc_count} docs</div>
    </div>`).join('');
  box.querySelectorAll('.tenant').forEach(node =>
    node.onclick = () => selectTenant(node.dataset.id));
}

function selectTenant(id) {
  S.tenant = id; S.run = null; S.tab = 'runs'; DASH.open = false;
  document.querySelectorAll('.tenant').forEach(n =>
    n.classList.toggle('active', n.dataset.id === id));
  renderTabs();
}

function goHome() {
  S.tenant = null; S.run = null;
  document.querySelectorAll('.tenant').forEach(n => n.classList.remove('active'));
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
  main().innerHTML = '<div class="muted">Loading dashboard…</div>';
  let o;
  try { o = await api('/api/overview' + dashFilterQuery()); }
  catch (e) { main().innerHTML = '<div class="empty">Failed to load: '+esc(e.message)+'</div>'; return; }
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
        <div class="counts">${tc.run_count} runs · ${tc.variant_count} variants · ${tc.prompt_count} prompts · ${tc.dataset_count} datasets</div>
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
    node.onclick = () => { selectTenant(node.dataset.id); S.run = node.dataset.run; renderRunDetail(); });
  main().querySelectorAll('.tcard').forEach(node =>
    node.onclick = () => selectTenant(node.dataset.id));
  main().querySelectorAll('.recent-row').forEach(node =>
    node.onclick = () => { selectTenant(node.dataset.id); S.run = node.dataset.run; renderRunDetail(); });
}

// Re-fetch + re-render the dashboard while keeping the dropdown open so the
// user can adjust multiple tenants without it collapsing each time.
function reloadDashboardKeepingOpen() {
  DASH.open = true;
  renderDashboard();
}

function renderTabs() {
  const tabs = ['runs', 'datasets', 'iterations', 'prompts', 'docs'];
  main().innerHTML = `
    <div class="tabs">${tabs.map(t =>
      `<div class="tab ${t===S.tab?'active':''}" data-tab="${t}">${t}</div>`).join('')}</div>
    <div id="view"></div>`;
  main().querySelectorAll('.tab').forEach(node =>
    node.onclick = () => { S.tab = node.dataset.tab; S.run = null; renderTabs(); });
  if (S.tab === 'runs') S.run ? renderRunDetail() : renderRuns();
  else if (S.tab === 'datasets') renderDatasets();
  else if (S.tab === 'iterations') renderIterations();
  else if (S.tab === 'prompts') renderPrompts();
  else renderDocs();
}

async function renderRuns() {
  const view = el('view');
  view.innerHTML = '<div class="muted">Loading runs…</div>';
  const runs = await api(`/api/tenants/${S.tenant}/runs`);
  if (!runs.length) { view.innerHTML = '<div class="empty">No eval runs for this tenant.</div>'; return; }
  view.innerHTML = `<table><thead><tr>
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
    node.onclick = () => { S.run = node.dataset.run; renderRunDetail(); });
}

async function renderRunDetail() {
  const view = el('view');
  view.innerHTML = '<div class="muted">Loading run…</div>';
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
        <pre style="max-height:180px;overflow:auto">${esc(d.summary_md||'(no summary.md)')}</pre>
      </div>
    </div>
    <div class="card"><h3>Cases (${cases.length})</h3>
      <table><thead><tr><th>#</th><th>Case</th><th>Type</th><th>Composite</th><th></th><th>Tools</th></tr></thead>
      <tbody>${cases.map(c => `
        <tr class="clickable" data-idx="${c.index}">
          <td class="muted">${c.index}</td>
          <td>${esc(c.case_id)}</td>
          <td><span class="pill">${esc(c.task_type||'—')}</span></td>
          <td class="score ${scoreClass(c.composite_score)}">${fmtScore(c.composite_score)}</td>
          <td><div class="barwrap"><div class="bar" style="width:${Math.max(0,Math.min(100,c.composite_score||0))}%"></div></div></td>
          <td class="muted">${c.total_tool_calls ?? 0}${c.failed_tool_calls ? ' ('+c.failed_tool_calls+' failed)' : ''}</td>
        </tr>`).join('')}</tbody></table>
    </div>`;
  el('back').onclick = () => { S.run = null; renderTabs(); };
  view.querySelectorAll('tr.clickable').forEach(node =>
    node.onclick = () => renderCase(parseInt(node.dataset.idx, 10)));
}

async function renderCase(index) {
  const view = el('view');
  view.innerHTML = '<div class="muted">Loading case…</div>';
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
  const ctx = gt.context;
  const meta = gt.metadata;
  const ctxEntries = ctx && typeof ctx === 'object' ? Object.entries(ctx) : [];
  view.innerHTML = `
    <div class="crumb"><a id="back">← run</a> / case ${esc(c.case_id)} (#${index})</div>
    <div class="card"><h3>Input ${gt.dataset ? `<span class="muted" style="font-weight:400;font-size:11px">· ${esc(gt.dataset)}</span>` : ''}</h3>
      ${ctxEntries.length ? ctxEntries.map(([k,v]) => `
        <div class="kv" style="margin-bottom:8px"><b>${esc(k)}</b>
        <pre style="margin-top:4px">${esc(typeof v==='string'?v:JSON.stringify(v,null,2))}</pre></div>`).join('')
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
        <pre>${esc(judgeDiags.join('\n') || '(none)')}</pre>
      </div>
    </div>
    ${otherDiags.length ? `<div class="card"><h3>Diagnostics</h3>
      <pre>${esc(otherDiags.join('\n'))}</pre>
    </div>` : ''}
    <div class="card"><h3>Ground truth ${gt.dataset ? `<span class="muted" style="font-weight:400;font-size:11px">· ${esc(gt.dataset)}</span>` : ''}</h3>
      ${expected ? `<pre>${esc(JSON.stringify(expected, null, 2))}</pre>`
        : `<div class="muted">No matching dataset row found${gt.dataset ? '' : ' (dataset not available locally)'}.</div>`}
    </div>
    <div class="card"><h3>Trajectory: expected vs actual</h3>
      <div class="grid2">
        <div>
          <div class="kv muted" style="margin-bottom:6px">Expected (${expTraj.length})</div>
          ${expTraj.length ? expTraj.map(t => `
            <div class="tool"><b>${esc(t.tool)}</b>
            <div class="muted">${esc(JSON.stringify(t.arguments||{}))}</div></div>`).join('')
            : '<div class="muted">—</div>'}
        </div>
        <div>
          <div class="kv muted" style="margin-bottom:6px">Actual (${tools.length})</div>
          ${tools.length ? tools.map((t,i) => {
            const exp = expTraj[i];
            const match = exp && exp.tool === t.tool;
            return `<div class="tool"><b class="${exp?(match?'s-good':'s-bad'):''}">${esc(t.tool)}</b>${t.error?' <span class="s-bad">ERROR</span>':''}
            <div class="muted">${esc(JSON.stringify(t.arguments||{}))}</div></div>`;
          }).join('') : '<div class="muted">No tool calls.</div>'}
        </div>
      </div>
    </div>
    <div class="card"><h3>Output</h3><pre>${esc(c.output_text || '(empty)')}</pre></div>`;
  el('back').onclick = () => renderRunDetail();
}

async function renderIterations() {
  const view = el('view');
  view.innerHTML = '<div class="muted">Loading iterations…</div>';
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
  view.innerHTML = '<div class="muted">Loading prompts…</div>';
  const prompts = await api(`/api/tenants/${S.tenant}/prompts`);
  if (!prompts.length) { view.innerHTML = '<div class="empty">No prompts found.</div>'; return; }
  view.innerHTML = `
    <table><thead><tr><th>Prompt file</th><th>Size</th></tr></thead><tbody>
    ${prompts.map(p => `<tr class="clickable" data-path="${esc(p.path)}">
      <td><b>${esc(p.name)}</b><div class="muted" style="font-size:11px">${esc(p.path)}</div></td>
      <td class="muted">${p.bytes} B</td></tr>`).join('')}</tbody></table>
    <div id="prompt-view"></div>`;
  view.querySelectorAll('tr.clickable').forEach(node =>
    node.onclick = async () => {
      const d = await api(`/api/tenants/${S.tenant}/prompt?path=${encodeURIComponent(node.dataset.path)}`);
      el('prompt-view').innerHTML =
        `<div class="card"><h3>${esc(node.dataset.path)}</h3><pre>${esc(d.content||'')}</pre></div>`;
      el('prompt-view').scrollIntoView({behavior:'smooth'});
    });
}

const DS = { path: null, offset: 0, limit: 50 };

async function renderDatasets() {
  const view = el('view');
  view.innerHTML = '<div class="muted">Loading datasets…</div>';
  const datasets = await api(`/api/tenants/${S.tenant}/datasets`);
  if (!datasets.length) {
    view.innerHTML = '<div class="empty">No datasets found. (datasets/*.jsonl are gitignored — pull tenant data first.)</div>';
    return;
  }
  view.innerHTML = `
    <table><thead><tr><th>Dataset file</th><th>Rows</th><th>Size</th></tr></thead><tbody>
    ${datasets.map(ds => `<tr class="clickable" data-path="${esc(ds.path)}">
      <td><b>${esc(ds.name)}</b><div class="muted" style="font-size:11px">${esc(ds.path)}</div></td>
      <td>${ds.row_count}</td><td class="muted">${ds.bytes} B</td></tr>`).join('')}</tbody></table>
    <div id="dataset-view"></div>`;
  view.querySelectorAll('tr.clickable').forEach(node =>
    node.onclick = () => { DS.path = node.dataset.path; DS.offset = 0; renderDatasetRows(); });
}

async function renderDatasetRows() {
  const box = el('dataset-view');
  box.innerHTML = '<div class="muted">Loading rows…</div>';
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
      ${rows.map((r,i) => `
        <details><summary><b>${esc(r.case_id ?? (d.offset+i))}</b>
          ${r.task_type||r.scenario_type ? `<span class="pill" style="margin-left:8px">${esc(r.task_type||r.scenario_type)}</span>` : ''}</summary>
          <pre>${esc(JSON.stringify(r, null, 2))}</pre>
        </details>`).join('')}
    </div>`;
  const prev = el('ds-prev'), next = el('ds-next');
  if (prev) prev.onclick = () => { DS.offset = Math.max(0, DS.offset - DS.limit); renderDatasetRows(); };
  if (next) next.onclick = () => { DS.offset = DS.offset + DS.limit; renderDatasetRows(); };
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
  view.innerHTML = '<div class="muted">Loading docs…</div>';
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
  loadDocBody();
}

async function loadDocBody() {
  const body = el('doc-body');
  if (!body) return;
  body.innerHTML = '<div class="muted">Loading…</div>';
  const d = await api(`/api/tenants/${S.tenant}/doc?path=${encodeURIComponent(DOC.path)}`);
  body.innerHTML = renderMarkdown(d.content || '');
}

el('home-link').onclick = goHome;
// Close the tenant dropdown when clicking outside it.
document.addEventListener('click', () => {
  if (DASH.open) { DASH.open = false; const p = el('ms-panel'); if (p) p.classList.add('hidden'); }
});
loadTenants()
  .then(renderDashboard)
  .catch(e => el('tenant-list').innerHTML = '<div class="sub">Error: '+esc(e.message)+'</div>');
</script>
</body>
</html>
"""
