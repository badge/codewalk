// codewalk: the index's filters, hover cards, the code in context, a symbol
// palette, review, live reload, and the editor with its preview scrolled in step. No
// dependencies.

(() => {
  "use strict";

  let data = JSON.parse(document.getElementById("page-data").textContent || "{}");
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
  };
  // The reading view for this page's file: a walkthrough, or a spec
  const reading = () => (data.spec ? "spec" : "walk");
  const api = async (path, body) => {
    const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  };

  // ---- Theme -------------------------------------------------------------------------

  const theme = store.get("codewalk-theme");
  if (theme) document.documentElement.dataset.theme = theme;
  function toggleTheme() {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "light" : "dark";
    store.set("codewalk-theme", document.documentElement.dataset.theme);
  }

  // ---- Toast -------------------------------------------------------------------------

  function toast(text) {
    $$(".toast").forEach((t) => t.remove());
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = text;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 1900);
  }
  async function copy(text, what = "Copied") {
    try { await navigator.clipboard.writeText(text); toast(`${what}: ${text}`); }
    catch { toast("Couldn't copy"); }
  }

  // ---- Hover cards ---------------------------------------------------------------------

  let card = null;
  function hideCard() { card?.remove(); card = null; }
  function showCard(el, html) {
    hideCard();
    card = document.createElement("div");
    card.className = "hovercard";
    card.innerHTML = html;
    document.body.appendChild(card);
    const r = el.getBoundingClientRect();
    const cw = card.offsetWidth, ch = card.offsetHeight;
    let left = Math.min(r.left, innerWidth - cw - 12);
    let top = r.bottom + 8;
    if (top + ch > innerHeight - 8) top = r.top - ch - 8;
    card.style.left = `${Math.max(8, left)}px`;
    card.style.top = `${Math.max(56, top)}px`;
  }
  function symbolCard(s) {
    const reqs = (s.markers || []).map(([k, id]) => `<span>${esc(k)} ${esc(id)}</span>`).join("");
    return `<div class="hc-top"><span class="kind k-${esc(s.kind)}">${esc(s.kind)}</span><span class="hc-q">${esc(s.qualified)}</span></div>
      <div class="hc-sig">${esc(s.signature)}</div>
      ${s.doc ? `<div class="hc-doc">${esc(s.doc)}</div>` : ""}
      ${s.details ? `<pre class="hc-details">${esc(s.details)}</pre>` : ""}
      ${reqs ? `<div class="hc-reqs">${reqs}</div>` : ""}
      <div class="hc-where">${esc(s.file)}:${s.line} · click to see it in its file</div>`;
  }
  function termCard(d) {
    const status = d.status ? `<span class="status s-${esc(d.status)}">${esc(d.status)}</span>` : "";
    return `<div class="hc-top"><span class="kind k-${esc(d.kind)}">${esc(d.kind)}</span><span class="hc-q">${esc(d.kind === "term" ? d.id.replaceAll("-", " ") : d.id)}</span>${status}</div>
      <div class="hc-doc">${esc(d.text)}</div><div class="hc-where">${esc(d.file)}:${d.line} · click for where it's defined</div>`;
  }
  function reqCard(r) {
    const traces = (r.traces || []).map((t) => `<span class="t-${esc(t.kind)}">${esc(t.kind)} ${esc(t.name)}</span>`).join("");
    return `<div class="hc-top"><span class="kind k-req">req</span><span class="hc-q">${esc(r.id)}</span></div>
      <div class="hc-doc">${esc(r.text)}</div>
      ${traces ? `<div class="hc-reqs hc-traces">${traces}</div>` : ""}
      <div class="hc-where">${esc(r.file)}:${r.line}</div>`;
  }
  document.addEventListener("mouseover", (e) => {
    const sym = e.target.closest("a.sym");
    const req = e.target.closest("a.req");
    if (sym && data.symbols?.[sym.dataset.ref]) return showCard(sym, symbolCard(data.symbols[sym.dataset.ref]));
    const term = e.target.closest("[data-term]");
    if (term && data.terms?.[term.dataset.term]) return showCard(term, termCard(data.terms[term.dataset.term]));
    if (req && data.requirements?.[req.dataset.req]) return showCard(req, reqCard(data.requirements[req.dataset.req]));
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.closest("a.sym, a.req, [data-term]")) hideCard();
  });

  // ---- The code in context ----------------------------------------------------------------

  const panel = $("#context");
  let panelFile = null;
  // Pygments' classes for names: plain, functions, classes, namespaces, others, decorators
  const NAME = /^(n|nf|nc|nn|nx|nd|ne|fm)$/;

  // r[impl ui.context]
  async function openContext({ file, start, end, line, focusRef }) {
    if (!panel) return;
    hideCard();
    const view = await api(`/api/file?path=${encodeURIComponent(file)}`);
    panelFile = view;
    panel.hidden = false;
    panel.parentElement.classList.add("with-context");
    const rows = view.lines
      .map((l, i) => `<span class="row" data-line="${i + 1}"><span class="ln">${i + 1}</span><span class="lc">${l || " "}</span></span>`)
      .join("");
    panel.classList.toggle("no-outline", store.get("codewalk-outline") === "off");
    panel.innerHTML = `
      <div class="ctx-head">
        <span class="ctx-file" title="${esc(file)}">${esc(file)}</span>
        <span class="spacer"></span>
        <button class="act" data-action="toggle-outline" title="Show or hide this file's outline (o)">Outline</button>
        <a class="act" href="${esc(view.zed)}:${line || 1}" title="Open in Zed">Zed</a>
        <button class="ctx-close" data-action="close-context" title="Close (Esc)">×</button>
      </div>
      <div class="ctx-body">
      <div class="ctx-code"><pre class="code"><code>${rows}</code></pre></div>
      <div class="ctx-outline"><input placeholder="Filter symbols…" data-role="outline-filter">
        ${view.outline
          .map((o) => `<div class="oi" data-start="${o.start}" data-end="${o.end}" data-line="${o.line}" data-ref="${esc(o.ref)}" style="padding-left:${12 + Math.max(0, o.depth - (view.outline[0]?.depth || 0)) * 10}px" title="${esc(o.qualified)} · click to show, ⌥-click to copy its reference">
              <span class="kind k-${esc(o.kind)}">${esc(o.kind)}</span><span class="on">${esc(o.qualified.split("::").slice(-1)[0])}</span><span class="ol">${o.line}</span></div>`)
          .join("")}
      </div>
      </div>`;
    highlightRange(start, end, line);
  }
  function highlightRange(start, end, line) {
    if (!panel || panel.hidden) return;
    $$(".row.hl", panel).forEach((r) => r.classList.remove("hl"));
    $$(".oi.current", panel).forEach((o) => o.classList.remove("current"));
    if (!start) return;
    for (let n = start; n <= (end || start); n++) $(`.row[data-line="${n}"]`, panel)?.classList.add("hl");
    $(`.oi[data-start="${start}"]`, panel)?.classList.add("current");
    // The symbol's first line (its docs and markers) a couple of lines from the top
    const target = $(`.row[data-line="${Math.max(1, start - 2)}"]`, panel);
    const box = $(".ctx-code", panel);
    if (target && box) {
      const top = target.getBoundingClientRect().top - box.getBoundingClientRect().top + box.scrollTop;
      // Smooth for a short way; a long way, at once
      box.scrollTo({ top, behavior: Math.abs(top - box.scrollTop) < 1500 ? "smooth" : "auto" });
    }
    const item = $(".oi.current", panel);
    const list = $(".ctx-outline", panel);
    if (item && list) {
      const r = item.getBoundingClientRect(), l = list.getBoundingClientRect();
      if (r.top < l.top + 40 || r.bottom > l.bottom) list.scrollTo({ top: r.top - l.top + list.scrollTop - l.height / 3, behavior: "smooth" });
    }
  }
  function toggleOutline() {
    if (!panel) return;
    const off = !panel.classList.contains("no-outline");
    panel.classList.toggle("no-outline", off);
    store.set("codewalk-outline", off ? "off" : "on");
  }
  function closeContext() {
    if (!panel) return;
    panel.hidden = true;
    panel.parentElement.classList.remove("with-context");
  }
  function contextFor(ref) {
    const s = data.symbols?.[ref];
    if (s) openContext({ file: s.file, start: s.start, end: s.end, line: s.line });
  }

  // ---- Palette ---------------------------------------------------------------------------

  function palette() {
    const back = document.createElement("div");
    back.className = "palette-back";
    back.innerHTML = `<div class="palette"><input placeholder="Find a symbol: a name, or part of a path" spellcheck="false"><ul></ul>
      <div class="ph">↵ show it in its file · ⇧↵ copy its reference · esc close</div></div>`;
    document.body.appendChild(back);
    const input = $("input", back), list = $("ul", back);
    let items = [], sel = 0, timer;
    const draw = () => {
      list.innerHTML = items.map((s, i) => `<li class="${i === sel ? "sel" : ""}" data-i="${i}"><span class="kind k-${esc(s.kind)}">${esc(s.kind)}</span><span class="pr">${esc(s.ref)}</span><span class="pw">${esc(s.file)}:${s.line}</span></li>`).join("");
      $("li.sel", list)?.scrollIntoView({ block: "nearest" });
    };
    const pick = (i, copyIt) => {
      const s = items[i];
      if (!s) return;
      back.remove();
      if (copyIt) copy(s.ref, "Reference copied");
      else openContext({ file: s.file, start: s.start, end: s.end, line: s.line });
    };
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(async () => { items = input.value.trim() ? await api(`/api/symbols?q=${encodeURIComponent(input.value.trim())}`) : []; sel = 0; draw(); }, 90);
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); draw(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); draw(); e.preventDefault(); }
      else if (e.key === "Enter") { pick(sel, e.shiftKey); e.preventDefault(); }
      else if (e.key === "Escape") back.remove();
    });
    list.addEventListener("click", (e) => { const li = e.target.closest("li"); if (li) pick(+li.dataset.i, e.altKey); });
    back.addEventListener("click", (e) => { if (e.target === back) back.remove(); });
    input.focus();
  }

  // ---- Actions -----------------------------------------------------------------------------

  document.addEventListener("click", async (e) => {
    const sym = e.target.closest("a.sym");
    if (sym) { e.preventDefault(); return contextFor(sym.dataset.ref); }
    // A name in the code: show the symbol it names, if codewalk can tell which
    const name = e.target.closest(".lc span");
    if (name && NAME.test(name.className) && !getSelection().toString()) {
      const row = name.closest(".row");
      const fig = name.closest("figure.walk");
      const file = fig ? data.symbols?.[fig.dataset.ref]?.file : name.closest("#context") ? panelFile?.file : null;
      if (file && row?.dataset.line) {
        try {
          const s = await api(`/api/named?name=${encodeURIComponent(name.textContent.trim())}&file=${encodeURIComponent(file)}&line=${row.dataset.line}`);
          return openContext(s);
        } catch { return toast(`Not sure which ${name.textContent.trim()} that is`); }
      }
    }
    const req = e.target.closest("a.req");
    if (req && req.getAttribute("href")?.startsWith("#r-")) return;
    if (req) {
      e.preventDefault();
      const r = data.requirements?.[req.dataset.req];
      if (e.altKey) return copy(req.dataset.req, "Requirement");
      if (r) location.href = `/spec/${r.file}?req=${encodeURIComponent(req.dataset.req)}`;
      return;
    }
    const go = e.target.closest("[data-go]");
    if (go && !e.target.closest("a, button, summary, details")) { location.href = go.dataset.go; return; }
    if (!e.target.closest(".chosen")) $$(".chosen").forEach((el) => el.classList.remove("chosen"));
    const trace = e.target.closest("a.trace");
    if (trace) {
      e.preventDefault();
      return openContext({ file: trace.dataset.file, start: +trace.dataset.start, end: +trace.dataset.end, line: +trace.dataset.line });
    }
    const goto = e.target.closest("[data-goto-md]");
    if (goto) {
      e.preventDefault();
      const el = blockAt(+goto.dataset.gotoMd);
      if (el) { el.scrollIntoView({ block: "center" }); el.classList.add("flash-block"); setTimeout(() => el.classList.remove("flash-block"), 1200); }
      return;
    }
    const oi = e.target.closest(".oi");
    if (oi) {
      if (e.altKey) return copy(oi.dataset.ref, "Reference copied");
      return highlightRange(+oi.dataset.start, +oi.dataset.end, +oi.dataset.line);
    }
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const fig = btn.closest("figure.walk");
    const action = btn.dataset.action;
    if (action !== "copy-text" && btn.tagName === "A" && btn.getAttribute("href") === "#") e.preventDefault();
    if (action === "context" && fig) { e.preventDefault(); contextFor(fig.dataset.ref); }
    else if (action === "copy" && fig) copy(fig.dataset.ref, "Reference copied");
    else if (action === "copy-text") copy(btn.dataset.text, "Reference copied");
    else if (action === "diff" && fig) { const d = $("pre.diff:not(.plan)", fig); d.hidden = !d.hidden; }
    else if (action === "plan" && fig) { const d = $("pre.plan", fig); d.hidden = !d.hidden; }
    else if (action === "review" && fig) {
      await api("/api/review", { path: data.doc, ref: fig.dataset.ref });
      toast(`Marked reviewed: ${fig.dataset.ref}`);
      refresh();
    } else if (action === "review-all") {
      const r = await api("/api/review", { path: data.doc });
      toast(`${r.reviewed.length} marked reviewed`);
      refresh();
    } else if (action === "close-context") closeContext();
    else if (action === "toggle-outline") toggleOutline();
    else if (action === "toggle-margin") toggleMargin();
    else if (action === "palette") palette();
    else if (action === "theme") toggleTheme();
    else if (action === "save") save();
    else if (action === "edit" || action === "done") { e.preventDefault(); location.href = here(action === "edit" ? "edit" : reading()); }
    else if (action === "sync") setLinked(!linked);
    else if (action === "ask") {
      const group = btn.closest("[data-md-end]");
      // About one figure of several in a block: the question goes straight under it
      const fig = btn.closest("figure.walk");
      const where = fig?.dataset.md && !fig.classList.contains("proposal") ? { about: +fig.dataset.md } : { after: +group.dataset.mdEnd };
      composer(fig || group, { ...where, kind: "question" }, "Ask a question about this");
    } else if (action === "reply") {
      const thread = btn.closest(".thread");
      composer(thread, { thread: +thread.dataset.thread, kind: btn.dataset.kind }, { answer: "Answer", question: "Ask more", decision: "Record a decision", done: "Say what was done" }[btn.dataset.kind]);
    } else if (action === "reply-note") {
      const n = btn.closest(".note");
      composer(n, { to: +n.dataset.note }, "Reply to this note", true);
    } else if (action === "resolve") {
      const thread = btn.closest(".thread");
      const mode = btn.dataset.mode;
      if (mode === "remove" && !confirm("Remove this thread from the walkthrough altogether?")) return;
      await api("/api/resolve", { path: data.doc, thread: +thread.dataset.thread, mode });
      toast(mode === "changelog" ? "Moved to the changelog, as one line" : "Removed");
      refresh();
    } else if (action === "agree" && fig) {
      // r[impl proposal.agree]
      composer(fig, { line: +fig.dataset.md, end: +fig.dataset.mdEnd }, `Agree ${fig.dataset.ref}`, false, { endpoint: "/api/agree", text: "Agreed: write it as proposed." });
    } else if (action === "settle" && fig) {
      const r = await api("/api/settle", { path: data.doc, line: +fig.dataset.md });
      toast(`Settled: ${r.settled} is an ordinary excerpt now`);
      refresh();
    } else if (action === "reconcile") {
      await api("/api/reconcile", { path: data.doc, id: btn.dataset.req });
      toast(`${btn.dataset.req}: prose and requirement agree`);
      refresh();
    } else if (action === "reconcile-all") {
      const r = await api("/api/reconcile", { path: data.doc });
      toast(`${r.reconciled.length} requirements agree with their prose`);
      refresh();
    }
  });

  // A note, written into the Markdown: a new question after a block, or added to a thread
  function composer(after, target, title, chooseKind = false, { endpoint = "/api/note", text = "" } = {}) {
    $$(".composer").forEach((c) => c.remove());
    const box = document.createElement("form");
    box.className = "composer";
    box.innerHTML = `<div class="cp-head">${esc(title)} <span class="hint">It's written into the Markdown. ⌘↵ to send</span></div>
      ${chooseKind ? `<div class="cp-kinds">${["answer", "question", "decision", "note", "done"].map((k, i) => `<label><input type="radio" name="kind" value="${k}"${i ? "" : " checked"}> ${k}</label>`).join("")}</div>` : ""}
      <textarea rows="3" placeholder="Markdown, [[names]] and all"></textarea>
      <div class="cp-foot"><button type="button" class="tb" data-role="cancel">Cancel</button><button class="tb primary">Send</button></div>`;
    if (after.classList.contains("note")) after.appendChild(box);
    else after.insertAdjacentElement(after.classList.contains("thread") ? "beforeend" : "afterend", box);
    const ta = $("textarea", box);
    ta.value = text;
    ta.focus();
    ta.select();
    const send = async () => {
      if (!ta.value.trim()) return;
      const kind = $("input[name=kind]:checked", box)?.value;
      const r = await api(endpoint, { path: data.doc, text: ta.value, ...target, ...(kind ? { kind } : {}) });
      box.remove();
      toast(`Written${r.author ? ` as @${r.author}` : ""}`);
      refresh();
    };
    box.addEventListener("submit", (e) => { e.preventDefault(); send(); });
    ta.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); send(); }
      if (e.key === "Escape") box.remove();
    });
    $("[data-role=cancel]", box).addEventListener("click", () => box.remove());
  }

  // ---- Specs: the requirements in the margin, beside the prose that cites them ---------------

  // A walkthrough's margin of requirements can be put away, and stays as left
  // The margin's state, before anything lays it out
  let marginRows = []; // [the prose's top, how far below it its cards are], in the document's terms
  let focusCard = null; // the card you came for, which `followMargin` lines up rather than its group
  let marginHeld = null; // [a card, the block it's held beside], or true once scrolled by hand
  function toggleMargin(set) {
    const prose = $("#prose");
    const off = set ?? !prose.classList.contains("no-margin");
    prose.classList.toggle("no-margin", off);
    $("#margin-toggle")?.classList.toggle("on", !off);
    store.set("codewalk-margin", off ? "off" : "on");
    layoutMargin();
  }
  if (data.margin) toggleMargin(store.get("codewalk-margin") === "off");

  // Each group of cards beside the prose citing it, or below the group before it if that's
  // in the way. Reading a page, the margin is its own pane, scrolled to follow the prose:
  // see `followMargin`.
  function layoutMargin() {
    const margin = $("#margin");
    const doc = $(".spec-doc");
    if (!margin || !doc) return;
    const base = doc.getBoundingClientRect().top;
    let floor = 0;
    marginRows = [];
    for (const g of $$(".mgroup", margin)) {
      const anchor = $(`.spec-doc [data-md="${g.dataset.anchor}"]`);
      const want = anchor ? anchor.getBoundingClientRect().top - base : floor;
      const top = Math.max(want, floor);
      g.style.top = `${top}px`;
      floor = top + g.offsetHeight + 10;
      if (anchor) marginRows.push([want, top - want + (focusCard && g.contains(focusCard) ? focusCard.offsetTop : 0)]);
    }
    margin.style.minHeight = `${floor}px`;
    // Room below the last card, so the margin can scroll it up beside prose near the end
    $(".mspacer", margin)?.remove();
    if (getComputedStyle(margin).position === "sticky") {
      const spacer = margin.appendChild(Object.assign(document.createElement("div"), { className: "mspacer" }));
      Object.assign(spacer.style, { top: `${floor}px`, height: `${innerHeight}px` });
    }
    followMargin();
  }
  // r[impl ui.margin]
  // Scroll the margin so the cards for the prose in the middle of the screen are beside it:
  // each group lined up with its prose until the next is near, then easing to the next's
  // offset, so it keeps up as the page scrolls. Scrolled itself, it stays where it's put
  // until the page scrolls.
  function followMargin() {
    const margin = $("#margin");
    const doc = $(".spec-doc");
    if (Array.isArray(marginHeld)) return holdMargin(...marginHeld);
    if (marginHeld || !margin || !doc || !marginRows.length || getComputedStyle(margin).position !== "sticky") return;
    const d = doc.getBoundingClientRect().top;
    const reading = ($(".topbar").getBoundingClientRect().bottom + innerHeight) / 2 - d;
    const EASE = 160;
    let bias = marginRows[0][1];
    for (let i = 0; i < marginRows.length; i++) {
      const [a, b] = marginRows[i];
      if (reading < a) {
        if (i > 0) {
          const [a0, b0] = marginRows[i - 1];
          const from = Math.max(a0, a - EASE);
          bias = reading <= from ? b0 : b0 + ((b - b0) * (reading - from)) / Math.max(1, a - from);
        }
        break;
      }
      bias = b;
    }
    margin.scrollTop = margin.getBoundingClientRect().top - d + bias;
  }
  // Line one card up with a block of the document, and keep it there until the page scrolls
  function holdMargin(card, beside) {
    const margin = $("#margin");
    if (!margin || !card || !beside || getComputedStyle(margin).position !== "sticky") return;
    margin.scrollTop += card.getBoundingClientRect().top - beside.getBoundingClientRect().top;
    marginHeld = [card, beside];
  }
  addEventListener("scroll", followMargin, { passive: true });
  for (const kind of ["wheel", "touchstart", "keydown", "mousedown"]) {
    addEventListener(kind, (e) => { marginHeld = e.target.closest?.("#margin") ? true : null; }, { passive: true, capture: true });
  }
  addEventListener("resize", layoutMargin);
  addEventListener("load", layoutMargin);
  document.fonts?.ready.then(layoutMargin);
  document.addEventListener("mouseover", (e) => {
    const id = e.target.closest("[data-req-card]")?.dataset.reqCard || e.target.closest(".spec-doc a.req")?.dataset.req;
    $$(".lit").forEach((el) => el.classList.remove("lit"));
    if (!id) return;
    $$(`[data-req-card="${CSS.escape(id)}"], .spec-doc a.req[data-req="${CSS.escape(id)}"]`).forEach((el) => el.classList.add("lit"));
  });
  document.addEventListener("input", (e) => {
    if (e.target.dataset.role === "outline-filter") {
      const q = e.target.value.toLowerCase();
      $$(".oi", panel).forEach((o) => { o.hidden = q && !o.dataset.ref.toLowerCase().includes(q); });
    }
  });
  document.addEventListener("keydown", (e) => {
    const typing = e.target.closest("input, textarea");
    if (e.key === "Escape" && !typing) {
      if ($(".palette-back")) return;
      if (panel && !panel.hidden) return closeContext();
      if (data.view === "edit") location.href = here(reading());
    }
    if (typing) return;
    if (e.key === "/") { e.preventDefault(); palette(); }
    if (e.key === "o" && panel && !panel.hidden) toggleOutline();
    if (e.key === "m" && data.margin) toggleMargin();
    if (e.key === "e" && (data.view === "walk" || data.view === "spec")) location.href = here("edit");
  });

  // ---- Contents: the section you're in -------------------------------------------------------

  const tocLinks = $$(".toc a");
  if (tocLinks.length) {
    const spy = new IntersectionObserver((entries) => {
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        tocLinks.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${en.target.id}`));
      }
    }, { rootMargin: "-50px 0px -70% 0px" });
    $$(".prose h2[id], .prose h3[id]").forEach((h) => spy.observe(h));
  }

  // ---- Keeping your place between reading and editing ----------------------------------------

  // The line of the Markdown at the top of what you're looking at
  function topLine() {
    if (data.view === "edit") return lineAtY(src.scrollTop + 8);
    const top = $(".topbar").getBoundingClientRect().bottom + 4;
    const el = $$("#prose [data-md]").find((el) => el.getBoundingClientRect().bottom > top);
    return el ? +el.dataset.md : 1;
  }
  // r[impl ui.place]
  function here(view) { return `/${view}/${data.doc}?line=${topLine()}`; }
  // The rendered block a line of Markdown is in: the last one starting at or before it
  function blockAt(line) {
    let best = null;
    for (const el of $$("#prose [data-md]")) if (+el.dataset.md <= line && (!best || +el.dataset.md >= +best.dataset.md)) best = el;
    return best;
  }
  const startLine = +new URLSearchParams(location.search).get("line") || 0;
  const chosen = new URLSearchParams(location.search).get("req");
  const chosenCard = data.view === "spec" && chosen ? $(`#margin [data-req-card="${CSS.escape(chosen)}"]`) : null;
  focusCard = chosenCard;
  layoutMargin();
  if (data.view === "spec" && chosen) {
    // Came for a requirement: light it, and the prose citing it, until you click away
    const card = chosenCard;
    const anchor = card ? +card.closest(".mgroup").dataset.anchor : 0;
    const prose = startLine ? blockAt(startLine) : anchor ? blockAt(anchor) : null;
    const def = $(`.req-def[data-req-def="${CSS.escape(chosen)}"]`);
    [card, prose, def].forEach((el) => el?.classList.add("chosen"));
    const to = prose || def;
    if (to) { to.scrollIntoView({ block: "center" }); to.classList.add("flash-block"); }
    if (prose) holdMargin(card, prose);
  } else if (startLine && (data.view === "walk" || data.view === "spec")) {
    const el = blockAt(startLine);
    if (el) { el.scrollIntoView({ block: "start" }); scrollBy(0, -64); }
  }

  // ---- The index: filtering ---------------------------------------------------------------

  if (data.view === "glossary") {
    const f = $("#gl-filter");
    f?.addEventListener("input", () => {
      const q = f.value.trim().toLowerCase();
      $$(".gl-item").forEach((i) => { i.hidden = q && !i.dataset.search.includes(q); });
      $$(".gl-group").forEach((g) => { g.hidden = !g.querySelector(".gl-item:not([hidden])"); });
    });
    if (location.hash) document.getElementById(location.hash.slice(1))?.classList.add("flash-block");
  }

  if (data.view === "index") {
    const cards = $$(".card");
    const input = $("#filter");
    const hash = new URLSearchParams(location.hash.slice(1));
    const tags = new Set((hash.get("tags") || "").split(",").filter(Boolean));
    let q = (hash.get("q") || "").toLowerCase();
    if (input) input.value = q;
    const shown = new Set();
    function apply() {
      shown.clear();
      for (const c of cards) {
        const own = c.dataset.tags.split(" ").filter(Boolean);
        const show = [...tags].every((t) => own.includes(t)) && (!q || c.dataset.search.includes(q));
        c.hidden = !show;
        if (show) shown.add(c.dataset.rel);
      }
      $$(".folder").forEach((f) => { f.hidden = !$$(".card", f).some((c) => !c.hidden); });
      const none = $("#no-match");
      if (none) none.hidden = shown.size > 0;
      $$(".tag[data-tag]").forEach((b) => b.classList.toggle("on", tags.has(b.dataset.tag)));
      const h = new URLSearchParams();
      if (tags.size) h.set("tags", [...tags].join(","));
      if (q) h.set("q", q);
      history.replaceState(null, "", h.toString() ? `#${h}` : location.pathname);
    }
    document.addEventListener("click", (e) => {
      const t = e.target.closest(".tag[data-tag]");
      if (!t) return;
      e.preventDefault();
      e.stopPropagation();
      tags.has(t.dataset.tag) ? tags.delete(t.dataset.tag) : tags.add(t.dataset.tag);
      apply();
    }, true);
    input?.addEventListener("input", () => { q = input.value.trim().toLowerCase(); apply(); });
    apply();
  }


  // ---- Live reload --------------------------------------------------------------------------

  async function refresh(text) {
    if (!data.doc) return location.reload();
    const source = text ?? (await api(`/api/source?path=${encodeURIComponent(data.doc)}`)).text;
    const out = await api("/api/render", { path: data.doc, text: source });
    const prose = $("#prose");
    const y = (prose.closest(".preview") || document.scrollingElement).scrollTop;
    prose.innerHTML = out.html;
    data = { ...data, ...out.data, problems: out.problems };
    (prose.closest(".preview") || document.scrollingElement).scrollTop = y;
    layoutMargin();
    if (data.view === "edit") { sync.stale(); sync.fromSource(); markCursor(false); }
    drawProblems(out.problems);
    if (panel && !panel.hidden && panelFile) {
      const keep = $(".row.hl", panel);
      openContext({ file: panelFile.file, start: keep ? +keep.dataset.line : 0, end: keep ? +$$(".row.hl", panel).slice(-1)[0].dataset.line : 0 });
    }
    return out;
  }
  if (data.view === "walk" || data.view === "spec" || data.view === "edit") {
    const events = new EventSource("/events");
    events.onmessage = async (e) => {
      const ev = JSON.parse(e.data);
      const mine = ev.docs.includes(data.doc);
      const reader = data.view === "walk" || data.view === "spec";
      if (reader && (mine || ev.code)) { await refresh(); toast(mine ? "Updated" : "The code changed: updated"); }
      else if (reader && ev.review) await refresh();
      if (data.view === "edit") {
        if (mine && !dirty) { const t = (await api(`/api/source?path=${encodeURIComponent(data.doc)}`)).text; if (t !== src.value) { src.value = t; toast("Changed on disk: reloaded"); } }
        if (ev.code) { await refresh(src.value); toast("The code changed: preview updated"); }
      }
    };
  }

  // ---- The editor ---------------------------------------------------------------------------

  const src = $("#src");
  let dirty = false;
  const state = $("#save-state");
  function setDirty(d) { dirty = d; if (state) { state.textContent = d ? "Unsaved" : "Saved"; state.classList.toggle("dirty", d); } }
  async function save() {
    if (!src) return;
    await api("/api/save", { path: data.doc, text: src.value });
    setDirty(false);
    toast("Saved");
  }
  function drawProblems(problems) {
    const box = $("#problems");
    if (!box) return;
    box.innerHTML = (problems || []).map((p) => `<div class="prob ${esc(p.severity)}" data-line="${p.line}">
      <span class="pl">line ${p.line}</span><span class="ps">${esc(p.severity)}</span><span>${esc(p.message)}</span>
      ${(p.candidates || []).slice(0, 4).map((c) => `<span class="pc">${esc(c)}</span>`).join("")}</div>`).join("");
  }
  if (src) {
    drawProblems(data.problems);
    let timer;
    src.addEventListener("input", () => {
      setDirty(true);
      clearTimeout(timer);
      timer = setTimeout(() => refresh(src.value), 220);
      complete.update();
    });
    src.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); save(); return; }
      if (complete.handleKey(e)) return;
      if (e.key === "Tab") { e.preventDefault(); insertAt("    "); }
    });
    src.addEventListener("click", () => complete.update());
    src.addEventListener("blur", () => setTimeout(() => complete.close(), 150));
    window.addEventListener("beforeunload", (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });
    $("#problems").addEventListener("click", (e) => {
      const p = e.target.closest(".prob");
      const c = e.target.closest(".pc");
      if (!p) return;
      gotoLine(+p.dataset.line);
      if (c) replaceRefOnLine(+p.dataset.line, c.textContent);
    });
  }
  function insertAt(text) {
    const { selectionStart: a, selectionEnd: b, value } = src;
    src.value = value.slice(0, a) + text + value.slice(b);
    src.selectionStart = src.selectionEnd = a + text.length;
    src.dispatchEvent(new Event("input"));
  }
  function gotoLine(n) {
    const lines = src.value.split("\n");
    const pos = lines.slice(0, n - 1).reduce((s, l) => s + l.length + 1, 0);
    src.focus();
    src.setSelectionRange(pos, pos + (lines[n - 1] || "").length);
    const lh = parseFloat(getComputedStyle(src).lineHeight);
    src.scrollTop = Math.max(0, (n - 6) * lh);
  }
  function replaceRefOnLine(n, ref) {
    const p = (data.problems || []).find((x) => x.line === n);
    if (!p?.ref) return;
    const lines = src.value.split("\n");
    lines[n - 1] = lines[n - 1].replace(p.ref, ref);
    src.value = lines.join("\n");
    src.dispatchEvent(new Event("input"));
    toast(`Replaced with ${ref}`);
  }

  // ---- The editor and the preview, in step -----------------------------------------------
  //
  // Every rendered block says which line of the Markdown it starts on (`data-line`). A
  // hidden copy of the textarea, one div a line, says how far down the textarea each line
  // sits once wrapped. Together they give pairs of positions, one in each pane, and
  // scrolling either pane moves the other to the point between the pairs either side.

  const preview = $("#preview");
  let linked = store.get("codewalk-linked") !== "off";
  function setLinked(on) {
    linked = on;
    store.set("codewalk-linked", on ? "on" : "off");
    $("#sync-toggle")?.classList.toggle("on", on);
    if (on) sync.fromSource();
  }

  // r[impl ui.edit-panes]
  const sync = (() => {
    let lineTops = [], pairs = null, driver = null, release;
    const mirror = document.createElement("div");
    // Kept in a box of no size, fixed, so the whole Markdown it holds can't make the page
    // taller (and so scrollable, behind the panes)
    const hold = document.createElement("div");
    Object.assign(hold.style, { position: "fixed", top: "0", left: "0", width: "0", height: "0", overflow: "hidden", visibility: "hidden" });
    hold.appendChild(mirror);
    function measure() {
      if (!src) return;
      const cs = getComputedStyle(src);
      Object.assign(mirror.style, {
        position: "absolute", visibility: "hidden", top: "0", left: "0", boxSizing: "border-box",
        width: `${src.clientWidth}px`, font: cs.font, lineHeight: cs.lineHeight, letterSpacing: cs.letterSpacing,
        tabSize: cs.tabSize, padding: cs.padding, whiteSpace: "pre-wrap", overflowWrap: "break-word",
      });
      if (!hold.isConnected) document.body.appendChild(hold);
      mirror.replaceChildren(...src.value.split("\n").map((l) => { const d = document.createElement("div"); d.textContent = l || "\u200b"; return d; }));
      lineTops = Array.from(mirror.children, (d) => d.offsetTop);
      lineTops.push(mirror.scrollHeight);
    }
    function build() {
      measure();
      const base = preview.getBoundingClientRect().top - preview.scrollTop;
      const raw = $$("#prose [data-md]")
        .map((el) => [lineTops[+el.dataset.md - 1] ?? 0, el.getBoundingClientRect().top - base])
        .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      pairs = [[0, 0]];
      for (const [a, b] of raw) {
        const [pa, pb] = pairs[pairs.length - 1];
        if (a > pa && b > pb) pairs.push([a, b]);
      }
      pairs.push([Math.max(src.scrollHeight, lineTops[lineTops.length - 1]) , preview.scrollHeight]);
    }
    // Where `y` in one pane (0: the Markdown, 1: the preview) is in the other
    function map(y, from) {
      if (!pairs) build();
      const to = 1 - from;
      for (let i = 1; i < pairs.length; i++) {
        if (y <= pairs[i][from]) {
          const [a, b] = [pairs[i - 1], pairs[i]];
          const t = (y - a[from]) / Math.max(1, b[from] - a[from]);
          return a[to] + t * (b[to] - a[to]);
        }
      }
      return pairs[pairs.length - 1][to];
    }
    function drive(who) { driver = who; clearTimeout(release); release = setTimeout(() => (driver = null), 140); }
    function fromSource() { if (src && linked) { drive("src"); preview.scrollTop = map(src.scrollTop, 0); } }
    function fromPreview() { if (src && linked) { drive("preview"); src.scrollTop = map(preview.scrollTop, 1); } }
    if (src && preview) {
      src.addEventListener("scroll", () => { if (driver !== "preview") fromSource(); flashLine.follow(); });
      preview.addEventListener("scroll", () => { if (driver !== "src") fromPreview(); });
      window.addEventListener("resize", () => { pairs = null; fromSource(); });
    }
    return { stale: () => { pairs = null; }, fromSource, drive, lineTop: (n) => { if (!lineTops.length) measure(); return lineTops[Math.max(0, n - 1)] ?? 0; }, lineTops: () => { if (!lineTops.length) measure(); return lineTops; } };
  })();

  function lineAtY(y) {
    const tops = sync.lineTops();
    let n = 1;
    for (let i = 0; i < tops.length - 1; i++) if (tops[i] <= y) n = i + 1; else break;
    return n;
  }
  function caretLine() { return src.value.slice(0, src.selectionStart).split("\n").length; }

  // A brief band behind a line of the Markdown, to show where a click in the preview went
  const flashLine = (() => {
    const band = $("#ed-line");
    let line = 0, timer;
    function place() {
      if (!band || !line) return;
      const top = sync.lineTop(line), next = sync.lineTop(line + 1);
      band.style.top = `${top - src.scrollTop}px`;
      band.style.height = `${Math.max(next - top, parseFloat(getComputedStyle(src).lineHeight))}px`;
    }
    return {
      show(n) {
        if (!band) return;
        line = n; band.hidden = false; place();
        band.classList.add("show");
        clearTimeout(timer);
        timer = setTimeout(() => band.classList.remove("show"), 700);
      },
      follow: place,
    };
  })();

  // The preview block the caret is in, marked; brought into view if it's out of sight
  let cursorBlock = null;
  function markCursor(reveal = true) {
    if (!src) return;
    const el = blockAt(caretLine());
    if (el === cursorBlock && !reveal) return;
    cursorBlock?.classList.remove("at-cursor");
    cursorBlock = el;
    if (!el) return;
    el.classList.add("at-cursor");
    if (reveal) {
      const r = el.getBoundingClientRect(), p = preview.getBoundingClientRect();
      // Scroll the preview only: scrollIntoView would scroll the page too
      if (r.bottom < p.top + 40 || r.top > p.bottom - 40) { sync.drive("preview"); preview.scrollTop += r.top - p.top - p.height / 2 + r.height / 2; }
    }
  }

  // Click in the preview: put the caret on that line of the Markdown, level with the click
  preview?.addEventListener("click", (e) => {
    if (e.target.closest("a, button, input, .hovercard")) return;
    if (getSelection().toString()) return;
    const el = e.target.closest("#prose [data-md]");
    if (!el) return;
    let line = +el.dataset.md;
    // In a `walk` block, the line naming the symbol clicked
    const fig = e.target.closest("figure.walk[data-md]");
    if (fig) line = +fig.dataset.md;
    const lines = src.value.split("\n");
    const pos = lines.slice(0, line - 1).reduce((s, l) => s + l.length + 1, 0);
    const offset = el.getBoundingClientRect().top - preview.getBoundingClientRect().top;
    sync.drive("preview");
    src.focus({ preventScroll: true });
    src.setSelectionRange(pos, pos);
    src.scrollTop = sync.lineTop(line) - offset;
    flashLine.show(line);
    markCursor(false);
  });

  if (src) {
    $("#sync-toggle")?.classList.toggle("on", linked);
    for (const ev of ["keyup", "click"]) src.addEventListener(ev, () => markCursor(true));
    src.addEventListener("input", () => sync.stale());
    // Arrived with ?line=: open there
    requestAnimationFrame(() => {
      if (startLine) {
        const lines = src.value.split("\n");
        const pos = lines.slice(0, startLine - 1).reduce((s, l) => s + l.length + 1, 0);
        src.setSelectionRange(pos, pos);
        src.scrollTop = sync.lineTop(startLine) - 8;
        flashLine.show(startLine);
      }
      sync.fromSource();
      markCursor(false);
    });
  }

  // Completion: after `[[`, or on a line inside a ```walk block
  const complete = (() => {
    let box = null, items = [], sel = 0, ctx = null, timer, last = "";
    function context() {
      const pos = src.selectionStart;
      const before = src.value.slice(0, pos);
      const open = before.lastIndexOf("[[");
      if (open >= 0 && !before.slice(open).includes("]]") && !before.slice(open).includes("\n") && !before.slice(open).includes("|")) {
        return { kind: "wiki", from: open + 2, query: before.slice(open + 2) };
      }
      const lines = before.split("\n");
      const cur = lines[lines.length - 1];
      let inWalk = false;
      for (const l of lines.slice(0, -1)) {
        if (l.trim() === "```walk") inWalk = true;
        else if (l.trim().startsWith("```")) inWalk = false;
      }
      if (inWalk && /^\S*$/.test(cur) && cur.length) return { kind: "walk", from: pos - cur.length, query: cur };
      return null;
    }
    function close() { box?.remove(); box = null; items = []; ctx = null; }
    function place() {
      // A mirror of the textarea, to find where the caret is on screen
      const m = document.createElement("div");
      const cs = getComputedStyle(src);
      for (const p of ["font", "lineHeight", "padding", "border", "letterSpacing", "tabSize", "whiteSpace", "wordWrap", "width"]) m.style[p] = cs[p];
      m.style.position = "absolute"; m.style.visibility = "hidden"; m.style.whiteSpace = "pre-wrap"; m.style.wordWrap = "break-word";
      m.textContent = src.value.slice(0, src.selectionStart);
      const caret = document.createElement("span"); caret.textContent = "​"; m.appendChild(caret);
      document.body.appendChild(m);
      const r = src.getBoundingClientRect();
      const x = r.left + caret.offsetLeft - src.scrollLeft;
      const y = r.top + caret.offsetTop - src.scrollTop + parseFloat(cs.lineHeight);
      m.remove();
      box.style.left = `${Math.min(x, innerWidth - box.offsetWidth - 12)}px`;
      box.style.top = `${Math.min(y + 4, innerHeight - box.offsetHeight - 12)}px`;
    }
    function draw() {
      if (!items.length) return close();
      if (!box) { box = document.createElement("div"); box.className = "complete"; document.body.appendChild(box); box.addEventListener("mousedown", (e) => { const li = e.target.closest("li"); if (li) { e.preventDefault(); accept(+li.dataset.i); } }); }
      const s = items[sel];
      box.innerHTML = `<ul>${items.map((it, i) => `<li class="${i === sel ? "sel" : ""}" data-i="${i}"><span class="kind k-${esc(it.kind)}">${esc(it.kind)}</span>${esc(it.ref)}<span class="cw">${esc(it.file.split("/").slice(-2).join("/"))}:${it.line}</span></li>`).join("")}</ul>
        <div class="cd">${esc(s.signature)}${s.doc ? "\n\n" + esc(s.doc) : ""}</div>`;
      $("li.sel", box)?.scrollIntoView({ block: "nearest" });
      place();
    }
    function accept(i) {
      const s = items[i];
      if (!s || !ctx) return;
      const pos = src.selectionStart;
      const after = src.value.slice(pos);
      const tail = ctx.kind === "wiki" && !after.startsWith("]]") ? "]]" : "";
      src.value = src.value.slice(0, ctx.from) + s.ref + tail + after;
      src.selectionStart = src.selectionEnd = ctx.from + s.ref.length + tail.length;
      close();
      src.dispatchEvent(new Event("input"));
    }
    function update() {
      ctx = context();
      if (!ctx || ctx.query.length < 2) return close();
      if (ctx.query === last && box) return;
      last = ctx.query;
      clearTimeout(timer);
      timer = setTimeout(async () => { items = await api(`/api/symbols?q=${encodeURIComponent(ctx.query.split("::").slice(-1)[0])}`); const q = ctx.query.toLowerCase(); if (ctx.query.includes("::")) items = items.filter((it) => it.qualified.toLowerCase().includes(q)); sel = 0; draw(); }, 80);
    }
    function handleKey(e) {
      if (!box) return false;
      if (e.key === "ArrowDown") { sel = Math.min(items.length - 1, sel + 1); draw(); }
      else if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); draw(); }
      else if (e.key === "Enter" || e.key === "Tab") accept(sel);
      else if (e.key === "Escape") close();
      else return false;
      e.preventDefault();
      return true;
    }
    return { update, handleKey, close };
  })();

  // Arrived at /walk/x#ref-…: show that symbol off
  if (location.hash.startsWith("#ref-")) {
    const fig = document.getElementById(location.hash.slice(1));
    if (fig) { fig.classList.add("flash"); fig.scrollIntoView({ block: "center" }); }
  }
})();
