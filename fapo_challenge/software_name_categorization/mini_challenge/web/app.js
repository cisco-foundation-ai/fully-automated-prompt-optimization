/*
 * Copyright 2026 Cisco Systems, Inc. and its affiliates
 *
 * SPDX-License-Identifier: Apache-2.0
 */

const state = {
  labels: [],
  levels: [],
  currentLevel: "",
  training: [],
  miniTest: [],
  fapoReference: null,
};

const els = {
  prompt: document.querySelector("#prompt-input"),
  model: document.querySelector("#model-input"),
  run: document.querySelector("#run-button"),
  status: document.querySelector("#status-text"),
  levelTabs: document.querySelector("#level-tabs"),
  allowedLabels: document.querySelector("#allowed-labels"),
  verdictCard: document.querySelector("#verdict-card"),
  verdictKicker: document.querySelector("#verdict-kicker"),
  verdictTitle: document.querySelector("#verdict-title"),
  verdictQuote: document.querySelector("#verdict-quote"),
  verdictManualScore: document.querySelector("#verdict-manual-score"),
  verdictFapoScore: document.querySelector("#verdict-fapo-score"),
  manualScore: document.querySelector("#manual-score"),
  fapoScore: document.querySelector("#fapo-score"),
  fapoNote: document.querySelector("#fapo-note"),
  subsetCount: document.querySelector("#subset-count"),
  miniList: document.querySelector("#mini-test-list"),
  resultsBody: document.querySelector("#results-body"),
  resultSummary: document.querySelector("#result-summary"),
  search: document.querySelector("#search-input"),
  labelFilter: document.querySelector("#label-filter"),
  trainingBoard: document.querySelector("#training-board"),
};

const verdictCopy = {
  win: {
    kicker: "You won",
    title: "Manual prompt beats FAPO v006",
    quotes: [
      "That prompt walked in with a checklist and left with the trophy.",
      "Tiny test set, big main-character energy.",
      "FAPO just refreshed the page and pretended nothing happened.",
    ],
  },
  loss: {
    kicker: "You lost",
    title: "FAPO v006 holds the line",
    quotes: [
      "The prompt had coffee. FAPO had receipts.",
      "A noble attempt, but the scoreboard brought a red pen.",
      "FAPO kept its badge today. Your prompt made it check twice.",
    ],
  },
  tie: {
    kicker: "Tie",
    title: "Dead heat with FAPO v006",
    quotes: [
      "Two prompts enter, both ask for a recount.",
      "The scoreboard shrugged professionally.",
      "Nobody blinked. The metrics blinked first.",
    ],
  },
};

function pct(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function setStatus(message, kind = "") {
  els.status.textContent = message;
  els.status.className = kind;
}

function badge(text) {
  return `<span class="pill">${escapeHtml(text)}</span>`;
}

function resultBadge(text, isCorrect) {
  const stateClass = isCorrect ? "pill-ok" : "pill-miss";
  return `<span class="pill ${stateClass}">${escapeHtml(text)}</span>`;
}

function pickQuote(outcome) {
  const quotes = verdictCopy[outcome].quotes;
  return quotes[Math.floor(Math.random() * quotes.length)];
}

function hideVerdict() {
  els.verdictCard.hidden = true;
  els.verdictCard.className = "verdict-card";
  els.verdictKicker.textContent = "";
  els.verdictTitle.textContent = "";
  els.verdictQuote.textContent = "";
  els.verdictManualScore.textContent = "--";
  els.verdictFapoScore.textContent = "--";
}

function renderVerdict(result) {
  const manual = result.summary;
  const fapo = result.fapo_reference.summary;
  let outcome = "tie";
  if (manual.correct > fapo.correct) {
    outcome = "win";
  } else if (manual.correct < fapo.correct) {
    outcome = "loss";
  }

  const copy = verdictCopy[outcome];
  els.verdictCard.hidden = false;
  els.verdictCard.className = `verdict-card ${outcome}`;
  els.verdictKicker.textContent = copy.kicker;
  els.verdictTitle.textContent = copy.title;
  els.verdictQuote.textContent = `"${pickQuote(outcome)}"`;
  els.verdictManualScore.textContent = `${manual.correct}/${manual.total}`;
  els.verdictFapoScore.textContent = `${fapo.correct}/${fapo.total}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

async function loadInitialData() {
  const [config, training] = await Promise.all([
    fetchJson("/api/config"),
    fetchJson("/api/training"),
  ]);

  state.levels = config.levels;
  state.currentLevel = config.default_level;
  state.training = training;

  renderLevelTabs();
  await setLevel(state.currentLevel);
}

function currentLevelConfig() {
  return state.levels.find((level) => level.id === state.currentLevel);
}

async function setLevel(levelId) {
  state.currentLevel = levelId;
  const level = currentLevelConfig();
  state.labels = level.labels;
  state.fapoReference = level.fapo_reference;
  els.prompt.value = level.starter_prompt;

  const fapoSummary = state.fapoReference.summary;
  els.fapoScore.textContent = pct(fapoSummary.micro_f1_percent);
  els.fapoNote.textContent = state.fapoReference.source_note;
  els.subsetCount.textContent = `${level.test_count} cases · ${level.label_count} labels`;
  els.manualScore.textContent = "--";
  els.resultSummary.textContent = "";
  hideVerdict();
  els.resultsBody.innerHTML = `
    <tr>
      <td colspan="5" class="empty">Run the mini eval to populate results.</td>
    </tr>
  `;

  await loadMiniTest();
  renderLevelTabs();
  renderAllowedLabels();
  populateLabelFilter();
  renderMiniTest();
  renderTraining();
}

async function loadMiniTest() {
  state.miniTest = await fetchJson(`/api/mini-test?level=${encodeURIComponent(state.currentLevel)}`);
}

function renderLevelTabs() {
  els.levelTabs.innerHTML = state.levels
    .map(
      (level) => `
        <button
          class="level-tab${level.id === state.currentLevel ? " active" : ""}"
          type="button"
          role="tab"
          aria-selected="${level.id === state.currentLevel}"
          data-level="${escapeHtml(level.id)}"
        >
          ${escapeHtml(level.name)}
          <span>${level.label_count}</span>
        </button>
      `
    )
    .join("");
}

function renderAllowedLabels() {
  els.allowedLabels.innerHTML = state.labels
    .map((label) => `<span class="allowed-label">${escapeHtml(label)}</span>`)
    .join("");
}

function populateLabelFilter() {
  els.labelFilter.innerHTML = '<option value="">All labels</option>';
  for (const label of state.labels) {
    const option = document.createElement("option");
    option.value = label;
    option.textContent = label;
    els.labelFilter.appendChild(option);
  }
}

function renderMiniTest() {
  els.miniList.innerHTML = state.miniTest
    .map(
      (row) => `
        <div class="mini-item">
          <strong>${escapeHtml(row.software_name)}</strong>
          <span class="subtle">${escapeHtml(row.difficulty)}</span>
        </div>
      `
    )
    .join("");
}

function renderTraining() {
  const query = els.search.value.trim().toLowerCase();
  const label = els.labelFilter.value;
  const rows = state.training.filter((row) => {
    const matchesText = !query || row.software_name.toLowerCase().includes(query);
    const matchesLabel = !label || row.expected === label;
    return matchesText && matchesLabel;
  });
  const grouped = new Map(state.labels.map((category) => [category, []]));

  for (const row of rows) {
    if (!grouped.has(row.expected)) {
      grouped.set(row.expected, []);
    }
    grouped.get(row.expected).push(row);
  }

  const visibleLabels = label ? [label] : state.labels;
  els.trainingBoard.innerHTML = visibleLabels
    .map(
      (category) => {
        const categoryRows = grouped.get(category) || [];
        const chips = categoryRows
          .map((row) => {
            const signal = `${row.ambiguity_type} · ${row.difficulty}`;
            return `
              <span
                class="software-bubble"
                tabindex="0"
                title="${escapeHtml(signal)}"
                data-signal="${escapeHtml(signal)}"
              >
                ${escapeHtml(row.software_name)}
              </span>
            `;
          })
          .join("");

        return `
          <section class="category-bubble${categoryRows.length ? "" : " empty-category"}">
            <div class="category-header">
              <strong>${escapeHtml(category)}</strong>
              <span>${categoryRows.length}</span>
            </div>
            <div class="software-bubble-list">
              ${chips || '<span class="empty-category-text">No matches</span>'}
            </div>
          </section>
        `;
      }
    )
    .join("");
}

function renderResults(result) {
  const summary = result.summary;
  els.manualScore.textContent = pct(summary.micro_f1_percent);
  renderVerdict(result);
  els.resultSummary.textContent =
    `${summary.correct}/${summary.total} manual, ` +
    `${result.fapo_reference.summary.correct}/${result.fapo_reference.summary.total} FAPO v006`;

  els.resultsBody.innerHTML = result.cases
    .map((row) => {
      const manualClass = row.correct ? "ok" : "miss";
      const fapoClass = row.fapo_correct ? "ok" : "miss";
      const validText = row.valid_label ? "" : " invalid label";
      return `
        <tr>
          <td><strong>${escapeHtml(row.software_name)}</strong></td>
          <td>${badge(row.expected)}</td>
          <td>
            ${resultBadge(row.prediction || "(empty)", row.correct)}
            <div class="${manualClass}">${row.correct ? "correct" : `miss${validText}`}</div>
          </td>
          <td>
            ${resultBadge(row.fapo_prediction, row.fapo_correct)}
            <div class="${fapoClass}">${row.fapo_correct ? "correct" : "miss"}</div>
          </td>
          <td class="${manualClass}">
            ${row.correct === row.fapo_correct ? "tie" : row.correct ? "manual ahead" : "FAPO ahead"}
          </td>
        </tr>
      `;
    })
    .join("");
}

async function runEval() {
  els.run.disabled = true;
  hideVerdict();
  setStatus("Running...", "warn");
  try {
    const result = await fetchJson("/api/evaluate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        prompt: els.prompt.value,
        model: els.model.value || "gpt-4o-mini",
        level: state.currentLevel,
      }),
    });
    renderResults(result);
    setStatus("Complete", "ok");
  } catch (error) {
    setStatus(error.message, "miss");
  } finally {
    els.run.disabled = false;
  }
}

els.run.addEventListener("click", runEval);
els.levelTabs.addEventListener("click", (event) => {
  const button = event.target.closest("[data-level]");
  if (button && button.dataset.level !== state.currentLevel) {
    setLevel(button.dataset.level).catch((error) => {
      setStatus(error.message, "miss");
    });
  }
});
els.search.addEventListener("input", renderTraining);
els.labelFilter.addEventListener("change", renderTraining);

loadInitialData().catch((error) => {
  setStatus(error.message, "miss");
});
