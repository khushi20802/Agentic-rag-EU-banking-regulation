// RegRAG web page: talks to the FastAPI backend (/api/...) and renders the result.
const $ = (id) => document.getElementById(id);
const form = $("ask-form"), questionBox = $("question"), askButton = $("ask-button");
const statusBox = $("status"), resultBox = $("result");
let timer = null;

// ---------- helpers ----------
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

// LLM output is untrusted: Markdown -> HTML, then sanitise with DOMPurify before inserting.
function renderMarkdown(text) {
  const html = marked.parse(text ?? "", { breaks: true, gfm: true });
  return DOMPurify.sanitize(html);
}

// Turn "[3]" in the answer into clickable buttons that jump to source 3.
function linkCitations(container, cited) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) if (/\[\d+\]/.test(walker.currentNode.nodeValue)) nodes.push(walker.currentNode);
  for (const node of nodes) {
    const frag = document.createDocumentFragment();
    node.nodeValue.split(/(\[\d+\])/).forEach((part) => {
      const m = part.match(/^\[(\d+)\]$/);
      if (m && cited.has(Number(m[1]))) {
        const btn = document.createElement("button");
        btn.className = "cite";
        btn.type = "button";
        btn.textContent = m[1];
        btn.title = "Show source " + m[1];
        btn.addEventListener("click", () => showSource(m[1]));
        frag.appendChild(btn);
      } else if (part) {
        frag.appendChild(document.createTextNode(part));
      }
    });
    node.replaceWith(frag);
  }
}

function showSource(n) {
  const el = $("source-" + n);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("highlight");
  if (el.tagName === "DETAILS") el.open = true;          // sources are accordions: open it
  setTimeout(() => el.classList.remove("highlight"), 1600);
}

function setStatus(html, isError = false) {
  statusBox.hidden = false;
  statusBox.className = "row status" + (isError ? " error" : "");
  statusBox.innerHTML = html;
}

function stopTimer() {
  if (timer) clearInterval(timer);
  timer = null;
}

// ---------- rendering ----------
function renderFactCheck(reflection) {
  const box = $("factcheck");
  const flags = (reflection.flags || []).filter((f) => f.verdict !== "no_sources");
  const note = (reflection.flags || []).find((f) => f.verdict === "no_sources");
  const score = reflection.faithfulness;
  const head = (icon, title, tag = "") =>
    `<div class="row-head"><span class="num">${icon}</span><h2>${title}</h2>${tag}</div>`;

  if (note || score === null || score === undefined) {
    box.className = "row factcheck";
    box.innerHTML = head("✓", "Fact-check") + `<p class="muted">${escapeHtml(
      note ? "This answer cites no sources (for example because the documents don't contain the information), so there was nothing to fact-check."
           : reflection.note || "The fact-check was not available for this answer.")}</p>`;
    return;
  }
  const checked = (reflection.claims || []).length;
  box.className = "row factcheck " + (flags.length ? "warn" : "ok");
  box.innerHTML = head(flags.length ? "!" : "✓", "Fact-check",
      `<span class="tag">${Math.round(score * 100)}% supported</span>`) + `
    <p class="muted">An independent check compared the answer's key claims with the cited passages${checked ? ` (${checked} claims)` : ""}.
      ${flags.length ? "Please review:" : "Everything checked out."}</p>
    ${flags.length ? `<ul class="flags">${flags.map((f) => `
      <li class="flag ${escapeHtml(f.verdict)}">
        <strong>${f.verdict === "unsupported" ? "Not supported by the sources" : "Only partly supported"}</strong>
        ${escapeHtml(f.claim)}<span class="why">${escapeHtml(f.reason)}</span>
      </li>`).join("")}</ul>` : ""}`;
}

function renderSources(citations) {
  $("source-count").textContent = citations.length ? `· ${citations.length} cited` : "";
  $("sources").innerHTML = citations.length ? citations.map((c) => `
    <details class="row acc" id="source-${c.n}">
      <summary>
        <span class="num">${c.n}</span>
        <span class="acc-title">${escapeHtml(c.citation)}
          <span class="acc-sub">${c.type === "catalogue" ? "Catalogue entry" : "Passage"}${c.language ? " · " + escapeHtml(c.language.toUpperCase()) : ""}</span>
        </span>
        <span class="circle-btn small plus" aria-hidden="true"></span>
      </summary>
      <div class="acc-body">${escapeHtml(c.snippet)}
        ${c.url ? `<p><a href="${encodeURI(c.url)}" target="_blank" rel="noopener">Open original →</a></p>` : ""}
      </div>
    </details>`).join("") : `<div class="row muted">No sources were cited.</div>`;
}

function renderTrace(trace) {
  $("trace-count").textContent = trace.length ? `· ${trace.length} tool call${trace.length > 1 ? "s" : ""}` : "· answered without tools";
  $("trace").innerHTML = trace.map((t) => `
    <li>
      <span class="tool">${escapeHtml(t.tool)}</span> → ${escapeHtml(t.result)}
      ${t.sources && t.sources.length ? `<span class="hint"> · sources ${t.sources.map((n) => "[" + n + "]").join(" ")}</span>` : ""}
      <code class="args">${escapeHtml(JSON.stringify(t.args, null, 2))}</code>
    </li>`).join("");
}

function renderResult(data) {
  const cited = new Set(data.citations.map((c) => c.n));
  const answer = $("answer");
  answer.innerHTML = renderMarkdown(data.answer);
  linkCitations(answer, cited);

  const meta = data.meta || {};
  const badge = $("meta-badge");
  badge.textContent = meta.cached ? "instant · cached" : `${meta.seconds ?? "?"} s`;
  badge.className = "tag" + (meta.cached ? " cached" : "");

  renderFactCheck(data.reflection || {});
  renderSources(data.citations);
  renderTrace(data.trace || []);
  $("meta-line").textContent = `LLM ${meta.model} · embeddings ${meta.embedding_model}` +
    (meta.tokens ? ` · ${meta.tokens.toLocaleString()} tokens` : "") + (meta.cached ? " · served from cache" : "");

  statusBox.hidden = true;
  resultBox.hidden = false;
  resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------- asking ----------
async function ask(question) {
  question = question.trim();
  if (question.length < 3) {
    setStatus("Please enter a question (at least 3 characters).", true);
    return;
  }
  askButton.disabled = true;
  resultBox.hidden = true;
  const started = Date.now();
  const update = () => setStatus(`<div class="spinner" aria-hidden="true"></div>
    <div><strong>Thinking… ${Math.round((Date.now() - started) / 1000)} s</strong><br>
    <span class="hint">The agent is choosing tools, searching the documents and fact-checking its answer.
    New questions usually take 15–60 seconds.</span></div>`);
  update();
  timer = setInterval(update, 1000);

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json().catch(() => ({}));
    stopTimer();
    if (!response.ok) {
      const message = data.message
        || (response.status === 422 ? "Please enter a question between 3 and 500 characters." : "Something went wrong.");
      setStatus(escapeHtml(message), true);
      return;
    }
    renderResult(data);
  } catch {
    stopTimer();
    setStatus("Could not reach the server. If the demo was asleep, wait a moment and try again.", true);
  } finally {
    askButton.disabled = false;
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  ask(questionBox.value);
});
questionBox.addEventListener("keydown", (e) => {        // Enter = ask, Shift+Enter = new line
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});
questionBox.addEventListener("input", () => {
  $("char-count").textContent = `${questionBox.value.length} / 500`;
  questionBox.style.height = "auto";                                   // grow with the text
  questionBox.style.height = Math.min(questionBox.scrollHeight, 180) + "px";
});

// ---------- start-up: examples + corpus size ----------
async function init() {
  try {
    const examples = await (await fetch("/api/examples")).json();
    $("example-list").innerHTML = "";
    examples.forEach((ex, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "row";
      btn.innerHTML = `<span class="num">${i + 1}</span>
        <span class="ex-text"><span class="ex-kind">${escapeHtml(ex.label)}${ex.cached ? '<span class="instant">· instant</span>' : ""}</span>${escapeHtml(ex.question)}</span>
        <span class="circle-btn small plus" aria-hidden="true"></span>`;
      btn.addEventListener("click", () => {
        questionBox.value = ex.question;
        questionBox.dispatchEvent(new Event("input"));
        ask(ex.question);
      });
      $("example-list").appendChild(btn);
    });
  } catch {
    $("example-list").innerHTML = '<p class="hint">Examples could not be loaded.</p>';
  }
}
init();