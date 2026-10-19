// DRAFT (dev preview only): Frieda Postfach in four tabs.
// The real panel provides Regeln, KI-Sortierung, KI-Protokoll, the runs and the timeline; only the per-mail
// "Aktivität" table is new. Nothing here is part of the integration yet.
import { UI_STYLE, applyPaging, esc, fmt, fmtShort, ico, pagerSlot } from "./frieda/ui.js";
// the panel's own styles, fresh (the browser may hold an older copy without a query)
const { STYLE } = await import(`./postfach/styles.js?draft=${Date.now().toString(36)}`);

const TABS = [
  ["aktivitaet", "Aktivität", "history"],
  ["regeln", "Regeln", "filter-outline"],
  ["ki", "KI-Sortierung", "creation"],
  ["protokoll", "KI-Protokoll", "shield-lock-outline"],
];

// which parts of the real panel each tab shows
const PANEL_CSS = {
  common: `.toolbar { display: none !important; } .wtray { display: none !important; }`,
  aktivitaet: `section.widget { display: none !important; }`,
  runs: `section.widget:not([data-widget="history"]) { display: none !important; }`,
  regeln: `section.widget:not([data-widget="rules"]) { display: none !important; }`,
  // the AI settings without "Zuletzt bewertet" (that moves to Aktivität)
  ki: `section.widget:not([data-widget="ai"]) { display: none !important; }
       section[data-widget="ai"] .card > h3.with-add, section[data-widget="ai"] .card > h3.with-add ~ * { display: none !important; }`,
  protokoll: `section.widget:not([data-widget="aiu"]) { display: none !important; }`,
};

const CHROME_CSS = `
  :host { display: block; }
  .toolbar { position: relative; }
  .tabsbar { display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff);
    border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .tabsbar::-webkit-scrollbar { display: none; }
  .tabsbar button { flex: none; display: inline-flex; align-items: center; gap: 8px; background: none; border: 0; border-radius: 0;
    color: inherit; opacity: .72; font: inherit; font-size: 14px; font-weight: 500; padding: 12px 14px 10px; min-height: 0;
    border-bottom: 2px solid transparent; --mdc-icon-size: 18px; cursor: pointer; }
  .tabsbar button[aria-selected="true"] { opacity: 1; border-bottom-color: var(--primary-color); }
  .tabsbar button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -4px; border-radius: 6px; }
  .tabsbar .n { font-size: 11px; padding: 0 6px; border-radius: 8px; background: color-mix(in srgb, var(--primary-color) 22%, transparent); }
  @media (max-width: 600px) {
    .tabsbar { gap: 0; padding: 0 4px; }
    .tabsbar button { flex: 1 1 0; min-width: 0; flex-direction: column; gap: 2px; padding: 8px 2px 6px; font-size: 12px; --mdc-icon-size: 20px; position: relative; }
    .tabsbar .n { position: absolute; top: 4px; left: calc(50% + 8px); }
  }
  .draftnote { margin: 12px 16px 0; padding: 8px 12px; border-radius: 10px; font-size: 13px; color: var(--secondary-text-color);
    background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
`;

const ACT_CSS = `
  .statusline { display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; }
  .statusline .st { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px 4px 8px; border-radius: 14px; font-size: 13px;
    background: var(--secondary-background-color); color: var(--frieda-text-on-fill); --mdc-icon-size: 16px; border: 0; font: inherit; font-size: 13px; min-height: 0; }
  .statusline button.st { cursor: pointer; }
  .statusline button.st:hover { background: color-mix(in srgb, var(--primary-color) 10%, var(--secondary-background-color)); }
  .statusline .st.ok ha-icon { color: var(--frieda-text-ok); }
  .statusline .st.ai ha-icon { color: var(--frieda-text-ai); }
  .statusline .st.err { background: color-mix(in srgb, var(--error-color, #db4437) 10%, transparent); color: var(--frieda-text-err); }
  .statusline .st.err button { background: none; border: 0; padding: 0; color: inherit; font: inherit; text-decoration: underline; cursor: pointer; min-height: 0; }
  .acttable .c-sel { width: 28px; padding-right: 0; }
  .acttable .res { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; padding: 2px 10px 2px 7px; border-radius: 12px;
    background: var(--secondary-background-color); color: var(--frieda-text-on-fill); --mdc-icon-size: 15px; white-space: nowrap; }
  .acttable .res.rule { background: color-mix(in srgb, var(--info-color, #039be5) 13%, transparent); color: var(--frieda-text-info); }
  .acttable .res.ai { background: color-mix(in srgb, var(--frieda-ai-color, #8e6bd8) 14%, transparent); color: var(--frieda-text-ai); }
  .acttable .res.held { background: color-mix(in srgb, var(--success-color, #43a047) 14%, transparent); color: var(--frieda-text-ok); }
  .acttable .res.del { background: color-mix(in srgb, var(--error-color, #db4437) 11%, transparent); color: var(--frieda-text-err); }
  .acttable .where { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; --mdc-icon-size: 15px; }
  .acttable .nm small { font-size: 12.5px; }
  .viewseg { margin-left: auto; }
  @container (max-width: 720px) {
    .acttable tbody tr[data-search] { grid-template-columns: 28px minmax(0, 1fr) auto; grid-template-areas: "sel subj time" "sel res res" "sel where where"; }
    .acttable .c-sel { grid-area: sel; align-self: start; padding-top: 4px; }
    .acttable .c-subj { grid-area: subj; }
    .acttable .c-time { grid-area: time; text-align: right; }
    .acttable .c-res { grid-area: res; }
    .acttable .c-where { grid-area: where; }
    .viewseg { margin-left: 0; }
  }
`;

const norm = (s) => String(s || "").toLowerCase().replace(/[^\p{L}\p{N} ]/gu, "").trim();

// One row per mail: what the rules or the AI did with it (from the example runs and ratings).
function activityRows(data) {
  const ratings = data["friedafetch_mail/ai"]?.ratings || [];
  const seen = new Set();
  const rows = [];
  for (const run of data["friedafetch_mail/rules/history"]?.runs || []) {
    for (const m of run.mails || []) {
      const key = `${m.subject}|${m.from}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const a = norm(m.subject);
      const rating = a && ratings.find((r) => { const b = norm(r.subject); return b && (b.includes(a.slice(0, 15)) || a.includes(b.slice(0, 15))); });
      const ai = m.ai || null;
      let kind = "none";
      if ((m.rules || []).length) kind = m.delete ? "del" : "rule";
      else if (ai?.held) kind = "held";
      else if (ai?.category) kind = "ai";
      const moved = (ai?.applied || []).find((a) => String(a).startsWith("moved:"));
      rows.push({
        time: run.started,
        subject: m.subject,
        from: m.from,
        kind,
        rule: (m.rules || []).join(", "),
        category: rating?.corrected || ai?.category || "",
        importance: ai?.importance,
        rating,
        where: m.delete ? "Papierkorb" : m.move_to ? `INBOX → ${m.move_to}` : moved ? `INBOX → ${moved.slice(6)}` : "INBOX",
      });
    }
  }
  return rows;
}

export async function mount({ el, root, data, q }) {
  const sheet = new CSSStyleSheet();
  root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];

  // the chrome: toolbar and tabs (above the panel)
  const chrome = document.createElement("div");
  el.before(chrome);
  const croot = chrome.attachShadow({ mode: "open" });

  // the new Aktivität tab (below the chrome, before the panel)
  const act = document.createElement("div");
  chrome.after(act);
  const aroot = act.attachShadow({ mode: "open" });

  const state = { tab: (location.hash || "").slice(1) || "aktivitaet", view: "mail", filter: "", q: "", sel: new Set(), pages: {} };
  if (!TABS.some(([id]) => id === state.tab)) state.tab = "aktivitaet";
  const rows = activityRows(data);
  const ai = data["friedafetch_mail/ai"];
  const auto = data["friedafetch_mail/rules/list"]?.automation || {};
  const lastErr = (data["friedafetch_mail/rules/history"]?.runs || []).find((r) => (r.errors || []).length);
  const layoutStub = { opt: (id, key, fb) => (state.pages[`size-${id}`] ?? fb), setOpt: (id, key, v) => (state.pages[`size-${id}`] = v) };

  const resLabel = (r) =>
    ({
      rule: [r.rule, "filter-check-outline", "rule"],
      del: [`${r.rule} · Papierkorb`, "delete-outline", "del"],
      held: ["Killswitch", "shield-check-outline", "held"],
      ai: [`${r.category}${r.importance ? ` · ${r.importance}/5` : ""}`, "creation", "ai"],
      none: ["keine Aktion", "minus-circle-outline", ""],
    })[r.kind];
  const kinds = { "": () => true, rule: (r) => r.kind === "rule" || r.kind === "del", ai: (r) => r.kind === "ai", held: (r) => r.kind === "held", none: (r) => r.kind === "none" };

  function goto(tab) {
    state.tab = tab;
    history.replaceState(null, "", `${location.pathname}${location.search}#${tab}`);
    draw();
    croot.querySelector(`[data-tab="${tab}"]`)?.focus();
  }

  function drawChrome() {
    const pendingSel = state.sel.size;
    croot.innerHTML = `<style>${UI_STYLE}${CHROME_CSS}</style>
      <div class="toolbar"><img src="./postfach/icon.svg" alt=""><span>Frieda Postfach</span><span class="grow"></span></div>
      <nav class="tabsbar" role="tablist" aria-label="Bereiche">${TABS.map(
        ([id, label, icon]) =>
          `<button role="tab" id="tab-${id}" aria-selected="${state.tab === id}" tabindex="${state.tab === id ? 0 : -1}" data-tab="${id}">${ico(icon)}${esc(label)}${id === "aktivitaet" && pendingSel ? `<span class="n">${pendingSel}</span>` : ""}</button>`
      ).join("")}</nav>
      <div class="draftnote">Entwurf · Tabs statt einer langen Seite. „Aktivität“ ist neu: eine Zeile pro Mail statt „Zuletzt bewertet“ und der Mail-Listen in den Ausführungen.</div>`;
    croot.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => goto(b.dataset.tab)));
    croot.querySelector('[role="tablist"]').addEventListener("keydown", (ev) => {
      const i = TABS.findIndex(([id]) => id === state.tab);
      const next = ev.key === "ArrowRight" ? i + 1 : ev.key === "ArrowLeft" ? i - 1 : null;
      if (next === null) return;
      ev.preventDefault();
      croot.querySelectorAll("[data-tab]")[(next + TABS.length) % TABS.length].click();
    });
  }

  function drawActivity() {
    if (state.tab !== "aktivitaet") {
      aroot.innerHTML = "";
      return;
    }
    const st = [
      auto.push?.state === "listening" ? `<button class="st ok" data-goto="regeln">${ico("lightning-bolt")}Push aktiv</button>` : "",
      `<button class="st" data-goto="regeln">${ico("timer-outline")}Takt alle ${esc(auto.interval || 5)} Min.</button>`,
      ai?.status?.active ? `<button class="st ai" data-goto="ki">${ico("creation")}KI: ${ai.status.mode === "act" ? "Aktionen ausführen" : "nur bewerten"}</button>` : "",
      lastErr ? `<span class="st err">${ico("alert-circle-outline")}Fehler ${esc(fmtShort(lastErr.started))}: ${esc(lastErr.errors[0])} · <button data-act="show-runs">Durchgänge</button></span>` : "",
    ].join("");
    const seg = (val, label, icon) => {
      const n = rows.filter(kinds[val]).length;
      if (val && !n) return "";
      return `<button class="seg ${state.filter === val ? "on" : ""}" data-filter="${val}" aria-pressed="${state.filter === val}">${ico(icon)}${esc(label)}<span class="n">${n}</span></button>`;
    };
    const view = `<div class="segs viewseg" role="group" aria-label="Ansicht"><button class="seg ${state.view === "mail" ? "on" : ""}" data-view="mail" aria-pressed="${state.view === "mail"}">${ico("email-outline")}Nach Mail</button><button class="seg ${state.view === "runs" ? "on" : ""}" data-view="runs" aria-pressed="${state.view === "runs"}">${ico("format-list-numbered")}Nach Durchgang</button></div>`;
    const list = rows.filter(kinds[state.filter] || kinds[""]);
    const body = list
      .map((r, i) => {
        const [label, icon, cls] = resLabel(r);
        const id = r.rating?.id || (r.kind === "rule" || r.kind === "del" ? null : `mail-${i}`); // rule hits are not for the AI
        const search = `${r.subject} ${r.from} ${label} ${r.where}`.toLowerCase();
        return `<tr class="arow ${id && state.sel.has(id) ? "picked" : ""}" data-search="${esc(search)}" data-subject="${esc(r.subject)}" data-from="${esc(r.from)}">
          <td class="c-sel">${id ? `<input type="checkbox" class="selbox" data-sel="${esc(id)}" ${state.sel.has(id) ? "checked" : ""} aria-label="Auswählen: ${esc(r.subject)}">` : ""}</td>
          <td class="c-time num dim">${esc(fmtShort(r.time))}</td>
          <td class="c-subj"><button class="rtext go" data-open><span class="nm"><strong>${esc(r.subject)}</strong><small>${esc(r.from)}</small></span>${ico("chevron-right")}</button></td>
          <td class="c-res"><span class="res ${cls}">${ico(icon)}${esc(label)}</span></td>
          <td class="c-where"><span class="where">${ico("folder-outline")}${esc(r.where)}</span></td>
        </tr>`;
      })
      .join("");
    const selbar = state.sel.size
      ? `<div class="selbar"><strong>${state.sel.size} ausgewählt</strong><span class="grow"></span><button class="link small" data-act="sel-clear">Auswahl aufheben</button><button class="pill" data-act="rerate">${ico("refresh")}Neu bewerten</button></div>`
      : "";
    const table =
      state.view === "mail"
        ? `<div class="card">
            <div class="chead"><h2>Aktivität</h2></div>
            <p class="muted" style="margin:0 0 10px">Jede Mail, die Frieda Postfach geprüft hat – und was Regeln und KI mit ihr gemacht haben. Ein Klick zeigt den ganzen Verlauf.</p>
            <div class="tbar"><label class="search">${ico("magnify")}<input type="search" data-q value="${esc(state.q)}" placeholder="Betreff oder Absender suchen" aria-label="Betreff oder Absender suchen"></label>
              <div class="segs" role="group" aria-label="Ergebnis">${seg("", "Alle", "format-list-bulleted")}${seg("rule", "Regel", "filter-outline")}${seg("ai", "KI", "creation")}${seg("held", "Killswitch", "shield-check-outline")}${seg("none", "Keine Aktion", "minus-circle-outline")}</div>${view}</div>
            ${selbar}
            <div class="scroll"><table class="dtable acttable" data-table="act"><thead><tr>
              <th class="c-sel"><span class="vh">Auswahl</span></th><th class="c-time num">Zeit</th><th>Mail</th><th class="c-res">Ergebnis</th><th class="c-where">Liegt jetzt</th>
            </tr></thead><tbody>${body}</tbody></table></div>${pagerSlot("act")}
          </div>`
        : `<div class="card"><div class="chead"><h2>Aktivität</h2></div><div class="tbar" style="margin-bottom:0"><span class="muted">Die Durchgänge sind die technische Sicht – für die Fehlersuche.</span>${view}</div></div>`;
    aroot.innerHTML = `<style>${UI_STYLE}${STYLE}${ACT_CSS}</style><div class="content widgets" style="padding-bottom:0"><section class="widget w-full"><div class="card"><div class="statusline">${st}</div></div></section><section class="widget w-full">${table}</section></div>`;
    if (state.view === "mail") {
      const qv = state.q.toLowerCase().trim();
      aroot.querySelectorAll("tbody tr[data-search]").forEach((tr) => (tr.dataset.nomatch = !qv || tr.dataset.search.includes(qv) ? "0" : "1"));
      applyPaging(aroot, layoutStub, "act", state.pages, { perPage: "Pro Seite", pageAll: "Alle", pageRange: "{0}–{1} von {2}", prevPage: "Vorherige Seite", nextPage: "Nächste Seite" }, 10);
    }
    aroot.querySelectorAll("[data-filter]").forEach((b) => b.addEventListener("click", () => ((state.filter = b.dataset.filter), (state.pages.act = 0), draw())));
    aroot.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => ((state.view = b.dataset.view), draw())));
    aroot.querySelector("[data-q]")?.addEventListener("input", (ev) => {
      state.q = ev.target.value;
      state.pages.act = 0;
      const pos = ev.target.selectionStart;
      draw();
      const inp = aroot.querySelector("[data-q]");
      inp.focus();
      inp.setSelectionRange(pos, pos);
    });
    aroot.querySelectorAll("[data-sel]").forEach((c) =>
      c.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (c.checked) state.sel.add(c.dataset.sel);
        else state.sel.delete(c.dataset.sel);
        draw();
      })
    );
    aroot.querySelector('[data-act="sel-clear"]')?.addEventListener("click", () => (state.sel.clear(), draw()));
    aroot.querySelector('[data-act="rerate"]')?.addEventListener("click", () => el._rerate({ ratingIds: [...state.sel].filter((id) => !id.startsWith("mail-")) }));
    aroot.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => goto(b.dataset.goto)));
    aroot.querySelector('[data-act="show-runs"]')?.addEventListener("click", () => ((state.view = "runs"), draw()));
    aroot.querySelectorAll("tbody tr[data-search]").forEach((tr) =>
      tr.addEventListener("click", (ev) => {
        if (ev.target.closest("input")) return;
        el._openTimeline({ message_id: null, subject: tr.dataset.subject, sender: tr.dataset.from });
      })
    );
  }

  function draw() {
    const part = state.tab === "aktivitaet" ? (state.view === "runs" ? "runs" : "aktivitaet") : state.tab;
    sheet.replaceSync(PANEL_CSS.common + PANEL_CSS[part]);
    drawChrome();
    drawActivity();
  }

  draw();
}
