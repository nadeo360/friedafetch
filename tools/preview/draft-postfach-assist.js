// DRAFT (dev preview only): describe a new AI category in your own words, Frieda turns it into a proposal.
// The answers here are scripted examples; later one websocket command per turn would ask the AI entity for structured
// JSON (name, description, folder, mark seen, flag), checked like a normal save. Only the user's text, the names of the
// categories and the folder names would go to the AI – no mails.
import { UI_STYLE, esc, ico, toast } from "./frieda/ui.js?v=__BUILD__";
import { STYLE } from "./postfach/styles.js?v=__BUILD__";

const CSS = `
  :host { position: fixed; inset: 0; z-index: 30; display: block; }
  .bd { position: absolute; inset: 0; background: rgba(0,0,0,.36); }
  .dlg { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(900px, 94vw); height: min(660px, 90vh);
    display: grid; grid-template-rows: auto minmax(0, 1fr); background: var(--card-background-color, #fff); color: var(--primary-text-color);
    border-radius: 20px; box-shadow: 0 24px 70px rgba(0,0,0,.3); overflow: hidden; }
  .top { display: flex; align-items: center; gap: 10px; padding: 14px 14px 12px 20px; border-bottom: 1px solid var(--divider-color, #e0e0e0); --mdc-icon-size: 20px; }
  .top h2 { margin: 0; font-size: 17px; font-weight: 600; flex: 1; }
  .top > ha-icon { color: var(--frieda-text-ai); }
  .top .views { display: none; }
  .body { display: grid; grid-template-columns: minmax(0, 1fr) 340px; min-height: 0; }

  /* the conversation */
  .chat { display: grid; grid-template-rows: minmax(0, 1fr) auto; min-height: 0; }
  .log { overflow: auto; padding: 18px 20px 8px; display: flex; flex-direction: column; gap: 10px; overscroll-behavior: contain;
    scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--secondary-text-color) 40%, transparent) transparent; }
  .msg { max-width: 86%; padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.45; white-space: pre-line; overflow-wrap: anywhere; }
  .msg.me { align-self: flex-end; background: color-mix(in srgb, var(--primary-color) 16%, transparent); border-bottom-right-radius: 6px; }
  .msg.ai { align-self: flex-start; background: var(--secondary-background-color); border-bottom-left-radius: 6px; }
  .msg.ai .who { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 12px; font-weight: 600; color: var(--frieda-text-ai); --mdc-icon-size: 14px; }
  .msg .changes { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
  .msg .changes span { font-size: 12px; padding: 1px 8px; border-radius: 10px; background: color-mix(in srgb, var(--frieda-ai-color, #8e6bd8) 14%, transparent); color: var(--frieda-text-ai); }
  .msg.warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 13%, var(--secondary-background-color)); }
  .typing { align-self: flex-start; display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--secondary-text-color); padding: 4px 6px; }
  .typing .spinner { width: 14px; height: 14px; border-width: 2px; }
  .compose { padding: 8px 16px 12px; border-top: 1px solid var(--divider-color, #e0e0e0); display: grid; gap: 8px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chips button { border: 1px solid var(--divider-color, #e0e0e0); background: none; color: var(--primary-text-color); border-radius: 16px; padding: 5px 12px;
    font: inherit; font-size: 13px; min-height: 0; cursor: pointer; text-align: left; }
  .chips button:hover { background: var(--secondary-background-color); }
  .row { display: flex; align-items: flex-end; gap: 8px; }
  textarea { flex: 1; min-width: 0; resize: none; box-sizing: border-box; min-height: 42px; max-height: 120px; padding: 10px 12px; border-radius: 14px;
    border: 1px solid var(--divider-color, #e0e0e0); background: var(--secondary-background-color); color: var(--primary-text-color); font: inherit; font-size: 14px; line-height: 1.4; }
  textarea:focus { outline: 2px solid color-mix(in srgb, var(--primary-color) 55%, transparent); outline-offset: 0; }
  button.send { width: 42px; height: 42px; border-radius: 50%; padding: 0; display: inline-grid; place-items: center; --mdc-icon-size: 20px; flex: none; }
  .privacy { display: flex; gap: 6px; align-items: flex-start; font-size: 12px; color: var(--secondary-text-color); --mdc-icon-size: 14px; }
  .privacy ha-icon { flex: none; margin-top: 1px; }

  /* the proposal */
  .pane { border-left: 1px solid var(--divider-color, #e0e0e0); display: grid; grid-template-rows: minmax(0, 1fr) auto; min-height: 0;
    background: color-mix(in srgb, var(--secondary-background-color) 40%, var(--card-background-color, #fff)); }
  .prop { overflow: auto; padding: 18px 18px 10px; display: grid; gap: 12px; align-content: start; }
  .prop h3 { margin: 0; font-size: 11.5px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: var(--secondary-text-color); }
  .empty { color: var(--secondary-text-color); font-size: 13.5px; line-height: 1.5; }
  .f { display: grid; gap: 4px; }
  .f > span { font-size: 12.5px; color: var(--secondary-text-color); }
  .f input[type=text], .f textarea, .f select { width: 100%; box-sizing: border-box; border-radius: 10px; border: 1px solid var(--divider-color, #e0e0e0);
    background: var(--card-background-color, #fff); color: var(--primary-text-color); font: inherit; font-size: 14px; padding: 8px 10px; min-height: 0; }
  .f textarea { min-height: 96px; max-height: none; resize: vertical; background: var(--card-background-color, #fff); }
  .f.flash input, .f.flash textarea, .f.flash select, label.opt.flash { animation: flash 1.6s ease-out; }
  @keyframes flash { 0% { box-shadow: 0 0 0 3px color-mix(in srgb, var(--frieda-ai-color, #8e6bd8) 45%, transparent); } 100% { box-shadow: 0 0 0 3px transparent; } }
  label.opt { display: flex; align-items: center; gap: 10px; font-size: 14px; border-radius: 10px; }
  .f .count { justify-self: end; font-size: 11.5px; color: var(--secondary-text-color); }
  .err { color: var(--frieda-text-err); font-size: 12.5px; }
  .test { border-top: 1px solid var(--divider-color, #e0e0e0); padding-top: 12px; display: grid; gap: 8px; }
  .test p { margin: 0; font-size: 12.5px; color: var(--secondary-text-color); }
  .test ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .test li { display: grid; padding: 7px 10px; border-radius: 10px; background: var(--card-background-color, #fff); font-size: 13px; }
  .test li small { color: var(--secondary-text-color); font-size: 12px; }
  .test .working { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--secondary-text-color); }
  .test .working .spinner { width: 14px; height: 14px; border-width: 2px; }
  .acts { display: flex; gap: 8px; justify-content: flex-end; padding: 12px 18px 16px; border-top: 1px solid var(--divider-color, #e0e0e0); }
  button:focus-visible, textarea:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

  /* phone: a tall sheet; conversation and proposal take turns */
  @media (max-width: 760px) {
    .dlg { left: 0; right: 0; top: auto; bottom: 0; transform: none; width: 100vw; height: 94vh; border-radius: 18px 18px 0 0; }
    .top { flex-wrap: wrap; padding: 12px 12px 10px 16px; }
    .top .views { display: flex; width: 100%; order: 3; }
    .top .views .segs { width: 100%; }
    .top .views .seg { flex: 1; justify-content: center; }
    .body { grid-template-columns: minmax(0, 1fr); }
    .body[data-view="chat"] .pane, .body[data-view="card"] .chat { display: none; }
    .pane { border-left: 0; }
    .top .views .seg.pulse::after { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--primary-color); }
    .msg { max-width: 92%; }
    .compose { padding: 8px 12px 12px; }
    .prop { padding: 16px; }
    .acts { padding: 10px 16px calc(14px + env(safe-area-inset-bottom, 0px)); }
    .acts button { flex: 1; height: 44px; }
  }
`;

// what the example "AI" knows: topics, and the mails a test run would find
const TOPICS = [
  {
    test: /steuer|finanzamt|elster/,
    name: "Steuer & Finanzamt",
    description: "Mails vom Steuerberater und vom Finanzamt (auch ELSTER): Steuerbescheide, Rückfragen und Unterlagen für die Steuererklärung.",
    overlap: "Rechnungen & Belege",
    sample: [["Ihr Steuerbescheid 2025", "Finanzamt Musterstadt", "Rechnungen & Belege"], ["ELSTER: Bestätigung Ihrer Übermittlung", "elster.example", "Persönlich & wichtig"], ["Rückfrage zu Ihren Belegen", "Kanzlei Beispiel", "Persönlich & wichtig"]],
  },
  {
    test: /paket|sendung|zustell|liefer|dhl|versand/,
    name: "Pakete & Lieferungen",
    description: "Versand- und Zustellnachrichten von Paketdiensten und Shops: Sendungsverfolgung, Zustellfenster, Abholung in der Filiale.",
    overlap: "Rechnungen & Belege",
    sample: [["Ihre Bestellung ist unterwegs", "Shop Versand", "Rechnungen & Belege"], ["Zustellung heute zwischen 10 und 14 Uhr", "Paketdienst", "Rechnungen & Belege"], ["Ihr Paket liegt in der Filiale", "Paketdienst", "Persönlich & wichtig"], ["Sendung zugestellt", "Paketdienst", "Rechnungen & Belege"]],
  },
  {
    test: /verein|vorstand|mitglied/,
    name: "Verein",
    description: "Mails vom Vorstand und von Mitgliedern des Vereins: Einladungen, Protokolle, Termine und Rundschreiben.",
    overlap: "Persönlich & wichtig",
    sample: [["Einladung zur Mitgliederversammlung", "Verein Vorstand", "Persönlich & wichtig"], ["Protokoll der Sitzung", "Verein Vorstand", "Newsletter & Werbung"]],
  },
];

const FOLDER_NAMES = { INBOX: "Posteingang", Archive: "Archiv", Junk: "Werbung", "Deleted Messages": "Papierkorb" };

export function openAssistant({ el, data }) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = host.attachShadow({ mode: "open" });
  const back = document.activeElement;
  const mailboxes = data["friedafetch_mail/mailboxes"]?.mailboxes || [];
  const cats = () => el._s.ai?.categories || [];
  const st = { p: null, turns: 0, topic: null, view: "chat", test: null, busy: false, err: "" };
  const folderName = (f) => FOLDER_NAMES[f] || f;

  root.innerHTML = `<style>${UI_STYLE}${STYLE}${CSS}</style>
    <div class="bd" data-close></div>
    <section class="dlg" role="dialog" aria-modal="true" aria-labelledby="as-title">
      <div class="top">${ico("creation")}<h2 id="as-title">Neue Kategorie mit Frieda</h2>
        <button class="icon" data-close aria-label="Schließen">${ico("close")}</button>
        <div class="views"><div class="segs" role="group" aria-label="Ansicht">
          <button class="seg on" data-view="chat" aria-pressed="true">${ico("chat-outline")}Gespräch</button>
          <button class="seg" data-view="card" aria-pressed="false" disabled>${ico("tag-outline")}Vorschlag</button></div></div>
      </div>
      <div class="body" data-view="chat">
        <div class="chat">
          <div class="log" role="log" aria-live="polite" aria-label="Gespräch"></div>
          <div class="compose">
            <div class="chips" role="group" aria-label="Vorschläge zum Antworten"></div>
            <div class="row"><textarea rows="1" placeholder="Beschreibe, welche Mails dazugehören …" aria-label="Deine Nachricht an Frieda"></textarea>
              <button class="send" data-send aria-label="Senden">${ico("send")}</button></div>
            <div class="privacy">${ico("shield-lock-outline")}<span>An die KI gehen nur deine Nachrichten sowie die Namen deiner Kategorien und Ordner – keine Mails. Im KI-Protokoll steht das als „Kategorie-Assistent“.</span></div>
          </div>
        </div>
        <div class="pane" aria-label="Vorschlag"><div class="prop"></div>
          <div class="acts"><button class="secondary" data-close>Abbrechen</button><button data-apply disabled>Übernehmen</button></div></div>
      </div>
    </section>`;
  const $ = (s) => root.querySelector(s);
  const log = $(".log");
  const input = $("textarea");

  function say(who, text, extra = "") {
    const m = document.createElement("div");
    m.className = `msg ${who}`;
    m.innerHTML = who === "me" ? esc(text) : `<span class="who">${ico("creation")}Frieda</span>${esc(text)}${extra}`;
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
    return m;
  }

  function chips(list) {
    $(".chips").innerHTML = list.map((c) => `<button data-chip>${esc(c)}</button>`).join("");
    root.querySelectorAll("[data-chip]").forEach((b) => b.addEventListener("click", () => send(b.textContent)));
  }

  // the proposal: always editable; fields the AI just changed light up briefly
  function drawCard(changed = []) {
    const p = st.p;
    const prop = $(".prop");
    $('[data-view="card"]').disabled = !p;
    if (!p) {
      prop.innerHTML = `<h3>Vorschlag</h3><p class="empty">Sobald du beschrieben hast, welche Mails dazugehören, steht hier mein Vorschlag – Name, Beschreibung für die KI und was mit den Mails passieren soll. Du kannst alles noch ändern.</p>`;
      $("[data-apply]").disabled = true;
      return;
    }
    const fl = (k) => (changed.includes(k) ? "flash" : "");
    const opt = (v, l) => `<option value="${esc(v)}" ${String(p.move_to || "") === v ? "selected" : ""}>${esc(l)}</option>`;
    prop.innerHTML = `<h3>Vorschlag</h3>
      <label class="f ${fl("name")}"><span>Name</span><input type="text" data-f="name" maxlength="40" value="${esc(p.name)}"></label>
      <label class="f ${fl("description")}"><span>Beschreibung für die KI</span><textarea data-f="description" maxlength="300">${esc(p.description)}</textarea><span class="count">${p.description.length} / 300</span></label>
      <label class="f ${fl("move_to")}"><span>Verschieben nach</span><select data-f="move_to">${opt("", "Nicht verschieben")}${mailboxes.map((b) => opt(b, folderName(b))).join("")}</select></label>
      <label class="opt ${fl("flag")}"><input type="checkbox" class="switch" data-f="flag" ${p.flag ? "checked" : ""}><span>Markieren</span></label>
      <label class="opt ${fl("mark_seen")}"><input type="checkbox" class="switch" data-f="mark_seen" ${p.mark_seen ? "checked" : ""}><span>Als gelesen markieren</span></label>
      ${st.err ? `<p class="err" role="alert">${esc(st.err)}</p>` : ""}
      <div class="test">${testHtml()}</div>`;
    $("[data-apply]").disabled = false;
    prop.querySelectorAll("[data-f]").forEach((n) =>
      n.addEventListener("input", () => {
        st.p[n.dataset.f] = n.type === "checkbox" ? n.checked : n.dataset.f === "move_to" ? n.value || null : n.value;
        if (n.dataset.f === "description") n.parentElement.querySelector(".count").textContent = `${n.value.length} / 300`;
        st.test = null;
        prop.querySelector(".test").innerHTML = testHtml();
        bindTest();
      })
    );
    bindTest();
  }

  // the optional test run: the last 20 rated mails go to the AI again (limit and killswitch apply)
  function testHtml() {
    if (st.test === "busy") return `<div class="working"><span class="spinner" aria-hidden="true"></span>20 Mails werden bewertet …</div>`;
    if (st.test) {
      const hits = st.test;
      return `<p><strong>${hits.length} von 20</strong> deiner letzten Mails wären in „${esc(st.p.name)}“ gelandet:</p>
        <ul>${hits.map(([s, f, before]) => `<li>${esc(s)}<small>${esc(f)} · bisher ${esc(before)}</small></li>`).join("")}</ul>
        <button class="link small" data-test>Noch einmal testen</button>`;
    }
    return `<p>Willst du sehen, wie das wirkt? Ich bewerte dafür deine letzten 20 Mails noch einmal – das zählt aufs Stundenlimit, der Killswitch gilt.</p>
      <button class="secondary small ib" data-test>${ico("play-outline")}Mit den letzten 20 Mails testen</button>`;
  }
  function bindTest() {
    root.querySelector("[data-test]")?.addEventListener("click", async () => {
      st.test = "busy";
      $(".test").innerHTML = testHtml();
      await new Promise((r) => setTimeout(r, 1500));
      st.test = (st.topic?.sample || []).slice(0, st.p.description.toLowerCase().includes("lohn") ? 3 : 2);
      $(".test").innerHTML = testHtml();
      bindTest();
    });
  }

  // the scripted "AI": a topic from the first message, then changes from the following ones
  function think(text) {
    const t = text.toLowerCase();
    const before = st.p ? { ...st.p } : null;
    const notes = [];
    if (!st.p) {
      st.topic = TOPICS.find((x) => x.test.test(t)) || null;
      const words = text.replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/).slice(0, 3).join(" ");
      st.p = st.topic
        ? { name: st.topic.name, description: st.topic.description, move_to: null, mark_seen: false, flag: false }
        : { name: words.charAt(0).toUpperCase() + words.slice(1), description: `Mails zu: ${text.trim()}`.slice(0, 300), move_to: null, mark_seen: false, flag: false };
    }
    const p = st.p;
    if (/nicht (mehr )?(verschieb|ins|in den)/.test(t)) p.move_to = null;
    else {
      const box = mailboxes.find((b) => t.includes(b.toLowerCase()) || t.includes(folderName(b).toLowerCase()));
      if (box && box !== "INBOX") p.move_to = box;
    }
    if (/nicht markier/.test(t)) p.flag = false;
    else if (/markier/.test(t) && !/gelesen/.test(t.split("markier")[0].slice(-20))) p.flag = true;
    if (/gelesen/.test(t)) p.mark_seen = !/nicht als gelesen|ungelesen/.test(t);
    if (/nur markier/.test(t)) p.move_to = null;
    if (/lohn|gehalt/.test(t) && !/Lohn/.test(p.description)) p.description = `${p.description} Auch Lohn- und Gehaltsabrechnungen.`.slice(0, 300);
    if (/abgrenz|passt so/.test(t)) notes.push("Gut, dann bleibt es bei der Abgrenzung.");
    const changed = before ? Object.keys(p).filter((k) => p[k] !== before[k]) : ["name", "description", "move_to", "flag", "mark_seen"];
    return { changed, notes, first: !before };
  }

  function answer({ changed, notes, first }) {
    const p = st.p;
    const what = [p.move_to ? `nach „${folderName(p.move_to)}“ verschieben` : "", p.flag ? "markieren" : "", p.mark_seen ? "als gelesen markieren" : ""].filter(Boolean);
    const label = { name: "Name", description: "Beschreibung", move_to: p.move_to ? `→ ${folderName(p.move_to)}` : "nicht verschieben", flag: p.flag ? "markieren" : "nicht markieren", mark_seen: p.mark_seen ? "als gelesen" : "nicht als gelesen" };
    if (first) {
      say("ai", `Mein Vorschlag: eine Kategorie „${p.name}“.\n\n${what.length ? `Solche Mails würde ich ${what.join(" und ")}.` : "Mit den Mails passiert erst einmal nichts – sie werden nur einsortiert."}\n\nDu kannst alles im Vorschlag direkt ändern oder mir sagen, was anders sein soll.`);
      if (st.topic?.overlap) {
        say("ai", `Achtung: „${st.topic.overlap}“ ist ähnlich. Ich habe die Beschreibung so gefasst, dass solche Mails hierher gehören und die übrigen dort bleiben. Wenn du lieber nur „${st.topic.overlap}“ erweitern willst, sag es.`).classList.add("warn");
      }
      chips(
        what.length
          ? ["Nicht verschieben, nur markieren", "Auch als gelesen markieren", st.topic?.name === "Steuer & Finanzamt" ? "Lohnabrechnungen gehören auch dazu" : "So abgrenzen passt"]
          : ["Ins Archiv verschieben", "Markieren", "Als gelesen markieren"]
      );
    } else if (st.turns > 5) {
      say("ai", "Für mehr Feinschliff ändere die Felder am besten direkt im Vorschlag – das geht schneller als hin und her.");
      chips([]);
    } else {
      const shown = changed.map((k) => label[k]).filter(Boolean);
      say("ai", [...notes, shown.length ? "Angepasst:" : notes.length ? "" : "Das habe ich nicht ganz verstanden – meinst du den Ordner, das Markieren oder welche Mails dazugehören?"].filter(Boolean).join("\n"),
        shown.length ? `<div class="changes">${shown.map((s) => `<span>${esc(s)}</span>`).join("")}</div>` : "");
      chips(["Passt so", ...(p.move_to ? ["Nicht verschieben"] : ["Ins Archiv verschieben"]), ...(p.flag ? [] : ["Markieren"])]);
    }
    drawCard(changed);
    if (first && matchMedia("(max-width: 760px)").matches) {
      $('[data-view="card"]').classList.add("pulse");
    }
  }

  async function send(text) {
    text = String(text || "").trim();
    if (!text || st.busy) return;
    if (/^passt so$/i.test(text) && st.p) {
      say("me", text);
      say("ai", "Prima. Mit „Übernehmen“ lege ich die Kategorie an – vorher ändert sich nichts.");
      chips([]);
      if (matchMedia("(max-width: 760px)").matches) setView("card");
      return;
    }
    st.busy = true;
    say("me", text);
    input.value = "";
    grow();
    chips([]);
    const typing = document.createElement("div");
    typing.className = "typing";
    typing.innerHTML = `<span class="spinner" aria-hidden="true"></span>Frieda denkt nach …`;
    log.appendChild(typing);
    log.scrollTop = log.scrollHeight;
    await new Promise((r) => setTimeout(r, 900));
    typing.remove();
    st.turns += 1;
    st.test = null;
    answer(think(text));
    st.busy = false;
    input.focus();
  }

  function setView(v) {
    st.view = v;
    $(".body").dataset.view = v;
    if (v === "card") $('[data-view="card"]').classList.remove("pulse");
    root.querySelectorAll("[data-view]").forEach((b) => b.matches("button") && (b.classList.toggle("on", b.dataset.view === v), b.setAttribute("aria-pressed", String(b.dataset.view === v))));
    (v === "chat" ? input : $(".prop [data-f]"))?.focus();
  }

  function close() {
    host.remove();
    back?.focus?.();
  }

  // apply: the same checks as the form (name needed, not used twice); later the normal save with its server checks
  function apply() {
    const p = st.p;
    const name = (p.name || "").trim();
    st.err = !name ? "Der Name fehlt." : cats().some((c) => c.name.toLowerCase() === name.toLowerCase()) ? `„${name}“ gibt es schon – bitte einen anderen Namen wählen.` : "";
    if (st.err) return drawCard();
    const cat = { id: Math.random().toString(16).slice(2, 10), name, description: p.description.trim().slice(0, 300), move_to: p.move_to, mark_seen: !!p.mark_seen, flag: !!p.flag };
    data["friedafetch_mail/ai"].categories.push(cat);
    el._s.ai.categories = [...cats(), cat];
    el._render();
    close();
    toast(el, `Kategorie „${name}“ angelegt`);
  }

  const grow = () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(120, input.scrollHeight)}px`;
  };
  input.addEventListener("input", grow);
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
      ev.preventDefault();
      send(input.value);
    }
  });
  $("[data-send]").addEventListener("click", () => send(input.value));
  root.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", close));
  $("[data-apply]").addEventListener("click", apply);
  root.querySelectorAll("button[data-view]").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
  // keyboard: Escape closes, Tab stays inside the dialog
  root.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") return close();
    if (ev.key !== "Tab") return;
    const f = [...root.querySelectorAll("button, textarea, input, select")].filter((n) => !n.disabled && n.offsetParent);
    const i = f.indexOf(root.activeElement);
    if (ev.shiftKey && i <= 0) (ev.preventDefault(), f[f.length - 1].focus());
    else if (!ev.shiftKey && i === f.length - 1) (ev.preventDefault(), f[0].focus());
  });

  say("ai", "Beschreib in eigenen Worten, welche Mails in die neue Kategorie gehören – und was mit ihnen passieren soll. Ich mache dir daraus einen Vorschlag, den du noch ändern kannst.");
  chips(["Alles vom Steuerberater und Finanzamt, ins Archiv und markieren", "Paketbenachrichtigungen, als gelesen markieren", "Mails aus dem Verein"]);
  drawCard();
  input.focus();
  return root;
}
