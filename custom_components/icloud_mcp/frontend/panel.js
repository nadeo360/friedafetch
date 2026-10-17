/* iCloud MCP – Posteingangsregeln: Verwaltungspanel (ohne Build-Schritt, ohne Abhängigkeiten). */

const FIELDS = ["from", "to", "cc", "subject", "any"];
const OPS = ["contains", "equals", "starts_with", "ends_with", "domain", "regex"];

const I18N = {
  de: {
    title: "iCloud Regeln",
    account: "Konto",
    rules: "Regeln",
    newRule: "Neue Regel",
    noRules: "Noch keine Regeln. Lege die erste Regel an oder lass sie dir vom Assistenten anlegen.",
    name: "Name",
    mailbox: "Postfach (Quelle)",
    match: "Bedingungen verknüpfen",
    all: "alle müssen zutreffen",
    any: "eine muss zutreffen",
    conditions: "Bedingungen",
    addCondition: "Bedingung hinzufügen",
    field: "Feld",
    op: "Vergleich",
    value: "Wert",
    actions: "Aktionen",
    moveTo: "Verschieben nach",
    noMove: "– nicht verschieben –",
    markSeen: "Gelesen-Status",
    unchanged: "– unverändert –",
    seen: "als gelesen markieren",
    unseen: "als ungelesen markieren",
    flag: "Markierung",
    flagSet: "markieren",
    flagClear: "Markierung entfernen",
    delete: "In den Papierkorb verschieben",
    stop: "Danach keine weiteren Regeln prüfen",
    enabled: "Aktiv",
    save: "Speichern",
    cancel: "Abbrechen",
    edit: "Bearbeiten",
    remove: "Löschen",
    confirmDelete: "Regel wirklich löschen?",
    hits: "Treffer",
    up: "Nach oben",
    down: "Nach unten",
    run: "Regeln ausführen",
    dryRunAll: "Probelauf (gesamtes Postfach)",
    runAll: "Jetzt anwenden (gesamtes Postfach)",
    runNew: "Nur neue Mails",
    confirmRun: "Regeln jetzt auf das gesamte Postfach anwenden? Verschieben und Löschen werden sofort ausgeführt.",
    lastRun: "Letzter Lauf",
    never: "noch nie",
    report: "Bericht",
    checked: "geprüft",
    matched: "Treffer",
    dryRun: "Probelauf",
    skipped: "Übersprungen",
    errors: "Fehler",
    uid: "UID",
    subject: "Betreff",
    from: "Von",
    rule: "Regel",
    action: "Aktion",
    aMove: "→ {0}",
    aDelete: "Papierkorb",
    aSeen: "gelesen",
    aUnseen: "ungelesen",
    aFlag: "markiert",
    aUnflag: "Markierung weg",
    loading: "Lade …",
    noAccount: "Kein iCloud-Konto eingerichtet oder Mail-Tools deaktiviert.",
    fields: { from: "Absender", to: "Empfänger", cc: "Kopie", subject: "Betreff", any: "irgendwo" },
    ops: {
      contains: "enthält",
      equals: "ist gleich",
      starts_with: "beginnt mit",
      ends_with: "endet mit",
      domain: "Domain ist",
      regex: "Regex",
    },
    baseline: "Ausgangsbasis gesetzt – beim nächsten Lauf werden neue Mails verarbeitet.",
    delete_disabled: "Löschen ist in den Optionen deaktiviert.",
    accounts: "Konten",
    accountRules: "{0} Regeln, {1} aktiv",
    accountAuto: "Automatik alle {0} Min.",
    accountManual: "Automatik aus",
    accountReadOnly: "Nur-Lesen",
    accountNoMail: "Mail-Tools deaktiviert",
    accountHits: "{0} Treffer gesamt",
    copyTo: "Kopieren nach …",
    copied: "Regel nach „{0}“ kopiert.",
    allAccounts: "Alle Konten",
    switchHint: "Regeln, Läufe und Berichte gelten je Konto. Wähle oben das Konto.",
  },
  en: {
    title: "iCloud rules",
    account: "Account",
    rules: "Rules",
    newRule: "New rule",
    noRules: "No rules yet. Create the first one here or let the assistant create it.",
    name: "Name",
    mailbox: "Mailbox (source)",
    match: "Combine conditions",
    all: "all must match",
    any: "any may match",
    conditions: "Conditions",
    addCondition: "Add condition",
    field: "Field",
    op: "Comparison",
    value: "Value",
    actions: "Actions",
    moveTo: "Move to",
    noMove: "– do not move –",
    markSeen: "Read state",
    unchanged: "– unchanged –",
    seen: "mark as read",
    unseen: "mark as unread",
    flag: "Flag",
    flagSet: "flag",
    flagClear: "remove flag",
    delete: "Move to trash",
    stop: "Stop evaluating further rules",
    enabled: "Enabled",
    save: "Save",
    cancel: "Cancel",
    edit: "Edit",
    remove: "Delete",
    confirmDelete: "Delete this rule?",
    hits: "Hits",
    up: "Move up",
    down: "Move down",
    run: "Run rules",
    dryRunAll: "Dry run (whole mailbox)",
    runAll: "Apply now (whole mailbox)",
    runNew: "New mail only",
    confirmRun: "Apply the rules to the whole mailbox now? Moves and deletions are executed immediately.",
    lastRun: "Last run",
    never: "never",
    report: "Report",
    checked: "checked",
    matched: "matched",
    dryRun: "dry run",
    skipped: "Skipped",
    errors: "Errors",
    uid: "UID",
    subject: "Subject",
    from: "From",
    rule: "Rule",
    action: "Action",
    aMove: "→ {0}",
    aDelete: "trash",
    aSeen: "read",
    aUnseen: "unread",
    aFlag: "flagged",
    aUnflag: "unflagged",
    loading: "Loading …",
    noAccount: "No iCloud account configured or mail tools disabled.",
    fields: { from: "Sender", to: "Recipient", cc: "Cc", subject: "Subject", any: "anywhere" },
    ops: {
      contains: "contains",
      equals: "equals",
      starts_with: "starts with",
      ends_with: "ends with",
      domain: "domain is",
      regex: "regex",
    },
    baseline: "Baseline set – new mail will be processed on the next run.",
    delete_disabled: "Deleting is disabled in the options.",
    accounts: "Accounts",
    accountRules: "{0} rules, {1} enabled",
    accountAuto: "automatic every {0} min",
    accountManual: "automation off",
    accountReadOnly: "read-only",
    accountNoMail: "mail tools disabled",
    accountHits: "{0} hits in total",
    copyTo: "Copy to …",
    copied: "Rule copied to “{0}”.",
    allAccounts: "All accounts",
    switchHint: "Rules, runs and reports are per account. Pick the account above.",
  },
};

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const STYLE = `
  :host { display: block; height: 100%; color: var(--primary-text-color); background: var(--primary-background-color); }
  .toolbar { display: flex; align-items: center; gap: 12px; height: 56px; padding: 0 16px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); font-size: 20px; }
  .toolbar .grow { flex: 1; }
  .toolbar select { background: rgba(255,255,255,.15); color: inherit; border: 1px solid rgba(255,255,255,.4); border-radius: 6px; padding: 4px 8px; font-size: 14px; }
  .content { padding: 16px; max-width: 1100px; margin: 0 auto; display: grid; gap: 16px; }
  .card { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0,0,0,.14)); border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0)); padding: 16px; }
  .card h2 { margin: 0 0 12px; font-size: 18px; font-weight: 500; display: flex; align-items: center; gap: 12px; }
  .card h2 .grow { flex: 1; }
  button { font: inherit; border: none; border-radius: 6px; padding: 8px 14px; cursor: pointer; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.secondary { background: transparent; color: var(--primary-color); border: 1px solid var(--primary-color); }
  button.danger { background: var(--error-color, #db4437); }
  button.icon { background: transparent; color: var(--secondary-text-color); padding: 4px 8px; font-size: 16px; }
  button:disabled { opacity: .5; cursor: default; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--divider-color, #e0e0e0); vertical-align: top; }
  th { color: var(--secondary-text-color); font-weight: 500; }
  tr.disabled td { opacity: .5; }
  .muted { color: var(--secondary-text-color); font-size: 13px; }
  .chip { display: inline-block; padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); font-size: 12px; margin: 2px 4px 2px 0; }
  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
  .row label { min-width: 170px; color: var(--secondary-text-color); font-size: 14px; }
  input[type=text], select { font: inherit; padding: 7px 10px; border: 1px solid var(--divider-color, #ccc); border-radius: 6px; background: var(--card-background-color, #fff); color: var(--primary-text-color); min-width: 160px; }
  input[type=text].grow { flex: 1; min-width: 200px; }
  .cond { display: grid; grid-template-columns: 150px 150px 1fr 40px; gap: 8px; margin-bottom: 8px; align-items: center; }
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
  select.copy { min-width: 0; max-width: 120px; padding: 3px 6px; font-size: 12px; }
  .scroll { overflow-x: auto; }
  .info { background: color-mix(in srgb, var(--primary-color) 10%, transparent); padding: 10px 12px; border-radius: 8px; font-size: 13px; }
  @media (max-width: 700px) { .cond { grid-template-columns: 1fr 1fr; } .row label { min-width: 100%; } }
`;

class ICloudMcpRulesPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._s = {
      accounts: [],
      entryId: null,
      rules: [],
      lastRun: null,
      mailboxes: [],
      editing: null,
      report: null,
      error: null,
      notice: null,
      busy: false,
      loaded: false,
    };
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
      const { accounts } = await this._ws({ type: "icloud_mcp/accounts" });
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
    const [list, boxes] = await Promise.all([
      this._ws({ type: "icloud_mcp/rules/list", entry_id: this._s.entryId }),
      this._ws({ type: "icloud_mcp/mailboxes", entry_id: this._s.entryId }).catch(() => ({ mailboxes: [] })),
    ]);
    this._s.rules = list.rules;
    this._s.lastRun = list.last_run;
    this._s.mailboxes = boxes.mailboxes;
    try {
      await this._loadAccounts();
    } catch (err) {
      /* account stats are optional */
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

  // ------------------------------------------------------------ form state
  _blankRule() {
    return {
      name: "",
      mailbox: "INBOX",
      match: "all",
      enabled: true,
      conditions: [{ field: "from", op: "contains", value: "" }],
      actions: { move_to: null, mark_seen: null, flag: null, delete: false, stop: true },
    };
  }

  _readForm() {
    const root = this.shadowRoot;
    const e = this._s.editing;
    if (!e) return null;
    const v = (id) => root.querySelector(`#${id}`)?.value;
    const c = (id) => root.querySelector(`#${id}`)?.checked;
    e.name = v("f-name") ?? e.name;
    e.mailbox = v("f-mailbox") ?? e.mailbox;
    e.match = v("f-match") ?? e.match;
    e.enabled = c("f-enabled") ?? e.enabled;
    e.conditions = [...root.querySelectorAll(".cond")].map((row) => ({
      field: row.querySelector(".c-field").value,
      op: row.querySelector(".c-op").value,
      value: row.querySelector(".c-value").value,
    }));
    const tri = (val) => (val === "" ? null : val === "true");
    e.actions = {
      move_to: v("f-move") || null,
      mark_seen: tri(v("f-seen") ?? ""),
      flag: tri(v("f-flag") ?? ""),
      delete: c("f-delete") ?? false,
      stop: c("f-stop") ?? true,
    };
    return e;
  }

  async _save() {
    const rule = this._readForm();
    await this._call(async () => {
      if (rule.id) {
        const { id, hits, created, ...changes } = rule;
        await this._ws({ type: "icloud_mcp/rules/update", entry_id: this._s.entryId, rule_id: id, changes });
      } else {
        await this._ws({ type: "icloud_mcp/rules/create", entry_id: this._s.entryId, rule });
      }
      this._s.editing = null;
      await this._reload();
    });
  }

  async _delete(id) {
    if (!confirm(this.t.confirmDelete)) return;
    await this._call(async () => {
      await this._ws({ type: "icloud_mcp/rules/delete", entry_id: this._s.entryId, rule_id: id });
      await this._reload();
    });
  }

  async _toggle(id, enabled) {
    await this._call(async () => {
      await this._ws({ type: "icloud_mcp/rules/update", entry_id: this._s.entryId, rule_id: id, changes: { enabled } });
      await this._reload();
    });
  }

  async _move(id, delta) {
    const idx = this._s.rules.findIndex((r) => r.id === id);
    const position = Math.max(0, Math.min(this._s.rules.length - 1, idx + delta));
    if (position === idx) return;
    await this._call(async () => {
      await this._ws({ type: "icloud_mcp/rules/update", entry_id: this._s.entryId, rule_id: id, changes: { position } });
      await this._reload();
    });
  }

  async _copy(id, targetEntryId) {
    const rule = this._s.rules.find((r) => r.id === id);
    const target = this._s.accounts.find((a) => a.entry_id === targetEntryId);
    if (!rule || !target) return;
    const { id: _id, hits, created, ...data } = rule;
    await this._call(async () => {
      await this._ws({ type: "icloud_mcp/rules/create", entry_id: targetEntryId, rule: data });
      await this._loadAccounts();
      this._s.notice = this.t.copied.replace("{0}", target.label);
    });
  }

  async _loadAccounts() {
    const { accounts } = await this._ws({ type: "icloud_mcp/accounts" });
    this._s.accounts = accounts;
    if (!accounts.some((a) => a.entry_id === this._s.entryId)) this._s.entryId = accounts[0]?.entry_id || null;
  }

  async _switchAccount(entryId) {
    this._s.entryId = entryId;
    this._s.editing = null;
    this._s.report = null;
    this._s.notice = null;
    await this._call(() => this._reload());
  }

  async _run(scope, dryRun) {
    if (!dryRun && scope === "all" && !confirm(this.t.confirmRun)) return;
    await this._call(async () => {
      this._s.report = await this._ws({ type: "icloud_mcp/rules/run", entry_id: this._s.entryId, scope, dry_run: dryRun });
      await this._reload();
    });
  }

  // ---------------------------------------------------------------- render
  _summary(rule) {
    const t = this.t;
    const conds = rule.conditions
      .map((c) => `<span class="chip">${esc(t.fields[c.field] || c.field)} ${esc(t.ops[c.op] || c.op)} „${esc(c.value)}“</span>`)
      .join(rule.match === "any" ? ` <span class="muted">${esc(t.any.split(" ")[0])}</span> ` : " ");
    const a = rule.actions;
    const acts = [];
    if (a.move_to) acts.push(t.aMove.replace("{0}", esc(a.move_to)));
    if (a.delete) acts.push(t.aDelete);
    if (a.mark_seen === true) acts.push(t.aSeen);
    if (a.mark_seen === false) acts.push(t.aUnseen);
    if (a.flag === true) acts.push(t.aFlag);
    if (a.flag === false) acts.push(t.aUnflag);
    return { conds, acts: acts.map((x) => `<span class="chip">${x}</span>`).join(" ") };
  }

  _account() {
    return this._s.accounts.find((a) => a.entry_id === this._s.entryId) || null;
  }

  _renderAccounts() {
    const t = this.t;
    const s = this._s;
    if (!s.accounts.length) return "";
    const fmt = (str, ...args) => str.replace(/\{(\d+)\}/g, (_, i) => args[Number(i)]);
    const tabs = s.accounts
      .map((a) => {
        const active = a.entry_id === s.entryId;
        const last = a.last_run ? new Date(a.last_run.finished || a.last_run.started).toLocaleString() : t.never;
        const badges = [
          `<span class="badge">${esc(a.rules_auto && a.mail_enabled && !a.read_only ? fmt(t.accountAuto, a.rules_interval) : t.accountManual)}</span>`,
          a.read_only ? `<span class="badge warn">${esc(t.accountReadOnly)}</span>` : "",
          a.mail_enabled ? "" : `<span class="badge warn">${esc(t.accountNoMail)}</span>`,
        ].join("");
        return `<button class="tab ${active ? "active" : ""}" data-action="account" data-id="${esc(a.entry_id)}" aria-pressed="${active}">
          <span class="label"><span class="dot ${a.rules_enabled ? "" : "off"}"></span>${esc(a.label)}</span>
          <span class="meta">${esc(a.apple_id || a.title)}</span>
          <span class="meta">${esc(fmt(t.accountRules, a.rules_total, a.rules_enabled))} · ${esc(fmt(t.accountHits, a.hits))}</span>
          <span class="meta">${esc(t.lastRun)}: ${esc(last)}</span>
          <span class="badges">${badges}</span>
        </button>`;
      })
      .join("");
    return `<div class="card"><h2><span class="grow">${esc(t.accounts)}</span><span class="muted">${s.accounts.length}</span></h2>
      <div class="tabs">${tabs}</div>
      ${s.accounts.length > 1 ? `<p class="muted" style="margin:10px 0 0">${esc(t.switchHint)}</p>` : ""}</div>`;
  }

  _renderRules() {
    const t = this.t;
    if (!this._s.rules.length) return `<p class="muted">${esc(t.noRules)}</p>`;
    const rows = this._s.rules
      .map((r, i) => {
        const { conds, acts } = this._summary(r);
        return `<tr class="${r.enabled ? "" : "disabled"}">
          <td><input type="checkbox" data-action="toggle" data-id="${r.id}" ${r.enabled ? "checked" : ""} title="${esc(t.enabled)}"></td>
          <td><strong>${esc(r.name)}</strong><div class="muted">${esc(r.mailbox)}</div></td>
          <td>${conds}</td>
          <td>${acts}${r.actions.stop === false ? `<div class="muted">↓</div>` : ""}</td>
          <td>${r.hits ?? 0}</td>
          <td style="white-space:nowrap">
            <button class="icon" data-action="up" data-id="${r.id}" ${i === 0 ? "disabled" : ""} title="${esc(t.up)}">▲</button>
            <button class="icon" data-action="down" data-id="${r.id}" ${i === this._s.rules.length - 1 ? "disabled" : ""} title="${esc(t.down)}">▼</button>
            <button class="icon" data-action="edit" data-id="${r.id}" title="${esc(t.edit)}">✎</button>
            <button class="icon" data-action="delete" data-id="${r.id}" title="${esc(t.remove)}">🗑</button>
            ${this._s.accounts.length > 1 ? `<select class="copy" data-action="copy" data-id="${r.id}" title="${esc(t.copyTo)}"><option value="">${esc(t.copyTo)}</option>${this._s.accounts.filter((a) => a.entry_id !== this._s.entryId).map((a) => `<option value="${esc(a.entry_id)}">${esc(a.label)}</option>`).join("")}</select>` : ""}
          </td></tr>`;
      })
      .join("");
    return `<div class="scroll"><table><thead><tr><th></th><th>${esc(t.name)}</th><th>${esc(t.conditions)}</th><th>${esc(t.actions)}</th><th>${esc(t.hits)}</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  _renderEditor() {
    const t = this.t;
    const e = this._s.editing;
    if (!e) return "";
    const opt = (val, label, cur) => `<option value="${esc(val)}" ${String(cur) === String(val) ? "selected" : ""}>${esc(label)}</option>`;
    const boxes = [...new Set(["INBOX", ...this._s.mailboxes])];
    const conds = e.conditions
      .map(
        (c, i) => `<div class="cond" data-index="${i}">
          <select class="c-field">${FIELDS.map((f) => opt(f, t.fields[f], c.field)).join("")}</select>
          <select class="c-op">${OPS.map((o) => opt(o, t.ops[o], c.op)).join("")}</select>
          <input type="text" class="c-value" value="${esc(c.value)}" placeholder="${esc(t.value)}">
          <button class="icon" data-action="remove-cond" data-index="${i}" ${e.conditions.length === 1 ? "disabled" : ""}>✕</button>
        </div>`
      )
      .join("");
    const a = e.actions;
    const tri = (val) => (val === null || val === undefined ? "" : String(val));
    return `<div class="card">
      <h2>${esc(e.id ? t.edit : t.newRule)}</h2>
      <div class="row"><label for="f-name">${esc(t.name)}</label><input type="text" id="f-name" class="grow" value="${esc(e.name)}"></div>
      <div class="row"><label for="f-mailbox">${esc(t.mailbox)}</label><select id="f-mailbox">${boxes.map((b) => opt(b, b, e.mailbox)).join("")}</select></div>
      <div class="row"><label for="f-match">${esc(t.match)}</label><select id="f-match">${opt("all", t.all, e.match)}${opt("any", t.any, e.match)}</select></div>
      <h3 class="muted">${esc(t.conditions)}</h3>
      ${conds}
      <button class="secondary" data-action="add-cond">+ ${esc(t.addCondition)}</button>
      <h3 class="muted">${esc(t.actions)}</h3>
      <div class="row"><label for="f-move">${esc(t.moveTo)}</label><select id="f-move">${opt("", t.noMove, a.move_to || "")}${this._s.mailboxes.map((b) => opt(b, b, a.move_to || "")).join("")}</select></div>
      <div class="row"><label for="f-seen">${esc(t.markSeen)}</label><select id="f-seen">${opt("", t.unchanged, tri(a.mark_seen))}${opt("true", t.seen, tri(a.mark_seen))}${opt("false", t.unseen, tri(a.mark_seen))}</select></div>
      <div class="row"><label for="f-flag">${esc(t.flag)}</label><select id="f-flag">${opt("", t.unchanged, tri(a.flag))}${opt("true", t.flagSet, tri(a.flag))}${opt("false", t.flagClear, tri(a.flag))}</select></div>
      <div class="row"><label></label><label><input type="checkbox" id="f-delete" ${a.delete ? "checked" : ""}> ${esc(t.delete)}</label></div>
      <div class="row"><label></label><label><input type="checkbox" id="f-stop" ${a.stop !== false ? "checked" : ""}> ${esc(t.stop)}</label></div>
      <div class="row"><label></label><label><input type="checkbox" id="f-enabled" ${e.enabled ? "checked" : ""}> ${esc(t.enabled)}</label></div>
      <div class="actionsbar"><button data-action="save" ${this._s.busy ? "disabled" : ""}>${esc(t.save)}</button><button class="secondary" data-action="cancel">${esc(t.cancel)}</button></div>
    </div>`;
  }

  _renderReport() {
    const t = this.t;
    const r = this._s.report;
    if (!r) return "";
    const actionText = (a) => {
      const parts = [];
      if (a.move_to) parts.push(t.aMove.replace("{0}", esc(a.move_to)));
      if (a.delete) parts.push(t.aDelete);
      if (a.mark_seen === true) parts.push(t.aSeen);
      if (a.mark_seen === false) parts.push(t.aUnseen);
      if (a.flag === true) parts.push(t.aFlag);
      if (a.flag === false) parts.push(t.aUnflag);
      return parts.join(", ");
    };
    const rows = (r.actions || [])
      .slice(0, 200)
      .map(
        (a) => `<tr><td>${a.uid}</td><td>${esc(a.subject)}</td><td>${esc((a.from || []).join(", "))}</td><td>${esc(a.rule)}</td><td>${actionText(a)}</td></tr>`
      )
      .join("");
    const skipped = (r.skipped || [])
      .map((s) => `<li>${esc(t[s.code] || s.reason)}${s.uid ? ` (UID ${s.uid})` : ""}${s.rule ? ` – ${esc(s.rule)}` : ""}${s.mailbox ? ` – ${esc(s.mailbox)}` : ""}</li>`)
      .join("");
    const errors = (r.errors || []).map((e) => `<li>${esc(e.error)}</li>`).join("");
    return `<div class="card">
      <h2><span class="grow">${esc(t.report)}${r.dry_run ? ` <span class="chip">${esc(t.dryRun)}</span>` : ""}</span><span class="muted">${r.checked} ${esc(t.checked)} · ${r.matched} ${esc(t.matched)}</span></h2>
      ${errors ? `<div class="error"><strong>${esc(t.errors)}</strong><ul>${errors}</ul></div>` : ""}
      ${skipped ? `<div class="muted"><strong>${esc(t.skipped)}</strong><ul>${skipped}</ul></div>` : ""}
      ${rows ? `<table><thead><tr><th>${esc(t.uid)}</th><th>${esc(t.subject)}</th><th>${esc(t.from)}</th><th>${esc(t.rule)}</th><th>${esc(t.action)}</th></tr></thead><tbody>${rows}</tbody></table>` : ""}
    </div>`;
  }

  _render() {
    const t = this.t;
    const s = this._s;
    const accountSel = "";
    const last = s.lastRun
      ? `${esc(t.lastRun)}: ${esc(new Date(s.lastRun.finished || s.lastRun.started).toLocaleString())} · ${s.lastRun.checked} ${esc(t.checked)} · ${s.lastRun.matched} ${esc(t.matched)}`
      : `${esc(t.lastRun)}: ${esc(t.never)}`;
    const body = !s.loaded
      ? `<p class="muted">${esc(t.loading)}</p>`
      : !s.entryId
        ? `<div class="card"><p>${esc(t.noAccount)}</p></div>`
        : `
      ${s.error ? `<div class="error">${esc(s.error)}</div>` : ""}
      ${s.notice ? `<div class="ok">${esc(s.notice)}</div>` : ""}
      ${this._renderAccounts()}
      <div class="card">
        <h2><span class="grow">${esc(t.rules)}${this._account() ? ` <span class="chip">${esc(this._account().label)}</span>` : ""}</span><button data-action="new" ${s.editing ? "disabled" : ""}>+ ${esc(t.newRule)}</button></h2>
        ${this._renderRules()}
      </div>
      ${this._renderEditor()}
      <div class="card">
        <h2><span class="grow">${esc(t.run)}</span><span class="muted">${last}</span></h2>
        <div class="actionsbar">
          <button class="secondary" data-action="run" data-scope="all" data-dry="1" ${s.busy ? "disabled" : ""}>${esc(t.dryRunAll)}</button>
          <button data-action="run" data-scope="all" data-dry="0" ${s.busy || this._account()?.read_only ? "disabled" : ""} title="${this._account()?.read_only ? esc(t.accountReadOnly) : ""}">${esc(t.runAll)}</button>
          <button class="secondary" data-action="run" data-scope="new" data-dry="0" ${s.busy || this._account()?.read_only ? "disabled" : ""}>${esc(t.runNew)}</button>
        </div>
      </div>
      ${this._renderReport()}`;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><span>${esc(t.title)}</span><span class="grow"></span>${accountSel}</div>
      <div class="content">${body}</div>`;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu && this._hass) {
      menu.hass = this._hass;
      menu.narrow = this._narrow;
    }
    this._bind();
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-action]").forEach((el) => {
      const action = el.dataset.action;
      const handler = {
        new: () => {
          this._s.editing = this._blankRule();
          this._render();
        },
        edit: () => {
          const rule = this._s.rules.find((r) => r.id === el.dataset.id);
          this._s.editing = JSON.parse(JSON.stringify(rule));
          this._render();
        },
        delete: () => this._delete(el.dataset.id),
        up: () => this._move(el.dataset.id, -1),
        down: () => this._move(el.dataset.id, 1),
        "add-cond": () => {
          this._readForm();
          this._s.editing.conditions.push({ field: "subject", op: "contains", value: "" });
          this._render();
        },
        "remove-cond": () => {
          this._readForm();
          this._s.editing.conditions.splice(Number(el.dataset.index), 1);
          this._render();
        },
        save: () => this._save(),
        cancel: () => {
          this._s.editing = null;
          this._render();
        },
        run: () => this._run(el.dataset.scope, el.dataset.dry === "1"),
      }[action];
      if (action === "toggle") {
        el.addEventListener("change", () => this._toggle(el.dataset.id, el.checked));
      } else if (action === "copy") {
        el.addEventListener("change", () => el.value && this._copy(el.dataset.id, el.value));
      } else if (action === "account") {
        el.addEventListener("click", () => this._switchAccount(el.dataset.id));
      } else if (handler) {
        el.addEventListener("click", handler);
      }
    });
  }
}

if (!customElements.get("icloud-mcp-rules-panel")) {
  customElements.define("icloud-mcp-rules-panel", ICloudMcpRulesPanel);
}
