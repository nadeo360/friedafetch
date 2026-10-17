/* Frieda – Konten, Freigaben und Aktivität (ohne Build-Schritt, ohne Abhängigkeiten). */

const ICON_URL = new URL("icon.svg", import.meta.url).href;


const I18N = {
  de: {
    title: "Frieda",
    checked: "geprüft",
    matched: "Treffer",
    loading: "Lade …",
    noAccount: "Kein iCloud-Konto eingerichtet oder Mail-Tools deaktiviert.",
    triggerAuto: "automatisch",
    triggerManual: "manuell",
    accounts: "Konten",
    accountReadOnly: "Nur-Lesen",
    accountNoMail: "Mail-Tools deaktiviert",
    switchHint: "Regeln, Läufe und Berichte gelten je Konto. Wähle oben das Konto.",
    approvals: "Freigaben",
    approvalsHint: "Aktionen, die auf deine Freigabe warten. Freigegebene Aktionen werden sofort ausgeführt.",
    noApprovals: "Keine offenen Freigaben.",
    approve: "Freigeben",
    deny: "Ablehnen",
    pending: "wartet",
    executed: "ausgeführt",
    failed: "fehlgeschlagen",
    denied: "abgelehnt",
    expired: "abgelaufen",
    validUntil: "gültig bis",
    decidedBy: "entschieden von",
    recentDecisions: "Letzte Entscheidungen",
    approvalsOff: "Freigaben sind für dieses Konto nicht aktiviert (Optionen → Freigaben).",
    reason_send: "E-Mail senden",
    reason_delete: "Löschen",
    reason_mass: "Massenaktion",
    activity: "Aktivität",
    activityHint: "Schreibende Aktionen der KI-Clients und Regelläufe, neueste zuerst.",
    noActivity: "Noch keine Aktionen protokolliert.",
    clearLog: "Protokoll leeren",
    confirmClear: "Aktivitätsprotokoll wirklich leeren?",
    colTime: "Zeit",
    colWho: "Client / Benutzer",
    colTool: "Tool",
    colDetails: "Details",
    colResult: "Ergebnis",
    resOk: "ok",
    resError: "Fehler",
    resBlocked: "blockiert",
    quota: "Kontingente (letzte Stunde)",
    quotaMailModify: "Mail verschieben/löschen/markieren",
    quotaMailSend: "Mails senden",
    quotaItemDelete: "Termine/Kontakte/Notizen löschen",
    unlimited: "unbegrenzt",
    showMore: "Mehr anzeigen",
    filter: "Filter",
    filterReset: "Filter zurücksetzen",
    filterCount: "{0} von {1} Einträgen",
    filterAll: "alle",
    filterPh: "filtern …",
    numPh: "z. B. >0",
    whoRules: "Regeln",
    accountNoSend: "kein Senden",
    accountNoDelete: "kein Löschen",
    extMail: "Frieda Postfach",
    extMailHint: "Posteingangsregeln, Push und Tagesüberblick bietet die Erweiterung „Frieda Postfach“ (eigene Integration, nutzt diese Verbindung).",
    triggerPush: "Push",
  },
  en: {
    title: "Frieda",
    checked: "checked",
    matched: "matched",
    loading: "Loading …",
    noAccount: "No iCloud account configured or mail tools disabled.",
    triggerAuto: "automatic",
    triggerManual: "manual",
    accounts: "Accounts",
    accountReadOnly: "read-only",
    accountNoMail: "mail tools disabled",
    switchHint: "Rules, runs and reports are per account. Pick the account above.",
    approvals: "Approvals",
    approvalsHint: "Actions waiting for your approval. Approved actions run immediately.",
    noApprovals: "No pending approvals.",
    approve: "Approve",
    deny: "Deny",
    pending: "pending",
    executed: "executed",
    failed: "failed",
    denied: "denied",
    expired: "expired",
    validUntil: "valid until",
    decidedBy: "decided by",
    recentDecisions: "Recent decisions",
    approvalsOff: "Approvals are not enabled for this account (options → Approvals).",
    reason_send: "send e-mail",
    reason_delete: "delete",
    reason_mass: "mass action",
    activity: "Activity",
    activityHint: "Writing actions of AI clients and rule runs, newest first.",
    noActivity: "No actions logged yet.",
    clearLog: "Clear log",
    confirmClear: "Really clear the activity log?",
    colTime: "Time",
    colWho: "Client / user",
    colTool: "Tool",
    colDetails: "Details",
    colResult: "Result",
    resOk: "ok",
    resError: "error",
    resBlocked: "blocked",
    quota: "Quotas (last hour)",
    quotaMailModify: "move/delete/flag mail",
    quotaMailSend: "send mail",
    quotaItemDelete: "delete events/contacts/notes",
    unlimited: "unlimited",
    showMore: "Show more",
    filter: "Filter",
    filterReset: "Reset filters",
    filterCount: "{0} of {1} entries",
    filterAll: "all",
    filterPh: "filter …",
    numPh: "e.g. >0",
    whoRules: "Rules",
    accountNoSend: "no sending",
    accountNoDelete: "no deleting",
    extMail: "Frieda Postfach",
    extMailHint: "Inbox rules, push and the daily overview come with the extension “Frieda Postfach” (separate integration, uses this connection).",
    triggerPush: "push",
  },
};

const trigLabel = (t, trig) => (trig === "auto" ? t.triggerAuto : trig === "push" ? t.triggerPush : t.triggerManual);

const fmt = (str, ...args) => String(str).replace(/\{(\d+)\}/g, (_, i) => args[Number(i)]);

// Numeric column filter: "5", "=5", ">0", ">=2", "<10", "<=3".
const numMatch = (value, query) => {
  const m = String(query).trim().match(/^(>=|<=|>|<|=)?\s*(-?\d+(?:[.,]\d+)?)$/);
  if (!m) return String(value).includes(String(query).trim());
  const v = Number(value);
  const q = Number(m[2].replace(",", "."));
  if (isNaN(v)) return false;
  return { ">": v > q, "<": v < q, ">=": v >= q, "<=": v <= q, "=": v === q }[m[1] || "="];
};

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);


// Parses ISO timestamps, including offsets without colon (+0200) that Safari rejects.
const parseTime = (iso) => (iso ? new Date(String(iso).replace(/([+-]\d{2})(\d{2})$/, "$1:$2")) : null);
const fmtDateTime = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleString() : "–";
};
const fmtClock = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "–";
};

// Adds data-label attributes to the cells of each row so the CSS can stack tables on phones.
const withLabels = (rowsHtml, labels) =>
  rowsHtml
    .split("<tr")
    .map((chunk, idx) => {
      if (idx === 0) return chunk;
      let i = 0;
      return chunk.replace(/<td(?![^>]*data-label)/g, () => `<td data-label="${esc(labels[i++] ?? "")}"`);
    })
    .join("<tr");

const STYLE = `
  :host { display: block; height: 100%; color: var(--primary-text-color); background: var(--primary-background-color); }
  .toolbar { display: flex; align-items: center; gap: 12px; height: 56px; padding: 0 16px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); font-size: 20px; }
  .toolbar .grow { flex: 1; }
  .toolbar select { background: rgba(255,255,255,.15); color: inherit; border: 1px solid rgba(255,255,255,.4); border-radius: 6px; padding: 4px 8px; font-size: 14px; }
  .content { padding: 16px; max-width: 1100px; margin: 0 auto; display: grid; gap: 16px; }
  .card { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0,0,0,.14)); border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0)); padding: 16px; }
  .card h2 { margin: 0 0 12px; font-size: 18px; font-weight: 500; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .card h2 .grow { flex: 1; }
  button { font: inherit; border: none; border-radius: 6px; padding: 8px 14px; cursor: pointer; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.secondary { background: transparent; color: var(--primary-color); border: 1px solid var(--primary-color); }
  button.danger { background: var(--error-color, #db4437); }
  button.icon { background: transparent; color: var(--secondary-text-color); padding: 4px 8px; font-size: 16px; }
  button:disabled { opacity: .5; cursor: default; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--divider-color, #e0e0e0); vertical-align: top; }
  th { color: var(--secondary-text-color); font-weight: 500; }
  .muted { color: var(--secondary-text-color); font-size: 13px; }
  .chip { display: inline-block; padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); font-size: 12px; margin: 2px 4px 2px 0; }
  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
  .row label { min-width: 170px; color: var(--secondary-text-color); font-size: 14px; }
  input[type=text], select { font: inherit; padding: 7px 10px; border: 1px solid var(--divider-color, #ccc); border-radius: 6px; background: var(--card-background-color, #fff); color: var(--primary-text-color); min-width: 160px; }
  input[type=text].grow { flex: 1; min-width: 200px; }
  .error { background: color-mix(in srgb, var(--error-color, #db4437) 12%, transparent); color: var(--error-color, #db4437); padding: 10px 12px; border-radius: 8px; }
  .ok { background: color-mix(in srgb, var(--success-color, #43a047) 12%, transparent); padding: 10px 12px; border-radius: 8px; }
  .actionsbar { display: flex; gap: 8px; flex-wrap: wrap; }
  .tabs { display: flex; gap: 10px; flex-wrap: wrap; }
  .tab { flex: 1 1 240px; text-align: left; background: var(--card-background-color, #fff); color: var(--primary-text-color); border: 2px solid var(--divider-color, #e0e0e0); border-radius: var(--ha-card-border-radius, 12px); padding: 12px 14px; display: grid; gap: 4px; }
  .tab.active { border-color: var(--primary-color); box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 18%, transparent); }
  .tab .label { font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 8px; }
  .tab .label .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--success-color, #43a047); display: inline-block; }
  .tab .label .dot.off { background: var(--secondary-text-color); }
  .tab .meta { color: var(--secondary-text-color); font-size: 12.5px; }
  .tab .badges { display: flex; gap: 6px; flex-wrap: wrap; }
  .badge { font-size: 11px; padding: 1px 7px; border-radius: 8px; background: var(--secondary-background-color, #eee); color: var(--secondary-text-color); }
  .badge.warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 20%, transparent); color: var(--primary-text-color); }
  .scroll { overflow-x: auto; }
  code { font-size: 12px; background: var(--secondary-background-color, #f0f0f0); padding: 1px 5px; border-radius: 4px; }
  .info { background: color-mix(in srgb, var(--primary-color) 10%, transparent); padding: 10px 12px; border-radius: 8px; font-size: 13px; }
  .toolbar img { width: 28px; height: 28px; border-radius: 7px; }
  table.stack { width: 100%; }
  .fbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
  .fbar .grow { flex: 1; }
  button.link { background: none; color: var(--primary-color); padding: 2px 4px; min-height: 0; }
  button.ftoggle { display: none; }
  thead tr.filters th { padding: 4px 6px 8px; font-weight: 400; }
  thead tr.filters input, thead tr.filters select { width: 100%; min-width: 0; box-sizing: border-box; padding: 4px 6px; font-size: 12.5px; }
  thead tr.filters .active { border-color: var(--primary-color); box-shadow: 0 0 0 1px var(--primary-color); }
  tr.fhide { display: none !important; }
  @media (max-width: 760px) {
    .toolbar { height: 52px; padding: 0 10px; font-size: 18px; }
    .content { padding: 10px; gap: 10px; }
    .card { padding: 12px; }
    .card h2 { font-size: 17px; }
    .card h2 button { flex: 1 1 auto; }
    table.stack thead { display: block; }
    table.stack thead tr.head { display: none; }
    table.stack thead tr.filters { display: none; }
    .ftable.fopen table.stack thead tr.filters { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; border: none; padding: 0; margin-bottom: 10px; background: none; }
    table.stack thead tr.filters th { display: block; padding: 0; border: none; }
    button.ftoggle { display: inline-block; }
    table.stack, table.stack tbody, table.stack tr, table.stack td { display: block; width: 100%; box-sizing: border-box; }
    table.stack tr { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 8px 10px; margin-bottom: 10px; background: var(--card-background-color, #fff); }
    table.stack td { border: none; padding: 4px 0; white-space: normal !important; }
    table.stack td[data-label]::before { content: attr(data-label); display: block; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; color: var(--secondary-text-color); margin-bottom: 2px; }
    table.stack td[data-label=""]::before, table.stack td:not([data-label])::before { display: none; }
    table.stack td.actions { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; padding-top: 8px; }
    .scroll { overflow: visible; }
    .actionsbar { flex-direction: column; }
    .actionsbar button { width: 100%; }
    .tabs .tab { flex-basis: 100%; }
    button { min-height: 44px; }
    button.icon { min-width: 44px; min-height: 44px; font-size: 18px; }
    .row { gap: 4px; }
    .row label { min-width: 100%; }
    .row label:has(input[type=checkbox]) { display: flex; align-items: center; gap: 10px; min-height: 44px; }
    input[type=checkbox] { width: 22px; height: 22px; }
  }
`;

class ICloudMcpRulesPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._s = {
      accounts: [],
      entryId: null,
      error: null,
      notice: null,
      audit: [],
      quota: {},
      approvals: null,
      auditLimit: 25,
      filters: {},
      filterOpen: {},
      busy: false,
      loaded: false,
    };
  }

  connectedCallback() {
    this._onVisible = () => {
      if (document.visibilityState === "visible") this._autoRefresh();
    };
    document.addEventListener("visibilitychange", this._onVisible);
    this._timer = setInterval(() => this._autoRefresh(), 30000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    document.removeEventListener("visibilitychange", this._onVisible);
  }

  async _autoRefresh() {
    const s = this._s;
    if (!this._hass || !s.loaded || !s.entryId || s.busy || document.visibilityState !== "visible") return;
    const active = this.shadowRoot.activeElement;
    if (active && ["SELECT", "INPUT", "TEXTAREA"].includes(active.tagName)) return;
    try {
      await this._reload();
      this._render();
    } catch (err) {
      /* keep the last state on transient errors */
    }
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._init();
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) {
      menu.hass = hass;
      menu.narrow = this._narrow;
    }
  }
  set narrow(v) {
    this._narrow = v;
  }
  set panel(p) {
    this._panel = p;
  }

  get t() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").toLowerCase();
    return lang.startsWith("de") ? I18N.de : I18N.en;
  }

  async _ws(msg) {
    return this._hass.callWS(msg);
  }

  async _init() {
    this._render();
    try {
      const { accounts } = await this._ws({ type: "friedafetch/accounts" });
      this._s.accounts = accounts;
      this._s.entryId = accounts[0]?.entry_id || null;
      if (this._s.entryId) await this._reload();
    } catch (err) {
      this._s.error = err.message || String(err);
    }
    this._s.loaded = true;
    this._render();
  }

  async _reload() {
    try {
      await this._loadAccounts();
      await this._loadAudit();
      await this._loadApprovals();
    } catch (err) {
      /* audit and approvals are optional */
    }
  }

  async _call(fn) {
    this._s.busy = true;
    this._s.error = null;
    this._render();
    try {
      await fn();
    } catch (err) {
      this._s.error = err.message || String(err);
    }
    this._s.busy = false;
    this._render();
  }

  async _loadAccounts() {
    const { accounts } = await this._ws({ type: "friedafetch/accounts" });
    this._s.accounts = accounts;
    if (!accounts.some((a) => a.entry_id === this._s.entryId)) this._s.entryId = accounts[0]?.entry_id || null;
  }

  async _loadApprovals() {
    const res = await this._ws({ type: "friedafetch/approvals/list", entry_id: this._s.entryId });
    this._s.approvals = res;
  }

  async _decide(requestId, decision) {
    await this._call(async () => {
      await this._ws({ type: "friedafetch/approvals/decide", entry_id: this._s.entryId, request_id: requestId, decision });
      await this._loadApprovals();
      await this._loadAudit();
      await this._loadAccounts();
    });
  }

  _renderApprovals() {
    const t = this.t;
    const a = this._s.approvals;
    if (!a) return "";
    const status = (st) => `<span class="badge ${st === "pending" ? "warn" : ""}">${esc(t[st] || st)}</span>`;
    const reason = (r) => esc(t[`reason_${r}`] || r);
    const pending = (a.requests || []).filter((r) => r.status === "pending");
    const decided = (a.requests || []).filter((r) => r.status !== "pending").slice(0, 10);
    const row = (r, withButtons) => `<tr>
        <td style="white-space:nowrap">${esc(fmtDateTime(r.created))}</td>
        <td>${esc(r.client || "–")}</td>
        <td><code>${esc(r.tool)}</code><div class="muted">${reason(r.reason)}</div></td>
        <td>${esc(r.summary)}${r.error ? `<div class="muted">${esc(r.error)}</div>` : ""}</td>
        <td>${status(r.status)}${withButtons ? `<div class="muted">${esc(t.validUntil)} ${esc(fmtClock(r.expires))}</div>` : r.decided_by ? `<div class="muted">${esc(t.decidedBy)} ${esc(r.decided_by)}</div>` : ""}</td>
        <td class="actions" style="white-space:nowrap">${withButtons ? `<button data-action="approve" data-id="${esc(r.id)}" ${this._s.busy ? "disabled" : ""}>${esc(t.approve)}</button> <button class="danger" data-action="deny" data-id="${esc(r.id)}" ${this._s.busy ? "disabled" : ""}>${esc(t.deny)}</button>` : ""}</td>
      </tr>`;
    const table = (rows) => `<div class="scroll"><table class="stack"><thead><tr><th>${esc(t.colTime)}</th><th>${esc(t.colWho)}</th><th>${esc(t.colTool)}</th><th>${esc(t.colDetails)}</th><th>${esc(t.colResult)}</th><th></th></tr></thead><tbody>${withLabels(rows, [t.colTime, t.colWho, t.colTool, t.colDetails, t.colResult, ""])}</tbody></table></div>`;
    return `<div class="card">
      <h2><span class="grow">${esc(t.approvals)}${pending.length ? ` <span class="badge warn">${pending.length}</span>` : ""}</span></h2>
      <p class="muted" style="margin:0 0 10px">${esc(a.enabled ? t.approvalsHint : t.approvalsOff)}</p>
      ${a.enabled ? (pending.length ? table(pending.map((r) => row(r, true)).join("")) : `<p class="muted">${esc(t.noApprovals)}</p>`) : ""}
      ${decided.length ? `<h3 class="muted">${esc(t.recentDecisions)}</h3>${table(decided.map((r) => row(r, false)).join(""))}` : ""}
    </div>`;
  }

  async _loadAudit() {
    const res = await this._ws({ type: "friedafetch/audit/list", entry_id: this._s.entryId, limit: this._s.auditLimit });
    this._s.audit = res.entries || [];
    this._s.quota = res.quota || {};
  }

  // ------------------------------------------------------- filter tables
  // cols: [{ label, filter: "text" | "select" | "num" }]; rows: [[{ html, v }, ...]]
  _filterTable(key, cols, rows, emptyText) {
    const t = this.t;
    if (!rows.length) return `<p class="muted">${esc(emptyText)}</p>`;
    const f = this._s.filters[key] || {};
    const active = Object.values(f).some((v) => v);
    const filterCell = (c, i) => {
      const val = f[i] || "";
      const cls = val ? "active" : "";
      const aria = `aria-label="${esc(t.filter + ": " + c.label)}"`;
      if (c.filter === "select") {
        const values = [...new Set(rows.map((r) => r[i].v).filter((v) => v !== ""))].sort((a, b) => a.localeCompare(b));
        return `<th><select class="${cls}" data-ftable="${key}" data-col="${i}" ${aria}><option value="">${esc(c.label)}: ${esc(t.filterAll)}</option>${values
          .map((v) => `<option value="${esc(v)}" ${v === val ? "selected" : ""}>${esc(c.label)}: ${esc(v)}</option>`)
          .join("")}</select></th>`;
      }
      const ph = c.filter === "num" ? `${c.label} (${t.numPh})` : `${c.label} ${t.filterPh}`;
      return `<th><input type="text" class="${cls}" data-ftable="${key}" data-col="${i}" data-kind="${c.filter || "text"}" value="${esc(val)}" placeholder="${esc(ph)}" ${aria}></th>`;
    };
    const body = rows
      .map((r) => `<tr>${r.map((c, i) => `<td data-label="${esc(cols[i].label)}" data-v="${esc(c.v)}"${c.cls ? ` class="${c.cls}"` : ""}>${c.html}</td>`).join("")}</tr>`)
      .join("");
    return `<div class="ftable ${this._s.filterOpen[key] || active ? "fopen" : ""}" data-ftable-wrap="${key}">
      <div class="fbar"><span class="muted fcount"></span><span class="grow"></span>
        <button class="link ftoggle" data-action="filter-toggle" data-table="${key}">${esc(t.filter)}${active ? " •" : ""}</button>
        <button class="link" data-action="filter-reset" data-table="${key}" ${active ? "" : "hidden"}>${esc(t.filterReset)}</button></div>
      <div class="scroll"><table class="stack"><thead><tr class="head">${cols.map((c) => `<th>${esc(c.label)}</th>`).join("")}</tr>
        <tr class="filters">${cols.map(filterCell).join("")}</tr></thead><tbody>${body}</tbody></table></div></div>`;
  }

  _applyFilters(key) {
    const wrap = this.shadowRoot.querySelector(`[data-ftable-wrap="${key}"]`);
    if (!wrap) return;
    const f = this._s.filters[key] || {};
    const kinds = {};
    wrap.querySelectorAll("[data-ftable]").forEach((el) => (kinds[el.dataset.col] = el.tagName === "SELECT" ? "select" : el.dataset.kind));
    const rows = [...wrap.querySelectorAll("tbody tr")];
    let shown = 0;
    rows.forEach((tr) => {
      const ok = Object.entries(f).every(([col, q]) => {
        if (!q) return true;
        const v = tr.cells[Number(col)]?.dataset.v ?? "";
        if (kinds[col] === "select") return v === q;
        if (kinds[col] === "num") return numMatch(v, q);
        return v.toLowerCase().includes(String(q).toLowerCase().trim());
      });
      tr.classList.toggle("fhide", !ok);
      if (ok) shown++;
    });
    const active = Object.values(f).some((v) => v);
    const count = wrap.querySelector(".fcount");
    if (count) count.textContent = active ? fmt(this.t.filterCount, shown, rows.length) : "";
    const reset = wrap.querySelector('[data-action="filter-reset"]');
    if (reset) reset.hidden = !active;
    const toggle = wrap.querySelector('[data-action="filter-toggle"]');
    if (toggle) toggle.textContent = this.t.filter + (active ? " •" : "");
    wrap.querySelectorAll("[data-ftable]").forEach((el) => el.classList.toggle("active", !!f[el.dataset.col]));
  }

  async _clearAudit() {
    if (!confirm(this.t.confirmClear)) return;
    await this._call(async () => {
      await this._ws({ type: "friedafetch/audit/clear", entry_id: this._s.entryId });
      await this._loadAudit();
    });
  }

  _renderActivity() {
    const t = this.t;
    const s = this._s;
    const q = s.quota || {};
    const quotaRow = (key, label) => {
      const v = q[key];
      if (!v) return "";
      const lim = v.limit ? `${v.used} / ${v.limit}` : `${v.used} / ${t.unlimited}`;
      const warn = v.limit && v.used >= v.limit * 0.8;
      return `<span class="badge ${warn ? "warn" : ""}">${esc(label)}: ${esc(lim)}</span>`;
    };
    const who = (e) => {
      if (e.tool === "icloud_run_rules" || String(e.client || "").startsWith("rules")) {
        const trig = e.details?.trigger || e.params?.trigger || (e.client === "rules (auto)" ? "auto" : e.client === "rules (push)" ? "push" : null);
        return [t.whoRules, trig ? trigLabel(t, trig) : null, e.user].filter(Boolean).join(" · ");
      }
      return [e.client, e.user].filter(Boolean).join(" · ") || "–";
    };
    const details = (e) => {
      const d = e.details || {};
      const p = e.params || {};
      const parts = [];
      if (p.subject) parts.push(`„${esc(p.subject)}“`);
      if (p.to) parts.push(`→ ${esc([].concat(p.to).join(", "))}`);
      if (p.target_mailbox) parts.push(`→ ${esc(p.target_mailbox)}`);
      if (p.summary) parts.push(`„${esc(p.summary)}“`);
      if (p.name) parts.push(`„${esc(p.name)}“`);
      if (d.count) parts.push(`${d.count}×`);
      else if (p.uids) parts.push(`${[].concat(p.uids).length}×`);
      else if (p.uid) parts.push(`UID ${esc(p.uid)}`);
      if (d.matched !== undefined) parts.push(`${d.checked} ${esc(t.checked)}, ${d.matched} ${esc(t.matched)}`);
      if (e.error) parts.push(`<span class="muted">${esc(e.error)}</span>`);
      return parts.join(" ");
    };
    const resText = (r) => (r === "ok" ? t.resOk : r === "blocked" ? t.resBlocked : t.resError);
    const rows = s.audit.map((e) => {
      const timeText = fmtDateTime(e.time);
      const whoText = who(e);
      const det = details(e);
      const res = resText(e.result);
      return [
        { html: `<span style="white-space:nowrap">${esc(timeText)}</span>`, v: timeText },
        { html: esc(whoText), v: whoText },
        { html: `<code>${esc(e.tool)}</code>`, v: e.tool || "" },
        { html: det, v: det.replace(/<[^>]*>/g, "").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'") },
        { html: `<span class="badge ${e.result === "ok" ? "" : "warn"}">${esc(res)}</span>`, v: res },
      ];
    });
    const cols = [
      { label: t.colTime, filter: "text" },
      { label: t.colWho, filter: "select" },
      { label: t.colTool, filter: "select" },
      { label: t.colDetails, filter: "text" },
      { label: t.colResult, filter: "select" },
    ];
    return `<div class="card">
      <h2><span class="grow">${esc(t.activity)}</span>
        <button class="secondary" data-action="audit-more" ${s.busy ? "disabled" : ""}>${esc(t.showMore)}</button>
        <button class="secondary" data-action="audit-clear" ${s.busy || !s.audit.length ? "disabled" : ""}>${esc(t.clearLog)}</button></h2>
      <p class="muted" style="margin:0 0 10px">${esc(t.activityHint)}</p>
      <div class="badges" style="margin-bottom:10px"><span class="muted" style="margin-right:6px">${esc(t.quota)}:</span>
        ${quotaRow("mail_modify", t.quotaMailModify)} ${quotaRow("mail_send", t.quotaMailSend)} ${quotaRow("item_delete", t.quotaItemDelete)}</div>
      ${this._filterTable("audit", cols, rows, t.noActivity)}
    </div>`;
  }

  async _switchAccount(entryId) {
    this._s.entryId = entryId;
    this._s.notice = null;
    await this._call(() => this._reload());
  }

  // ---------------------------------------------------------------- render
  _account() {
    return this._s.accounts.find((a) => a.entry_id === this._s.entryId) || null;
  }

  _renderAccounts() {
    const t = this.t;
    const s = this._s;
    if (!s.accounts.length) return "";
    const tabs = s.accounts
      .map((a) => {
        const active = a.entry_id === s.entryId;
        const badges = [
          a.read_only ? `<span class="badge warn">${esc(t.accountReadOnly)}</span>` : "",
          a.mail_enabled ? "" : `<span class="badge warn">${esc(t.accountNoMail)}</span>`,
          a.mail_enabled && !a.read_only && !a.allow_send ? `<span class="badge">${esc(t.accountNoSend)}</span>` : "",
          !a.read_only && !a.allow_delete ? `<span class="badge">${esc(t.accountNoDelete)}</span>` : "",
          a.approvals_enabled ? `<span class="badge">${esc(t.approvals)}${a.approvals_pending ? `: ${a.approvals_pending}` : ""}</span>` : "",
          (a.extensions || []).includes("mail") ? `<span class="badge">${esc(t.extMail)}</span>` : "",
        ].join("");
        return `<button class="tab ${active ? "active" : ""}" data-action="account" data-id="${esc(a.entry_id)}" aria-pressed="${active}">
          <span class="label"><span class="dot ${a.read_only ? "off" : ""}"></span>${esc(a.label)}</span>
          <span class="meta">${esc(a.apple_id || a.title)}</span>
          <span class="badges">${badges}</span>
        </button>`;
      })
      .join("");
    const hasMail = s.accounts.some((a) => (a.extensions || []).includes("mail"));
    return `<div class="card"><h2><span class="grow">${esc(t.accounts)}</span><span class="muted">${s.accounts.length}</span></h2>
      <div class="tabs">${tabs}</div>
      ${s.accounts.length > 1 ? `<p class="muted" style="margin:10px 0 0">${esc(t.switchHint)}</p>` : ""}
      ${hasMail ? "" : `<div class="info" style="margin-top:10px">${esc(t.extMailHint)}</div>`}</div>`;
  }

  _render() {
    const t = this.t;
    const s = this._s;
    const body = !s.loaded
      ? `<p class="muted">${esc(t.loading)}</p>`
      : !s.entryId
        ? `<div class="card"><p>${esc(t.noAccount)}</p></div>`
        : `
      ${s.error ? `<div class="error">${esc(s.error)}</div>` : ""}
      ${s.notice ? `<div class="ok">${esc(s.notice)}</div>` : ""}
      ${this._renderAccounts()}
      ${this._renderApprovals()}
      ${this._renderActivity()}`;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><img src="${esc(ICON_URL)}" alt=""><span>${esc(t.title)}</span><span class="grow"></span></div>
      <div class="content">${body}</div>`;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu && this._hass) {
      menu.hass = this._hass;
      menu.narrow = this._narrow;
    }
    this._bind();
    this._applyFilters("audit");
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-action]").forEach((el) => {
      const action = el.dataset.action;
      const handler = {
        "filter-toggle": () => {
          const key = el.dataset.table;
          this._s.filterOpen[key] = !this._s.filterOpen[key];
          this.shadowRoot.querySelector(`[data-ftable-wrap="${key}"]`)?.classList.toggle("fopen", this._s.filterOpen[key]);
        },
        "filter-reset": () => {
          const key = el.dataset.table;
          this._s.filters[key] = {};
          this.shadowRoot.querySelectorAll(`[data-ftable="${key}"]`).forEach((f) => (f.value = ""));
          this._applyFilters(key);
        },
        approve: () => this._decide(el.dataset.id, "approve"),
        deny: () => this._decide(el.dataset.id, "deny"),
        "audit-clear": () => this._clearAudit(),
        "audit-more": () => {
          this._s.auditLimit = Math.min(500, this._s.auditLimit + 50);
          this._call(() => this._loadAudit());
        },
      }[action];
      if (action === "account") {
        el.addEventListener("click", () => this._switchAccount(el.dataset.id));
      } else if (handler) {
        el.addEventListener("click", handler);
      }
    });
    root.querySelectorAll("[data-ftable]").forEach((el) => {
      const update = () => {
        const key = el.dataset.ftable;
        this._s.filters[key] = { ...(this._s.filters[key] || {}), [el.dataset.col]: el.value };
        this._applyFilters(key);
      };
      el.addEventListener(el.tagName === "SELECT" ? "change" : "input", update);
    });
  }
}

if (!customElements.get("friedafetch-panel")) {
  customElements.define("friedafetch-panel", ICloudMcpRulesPanel);
}
