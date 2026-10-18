/* Frieda – Überblick, Nutzung, Freigaben und Änderungsprotokoll (ohne Build-Schritt, ohne Abhängigkeiten). */

const ICON_URL = new URL("icon.svg", import.meta.url).href;

// Tool name -> [area, label (de), label (en), done (de), done (en)]
const TOOLS = {
  icloud_list_calendars: ["calendar", "Kalender auflisten", "List calendars"],
  icloud_list_events: ["calendar", "Termine abrufen", "List events"],
  icloud_get_event: ["calendar", "Termin lesen", "Read event"],
  icloud_create_event: ["calendar", "Termin anlegen", "Create event", "Termin angelegt", "Event created"],
  icloud_update_event: ["calendar", "Termin ändern", "Update event", "Termin geändert", "Event updated"],
  icloud_delete_event: ["calendar", "Termin löschen", "Delete event", "Termin gelöscht", "Event deleted"],
  icloud_find_free_time: ["calendar", "Freie Zeiten suchen", "Find free time"],
  icloud_search_contacts: ["contacts", "Kontakte suchen", "Search contacts"],
  icloud_get_contact: ["contacts", "Kontakt lesen", "Read contact"],
  icloud_create_contact: ["contacts", "Kontakt anlegen", "Create contact", "Kontakt angelegt", "Contact created"],
  icloud_update_contact: ["contacts", "Kontakt ändern", "Update contact", "Kontakt geändert", "Contact updated"],
  icloud_delete_contact: ["contacts", "Kontakt löschen", "Delete contact", "Kontakt gelöscht", "Contact deleted"],
  icloud_upcoming_birthdays: ["contacts", "Geburtstage abrufen", "Upcoming birthdays"],
  icloud_find_duplicate_contacts: ["contacts", "Doppelte Kontakte finden", "Find duplicate contacts"],
  icloud_list_mailboxes: ["mail", "Postfächer auflisten", "List mailboxes"],
  icloud_search_mail: ["mail", "Mails suchen", "Search mail"],
  icloud_get_mail: ["mail", "Mail lesen", "Read mail"],
  icloud_send_mail: ["mail", "Mail senden", "Send mail", "Mail gesendet", "Mail sent"],
  icloud_mark_mail: ["mail", "Mails markieren", "Flag mail", "Mails markiert", "Mail flagged"],
  icloud_move_mail: ["mail", "Mails verschieben", "Move mail", "Mails verschoben", "Mail moved"],
  icloud_delete_mail: ["mail", "Mails löschen", "Delete mail", "Mails gelöscht", "Mail deleted"],
  icloud_mailbox_stats: ["mail", "Postfach analysieren", "Analyse mailbox"],
  icloud_unsubscribe: ["mail", "Newsletter abbestellen", "Unsubscribe", "Newsletter abbestellt", "Unsubscribed"],
  icloud_save_attachments: ["mail", "Anhänge speichern", "Save attachments", "Anhänge gespeichert", "Attachments saved"],
  icloud_list_notes: ["notes", "Notizen auflisten", "List notes"],
  icloud_get_note: ["notes", "Notiz lesen", "Read note"],
  icloud_create_note: ["notes", "Notiz anlegen", "Create note", "Notiz angelegt", "Note created"],
  icloud_update_note: ["notes", "Notiz ändern", "Update note", "Notiz geändert", "Note updated"],
  icloud_delete_note: ["notes", "Notiz löschen", "Delete note", "Notiz gelöscht", "Note deleted"],
  icloud_approval_status: ["approvals", "Freigabestatus abfragen", "Approval status"],
  icloud_list_rules: ["rules", "Regeln auflisten", "List rules"],
  icloud_create_rule: ["rules", "Regel anlegen", "Create rule", "Regel angelegt", "Rule created"],
  icloud_update_rule: ["rules", "Regel ändern", "Update rule", "Regel geändert", "Rule updated"],
  icloud_delete_rule: ["rules", "Regel löschen", "Delete rule", "Regel gelöscht", "Rule deleted"],
  icloud_run_rules: ["rules", "Regeln anwenden", "Run rules", "Regeln angewendet", "Rules applied"],
  icloud_daily_overview: ["rules", "Tagesüberblick", "Daily overview"],
  friedafetch_mail_ai_sort: ["rules", "KI-Sortierung", "AI sorting", "Mails von KI einsortiert", "Mails sorted by AI"],
};

const AREA_ICON = {
  mail: "mdi:email-outline",
  calendar: "mdi:calendar-month-outline",
  contacts: "mdi:account-box-outline",
  notes: "mdi:note-text-outline",
  rules: "mdi:email-fast-outline",
  approvals: "mdi:shield-check-outline",
  other: "mdi:tools",
};

// Texts and styles live in their own modules; they are loaded with the same ?v= as this file so that
// a browser never combines a new panel with old texts after an update.
const VERSION_QUERY = new URL(import.meta.url).search;
const [{ I18N }, { STYLE }] = await Promise.all([import(`./i18n.js${VERSION_QUERY}`), import(`./styles.js${VERSION_QUERY}`)]);

const fmt = (str, ...args) => String(str).replace(/\{(\d+)\}/g, (_, i) => args[Number(i)]);

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Parses ISO timestamps, including offsets without colon (+0200) that Safari rejects.
const parseTime = (iso) => (iso ? new Date(String(iso).replace(/([+-]\d{2})(\d{2})$/, "$1:$2")) : null);
const fmtDateTime = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleString() : "–";
};
const fmtDate = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleDateString() : "–";
};
const fmtClock = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "–";
};
const fmtNum = (n) => Number(n || 0).toLocaleString();

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


class FriedaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._s = {
      accounts: [],
      entryId: null,
      error: null,
      overview: null,
      audit: [],
      quota: {},
      approvals: null,
      auditLimit: 50,
      filter: { q: "", area: "", result: "", source: "" },
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
    if (this.shadowRoot.querySelector(".ev details[open]")) return;
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

  get lang() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "en").toLowerCase();
    return lang.startsWith("de") ? "de" : "en";
  }

  get t() {
    return I18N[this.lang];
  }

  _toolLabel(name, done = false) {
    const info = TOOLS[name];
    if (!info) return name;
    const de = this.lang === "de";
    if (done && info[3]) return de ? info[3] : info[4];
    return de ? info[1] : info[2];
  }

  _area(name) {
    return TOOLS[name]?.[0] || "other";
  }

  _rel(iso) {
    const t = this.t;
    const d = parseTime(iso);
    if (!d || isNaN(d)) return "–";
    const min = Math.round((Date.now() - d.getTime()) / 60000);
    if (min < 1) return t.justNow;
    if (min < 60) return fmt(t.minAgo, min);
    if (min < 24 * 60) return fmt(t.hAgo, Math.floor(min / 60));
    const days = Math.floor(min / 1440);
    if (days < 2) return t.yesterday.toLowerCase();
    if (days < 7) return fmt(t.dAgo, days);
    return fmtDate(iso);
  }

  _source(src) {
    const t = this.t;
    if (!src || src === "unknown") return t.srcUnknown;
    if (src === "friedafetch") return t.srcEndpoint;
    if (src === "mcp_server") return t.srcHaMcp;
    return fmt(t.srcAssist, src);
  }

  async _ws(msg) {
    return this._hass.callWS(msg);
  }

  async _init() {
    this._render();
    try {
      await this._loadAccounts();
      if (this._s.entryId) await this._reload();
    } catch (err) {
      this._s.error = err.message || String(err);
    }
    this._s.loaded = true;
    this._render();
  }

  async _reload() {
    await this._loadAccounts();
    const jobs = [this._loadOverview(), this._loadAudit(), this._loadApprovals()];
    await Promise.all(jobs.map((j) => j.catch(() => null)));
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

  async _loadOverview() {
    this._s.overview = await this._ws({ type: "friedafetch/overview", entry_id: this._s.entryId });
  }

  async _loadApprovals() {
    this._s.approvals = await this._ws({ type: "friedafetch/approvals/list", entry_id: this._s.entryId });
  }

  async _loadAudit() {
    const res = await this._ws({ type: "friedafetch/audit/list", entry_id: this._s.entryId, limit: this._s.auditLimit });
    this._s.audit = res.entries || [];
    this._s.quota = res.quota || {};
  }

  async _decide(requestId, decision) {
    await this._call(async () => {
      await this._ws({ type: "friedafetch/approvals/decide", entry_id: this._s.entryId, request_id: requestId, decision });
      await this._reload();
    });
  }

  async _clearAudit() {
    if (!confirm(this.t.confirmClear)) return;
    await this._call(async () => {
      await this._ws({ type: "friedafetch/audit/clear", entry_id: this._s.entryId });
      await this._loadAudit();
    });
  }

  async _resetUsage() {
    if (!confirm(this.t.confirmResetUsage)) return;
    await this._call(async () => {
      await this._ws({ type: "friedafetch/usage/reset", entry_id: this._s.entryId });
      await this._loadOverview();
    });
  }

  async _switchAccount(entryId) {
    this._s.entryId = entryId;
    await this._call(() => this._reload());
  }

  async _copy(text, btn) {
    try {
      await navigator.clipboard.writeText(text);
      const old = btn.textContent;
      btn.textContent = this.t.copied;
      setTimeout(() => (btn.textContent = old), 1500);
    } catch (err) {
      window.prompt("", text);
    }
  }

  _account() {
    return this._s.accounts.find((a) => a.entry_id === this._s.entryId) || null;
  }

  // ------------------------------------------------------------ accounts
  _renderAccounts() {
    const t = this.t;
    const s = this._s;
    if (s.accounts.length < 2) return "";
    const tabs = s.accounts
      .map((a) => {
        const active = a.entry_id === s.entryId;
        const badges = [
          a.read_only ? `<span class="badge warn">${esc(t.accountReadOnly)}</span>` : "",
          a.mail_enabled ? "" : `<span class="badge warn">${esc(t.accountNoMail)}</span>`,
          a.mail_enabled && !a.read_only && !a.allow_send ? `<span class="badge">${esc(t.accountNoSend)}</span>` : "",
          !a.read_only && !a.allow_delete ? `<span class="badge">${esc(t.accountNoDelete)}</span>` : "",
          a.approvals_pending ? `<span class="badge warn">${esc(t.approvals)}: ${a.approvals_pending}</span>` : "",
        ].join("");
        return `<button class="tab ${active ? "active" : ""}" data-action="account" data-id="${esc(a.entry_id)}" aria-pressed="${active}">
          <span class="label"><span class="dot ${a.read_only ? "off" : ""}"></span>${esc(a.label)}</span>
          <span class="meta">${esc(a.apple_id || a.title)}</span>
          <span class="badges">${badges}</span>
        </button>`;
      })
      .join("");
    return `<div class="card"><h2><span class="grow">${esc(t.accounts)}</span><span class="muted">${s.accounts.length}</span></h2>
      <div class="tabs">${tabs}</div>
      <p class="muted" style="margin:10px 0 0">${esc(t.switchHint)}</p></div>`;
  }

  // ------------------------------------------------------------ overview
  _renderOverview() {
    const t = this.t;
    const o = this._s.overview;
    const a = this._account();
    if (!o || !a) return "";
    const ep = o.endpoint || {};
    const origin = window.location.origin;
    const last = o.usage?.last;
    const accountBadges = [
      a.read_only ? `<span class="badge warn">${esc(t.accountReadOnly)}</span>` : "",
      a.mail_enabled ? "" : `<span class="badge warn">${esc(t.accountNoMail)}</span>`,
      a.mail_enabled && !a.read_only && !a.allow_send ? `<span class="badge">${esc(t.accountNoSend)}</span>` : "",
      !a.read_only && !a.allow_delete ? `<span class="badge">${esc(t.accountNoDelete)}</span>` : "",
    ].join("");
    const endpointTile = `<div class="tile">
        <div class="head"><span class="dot ${ep.active ? "" : "off"}"></span><ha-icon icon="mdi:connection"></ha-icon><span>${esc(t.endpoint)}</span><span class="state">${esc(ep.active ? t.endpointOn : t.endpointOff)}</span></div>
        <div class="url"><span class="lbl">${esc(t.endpointFull)}</span><code>${esc(origin + ep.path)}</code><button class="link small" data-action="copy" data-text="${esc(origin + ep.path)}">${esc(t.copy)}</button></div>
        <div class="url"><span class="lbl">${esc(t.endpointRo)}</span><code>${esc(origin + ep.readonly_path)}</code><button class="link small" data-action="copy" data-text="${esc(origin + ep.readonly_path)}">${esc(t.copy)}</button></div>
        <div class="line muted">${esc(fmt(t.toolsCount, ep.tools, ep.tools_readonly, ep.tools_write))} · ${esc(ep.admin_only ? t.adminOnly : t.anyToken)}</div>
        ${accountBadges ? `<div class="badges">${accountBadges}</div>` : ""}
        <div class="line"><span class="muted">${esc(t.lastRequest)}:</span>${
          last ? `<span>${esc(this._rel(last.time))} · ${esc(this._toolLabel(last.tool))}</span><span class="muted">(${esc(this._source(last.source))})</span>` : `<span class="muted">${esc(t.noRequest)}</span>`
        }</div>
      </div>`;
    const clients = (o.clients || []).slice(0, 5);
    const ha = o.ha_mcp_server || {};
    const clientsTile = `<div class="tile">
        <div class="head"><ha-icon icon="mdi:robot-outline"></ha-icon><span>${esc(t.clientsTitle)}</span></div>
        ${
          clients.length
            ? `<div class="clients">${clients
                .map((c) => {
                  const fresh = parseTime(c.last_seen) && Date.now() - parseTime(c.last_seen).getTime() < 24 * 3600 * 1000;
                  return `<div class="client"><span class="dot ${fresh ? "" : "off"}"></span><span class="name">${esc(c.name)}</span>${c.version ? `<span class="muted">${esc(c.version)}</span>` : ""}${c.profile === "readonly" ? `<span class="badge">${esc(t.profileRo)}</span>` : ""}<span class="muted seen">${esc(fmt(t.clientSeen, this._rel(c.last_seen)))}</span></div>`;
                })
                .join("")}</div>`
            : `<div class="muted">${esc(t.noClients)}</div>`
        }
        ${(o.llm_api || []).length ? `<div class="line muted">${esc(fmt(t.assistApi, o.llm_api.join(", ")))}</div>` : ""}
        ${(o.injection_locks || [])
          .map((l) => {
            const [platform, user] = String(l.source).split(":");
            const who = this._source(platform);
            return `<div class="line"><span class="dot warn"></span><span>${esc(fmt(t.injectionLock, who, fmtClock(l.until), this._toolLabel(l.tool)))}</span></div>`;
          })
          .join("")}
        ${ha.installed ? `<div class="line"><span class="dot ${ha.selected ? "" : "off"}"></span><span class="muted">${esc(ha.selected ? t.haMcpOn : t.haMcpOff)}</span></div>` : ""}
      </div>`;
    return `<div class="card"><h2><span class="grow">${esc(t.overview)}</span><span class="muted">${esc(a.apple_id || a.title)}</span></h2>
      <div class="tiles">${endpointTile}${clientsTile}${this._renderPostfachTile(o.postfach || {})}</div></div>`;
  }

  _renderPostfachTile(pf) {
    const t = this.t;
    const st = pf.status || {};
    const dotCls = { running: "", not_loaded: "err", not_linked: "warn", not_installed: "off" }[pf.state] ?? "off";
    const stateText = { running: t.pfRunning, not_loaded: t.pfNotLoaded, not_linked: t.pfNotLinked, not_installed: t.pfNotInstalled }[pf.state] || pf.state;
    let lines = "";
    if (pf.state === "running") {
      const interval = st.interval;
      let mode = "";
      if (!st.auto) mode = t.pfModeOff;
      else if (st.push === "listening" || st.push === "connecting") mode = fmt(t.pfModePush, interval);
      else if (st.push) mode = fmt(t.pfModePushDown, interval);
      else mode = fmt(t.pfModeTimer, interval);
      lines = [
        st.rules_total !== undefined ? `<div class="line">${esc(fmt(t.pfRules, st.rules_total, st.rules_enabled))}</div>` : "",
        st.auto !== undefined ? `<div class="line muted">${esc(mode)}</div>` : "",
        `<div><a class="btn" href="/frieda-postfach">${esc(t.pfOpen)}</a></div>`,
      ].join("");
    } else {
      const hint = { not_loaded: t.pfNotLoadedHint, not_linked: t.pfNotLinkedHint, not_installed: t.pfNotInstalledHint }[pf.state];
      lines = hint ? `<div class="muted">${esc(hint)}</div>` : "";
    }
    return `<div class="tile">
      <div class="head"><span class="dot ${dotCls}"></span><ha-icon icon="mdi:email-fast-outline"></ha-icon><span>${esc(t.postfach)}</span><span class="state">${esc(stateText)}${pf.version && pf.state !== "not_installed" ? ` · v${esc(pf.version)}` : ""}</span></div>
      ${lines}
    </div>`;
  }

  // ---------------------------------------------------------------- usage
  _renderUsage() {
    const t = this.t;
    const u = this._s.overview?.usage;
    if (!u) return "";
    const q = this._s.quota || {};
    const quota = [
      ["mail_modify", t.quotaMailModify],
      ["mail_send", t.quotaMailSend],
      ["item_delete", t.quotaItemDelete],
    ]
      .map(([key, label]) => {
        const v = q[key];
        if (!v) return "";
        const warn = v.limit && v.used >= v.limit * 0.8;
        return `<span class="badge ${warn ? "warn" : ""}">${esc(label)}: ${esc(v.used)} / ${esc(v.limit || t.unlimited)}</span>`;
      })
      .join("");
    const stat = (label, b, sub) => `<div class="stat"><div class="k">${esc(label)}</div><div class="v">${esc(fmtNum(b.read + b.write))}</div>
        <div class="s">${esc(fmtNum(b.read))} ${esc(t.reads)} · ${esc(fmtNum(b.write))} ${esc(t.writes)}${b.error ? ` · ${esc(fmtNum(b.error))} ${esc(t.errors)}` : ""}</div>${sub ? `<div class="s">${esc(sub)}</div>` : ""}</div>`;
    const total = u.total.read + u.total.write;
    const header = `<h2><span class="grow">${esc(t.usage)}</span>${total ? `<button class="link small" data-action="usage-reset" ${this._s.busy ? "disabled" : ""}>${esc(t.resetUsage)}</button>` : ""}</h2>
      <p class="muted" style="margin:0 0 12px">${esc(t.usageHint)}</p>`;
    const quotaHtml = quota ? `<div class="badges" style="margin-top:12px"><span class="muted">${esc(t.quota)}:</span>${quota}</div>` : "";
    if (!total) return `<div class="card">${header}<p class="muted">${esc(t.noUsage)}</p>${quotaHtml}</div>`;
    const max = Math.max(1, ...u.series.map((d) => d.read + d.write));
    const chart = u.series
      .map((d) => {
        const r = (d.read / max) * 100;
        const w = (d.write / max) * 100;
        const tip = `${fmtDate(d.date)}: ${d.read} ${t.reads}, ${d.write} ${t.writes}${d.error ? `, ${d.error} ${t.errors}` : ""}`;
        return `<div class="col ${d.write ? "" : "solo"}" title="${esc(tip)}"><div class="r" style="height:${r}%"></div><div class="w" style="height:${w}%"></div></div>`;
      })
      .join("");
    const axis = u.series
      .map((d, i) => `<span>${i % 2 === u.series.length % 2 ? "" : esc(String(parseTime(d.date + "T12:00:00")?.getDate() ?? ""))}</span>`)
      .join("");
    const topMax = Math.max(1, ...u.tools.map((x) => x.count));
    const tools = u.tools
      .map((x) => {
        const ro = !TOOLS[x.tool] || !TOOLS[x.tool][3];
        return `<div class="bar"><span>${esc(this._toolLabel(x.tool))}</span><span class="muted">${esc(fmtNum(x.count))}</span>
          <div class="track"><div class="fill ${ro ? "ro" : ""}" style="width:${(x.count / topMax) * 100}%"></div></div></div>`;
      })
      .join("");
    const sources = Object.entries(u.sources || {})
      .sort((a, b) => b[1] - a[1])
      .map(([src, n]) => `<span class="chip">${esc(this._source(src))} · ${esc(fmtNum(n))}</span>`)
      .join("");
    return `<div class="card">${header}
      <div class="stats">${stat(t.today, u.today)}${stat(t.week, u.week)}${stat(t.month, u.month)}${stat(t.total, u.total, u.since ? fmt(t.since, fmtDate(u.since)) : "")}</div>
      <div class="usage-grid" style="margin-top:14px">
        <div><h3>${esc(t.last14)}</h3><div class="chart">${chart}</div><div class="axis">${axis}</div>
          <div class="legend"><span><i style="background:color-mix(in srgb, var(--primary-color) 35%, transparent)"></i>${esc(t.reads)}</span><span><i style="background:var(--primary-color)"></i>${esc(t.writes)}</span></div></div>
        <div><h3>${esc(t.topTools)}</h3><div class="bars">${tools}</div>
          ${sources ? `<h3>${esc(t.sources)}</h3><div>${sources}</div>` : ""}</div>
      </div>
      ${quotaHtml}
    </div>`;
  }

  // ------------------------------------------------------------ approvals
  _renderApprovals() {
    const t = this.t;
    const a = this._s.approvals;
    if (!a) return "";
    const pending = (a.requests || []).filter((r) => r.status === "pending");
    const decided = (a.requests || []).filter((r) => r.status !== "pending").slice(0, 10);
    if (!a.enabled && !decided.length) return "";
    const status = (st) => `<span class="badge ${st === "pending" ? "warn" : ""}">${esc(t[st] || st)}</span>`;
    const reason = (r) => esc(t[`reason_${r}`] || r);
    const row = (r, withButtons) => `<tr>
        <td style="white-space:nowrap">${esc(fmtDateTime(r.created))}</td>
        <td>${esc(r.client ? this._source(r.client) : "–")}</td>
        <td>${esc(this._toolLabel(r.tool))}<div class="muted">${reason(r.reason)}</div></td>
        <td>${esc(r.summary)}${r.error ? `<div class="muted">${esc(r.error)}</div>` : ""}</td>
        <td>${status(r.status)}${withButtons ? `<div class="muted">${esc(r.reason === "delay" ? t.sendsAt : t.validUntil)} ${esc(fmtClock(r.expires))}</div>` : r.decided_by ? `<div class="muted">${esc(t.decidedBy)} ${esc(r.decided_by === "delay" ? t.decidedByDelay : r.decided_by === "restart" ? t.decidedByRestart : r.decided_by)}</div>` : ""}</td>
        <td class="actions" style="white-space:nowrap">${withButtons ? `<button data-action="approve" data-id="${esc(r.id)}" ${this._s.busy ? "disabled" : ""}>${esc(r.reason === "delay" ? t.sendNow : t.approve)}</button> <button class="danger" data-action="deny" data-id="${esc(r.id)}" ${this._s.busy ? "disabled" : ""}>${esc(r.reason === "delay" ? t.cancelSend : t.deny)}</button>` : ""}</td>
      </tr>`;
    const labels = [t.colTime, t.colWho, t.colTool, t.colDetails, t.colResult, ""];
    const table = (rows) => `<div class="scroll"><table class="stack"><thead><tr>${labels.map((l) => `<th>${esc(l)}</th>`).join("")}</tr></thead><tbody>${withLabels(rows, labels)}</tbody></table></div>`;
    return `<div class="card">
      <h2><span class="grow">${esc(t.approvals)}${pending.length ? ` <span class="badge warn">${pending.length}</span>` : ""}</span></h2>
      <p class="muted" style="margin:0 0 10px">${esc(a.enabled ? t.approvalsHint : t.approvalsOff)}</p>
      ${a.enabled ? (pending.length ? table(pending.map((r) => row(r, true)).join("")) : `<p class="muted">${esc(t.noApprovals)}</p>`) : ""}
      ${decided.length ? `<h3>${esc(t.recentDecisions)}</h3>${table(decided.map((r) => row(r, false)).join(""))}` : ""}
    </div>`;
  }

  // ------------------------------------------------------------- activity
  _isRuleEntry(e) {
    return e.tool === "icloud_run_rules" && (String(e.client || "").startsWith("rules") || e.details?.trigger || e.params?.trigger);
  }

  _who(e) {
    const t = this.t;
    if (this._isRuleEntry(e)) {
      const trig = e.details?.trigger || e.params?.trigger || (e.client === "rules (auto)" ? "auto" : e.client === "rules (push)" ? "push" : "manual");
      const trigText = trig === "auto" ? t.triggerAuto : trig === "push" ? t.triggerPush : trig === "assistant" ? t.triggerAssistant : t.triggerManual;
      return { key: "rules", text: [`${t.srcRules} (${trigText})`, e.user].filter(Boolean).join(" · ") };
    }
    if (e.tool === "friedafetch_mail_ai_sort") {
      const trig = e.details?.trigger || e.params?.trigger;
      const trigText = trig === "auto" ? t.triggerAuto : trig === "push" ? t.triggerPush : trig === "assistant" ? t.triggerAssistant : t.triggerManual;
      return { key: "ai", text: `${t.srcAi} (${trigText})` };
    }
    const src = e.client || "unknown";
    return { key: src, text: [this._source(src), e.user].filter(Boolean).join(" · ") };
  }

  _chips(e) {
    const t = this.t;
    const d = e.details || {};
    const p = e.params || {};
    const chips = [];
    const quote = (v) => `„${v}“`;
    const n = d.count ?? (p.uids ? [].concat(p.uids).length : p.uid !== undefined && e.tool.includes("mail") ? 1 : null);
    if (e.tool.includes("_mail") && n) chips.push(n === 1 ? t.oneMail : fmt(t.nMails, n));
    else if (d.count) chips.push(`${d.count}×`);
    if (p.subject) chips.push(quote(p.subject));
    if (p.to) chips.push(`→ ${[].concat(p.to).join(", ")}`);
    if (p.target_mailbox) chips.push(`→ ${p.target_mailbox}`);
    if (p.summary || d.summary) chips.push(quote(p.summary || d.summary));
    if (p.full_name || p.name || d.name) chips.push(quote(p.full_name || p.name || d.name));
    if (p.title) chips.push(quote(p.title));
    if (p.seen === true) chips.push(this.lang === "de" ? "gelesen" : "read");
    if (p.seen === false) chips.push(this.lang === "de" ? "ungelesen" : "unread");
    if (p.flagged === true) chips.push(this.lang === "de" ? "markiert" : "flagged");
    if (p.flagged === false) chips.push(this.lang === "de" ? "Markierung entfernt" : "unflagged");
    if (d.matched !== undefined)
      chips.push(fmt(e.tool === "friedafetch_mail_ai_sort" ? t.ratedApplied : t.checkedMatched, d.checked ?? 0, d.matched));
    return chips;
  }

  _dayLabel(iso) {
    const t = this.t;
    const d = parseTime(iso);
    if (!d || isNaN(d)) return "–";
    const today = new Date();
    const y = new Date(today);
    y.setDate(today.getDate() - 1);
    if (d.toDateString() === today.toDateString()) return t.todayLabel;
    if (d.toDateString() === y.toDateString()) return t.yesterday;
    return d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
  }

  _renderActivity() {
    const t = this.t;
    const s = this._s;
    const f = s.filter;
    const entries = s.audit.map((e) => {
      const who = this._who(e);
      const area = this._area(e.tool);
      const chips = this._chips(e);
      const res = e.result === "ok" ? t.resOk : e.result === "blocked" ? t.resBlocked : t.resError;
      const what = this._toolLabel(e.tool, e.result === "ok");
      const text = [what, e.tool, who.text, ...chips, e.error || "", res].join(" ").toLowerCase();
      return { e, who, area, chips, res, what, text };
    });
    const visible = entries.filter(
      (x) =>
        (!f.q || x.text.includes(f.q.toLowerCase().trim())) &&
        (!f.area || x.area === f.area) &&
        (!f.result || x.e.result === f.result) &&
        (!f.source || x.who.key === f.source)
    );
    const opt = (val, label, cur) => `<option value="${esc(val)}" ${val === cur ? "selected" : ""}>${esc(label)}</option>`;
    const areas = [...new Set(entries.map((x) => x.area))];
    const srcName = (k) => (k === "rules" ? t.srcRules : k === "ai" ? t.srcAi : this._source(k));
    const sources = [...new Map(entries.map((x) => [x.who.key, srcName(x.who.key)])).entries()];
    const filters = entries.length
      ? `<div class="fbar">
          <input type="text" data-filter="q" value="${esc(f.q)}" placeholder="${esc(t.search)}" aria-label="${esc(t.search)}">
          <select data-filter="area" aria-label="${esc(t.allAreas)}">${opt("", t.allAreas, f.area)}${areas.map((a) => opt(a, t[`area_${a}`] || a, f.area)).join("")}</select>
          ${sources.length > 1 ? `<select data-filter="source" aria-label="${esc(t.allSources)}">${opt("", t.allSources, f.source)}${sources.map(([k, l]) => opt(k, l, f.source)).join("")}</select>` : ""}
          <select data-filter="result" aria-label="${esc(t.allResults)}">${opt("", t.allResults, f.result)}${opt("ok", t.resOk, f.result)}${opt("error", t.resError, f.result)}${opt("blocked", t.resBlocked, f.result)}</select>
          ${visible.length !== entries.length ? `<span class="muted count">${esc(fmt(t.countOf, visible.length, entries.length))}</span>` : ""}
        </div>`
      : "";
    let lastDay = null;
    const list = visible
      .map((x) => {
        const e = x.e;
        const day = this._dayLabel(e.time);
        const head = day !== lastDay ? `<div class="day">${esc(day)}</div>` : "";
        lastDay = day;
        const bad = e.result !== "ok";
        const params = Object.keys(e.params || {}).length ? JSON.stringify(e.params, null, 2) : "";
        return `${head}<div class="ev ${bad ? "bad" : ""}">
          <div class="ico"><ha-icon icon="${AREA_ICON[x.area] || AREA_ICON.other}"></ha-icon></div>
          <div class="what">${esc(x.what)} ${x.chips.map((c) => `<span class="chip">${esc(c)}</span>`).join("")}</div>
          <div class="when" title="${esc(fmtDateTime(e.time))}">${esc(fmtClock(e.time))}</div>
          <div class="who">${esc(x.who.text)}</div>
          <div class="side">${bad ? `<span class="badge ${e.result === "blocked" ? "warn" : "err"}">${esc(x.res)}</span>` : ""}</div>
          ${e.error ? `<div class="errtext">${esc(e.error)}</div>` : ""}
          ${params ? `<details><summary>${esc(t.details)}</summary><div class="muted"><code>${esc(e.tool)}</code></div><pre>${esc(params)}</pre></details>` : ""}
        </div>`;
      })
      .join("");
    const more = s.audit.length >= s.auditLimit && s.auditLimit < 500;
    return `<div class="card">
      <h2><span class="grow">${esc(t.activity)}</span>
        <button class="link small" data-action="audit-clear" ${s.busy || !s.audit.length ? "disabled" : ""}>${esc(t.clearLog)}</button></h2>
      <p class="muted" style="margin:0 0 10px">${esc(t.activityHint)}</p>
      ${filters}
      ${entries.length ? (visible.length ? `<div>${list}</div>` : `<p class="muted">${esc(t.noMatch)}</p>`) : `<p class="muted">${esc(t.noActivity)}</p>`}
      ${more ? `<div style="margin-top:10px"><button class="secondary small" data-action="audit-more" ${s.busy ? "disabled" : ""}>${esc(t.showMore)}</button></div>` : ""}
    </div>`;
  }

  // ---------------------------------------------------------------- render
  _render() {
    const t = this.t;
    const s = this._s;
    const focus = this.shadowRoot.activeElement?.dataset?.filter;
    const body = !s.loaded
      ? `<p class="muted">${esc(t.loading)}</p>`
      : !s.entryId
        ? `<div class="card"><p>${esc(t.noAccount)}</p></div>`
        : `
      ${s.error ? `<div class="error">${esc(s.error)}</div>` : ""}
      ${this._renderAccounts()}
      ${this._renderOverview()}
      ${this._renderApprovals()}
      ${this._renderUsage()}
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
    if (focus) {
      const el = this.shadowRoot.querySelector(`[data-filter="${focus}"]`);
      if (el) {
        el.focus();
        if (el.tagName === "INPUT") el.setSelectionRange(el.value.length, el.value.length);
      }
    }
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-action]").forEach((el) => {
      const action = el.dataset.action;
      const handler = {
        account: () => this._switchAccount(el.dataset.id),
        copy: () => this._copy(el.dataset.text, el),
        approve: () => this._decide(el.dataset.id, "approve"),
        deny: () => this._decide(el.dataset.id, "deny"),
        "audit-clear": () => this._clearAudit(),
        "usage-reset": () => this._resetUsage(),
        "audit-more": () => {
          this._s.auditLimit = Math.min(500, this._s.auditLimit + 100);
          this._call(() => this._loadAudit());
        },
      }[action];
      if (handler) el.addEventListener("click", handler);
    });
    root.querySelectorAll("[data-filter]").forEach((el) => {
      el.addEventListener(el.tagName === "SELECT" ? "change" : "input", () => {
        this._s.filter = { ...this._s.filter, [el.dataset.filter]: el.value };
        this._render();
      });
    });
  }
}

if (!customElements.get("friedafetch-panel")) {
  customElements.define("friedafetch-panel", FriedaPanel);
}
