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

const LOC_CSS = `
  .loc { grid-column: 1 / -1; display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; column-gap: 10px; row-gap: 2px; align-items: center;
    margin-top: 12px; padding: 10px 12px; border-radius: 12px; background: var(--secondary-background-color); font-size: 13.5px; --mdc-icon-size: 18px; }
  .loc .li { display: inline-grid; place-items: center; color: var(--secondary-text-color); }
  .loc .li .spinner { width: 14px; height: 14px; border-width: 2px; }
  .loc.same .li { color: var(--frieda-text-ok); }
  .loc.moved .li { color: var(--frieda-text-info); }
  .loc.gone .li { color: var(--frieda-text-warn); }
  .loc .lt { min-width: 0; overflow-wrap: anywhere; }
  .loc .lt small { display: block; font-size: 12px; color: var(--secondary-text-color); }
  .loc .note { grid-column: 2 / -1; font-size: 12.5px; color: var(--secondary-text-color); }
  .loc button.link { font-size: 12.5px; white-space: nowrap; }
  .sheet-head.drafted .state.box { display: none; }  /* the sheet's folder chip says what Frieda did – the check below says where it is */
  .sheet-head .loc { margin-top: 6px; }
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
  .errline { display: flex; align-items: flex-start; gap: 8px; font-size: 12.5px; color: var(--secondary-text-color); --mdc-icon-size: 15px; }
  .errline ha-icon { color: var(--frieda-text-err); flex: none; margin-top: 1px; }
  .errline span { flex: 1; min-width: 0; overflow-wrap: anywhere; }
  .errline button { flex: none; padding: 0; border: 0; background: none; color: inherit; font: inherit; text-decoration: underline; min-height: 0; cursor: pointer; }
  .lscroll, .rbody, .rail { scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--secondary-text-color) 40%, transparent) transparent; }
  .lscroll { flex: 1; min-height: 0; overflow: auto; overscroll-behavior: contain; }
  ul.mlist { list-style: none; margin: 0; padding: 0; }
  .mlist li.day { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: 10px; padding: 10px 16px 4px;
    background: var(--card-background-color, #fff); }
  .listpane.picking .mlist li.day { padding-left: 16px; }
  button.dayfold { display: inline-flex; align-items: center; gap: 4px; padding: 0; border: 0; background: none; color: var(--secondary-text-color); min-height: 0;
    font: inherit; font-size: 11.5px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; cursor: pointer; --mdc-icon-size: 16px; }
  button.dayfold[disabled] { cursor: default; }
  button.dayfold .dn { font-weight: 500; letter-spacing: 0; opacity: .8; }
  button.dayfold .dn::before { content: "· "; }
  button.dayfold:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; border-radius: 4px; }
  .lmore { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 14px; font-size: 13px; }
  .lmore .spinner { width: 14px; height: 14px; border-width: 2px; }
  .daypicks { display: flex; flex-wrap: wrap; gap: 6px; }
  .daypicks .seg { background: var(--secondary-background-color); }
  .daypicks .seg.on { background: color-mix(in srgb, var(--primary-color) 16%, transparent); color: var(--primary-text-color); box-shadow: none; }
  .mlist li.m { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); column-gap: 10px; align-items: start; margin: 0 6px; padding: 9px 10px 10px;
    border-radius: 10px; }
  .mlist li.m + li.m::after { content: ""; position: absolute; left: 10px; right: 10px; top: 0; height: 1px; background: var(--divider-color, #e0e0e0); }
  .mlist li.m:hover::after, .mlist li.m:hover + li.m::after, .mlist li.m.open::after, .mlist li.m.open + li.m::after { opacity: 0; }
  .listpane.picking li.m { grid-template-columns: 20px minmax(0, 1fr); }
  .mlist li.m:hover { background: color-mix(in srgb, var(--secondary-background-color) 55%, transparent); }
  .mlist li.m.picked { background: color-mix(in srgb, var(--primary-color) 6%, transparent); }
  .mlist li.m.open { background: color-mix(in srgb, var(--primary-color) 12%, transparent); }
  .mlist li.m:has(.mitem:focus-visible) { outline: 2px solid var(--primary-color); outline-offset: -2px; }
  .mlist li.m.open .from, .mlist li.m.open .subj { color: var(--primary-text-color); }
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
  .mitem .from { font-weight: 500; }
  .mitem .subj { font-size: 13.5px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mitem .r3 { display: flex; align-items: center; gap: 10px; min-width: 0; margin-top: 2px; }
  .meta, .mv { display: inline-flex; align-items: center; gap: 5px; min-width: 0; font-size: 12.5px; color: var(--secondary-text-color); --mdc-icon-size: 14px; }
  .meta .rl { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .meta ha-icon, .mv ha-icon { flex: none; }
  .mv { flex: none; }
  .mv ha-icon { opacity: .7; }
  .meta.ai ha-icon { color: var(--frieda-text-ai); }
  .meta.rule ha-icon { color: var(--frieda-text-info); }
  .meta.held ha-icon { color: var(--frieda-text-ok); }
  .rhead .chips .meta, .rhead .chips .mv { font-size: 13px; }
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
  .rhead .chips { gap: 14px; }
  h3.sect { margin: 0 0 12px; font-size: 11.5px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: var(--secondary-text-color); }
  .rfoot { padding: 10px 26px 14px; font-size: 12px; color: var(--secondary-text-color); border-top: 1px solid var(--divider-color, #e0e0e0); }
  .rempty { flex: 1; display: grid; place-content: center; justify-items: center; gap: 10px; padding: 24px; text-align: center; color: var(--secondary-text-color); --mdc-icon-size: 44px; }
  .rempty ha-icon { opacity: .45; }
  .runsbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

  /* picking several mails */
  .lhead .pickbtn { flex: none; }
  .pickbar { display: flex; align-items: center; gap: 8px; min-height: 36px; }
  .pickbar .grow { flex: 1; }
  label.pickall { display: inline-flex; align-items: center; gap: 10px; font-size: 14px; cursor: pointer; }
  .pickbar button.link { font-weight: 500; }
  .av.pick, .av.off { width: 20px; height: 20px; margin-top: 1px; --mdc-icon-size: 14px; }
  .av.pick { background: transparent; box-shadow: inset 0 0 0 1.5px var(--secondary-text-color); pointer-events: none; }
  li.m.picked .av.pick { background: var(--primary-color); color: var(--text-primary-color, #fff); box-shadow: none; }
  .av.off { background: none; pointer-events: none; }
  li.m.dim .mitem { opacity: .5; cursor: default; }
  .listpane.picking li.m.picked { background: color-mix(in srgb, var(--primary-color) 10%, transparent); }
  .actbar { position: sticky; bottom: 0; z-index: 3; display: flex; align-items: center; gap: 12px; padding: 10px 14px;
    border-top: 1px solid var(--divider-color, #e0e0e0); background: var(--card-background-color, #fff); font-size: 14px; }
  .actbar .grow { flex: 1; }
  .actbar .pill[disabled] { opacity: .45; }
  .rr { display: inline-flex; align-items: center; gap: 5px; flex: none; font-size: 12px; color: var(--secondary-text-color); --mdc-icon-size: 14px; }
  .rr.done { color: var(--frieda-text-ok); }
  .rr.work { color: var(--frieda-text-ai); }
  .rr .spinner { width: 12px; height: 12px; border-width: 2px; }
  .lhead .batch { margin: 0; }
  .pickinfo { gap: 12px; max-width: 420px; margin: 0 auto; }
  .pickinfo > ha-icon { --mdc-icon-size: 40px; width: 40px; height: 40px; }
  .pickinfo strong { font-size: 17px; color: var(--primary-text-color); }
  ul.picklist { list-style: none; margin: 4px 0; padding: 0; width: 100%; display: grid; gap: 6px; text-align: left; }
  ul.picklist li { display: grid; padding: 8px 12px; border-radius: 10px; background: var(--secondary-background-color); font-size: 13.5px; color: var(--primary-text-color); }
  ul.picklist li span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  ul.picklist li small { color: var(--secondary-text-color); font-size: 12px; }
  ul.picklist li.muted { background: none; padding: 0 12px; }

  /* tablet: the views move into a menu above the list */
  @container (max-width: 1000px) {
    .mc { grid-template-columns: minmax(280px, 340px) minmax(0, 1fr); }
    .rail { display: none; }
    .lhead select.boxsel { display: block; flex: 1 1 auto; font-size: 15px; font-weight: 600; }  /* the menu is the title here */
    .lhead .ttl { display: none; }
    .lstatus { display: flex; }
  }
  /* phone: the list; a mail opens in the sheet over it */
  @container (max-width: 720px) {
    .mc { display: block; height: auto; overflow: visible; }
    .listpane { border-right: 0; }
    .reader { display: none; }  /* the mail opens in the sheet over the list */
    .lhead .lrow { flex-wrap: wrap; }
    .lhead label.search { order: 3; flex: 1 1 100%; }  /* the search gets its own line, so "Auswählen" keeps its words */
    .lscroll, .rbody { overflow: visible; }
    .rbody { padding: 18px 16px 8px; }
    .rfoot { padding: 10px 16px 14px; }
    .rhead h2 { font-size: 19px; }
    .lhead label.search { flex-basis: auto; }
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

// "volume=1": a busy mailbox – about 100 mails today, 60 yesterday, 30 the day before (example senders only)
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
function volumeRows() {
  const out = [];
  const midnight = new Date(new Date().toDateString()).getTime();
  const plan = [[0, 100, Date.now() - midnight - 120000], [1, 60, 86400000], [2, 30, 86400000]];
  let k = 0;
  for (const [daysAgo, n, span] of plan) {
    for (let j = 0; j < n; j++, k++) {
      const [name, from, type, subjects] = SENDERS[(k * 7 + j) % SENDERS.length];
      const time = new Date(midnight - daysAgo * 86400000 + Math.round(((j + 0.5) / n) * span)).toISOString();
      const subject = subjects[(k + j) % subjects.length];
      const base = { time, trigger: k % 9 ? "push" : "auto", subject, from, name, rule: "", category: "", applied: [], volume: true };
      if (type === "ci") out.push({ ...base, kind: "del", rule: "CI-Meldungen löschen" });
      else if (type === "promo") out.push({ ...base, kind: "del", rule: "Werbung & Newsletter löschen" });
      else if (type === "held") out.push({ ...base, kind: "held" });
      else if (k % 17 === 0) out.push({ ...base, kind: "none" });
      else {
        const [category, importance, applied, reason] = {
          news: ["Newsletter & Werbung", 1, ["moved:Deleted Messages"], "Werblicher Newsletter."],
          bill: ["Rechnungen & Belege", 3, [], "Beleg oder Versandinformation."],
          personal: ["Persönlich & wichtig", 4, ["flagged", "notified"], "Persönliche Nachricht eines Kontakts."],
        }[type];
        out.push({ ...base, kind: "ai", category, importance, applied, reason });
      }
    }
  }
  return out;
}

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
const shortDay = (d) => d.replace(/^(\p{L}+), (\d+)\. (\p{L}{3})\p{L}*$/u, "$1, $2. $3"); // "Freitag, 17. Okt"
const clock = (iso) => new Date(iso).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
const plus = (iso, s) => new Date(new Date(iso).getTime() + s * 1000).toISOString();

// One entry per mail: what the rules or the AI did with it (from the example runs and ratings).
function activityRows(data, volume = false) {
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
  if (volume) rows.push(...volumeRows());
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

export async function mount({ el, root, data, q }) {
  const sheet = new CSSStyleSheet();
  root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
  const chrome = document.createElement("div");
  el.before(chrome);
  const croot = chrome.attachShadow({ mode: "open" });
  const act = document.createElement("div");
  chrome.after(act);
  const aroot = act.attachShadow({ mode: "open" });

  const loc = new Map(); // mail → { busy, mailbox, at }: the real place in iCloud, looked up on opening
  const state = { tab: q?.get("tab") || (location.hash || "").slice(1) || "aktivitaet", box: "all", q: "", sel: new Set(), open: null, shown: 50, picking: false, anchor: null, batch: null, folded: new Set() };
  if (!TABS.some(([id]) => id === state.tab)) state.tab = "aktivitaet";
  const rows = activityRows(data, !!q?.get("volume"));
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
  // the list stays quiet: grey text, only the small symbol carries the colour; the folder only when the mail moved
  const meta = (r, full = false) => {
    const [label, icon, cls] = {
      rule: [r.rule, "filter-check-outline", "rule"],
      del: [r.rule, "filter-check-outline", "rule"],
      held: ["Killswitch – nicht an die KI", "shield-check-outline", "held"],
      ai: [`${r.category}${r.importance ? ` · ${r.importance}/5` : ""}`, r.original ? "pencil-outline" : "creation", "ai"],
      none: ["keine Aktion", "minus-circle-outline", ""],
    }[r.kind];
    const where = full || r.folder !== "INBOX" ? `<span class="mv">${ico(full ? folderIcon(r.folder) : "arrow-right")}${esc(folderName(r.folder))}</span>` : "";
    return `<span class="meta ${cls}">${ico(icon)}<span class="rl">${esc(label)}</span></span>${where}`;
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
        <h3>Von Frieda abgelegt in</h3>${FOLDERS.map(box).join("")}
        <h3>Technik</h3><button class="box" data-act="runs">${ico("format-list-numbered")}<span class="lbl">Durchgänge</span></button>
        <span class="grow"></span>
        <div class="status">${statusItems()}</div>
      </nav>`;
  }

  // the mails of the current view and search (all of them, also those not shown yet)
  function listNow() {
    const test = view()[3];
    const qv = state.q.toLowerCase().trim();
    return rows.filter(test).filter((r) => !qv || `${r.subject} ${r.name} ${r.from} ${r.category} ${r.rule}`.toLowerCase().includes(qv));
  }

  // where a mail stands in the running (or last) re-rating
  function rowBatch(i) {
    const b = el._s.ai?.batch;
    if (!state.batch || !b || b.started !== state.batch.started) return "";
    const k = state.batch.rows.indexOf(i);
    if (k < 0) return "";
    if (k < b.done) return `<span class="rr done">${ico("check")}neu bewertet</span>`;
    if (b.state !== "running") return "";
    return k === b.done ? `<span class="rr work"><span class="spinner" aria-hidden="true"></span>wird bewertet</span>` : `<span class="rr wait">${ico("clock-outline")}wartet</span>`;
  }

  function drawList() {
    const label = view()[1];
    const list = listNow();
    const pickable = list.filter((r) => r.selectable);
    const allPicked = pickable.length > 0 && pickable.every((r) => state.sel.has(r.i));
    const somePicked = pickable.some((r) => state.sel.has(r.i));
    const opts = (group, items) => `<optgroup label="${group}">${items.map(([id, l, , tst]) => `<option value="${esc(id)}" ${state.box === id ? "selected" : ""}>${esc(l)} (${rows.filter(tst).length})</option>`).join("")}</optgroup>`;
    // the days of the whole view (also the mails not shown yet): their count, and in picking one box per day
    const days = new Map();
    for (const r of list) {
      const d = dayLabel(r.time);
      if (!days.has(d)) days.set(d, []);
      days.get(d).push(r);
    }
    const dayHead = (d) => {
      const all = days.get(d);
      const sel = all.filter((r) => r.selectable);
      const on = sel.length > 0 && sel.every((r) => state.sel.has(r.i));
      const folded = state.folded.has(d) && !state.picking;
      const box = state.picking
        ? `<input type="checkbox" class="selbox" data-day="${esc(d)}" ${on ? "checked" : ""} ${sel.length ? "" : "disabled"} aria-label="${esc(`Alle von ${d} auswählen (${sel.length})`)}">`
        : "";
      return `<li class="day">${box}<button class="dayfold" data-fold="${esc(d)}" aria-expanded="${!folded}" ${state.picking ? "disabled" : ""}>${state.picking ? "" : ico(folded ? "chevron-right" : "chevron-down")}<span>${esc(d)}</span><span class="dn">${all.length}</span></button></li>`;
    };
    // day by day: the header (with its count), then its mails up to the current chunk; a folded day costs nothing
    const row = (r, d) => {
        const picked = state.sel.has(r.i);
        // only while picking: a round box in front of each mail (rule hits stay without one)
        const av = state.picking ? `<span class="av ${r.selectable ? "pick" : "off"}" aria-hidden="true">${picked ? ico("check") : ""}</span>` : "";
        const when = clock(r.time); // the day stands in the header above
        const name = `${r.name}, ${r.subject}, ${d} ${clock(r.time)}`;
        const role = state.picking
          ? r.selectable
            ? `role="checkbox" aria-checked="${picked}" aria-label="${esc(name)}"`
            : `aria-disabled="true" aria-label="${esc(`${name} – von einer Regel erledigt, nicht für die KI`)}"`
          : `aria-current="${state.open === r.i}" aria-label="${esc(name)}"`;
        return `<li class="m ${!state.picking && state.open === r.i ? "open" : ""} ${picked ? "picked" : ""} ${state.picking && !r.selectable ? "dim" : ""}">
            ${av}
            <button class="mitem" data-open="${r.i}" ${role}>
              <span class="r1"><span class="from">${esc(r.name)}</span><span class="time">${esc(when)}</span></span>
              <span class="subj">${esc(r.subject)}</span>
              <span class="r3">${meta(r)}${rowBatch(r.i)}</span>
            </button>
          </li>`;
    };
    let budget = state.shown;
    let left = 0;
    const parts = [];
    for (const [d, all] of days) {
      const folded = state.folded.has(d) && !state.picking;
      if (budget <= 0) {
        if (!folded) left += all.length;
        continue;
      }
      parts.push(dayHead(d));
      if (folded) continue;
      all.slice(0, budget).forEach((r) => parts.push(row(r, d)));
      left += Math.max(0, all.length - budget);
      budget -= all.length;
    }
    const items = parts.join("");
    const more = left > 0 ? `<div class="lmore" data-more-sentinel><span class="spinner" aria-hidden="true"></span><button class="link small" data-act="more">Weitere ${Math.min(50, left)} anzeigen</button><span class="muted">noch ${left}</span></div>` : "";
    const tools = state.picking
      ? `<div class="pickbar">
          <label class="pickall"><input type="checkbox" class="selbox" data-act="all" ${allPicked ? "checked" : ""} ${pickable.length ? "" : "disabled"}><span>Alle auswählen <span class="muted">(${pickable.length})</span></span></label>
          <span class="grow"></span><button class="link" data-act="pick-done">Fertig</button>
        </div>
        ${days.size > 1 ? `<div class="daypicks" role="group" aria-label="Nach Tag auswählen">${[...days.entries()].slice(0, 3).map(([d, all]) => {
          const sel = all.filter((r) => r.selectable);
          const on = sel.length > 0 && sel.every((r) => state.sel.has(r.i));
          return `<button class="seg ${on ? "on" : ""}" data-day="${esc(d)}" aria-pressed="${on}" ${sel.length ? "" : "disabled"}>${esc(shortDay(d))}<span class="n">${sel.length}</span></button>`;
        }).join("")}</div>` : ""}`
      : `<div class="lrow">
          <select class="fsel boxsel" data-boxsel aria-label="Ansicht">${opts("Ergebnis", KINDS.filter(([id, , , t]) => id === "all" || rows.some(t)))}${opts("Von Frieda abgelegt in", FOLDERS)}<optgroup label="Technik"><option value="runs">Durchgänge</option></optgroup></select>
          <label class="search">${ico("magnify")}<input type="search" data-q value="${esc(state.q)}" placeholder="Suchen" aria-label="Betreff oder Absender suchen"></label>
          <button class="secondary small ib pickbtn" data-act="pick" ${pickable.length ? "" : "disabled"}>${ico("checkbox-multiple-marked-outline")}<span>Auswählen</span></button>
        </div>`;
    const batch = el._s.ai?.batch ? el._renderBatch(el._s.ai) : "";
    const actbar = state.picking
      ? `<div class="actbar"><span><strong>${state.sel.size}</strong> ausgewählt</span><span class="grow"></span><button class="pill" data-act="rerate" ${state.sel.size && !running() ? "" : "disabled"}>${ico("refresh")}Neu bewerten</button></div>`
      : "";
    return `<div class="listpane ${state.picking ? "picking" : ""}">
        <div class="lhead">
          <div class="ttl"><h2>${esc(label)}</h2><span class="cnt">${list.length}</span></div>
          ${tools}
          ${state.picking ? "" : `<div class="lstatus">${statusItems()}</div>`}
          ${lastErr && !state.picking ? `<div class="errline">${ico("alert-circle-outline")}<span>Fehler um ${esc(clock(lastErr.started))}: ${esc(lastErr.errors[0])}</span><button data-act="runs">Details</button></div>` : ""}
          ${batch}
        </div>
        <div class="lscroll">${items ? `<ul class="mlist" aria-label="Mails">${items}</ul>${more}` : `<div class="lempty">Keine Mails in dieser Ansicht.</div>`}</div>
        ${actbar}
      </div>`;
  }

  const running = () => el._s.ai?.batch?.state === "running";

  function drawReader() {
    if (state.picking) {
      const picked = rows.filter((r) => state.sel.has(r.i));
      const n = picked.length;
      return `<section class="reader" aria-label="Auswahl"><div class="rempty pickinfo">
          ${ico("checkbox-multiple-marked-outline")}
          <strong>${n ? `${n} ${n === 1 ? "Mail" : "Mails"} ausgewählt` : "Noch keine Mail ausgewählt"}</strong>
          <span>Klicke Mails in der Liste an. Mit ⇧ wählst du einen ganzen Bereich.</span>
          ${n ? `<ul class="picklist">${picked.slice(0, 6).map((r) => `<li><span>${esc(r.subject)}</span><small>${esc(r.name)}</small></li>`).join("")}${n > 6 ? `<li class="muted">und ${n - 6} weitere</li>` : ""}</ul>` : ""}
          ${n ? `<button class="pill" data-act="rerate" ${running() ? "disabled" : ""}>${ico("refresh")}${n === 1 ? "Neu bewerten" : `${n} Mails neu bewerten`}</button>` : ""}
        </div></section>`;
    }
    const r = rows.find((x) => x.i === state.open);
    if (!r) return `<section class="reader" aria-label="Mail"><div class="rempty">${ico("email-open-outline")}<span>Wähle eine Mail, um zu sehen,<br>was Regeln und KI mit ihr gemacht haben.</span></div></section>`;
    const ev = timeline(r);
    const steps = ev.map((e, i) => el._tlStep(e, i === ev.length - 1)).join("");
    const canRerate = r.selectable && ai?.status?.active;
    return `<section class="reader" aria-label="Mail">
        <div class="rtop"><span class="grow"></span>
          ${canRerate ? `<button class="secondary small ib" data-act="rerate-one" ${running() ? "disabled" : ""}>${ico("refresh")}Neu bewerten</button>` : ""}</div>
        <div class="rbody">
          <div class="rhead">
            <h2 tabindex="-1" id="r-title">${esc(r.subject)}</h2>
            <span class="av" aria-hidden="true">${esc(initials(r.name))}</span>
            <span class="who"><strong>${esc(r.name)}</strong><small>${esc(r.from)}</small></span>
            <span class="date">${esc(fmtDateTime(plus(r.time, -40)))}</span>
            <div class="chips">${meta(r)}${rowBatch(r.i)}</div>
            ${locHtml(r.i)}
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
      aroot.innerHTML = `<style>${UI_STYLE}${STYLE}${MC_CSS}${LOC_CSS}</style><div class="content widgets" style="padding-bottom:0"><section class="widget w-full"><div class="card"><div class="runsbar">
          <button class="secondary small ib" data-act="back-runs">${ico("chevron-left")}Zurück zu den Mails</button><span class="muted">Durchgänge: die technische Sicht für die Fehlersuche.</span></div></div></section></div>`;
    } else {
      aroot.innerHTML = `<style>${UI_STYLE}${STYLE}${MC_CSS}${LOC_CSS}</style><div class="content widgets" style="padding-bottom:0"><section class="widget w-full"><div class="mcwrap">
          <div class="mc">${drawRail()}${drawList()}${drawReader()}</div></div></section></div>`;
      const all = aroot.querySelector('[data-act="all"]');
      if (all && !all.checked) all.indeterminate = listNow().some((r) => r.selectable && state.sel.has(r.i));
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

  // phones: no reading pane – the mail opens in the panel's own sheet over the list (swipe down to close)
  const narrow = () => (aroot.querySelector(".mcwrap")?.clientWidth || innerWidth) <= 720;

  function sheetData(r) {
    return {
      found: true,
      message_id: `<draft-${r.i}@example>`,
      subject: r.subject,
      sender: r.from,
      date: plus(r.time, -40),
      category: r.kind === "ai" ? r.category : null,
      corrected: !!r.original,
      held: r.kind === "held",
      mailbox: "INBOX",
      location: r.kind === "del" ? "trash" : r.folder !== "INBOX" ? r.folder : null,
      events: timeline(r),
    };
  }

  // Example answers of the lookup (a new websocket command would search iCloud by Message-ID, like the re-rating does):
  // mostly where Frieda left the mail; some were moved in Apple Mail afterwards, some are gone.
  function actualPlace(r) {
    if (r.i % 13 === 7) return null;
    if (r.i % 6 === 5) return r.folder === "Archive" ? "INBOX" : "Archive";
    return r.folder;
  }

  async function locate(i) {
    const r = rows.find((x) => x.i === i);
    if (!r || loc.get(i)?.busy) return;
    loc.set(i, { ...(loc.get(i) || {}), busy: true });
    refresh(i);
    await new Promise((res) => setTimeout(res, 700 + (i % 3) * 250));
    loc.set(i, { busy: false, mailbox: actualPlace(r), at: new Date().toISOString() });
    refresh(i);
  }

  function refresh(i) {
    if (state.open !== i) return;
    if (el._s.sheet?.key?.message_id === `<draft-${i}@example>`) el._render();
    else drawActivity();
  }

  function locHtml(i) {
    const r = rows.find((x) => x.i === i);
    const l = loc.get(i);
    if (!r || !l) return "";
    if (l.busy && !l.at) return `<div class="loc"><span class="li"><span class="spinner" aria-hidden="true"></span></span><span class="lt">Wird in iCloud gesucht …</span></div>`;
    const again = `<button class="link" data-act="locate" data-i="${i}" ${l.busy ? "disabled" : ""}>${l.busy ? "Sucht …" : "Erneut prüfen"}</button>`;
    const at = `geprüft ${clock(l.at)}`;
    const frieda = r.kind === "del" || r.folder !== "INBOX" ? `Frieda hatte sie nach „${folderName(r.folder)}“ verschoben` : "Frieda hatte sie im Posteingang gelassen";
    if (!l.mailbox)
      return `<div class="loc gone" role="status"><span class="li">${ico("help-circle-outline")}</span><span class="lt">Nicht mehr in iCloud gefunden<small>${at}</small></span>${again}
        <span class="note">${esc(frieda)}; danach wurde sie gelöscht oder der Papierkorb geleert.</span></div>`;
    if (l.mailbox !== r.folder)
      return `<div class="loc moved" role="status"><span class="li">${ico("folder-swap-outline")}</span><span class="lt">Liegt jetzt in ${esc(folderName(l.mailbox))}<small>${at}</small></span>${again}
        <span class="note">${esc(frieda)}; danach wurde sie woanders hin verschoben.</span></div>`;
    return `<div class="loc same" role="status"><span class="li">${ico("check-circle-outline")}</span><span class="lt">Liegt jetzt in ${esc(folderName(l.mailbox))}<small>${at}</small></span>${again}</div>`;
  }

  function open(i) {
    state.open = i;
    if (!loc.has(i)) locate(i);
    if (narrow()) {
      const r = rows.find((x) => x.i === i);
      el._s.sheet = { key: { message_id: `<draft-${i}@example>`, subject: r.subject, sender: r.from }, data: sheetData(r), loading: false, error: null };
      el._render();
      draw();
      return;
    }
    state.jumped = true;
    draw();
  }

  // select one mail, or with Shift everything between the last one and this one
  function toggle(i, ev) {
    const list = listNow();
    if (!rows.find((r) => r.i === i)?.selectable) return;
    if (ev?.shiftKey && state.anchor != null && list.some((r) => r.i === state.anchor)) {
      const [a, b] = [list.findIndex((r) => r.i === state.anchor), list.findIndex((r) => r.i === i)].sort((x, y) => x - y);
      list.slice(a, b + 1).forEach((r) => r.selectable && state.sel.add(r.i));
    } else if (state.sel.has(i)) state.sel.delete(i);
    else state.sel.add(i);
    state.anchor = i;
    state.picking = true;
    draw();
  }

  function stopPicking() {
    state.picking = false;
    state.sel.clear();
    state.anchor = null;
    draw();
  }

  // asks (the panel's own dialog), then marks the chosen mails in the list while the batch runs
  async function rerate(ids) {
    const order = rows.map((r) => r.i).filter((i) => ids.includes(i));
    const before = el._s.ai?.batch?.started;
    await el._rerate({ messages: order.map((i) => ({ message_id: `<draft-${i}@example>` })) });
    const b = el._s.ai?.batch;
    if (!b || b.started === before) return;
    state.batch = { rows: order, started: b.started };
    state.picking = false;
    state.sel.clear();
    draw();
  }

  // a new view shows its newest mail (wide screens) – never a mail that is not in the list
  function switchBox(box) {
    state.box = box;
    state.shown = 50;
    const test = (VIEWS.find(([id]) => id === box) || [])[3];
    state.open = test && !narrow() && !state.picking ? (rows.find(test)?.i ?? null) : state.open;
    if (state.open != null && !loc.has(state.open)) locate(state.open);
    draw();
  }

  let loadMore = null;

  function bind() {
    const on = (sel, fn, type = "click") => aroot.querySelectorAll(sel).forEach((n) => n.addEventListener(type, (ev) => fn(n, ev)));
    on("[data-goto]", (b) => goto(b.dataset.goto));
    on("[data-box]", (b) => switchBox(b.dataset.box));
    on("[data-boxsel]", (s) => switchBox(s.value), "change");
    on('[data-act="runs"]', () => ((state.box = "runs"), draw()));
    on('[data-act="back-runs"]', () => ((state.box = "all"), draw()));
    on('[data-act="more"]', () => ((state.shown += 50), draw()));
    on('[data-act="pick"]', () => ((state.picking = true), draw(), aroot.querySelector('[data-act="all"]')?.focus()));
    on('[data-act="pick-done"]', () => (stopPicking(), aroot.querySelector('[data-act="pick"]')?.focus()));
    on('[data-act="all"]', (c) => {
      const pickable = listNow().filter((r) => r.selectable);
      if (c.checked) pickable.forEach((r) => state.sel.add(r.i));
      else pickable.forEach((r) => state.sel.delete(r.i));
      draw();
    }, "change");
    on("[data-day]", (b, ev) => {
      ev.stopPropagation();
      const all = listNow().filter((r) => r.selectable && dayLabel(r.time) === b.dataset.day);
      const on = all.every((r) => state.sel.has(r.i));
      all.forEach((r) => (on ? state.sel.delete(r.i) : state.sel.add(r.i)));
      draw();
    });
    on("[data-fold]", (b) => {
      const d = b.dataset.fold;
      if (state.folded.has(d)) state.folded.delete(d);
      else state.folded.add(d);
      draw();
    });
    // load the next mails shortly before the end of the list (the button stays for keyboards)
    loadMore?.disconnect();
    const sentinel = aroot.querySelector("[data-more-sentinel]");
    if (sentinel && "IntersectionObserver" in window) {
      loadMore = new IntersectionObserver(
        (entries) => {
          if (!entries.some((e) => e.isIntersecting)) return;
          loadMore.disconnect();
          state.shown += 50;
          draw();
        },
        { root: narrow() ? null : aroot.querySelector(".lscroll"), rootMargin: "300px" }
      );
      loadMore.observe(sentinel);
    }
    on('[data-act="locate"]', (b) => locate(Number(b.dataset.i)));
    on('[data-act="rerate"]', () => rerate([...state.sel]));
    on('[data-act="rerate-one"]', () => rerate([state.open]));
    on('[data-action="rerate-cancel"]', () => el._call(async () => (el._s.ai = await el._ws({ type: "friedafetch_mail/ai/rerate/cancel", entry_id: el._s.entryId }))));
    on('[data-action="batch-hide"]', () => ((el._s.batchHidden = el._s.ai?.batch?.started), draw()));
    on("[data-pick]", (b, ev) => toggle(Number(b.dataset.pick), ev));
    on("[data-open]", (b, ev) => {
      const i = Number(b.dataset.open);
      // like a mail program: ⌘/Ctrl adds one mail, Shift a range; in picking every click selects
      if (state.picking || ev.metaKey || ev.ctrlKey || ev.shiftKey) toggle(i, ev);
      else open(i);
    });
    on("[data-q]", (inp) => ((state.q = inp.value), (state.shown = 50), draw()), "input");
    on(".mc", (n, ev) => ev.key === "Escape" && state.picking && (stopPicking(), aroot.querySelector('[data-act="pick"]')?.focus()), "keydown");
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
        if (ev.shiftKey && state.picking) toggle(Number(next.dataset.open), ev);
        else if (!state.picking && !narrow()) open(Number(next.dataset.open));
      },
      "keydown"
    );
  }

  function draw() {
    const part = state.tab === "aktivitaet" ? (state.box === "runs" ? "runs" : "aktivitaet") : state.tab;
    sheet.replaceSync(PANEL_CSS.common + PANEL_CSS[part] + LOC_CSS);
    drawChrome();
    drawActivity();
  }

  // DRAFT: "Mit Frieda beschreiben" next to "+" of the AI categories (the panel redraws it, so it is added again each time)
  function injectAssist() {
    const add = root.querySelector('[data-action="ai-cat-new"]');
    if (!add || root.querySelector("[data-assist]")) return;
    add.insertAdjacentHTML("afterend", `<button class="secondary small ib" data-assist style="margin-left:8px">${ico("creation")}Mit Frieda beschreiben</button>`);
    root.querySelector("[data-assist]").addEventListener("click", openAssist);
  }
  async function openAssist() {
    const m = await import("./draft-postfach-assist.js?v=__BUILD__");
    m.openAssistant({ el, data });
  }

  // the panel redraws when the AI state changes (live): follow the re-rating in the list
  const panelRender = el._render.bind(el);
  let lastBatch = "";
  el._render = (...args) => {
    const out = panelRender(...args);
    injectAssist();
    const mid = el._s.sheet?.key?.message_id || "";
    const head = mid.startsWith("<draft-") && root.querySelector(".sheet-head");
    if (head) {
      const i = Number(mid.slice(7, mid.indexOf("@")));
      head.classList.add("drafted");
      head.querySelector(".loc")?.remove();
      head.insertAdjacentHTML("beforeend", locHtml(i));
      head.querySelector('[data-act="locate"]')?.addEventListener("click", () => locate(i));
    }
    const key = JSON.stringify(el._s.ai?.batch || null) + el._s.batchHidden;
    if (key !== lastBatch) {
      lastBatch = key;
      if (state.tab === "aktivitaet") drawActivity();
    }
    return out;
  };

  // wide screens start with the newest mail open, like a mail program
  if (innerWidth > 720 && rows.length) {
    state.open = rows[0].i;
    locate(rows[0].i);
  }
  draw();
  injectAssist();
  if (q?.get("assist")) openAssist();
}
