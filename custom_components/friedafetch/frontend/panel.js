/* Frieda – Posteingangsregeln: Verwaltungspanel (ohne Build-Schritt, ohne Abhängigkeiten). */

const ICON_URL = new URL("icon.svg", import.meta.url).href;

const FIELDS = ["from", "to", "cc", "subject", "any"];
const OPS = ["contains", "equals", "starts_with", "ends_with", "domain", "regex"];

const I18N = {
  de: {
    title: "Frieda",
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
    autoEvery: "Automatik: alle {0} Min.",
    nextRun: "nächster Lauf {0}",
    lastCheck: "letzte Prüfung {0}",
    check_ran: "ausgeführt",
    check_no_enabled_rules: "nichts zu tun",
    check_error: "Fehler",
    autoOff: "Automatik aus – aktivierbar in den Optionen unter „Posteingangsregeln“.",
    autoIdle: "Keine aktive Regel: Die Automatik läuft, hat aber nichts zu tun. Lege eine Regel an oder aktiviere eine.",
    triggerAuto: "automatisch",
    triggerManual: "manuell",
    nextShort: "nächster {0}",
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
    expandAll: "Alle aufklappen",
    collapseAll: "Alle zuklappen",
    nConditions: "{0} Bedingungen",
    oneCondition: "1 Bedingung",
    matchAnyShort: "eine muss zutreffen",
    matchAllShort: "alle müssen zutreffen",
    continueRules: "danach weitere Regeln prüfen",
    noActions: "keine Aktion",
    history: "Ausführungen",
    historyHint: "Manuelle und automatische Regelläufe, neueste zuerst. Aufeinanderfolgende automatische Läufe ohne Treffer werden zusammengefasst.",
    noHistory: "Noch keine Ausführungen aufgezeichnet.",
    clearHistory: "Verlauf leeren",
    confirmClearHistory: "Verlauf der Ausführungen wirklich leeren?",
    colTrigger: "Auslöser",
    colScope: "Umfang",
    colChecked: "Geprüft",
    colMatched: "Treffer",
    colRules: "Regeln",
    scopeNew: "neue Mails",
    scopeAll: "gesamtes Postfach",
    runsMerged: "{0} Läufe",
    resIdle: "keine Treffer",
    filter: "Filter",
    filterReset: "Filter zurücksetzen",
    filterCount: "{0} von {1} Einträgen",
    filterAll: "alle",
    filterPh: "filtern …",
    numPh: "z. B. >0",
    whoRules: "Regeln",
  },
  en: {
    title: "Frieda",
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
    autoEvery: "Automation: every {0} min",
    nextRun: "next run {0}",
    lastCheck: "last check {0}",
    check_ran: "ran",
    check_no_enabled_rules: "nothing to do",
    check_error: "error",
    autoOff: "Automation off – enable it in the options under “Inbox rules”.",
    autoIdle: "No enabled rule: the automation is running but has nothing to do. Create or enable a rule.",
    triggerAuto: "automatic",
    triggerManual: "manual",
    nextShort: "next {0}",
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
    expandAll: "Expand all",
    collapseAll: "Collapse all",
    nConditions: "{0} conditions",
    oneCondition: "1 condition",
    matchAnyShort: "any may match",
    matchAllShort: "all must match",
    continueRules: "then continue with further rules",
    noActions: "no action",
    history: "Runs",
    historyHint: "Manual and automatic rule runs, newest first. Consecutive automatic runs without hits are merged.",
    noHistory: "No runs recorded yet.",
    clearHistory: "Clear history",
    confirmClearHistory: "Really clear the run history?",
    colTrigger: "Trigger",
    colScope: "Scope",
    colChecked: "Checked",
    colMatched: "Hits",
    colRules: "Rules",
    scopeNew: "new mail",
    scopeAll: "whole mailbox",
    runsMerged: "{0} runs",
    resIdle: "no hits",
    filter: "Filter",
    filterReset: "Reset filters",
    filterCount: "{0} of {1} entries",
    filterAll: "all",
    filterPh: "filter …",
    numPh: "e.g. >0",
    whoRules: "Rules",
  },
};

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
  code { font-size: 12px; background: var(--secondary-background-color, #f0f0f0); padding: 1px 5px; border-radius: 4px; }
  .info { background: color-mix(in srgb, var(--primary-color) 10%, transparent); padding: 10px 12px; border-radius: 8px; font-size: 13px; }
  .toolbar img { width: 28px; height: 28px; border-radius: 7px; }
  table.stack { width: 100%; }
  .rules { display: grid; gap: 8px; }
  .rule { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; background: var(--card-background-color, #fff); scroll-margin-top: 16px; transition: box-shadow .4s; }
  .rule.open { border-color: color-mix(in srgb, var(--primary-color) 45%, var(--divider-color, #e0e0e0)); }
  .rule.flash { box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 35%, transparent); }
  .rule.disabled .rule-head .rule-title, .rule.disabled .rule-head .rule-side { opacity: .55; }
  .rule-head { display: flex; align-items: center; gap: 8px; padding: 6px 10px 6px 4px; }
  .rule-head .chev { transition: transform .15s; }
  .rule.open .rule-head .chev { transform: rotate(90deg); }
  .rule-title { flex: 1; min-width: 0; cursor: pointer; display: grid; gap: 1px; }
  .rule-title strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rule-side { display: flex; align-items: center; gap: 6px; max-width: 50%; }
  .rule-acts { display: flex; flex-wrap: wrap; justify-content: flex-end; }
  .rule-side .badge { white-space: nowrap; }
  .rule-body { padding: 4px 14px 12px 44px; display: grid; gap: 10px; border-top: 1px dashed var(--divider-color, #e0e0e0); }
  .rule-body .lbl { font-size: 12px; color: var(--secondary-text-color); margin-bottom: 2px; }
  .rule-tools { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .editor { padding: 12px 14px; scroll-margin-top: 16px; }
  .editor h3.title { margin: 0 0 12px; font-size: 16px; font-weight: 500; }
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
    .rule-head { flex-wrap: wrap; padding: 4px 8px 4px 2px; }
    .rule-side { max-width: none; flex-basis: 100%; padding-left: 92px; box-sizing: border-box; }
    .rule-acts { flex: 1; justify-content: flex-start; }
    .rule-body { padding: 6px 10px 10px; }
    .rule-tools select.copy { width: auto; flex: 1 1 140px; }
    .editor { padding: 10px; }
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
    .cond { grid-template-columns: 1fr; gap: 6px; padding: 8px; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; }
    .cond button.icon { justify-self: end; }
    button { min-height: 44px; }
    button.icon { min-width: 44px; min-height: 44px; font-size: 18px; }
    input[type=text], select, select.copy { width: 100%; max-width: none; min-width: 0; box-sizing: border-box; min-height: 44px; font-size: 16px; }
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
      rules: [],
      lastRun: null,
      mailboxes: [],
      editing: null,
      report: null,
      error: null,
      notice: null,
      audit: [],
      quota: {},
      approvals: null,
      auditLimit: 25,
      history: [],
      historyTotal: 0,
      historyLimit: 50,
      expanded: new Set(),
      filters: {},
      filterOpen: {},
      focusEditor: false,
      scrollTo: null,
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
    if (!this._hass || !s.loaded || !s.entryId || s.busy || s.editing || document.visibilityState !== "visible") return;
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
    const [list, boxes] = await Promise.all([
      this._ws({ type: "friedafetch/rules/list", entry_id: this._s.entryId }),
      this._ws({ type: "friedafetch/mailboxes", entry_id: this._s.entryId }).catch(() => ({ mailboxes: [] })),
    ]);
    this._s.rules = list.rules;
    this._s.lastRun = list.last_run;
    this._s.automation = list.automation || null;
    this._s.mailboxes = boxes.mailboxes;
    try {
      await this._loadAccounts();
      await this._loadAudit();
      await this._loadHistory();
      await this._loadApprovals();
    } catch (err) {
      /* account stats, history, audit and approvals are optional */
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
      let saved;
      if (rule.id) {
        const { id, hits, created, ...changes } = rule;
        saved = await this._ws({ type: "friedafetch/rules/update", entry_id: this._s.entryId, rule_id: id, changes });
      } else {
        saved = await this._ws({ type: "friedafetch/rules/create", entry_id: this._s.entryId, rule });
      }
      const savedId = saved?.rule?.id || rule.id;
      if (savedId) {
        this._s.expanded.add(savedId);
        this._s.scrollTo = savedId;
      }
      this._s.editing = null;
      await this._reload();
    });
  }

  async _delete(id) {
    if (!confirm(this.t.confirmDelete)) return;
    await this._call(async () => {
      await this._ws({ type: "friedafetch/rules/delete", entry_id: this._s.entryId, rule_id: id });
      await this._reload();
    });
  }

  async _toggle(id, enabled) {
    await this._call(async () => {
      await this._ws({ type: "friedafetch/rules/update", entry_id: this._s.entryId, rule_id: id, changes: { enabled } });
      await this._reload();
    });
  }

  async _move(id, delta) {
    const idx = this._s.rules.findIndex((r) => r.id === id);
    const position = Math.max(0, Math.min(this._s.rules.length - 1, idx + delta));
    if (position === idx) return;
    await this._call(async () => {
      await this._ws({ type: "friedafetch/rules/update", entry_id: this._s.entryId, rule_id: id, changes: { position } });
      await this._reload();
    });
  }

  async _copy(id, targetEntryId) {
    const rule = this._s.rules.find((r) => r.id === id);
    const target = this._s.accounts.find((a) => a.entry_id === targetEntryId);
    if (!rule || !target) return;
    const { id: _id, hits, created, ...data } = rule;
    await this._call(async () => {
      await this._ws({ type: "friedafetch/rules/create", entry_id: targetEntryId, rule: data });
      await this._loadAccounts();
      this._s.notice = this.t.copied.replace("{0}", target.label);
    });
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

  async _loadHistory() {
    const res = await this._ws({ type: "friedafetch/rules/history", entry_id: this._s.entryId, limit: this._s.historyLimit });
    this._s.history = res.runs || [];
    this._s.historyTotal = res.total || 0;
  }

  async _clearHistory() {
    if (!confirm(this.t.confirmClearHistory)) return;
    await this._call(async () => {
      await this._ws({ type: "friedafetch/rules/history/clear", entry_id: this._s.entryId });
      await this._loadHistory();
    });
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

  _renderHistory() {
    const t = this.t;
    const s = this._s;
    const time = (h) => {
      if ((h.runs || 1) > 1) {
        const a = parseTime(h.started);
        const b = parseTime(h.finished);
        const sameDay = a && b && a.toDateString() === b.toDateString();
        return `${fmtDateTime(h.started)} – ${sameDay ? fmtClock(h.finished) : fmtDateTime(h.finished)}`;
      }
      return fmtDateTime(h.finished || h.started);
    };
    const rows = s.history.map((h) => {
      const trig = h.trigger === "auto" ? t.triggerAuto : t.triggerManual;
      const scope = h.scope === "all" ? t.scopeAll : t.scopeNew;
      const ruleText = Object.entries(h.rules || {})
        .map(([name, n]) => `${name} (${n})`)
        .join(", ");
      const errors = (h.errors || []).length;
      const res = errors ? t.resError : h.matched ? t.resOk : t.resIdle;
      const timeText = time(h);
      return [
        { html: `<span style="white-space:nowrap">${esc(timeText)}</span>${(h.runs || 1) > 1 ? `<div class="muted">${esc(fmt(t.runsMerged, h.runs))}</div>` : ""}`, v: timeText },
        { html: esc(trig), v: trig },
        { html: esc(scope) + (h.mailboxes?.length ? `<div class="muted">${esc(h.mailboxes.join(", "))}</div>` : ""), v: scope },
        { html: esc(h.checked ?? 0), v: String(h.checked ?? 0) },
        { html: h.matched ? `<strong>${esc(h.matched)}</strong>` : "0", v: String(h.matched ?? 0) },
        { html: ruleText ? Object.entries(h.rules).map(([n, c]) => `<span class="chip">${esc(n)} · ${esc(c)}</span>`).join("") : "–", v: ruleText },
        {
          html: `<span class="badge ${errors ? "warn" : ""}">${esc(res)}</span>${errors ? `<div class="muted">${esc(h.errors.join("; "))}</div>` : ""}`,
          v: res,
        },
      ];
    });
    const cols = [
      { label: t.colTime, filter: "text" },
      { label: t.colTrigger, filter: "select" },
      { label: t.colScope, filter: "select" },
      { label: t.colChecked, filter: "num" },
      { label: t.colMatched, filter: "num" },
      { label: t.colRules, filter: "text" },
      { label: t.colResult, filter: "select" },
    ];
    const more = s.historyTotal > s.history.length;
    return `<div class="card">
      <h2><span class="grow">${esc(t.history)}</span>
        ${more ? `<button class="secondary" data-action="history-more" ${s.busy ? "disabled" : ""}>${esc(t.showMore)}</button>` : ""}
        <button class="secondary" data-action="history-clear" ${s.busy || !s.history.length ? "disabled" : ""}>${esc(t.clearHistory)}</button></h2>
      <p class="muted" style="margin:0 0 10px">${esc(t.historyHint)}</p>
      ${this._filterTable("runs", cols, rows, t.noHistory)}
    </div>`;
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
      if (e.tool === "icloud_run_rules" || e.client === "rules" || e.client === "rules (auto)") {
        const trig = e.details?.trigger || e.params?.trigger || (e.client === "rules (auto)" ? "auto" : null);
        return [t.whoRules, trig ? (trig === "auto" ? t.triggerAuto : t.triggerManual) : null, e.user].filter(Boolean).join(" · ");
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
    this._s.editing = null;
    this._s.report = null;
    this._s.notice = null;
    await this._call(() => this._reload());
  }

  async _run(scope, dryRun) {
    if (!dryRun && scope === "all" && !confirm(this.t.confirmRun)) return;
    await this._call(async () => {
      this._s.report = await this._ws({ type: "friedafetch/rules/run", entry_id: this._s.entryId, scope, dry_run: dryRun });
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
    const tabs = s.accounts
      .map((a) => {
        const active = a.entry_id === s.entryId;
        const last = a.last_run ? fmtDateTime(a.last_run.finished || a.last_run.started) : t.never;
        const badges = [
          `<span class="badge">${esc(
            a.automation && a.automation.enabled
              ? fmt(t.accountAuto, a.automation.interval) + (a.automation.next_run ? " · " + fmt(t.nextShort, fmtClock(a.automation.next_run)) : "")
              : t.accountManual
          )}</span>`,
          a.automation && a.automation.idle_reason ? `<span class="badge warn">${esc(t.check_no_enabled_rules)}</span>` : "",
          a.read_only ? `<span class="badge warn">${esc(t.accountReadOnly)}</span>` : "",
          a.mail_enabled ? "" : `<span class="badge warn">${esc(t.accountNoMail)}</span>`,
          a.approvals_pending ? `<span class="badge warn">${esc(t.approvals)}: ${a.approvals_pending}</span>` : "",
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
    const s = this._s;
    const newEditor = s.editing && !s.editing.id ? `<div class="rule open" data-rule-id="">${this._renderEditor()}</div>` : "";
    if (!s.rules.length) return newEditor || `<p class="muted">${esc(t.noRules)}</p>`;
    const items = s.rules
      .map((r, i) => {
        const { conds, acts } = this._summary(r);
        const editingThis = s.editing && s.editing.id === r.id;
        const open = editingThis || s.expanded.has(r.id);
        const n = r.conditions.length;
        const meta = [r.mailbox, n === 1 ? t.oneCondition : fmt(t.nConditions, n)];
        if (n > 1) meta.push(r.match === "any" ? t.matchAnyShort : t.matchAllShort);
        const copy =
          s.accounts.length > 1
            ? `<select class="copy" data-action="copy" data-id="${esc(r.id)}" title="${esc(t.copyTo)}"><option value="">${esc(t.copyTo)}</option>${s.accounts
                .filter((a) => a.entry_id !== s.entryId)
                .map((a) => `<option value="${esc(a.entry_id)}">${esc(a.label)}</option>`)
                .join("")}</select>`
            : "";
        const body = editingThis
          ? this._renderEditor()
          : open
            ? `<div class="rule-body">
                <div><div class="lbl">${esc(t.conditions)}</div>${conds}</div>
                <div><div class="lbl">${esc(t.actions)}</div>${acts || `<span class="muted">${esc(t.noActions)}</span>`}${r.actions.stop === false ? `<div class="muted">↓ ${esc(t.continueRules)}</div>` : ""}</div>
                <div class="rule-tools">
                  <button class="secondary" data-action="edit" data-id="${esc(r.id)}" ${s.editing ? "disabled" : ""}>✎ ${esc(t.edit)}</button>
                  <button class="icon" data-action="up" data-id="${esc(r.id)}" ${i === 0 ? "disabled" : ""} title="${esc(t.up)}" aria-label="${esc(t.up)}">▲</button>
                  <button class="icon" data-action="down" data-id="${esc(r.id)}" ${i === s.rules.length - 1 ? "disabled" : ""} title="${esc(t.down)}" aria-label="${esc(t.down)}">▼</button>
                  <button class="icon" data-action="delete" data-id="${esc(r.id)}" title="${esc(t.remove)}" aria-label="${esc(t.remove)}">🗑</button>
                  ${copy}
                </div>
              </div>`
            : "";
        return `<div class="rule ${open ? "open" : ""} ${r.enabled ? "" : "disabled"}" data-rule-id="${esc(r.id)}">
          <div class="rule-head">
            <button class="icon chev" data-action="expand" data-id="${esc(r.id)}" aria-expanded="${open}" aria-label="${esc(r.name)}" ${editingThis ? "disabled" : ""}>▸</button>
            <input type="checkbox" data-action="toggle" data-id="${esc(r.id)}" ${r.enabled ? "checked" : ""} title="${esc(t.enabled)}" aria-label="${esc(t.enabled)}">
            <div class="rule-title" data-action="expand" data-id="${esc(r.id)}"><strong>${esc(r.name)}</strong><span class="muted">${esc(meta.join(" · "))}</span></div>
            <span class="rule-side"><span class="rule-acts">${acts}</span><span class="badge" title="${esc(t.hits)}">${esc(r.hits ?? 0)} ${esc(t.hits)}</span></span>
          </div>
          ${body}
        </div>`;
      })
      .join("");
    return `<div class="rules">${newEditor}${items}</div>`;
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
    return `<div class="editor" id="editor">
      <h3 class="title">${esc(e.id ? t.edit : t.newRule)}</h3>
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
      ${rows ? `<div class="scroll"><table class="stack"><thead><tr><th>${esc(t.uid)}</th><th>${esc(t.subject)}</th><th>${esc(t.from)}</th><th>${esc(t.rule)}</th><th>${esc(t.action)}</th></tr></thead><tbody>${withLabels(rows, [t.uid, t.subject, t.from, t.rule, t.action])}</tbody></table></div>` : ""}
    </div>`;
  }

  _render() {
    const t = this.t;
    const s = this._s;
    const accountSel = "";
    const trig = s.lastRun ? (s.lastRun.trigger === "auto" ? t.triggerAuto : t.triggerManual) : "";
    const last = s.lastRun
      ? `${esc(t.lastRun)}: ${esc(fmtDateTime(s.lastRun.finished || s.lastRun.started))} (${esc(trig)}) · ${s.lastRun.checked} ${esc(t.checked)} · ${s.lastRun.matched} ${esc(t.matched)}`
      : `${esc(t.lastRun)}: ${esc(t.never)}`;
    const au = s.automation;
    const allOpen = s.rules.length > 0 && s.rules.every((r) => s.expanded.has(r.id));
    let autoHtml = "";
    if (au && au.enabled) {
      const parts = [fmt(t.autoEvery, au.interval)];
      if (au.next_run) parts.push(fmt(t.nextRun, fmtClock(au.next_run)));
      if (au.last_check) parts.push(`${fmt(t.lastCheck, fmtClock(au.last_check.time))}: ${t["check_" + au.last_check.result] || au.last_check.result}`);
      autoHtml = `<p class="muted" style="margin:0 0 10px">${esc(parts.join(" · "))}</p>`;
      if (au.idle_reason === "no_enabled_rules") autoHtml += `<div class="info" style="margin-bottom:10px">${esc(t.autoIdle)}</div>`;
    } else if (au) {
      autoHtml = `<div class="info" style="margin-bottom:10px">${esc(t.autoOff)}</div>`;
    }
    const body = !s.loaded
      ? `<p class="muted">${esc(t.loading)}</p>`
      : !s.entryId
        ? `<div class="card"><p>${esc(t.noAccount)}</p></div>`
        : `
      ${s.error ? `<div class="error">${esc(s.error)}</div>` : ""}
      ${s.notice ? `<div class="ok">${esc(s.notice)}</div>` : ""}
      ${this._renderAccounts()}
      <div class="card">
        <h2><span class="grow">${esc(t.rules)}${this._account() ? ` <span class="chip">${esc(this._account().label)}</span>` : ""}</span>
          ${s.rules.length > 1 ? `<button class="secondary" data-action="expand-all" data-open="${allOpen ? "0" : "1"}">${esc(allOpen ? t.collapseAll : t.expandAll)}</button>` : ""}
          <button data-action="new" ${s.editing ? "disabled" : ""}>+ ${esc(t.newRule)}</button></h2>
        ${this._renderRules()}
      </div>
      <div class="card">
        <h2><span class="grow">${esc(t.run)}</span><span class="muted">${last}</span></h2>
        ${autoHtml}
        <div class="actionsbar">
          <button class="secondary" data-action="run" data-scope="all" data-dry="1" ${s.busy ? "disabled" : ""}>${esc(t.dryRunAll)}</button>
          <button data-action="run" data-scope="all" data-dry="0" ${s.busy || this._account()?.read_only ? "disabled" : ""} title="${this._account()?.read_only ? esc(t.accountReadOnly) : ""}">${esc(t.runAll)}</button>
          <button class="secondary" data-action="run" data-scope="new" data-dry="0" ${s.busy || this._account()?.read_only ? "disabled" : ""}>${esc(t.runNew)}</button>
        </div>
      </div>
      ${this._renderReport()}
      ${this._renderHistory()}
      ${this._renderApprovals()}
      ${this._renderActivity()}`;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar"><ha-menu-button></ha-menu-button><img src="${esc(ICON_URL)}" alt=""><span>${esc(t.title)}</span><span class="grow"></span>${accountSel}</div>
      <div class="content">${body}</div>`;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu && this._hass) {
      menu.hass = this._hass;
      menu.narrow = this._narrow;
    }
    this._bind();
    ["runs", "audit"].forEach((key) => this._applyFilters(key));
    this._afterRender();
  }

  // Brings a freshly opened editor or a just-saved rule into view.
  _afterRender() {
    const root = this.shadowRoot;
    const smooth = !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (this._s.focusEditor) {
      this._s.focusEditor = false;
      const ed = root.querySelector("#editor");
      if (ed) {
        requestAnimationFrame(() => {
          ed.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
          root.querySelector("#f-name")?.focus({ preventScroll: true });
        });
      }
    } else if (this._s.scrollTo) {
      const id = this._s.scrollTo;
      this._s.scrollTo = null;
      const el = [...root.querySelectorAll(".rule[data-rule-id]")].find((n) => n.dataset.ruleId === id);
      if (el) {
        requestAnimationFrame(() => {
          el.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "nearest" });
          el.classList.add("flash");
          setTimeout(() => el.classList.remove("flash"), 1600);
        });
      }
    }
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-action]").forEach((el) => {
      const action = el.dataset.action;
      const handler = {
        new: () => {
          this._s.editing = this._blankRule();
          this._s.focusEditor = true;
          this._render();
        },
        edit: () => {
          const rule = this._s.rules.find((r) => r.id === el.dataset.id);
          this._s.editing = JSON.parse(JSON.stringify(rule));
          this._s.focusEditor = true;
          this._render();
        },
        expand: () => {
          const id = el.dataset.id;
          if (this._s.editing && this._s.editing.id === id) return;
          if (this._s.expanded.has(id)) this._s.expanded.delete(id);
          else this._s.expanded.add(id);
          this._render();
        },
        "expand-all": () => {
          this._s.expanded = el.dataset.open === "1" ? new Set(this._s.rules.map((r) => r.id)) : new Set();
          this._render();
        },
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
        "history-more": () => {
          this._s.historyLimit = Math.min(200, this._s.historyLimit + 50);
          this._call(() => this._loadHistory());
        },
        "history-clear": () => this._clearHistory(),
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
          const id = this._s.editing?.id;
          this._s.editing = null;
          if (id) this._s.scrollTo = id;
          this._render();
        },
        run: () => this._run(el.dataset.scope, el.dataset.dry === "1"),
        approve: () => this._decide(el.dataset.id, "approve"),
        deny: () => this._decide(el.dataset.id, "deny"),
        "audit-clear": () => this._clearAudit(),
        "audit-more": () => {
          this._s.auditLimit = Math.min(500, this._s.auditLimit + 50);
          this._call(() => this._loadAudit());
        },
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
