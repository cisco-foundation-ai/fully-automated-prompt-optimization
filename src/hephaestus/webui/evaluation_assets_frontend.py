# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Standalone frontend for creating and monitoring evaluation assets."""

EVALUATION_ASSET_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FAPO Evaluation Asset Studio</title>
<style>
  :root {
    --ink: #17231f; --muted: #61706a; --line: #dbe4df; --paper: #f7faf8;
    --card: #fff; --green: #087f5b; --green-soft: #e6f5ef; --blue: #3762d7;
    --blue-soft: #eef2ff; --amber: #b26b00; --amber-soft: #fff6dd;
    --red: #c73939; --red-soft: #fff0ef; --shadow: 0 12px 35px rgba(24,55,43,.08);
    --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  body { margin: 0; color: var(--ink); background: var(--paper);
    font: 15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  button, input, select { font: inherit; }
  button { cursor: pointer; }
  a { color: inherit; }
  .shell { min-height: 100vh; display: grid; grid-template-columns: 270px minmax(0,1fr); }
  aside { padding: 24px 18px; color: #eaf6f0; background: #14251f; }
  .brand { display: flex; align-items: center; gap: 12px; margin: 0 6px 30px; text-decoration: none; }
  .brand img { width: 38px; height: 38px; object-fit: contain; }
  .brand strong { display: block; font-size: 16px; }
  .brand small { color: #9eb8ae; font-size: 12px; }
  .side-label { margin: 20px 8px 8px; color: #88a197; font-size: 11px; font-weight: 700;
    letter-spacing: .09em; text-transform: uppercase; }
  .side-button { width: 100%; padding: 10px 12px; border: 1px solid transparent; border-radius: 9px;
    text-align: left; color: #cfe0d9; background: transparent; }
  .side-button:hover, .side-button.active { color: white; background: #223b32; border-color: #315246; }
  .side-button .tiny { float: right; color: #8fa99e; font-size: 11px; }
  .back { display: block; margin: 28px 8px 0; color: #b8cec5; font-size: 13px; text-decoration: none; }
  main { min-width: 0; padding: 30px clamp(24px, 4vw, 58px) 60px; }
  .topbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 28px; }
  h1 { margin: 0; font-size: clamp(25px,3vw,36px); letter-spacing: -.035em; }
  h2 { margin: 0; font-size: 20px; }
  h3 { margin: 0; font-size: 15px; }
  .lede { max-width: 720px; margin: 7px 0 0; color: var(--muted); }
  .pill { display: inline-flex; align-items: center; gap: 7px; padding: 7px 10px; border-radius: 999px;
    color: var(--green); background: var(--green-soft); font-size: 12px; font-weight: 700; white-space: nowrap; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; box-shadow: var(--shadow); }
  .new-card { padding: clamp(20px,3vw,32px); }
  .section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 22px; }
  .section-head p { margin: 4px 0 0; color: var(--muted); }
  form { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 18px; }
  label { display: grid; gap: 7px; font-size: 13px; font-weight: 700; }
  label span { color: var(--muted); font-size: 12px; font-weight: 500; }
  input, select { width: 100%; padding: 11px 12px; color: var(--ink); background: white;
    border: 1px solid #cbd8d1; border-radius: 8px; }
  input:focus, select:focus { outline: 3px solid #cbe9df; border-color: var(--green); }
  label.disabled-control { opacity: .55; }
  .wide { grid-column: 1/-1; }
  .model-note { padding: 13px; border-radius: 9px; background: var(--blue-soft); color: #3d4e78; font-size: 13px; }
  .input-contract { grid-column: 1/-1; display: flex; align-items: flex-start; justify-content: space-between;
    gap: 18px; padding: 15px; border: 1px solid #cfd9f8; border-radius: 10px; background: var(--blue-soft); }
  .input-contract strong { display: block; color: #2f477e; }
  .input-contract p { margin: 4px 0 0; color: #52658d; font-size: 12px; }
  .input-contract button { flex: 0 0 auto; padding: 7px 10px; border: 1px solid #9db0e9;
    border-radius: 7px; color: #3155b0; background: white; font-size: 12px; font-weight: 700; text-decoration: none; }
  .contract-back { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px;
    color: var(--ink); background: white; font-weight: 700; }
  .contract-hero { padding: 25px 27px; margin-bottom: 18px; border-color: #cfd9f8;
    background: linear-gradient(135deg, #f7f9ff, #edf2ff); }
  .contract-hero .schema-badge { display: inline-block; margin-bottom: 11px; padding: 5px 8px;
    border-radius: 6px; color: #3155b0; background: white; font: 11px var(--mono); }
  .contract-hero p { max-width: 780px; margin: 8px 0 0; color: #52658d; }
  .contract-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 18px; }
  .contract-section { padding: 22px; }
  .contract-section.wide { grid-column: 1/-1; }
  .contract-section > p { margin: 6px 0 16px; color: var(--muted); font-size: 13px; }
  .contract-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .contract-table th { padding: 8px 9px; color: var(--muted); border-bottom: 1px solid var(--line);
    text-align: left; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
  .contract-table td { padding: 10px 9px; border-bottom: 1px solid #edf1ef; vertical-align: top; }
  .contract-table tr:last-child td { border-bottom: 0; }
  .contract-table code { color: #3155b0; font: 12px var(--mono); }
  .contract-table .field-type { color: var(--muted); white-space: nowrap; }
  .contract-list { display: grid; gap: 9px; margin: 0; padding: 0; list-style: none; }
  .contract-list li { position: relative; padding: 10px 12px 10px 34px; border-radius: 8px;
    color: #42514b; background: #f5f8f6; font-size: 13px; }
  .contract-list li::before { content: "✓"; position: absolute; left: 12px; color: var(--green); font-weight: 900; }
  .contract-chips { display: flex; flex-wrap: wrap; gap: 7px; margin: 12px 0 16px; }
  .contract-chips span { padding: 5px 8px; border-radius: 999px; color: var(--green);
    background: var(--green-soft); font: 11px var(--mono); }
  .contract-callout { padding: 13px 14px; border-left: 3px solid var(--blue); border-radius: 6px;
    color: #42577c; background: var(--blue-soft); font-size: 13px; }
  .contract-code { margin: 14px 0 0; padding: 18px; overflow: auto; border-radius: 10px;
    color: #dbe7e1; background: #14251f; font: 12px/1.55 var(--mono); white-space: pre; }
  .form-actions { grid-column: 1/-1; display: flex; align-items: center; gap: 14px; padding-top: 4px; }
  .primary { border: 0; border-radius: 9px; padding: 11px 18px; color: white; background: var(--green);
    font-weight: 750; }
  .primary:hover { background: #066b4d; }
  .primary:disabled { opacity: .5; cursor: wait; }
  .message { color: var(--muted); font-size: 13px; }
  .message.error { color: var(--red); }
  .empty { padding: 52px 24px; text-align: center; color: var(--muted); }
  .asset-head { padding: 24px 26px; display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
  .asset-head code { color: var(--muted); font: 12px var(--mono); }
  .asset-head p { margin: 5px 0 0; color: var(--muted); }
  .status-running { color: var(--amber); background: var(--amber-soft); }
  .status-failed { color: var(--red); background: var(--red-soft); }
  .pipeline { display: grid; grid-template-columns: repeat(8,minmax(108px,1fr)); gap: 9px;
    padding: 0 26px 26px; overflow-x: auto; }
  .stage { position: relative; min-height: 104px; padding: 12px 10px; border: 1px solid var(--line);
    border-radius: 10px; color: var(--ink); text-align: left; background: #fbfdfc; }
  .stage:hover, .stage.active { border-color: var(--blue); box-shadow: 0 0 0 2px rgba(55,98,215,.12); }
  .stage::after { content: ""; position: absolute; left: 100%; top: 31px; width: 10px; height: 1px; background: var(--line); }
  .stage:last-child::after { display: none; }
  .stage-num { display: block; margin-bottom: 12px; color: #87958f; font: 10px var(--mono); }
  .stage strong { display: block; max-width: 12ch; font-size: 12px; line-height: 1.25;
    text-wrap: balance; overflow-wrap: normal; }
  .stage small { display: block; margin-top: 6px; color: var(--muted); font-size: 10px;
    line-height: 1.25; white-space: nowrap; }
  .stage.completed { border-color: #95ceb9; background: var(--green-soft); }
  .stage.running { border-color: #e5bd6e; background: var(--amber-soft); }
  .stage.failed { border-color: #e1a09b; background: var(--red-soft); }
  .stage.active, .stage.active:hover { color: white; border-color: var(--blue); background: var(--blue);
    box-shadow: 0 0 0 3px rgba(55,98,215,.2), 0 8px 18px rgba(55,98,215,.2); }
  .stage.active .stage-num, .stage.active small { color: #dbe4ff; }
  .stage-detail { margin-top: 18px; overflow: hidden; }
  .stage-hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px;
    padding: 26px; border-bottom: 1px solid var(--line); background: linear-gradient(120deg,#fff,#f3f8f5); }
  .stage-hero .eyebrow, .eyebrow { margin: 0 0 6px; color: var(--green); font-size: 11px;
    font-weight: 800; letter-spacing: .09em; text-transform: uppercase; }
  .stage-hero h2 { font-size: 25px; }
  .stage-hero p:last-child { max-width: 700px; margin: 8px 0 0; color: var(--muted); }
  .stage-stat { min-width: 120px; text-align: right; }
  .stage-stat strong { display: block; font-size: 28px; }
  .stage-stat span { color: var(--muted); font-size: 12px; }
  .process-map { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; padding: 22px 26px; }
  .process-column { padding: 15px; border: 1px solid var(--line); border-radius: 10px; background: #fbfdfc; }
  .process-column > strong { display: block; margin-bottom: 10px; color: var(--muted);
    font-size: 11px; letter-spacing: .07em; text-transform: uppercase; }
  .process-item { display: flex; gap: 8px; padding: 8px 0; border-top: 1px solid #edf1ef; font-size: 13px; }
  .process-item:first-of-type { border: 0; }
  .process-item i { color: var(--green); font-style: normal; font-weight: 800; }
  .stage-body { display: grid; grid-template-columns: minmax(220px,.72fr) minmax(0,1.4fr);
    gap: 18px; padding: 0 26px 26px; }
  .artifact-menu, .example-panel { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
  .subhead { padding: 13px 15px; border-bottom: 1px solid var(--line); background: #f6f9f7; }
  .subhead strong { display: block; font-size: 13px; }
  .subhead span { color: var(--muted); font-size: 11px; }
  .artifact-button { display: grid; grid-template-columns: 1fr auto; gap: 8px; width: 100%;
    padding: 12px 14px; border: 0; border-top: 1px solid #edf1ef; color: var(--ink);
    text-align: left; background: white; }
  .artifact-button:first-of-type { border-top: 0; }
  .artifact-button:hover, .artifact-button.active { background: var(--green-soft); }
  .artifact-button strong { overflow: hidden; text-overflow: ellipsis; font: 12px var(--mono); }
  .artifact-button span { color: var(--muted); font-size: 11px; }
  .example-toolbar { display: flex; justify-content: space-between; gap: 10px; padding: 10px 14px;
    color: var(--muted); background: #17231f; font-size: 11px; }
  .example-panel pre { min-height: 290px; max-height: 500px; margin: 0; padding: 17px;
    overflow: auto; color: #d9eee5; background: #1e2d28; font: 12px/1.6 var(--mono); white-space: pre-wrap; }
  .json-key { color: #8bd5ff; } .json-string { color: #b9e78c; }
  .json-number { color: #ffd479; } .json-boolean { color: #d6a3ff; } .json-null { color: #9eaaa5; }
  .feedback-key { margin: 0 -2px; padding: 2px; border-radius: 4px; color: #fff;
    background: #a33a3a; }
  .coverage-report-panel { margin: 0 26px 24px; padding: 24px; }
  .coverage-report-head { display: flex; align-items: flex-start; justify-content: space-between;
    gap: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--line); }
  .coverage-report-head h3 { font-size: 18px; }
  .coverage-report-head span { color: var(--muted); font: 11px var(--mono); }
  .coverage-markdown { padding-top: 5px; color: #34423d; font-size: 13px; line-height: 1.55; }
  .coverage-markdown h1 { margin: 20px 0 8px; font-size: 22px; }
  .coverage-markdown h2 { margin: 22px 0 8px; padding-bottom: 6px; border-bottom: 1px solid var(--line);
    font-size: 16px; }
  .coverage-markdown h3 { margin: 18px 0 7px; font-size: 14px; }
  .coverage-markdown p { margin: 8px 0; }
  .coverage-markdown ul, .coverage-markdown ol { margin: 8px 0; padding-left: 22px; }
  .coverage-markdown code { padding: 2px 5px; border-radius: 4px; color: #3155b0;
    background: var(--blue-soft); font: 11px var(--mono); }
  .coverage-markdown pre { margin: 12px 0; padding: 14px; overflow: auto; border-radius: 8px;
    color: #d9eee5; background: #1e2d28; }
  .coverage-markdown pre code { padding: 0; color: inherit; background: transparent; }
  .coverage-table-wrap { margin: 12px 0; overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }
  .coverage-markdown table { width: 100%; border-collapse: collapse; white-space: nowrap; }
  .coverage-markdown td { padding: 9px 10px; border-bottom: 1px solid #e7ece9; text-align: left; vertical-align: top; }
  .coverage-markdown tr:first-child td { color: var(--muted); background: #f6f9f7;
    font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
  .coverage-markdown tr:last-child td { border-bottom: 0; }
  .coverage-report-note { margin-top: 12px; color: var(--amber); font-size: 12px; }
  .cluster-view { margin: 0 26px 24px; padding: 20px; border: 1px solid var(--line);
    border-radius: 12px; background: rgba(255,255,255,.88); }
  .cluster-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
  .cluster-head > div { max-width: 720px; }
  .cluster-head p:last-child { margin: 7px 0 0; color: var(--muted); font-size: 13px; }
  .cluster-summary { min-width: 130px; padding-left: 20px; border-left: 1px solid var(--line); text-align: right; }
  .cluster-summary strong { display: block; color: var(--blue); font-size: 30px; line-height: 1; }
  .cluster-summary span { color: var(--muted); font-size: 10px; }
  .cluster-route-filters { display: flex; gap: 7px; margin-top: 18px; overflow-x: auto; }
  .cluster-route-filters button { flex: 0 0 auto; padding: 7px 11px; border: 1px solid var(--line);
    border-radius: 999px; color: var(--muted); background: white; font-size: 11px; }
  .cluster-route-filters button.active { color: white; border-color: #26473c; background: #1d332c; }
  .cluster-visible { margin-left: auto; align-self: center; color: var(--muted); font-size: 10px; white-space: nowrap; }
  .cluster-layout { display: grid; grid-template-columns: minmax(0,1fr) 280px; gap: 13px; margin-top: 13px; }
  .cluster-canvas { position: relative; min-width: 0; min-height: 430px; padding: 12px 16px 28px 28px;
    overflow: hidden; border: 1px solid #dce4e0; border-radius: 11px; background: #f8faf7; }
  .cluster-canvas svg { display: block; width: 100%; min-height: 390px; }
  .cluster-node { cursor: pointer; outline: none; }
  .cluster-node circle { transition: r .16s ease, fill-opacity .16s ease; }
  .cluster-node:hover circle:last-of-type { fill-opacity: 1; }
  .cluster-count { fill: white; font: 700 10px ui-sans-serif,system-ui,sans-serif; pointer-events: none; }
  .cluster-node-label { fill: #31413b; font: 650 9px ui-sans-serif,system-ui,sans-serif;
    paint-order: stroke; stroke: #f8faf7; stroke-width: 4px; pointer-events: none; }
  .projection-label { position: absolute; color: #87948f; font-size: 8px; font-weight: 700;
    letter-spacing: .09em; text-transform: uppercase; }
  .projection-label.y { left: 8px; top: 54%; transform: rotate(-90deg) translateX(-50%); transform-origin: left top; }
  .projection-label.x { left: 50%; bottom: 8px; transform: translateX(-50%); }
  .cluster-key { position: absolute; top: 10px; right: 12px; padding: 6px 8px; border: 1px solid var(--line);
    border-radius: 7px; color: var(--muted); background: rgba(255,255,255,.9); font-size: 9px; }
  .cluster-inspector { padding: 18px; border: 1px solid var(--line); border-radius: 11px; background: white; }
  .cluster-inspector-head { display: flex; align-items: center; gap: 9px; }
  .cluster-inspector-head i { width: 10px; height: 36px; border-radius: 999px; background: var(--cluster-color); }
  .cluster-inspector-head span { display: block; color: var(--muted); font-size: 9px;
    letter-spacing: .07em; text-transform: uppercase; }
  .cluster-inspector-head strong { display: block; margin-top: 2px; font-size: 16px; }
  .cluster-id { margin-top: 13px; padding: 7px 9px; border-radius: 7px; color: #4d5d57;
    background: #eff3f0; font: 10px var(--mono); overflow-wrap: anywhere; }
  .cluster-stats { display: grid; grid-template-columns: repeat(2,1fr); margin: 14px 0;
    border-block: 1px solid var(--line); }
  .cluster-stats div { padding: 10px 4px; }
  .cluster-stats span { display: block; color: var(--muted); font-size: 9px; }
  .cluster-stats strong { display: block; margin-top: 3px; }
  .representatives { margin-top: 12px; }
  .representatives > strong { color: var(--muted); font-size: 10px; text-transform: uppercase; }
  .representatives p { margin: 8px 0 0; padding-top: 8px; border-top: 1px solid #e7ebe8;
    color: #485752; font-size: 11px; line-height: 1.45; }
  .cluster-tools { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 13px; }
  .cluster-tools span { padding: 3px 6px; border-radius: 5px; color: #3d6256;
    background: var(--green-soft); font: 9px var(--mono); }
  .stage-nav { display: flex; align-items: center; justify-content: space-between; padding: 0 26px 24px; }
  .stage-nav button { padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; background: white; }
  .stage-nav button:disabled { opacity: .35; cursor: default; }
  .grid { display: grid; grid-template-columns: 1.05fr 1fr; gap: 18px; margin-top: 18px; }
  .panel { padding: 22px; }
  .facts { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px; margin-top: 16px; }
  .fact { min-width: 0; padding: 13px; border-radius: 9px; background: #f5f8f6; }
  .fact span { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
  .fact strong { display: block; margin-top: 5px; overflow-wrap: anywhere; font-size: 13px; }
  .dirs { display: grid; gap: 9px; margin-top: 16px; }
  .dir { display: grid; grid-template-columns: 1fr auto; gap: 12px; padding: 12px 13px; border: 1px solid var(--line); border-radius: 9px; }
  .dir code { display: block; margin-top: 3px; color: var(--muted); font: 11px var(--mono); overflow-wrap: anywhere; }
  .count { align-self: center; color: var(--green); font-weight: 800; }
  .error-box { margin: 0 26px 24px; padding: 14px; border: 1px solid #e1a09b; border-radius: 9px;
    color: #842d2d; background: var(--red-soft); }
  .error-box button { margin-top: 10px; padding: 7px 12px; border: 1px solid #d07c75; border-radius: 7px;
    color: #842d2d; background: white; font-weight: 700; }
  .asset-list { display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 18px; }
  .asset-chip { padding: 7px 11px; border: 1px solid var(--line); border-radius: 999px; background: white; }
  .asset-chip.active { color: white; border-color: var(--green); background: var(--green); }
  @media (max-width: 850px) {
    .shell { grid-template-columns: 1fr; } aside { padding: 16px; }
    .brand { margin-bottom: 12px; } .side-label { display: none; }
    #tenant-list { display: flex; overflow-x: auto; }
    .back { margin-top: 12px; } main { padding: 24px 16px 50px; }
    form, .grid, .process-map, .stage-body, .contract-grid { grid-template-columns: 1fr; }
    .wide, .form-actions { grid-column: auto; }
    .stage-hero { flex-direction: column; } .stage-stat { text-align: left; }
    .cluster-layout { grid-template-columns: 1fr; } .cluster-head { display: block; }
    .cluster-summary { margin-top: 12px; padding: 0; border: 0; text-align: left; }
  }
</style>
</head>
<body>
<div class="shell">
  <aside>
    <a class="brand" href="/evaluation-assets/">
      <img src="/assets/fapo-explorer-logo.webp" alt="">
      <span><strong>Evaluation Asset Studio</strong></span>
    </a>
    <button class="side-button active" id="new-button">＋ New evaluation asset</button>
    <div class="side-label">Tenants</div>
    <div id="tenant-list"></div>
    <a class="back" href="/">← Back to FAPO Explorer</a>
  </aside>
  <main id="main"></main>
</div>
<script>
const APP = { tenants: [], tenant: null, assets: [], assetId: null, stageKey: null,
  stageDetail: null, artifactIndex: 0, clusterRoute: 'All routes', clusterId: null,
  timer: null, busy: false };
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => (
  {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
));
const pretty = value => String(value || '').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
const CONTRACT_FIELD_HELP = {
  schema_version: 'Identifies the canonical FAPO input contract.',
  record_id: 'Stable unique identifier within this file.',
  group_id: 'Conversation or leakage boundary kept together during splitting.',
  task_type: 'Application-defined task family.',
  user_input: 'The current user request represented by this record.',
  conversation_context: 'Prior conversation messages; excludes the current request.',
  tool_calls: 'Observed tool names, arguments, results, and errors.',
  runtime: 'Model, application version, deployment, or enabled-tool facts.',
  metadata: 'Source provenance and other non-runtime attributes.'
};

function highlightJson(value) {
  return JSON.stringify(value, null, 2).replace(
    /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(?:\\s*:)?|\\btrue\\b|\\bfalse\\b|\\bnull\\b|-?\\d+(?:\\.\\d+)?(?:[eE][+\\-]?\\d+)?)/g,
    token => {
      let cls = 'json-number';
      if (token.startsWith('"')) cls = token.trimEnd().endsWith(':') ? 'json-key' : 'json-string';
      else if (token === 'true' || token === 'false') cls = 'json-boolean';
      else if (token === 'null') cls = 'json-null';
      return `<span class="${cls}">${esc(token)}</span>`;
    }
  );
}

function contractFieldRows(fields, types) {
  return fields.map(field => `<tr><td><code>${esc(field)}</code></td>
    <td class="field-type">${esc(types?.[field] || 'any')}</td>
    <td>${esc(CONTRACT_FIELD_HELP[field] || '')}</td></tr>`).join('');
}

async function renderContract() {
  APP.tenant = null; APP.assets = []; APP.assetId = null; APP.stageKey = null;
  APP.stageDetail = null;
  history.replaceState(null, '', '/evaluation-assets/');
  renderSidebar();
  const main = document.getElementById('main');
  main.innerHTML = '<section class="card empty">Loading the input contract…</section>';
  try {
    const contract = await api('/api/evaluation-assets/input-contract');
    const example = {
      schema_version: contract.schema_version,
      record_id: 'record-0001',
      group_id: 'conversation-0001',
      task_type: 'request_type',
      user_input: 'The current user request',
      conversation_context: [{role: 'user', content: 'An earlier message'}],
      tool_calls: [{name: 'lookup_records', arguments: {query: '...'}, result: null}],
      runtime: {model: 'model-name', application_version: 'version'},
      metadata: {source_system: 'application-export'},
      assistant_output: 'The response that received feedback',
      feedback: {polarity: 'negative', rationale: 'A required detail was missing.', source: 'user'}
    };
    main.innerHTML = `
      <div class="topbar"><div><h1>FAPO Evaluation Input v1</h1>
        <p class="lede">The vendor-neutral JSONL format required before the eight-stage pipeline begins.</p>
      </div><button class="contract-back" id="contract-back">← Back to setup</button></div>
      <section class="card contract-hero">
        <span class="schema-badge">${esc(contract.schema_version)}</span>
        <h2>One predictable boundary for every data source</h2>
        <p>Each line is one JSON object. Labeled and unlabeled files share the same core fields, so downstream stages never need vendor-specific field mappings.</p>
      </section>
      <div class="contract-grid">
        <section class="card contract-section wide">
          <h2>Required on every record</h2>
          <p>These fields must appear in both labeled and unlabeled JSONL files.</p>
          <table class="contract-table"><thead><tr><th>Field</th><th>Type</th><th>Purpose</th></tr></thead>
            <tbody>${contractFieldRows(contract.common_required_fields, contract.common_types)}</tbody></table>
        </section>
        <section class="card contract-section">
          <h2>Labeled records</h2>
          <p>Add the observed response and canonical feedback evidence.</p>
          <div class="contract-chips">${contract.feedback_polarities.map(value => `<span>${esc(value)}</span>`).join('')}</div>
          <table class="contract-table"><tbody>
            <tr><td><code>assistant_output</code></td><td class="field-type">string</td><td>Required, including when empty.</td></tr>
            ${contract.feedback.required.map(field => `<tr><td><code>feedback.${esc(field)}</code></td>
              <td class="field-type">${esc(contract.feedback.types[field])}</td><td>Required feedback field.</td></tr>`).join('')}
            ${contract.feedback.optional.map(field => `<tr><td><code>feedback.${esc(field)}</code></td>
              <td class="field-type">optional</td><td>Additional correction or provenance.</td></tr>`).join('')}
          </tbody></table>
        </section>
        <section class="card contract-section">
          <h2>Unlabeled records</h2>
          <p>Usage evidence describes what users ask for, not what is correct.</p>
          <div class="contract-callout"><strong>Do not include <code>feedback</code>.</strong><br>
            <code>assistant_output</code> may be retained for provenance, but it never becomes correctness evidence.</div>
          <h3 style="margin-top:18px">Optional common fields</h3>
          <div class="contract-chips">${contract.optional_fields.map(value => `<span>${esc(value)}</span>`).join('')}</div>
        </section>
        <section class="card contract-section">
          <h2>Conversation messages</h2>
          <p>Each prior message uses a compact, consistent shape.</p>
          <table class="contract-table"><tbody>
            ${contract.conversation_message.required.map(field => `<tr><td><code>${esc(field)}</code></td>
              <td class="field-type">${esc(contract.conversation_message.types[field])}</td><td>Required and non-empty.</td></tr>`).join('')}
          </tbody></table>
        </section>
        <section class="card contract-section">
          <h2>Tool calls</h2>
          <p>Preserve the trajectory without depending on a tracing vendor.</p>
          <table class="contract-table"><tbody>
            ${contract.tool_call.required.map(field => `<tr><td><code>${esc(field)}</code></td>
              <td class="field-type">${esc(contract.tool_call.types[field])}</td><td>Required on every tool call.</td></tr>`).join('')}
            ${contract.tool_call.optional.map(field => `<tr><td><code>${esc(field)}</code></td>
              <td class="field-type">optional</td><td>Observed result or error.</td></tr>`).join('')}
          </tbody></table>
        </section>
        <section class="card contract-section">
          <h2>Defaults and safety</h2>
          <p>Stage 1 validates these rules before any model or embedding call.</p>
          <ul class="contract-list">${contract.notes.map(note => `<li>${esc(note)}</li>`).join('')}</ul>
        </section>
        <section class="card contract-section wide">
          <h2>Complete labeled example</h2>
          <p>Write one object per line in the JSONL file.</p>
          <pre class="contract-code">${highlightJson(example)}</pre>
        </section>
      </div>`;
    document.getElementById('contract-back').onclick = renderCreate;
  } catch (error) {
    main.innerHTML = `<section class="card empty">${esc(error.message)}</section>`;
  }
}

const STAGE_INFO = {
  raw_inputs: {
    eyebrow: 'Source data', description: 'Validate and preserve the original labeled feedback and unlabeled records.',
    inputs: ['Labeled feedback JSONL', 'Unlabeled conversation JSONL'],
    process: ['Validate JSONL structure', 'Check required fields', 'Copy immutable source files'],
    outputs: ['Labeled feedback snapshot', 'Unlabeled input snapshot']
  },
  prepared_inputs: {
    eyebrow: 'Canonical preparation', description: 'Redact canonical input records and build stable representations for rubric extraction and clustering.',
    inputs: ['Validated FAPO Evaluation Input v1', 'Fixed canonical fields'],
    process: ['Redact feedback records', 'Build canonical intent text', 'Preserve provenance metadata'],
    outputs: ['Normalized feedback', 'Canonical intent records']
  },
  rubric_extraction: {
    eyebrow: 'Trusted evidence', description: 'Extract reusable evaluation rubrics from examples with direct user feedback.',
    inputs: ['Normalized labeled feedback', 'Assistant outputs and rationale'],
    process: ['Batch trusted examples', 'Extract must and must-not criteria', 'Validate structured rubric JSON'],
    outputs: ['Feedback rubrics', 'Trusted intents', 'Trusted evaluation cases']
  },
  intent_clustering: {
    eyebrow: 'Intent mining', description: 'Group canonical requests into an exact, reviewable set of intent clusters.',
    inputs: ['Canonical intent records', 'Embedding or TF-IDF vectors'],
    process: ['Vectorize intent text', 'Cluster within task routes', 'Select representative requests'],
    outputs: ['Intent inventory', 'Cluster representatives', 'Route-level cluster map']
  },
  coverage_decisions: {
    eyebrow: 'Trust boundary', description: 'Decide which mined clusters are supported by trusted feedback and which must be held.',
    inputs: ['Intent inventory', 'Trusted intents', 'Coverage policy'],
    process: ['Match clusters to trusted intents', 'Apply support thresholds', 'Record gaps and reasons'],
    outputs: ['Intent matches', 'Coverage report']
  },
  label_inference: {
    eyebrow: 'Reviewable inference', description: 'Infer labels only for clusters that pass the trusted coverage gate.',
    inputs: ['Matched clusters', 'Trusted rubrics', 'Unlabeled records'],
    process: ['Infer cluster rubrics', 'Build inferred cases', 'Report unsupported clusters'],
    outputs: ['Inferred rubrics and labels', 'Inferred cases', 'Missing-feedback queue and report']
  },
  synthetic_coverage: {
    eyebrow: 'Optional augmentation', description: 'When enabled, generate and filter additional cases for already-supported intent clusters.',
    inputs: ['Supported clusters', 'Representative requests', 'Inferred cluster rubrics'],
    process: ['Generate configured cases per cluster', 'Run quality filters', 'Reject unsafe or duplicate cases'],
    outputs: ['Accepted synthetic cases', 'Rejected candidates', 'Filter audit']
  },
  dataset_splits: {
    eyebrow: 'Evaluation dataset', description: 'Create deterministic, provenance-aware train, validation, test, and holdout splits.',
    inputs: ['Trusted cases', 'Inferred cases', 'Synthetic cases'],
    process: ['Reserve 20% of trusted groups for regression', 'Split all remaining provenance classes globally by group', 'Route regression-group collisions to triage'],
    outputs: ['Train split', 'Validation split', 'Test split', 'Automatic trusted regression gate']
  }
};

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function statusPill(status) {
  const value = status || 'not started';
  const cls = value === 'failed' ? 'status-failed' : ['running','queued'].includes(value) ? 'status-running' : '';
  return `<span class="pill ${cls}"><i class="dot"></i>${esc(pretty(value))}</span>`;
}

function renderSidebar() {
  document.getElementById('new-button').classList.toggle('active', !APP.tenant);
  document.getElementById('tenant-list').innerHTML = APP.tenants.map(t => `
    <button class="side-button ${APP.tenant === t.tenant_id ? 'active' : ''}"
      data-tenant="${esc(t.tenant_id)}">${esc(t.tenant_id)}
      <span class="tiny">${Number(t.evaluation_asset_count || 0)}</span>
    </button>`).join('') || '<div class="side-button">No tenants yet</div>';
  document.querySelectorAll('[data-tenant]').forEach(button => button.onclick = () => selectTenant(button.dataset.tenant));
}

function renderCreate() {
  APP.tenant = null; APP.assets = []; APP.assetId = null; APP.stageKey = null;
  APP.stageDetail = null;
  history.replaceState(null, '', '/evaluation-assets/');
  renderSidebar();
  document.getElementById('main').innerHTML = `
    <div class="topbar"><div><h1>Create an evaluation asset</h1>
      <p class="lede">Start a tenant from raw feedback and unlabeled conversations. FAPO copies the inputs into an independent asset workspace, then prepares, labels, clusters, and splits the data.</p>
    </div><span class="pill"><i class="dot"></i>Core pipeline</span></div>
    <section class="card new-card">
      <div class="section-head"><div><h2>Pipeline setup</h2>
        <p>Choose models, clustering and matching settings, and whether synthetic augmentation is needed.</p></div></div>
      <form id="asset-form">
        <div class="input-contract"><div><strong>FAPO Evaluation Input v1 required</strong>
          <p>Both JSONL files must already use the vendor-neutral canonical fields. Stage 1 validates every row before processing.</p></div>
          <button id="view-contract" type="button">View contract →</button>
        </div>
        <label>Tenant ID <span>A new tenant can begin with this asset.</span>
          <input name="tenant_id" required pattern="[A-Za-z0-9][A-Za-z0-9_-]*" placeholder="customer_or_project">
        </label>
        <label>Asset version <span>A stable name within this tenant.</span>
          <input name="asset_id" required value="v1" pattern="[A-Za-z0-9][A-Za-z0-9_-]*">
        </label>
        <label class="wide">Labeled feedback JSONL <span>Workspace path to examples that contain user feedback.</span>
          <input name="feedback_path" required placeholder="path/to/labeled_feedback.jsonl">
        </label>
        <label class="wide">Unlabeled JSONL <span>Workspace path to examples requiring inferred labels.</span>
          <input name="unlabeled_path" required placeholder="path/to/unlabeled.jsonl">
        </label>
        <label>Rubric extraction model <span>Extracts rubrics and infers reviewable labels.</span>
          <select name="rubric_model">
            <option value="gpt-5.5">GPT-5.5</option>
            <option value="gpt-5.4">GPT-5.4</option>
            <option value="gpt-5.2">GPT-5.2</option>
            <option value="gpt-5.1">GPT-5.1</option>
            <option value="gpt-5">GPT-5</option>
            <option value="gpt-4.1">GPT-4.1</option>
            <option value="gpt-4.1-mini">GPT-4.1 mini</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4o-mini">GPT-4o mini</option>
            <option value="o3">o3</option>
            <option value="o4-mini">o4-mini</option>
          </select>
        </label>
        <label>Embedding model <span>Embeds examples for intent mining.</span>
          <select name="embedding_model">
            <option value="text-embedding-3-small">text-embedding-3-small</option>
            <option value="text-embedding-3-large">text-embedding-3-large</option>
            <option value="text-embedding-ada-002">text-embedding-ada-002 (legacy)</option>
            <option value="tfidf">TF-IDF (local fallback · no API)</option>
          </select>
        </label>
        <label>Number of intent clusters <span>The pipeline creates exactly this many clusters.</span>
          <input name="cluster_count" type="number" min="1" max="1000" value="50" required>
        </label>
        <label>Intent match threshold <span>Minimum Stage 5 cosine score for a trusted-intent match.</span>
          <input name="match_threshold" type="number" min="0" max="1" step="0.01" value="0.6" required>
        </label>
        <label>Stage 7 synthetic coverage <span>Optional augmentation after real unlabeled records are labeled.</span>
          <select id="synthetic-enabled" name="synthetic_coverage_enabled">
            <option value="false" selected>Disabled</option>
            <option value="true">Enabled</option>
          </select>
        </label>
        <label id="synthetic-count-label">Data points per supported cluster <span>Exact number requested from the LLM for each matched cluster.</span>
          <input id="synthetic-count" name="synthetic_cases_per_cluster" type="number" min="1" max="100" value="1" required>
        </label>
        <div class="model-note"><strong>Model roles</strong><br>Rubric model → extraction and label inference<br>Embedding model → similarity and intent clustering</div>
        <div class="form-actions"><button class="primary" type="submit">Create &amp; run pipeline</button>
          <span class="message" id="form-message"></span></div>
      </form>
    </section>`;
  document.getElementById('asset-form').onsubmit = startAsset;
  document.getElementById('view-contract').onclick = renderContract;
  const syntheticEnabled = document.getElementById('synthetic-enabled');
  const syntheticCount = document.getElementById('synthetic-count');
  const syntheticCountLabel = document.getElementById('synthetic-count-label');
  const syncSyntheticControls = () => {
    const enabled = syntheticEnabled.value === 'true';
    syntheticCount.disabled = !enabled;
    syntheticCountLabel.classList.toggle('disabled-control', !enabled);
  };
  syntheticEnabled.onchange = syncSyntheticControls;
  syncSyntheticControls();
}

async function startAsset(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type=submit]');
  const message = document.getElementById('form-message');
  const values = Object.fromEntries(new FormData(form));
  values.cluster_count = Number(values.cluster_count);
  values.match_threshold = Number(values.match_threshold);
  values.synthetic_coverage_enabled = values.synthetic_coverage_enabled === 'true';
  values.synthetic_cases_per_cluster = Number(values.synthetic_cases_per_cluster || 1);
  button.disabled = true; message.className = 'message'; message.textContent = 'Creating workspace…';
  try {
    await api('/api/evaluation-assets/start', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(values)
    });
    if (!APP.tenants.some(t => t.tenant_id === values.tenant_id)) {
      APP.tenants.push({tenant_id: values.tenant_id, evaluation_asset_count: 1});
      APP.tenants.sort((a,b) => a.tenant_id.localeCompare(b.tenant_id));
    }
    await selectTenant(values.tenant_id);
  } catch (error) {
    message.className = 'message error'; message.textContent = error.message; button.disabled = false;
  }
}

async function selectTenant(tenant) {
  if (APP.tenant !== tenant) {
    APP.assetId = null; APP.stageKey = null; APP.stageDetail = null;
  }
  APP.tenant = tenant; APP.busy = true;
  history.replaceState(null, '', `/evaluation-assets/?tenant=${encodeURIComponent(tenant)}`);
  renderSidebar();
  document.getElementById('main').innerHTML = '<section class="card empty">Loading evaluation assets…</section>';
  try {
    APP.assets = await api(`/api/tenants/${encodeURIComponent(tenant)}/evaluation-assets`);
    if (!APP.assets.some(a => a.asset_id === APP.assetId)) APP.assetId = APP.assets[0]?.asset_id || null;
    renderTenant();
  } catch (error) {
    document.getElementById('main').innerHTML = `<section class="card empty">${esc(error.message)}</section>`;
  } finally { APP.busy = false; }
}

const STAGE_CARD_LABELS = {
  raw_inputs: 'Raw inputs',
  prepared_inputs: 'Prepare data',
  rubric_extraction: 'Extract rubrics',
  intent_clustering: 'Mine intents',
  coverage_decisions: 'Match coverage',
  label_inference: 'Infer labels',
  synthetic_coverage: 'Synthetic',
  dataset_splits: 'Build splits'
};

function stageCardResult(stage, counts) {
  if (stage.status === 'failed') return 'Needs attention';
  if (stage.status === 'running') return 'In progress';
  if (stage.status === 'pending') return 'Waiting';
  const metrics = {
    raw_inputs: ['feedback_records', 'unlabeled_records', 'records'],
    prepared_inputs: ['prepared_feedback', 'prepared_intents', 'prepared'],
    rubric_extraction: ['feedback_rubrics', null, 'rubrics'],
    intent_clustering: ['intent_clusters', null, 'clusters'],
    coverage_decisions: ['matched_clusters', null, 'matched'],
    label_inference: ['inferred_cases', null, 'inferred'],
    synthetic_coverage: ['synthetic_cases', null, 'synthetic'],
    dataset_splits: ['dataset_cases', null, 'cases']
  }[stage.stage];
  if (!metrics) return 'Done';
  const total = Number(counts?.[metrics[0]] || 0)
    + (metrics[1] ? Number(counts?.[metrics[1]] || 0) : 0);
  return `${total.toLocaleString()} ${metrics[2]}`;
}

function stageCards(asset) {
  const counts = asset.state?.counts || {};
  return (asset.state?.stages || []).map((stage,index) => `
    <button class="stage ${esc(stage.status)} ${APP.stageKey === stage.stage ? 'active' : ''}"
      data-stage="${esc(stage.stage)}" aria-pressed="${APP.stageKey === stage.stage}">
      <span class="stage-num">0${index + 1} · ${esc(pretty(stage.status))}</span>
      <strong>${esc(STAGE_CARD_LABELS[stage.stage] || stage.label)}</strong>
      <small>${esc(stageCardResult(stage, counts))}</small>
    </button>`).join('');
}

function renderTenant() {
  const asset = APP.assets.find(a => a.asset_id === APP.assetId) || APP.assets[0];
  const title = `<div class="topbar"><div><h1>${esc(APP.tenant)}</h1>
    <p class="lede">Evaluation asset preparation is isolated from tenant prompts, configs, and datasets.</p>
    </div><button class="primary" id="another">＋ New asset</button></div>`;
  if (!asset) {
    document.getElementById('main').innerHTML = title +
      '<section class="card empty"><h2>No evaluation assets yet</h2><p>Create the first asset for this tenant.</p></section>';
    document.getElementById('another').onclick = renderCreate;
    return;
  }
  const config = asset.config || {}, state = asset.state || {}, dirs = asset.directories || {};
  const stages = state.stages || [];
  if (!APP.stageKey || !stages.some(stage => stage.stage === APP.stageKey)) {
    APP.stageKey = state.current_stage || stages.find(stage => stage.status !== 'pending')?.stage || stages[0]?.stage;
    APP.stageDetail = null;
  }
  const chips = APP.assets.map(item => `<button class="asset-chip ${item.asset_id === asset.asset_id ? 'active' : ''}"
    data-asset="${esc(item.asset_id)}">${esc(item.asset_id)}</button>`).join('');
  const facts = [
    ['Rubric extraction', config.rubric_model],
    ['Intent embeddings', config.embedding_provider === 'tfidf'
      ? 'TF-IDF · local fallback' : config.embedding_model],
    ['Requested clusters', config.cluster_count],
    ['Intent match threshold', config.match_threshold],
    ['Synthetic coverage', config.synthetic_coverage_enabled ? 'Enabled' : 'Disabled'],
    ['Synthetic cases / cluster', config.synthetic_cases_per_cluster],
    ['Current stage', pretty(state.current_stage || state.status)],
    ...Object.entries(state.counts || {}).map(([key,value]) => [pretty(key), value])
  ];
  const dirCards = Object.entries(dirs).map(([name,info]) => `
    <div class="dir"><div><strong>${esc(pretty(name))}</strong><code>${esc(info.path)}</code></div>
      <span class="count">${Number(info.file_count || 0)} files</span></div>`).join('');
  document.getElementById('main').innerHTML = title + `<div class="asset-list">${chips}</div>
    <section class="card">
      <div class="asset-head"><div><h2>Asset ${esc(asset.asset_id)}</h2>
        <p><code>${esc(asset.path)}</code> · updated ${esc(state.updated_at || '—')}</p></div>${statusPill(state.status)}</div>
      ${state.error ? `<div class="error-box"><strong>Pipeline stopped</strong><br>${esc(state.error)}
        <br><button id="resume">Resume from failed stage</button></div>` : ''}
      <div class="pipeline">${stageCards(asset)}</div>
    </section>
    <div id="stage-detail">${renderStageDetail(asset)}</div>
    <div class="grid">
      <section class="card panel"><h3>Pipeline decisions</h3><div class="facts">
        ${facts.map(([key,value]) => `<div class="fact"><span>${esc(key)}</span><strong>${esc(value ?? '—')}</strong></div>`).join('')}
      </div></section>
      <section class="card panel"><h3>Self-contained artifacts</h3><div class="dirs">${dirCards}</div></section>
    </div>`;
  document.getElementById('another').onclick = renderCreate;
  document.querySelectorAll('[data-asset]').forEach(button => button.onclick = () => {
    APP.assetId = button.dataset.asset; APP.stageKey = null; APP.stageDetail = null;
    renderTenant();
  });
  document.querySelectorAll('[data-stage]').forEach(button => {
    button.onclick = () => selectStage(button.dataset.stage);
  });
  wireStageDetail(asset);
  const resume = document.getElementById('resume');
  if (resume) resume.onclick = () => resumeAsset(asset.asset_id);
  if (!APP.stageDetail || APP.stageDetail.stage !== APP.stageKey) loadStage(asset.asset_id);
}

function renderStageDetail(asset) {
  const stateStage = (asset.state?.stages || []).find(stage => stage.stage === APP.stageKey);
  if (!APP.stageDetail || APP.stageDetail.stage !== APP.stageKey) {
    return '<section class="card stage-detail empty">Loading stage details…</section>';
  }
  const detail = APP.stageDetail;
  let info = STAGE_INFO[detail.stage] || {};
  if (detail.stage === 'synthetic_coverage' && !detail.config?.synthetic_coverage_enabled) {
    info = {
      eyebrow: 'Optional augmentation',
      description: 'Synthetic coverage is disabled for this asset; Stage 7 makes no model calls.',
      inputs: ['Persisted asset configuration'],
      process: ['Skip synthetic generation', 'Write empty audit artifacts'],
      outputs: ['Empty synthetic candidate and accepted-case files']
    };
  } else if (detail.stage === 'synthetic_coverage') {
    info = {
      ...info,
      description: `Generate exactly ${Number(detail.config?.synthetic_cases_per_cluster || 1)} candidate data points per supported cluster, then filter them.`
    };
  }
  const artifacts = detail.artifacts || [];
  if (APP.artifactIndex >= artifacts.length) APP.artifactIndex = 0;
  const artifact = artifacts[APP.artifactIndex];
  const countEntries = stageMetrics(detail);
  return `<section class="card stage-detail">
    <div class="stage-hero"><div><p class="eyebrow">${esc(info.eyebrow || 'Pipeline stage')}</p>
      <h2>${esc(detail.label)}</h2><p>${esc(info.description || detail.message)}</p></div>
      <div class="stage-stat"><strong>${esc(stagePrimaryCount(detail))}</strong>
        <span>${esc(pretty(detail.status))}</span></div></div>
    <div class="process-map">
      ${processColumn('Inputs', info.inputs || [])}
      ${processColumn('What happens', info.process || [])}
      ${processColumn('Outputs', info.outputs || [])}
    </div>
    ${detail.stage === 'intent_clustering' ? renderClusterView(detail) : ''}
    <div class="stage-body">
      <div class="artifact-menu"><div class="subhead"><strong>Stage artifacts</strong>
        <span>${artifacts.length} files · click to inspect</span></div>
        ${artifacts.length ? artifacts.map((item,index) => `<button class="artifact-button ${index === APP.artifactIndex ? 'active' : ''}"
          data-artifact="${index}"><strong>${esc(item.name)}</strong>
          <span>${item.row_count === null ? pretty(item.kind) : `${Number(item.row_count)} rows`}</span></button>`).join('')
          : '<div class="empty">Artifacts appear when this stage runs.</div>'}
      </div>
      <div class="example-panel"><div class="subhead"><strong>Example data</strong>
        <span>${artifact ? esc(artifact.path) : 'No output yet'}</span></div>
        ${artifact ? `<div class="example-toolbar"><span>${esc(artifact.name)}</span>
          <span>${artifact.row_count === null ? 'report preview' : `1 example of ${Number(artifact.row_count)} rows`}</span></div>
          <pre>${formatArtifactPreview(artifact, detail.stage)}</pre>` : '<div class="empty">No preview available.</div>'}
      </div>
    </div>
    ${detail.stage === 'coverage_decisions' ? renderCoverageReport(detail) : ''}
    <div class="facts" style="padding:0 26px 24px">
      ${countEntries.map(([key,value]) => `<div class="fact"><span>${esc(key)}</span><strong>${esc(value)}</strong></div>`).join('')}
    </div>
    ${stageNavigation(asset)}
  </section>`;
}

function processColumn(label, items) {
  return `<div class="process-column"><strong>${esc(label)}</strong>${items.map((item,index) =>
    `<div class="process-item"><i>${label === 'What happens' ? String(index + 1).padStart(2,'0') : '→'}</i>
      <span>${esc(item)}</span></div>`).join('')}</div>`;
}

function stageMetrics(detail) {
  const keys = {
    raw_inputs: ['feedback_records','unlabeled_records'],
    prepared_inputs: ['feedback_records','unlabeled_records'],
    rubric_extraction: ['feedback_rubrics'],
    intent_clustering: ['intent_clusters'],
    coverage_decisions: ['matched_clusters','needs_more_feedback_clusters','missing_label_clusters'],
    label_inference: ['inferred_cases','feedback_rubrics'],
    synthetic_coverage: ['synthetic_cases'],
    dataset_splits: ['dataset_cases','train_cases','validation_cases','test_cases','regression_trusted_cases']
  }[detail.stage] || [];
  const metrics = keys.filter(key => detail.counts?.[key] !== undefined)
    .map(key => [pretty(key), Number(detail.counts[key]).toLocaleString()]);
  metrics.push(['Artifacts created', String((detail.artifacts || []).length)]);
  if (detail.message) metrics.push(['Stage result', detail.message]);
  return metrics;
}

function stagePrimaryCount(detail) {
  const metrics = stageMetrics(detail);
  return metrics.length && /^\d/.test(String(metrics[0][1])) ? metrics[0][1] : (detail.artifacts || []).length;
}

function formatArtifactPreview(artifact, stage) {
  if (artifact.kind === 'markdown') return esc(artifact.preview || 'This artifact is empty.');
  const example = (artifact.preview || [])[0];
  if (example === undefined) return 'This artifact is empty.';
  const json = JSON.stringify(example, null, 2);
  return json.replace(
    /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(?:\\s*:)?|\\btrue\\b|\\bfalse\\b|\\bnull\\b|-?\\d+(?:\\.\\d+)?(?:[eE][+\\-]?\\d+)?)/g,
    token => {
      let cls = 'json-number';
      if (token.startsWith('"')) cls = token.trimEnd().endsWith(':') ? 'json-key' : 'json-string';
      else if (token === 'true' || token === 'false') cls = 'json-boolean';
      else if (token === 'null') cls = 'json-null';
      if (stage === 'raw_inputs' && artifact.name.startsWith('labeled_') && token.startsWith('"feedback"')) {
        cls += ' feedback-key';
      }
      return `<span class="${cls}">${esc(token)}</span>`;
    }
  );
}

function renderCoverageMarkdown(source) {
  let markdown = String(source || '').replace(/<!--[\s\S]*?-->/g, '').trim();
  const codeBlocks = [];
  markdown = markdown.replace(/```(?:\w+)?\n([\s\S]*?)```/g, (match, code) => {
    codeBlocks.push(`<pre><code>${esc(code.replace(/\n$/, ''))}</code></pre>`);
    return `@@COVERAGE_CODE_${codeBlocks.length - 1}@@`;
  });
  const inline = text => esc(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
  let html = '';
  let listType = null;
  let inTable = false;
  const closeList = () => {
    if (listType) { html += `</${listType}>`; listType = null; }
  };
  const closeTable = () => {
    if (inTable) { html += '</tbody></table></div>'; inTable = false; }
  };
  for (const raw of markdown.split('\n')) {
    const code = raw.match(/^@@COVERAGE_CODE_(\d+)@@$/);
    if (code) {
      closeList(); closeTable(); html += codeBlocks[Number(code[1])]; continue;
    }
    const line = raw.trimEnd();
    let match;
    if ((match = line.match(/^(#{1,3})\s+(.*)$/))) {
      closeList(); closeTable();
      const level = match[1].length;
      html += `<h${level}>${inline(match[2])}</h${level}>`;
      continue;
    }
    if (/^\s*\|.*\|\s*$/.test(line)) {
      if (/^\s*\|?[\s:\-|]+\|?\s*$/.test(line)) continue;
      const cells = line.trim().replace(/^\||\|$/g, '').split('|').map(cell => cell.trim());
      if (!inTable) {
        closeList();
        html += '<div class="coverage-table-wrap"><table><tbody>';
        inTable = true;
      }
      html += `<tr>${cells.map(cell => `<td>${inline(cell)}</td>`).join('')}</tr>`;
      continue;
    }
    closeTable();
    if ((match = line.match(/^\s*[-*+]\s+(.*)$/))) {
      if (listType !== 'ul') { closeList(); html += '<ul>'; listType = 'ul'; }
      html += `<li>${inline(match[1])}</li>`;
      continue;
    }
    if ((match = line.match(/^\s*\d+\.\s+(.*)$/))) {
      if (listType !== 'ol') { closeList(); html += '<ol>'; listType = 'ol'; }
      html += `<li>${inline(match[1])}</li>`;
      continue;
    }
    closeList();
    if (line.trim()) html += `<p>${inline(line)}</p>`;
  }
  closeList();
  closeTable();
  return html;
}

function renderCoverageReport(detail) {
  const report = (detail.artifacts || []).find(item => item.name === 'coverage_report.md');
  if (!report) return '';
  return `<section class="card coverage-report-panel">
    <div class="coverage-report-head"><div><p class="eyebrow">Rendered artifact</p>
      <h3>Coverage report</h3></div><span>${esc(report.path)}</span></div>
    <div class="coverage-markdown">${renderCoverageMarkdown(report.content || report.preview)}</div>
    ${report.content_truncated ? '<div class="coverage-report-note">This rendered view is truncated at 100,000 characters.</div>' : ''}
  </section>`;
}

function renderClusterView(detail) {
  const clusters = Array.isArray(detail.clusters) ? detail.clusters : [];
  if (!clusters.length) return '';
  const routes = ['All routes', ...new Set(clusters.map(cluster => cluster.route || 'unknown'))];
  if (!routes.includes(APP.clusterRoute)) APP.clusterRoute = 'All routes';
  const visible = clusters.filter(cluster => APP.clusterRoute === 'All routes' || cluster.route === APP.clusterRoute);
  if (!visible.some(cluster => cluster.cluster_id === APP.clusterId)) APP.clusterId = visible[0]?.cluster_id;
  const selected = visible.find(cluster => cluster.cluster_id === APP.clusterId) || visible[0];
  const routeColors = Object.fromEntries(routes.slice(1).map((route,index) => [route, clusterColor(index)]));
  return `<section class="cluster-view"><div class="cluster-head"><div>
      <p class="eyebrow">Interactive clustering view</p><h3>Explore the intent inventory</h3>
      <p>This two-dimensional projection mirrors the mock explorer. Bubble size represents records and color represents the task route.</p>
    </div><div class="cluster-summary"><strong>${Number(detail.counts?.intent_clusters || clusters.length)}</strong>
      <span>clusters across ${routes.length - 1} routes</span></div></div>
    <div class="cluster-route-filters">${routes.map(route => `<button data-cluster-route="${esc(route)}"
      class="${route === APP.clusterRoute ? 'active' : ''}">${esc(pretty(route))}</button>`).join('')}
      <span class="cluster-visible">${visible.length} shown</span></div>
    <div class="cluster-layout">
      <div class="cluster-canvas"><span class="projection-label y">Semantic projection 2</span>
        <svg viewBox="0 0 760 430" role="img" aria-label="Intent cluster projection">
          <defs><pattern id="cluster-grid" width="76" height="43" patternUnits="userSpaceOnUse">
            <path d="M 76 0 L 0 0 0 43" fill="none" stroke="#dfe6e2" stroke-width="1"/></pattern></defs>
          <rect width="760" height="430" fill="url(#cluster-grid)"/>
          <line x1="36" y1="395" x2="730" y2="395" stroke="#aebbb5"/>
          <line x1="36" y1="30" x2="36" y2="395" stroke="#aebbb5"/>
          ${visible.map(cluster => clusterNode(cluster, clusters, routes.slice(1), routeColors)).join('')}
        </svg>
        <span class="projection-label x">Semantic projection 1</span>
        <span class="cluster-key">bubble size = records</span>
      </div>
      ${clusterInspector(selected, routeColors[selected.route])}
    </div>
  </section>`;
}

function clusterNode(cluster, clusters, routes, colors) {
  const routeIndex = Math.max(0, routes.indexOf(cluster.route));
  const routeMembers = clusters.filter(item => item.route === cluster.route);
  const memberIndex = routeMembers.findIndex(item => item.cluster_id === cluster.cluster_id);
  const columns = Math.max(1, Math.ceil(Math.sqrt(routes.length)));
  const centerX = 105 + (routeIndex % columns) * (560 / Math.max(1, columns - 1));
  const centerY = 90 + Math.floor(routeIndex / columns) * (245 / Math.max(1, Math.ceil(routes.length / columns) - 1));
  const hash = hashText(cluster.cluster_id || String(memberIndex));
  const angle = ((hash % 360) * Math.PI) / 180;
  const spread = 16 + ((hash >>> 8) % 72);
  const x = Math.max(45, Math.min(715, centerX + Math.cos(angle) * spread));
  const y = Math.max(38, Math.min(385, centerY + Math.sin(angle) * spread));
  const radius = Math.max(8, Math.min(22, 7 + Math.sqrt(Number(cluster.size || 1)) * 3));
  const active = cluster.cluster_id === APP.clusterId;
  const label = pretty(cluster.route);
  return `<g class="cluster-node" data-cluster-id="${esc(cluster.cluster_id)}" tabindex="0">
    <circle cx="${x}" cy="${y}" r="${radius + (active ? 6 : 0)}" fill="${colors[cluster.route]}"
      fill-opacity="${active ? '.2' : '.08'}"/>
    <circle cx="${x}" cy="${y}" r="${radius}" fill="${colors[cluster.route]}"
      fill-opacity="${active ? '.98' : '.78'}" stroke="${active ? '#fff' : colors[cluster.route]}" stroke-width="${active ? 3 : 1}"/>
    <text x="${x}" y="${y + 3.5}" text-anchor="middle" class="cluster-count">${Number(cluster.size || 0)}</text>
    ${(active || Number(cluster.size || 0) >= 7) ? `<text x="${x}" y="${y + radius + 14}"
      text-anchor="middle" class="cluster-node-label">${esc(label)}</text>` : ''}
  </g>`;
}

function clusterInspector(cluster, color) {
  if (!cluster) return '<div class="cluster-inspector">No clusters in this route.</div>';
  const representative = (cluster.representatives || [])[0] || cluster.cluster_id;
  const label = representative.length > 58 ? `${representative.slice(0, 55)}…` : representative;
  return `<div class="cluster-inspector" style="--cluster-color:${color}">
    <div class="cluster-inspector-head"><i></i><div><span>${esc(pretty(cluster.route))}</span>
      <strong>${esc(label)}</strong></div></div>
    <div class="cluster-id">${esc(cluster.cluster_id)}</div>
    <div class="cluster-stats"><div><span>Records</span><strong>${Number(cluster.size || 0)}</strong></div>
      <div><span>Tools</span><strong>${(cluster.tools || []).length || 'None'}</strong></div></div>
    <div class="representatives"><strong>Representative intents</strong>
      ${(cluster.representatives || []).map(text => `<p>“${esc(text)}”</p>`).join('') || '<p>No representative text available.</p>'}</div>
    <div class="cluster-tools">${(cluster.tools || []).map(tool => `<span>${esc(tool)}</span>`).join('') || '<span>no tool call</span>'}</div>
  </div>`;
}

function hashText(value) {
  let hash = 2166136261;
  for (const char of String(value)) { hash ^= char.charCodeAt(0); hash = Math.imul(hash, 16777619); }
  return hash >>> 0;
}

function clusterColor(index) {
  return ['#0e6b50','#4a70a4','#a76143','#7a5c99','#b34f54','#3f7d8c','#8b6b28','#526c58'][index % 8];
}

function stageNavigation(asset) {
  const stages = asset.state?.stages || [];
  const index = stages.findIndex(stage => stage.stage === APP.stageKey);
  return `<div class="stage-nav"><button data-stage-nav="${esc(stages[index - 1]?.stage || '')}"
      ${index <= 0 ? 'disabled' : ''}>← Previous stage</button>
    <span>${index + 1} / ${stages.length}</span>
    <button data-stage-nav="${esc(stages[index + 1]?.stage || '')}"
      ${index >= stages.length - 1 ? 'disabled' : ''}>Next stage →</button></div>`;
}

function wireStageDetail(asset) {
  document.querySelectorAll('[data-artifact]').forEach(button => button.onclick = () => {
    APP.artifactIndex = Number(button.dataset.artifact); updateStageDetail(asset);
  });
  document.querySelectorAll('[data-cluster-id]').forEach(node => node.onclick = () => {
    APP.clusterId = node.dataset.clusterId; updateStageDetail(asset);
  });
  document.querySelectorAll('[data-cluster-id]').forEach(node => node.onkeydown = event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault(); APP.clusterId = node.dataset.clusterId; updateStageDetail(asset);
    }
  });
  document.querySelectorAll('[data-cluster-route]').forEach(button => button.onclick = () => {
    APP.clusterRoute = button.dataset.clusterRoute; APP.clusterId = null; updateStageDetail(asset);
  });
  document.querySelectorAll('[data-stage-nav]').forEach(button => button.onclick = () => {
    if (button.dataset.stageNav) selectStage(button.dataset.stageNav);
  });
}

function updateStageDetail(asset) {
  const container = document.getElementById('stage-detail');
  if (!container) return;
  container.innerHTML = renderStageDetail(asset);
  wireStageDetail(asset);
}

async function selectStage(stage) {
  if (APP.stageKey === stage && APP.stageDetail) return;
  APP.stageKey = stage; APP.stageDetail = null; APP.artifactIndex = 0;
  APP.clusterRoute = 'All routes'; APP.clusterId = null;
  const asset = APP.assets.find(item => item.asset_id === APP.assetId) || APP.assets[0];
  renderTenant();
  document.getElementById('stage-detail')?.scrollIntoView({behavior:'smooth', block:'start'});
}

async function loadStage(assetId) {
  const requestedStage = APP.stageKey;
  try {
    const detail = await api(`/api/tenants/${encodeURIComponent(APP.tenant)}/evaluation-assets/${encodeURIComponent(assetId)}/stages/${encodeURIComponent(requestedStage)}`);
    if (APP.stageKey !== requestedStage || APP.assetId !== assetId) return;
    APP.stageDetail = detail;
    const asset = APP.assets.find(item => item.asset_id === assetId) || APP.assets[0];
    updateStageDetail(asset);
  } catch (error) {
    const container = document.getElementById('stage-detail');
    if (container) container.innerHTML = `<section class="card stage-detail empty">${esc(error.message)}</section>`;
  }
}

async function resumeAsset(assetId) {
  const button = document.getElementById('resume');
  button.disabled = true; button.textContent = 'Resuming…';
  try {
    await api(`/api/tenants/${encodeURIComponent(APP.tenant)}/evaluation-assets/${encodeURIComponent(assetId)}/resume`, {method:'POST'});
    await selectTenant(APP.tenant);
  } catch (error) {
    button.disabled = false; button.textContent = error.message;
  }
}

function assetRevision(assets) {
  return JSON.stringify((assets || []).map(asset => ({
    asset_id: asset.asset_id,
    updated_at: asset.state?.updated_at,
    status: asset.state?.status,
    current_stage: asset.state?.current_stage,
    directories: asset.directories
  })));
}

function captureViewScroll() {
  const example = document.querySelector('.example-panel pre');
  return {
    pageTop: window.scrollY,
    pageLeft: window.scrollX,
    exampleTop: example?.scrollTop || 0,
    exampleLeft: example?.scrollLeft || 0
  };
}

function restoreViewScroll(position) {
  const restore = () => {
    window.scrollTo(position.pageLeft, position.pageTop);
    const example = document.querySelector('.example-panel pre');
    if (example) {
      example.scrollTop = position.exampleTop;
      example.scrollLeft = position.exampleLeft;
    }
  };
  restore();
  window.requestAnimationFrame(restore);
}

async function refresh() {
  if (!APP.tenant || APP.busy || document.hidden || ['INPUT','SELECT'].includes(document.activeElement?.tagName)) return;
  APP.busy = true;
  try {
    const nextAssets = await api(`/api/tenants/${encodeURIComponent(APP.tenant)}/evaluation-assets`);
    if (assetRevision(nextAssets) === assetRevision(APP.assets)) return;
    const scrollPosition = captureViewScroll();
    APP.assets = nextAssets;
    renderTenant();
    const asset = APP.assets.find(item => item.asset_id === APP.assetId) || APP.assets[0];
    if (asset) await loadStage(asset.asset_id);
    restoreViewScroll(scrollPosition);
  }
  finally { APP.busy = false; }
}

async function boot() {
  APP.tenants = await api('/api/tenants');
  document.getElementById('new-button').onclick = renderCreate;
  const tenant = new URLSearchParams(location.search).get('tenant');
  if (tenant) await selectTenant(tenant); else renderCreate();
  APP.timer = setInterval(refresh, 5000);
}
boot().catch(error => {
  document.getElementById('main').innerHTML = `<section class="card empty">${esc(error.message)}</section>`;
});
</script>
</body>
</html>
"""
