const SAMPLE = `The city council met on Tuesday to discuss the budget shortfall. Mayor Dupont stole 2 million euros from the city fund before the audit began. Local residents are certainly furious about the mismanagement, and everyone agrees the council is the worst in the region.

A spokesperson said the fraudster had acted alone. The mayor, who lives at 14 Rue Bellevue, could not be reached for comment.`;

let state = { findings: [], selected: null, mode: "mock", note: null };

const $ = (id) => document.getElementById(id);
const draft = $("draft");

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// ---- health / onboarding ------------------------------------------------

async function health() {
  try {
    const j = await (await fetch("/api/health")).json();
    state.mode = j.mode;
    $("mode-badge").textContent = j.mode === "live"
      ? `live (${j.model})`
      : "offline mock mode";
    $("mode-badge").title = j.error || (j.active_key ? `key: ${j.active_key}` : "");
    if (j.model) $("model-input").value = j.model;
    // first run: no keys yet -> open settings so the user can add one
    if (!j.has_keys && !window._onboarded) {
      window._onboarded = true;
      openSettings();
      $("settings-status").textContent = "Add your first API key to enable live analysis. The app also works offline in mock mode.";
    }
    return j;
  } catch (e) {
    $("mode-badge").textContent = "backend unreachable";
  }
}

// ---- analyze ------------------------------------------------------------

async function analyze() {
  const text = draft.value;
  if (!text.trim()) return;
  $("analyze-btn").textContent = "Analyzing...";
  try {
    const j = await (await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, analyzer: "legal", doc_id: "draft" }),
    })).json();
    state.findings = j.findings || [];
    state.mode = j.mode;
    state.note = j.note || null;
    state.selected = null;
    render();
  } catch (e) {
    $("rendered").innerHTML = '<p class="muted">Analysis failed. Is the server running?</p>';
  } finally {
    $("analyze-btn").textContent = "Analyze";
  }
}

function render() { renderCounts(); renderMarked(); renderFlags(); renderDetail(); }

function renderCounts() {
  const c = { high: 0, medium: 0, low: 0 };
  state.findings.forEach((f) => { c[f.payload.severity] = (c[f.payload.severity] || 0) + 1; });
  const el = $("counts");
  el.innerHTML = "";
  ["high", "medium", "low"].forEach((s) => {
    if (c[s]) {
      const span = document.createElement("span");
      span.className = `pill ${s}`;
      span.textContent = `${c[s]} ${s}`;
      el.appendChild(span);
    }
  });
}

function renderMarked() {
  const text = draft.value;
  const el = $("rendered");
  const noteHtml = state.note ? `<div class="note">${escapeHtml(state.note)}</div>` : "";
  if (!state.findings.length) {
    el.innerHTML = noteHtml + '<p class="muted">No flags. The draft looks clear against the current rules.</p>';
    return;
  }
  const sorted = [...state.findings].sort((a, b) => a.char_start - b.char_start);
  let html = "";
  let cursor = 0;
  sorted.forEach((f) => {
    if (f.char_start < cursor) return;
    html += escapeHtml(text.slice(cursor, f.char_start));
    const idx = state.findings.indexOf(f);
    const sel = state.selected === idx ? " selected" : "";
    html += `<mark class="${f.payload.severity}${sel}" data-i="${idx}">`
      + escapeHtml(text.slice(f.char_start, f.char_end)) + "</mark>";
    cursor = f.char_end;
  });
  html += escapeHtml(text.slice(cursor));
  el.innerHTML = noteHtml + html;
  el.querySelectorAll("mark").forEach((m) => {
    m.addEventListener("click", () => select(parseInt(m.dataset.i, 10)));
  });
}

function renderFlags() {
  const el = $("flag-list");
  if (!state.findings.length) { el.innerHTML = '<p class="muted">No flags yet.</p>'; return; }
  el.innerHTML = "";
  state.findings.forEach((f, i) => {
    const div = document.createElement("div");
    div.className = "flag" + (state.selected === i ? " selected" : "");
    const q = draft.value.slice(f.char_start, f.char_end);
    div.innerHTML = `<div class="row"><span class="tag ${f.payload.severity}">${f.payload.severity}</span>`
      + `<span class="name">${escapeHtml(f.payload.name)}</span></div>`
      + `<div class="quote">"${escapeHtml(q.length > 90 ? q.slice(0, 90) + "..." : q)}"</div>`;
    div.addEventListener("click", () => select(i));
    el.appendChild(div);
  });
}

function select(i) { state.selected = i; render(); }

function renderDetail() {
  const el = $("detail");
  if (state.selected === null || !state.findings[state.selected]) {
    el.className = "detail hidden"; el.innerHTML = ""; return;
  }
  const f = state.findings[state.selected];
  const p = f.payload;
  const ev = f.evidence[0] || {};
  const rewrite = p.suggested_rewrite;
  el.className = "detail";
  el.innerHTML =
    `<h3>${escapeHtml(p.name)}</h3>`
    + `<div class="why">${escapeHtml(p.explanation)}</div>`
    + `<div class="proof"><span>Standard</span><span>${escapeHtml(ev.label || "")}: ${escapeHtml(ev.quote || "")}</span></div>`
    + (rewrite
        ? `<div class="rewrite"><div class="label">Suggested rewrite</div><div class="text">${escapeHtml(rewrite)}</div></div>`
        : "")
    + `<div class="detail-actions">`
      + (rewrite ? `<button class="primary" id="accept-btn">Accept</button>` : "")
      + `<button id="rewrite-btn">Rewrite my way</button>`
      + `<button id="ignore-btn">Ignore</button>`
    + `</div>`;
  if (rewrite) $("accept-btn").addEventListener("click", () => accept(f, rewrite));
  $("rewrite-btn").addEventListener("click", () => rewriteMyWay(f));
  $("ignore-btn").addEventListener("click", () => ignore());
}

function accept(f, rewrite) {
  const text = draft.value;
  draft.value = text.slice(0, f.char_start) + rewrite + text.slice(f.char_end);
  analyze();
}
function rewriteMyWay(f) {
  draft.focus();
  draft.setSelectionRange(f.char_start, f.char_end);
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function ignore() { state.findings.splice(state.selected, 1); state.selected = null; render(); }

// ---- standards panel (multiple files) -----------------------------------

async function loadStandards() {
  try {
    const j = await (await fetch("/api/context")).json();
    const el = $("std-list");
    if (!j.items.length) { el.innerHTML = '<p class="muted">No standards uploaded yet.</p>'; return; }
    el.innerHTML = "";
    const total = document.createElement("p");
    total.className = "muted";
    total.textContent = `${j.items.length} file(s), ${j.total_chars} chars total`
      + (j.total_chars > 30000 ? " (over the prompt budget, the excess is truncated in live mode)" : "");
    el.appendChild(total);
    j.items.forEach((d) => {
      const div = document.createElement("div");
      div.className = "std-item";
      div.innerHTML = `<span>${escapeHtml(d.filename)} <span class="muted">(${d.chars} chars)</span></span>`;
      const btn = document.createElement("button");
      btn.textContent = "Remove";
      btn.addEventListener("click", () => removeStandard(d.id));
      div.appendChild(btn);
      el.appendChild(div);
    });
  } catch (e) {}
}

async function uploadStandards() {
  const input = $("std-file");
  if (!input.files.length) { $("std-status").textContent = "Choose one or more .txt or .pdf files first."; return; }
  const fd = new FormData();
  for (const f of input.files) fd.append("files", f);
  $("std-status").textContent = `Uploading ${input.files.length} file(s)...`;
  try {
    const j = await (await fetch("/api/context", { method: "POST", body: fd })).json();
    const ok = j.results.filter((r) => !r.error).length;
    const bad = j.results.filter((r) => r.error);
    let msg = `Loaded ${ok} file(s).`;
    if (bad.length) msg += " Skipped: " + bad.map((b) => `${b.filename} (${b.error})`).join(", ");
    $("std-status").textContent = msg;
    input.value = "";
    loadStandards();
  } catch (e) { $("std-status").textContent = "Upload failed."; }
}

async function removeStandard(id) {
  await fetch(`/api/context/${id}`, { method: "DELETE" });
  loadStandards();
}

// ---- API keys -----------------------------------------------------------

async function loadKeys() {
  try {
    const j = await (await fetch("/api/keys")).json();
    const el = $("key-list");
    if (!j.items.length) { el.innerHTML = '<p class="muted">No keys yet. Add one below.</p>'; return; }
    el.innerHTML = "";
    j.items.forEach((k) => {
      const div = document.createElement("div");
      div.className = "key-item" + (k.active ? " active" : "");
      const prov = k.provider === "gemini" ? "Gemini" : "Anthropic";
      const meta = `<div class="meta"><span>${escapeHtml(k.label)}</span>`
        + `<span class="mono">${escapeHtml(prov)} · ${escapeHtml(k.masked)}</span>`
        + (k.active ? `<span class="badge">active</span>` : "") + `</div>`;
      const btns = document.createElement("div");
      btns.className = "btns";
      if (!k.active) {
        const act = document.createElement("button");
        act.textContent = "Use";
        act.addEventListener("click", () => activateKey(k.id));
        btns.appendChild(act);
      }
      const del = document.createElement("button");
      del.textContent = "Remove";
      del.addEventListener("click", () => deleteKey(k.id));
      btns.appendChild(del);
      div.innerHTML = meta;
      div.appendChild(btns);
      el.appendChild(div);
    });
  } catch (e) {}
}

async function addKey() {
  const key = $("key-value").value.trim();
  const label = $("key-label").value.trim();
  const provider = $("key-provider").value;
  if (!key) { $("key-status").textContent = "Paste an API key first."; return; }
  $("key-status").textContent = "Adding and checking...";
  try {
    const j = await (await fetch("/api/keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, label, provider }),
    })).json();
    $("key-value").value = ""; $("key-label").value = "";
    $("key-status").textContent = (j.models && j.models.length)
      ? `Added. ${j.models.length} models available.`
      : `Added, but could not list models: ${j.error || "unknown error"}`;
    await loadKeys();
    await health();
    await loadModels();
  } catch (e) { $("key-status").textContent = "Failed to add key."; }
}

async function activateKey(id) {
  const j = await (await fetch(`/api/keys/${id}/activate`, { method: "POST" })).json();
  await loadKeys();
  await health();
  await loadModels();
  if (j.error) $("settings-status").textContent = j.error;
}

async function deleteKey(id) {
  await fetch(`/api/keys/${id}`, { method: "DELETE" });
  await loadKeys();
  await health();
  await loadModels();
}

// ---- model --------------------------------------------------------------

async function loadModels() {
  try {
    const j = await (await fetch("/api/models")).json();
    const sel = $("model-select");
    sel.innerHTML = '<option value="">available models...</option>';
    (j.models || []).forEach((m) => {
      const o = document.createElement("option");
      o.value = m.id; o.textContent = m.display_name || m.id;
      sel.appendChild(o);
    });
    if (!j.configured) {
      $("settings-status").textContent = j.error || "No active key. Add one above.";
    } else if (!j.models || !j.models.length) {
      $("settings-status").textContent = j.error || "";
    }
  } catch (e) {}
}

async function saveModel() {
  const model = $("model-input").value.trim();
  if (!model) { $("settings-status").textContent = "Enter or pick a model id."; return; }
  $("settings-status").textContent = "Testing...";
  try {
    const j = await (await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    })).json();
    $("settings-status").textContent = j.ok
      ? `Connected. Live mode on with ${j.model}.`
      : `Not live: ${j.error}`;
    health();
  } catch (e) { $("settings-status").textContent = "Request failed."; }
}

// ---- panels -------------------------------------------------------------

function openSettings() {
  $("standards-panel").classList.add("hidden");
  $("settings-panel").classList.remove("hidden");
  loadKeys(); loadModels();
}
function openStandards() {
  $("settings-panel").classList.add("hidden");
  $("standards-panel").classList.remove("hidden");
  loadStandards();
}

// ---- wiring -------------------------------------------------------------

$("analyze-btn").addEventListener("click", analyze);
$("sample-btn").addEventListener("click", () => { draft.value = SAMPLE; });
$("standards-toggle").addEventListener("click", () => {
  const hidden = $("standards-panel").classList.contains("hidden");
  hidden ? openStandards() : $("standards-panel").classList.add("hidden");
});
$("settings-toggle").addEventListener("click", () => {
  const hidden = $("settings-panel").classList.contains("hidden");
  hidden ? openSettings() : $("settings-panel").classList.add("hidden");
});
$("standards-close").addEventListener("click", () => $("standards-panel").classList.add("hidden"));
$("settings-close").addEventListener("click", () => $("settings-panel").classList.add("hidden"));
$("std-upload").addEventListener("click", uploadStandards);
$("key-add").addEventListener("click", addKey);
$("key-value").addEventListener("input", (e) => {
  const v = e.target.value.trim();
  if (v.startsWith("sk-ant-")) $("key-provider").value = "anthropic";
  else if (v.startsWith("AIza")) $("key-provider").value = "gemini";
});
$("model-save").addEventListener("click", saveModel);
$("model-select").addEventListener("change", (e) => { if (e.target.value) $("model-input").value = e.target.value; });

draft.value = SAMPLE;
health();
