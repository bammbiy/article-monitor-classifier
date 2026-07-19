"use strict";

/* ---------------------------------------------------------------------
   Article Judge AI — frontend logic.
   Talks to the FastAPI backend (see ../backend). No build step, no
   framework — this is a small local dev tool, plain DOM is enough.
   ------------------------------------------------------------------- */

const els = {
  linksInput: document.getElementById("links-input"),
  runBtn: document.getElementById("run-btn"),
  clearBtn: document.getElementById("clear-btn"),
  exportBtn: document.getElementById("export-btn"),
  intakeStatus: document.getElementById("intake-status"),
  criteriaTextarea: document.getElementById("criteria-textarea"),
  saveCriteriaBtn: document.getElementById("save-criteria-btn"),
  criteriaStatus: document.getElementById("criteria-status"),
  apiBaseInput: document.getElementById("api-base-input"),
  log: document.getElementById("log"),
  logEmpty: document.getElementById("log-empty"),
  ticketTemplate: document.getElementById("ticket-template"),
  tallyCollect: document.getElementById("tally-collect"),
  tallySkip: document.getElementById("tally-skip"),
  tallyError: document.getElementById("tally-error"),
};

const TYPE_LABEL = { article: "Article", youtube: "YouTube", social: "Social", unknown: "Link" };
const STAMP_LABEL = { COLLECT: "Collected", SKIP: "Skipped" };

let results = [];
let tally = { collect: 0, skip: 0, error: 0 };
let isRunning = false;

function apiBase() {
  return els.apiBaseInput.value.trim().replace(/\/$/, "");
}

/* ---------- persistence: remember the API base URL between visits ---------- */

(function restoreApiBase() {
  const saved = localStorage.getItem("article-judge:api-base");
  if (saved) els.apiBaseInput.value = saved;
})();

els.apiBaseInput.addEventListener("change", () => {
  localStorage.setItem("article-judge:api-base", els.apiBaseInput.value.trim());
});

/* ---------- criteria panel ---------- */

async function loadCriteria() {
  try {
    const res = await fetch(`${apiBase()}/api/criteria`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    els.criteriaTextarea.value = data.content;
  } catch (err) {
    els.criteriaStatus.textContent = `Couldn't load criteria (${err.message}). Is the backend running?`;
  }
}

els.saveCriteriaBtn.addEventListener("click", async () => {
  els.criteriaStatus.textContent = "Saving…";
  try {
    const res = await fetch(`${apiBase()}/api/criteria`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: els.criteriaTextarea.value }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    els.criteriaStatus.textContent = "Saved. Next run will use the updated rules.";
  } catch (err) {
    els.criteriaStatus.textContent = `Save failed (${err.message}).`;
  }
});

/* ---------- link parsing ---------- */

function parseLinks(raw) {
  const seen = new Set();
  const urls = [];
  for (const line of raw.split("\n")) {
    const u = line.trim();
    if (!u || u.startsWith("#")) continue;
    if (!seen.has(u)) {
      seen.add(u);
      urls.push(u);
    }
  }
  return urls;
}

/* ---------- tally + ticket rendering ---------- */

function resetLog() {
  results = [];
  tally = { collect: 0, skip: 0, error: 0 };
  renderTally();
  els.log.innerHTML = "";
  els.log.appendChild(els.logEmpty);
  els.logEmpty.style.display = "";
  els.exportBtn.disabled = true;
}

function renderTally() {
  els.tallyCollect.textContent = tally.collect;
  els.tallySkip.textContent = tally.skip;
  els.tallyError.textContent = tally.error;
}

function addTicket(result) {
  els.logEmpty.style.display = "none";

  const decision = result.decision === "COLLECT" || result.decision === "SKIP" ? result.decision : "ERROR";
  if (decision === "COLLECT") tally.collect += 1;
  else if (decision === "SKIP") tally.skip += 1;
  else tally.error += 1;
  renderTally();

  const node = els.ticketTemplate.content.cloneNode(true);
  const ticket = node.querySelector(".ticket");
  ticket.dataset.decision = decision;

  const stamp = node.querySelector(".stamp");
  stamp.textContent = decision === "ERROR" ? "Needs review" : STAMP_LABEL[decision];

  node.querySelector(".ticket__type-badge").textContent = TYPE_LABEL[result.source_type] || "Link";
  node.querySelector(".ticket__source").textContent = result.source || "";
  node.querySelector(".ticket__title").textContent = result.title || result.url;
  node.querySelector(".ticket__topic").textContent = result.topic || "";
  node.querySelector(".ticket__reason").textContent = result.reason || "";
  node.querySelector(".ticket__error").textContent = result.error || "";

  const link = node.querySelector(".ticket__link");
  link.href = result.url;

  els.log.appendChild(node);
  els.log.scrollTop = els.log.scrollHeight;

  results.push(result);
  els.exportBtn.disabled = results.length === 0;
}

/* ---------- run judgment (SSE over fetch, since EventSource can't POST) ---------- */

function setRunning(running) {
  isRunning = running;
  els.runBtn.disabled = running;
  els.runBtn.querySelector(".btn__label").textContent = running ? "Judging…" : "Run judgment";
}

async function runJudgment() {
  if (isRunning) return;

  const urls = parseLinks(els.linksInput.value);
  if (urls.length === 0) {
    els.intakeStatus.dataset.state = "error";
    els.intakeStatus.textContent = "Paste at least one link first.";
    return;
  }

  setRunning(true);
  els.intakeStatus.dataset.state = "";
  els.intakeStatus.textContent = `Sending ${urls.length} link(s)…`;

  let processed = 0;

  try {
    const res = await fetch(`${apiBase()}/api/judge/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls }),
    });

    if (!res.ok || !res.body) {
      throw new Error(`HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop(); // last chunk may be incomplete, keep it for next read

      for (const raw of events) {
        const line = raw.trim();
        if (!line.startsWith("data:")) continue;
        const payload = JSON.parse(line.slice(5).trim());

        if (payload.type === "result") {
          processed += 1;
          addTicket(payload.data);
          els.intakeStatus.textContent = `Processed ${processed}/${urls.length}…`;
        } else if (payload.type === "done") {
          els.intakeStatus.dataset.state = "ok";
          els.intakeStatus.textContent = `Done — ${processed}/${urls.length} processed.`;
        }
      }
    }
  } catch (err) {
    els.intakeStatus.dataset.state = "error";
    els.intakeStatus.textContent = `Couldn't reach the backend (${err.message}). Is it running at ${apiBase()}?`;
  } finally {
    setRunning(false);
  }
}

els.runBtn.addEventListener("click", runJudgment);
els.clearBtn.addEventListener("click", resetLog);

/* ---------- CSV export ---------- */

function toCsv(rows) {
  const headers = ["no", "decision", "source_type", "source", "title", "topic", "reason", "url", "error"];
  const escape = (val) => {
    const s = String(val ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [headers.join(",")];
  rows.forEach((row) => {
    lines.push(headers.map((h) => escape(row[h])).join(","));
  });
  return "\uFEFF" + lines.join("\n"); // BOM so Excel doesn't mangle non-ASCII text
}

els.exportBtn.addEventListener("click", () => {
  const csv = toCsv(results);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  a.href = url;
  a.download = `results_${stamp}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});

/* ---------- init ---------- */

loadCriteria();
