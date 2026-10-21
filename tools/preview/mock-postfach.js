// Example backend for the Frieda Postfach preview: activity, timeline, location, correction, category assistant.
// Example data only (example.* addresses); the answers of the "AI" are scripted.

const SENDERS = [
  ["Gartenmarkt", "news@gartenmarkt.example", "news", ["Herbstpflanzen jetzt 20 % günstiger", "Ihr Wochenangebot", "Nur heute: Gratis-Versand"]],
  ["Möbelhaus", "newsletter@moebel.example", "news", ["Neue Kollektion ist da", "Sofa-Wochen: bis zu 40 %", "Ihr persönlicher Gutschein"]],
  ["Shop Versand", "versand@shop.example", "bill", ["Ihre Bestellung ist unterwegs", "Rechnung zu Ihrer Bestellung", "Zustellung heute zwischen 10 und 14 Uhr"]],
  ["Stadtwerke", "rechnung@stadtwerke.example", "bill", ["Ihre Abschlagsrechnung", "Zählerstand bitte melden"]],
  ["Erika Mustermann", "erika@example.com", "personal", ["Kurze Frage zu Samstag", "Fotos vom Wochenende", "Re: Termin nächste Woche"]],
  ["Anna Beispiel", "anna@example.com", "personal", ["Treffen am Donnerstag?", "Danke dir!"]],
  ["Verein Vorstand", "vorstand@verein.example", "personal", ["Einladung zur Mitgliederversammlung", "Protokoll der Sitzung"]],
  ["CI-Server", "ci@code.example", "ci", ["Run failed: CI - main", "Run failed: nightly", "[bot] Bump dependency"]],
  ["Werbung", "promo@werbung.example", "promo", ["Rabatt-Code nur heute", "Sie haben gewonnen!", "Letzte Chance"]],
  ["Reiseportal", "noreply@reiseportal.example", "bill", ["Ihre Buchungsbestätigung", "Check-in jetzt möglich"]],
  ["Praxis Dr. Beispiel", "praxis@example.com", "held", ["Befund", "Terminerinnerung"]],
];
const CATS = { news: ["Newsletter & Werbung", 1, ["moved:Deleted Messages"], "Werblicher Newsletter."], bill: ["Rechnungen & Belege", 3, [], "Beleg oder Versandinformation."], personal: ["Persönlich & wichtig", 4, ["flagged", "notified"], "Persönliche Nachricht eines Kontakts."] };
const TRASH = "trash";
const pad = (n) => String(n).padStart(2, "0");
const dayOf = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

function makeRows(volume) {
  const now = Date.now();
  const at = (min) => new Date(now - min * 60000).toISOString();
  const base = [
    { id: "test-frieda", min: 2, name: "Erika Mustermann", from: "erika@example.com", subject: "Test Frieda", type: "personal", importance: 5 },
    { id: "nur-ein-test", min: 5, name: "Anna Beispiel", from: "anna@example.com", subject: "Nur ein Test", type: "none" },
    { id: "befund", min: 40, name: "Praxis Dr. Beispiel", from: "praxis@example.com", subject: "Befund", type: "held" },
    { id: "gartenmarkt-rabatt", min: 40, name: "Gartenmarkt", from: "news@gartenmarkt.example", subject: "🍁 Nur noch 6 Tage: 15% Rabatt mit Code OKT06 bei Gartenmarkt", type: "news" },
    { id: "ci-run-failed", min: 40, name: "CI-Server", from: "ci@code.example", subject: "[nadeo360/friedafetch] Run failed: CI - main", type: "ci" },
    { id: "ratenkredit", min: 90, name: "Kundenservice Bank", from: "service@bank.example", subject: "Ihr Ratenkredit - letzte Rate im November", type: "bill", importance: 4, corrected: "Persönlich & wichtig" },
    { id: "karte-belasten", min: 90, name: "Reiseportal", from: "noreply@reiseportal.example", subject: "Wir werden Ihre Karte bald belasten", type: "bill", importance: 4, confidence: "low" },
    { id: "bestellung-unterwegs", min: 60 * 15, name: "Shop Versand", from: "versand@shop.example", subject: "Ihre Bestellung ist unterwegs", type: "bill", confidence: "low" },
    { id: "moebel-wochenende", min: 60 * 17, name: "Möbelhaus", from: "newsletter@moebel.example", subject: "Wochenend-Angebote: bis zu 40 % auf Sofas", type: "news", confidence: "medium" },
    { id: "elternabend", min: 60 * 21, name: "Schule Sekretariat", from: "sekretariat@schule.example", subject: "Elternabend am Donnerstag", type: "personal", importance: 4, gone: true },
    { id: "rabatt-code", min: 60 * 23, name: "Werbung", from: "promo@werbung.example", subject: "Rabatt-Code nur heute", type: "promo" },
  ].map((x) => ({ ...x, time: at(x.min) }));
  if (volume) {
    const midnight = new Date(new Date().toDateString()).getTime();
    let k = 0;
    for (const [daysAgo, n, span] of [[0, 100, now - midnight - 120000], [1, 60, 86400000], [2, 30, 86400000]]) {
      for (let j = 0; j < n; j++, k++) {
        const [name, from, type, subjects] = SENDERS[(k * 7 + j) % SENDERS.length];
        const kind = k % 17 === 0 && CATS[type] ? "none" : type;
        const corrected = kind === "bill" && k % 23 === 5 ? "Persönlich & wichtig" : undefined;
        base.push({ id: `vol-${k}`, name, from, type: kind, corrected, confidence: k % 9 === 4 ? "low" : "high", subject: subjects[(k + j) % subjects.length], time: new Date(midnight - daysAgo * 86400000 + Math.round(((j + 0.5) / n) * span)).toISOString() });
      }
    }
  }
  base.sort((a, b) => (a.time < b.time ? 1 : -1));
  return base.map((x, i) => {
    const mid = `<${x.id}@example>`;
    const row = { key: mid, message_id: mid, mailbox: "INBOX", uid: 1000 - i, subject: x.subject, from: x.from, name: x.name, date: x.time, time: x.time, updated: x.time, trigger: "push", rules: [], move_to: null, delete: false, seen: null, flag: null, ai: null, day: dayOf(x.time) };
    if (x.type === "ci") Object.assign(row, { rules: ["CI-Meldungen löschen"], delete: true });
    else if (x.type === "promo") Object.assign(row, { rules: ["Werbung & Newsletter löschen"], delete: true });
    else if (x.type === "held") row.ai = { category: null, importance: null, confidence: null, applied: [], held: ["term"] };
    else if (CATS[x.type]) {
      const [category, importance, applied, reason] = CATS[x.type];
      row.ai = { category: x.corrected || category, importance: x.importance || importance, confidence: x.confidence || "high", applied, held: null };
      row.reason = reason;
      row.rating_id = `r${i}`;
      row.corrected = !!x.corrected;
      row.original = x.corrected ? category : null;
    }
    row.kind = row.rules.length ? "rule" : row.ai?.held ? "held" : row.ai?.category ? "ai" : "none";
    const moved = (row.ai?.applied || []).find((a) => a.startsWith("moved:"));
    row.folder = row.delete ? TRASH : moved ? (moved.slice(6) === "Deleted Messages" ? TRASH : moved.slice(6)) : "INBOX";
    row.selectable = !!row.message_id && row.kind !== "rule";
    row.unsure = row.kind === "ai" && row.ai.confidence === "low" && !row.corrected;
    // read / flagged as the mailbox has it (mailstate.py): the newest ones still unread, flagged personal mails
    // (one was moved out of the inbox on another device: it keeps the state it had there)
    row.state = row.folder === "INBOX" ? { seen: i >= 2 && i !== 6, flagged: (row.ai?.applied || []).includes("flagged"), gone: !!x.gone, checked: new Date(now).toISOString() } : null;
    return row;
  });
}

const matches = (row, view, query) => {
  if (view === "unsure" && !row.unsure) return false;
  if (view.startsWith("k:") && row.kind !== view.slice(2)) return false;
  if (view.startsWith("f:") && row.folder !== view.slice(2)) return false;
  if (!query) return true;
  const hay = [row.subject, row.from, row.name, row.ai?.category, ...(row.rules || [])].join(" ").toLowerCase();
  return query.toLowerCase().split(/\s+/).every((w) => hay.includes(w));
};

// the scripted "AI" of the category assistant
const TOPICS = [
  { test: /steuer|finanzamt|elster|tax/, name: "Steuer & Finanzamt", description: "Mails vom Steuerberater und vom Finanzamt (auch ELSTER): Steuerbescheide, Rückfragen und Unterlagen für die Steuererklärung. Normale Rechnungen gehören nicht hierher.", overlap: "Rechnungen & Belege",
    sample: [["Ihr Steuerbescheid 2025", "Finanzamt Musterstadt", "Rechnungen & Belege"], ["ELSTER: Bestätigung Ihrer Übermittlung", "elster.example", "Persönlich & wichtig"], ["Rückfrage zu Ihren Belegen", "Kanzlei Beispiel", "Persönlich & wichtig"]] },
  { test: /paket|sendung|zustell|liefer|versand|parcel/, name: "Pakete & Lieferungen", description: "Versand- und Zustellnachrichten von Paketdiensten und Shops: Sendungsverfolgung, Zustellfenster, Abholung in der Filiale. Rechnungen gehören nicht hierher.", overlap: "Rechnungen & Belege",
    sample: [["Ihre Bestellung ist unterwegs", "Shop Versand", "Rechnungen & Belege"], ["Zustellung heute zwischen 10 und 14 Uhr", "Shop Versand", "Rechnungen & Belege"], ["Ihr Paket liegt in der Filiale", "Paketdienst", "Persönlich & wichtig"], ["Sendung zugestellt", "Paketdienst", "Rechnungen & Belege"]] },
  { test: /verein|vorstand|mitglied|club/, name: "Verein", description: "Mails vom Vorstand und von Mitgliedern des Vereins: Einladungen, Protokolle, Termine und Rundschreiben.", overlap: "Persönlich & wichtig",
    sample: [["Einladung zur Mitgliederversammlung", "Verein Vorstand", "Persönlich & wichtig"], ["Protokoll der Sitzung", "Verein Vorstand", "Newsletter & Werbung"]] },
];

function assist(m, mailboxes) {
  const turns = m.conversation || [];
  const said = turns.filter((x) => x.role === "user").map((x) => x.text);
  const last = (said[said.length - 1] || "").toLowerCase();
  const all = said.join(" ").toLowerCase();
  const topic = TOPICS.find((x) => x.test.test(all));
  const folderName = { Archive: "archiv", Junk: "werbung", "Deleted Messages": "papierkorb" };
  let p = m.proposal ? { ...m.proposal } : null;
  const first = !p;
  if (!p) {
    const words = said[0].replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/).slice(0, 3).join(" ");
    p = topic ? { name: topic.name, description: topic.description, move_to: null, mark_seen: false, flag: false } : { name: words.charAt(0).toUpperCase() + words.slice(1), description: `Mails zu: ${said[0]}`.slice(0, 300), move_to: null, mark_seen: false, flag: false };
  }
  if (/nicht (mehr )?(verschieb|ins|in den)|nur markier/.test(last)) p.move_to = null;
  else {
    const box = mailboxes.find((b) => b !== "INBOX" && (last.includes(b.toLowerCase()) || (folderName[b] && last.includes(folderName[b]))));
    if (box) p.move_to = box;
  }
  if (/nicht markier/.test(last)) p.flag = false;
  else if (/markier/.test(last) && !/gelesen/.test(last.split("markier")[0].slice(-20))) p.flag = true;
  if (/gelesen/.test(last)) p.mark_seen = !/nicht als gelesen|ungelesen/.test(last);
  if (/lohn|gehalt/.test(last) && !/Lohn/.test(p.description)) p.description = `${p.description} Auch Lohn- und Gehaltsabrechnungen.`.slice(0, 300);
  const what = [p.move_to ? `nach „${p.move_to === "Archive" ? "Archiv" : p.move_to}“ verschieben` : "", p.flag ? "markieren" : "", p.mark_seen ? "als gelesen markieren" : ""].filter(Boolean);
  const reply = first
    ? `Mein Vorschlag: eine Kategorie „${p.name}“. ${what.length ? `Solche Mails würde ich ${what.join(" und ")}.` : "Mit den Mails passiert erst einmal nichts – sie werden nur einsortiert."}${topic?.overlap ? ` „${topic.overlap}“ ist ähnlich; die Beschreibung grenzt die beiden ab.` : ""}`
    : "Angepasst – schau dir den Vorschlag an.";
  return { reply, proposal: p, overlap: topic?.overlap || null, topic };
}

// Runs, ratings and the AI log as the backend keeps them – built from the same mails as the activity.
function derive(data, rows) {
  const ai = data["friedafetch_mail/ai"];
  const account = data["friedafetch_mail/accounts"].accounts[0];
  const rules = data["friedafetch_mail/rules/list"].rules;
  const automation = { enabled: true, interval: 5, enabled_rules: rules.filter((r) => r.enabled).length, push: { state: "listening" }, next_run: null, last_check: { time: new Date().toISOString(), result: "ran", error: null }, idle_reason: null };
  Object.assign(data["friedafetch_mail/rules/list"], { entry_id: "e1", automation });
  for (const r of rules) Object.assign(r, { created: r.created || "2026-09-01T10:00:00+02:00", actions: { attachments_folder: null, ...r.actions } });
  data["friedafetch_mail/accounts"].version = "__BUILD__"; // the panel's own build: no "new version" hint
  Object.assign(account, { automation, core_entry_id: "e1", rules_total: rules.length, rules_enabled: rules.filter((r) => r.enabled).length, digest_time: "07:30", last_run: data["friedafetch_mail/rules/list"].last_run });
  // iCloud's folders (the trash is "Deleted Messages"), plus two of the user's own
  data["friedafetch_mail/mailboxes"] = { mailboxes: ["INBOX", "Archive", "Belege", "Company", "Drafts", "Sent Messages", "Junk", "Deleted Messages"] };
  Object.assign(ai.status, { include_body: false, body_chars: 1000, excluded: 2, block_terms: 3, last_run: rows.find((r) => r.kind === "ai")?.time || null, last_error: null });
  ai.ratings = rows
    .filter((r) => r.kind === "ai")
    .map((r) => ({ id: r.rating_id, time: r.time, mailbox: "INBOX", uid: r.uid, message_id: r.message_id, subject: r.subject, from: r.name, from_domain: r.from.split("@")[1], date: r.date, mode: "act", category: r.original || r.ai.category, importance: r.ai.importance, confidence: r.ai.confidence, reason: r.reason, applied: r.ai.applied, corrected: r.original ? r.ai.category : null, suspicious: false }))
    .reverse();
  ai.examples = rows.filter((r) => r.corrected).length;
  ai.corrected = ai.examples;
  ai.batch = ai.batch ?? null;
  // the AI log: one transmission per rated mail, one hold per kill-switch mail, the daily overview, one failure
  const sort = rows
    .filter((r) => r.kind === "ai" || r.kind === "held")
    .map((r) => (r.kind === "held"
      ? { time: r.time, kind: "sort", entity: "ai_task.mein_ki_modell", trigger: r.trigger, sent: false, ok: true, held_back: [{ type: "term", value: "Diagnose", where: ["subject"] }], fields: [], chars: 0, sender: r.from, subject: r.subject, message_id: r.message_id }
      : { time: r.time, kind: "sort", entity: "ai_task.mein_ki_modell", trigger: r.trigger, sent: true, ok: true, fields: ["from", "to", "subject", "date"], chars: 1300 + (r.subject.length * 7) % 400, duration: 3.4, sender: r.from, subject: r.subject, message_id: r.message_id }));
  const at = (min) => new Date(Date.now() - min * 60000).toISOString();
  const log = [...sort, { time: at(60 * 20), kind: "digest", entity: "ai_task.mein_ki_modell", trigger: "auto", sent: true, ok: true, fields: ["unread", "events", "birthdays", "rules"], chars: 3120, items: 14 },
    { time: at(60 * 26), kind: "sort", entity: "ai_task.mein_ki_modell", trigger: "push", sent: true, ok: false, error: "Quota exceeded for the Gemini API", fields: ["from", "to", "subject", "date"], chars: 1350, sender: "noreply@reiseportal.example", subject: "Sie haben eine Nachricht von Ihrem Hotel" }]
    .sort((a, b) => (a.time < b.time ? 1 : -1));
  const blank = { error: null, held_back: null, items: null, duration: null, message_id: null, sender: "", subject: "" };
  ai.usage = { ...usageWindows(log), log: log.map((e) => ({ ...blank, ...e })) };
  // the runs: one pass per arrival time (push), plus a merged idle stretch and a pass that failed
  const passes = new Map();
  for (const r of [...rows].reverse()) {
    if (!passes.has(r.time)) passes.set(r.time, []);
    passes.get(r.time).push(r);
  }
  const runs = [...passes.entries()].map(([time, mails]) => {
    const perRule = {};
    for (const m of mails) for (const rule of m.rules) perRule[rule] = (perRule[rule] || 0) + 1;
    const rated = mails.filter((m) => m.kind === "ai");
    return { started: time, finished: time, trigger: "push", scope: "new", mailboxes: ["INBOX"], checked: mails.length, matched: mails.filter((m) => m.rules.length).length, actions: mails.filter((m) => m.rules.length).length, rules: perRule,
      ai: rated.length || mails.some((m) => m.kind === "held") ? { rated: rated.length, applied: rated.filter((m) => m.ai.applied.length).length, held: mails.filter((m) => m.kind === "held").length, errors: [] } : null,
      mails: mails.map((m) => ({ subject: m.subject, from: m.from, name: m.name, mailbox: "INBOX", uid: m.uid, message_id: m.message_id, date: m.date, rules: m.rules, move_to: null, delete: m.delete, seen: null, flag: null, ai: m.ai ? { category: m.ai.category, importance: m.ai.importance, confidence: m.ai.confidence, applied: m.ai.applied, held: m.ai.held } : null })),
      mails_more: 0, errors: [], skipped: 0, saved_files: 0, idle: false, runs: 1 };
  });
  runs.push({ started: at(300), finished: at(120), trigger: "auto", scope: "new", mailboxes: ["INBOX"], checked: 0, matched: 0, rules: {}, ai: null, mails: [], mails_more: 0, errors: [], idle: true, runs: 15 });
  runs.push({ started: at(900), finished: at(900), trigger: "auto", scope: "new", mailboxes: ["INBOX"], checked: 2, matched: 0, rules: {}, ai: null, mails: [], mails_more: 0, errors: ["IMAP operation failed: timeout"], idle: false, runs: 1 });
  for (const r of runs) Object.assign(r, { actions: r.actions ?? r.matched, skipped: r.skipped ?? 0, saved_files: r.saved_files ?? 0 });
  runs.sort((a, b) => (a.started < b.started ? 1 : -1));
  runs.forEach((r, i) => (r.id = runs.length - i));
  const history = data["friedafetch_mail/rules/history"];
  history.runs = runs.slice(0, 200);
  history.total = history.runs.length;
  history.current = history.current ?? null;
}

function usageWindows(log) {
  const win = (days) => {
    const since = Date.now() - days * 86400000;
    const w = { calls: 0, chars: 0, body: 0, held_back: 0, errors: 0, sort: 0, digest: 0, assist: 0, entities: {} };
    for (const e of log) {
      if (new Date(e.time).getTime() < since) continue;
      if (!e.sent) { w.held_back += 1; continue; }
      w.calls += 1;
      w.chars += e.chars || 0;
      w[e.kind] = (w[e.kind] || 0) + 1;
      if ((e.fields || []).includes("body")) w.body += 1;
      if (e.ok === false) w.errors += 1;
      w.entities[e.entity] = (w.entities[e.entity] || 0) + 1;
    }
    return w;
  };
  return { today: win(1), week: win(7), month: win(30) };
}

export function install({ data, q }) {
  const rows = makeRows(!!q.get("volume"));
  window.__rows = rows;
  derive(data, rows);
  const ai = data["friedafetch_mail/ai"];
  const live = (topic) => window.__live?.["friedafetch_mail/subscribe"]?.({ entry_id: "e1", topic });
  const rulesList = data["friedafetch_mail/rules/list"];
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const find = (mid) => rows.find((r) => r.message_id === mid);

  return async function handle(m) {
    if (m.type === "friedafetch_mail/activity/list") {
      const view = m.view || "all";
      const query = (m.query || "").trim();
      const kinds = { ai: 0, rule: 0, held: 0, none: 0 };
      const folders = {};
      for (const r of rows) {
        kinds[r.kind] += 1;
        folders[r.folder] = (folders[r.folder] || 0) + 1;
      }
      const hits = rows.filter((r) => matches(r, view, query));
      const days = [];
      for (const r of hits) {
        let d = days.find((x) => x.day === r.day);
        if (!d) days.push((d = { day: r.day, total: 0, selectable: 0 }));
        d.total += 1;
        d.selectable += r.selectable ? 1 : 0;
      }
      const offset = m.offset || 0;
      const unsure = rows.filter((r) => r.unsure).length;
      return structuredClone({ items: hits.slice(offset, offset + (m.limit || 50)), total: hits.length, selectable: hits.filter((r) => r.selectable).length, days, counts: { all: rows.length, unsure, kinds, folders } });
    }
    if (m.type === "friedafetch_mail/activity/select") {
      return { messages: rows.filter((r) => matches(r, m.view || "all", (m.query || "").trim()) && r.selectable && (!m.day || r.day === m.day)).map((r) => ({ key: r.key, message_id: r.message_id, mailbox: r.mailbox })) };
    }
    if (m.type === "friedafetch_mail/activity/clear") {
      rows.length = 0;
      return { cleared: true };
    }
    if (m.type === "friedafetch_mail/mail/locate") {
      await wait(Number(q.get("locslow") || 700));
      const i = rows.findIndex((r) => r.message_id === m.message_id);
      const r = rows[i];
      const checked = new Date().toISOString();
      if (!r || i % 13 === 7) return { found: false, mailbox: null, trash: false, checked };
      const place = i % 6 === 5 ? (r.folder === "Archive" ? "INBOX" : "Archive") : r.folder;
      return place === TRASH ? { found: true, mailbox: "Deleted Messages", trash: true, checked } : { found: true, mailbox: place, trash: false, checked };
    }
    if (m.type === "friedafetch_mail/mail/timeline") {
      await wait(Number(q.get("tlslow") || 50));
      const r = find(m.message_id) || rows.find((x) => x.subject === m.subject);
      if (!r) return { subject: m.subject, sender: m.sender, found: false, events: [] };
      const t0 = new Date(new Date(r.time).getTime() - 40000);
      const at = (s) => new Date(t0.getTime() + s * 1000).toISOString();
      const ev = [{ kind: "received", time: at(0), mailbox: "INBOX" }, { kind: "checked", time: at(2), trigger: r.trigger, rules: r.rules, delete: r.delete, move_to: r.move_to, count: 1 }];
      if (r.kind === "held") ev.push({ kind: "ai_held", time: at(3), reasons: [{ type: "term", value: "Diagnose", where: ["subject"] }] });
      if (r.kind === "ai") {
        ev.push({ kind: "ai_sent", time: at(3), entity: "ai_task.mein_ki_modell", ok: true, chars: 1480, duration: 3.4, fields: ["from", "to", "subject", "date"] });
        ev.push({ kind: "rated", time: at(7), category: r.original || r.ai.category, importance: r.ai.importance, confidence: r.ai.confidence, reason: r.reason || "" });
        if (r.ai.applied.length) ev.push({ kind: "ai_applied", time: at(8), applied: r.ai.applied });
        if (r.corrected) ev.push({ kind: "corrected", time: at(3600), before: r.original, after: r.ai.category });
        if (r.rerated) ev.push({ kind: "rated", again: true, time: r.rerated, category: r.ai.category, importance: r.ai.importance, confidence: r.ai.confidence, reason: r.reason || "" });
      }
      return structuredClone({ message_id: r.message_id, subject: r.subject, sender: r.from, date: r.date, mailbox: "INBOX", location: r.folder === "INBOX" ? null : r.folder, category: r.ai?.category || null, importance: r.ai?.importance || null, confidence: r.ai?.confidence || null, rating_id: r.rating_id || null, corrected: !!r.corrected, held: r.kind === "held", found: true, events: ev });
    }
    if (m.type === "friedafetch_mail/ai/correct") {
      const r = rows.find((x) => x.rating_id === m.rating_id);
      if (r) {
        if (!r.original) r.original = r.ai.category;
        r.ai.category = m.category;
        r.corrected = m.category !== r.original;
        r.unsure = r.ai.confidence === "low" && !r.corrected;
        ai.corrected = rows.filter((x) => x.corrected).length;
      }
      return { rating: { id: m.rating_id, corrected: m.category } };
    }
    if (m.type === "friedafetch_mail/ai/categories") {
      ai.categories = m.categories.map((c, i) => ({ id: c.id || `n${i}`, ...c }));
      return structuredClone(ai);
    }
    if (m.type === "friedafetch_mail/ai/assist") {
      await wait(Number(q.get("aislow") || 900));
      const res = assist(m, data["friedafetch_mail/mailboxes"].mailboxes);
      ai.status.used_this_hour += 1;
      ai.usage.log.unshift({ time: new Date().toISOString(), kind: "assist", entity: "ai_task.mein_ki_modell", trigger: "panel", sent: true, ok: true, fields: ["conversation", "categories", "folders"], chars: 1210, duration: 2.1, sender: "", subject: "" });
      window.__assistTopic = res.topic;
      return { reply: res.reply, proposal: res.proposal, overlap: res.overlap };
    }
    if (m.type === "friedafetch_mail/ai/assist/test") {
      await wait(Number(q.get("aislow") || 1500));
      const name = m.proposal.name;
      const sample = (window.__assistTopic?.sample || []).slice(0, (m.proposal.description || "").toLowerCase().includes("lohn") ? 3 : 2);
      const results = [...sample.map(([subject, from, before]) => ({ subject, from, before, after: name })), ...Array.from({ length: 20 - sample.length }, (_, k) => ({ subject: `Mail ${k}`, from: "x", before: "Newsletter & Werbung", after: "Newsletter & Werbung" }))]
        .map((r) => ({ ...r, first: r.before, expected: null, confidence: "high" }));
      ai.status.used_this_hour += 20;
      return { name, tested: 20, held: 0, missing: 0, limit: false, errors: [], results, hits: sample.length };
    }
    if (m.type === "friedafetch_mail/ai/check") {
      await wait(Number(q.get("aislow") || 1500));
      const corrected = rows.filter((r) => r.corrected).slice(0, 20);
      // the scripted AI: every third one still lands in the category it picked first
      const results = corrected.map((r, i) => ({ subject: r.subject, from: r.name, before: r.ai.category, first: r.original, expected: r.ai.category, after: i % 3 === 2 ? r.original : r.ai.category, confidence: i % 3 === 2 ? "low" : "high" }));
      ai.status.used_this_hour += results.length;
      return { entity: m.entity || ai.status.entity, corrected: corrected.length, tested: results.length, held: 0, missing: 0, limit: false, errors: [], results, hits: results.filter((x) => x.after === x.expected).length };
    }
    if (m.type === "friedafetch_mail/ai/rerate") {
      // works through the messages, one per tick, and reports live – like the background task
      const keys = [...(m.rating_ids || []).map((id) => rows.find((r) => r.rating_id === id)?.message_id), ...(m.messages || []).map((x) => x.message_id)].filter(Boolean);
      ai.batch = { state: "running", total: keys.length, done: 0, rated: 0, held: 0, missing: 0, applied: 0, errors: [], apply: !!m.apply, started: new Date().toISOString(), finished: null, resume_at: null };
      const waitAfter = Number(q.get("waitafter") || 0);
      let waited = 0;
      const tick = () => {
        const b = ai.batch;
        if (b.state === "waiting") {
          if (++waited < 3) return setTimeout(tick, Number(q.get("tick") || 1200));
          Object.assign(b, { state: "running", resume_at: null });
        }
        if (b.state !== "running") return;
        if (waitAfter && b.done === waitAfter && !waited) {
          const next = new Date();
          next.setHours(next.getHours() + 1, 0, 0, 0);
          Object.assign(b, { state: "waiting", resume_at: next.toISOString() });
          live("ai");
          return setTimeout(tick, Number(q.get("tick") || 1200));
        }
        const r = find(keys[b.done]);
        if (r?.kind === "held") b.held += 1;
        else if (r) {
          r.rerated = new Date().toISOString();
          b.rated += 1;
          if (m.apply && r.ai?.applied?.length) b.applied += 1;
        } else b.missing += 1;
        b.done += 1;
        if (b.done >= b.total) {
          b.state = "done";
          b.finished = new Date().toISOString();
          live("activity");
        }
        live("ai");
        if (b.state === "running") setTimeout(tick, Number(q.get("tick") || 1200));
      };
      setTimeout(tick, Number(q.get("tick") || 1200));
      return structuredClone(ai);
    }
    if (m.type === "friedafetch_mail/ai/rerate/cancel") {
      if (["running", "waiting"].includes(ai.batch?.state)) Object.assign(ai.batch, { state: "cancelled", finished: new Date().toISOString(), resume_at: null });
      return structuredClone(ai);
    }
    if (m.type === "friedafetch_mail/ai/run") {
      await wait(800);
      ai.status.used_this_hour += 1;
      return structuredClone({ report: { trigger: "manual", rated: 1, applied: 0, skipped: 0, errors: [], items: [] }, ...ai });
    }
    if (m.type === "friedafetch_mail/ai/clear") {
      ai.ratings = [];
      return structuredClone(ai);
    }
    if (m.type === "friedafetch_mail/ai/usage/clear") {
      ai.usage = { ...usageWindows([]), log: [] };
      return structuredClone(ai);
    }
    if (m.type === "friedafetch_mail/rules/create") {
      const rule = { ...m.rule, id: `r${Date.now().toString(36)}`, hits: 0, created: new Date().toISOString() };
      rulesList.rules.push(rule);
      return { rule };
    }
    if (m.type === "friedafetch_mail/rules/update") {
      const rule = rulesList.rules.find((r) => r.id === m.rule_id);
      Object.assign(rule, m.changes);
      return { rule };
    }
    if (m.type === "friedafetch_mail/rules/delete") {
      rulesList.rules = rulesList.rules.filter((r) => r.id !== m.rule_id);
      return { deleted: true };
    }
    if (m.type === "friedafetch_mail/rules/history/clear") {
      data["friedafetch_mail/rules/history"].runs = [];
      return { cleared: true };
    }
    if (m.type === "friedafetch_mail/rules/run") {
      // the example mails the enabled rules hit (all of them in a dry run, nothing changes here)
      await wait(600);
      const active = rulesList.rules.filter((r) => r.enabled && (!m.rule_ids || m.rule_ids.includes(r.id)));
      const actions = rows
        .filter((r) => r.rules.length)
        .flatMap((r) => active.filter((rule) => r.rules.includes(rule.name)).map((rule) => ({ uid: r.uid, mailbox: "INBOX", subject: r.subject, from: [r.from], message_id: r.message_id, rule: rule.name, rule_id: rule.id, ...rule.actions })));
      const now = new Date().toISOString();
      return { scope: m.scope || "all", trigger: "manual", dry_run: !!m.dry_run, started: now, finished: now, checked_mails: [], checked: m.scope === "new" ? 0 : rows.length, matched: m.scope === "new" ? 0 : actions.length, actions: m.scope === "new" ? [] : actions, skipped: [], errors: [] };
    }
    return undefined;
  };
}
