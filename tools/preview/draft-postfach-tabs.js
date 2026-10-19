// DRAFT (dev preview only): Frieda Postfach in four tabs.
// The real panel provides Regeln, KI-Sortierung, KI-Protokoll, the runs and the timeline steps; only "Aktivität"
// (a mail client: views and folders, the mails, a reading pane with the timeline) is new. Nothing here is part of
// the integration yet.
// the same build key as the panels (build.py fills it in), so the browser never mixes old and new files
import { UI_STYLE, esc, fmtDateTime, ico } from "./frieda/ui.js?v=__BUILD__";
import { STYLE } from "./postfach/styles.js?v=__BUILD__";

const TABS = [
  ["aktivitaet", "Aktivität", "email-outline"],
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
  .tabsbar { display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; padding: 0 12px;
    background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff);
    border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .tabsbar::-webkit-scrollbar { display: none; }
  .tabsbar button { flex: none; display: inline-flex; align-items: center; gap: 8px; background: none; border: 0; border-radius: 0;
    color: inherit; opacity: .72; font: inherit; font-size: 14px; font-weight: 500; padding: 12px 14px 10px; min-height: 0;
    border-bottom: 2px solid transparent; --mdc-icon-size: 18px; cursor: pointer; }
  .tabsbar button[aria-selected="true"] { opacity: 1; border-bottom-color: var(--primary-color); }
  .tabsbar button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -4px; border-radius: 6px; }
  @media (max-width: 600px) {
    .tabsbar { gap: 0; padding: 0 4px; }
    .tabsbar button { flex: 1 1 0; min-width: 0; flex-direction: column; gap: 2px; padding: 8px 2px 6px; font-size: 12px; --mdc-icon-size: 20px; }
  }
  .draftnote { margin: 12px 16px 0; padding: 8px 12px; border-radius: 10px; font-size: 13px; color: var(--secondary-text-color);
    background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
`;

const MC_CSS = `
  .mcwrap { container-type: inline-size; }
  .mc { display: grid; grid-template-columns: 216px minmax(300px, 390px) minmax(0, 1fr); height: max(540px, calc(100vh - 196px));
    background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none); overflow: hidden; }

  /* views and folders */
  .rail { display: flex; flex-direction: column; gap: 1px; padding: 12px 8px; overflow: auto; border-right: 1px solid var(--divider-color, #e0e0e0);
    background: color-mix(in srgb, var(--secondary-background-color) 45%, var(--card-background-color, #fff)); }
  .rail h3 { margin: 14px 10px 4px; font-size: 11.5px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: var(--secondary-text-color); }
  .rail h3:first-child { margin-top: 2px; }
  .rail button.box { display: flex; align-items: center; gap: 10px; width: 100%; padding: 7px 10px; border: 0; border-radius: 8px; background: none;
    color: var(--primary-text-color); font: inherit; font-size: 14px; text-align: left; min-height: 0; cursor: pointer; --mdc-icon-size: 18px; }
  .rail button.box ha-icon { color: var(--secondary-text-color); flex: none; }
  .rail button.box .lbl { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rail button.box .n { font-size: 12px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .rail button.box:hover { background: var(--secondary-background-color); }
  .rail button.box[aria-current="true"] { background: color-mix(in srgb, var(--primary-color) 13%, transparent); font-weight: 500; }
  .rail button.box[aria-current="true"] ha-icon { color: var(--primary-color); }
  .rail .grow { flex: 1; min-height: 16px; }
  .status { display: grid; gap: 1px; padding-top: 8px; border-top: 1px solid var(--divider-color, #e0e0e0); }
  .status button.st { display: flex; align-items: center; gap: 8px; padding: 5px 10px; border: 0; border-radius: 6px; background: none; color: var(--secondary-text-color);
    font: inherit; font-size: 12.5px; text-align: left; min-height: 0; cursor: pointer; --mdc-icon-size: 15px; }
  .status button.st:hover { background: var(--secondary-background-color); color: var(--primary-text-color); }
  .st.ok ha-icon { color: var(--frieda-text-ok); }
  .st.ai ha-icon { color: var(--frieda-text-ai); }

  /* the mails */
  .listpane { display: flex; flex-direction: column; min-width: 0; min-height: 0; border-right: 1px solid var(--divider-color, #e0e0e0); }
  .lhead { display: grid; gap: 8px; padding: 14px 14px 10px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .lhead .ttl { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
  .lhead h2 { margin: 0; font-size: 18px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lhead .cnt { font-size: 13px; color: var(--secondary-text-color); }
  .lhead .lrow { display: flex; gap: 8px; }
  .lhead label.search { flex: 1 1 120px; min-width: 0; max-width: none; }
  .lhead select.boxsel { display: none; flex: 0 1 auto; min-width: 0; max-width: 55%; }
  .lstatus { display: none; flex-wrap: wrap; gap: 4px 12px; }
  .lstatus button.st { display: inline-flex; align-items: center; gap: 6px; padding: 0; border: 0; background: none; color: var(--secondary-text-color);
    font: inherit; font-size: 12.5px; min-height: 0; cursor: pointer; --mdc-icon-size: 15px; }
  .errline { display: flex; align-items: flex-start; gap: 8px; padding: 8px 10px; border-radius: 10px; font-size: 13px; --mdc-icon-size: 17px;
    background: color-mix(in srgb, var(--error-color, #db4437) 10%, transparent); color: var(--frieda-text-err); }
  .errline span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .errline button { flex: none; padding: 0; border: 0; background: none; color: inherit; font: inherit; text-decoration: underline; min-height: 0; cursor: pointer; }
  .selbar { margin: 0; }
  .lscroll, .rbody, .rail { scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--secondary-text-color) 40%, transparent) transparent; }
  .lscroll { flex: 1; min-height: 0; overflow: auto; overscroll-behavior: contain; }
  ul.mlist { list-style: none; margin: 0; padding: 0; }
  .mlist li.day { position: sticky; top: 0; z-index: 2; padding: 6px 14px; font-size: 12px; font-weight: 600; color: var(--secondary-text-color);
    background: color-mix(in srgb, var(--secondary-background-color) 75%, var(--card-background-color, #fff)); }
  .mlist li.m { position: relative; display: grid; grid-template-columns: 36px minmax(0, 1fr); column-gap: 12px; padding: 10px 14px 11px 12px;
    border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .mlist li.m:hover { background: color-mix(in srgb, var(--secondary-background-color) 55%, transparent); }
  .mlist li.m.picked { background: color-mix(in srgb, var(--primary-color) 6%, transparent); }
  .mlist li.m.open { background: color-mix(in srgb, var(--primary-color) 12%, transparent); }
  .mlist li.m.open::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--primary-color); }
  .mlist li.m:has(.mitem:focus-visible) { outline: 2px solid var(--primary-color); outline-offset: -2px; }
  .av { position: relative; z-index: 1; width: 36px; height: 36px; border-radius: 50%; display: inline-grid; place-items: center; padding: 0; border: 0;
    background: var(--secondary-background-color); color: var(--frieda-text-on-fill); font: inherit; font-size: 13px; font-weight: 600; min-height: 0; --mdc-icon-size: 20px; }
  button.av { cursor: pointer; }
  button.av:hover { box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 45%, transparent); }
  button.av[aria-checked="true"] { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.av:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  button.mitem { display: grid; gap: 2px; min-width: 0; padding: 0; border: 0; background: none; color: inherit; font: inherit; text-align: left; min-height: 0; cursor: pointer; }
  button.mitem::after { content: ""; position: absolute; inset: 0; }  /* the whole row opens the mail */
  button.mitem:focus-visible { outline: none; }
  .mitem .r1 { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
  .mitem .from { flex: 1; min-width: 0; font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mitem .time { flex: none; font-size: 12px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  .mitem .subj { font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mitem .r3 { display: flex; align-items: center; gap: 8px; min-width: 0; margin-top: 4px; }
  .res { display: inline-flex; align-items: center; gap: 5px; min-width: 0; max-width: 100%; padding: 2px 9px 2px 6px; border-radius: 11px; font-size: 12px;
    background: var(--secondary-background-color); color: var(--frieda-text-on-fill); --mdc-icon-size: 14px; }
  .res .rl { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .res ha-icon { flex: none; }
  .res.rule { background: color-mix(in srgb, var(--info-color, #039be5) 13%, transparent); color: var(--frieda-text-info); }
  .res.ai { background: color-mix(in srgb, var(--frieda-ai-color, #8e6bd8) 14%, transparent); color: var(--frieda-text-ai); }
  .res.held { background: color-mix(in srgb, var(--success-color, #43a047) 14%, transparent); color: var(--frieda-text-ok); }
  .res.del { background: color-mix(in srgb, var(--error-color, #db4437) 11%, transparent); color: var(--frieda-text-err); }
  .where { display: inline-flex; align-items: center; gap: 4px; flex: none; font-size: 12px; color: var(--secondary-text-color); white-space: nowrap; --mdc-icon-size: 14px; }
  .lempty { padding: 32px 16px; text-align: center; color: var(--secondary-text-color); font-size: 14px; }

  /* the reading pane */
  .reader { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
  .rtop { display: flex; align-items: center; gap: 8px; min-height: 52px; box-sizing: border-box; padding: 8px 14px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .rtop .grow { flex: 1; }
  .rtop button.back { display: none; align-items: center; gap: 2px; padding: 4px 8px 4px 2px; border: 0; background: none; color: var(--primary-color);
    font: inherit; font-size: 15px; min-height: 0; cursor: pointer; --mdc-icon-size: 24px; }
  .rbody { flex: 1; min-height: 0; overflow: auto; padding: 22px 26px 12px; overscroll-behavior: contain; }
  .rhead { display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; column-gap: 12px; row-gap: 4px; align-items: center;
    padding-bottom: 16px; margin-bottom: 18px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .rhead h2 { grid-column: 1 / -1; margin: 0 0 12px; font-size: 21px; font-weight: 600; line-height: 1.3; overflow-wrap: anywhere; }
  .rhead h2:focus { outline: none; }
  .rhead .av { width: 44px; height: 44px; font-size: 15px; }
  .rhead .who { display: grid; min-width: 0; }
  .rhead .who strong { font-size: 14.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rhead .who small { font-size: 13px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rhead .date { font-size: 12.5px; color: var(--secondary-text-color); white-space: nowrap; align-self: start; padding-top: 3px; }
  .rhead .chips { grid-column: 2 / -1; display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
  .rhead .chips .res, .rhead .chips .where { font-size: 12.5px; }
  .rhead .chips .where { padding: 2px 9px 2px 6px; border-radius: 11px; background: var(--secondary-background-color); color: var(--frieda-text-on-fill); }
  h3.sect { margin: 0 0 12px; font-size: 11.5px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: var(--secondary-text-color); }
  .rfoot { padding: 10px 26px 14px; font-size: 12px; color: var(--secondary-text-color); border-top: 1px solid var(--divider-color, #e0e0e0); }
  .rempty { flex: 1; display: grid; place-content: center; justify-items: center; gap: 10px; padding: 24px; text-align: center; color: var(--secondary-text-color); --mdc-icon-size: 44px; }
  .rempty ha-icon { opacity: .45; }
  .runsbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

  /* tablet: the views move into a menu above the list */
  @container (max-width: 1000px) {
    .mc { grid-template-columns: minmax(280px, 340px) minmax(0, 1fr); }
    .rail { display: none; }
    .lhead select.boxsel { display: block; flex: 1 1 auto; font-size: 15px; font-weight: 600; }  /* the menu is the title here */
    .lhead .ttl { display: none; }
    .lstatus { display: flex; }
  }
  /* phone: list or mail, like a mail app */
  @container (max-width: 720px) {
    .mc { display: block; height: auto; overflow: visible; }
    .listpane { border-right: 0; }
    .reader { display: none; }
    .mc.reading .listpane { display: none; }
    .mc.reading .reader { display: flex; }
    .rtop button.back { display: inline-flex; }
    .lscroll, .rbody { overflow: visible; }
    .rbody { padding: 18px 16px 8px; }
    .rfoot { padding: 10px 16px 14px; }
    .rhead h2 { font-size: 19px; }
    .lhead label.search { flex-basis: auto; }
    button.av { width: 40px; height: 40px; }
    .mlist li.m { grid-template-columns: 40px minmax(0, 1fr); }
  }
`;

const NAMES = {
  "erika@example.com": "Erika Mustermann",
  "anna@example.com": "Anna Beispiel",
  "ci@code.example": "CI-Server",
  "praxis@example.com": "Praxis Dr. Beispiel",
};

// More example mails from yesterday, so the list shows days.
const EXTRA = [
  { ago: 60 * 15, subject: "Ihre Bestellung ist unterwegs", from: "versand@shop.example", name: "Shop Versand", kind: "ai", category: "Rechnungen & Belege", importance: 3, reason: "Versandbestätigung einer Bestellung.", applied: [] },
  { ago: 60 * 17, subject: "Wochenend-Angebote: bis zu 40 % auf Sofas", from: "newsletter@moebel.example", name: "Möbelhaus", kind: "ai", category: "Newsletter & Werbung", importance: 1, reason: "Werbung mit Rabattaktion.", applied: ["moved:Deleted Messages"] },
  { ago: 60 * 21, subject: "Elternabend am Donnerstag", from: "sekretariat@schule.example", name: "Schule Sekretariat", kind: "ai", category: "Persönlich & wichtig", importance: 4, reason: "Termin der Schule mit Bitte um Rückmeldung.", applied: ["flagged", "notified"] },
  { ago: 60 * 23, subject: "Rabatt-Code nur heute", from: "promo@werbung.example", name: "Werbung", kind: "del", rule: "Werbung & Newsletter löschen" },
];

const norm = (s) => String(s || "").toLowerCase().replace(/[^\p{L}\p{N} ]/gu, "").trim();
const initials = (name) =>
  String(name)
    .replace(/@.*/, "")
    .split(/[\s._-]+/)
    .filter((w) => /^\p{L}/u.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("") || "?";
const dayLabel = (iso) => {
  const d = new Date(iso);
  const today = new Date();
  const days = Math.round((new Date(today.toDateString()) - new Date(d.toDateString())) / 86400000);
  return days === 0 ? "Heute" : days === 1 ? "Gestern" : d.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });
};
const clock = (iso) => new Date(iso).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
const plus = (iso, s) => new Date(new Date(iso).getTime() + s * 1000).toISOString();

// One entry per mail: what the rules or the AI did with it (from the example runs and ratings).
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
      rows.push({
        time: run.started,
        trigger: run.trigger,
        subject: rating?.subject || m.subject,
        from: m.from,
        name: NAMES[m.from] || rating?.from || m.from,
        kind,
        rule: (m.rules || []).join(", "),
        moveTo: m.move_to,
        category: rating?.corrected || ai?.category || "",
        original: rating?.corrected ? rating.category : null,
        importance: ai?.importance,
        reason: rating?.reason,
        applied: ai?.applied || [],
        rating,
      });
    }
  }
  const now = Date.now();
  for (const x of EXTRA) rows.push({ ...x, time: new Date(now - x.ago * 60000).toISOString(), trigger: "push", rule: x.rule || "", category: x.category || "", applied: x.applied || [] });
  rows.sort((a, b) => (a.time < b.time ? 1 : -1));
  rows.forEach((r, i) => {
    r.i = i;
    const moved = r.applied.find((a) => String(a).startsWith("moved:"));
    r.folder = r.kind === "del" ? "Deleted Messages" : r.moveTo || (moved ? moved.slice(6) : "INBOX");
    r.selectable = r.kind !== "rule" && r.kind !== "del"; // rule hits are not for the AI
  });
  return rows;
}

// The timeline of one mail, in the panel's own event format (so its _tlStep draws it).
function timeline(r) {
  const t0 = plus(r.time, -40);
  const ev = [{ kind: "received", time: t0, mailbox: "INBOX" }];
  ev.push({ kind: "checked", time: plus(t0, 2), trigger: r.trigger, rules: r.rule ? [r.rule] : [], delete: r.kind === "del", move_to: r.moveTo || null });
  if (r.kind === "held") ev.push({ kind: "ai_held", time: plus(t0, 3), reasons: [{ type: "term", value: "Diagnose" }] });
  if (r.kind === "ai") {
    ev.push({ kind: "ai_sent", time: plus(t0, 3), entity: "ai_task.mein_ki_modell", ok: true, chars: 1480, duration: 3.4, fields: ["from", "to", "subject", "date"] });
    ev.push({ kind: "rated", time: plus(t0, 7), category: r.original || r.category, importance: r.importance, reason: r.reason || "" });
    if (r.applied.length) ev.push({ kind: "ai_applied", time: plus(t0, 8), applied: r.applied });
    if (r.original) ev.push({ kind: "corrected", time: plus(t0, 3600), before: r.original, after: r.category });
  }
  return ev;
}

export async function mount({ el, root, data }) {
  const sheet = new CSSStyleSheet();
  root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
  const chrome = document.createElement("div");
  el.before(chrome);
  const croot = chrome.attachShadow({ mode: "open" });
  const act = document.createElement("div");
  chrome.after(act);
  const aroot = act.attachShadow({ mode: "open" });

  const state = { tab: (location.hash || "").slice(1) || "aktivitaet", box: "all", q: "", sel: new Set(), open: null, reading: false, shown: 25 };
  if (!TABS.some(([id]) => id === state.tab)) state.tab = "aktivitaet";
  const rows = activityRows(data);
  const ai = data["friedafetch_mail/ai"];
  const auto = data["friedafetch_mail/rules/list"]?.automation || {};
  const lastErr = (data["friedafetch_mail/rules/history"]?.runs || []).find((r) => (r.errors || []).length);

  const res = (r) => {
    const [label, icon, cls] = {
      rule: [r.rule, "filter-check-outline", "rule"],
      del: [r.rule, "delete-outline", "del"],
      held: ["Killswitch", "shield-check-outline", "held"],
      ai: [`${r.category}${r.importance ? ` · ${r.importance}/5` : ""}`, r.original ? "pencil-outline" : "creation", "ai"],
      none: ["keine Aktion", "minus-circle-outline", ""],
    }[r.kind];
    return `<span class="res ${cls}">${ico(icon)}<span class="rl">${esc(label)}</span></span>`;
  };
  const folderIcon = (f) => (f === "Deleted Messages" ? "delete-outline" : f === "INBOX" ? "inbox" : "folder-outline");
  const folderName = (f) => ({ INBOX: "Posteingang", "Deleted Messages": "Papierkorb", Junk: "Werbung", Archive: "Archiv" })[f] || f; // as Apple Mail names them

  // views: by result, by folder (where the mail is now), and the runs
  const KINDS = [
    ["all", "Alle Mails", "email-multiple-outline", () => true],
    ["k:ai", "KI", "creation", (r) => r.kind === "ai"],
    ["k:rule", "Regel", "filter-outline", (r) => r.kind === "rule" || r.kind === "del"],
    ["k:held", "Killswitch", "shield-check-outline", (r) => r.kind === "held"],
    ["k:none", "Keine Aktion", "minus-circle-outline", (r) => r.kind === "none"],
  ];
  const folders = [...new Set(rows.map((r) => r.folder))].sort((a, b) => (a === "INBOX" ? -1 : b === "INBOX" ? 1 : a.localeCompare(b)));
  const FOLDERS = folders.map((f) => [`f:${f}`, folderName(f), folderIcon(f), (r) => r.folder === f]);
  const VIEWS = [...KINDS, ...FOLDERS];
  const view = () => VIEWS.find(([id]) => id === state.box) || VIEWS[0];

  function goto(tab) {
    state.tab = tab;
    history.replaceState(null, "", `${location.pathname}${location.search}#${tab}`);
    draw();
    croot.querySelector(`[data-tab="${tab}"]`)?.focus();
  }

  function drawChrome() {
    croot.innerHTML = `<style>${UI_STYLE}${CHROME_CSS}</style>
      <div class="toolbar"><img src="./postfach/icon.svg" alt=""><span>Frieda Postfach</span><span class="grow"></span></div>
      <nav class="tabsbar" role="tablist" aria-label="Bereiche">${TABS.map(
        ([id, label, icon]) => `<button role="tab" aria-selected="${state.tab === id}" tabindex="${state.tab === id ? 0 : -1}" data-tab="${id}">${ico(icon)}${esc(label)}</button>`
      ).join("")}</nav>
      <div class="draftnote">Entwurf · „Aktivität“ wie ein Mailprogramm: links Ansichten und Ordner, in der Mitte die geprüften Mails, rechts was mit der gewählten Mail passiert ist.</div>`;
    croot.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => goto(b.dataset.tab)));
    croot.querySelector('[role="tablist"]').addEventListener("keydown", (ev) => {
      const i = TABS.findIndex(([id]) => id === state.tab);
      const next = ev.key === "ArrowRight" ? i + 1 : ev.key === "ArrowLeft" ? i - 1 : null;
      if (next === null) return;
      ev.preventDefault();
      croot.querySelectorAll("[data-tab]")[(next + TABS.length) % TABS.length].click();
    });
  }

  const statusItems = () =>
    [
      auto.push?.state === "listening" ? `<button class="st ok" data-goto="regeln">${ico("lightning-bolt")}Push aktiv</button>` : "",
      `<button class="st" data-goto="regeln">${ico("timer-outline")}Zusätzlich alle ${esc(auto.interval || 5)} Min.</button>`,
      ai?.status?.active ? `<button class="st ai" data-goto="ki">${ico("creation")}KI ${ai.status.mode === "act" ? "führt Aktionen aus" : "bewertet nur"}</button>` : "",
    ].join("");

  function drawRail() {
    const box = ([id, label, icon, test]) =>
      `<button class="box" data-box="${esc(id)}" aria-current="${state.box === id}">${ico(icon)}<span class="lbl">${esc(label)}</span><span class="n">${rows.filter(test).length}</span></button>`;
    return `<nav class="rail" aria-label="Ansichten">
        <h3>Ergebnis</h3>${KINDS.filter(([id, , , test]) => id === "all" || rows.some(test)).map(box).join("")}
        <h3>Liegt jetzt in</h3>${FOLDERS.map(box).join("")}
        <h3>Technik</h3><button class="box" data-act="runs">${ico("format-list-numbered")}<span class="lbl">Durchgänge</span></button>
        <span class="grow"></span>
        <div class="status">${statusItems()}</div>
      </nav>`;
  }

  function drawList() {
    const [, label, , test] = view();
    const qv = state.q.toLowerCase().trim();
    const list = rows.filter(test).filter((r) => !qv || `${r.subject} ${r.name} ${r.from} ${r.category} ${r.rule}`.toLowerCase().includes(qv));
    const opts = (group, items) => `<optgroup label="${group}">${items.map(([id, l, , tst]) => `<option value="${esc(id)}" ${state.box === id ? "selected" : ""}>${esc(l)} (${rows.filter(tst).length})</option>`).join("")}</optgroup>`;
    let day = "";
    const items = list
      .slice(0, state.shown)
      .map((r) => {
        const d = dayLabel(r.time);
        const head = d !== day ? `<li class="day" aria-hidden="true">${esc((day = d))}</li>` : "";
        const picked = state.sel.has(r.i);
        const av = r.selectable
          ? `<button class="av" role="checkbox" aria-checked="${picked}" data-pick="${r.i}" aria-label="Auswählen: ${esc(r.subject)}">${picked ? ico("check") : esc(initials(r.name))}</button>`
          : `<span class="av" aria-hidden="true">${esc(initials(r.name))}</span>`;
        return `${head}<li class="m ${state.open === r.i ? "open" : ""} ${picked ? "picked" : ""}">
            ${av}
            <button class="mitem" data-open="${r.i}" aria-current="${state.open === r.i}" aria-label="${esc(`${r.name}, ${r.subject}, ${d} ${clock(r.time)}`)}">
              <span class="r1"><span class="from">${esc(r.name)}</span><span class="time">${esc(d === "Heute" ? clock(r.time) : d === "Gestern" ? `Gestern` : new Date(r.time).toLocaleDateString("de-DE"))}</span></span>
              <span class="subj">${esc(r.subject)}</span>
              <span class="r3">${res(r)}<span class="where">${ico(folderIcon(r.folder))}${esc(folderName(r.folder))}</span></span>
            </button>
          </li>`;
      })
      .join("");
    const more = list.length > state.shown ? `<div class="lempty"><button class="secondary small" data-act="more">Weitere ${Math.min(25, list.length - state.shown)} anzeigen</button></div>` : "";
    const selbar = state.sel.size
      ? `<div class="selbar"><strong>${state.sel.size} ausgewählt</strong><span class="grow"></span><button class="link small" data-act="sel-clear">Aufheben</button><button class="pill" data-act="rerate">${ico("refresh")}Neu bewerten</button></div>`
      : "";
    return `<div class="listpane">
        <div class="lhead">
          <div class="ttl"><h2>${esc(label)}</h2><span class="cnt">${list.length}</span></div>
          <div class="lrow">
            <select class="fsel boxsel" data-boxsel aria-label="Ansicht">${opts("Ergebnis", KINDS.filter(([id, , , t]) => id === "all" || rows.some(t)))}${opts("Liegt jetzt in", FOLDERS)}<optgroup label="Technik"><option value="runs">Durchgänge</option></optgroup></select>
            <label class="search">${ico("magnify")}<input type="search" data-q value="${esc(state.q)}" placeholder="Suchen" aria-label="Betreff oder Absender suchen"></label>
          </div>
          <div class="lstatus">${statusItems()}</div>
          ${lastErr ? `<div class="errline">${ico("alert-circle-outline")}<span>Letzter Fehler ${esc(clock(lastErr.started))}: ${esc(lastErr.errors[0])}</span><button data-act="runs">Durchgänge</button></div>` : ""}
          ${selbar}
        </div>
        <div class="lscroll">${items ? `<ul class="mlist" aria-label="Mails">${items}</ul>${more}` : `<div class="lempty">Keine Mails in dieser Ansicht.</div>`}</div>
      </div>`;
  }

  function drawReader() {
    const r = rows.find((x) => x.i === state.open);
    if (!r) return `<section class="reader" aria-label="Mail"><div class="rempty">${ico("email-open-outline")}<span>Wähle eine Mail, um zu sehen,<br>was Regeln und KI mit ihr gemacht haben.</span></div></section>`;
    const ev = timeline(r);
    const steps = ev.map((e, i) => el._tlStep(e, i === ev.length - 1)).join("");
    const canRerate = r.selectable && ai?.status?.active;
    return `<section class="reader" aria-label="Mail">
        <div class="rtop"><button class="back" data-act="back">${ico("chevron-left")}${esc(view()[1])}</button><span class="grow"></span>
          ${canRerate ? `<button class="secondary small ib" data-act="rerate-one">${ico("refresh")}Neu bewerten</button>` : ""}</div>
        <div class="rbody">
          <div class="rhead">
            <h2 tabindex="-1" id="r-title">${esc(r.subject)}</h2>
            <span class="av" aria-hidden="true">${esc(initials(r.name))}</span>
            <span class="who"><strong>${esc(r.name)}</strong><small>${esc(r.from)}</small></span>
            <span class="date">${esc(fmtDateTime(plus(r.time, -40)))}</span>
            <div class="chips">${res(r)}<span class="where">${ico(folderIcon(r.folder))}${esc(folderName(r.folder))}</span></div>
          </div>
          <h3 class="sect">Verlauf</h3>
          <ol class="tl">${steps}</ol>
        </div>
        <div class="rfoot">Verknüpft über die Message-ID der Mail · alles bleibt lokal in Home Assistant</div>
      </section>`;
  }

  function drawActivity() {
    if (state.tab !== "aktivitaet") return void (aroot.innerHTML = "");
    // keep focus and scroll positions across the redraw
    const a = aroot.activeElement;
    const focus = a ? ["data-open", "data-pick", "data-box", "data-q", "data-boxsel", "data-act"].map((k) => (a.hasAttribute(k) ? `[${k}="${a.getAttribute(k)}"]` : "")).find(Boolean) : null;
    const caret = a?.selectionStart;
    const scroll = [aroot.querySelector(".lscroll")?.scrollTop, aroot.querySelector(".rbody")?.scrollTop];
    if (state.box === "runs") {
      aroot.innerHTML = `<style>${UI_STYLE}${STYLE}${MC_CSS}</style><div class="content widgets" style="padding-bottom:0"><section class="widget w-full"><div class="card"><div class="runsbar">
          <button class="secondary small ib" data-act="back-runs">${ico("chevron-left")}Zurück zu den Mails</button><span class="muted">Durchgänge: die technische Sicht für die Fehlersuche.</span></div></div></section></div>`;
    } else {
      aroot.innerHTML = `<style>${UI_STYLE}${STYLE}${MC_CSS}</style><div class="content widgets" style="padding-bottom:0"><section class="widget w-full"><div class="mcwrap">
          <div class="mc ${state.reading ? "reading" : ""}">${drawRail()}${drawList()}${drawReader()}</div></div></section></div>`;
    }
    if (focus) {
      const n = aroot.querySelector(focus);
      n?.focus({ preventScroll: true });
      if (n && caret != null && n.setSelectionRange) n.setSelectionRange(caret, caret);
    }
    const [ls, rs] = scroll;
    if (ls != null && aroot.querySelector(".lscroll")) aroot.querySelector(".lscroll").scrollTop = ls;
    if (rs != null && aroot.querySelector(".rbody") && !state.jumped) aroot.querySelector(".rbody").scrollTop = rs;
    state.jumped = false;
    bind();
  }

  function open(i) {
    state.open = i;
    state.reading = true;
    state.jumped = true;
    draw();
    // on a phone the mail replaces the list: start at its top, with the focus on its subject
    if (aroot.querySelector(".rtop .back")?.offsetParent) {
      aroot.host.scrollIntoView({ block: "start" });
      aroot.querySelector("#r-title")?.focus({ preventScroll: true });
    }
  }

  // a new view shows its newest mail (wide screens) – never a mail that is not in the list
  function switchBox(box) {
    state.box = box;
    state.shown = 25;
    state.reading = false;
    const test = (VIEWS.find(([id]) => id === box) || [])[3];
    const wide = !aroot.querySelector(".rtop .back")?.offsetParent;
    state.open = test && wide ? (rows.find(test)?.i ?? null) : null;
    draw();
  }

  function bind() {
    const on = (sel, fn, type = "click") => aroot.querySelectorAll(sel).forEach((n) => n.addEventListener(type, (ev) => fn(n, ev)));
    on("[data-goto]", (b) => goto(b.dataset.goto));
    on("[data-box]", (b) => switchBox(b.dataset.box));
    on("[data-boxsel]", (s) => switchBox(s.value), "change");
    on('[data-act="runs"]', () => ((state.box = "runs"), draw()));
    on('[data-act="back-runs"]', () => ((state.box = "all"), draw()));
    on('[data-act="more"]', () => ((state.shown += 25), draw()));
    on('[data-act="sel-clear"]', () => (state.sel.clear(), draw()));
    on('[data-act="rerate"]', () => el._rerate({ messages: [...state.sel].map((i) => ({ message_id: `<draft-${i}@example>` })) }));
    on('[data-act="rerate-one"]', () => el._rerate({ messages: [{ message_id: `<draft-${state.open}@example>` }] }));
    on('[data-act="back"]', () => {
      state.reading = false;
      draw();
      aroot.querySelector(`[data-open="${state.open}"]`)?.focus();
      aroot.querySelector(`[data-open="${state.open}"]`)?.scrollIntoView({ block: "center" });
    });
    on("[data-pick]", (b) => {
      const i = Number(b.dataset.pick);
      if (state.sel.has(i)) state.sel.delete(i);
      else state.sel.add(i);
      draw();
    });
    on("[data-open]", (b) => open(Number(b.dataset.open)));
    on("[data-q]", (inp) => ((state.q = inp.value), (state.shown = 25), draw()), "input");
    // arrow keys move through the list like in a mail program
    on(
      ".mlist",
      (list, ev) => {
        if (!["ArrowDown", "ArrowUp"].includes(ev.key) || !ev.target.matches("[data-open]")) return;
        const all = [...list.querySelectorAll("[data-open]")];
        const next = all[all.indexOf(ev.target) + (ev.key === "ArrowDown" ? 1 : -1)];
        if (!next) return;
        ev.preventDefault();
        next.focus();
        next.scrollIntoView({ block: "nearest" });
        if (!aroot.querySelector(".rtop .back")?.offsetParent) open(Number(next.dataset.open));
      },
      "keydown"
    );
  }

  function draw() {
    const part = state.tab === "aktivitaet" ? (state.box === "runs" ? "runs" : "aktivitaet") : state.tab;
    sheet.replaceSync(PANEL_CSS.common + PANEL_CSS[part]);
    drawChrome();
    drawActivity();
  }

  // wide screens start with the newest mail open, like a mail program
  if (innerWidth > 720 && rows.length) state.open = rows[0].i;
  draw();
}
