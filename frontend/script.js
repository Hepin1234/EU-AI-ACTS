const CATEGORY_LABELS = {
  prohibited: "Prohibited",
  high_risk: "High Risk",
  limited_risk: "Limited Risk",
  minimal_risk: "Minimal Risk",
};

const REMEMBER_KEY_STORAGE = {
  anthropic: "ai-checker-api-key-anthropic",
  openai: "ai-checker-api-key-openai",
};

const form = document.getElementById("analyze-form");
const urlInput = document.getElementById("url");
const modeSelect = document.getElementById("analysis-mode");
const submitBtn = document.getElementById("submit-btn");

const PROVIDER_FIELDS = {
  anthropic: {
    details: document.getElementById("anthropic-key-details"),
    keyInput: document.getElementById("anthropic-api-key"),
    rememberCheckbox: document.getElementById("anthropic-remember-key"),
  },
  openai: {
    details: document.getElementById("openai-key-details"),
    keyInput: document.getElementById("openai-api-key"),
    rememberCheckbox: document.getElementById("openai-remember-key"),
  },
};
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");

const categoryBadge = document.getElementById("category-badge");
const confidenceBadge = document.getElementById("confidence-badge");
const explanationEl = document.getElementById("explanation");
const caveatsBlock = document.getElementById("caveats-block");
const caveatsList = document.getElementById("caveats-list");
const citationsBlock = document.getElementById("citations-block");
const citationsList = document.getElementById("citations-list");
const resultMeta = document.getElementById("result-meta");
const disclaimerText = document.getElementById("disclaimer-text");

function restoreRememberedKeys() {
  for (const [provider, fields] of Object.entries(PROVIDER_FIELDS)) {
    const saved = sessionStorage.getItem(REMEMBER_KEY_STORAGE[provider]);
    if (saved) {
      fields.keyInput.value = saved;
      fields.rememberCheckbox.checked = true;
      fields.details.open = true;
    }
  }
}

function syncRememberedKeys() {
  for (const [provider, fields] of Object.entries(PROVIDER_FIELDS)) {
    if (fields.rememberCheckbox.checked && fields.keyInput.value.trim()) {
      sessionStorage.setItem(REMEMBER_KEY_STORAGE[provider], fields.keyInput.value.trim());
    } else {
      sessionStorage.removeItem(REMEMBER_KEY_STORAGE[provider]);
    }
  }
}

function updateModeVisibility() {
  for (const [provider, fields] of Object.entries(PROVIDER_FIELDS)) {
    fields.details.hidden = modeSelect.value !== provider;
  }
}

function showStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = `status ${kind}`;
  statusEl.hidden = false;
}

function hideStatus() {
  statusEl.hidden = true;
}

function fillList(listEl, blockEl, items) {
  listEl.innerHTML = "";
  if (!items || items.length === 0) {
    blockEl.hidden = true;
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    listEl.appendChild(li);
  }
  blockEl.hidden = false;
}

function renderResult(data) {
  const c = data.classification;

  categoryBadge.textContent = CATEGORY_LABELS[c.category] || c.category;
  categoryBadge.className = `badge badge-${c.category}`;
  confidenceBadge.textContent = `${c.confidence} confidence`;
  explanationEl.textContent = c.explanation;

  fillList(caveatsList, caveatsBlock, c.caveats);
  fillList(citationsList, citationsBlock, c.cited_articles);

  resultMeta.textContent = `Analyzed ${data.pages_analyzed} page${data.pages_analyzed === 1 ? "" : "s"} of ${data.url}, discovered via ${data.source.replace(/_/g, " ")}.`;
  disclaimerText.textContent = data.disclaimer;

  resultEl.hidden = false;
}

function normalizeDetail(rawDetail) {
  if (typeof rawDetail === "string") return rawDetail;
  if (Array.isArray(rawDetail)) {
    // FastAPI's own request-validation errors (bad/missing fields) shape `detail` as a
    // list of {msg, loc, ...} objects rather than a string — flatten it into one.
    return rawDetail.map((e) => e.msg || JSON.stringify(e)).join("; ");
  }
  return null;
}

function errorMessageForStatus(status, rawDetail) {
  const detail = normalizeDetail(rawDetail);
  if (status === 400) return detail || "There's a problem with the request — check the URL and API key.";
  if (status === 422) return detail || "That request wasn't valid — check the URL you entered.";
  if (status === 424) return detail || "Couldn't read that site — it may block scrapers or have no reachable pages.";
  if (status === 429) return "Too many requests right now — wait a moment and try again.";
  if (status === 502) return detail || "The classifier couldn't produce a result — try again in a moment.";
  return detail || "Something went wrong. Please try again.";
}

modeSelect.addEventListener("change", updateModeVisibility);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideStatus();
  resultEl.hidden = true;
  syncRememberedKeys();

  const url = urlInput.value.trim();
  const mode = modeSelect.value;
  const apiKey = mode === "free" ? "" : PROVIDER_FIELDS[mode].keyInput.value.trim();
  if (!url) {
    showStatus("Enter a URL to analyze.", "error");
    return;
  }

  submitBtn.disabled = true;
  showStatus("Analyzing — reading the site and checking it against the EU AI Act. This can take up to 30 seconds.", "loading");

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, mode, api_key: apiKey || null }),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      showStatus(errorMessageForStatus(response.status, data.detail), "error");
      return;
    }

    hideStatus();
    renderResult(data);
  } catch (err) {
    showStatus("Couldn't reach the server. Check your connection and try again.", "error");
  } finally {
    submitBtn.disabled = false;
  }
});

restoreRememberedKeys();
updateModeVisibility();
