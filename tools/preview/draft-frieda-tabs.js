// DRAFT (dev preview only): Frieda in three tabs. All content is the real panel; the tabs only decide what is shown.
import { UI_STYLE, esc, ico } from "./frieda/ui.js?v=__BUILD__";

const TABS = [
  ["ueberblick", "Überblick", "view-dashboard-outline"],
  ["freigaben", "Freigaben", "check-decagram-outline"],
  ["protokoll", "Änderungsprotokoll", "history"],
];

const PANEL_CSS = {
  common: `.toolbar { display: none !important; } .wtray { display: none !important; }`,
  ueberblick: `section.widget:not([data-widget="overview"]):not([data-widget="usage"]) { display: none !important; }`,
  freigaben: `section.widget:not([data-widget="approvals"]) { display: none !important; }`,
  protokoll: `section.widget:not([data-widget="activity"]) { display: none !important; }`,
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
  .tabsbar .n { font-size: 11px; font-weight: 600; padding: 0 6px; border-radius: 8px; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  @media (max-width: 600px) {
    .tabsbar { gap: 0; padding: 0 4px; }
    .tabsbar button { flex: 1 1 0; min-width: 0; flex-direction: column; gap: 2px; padding: 8px 2px 6px; font-size: 12px; --mdc-icon-size: 20px; position: relative; }
    .tabsbar .n { position: absolute; top: 4px; left: calc(50% + 8px); }
  }
  .draftnote { margin: 12px 16px 0; padding: 8px 12px; border-radius: 10px; font-size: 13px; color: var(--secondary-text-color);
    background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
  .empty { margin: 16px; padding: 28px 16px; border-radius: var(--ha-card-border-radius, 12px); background: var(--card-background-color);
    color: var(--secondary-text-color); text-align: center; display: grid; justify-items: center; gap: 8px; --mdc-icon-size: 32px; }
`;

export async function mount({ el, root, data }) {
  const sheet = new CSSStyleSheet();
  root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
  const chrome = document.createElement("div");
  el.before(chrome);
  const croot = chrome.attachShadow({ mode: "open" });

  const state = { tab: (location.hash || "").slice(1) || "ueberblick" };
  if (!TABS.some(([id]) => id === state.tab)) state.tab = "ueberblick";
  const pending = () => (data["friedafetch/approvals/list"]?.requests || []).filter((r) => r.status === "pending").length;

  function draw() {
    sheet.replaceSync(PANEL_CSS.common + PANEL_CSS[state.tab]);
    const n = pending();
    const hasApprovals = !!root.querySelector('section[data-widget="approvals"]');
    croot.innerHTML = `<style>${UI_STYLE}${CHROME_CSS}</style>
      <div class="toolbar"><img src="./frieda/icon.svg" alt=""><span>Frieda</span><span class="grow"></span></div>
      <nav class="tabsbar" role="tablist" aria-label="Bereiche">${TABS.map(
        ([id, label, icon]) =>
          `<button role="tab" aria-selected="${state.tab === id}" tabindex="${state.tab === id ? 0 : -1}" data-tab="${id}">${ico(icon)}${esc(label)}${id === "freigaben" && n ? `<span class="n" aria-label="${n} offen">${n}</span>` : ""}</button>`
      ).join("")}</nav>
      <div class="draftnote">Entwurf · Tabs statt einer langen Seite. Offene Freigaben zählt der Tab-Reiter, damit sie auch von den anderen Tabs aus auffallen.</div>
      ${state.tab === "freigaben" && !hasApprovals ? `<div class="empty">${ico("check-circle-outline")}<strong>Keine offenen Freigaben</strong><span>Sobald ein KI-Werkzeug eine Mail senden oder löschen will, erscheint sie hier.</span></div>` : ""}`;
    croot.querySelectorAll("[data-tab]").forEach((b) =>
      b.addEventListener("click", () => {
        state.tab = b.dataset.tab;
        history.replaceState(null, "", `${location.pathname}${location.search}#${state.tab}`);
        draw();
        croot.querySelector(`[data-tab="${state.tab}"]`)?.focus();
      })
    );
    croot.querySelector('[role="tablist"]').addEventListener("keydown", (ev) => {
      const i = TABS.findIndex(([id]) => id === state.tab);
      const next = ev.key === "ArrowRight" ? i + 1 : ev.key === "ArrowLeft" ? i - 1 : null;
      if (next === null) return;
      ev.preventDefault();
      croot.querySelectorAll("[data-tab]")[(next + TABS.length) % TABS.length].click();
    });
  }

  draw();
}
