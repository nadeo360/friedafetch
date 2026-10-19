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
    { min: 2, name: "Erika Mustermann", from: "erika@example.com", subject: "Test Frieda", type: "personal", importance: 5 },
    { min: 5, name: "Anna Beispiel", from: "anna@example.com", subject: "Nur ein Test", type: "none" },
    { min: 40, name: "Praxis Dr. Beispiel", from: "praxis@example.com", subject: "Befund", type: "held" },
    { min: 40, name: "Gartenmarkt", from: "news@gartenmarkt.example", subject: "🍁 Nur noch 6 Tage: 15% Rabatt mit Code OKT06 bei Gartenmarkt", type: "news" },
    { min: 40, name: "CI-Server", from: "ci@code.example", subject: "[nadeo360/friedafetch] Run failed: CI - main", type: "ci" },
    { min: 90, name: "Kundenservice Bank", from: "service@bank.example", subject: "Ihr Ratenkredit - letzte Rate im November", type: "bill", importance: 4, corrected: "Persönlich & wichtig" },
    { min: 90, name: "Reiseportal", from: "noreply@reiseportal.example", subject: "Wir werden Ihre Karte bald belasten", type: "bill", importance: 4 },
    { min: 60 * 15, name: "Shop Versand", from: "versand@shop.example", subject: "Ihre Bestellung ist unterwegs", type: "bill" },
    { min: 60 * 17, name: "Möbelhaus", from: "newsletter@moebel.example", subject: "Wochenend-Angebote: bis zu 40 % auf Sofas", type: "news" },
    { min: 60 * 21, name: "Schule Sekretariat", from: "sekretariat@schule.example", subject: "Elternabend am Donnerstag", type: "personal", importance: 4 },
    { min: 60 * 23, name: "Werbung", from: "promo@werbung.example", subject: "Rabatt-Code nur heute", type: "promo" },
  ].map((x) => ({ ...x, time: at(x.min) }));
  if (volume) {
    const midnight = new Date(new Date().toDateString()).getTime();
    let k = 0;
    for (const [daysAgo, n, span] of [[0, 100, now - midnight - 120000], [1, 60, 86400000], [2, 30, 86400000]]) {
      for (let j = 0; j < n; j++, k++) {
        const [name, from, type, subjects] = SENDERS[(k * 7 + j) % SENDERS.length];
        base.push({ name, from, type: k % 17 === 0 && CATS[type] ? "none" : type, subject: subjects[(k + j) % subjects.length], time: new Date(midnight - daysAgo * 86400000 + Math.round(((j + 0.5) / n) * span)).toISOString() });
      }
    }
  }
  base.sort((a, b) => (a.time < b.time ? 1 : -1));
  return base.map((x, i) => {
    const mid = `<mail-${i}@example>`;
    const row = { key: mid, message_id: mid, mailbox: "INBOX", uid: 1000 - i, subject: x.subject, from: x.from, name: x.name, date: x.time, time: x.time, trigger: "push", rules: [], move_to: null, delete: false, seen: null, flag: null, ai: null, day: dayOf(x.time) };
    if (x.type === "ci") Object.assign(row, { rules: ["CI-Meldungen löschen"], delete: true });
    else if (x.type === "promo") Object.assign(row, { rules: ["Werbung & Newsletter löschen"], delete: true });
    else if (x.type === "held") row.ai = { held: ["term"] };
    else if (CATS[x.type]) {
      const [category, importance, applied, reason] = CATS[x.type];
      row.ai = { category: x.corrected || category, importance: x.importance || importance, applied };
      row.reason = reason;
      row.rating_id = `r${i}`;
      row.corrected = !!x.corrected;
      row.original = x.corrected ? category : null;
    }
    row.kind = row.rules.length ? "rule" : row.ai?.held ? "held" : row.ai?.category ? "ai" : "none";
    const moved = (row.ai?.applied || []).find((a) => a.startsWith("moved:"));
    row.folder = row.delete ? TRASH : moved ? (moved.slice(6) === "Deleted Messages" ? TRASH : moved.slice(6)) : "INBOX";
    row.selectable = !!row.message_id && row.kind !== "rule";
    return row;
  });
}

const matches = (row, view, query) => {
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

export function install({ data, q }) {
  const rows = makeRows(!!q.get("volume"));
  window.__rows = rows;
  const ai = data["friedafetch_mail/ai"];
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
      return structuredClone({ items: hits.slice(offset, offset + (m.limit || 50)), total: hits.length, selectable: hits.filter((r) => r.selectable).length, days, counts: { all: rows.length, kinds, folders } });
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
        ev.push({ kind: "rated", time: at(7), category: r.original || r.ai.category, importance: r.ai.importance, reason: r.reason || "" });
        if (r.ai.applied.length) ev.push({ kind: "ai_applied", time: at(8), applied: r.ai.applied });
        if (r.corrected) ev.push({ kind: "corrected", time: at(3600), before: r.original, after: r.ai.category });
      }
      return structuredClone({ message_id: r.message_id, subject: r.subject, sender: r.from, date: r.date, mailbox: "INBOX", location: r.folder === "INBOX" ? null : r.folder, category: r.ai?.category || null, importance: r.ai?.importance || null, rating_id: r.rating_id || null, corrected: !!r.corrected, held: r.kind === "held", found: true, events: ev });
    }
    if (m.type === "friedafetch_mail/ai/correct") {
      const r = rows.find((x) => x.rating_id === m.rating_id);
      if (r) {
        if (!r.original) r.original = r.ai.category;
        r.ai.category = m.category;
        r.corrected = m.category !== r.original;
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
      const results = [...sample.map(([subject, from, before]) => ({ subject, from, before, after: name })), ...Array.from({ length: 20 - sample.length }, (_, k) => ({ subject: `Mail ${k}`, from: "x", before: "Newsletter & Werbung", after: "Newsletter & Werbung" }))];
      ai.status.used_this_hour += 20;
      return { name, tested: 20, held: 0, missing: 0, limit: false, errors: [], results, hits: sample.length };
    }
    return undefined;
  };
}
