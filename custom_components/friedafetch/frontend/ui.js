/* Frieda UI – the shared design library of the Frieda panels.

   Frieda serves it at /friedafetch_static/ui.js; Frieda Postfach (and future extensions) import it from there, so
   every panel uses the same tokens, components, tables, menus, dialogs and widgets. Colours come from the Home
   Assistant theme variables. Bump UI_API when an export changes incompatibly.

   Layouts are stored per Home Assistant user in HA's frontend user data, so they survive restarts and follow the
   user to other devices. */

export const UI_API = 4; // 2: donut(), Layout.opt()/setOpt(); 3: keepScroll(); 4: keepFocus(), mount(), announce(), .chead

// ------------------------------------------------------------------ helpers
const escape = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
export const esc = escape;
export const fmt = (str, ...args) => String(str).replace(/\{(\d+)\}/g, (_, i) => args[Number(i)]);
// Parses ISO timestamps, including offsets without colon (+0200) that Safari rejects.
export const parseTime = (iso) => (iso ? new Date(String(iso).replace(/([+-]\d{2})(\d{2})$/, "$1:$2")) : null);
export const fmtDateTime = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleString() : "–";
};
export const fmtDate = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleDateString() : "–";
};
export const fmtClock = (iso) => {
  const d = parseTime(iso);
  return d && !isNaN(d) ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "–";
};
// Short time for lists: only the time today, otherwise date and time.
export const fmtShort = (iso) => {
  const d = parseTime(iso);
  if (!d || isNaN(d)) return "–";
  const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return d.toDateString() === new Date().toDateString() ? time : `${d.toLocaleDateString([], { day: "2-digit", month: "2-digit" })} ${time}`;
};
export const fmtNum = (n) => Number(n || 0).toLocaleString();

// Material Design Icons from Home Assistant's own icon set.
// With a title the icon carries meaning and gets an accessible name; without one it is decoration.
export const ico = (name, title = "") =>
  title
    ? `<ha-icon icon="mdi:${name}" role="img" aria-label="${escape(title)}" title="${escape(title)}"></ha-icon>`
    : `<ha-icon icon="mdi:${name}" aria-hidden="true"></ha-icon>`;

// Redraws a panel without losing the scroll position. Safari and the companion apps do not anchor the scroll
// position like Chrome, so replacing the panel's content (on every filter click) would jump to the top.
export function keepScroll(host, draw) {
  const saved = [];
  let node = host;
  while (node && node !== document) {
    if (node.scrollTop > 0) saved.push([node, node.scrollTop]);
    node = node.parentNode instanceof ShadowRoot ? node.parentNode.host : node.parentNode;
  }
  const doc = document.scrollingElement;
  const top = doc ? doc.scrollTop : 0;
  draw();
  const restore = () => {
    for (const [el, y] of saved) if (el.scrollTop !== y) el.scrollTop = y;
    if (doc && doc.scrollTop !== top) doc.scrollTop = top;
  };
  restore();
  requestAnimationFrame(restore); // once more after icons and fonts have their size
}

// ------------------------------------------------------------------ accessibility
// Panels redraw their whole content on every change. These helpers keep that invisible for keyboard and screen
// reader users: the focus stays on the same control, a dialog keeps the focus inside, and news is read out.
const FOCUS_ATTRS = ["data-pager-do", "data-action", "data-v", "data-id", "data-k", "data-i", "data-w", "data-index", "data-scope", "data-dry", "data-filter", "data-search-table", "data-col-table", "data-col"];
const CONTEXT_ATTRS = ["data-pager", "data-rule-id", "data-widget", "data-detail-for"];
const FOCUSABLE = "button, input, select, textarea, summary, a[href]";
const quote = (v) => `"${String(v).replace(/["\\]/g, "\\$&")}"`;

// A selector that finds the same control again after a redraw.
function describe(el) {
  const ctxEl = el.closest(CONTEXT_ATTRS.map((a) => `[${a}]`).join(","));
  const ctxAttr = ctxEl && CONTEXT_ATTRS.find((a) => ctxEl.hasAttribute(a));
  const ctx = ctxEl ? `[${ctxAttr}=${quote(ctxEl.getAttribute(ctxAttr))}] ` : "";
  if (el.tagName === "SUMMARY") {
    const det = el.parentElement;
    return `${ctx}details${[...det.classList].map((c) => `.${c}`).join("")} > summary`;
  }
  if (el.id) return `#${el.id}`;
  const own = FOCUS_ATTRS.filter((a) => el.hasAttribute(a)).map((a) => `[${a}=${quote(el.getAttribute(a))}]`).join("");
  return own ? `${ctx}${el.tagName.toLowerCase()}${own}` : "";
}

const shown = (el) => !!el && !el.disabled && el.getClientRects().length > 0;

// Redraws and puts the focus back where it was (or into a dialog that just opened, or back to its opener).
export function keepFocus(root, draw) {
  const DIALOG = ".modal, .sheet"; // confirmation dialogs and side sheets
  const hadModal = !!root.querySelector(DIALOG);
  let el = root.activeElement;
  // an entry of a menu closes the menu: come back to the menu button
  const menu = el?.closest?.("details.menu");
  if (menu && el.tagName === "BUTTON") el = menu.querySelector(":scope > summary");
  const sel = el ? describe(el) : "";
  const all = () => [...root.querySelectorAll(FOCUSABLE)];
  const index = el ? all().indexOf(el) : -1;
  const caret = el?.tagName === "INPUT" && /^(text|search)$/.test(el.type) ? [el.selectionStart, el.selectionEnd] : null;
  draw();
  const hasModal = !!root.querySelector(DIALOG);
  let target = null;
  if (hasModal && !hadModal) {
    root.__opener = sel;
    target =
      root.querySelector('.modal [data-action="confirm-no"]') ||
      root.querySelector('.sheet [data-action="sheet-close"]') ||
      root.querySelector(".modal button, .sheet button");
  } else if (hadModal && !hasModal) {
    target = root.__opener ? root.querySelector(root.__opener) : null;
    root.__opener = "";
  } else if (el) {
    target = sel ? root.querySelector(sel) : null;
    if (!shown(target) && index >= 0) target = all().slice(Math.max(0, index - 1)).find(shown) || null;
  }
  if (!shown(target) || target === root.activeElement) return;
  target.focus({ preventScroll: true });
  if (caret && target.tagName === "INPUT") {
    try {
      target.setSelectionRange(...caret);
    } catch (err) {
      /* not a text field */
    }
  }
}

// Puts the panel's markup into a frame next to a live region that survives redraws. While a dialog or sheet is open,
// everything else is inert, so Tab stays in the dialog and screen readers only read it.
export function mount(root, html) {
  let frame = root.querySelector("[data-frame]");
  if (!frame) {
    root.innerHTML = `<div data-frame></div><div class="vh" data-live aria-live="polite" aria-atomic="true"></div>`;
    frame = root.querySelector("[data-frame]");
  }
  frame.innerHTML = html;
  const modal = frame.querySelector(".modal, .sheet");
  const own = ["modal", "modal-backdrop", "sheet", "sheet-backdrop"];
  for (const child of frame.children) {
    if (child.tagName === "STYLE") continue;
    child.inert = !!modal && !own.some((c) => child.classList.contains(c));
  }
  // notices and errors (marked data-announce) are read out once when they appear
  const news = [...frame.querySelectorAll("[data-announce]")].map((n) => n.textContent.trim()).filter(Boolean).join(" ");
  if (news && news !== root.__news) announce(root, news);
  root.__news = news;
}

// Reads a short text out (e.g. "3 hits") without moving the focus.
// A longer delay suits texts that follow typing (search hits), so only the last one is read.
export function announce(root, text, delay = 100) {
  const live = root.querySelector("[data-live]");
  if (!live) return;
  clearTimeout(root.__liveTimer);
  live.textContent = "";
  root.__liveTimer = setTimeout(() => (live.textContent = text), delay);
}

// Copies text to the clipboard. Plain http:// (e.g. the local IP) has no Clipboard API, so a hidden text field is
// used there. Returns whether it worked; the focus goes back to `restore` (e.g. the copy button).
export async function copyText(text, restore = null) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (err) {
    /* fall back below */
  }
  const field = document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.style.cssText = "position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none";
  document.body.appendChild(field);
  field.select();
  field.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (err) {
    ok = false;
  }
  field.remove();
  restore?.focus?.({ preventScroll: true });
  return ok;
}

// Short confirmation in Home Assistant's own toast at the bottom of the screen (also read out by screen readers).
export function toast(host, message) {
  host.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
  if (host.shadowRoot) announce(host.shadowRoot, message);
}

// ------------------------------------------------------------------ paging
// Tables render all their rows; paging only shows a part of the rows that match the search (rows with
// data-nomatch="1" do not). Detail rows after a row follow it, day headings without visible rows disappear.
// The page size is stored with the layout (per table), the current page lives in the panel (state[table]).
export const PAGE_SIZES = [5, 10, 25, 50, 0]; // 0 = all

// Placeholder below a table; applyPaging() fills it.
export const pagerSlot = (table) => `<div class="pager" data-pager="${escape(table)}"></div>`;

export function applyPaging(root, layout, table, state, t, fallback = 10) {
  const tbl = root.querySelector(`table[data-table="${table}"]`);
  const bar = root.querySelector(`[data-pager="${table}"]`);
  if (!tbl) return;
  const size = Number(layout.opt(`page-${table}`, "size", fallback));
  const rows = [...tbl.querySelectorAll("tbody tr[data-search]")];
  const match = rows.filter((tr) => tr.dataset.nomatch !== "1");
  const pages = size ? Math.max(1, Math.ceil(match.length / size)) : 1;
  const page = Math.max(0, Math.min(state[table] || 0, pages - 1));
  state[table] = page;
  const from = size ? page * size : 0;
  const to = size ? Math.min(from + size, match.length) : match.length;
  const show = new Set(match.slice(from, to));
  for (const tr of rows) {
    const visible = show.has(tr);
    tr.hidden = !visible;
    for (let n = tr.nextElementSibling; n && !n.hasAttribute("data-search") && !n.classList.contains("dayrow"); n = n.nextElementSibling) {
      n.hidden = !visible;
    }
  }
  tbl.querySelectorAll("tr.dayrow").forEach((day) => {
    let any = false;
    for (let n = day.nextElementSibling; n && !n.classList.contains("dayrow"); n = n.nextElementSibling) {
      if (n.hasAttribute("data-search") && !n.hidden) {
        any = true;
        break;
      }
    }
    day.hidden = !any;
  });
  if (!bar) return;
  if (match.length <= PAGE_SIZES[0]) {
    bar.hidden = true;
    bar.innerHTML = "";
    return;
  }
  bar.hidden = false;
  const focused = root.activeElement && bar.contains(root.activeElement) ? root.activeElement.dataset.pagerDo : null;
  const opts = PAGE_SIZES.map((n) => `<option value="${n}" ${n === size ? "selected" : ""}>${n ? n : escape(t.pageAll)}</option>`).join("");
  bar.innerHTML = `<label class="psize"><span>${escape(t.perPage)}</span><select class="fsel" data-pager-do="size" aria-label="${escape(t.perPage)}">${opts}</select></label>
    <span class="grow"></span>
    <span class="prange" aria-live="polite">${escape(fmt(t.pageRange, match.length ? from + 1 : 0, to, match.length))}</span>
    <button class="icon" data-pager-do="prev" ${page === 0 ? "disabled" : ""} aria-label="${escape(t.prevPage)}" title="${escape(t.prevPage)}">${ico("chevron-left")}</button>
    <button class="icon" data-pager-do="next" ${page >= pages - 1 ? "disabled" : ""} aria-label="${escape(t.nextPage)}" title="${escape(t.nextPage)}">${ico("chevron-right")}</button>`;
  const again = () => applyPaging(root, layout, table, state, t, fallback);
  bar.querySelector('[data-pager-do="size"]').addEventListener("change", (ev) => {
    layout.setOpt(`page-${table}`, "size", Number(ev.target.value));
    state[table] = 0;
    again();
  });
  bar.querySelector('[data-pager-do="prev"]').addEventListener("click", () => {
    state[table] = page - 1;
    again();
  });
  bar.querySelector('[data-pager-do="next"]').addEventListener("click", () => {
    state[table] = page + 1;
    again();
  });
  // keep the focus on the control that was used (the bar was just redrawn)
  if (focused) {
    const el = bar.querySelector(`[data-pager-do="${focused}"]`);
    (el && !el.disabled ? el : bar.querySelector("[data-pager-do]:not(:disabled)"))?.focus({ preventScroll: true });
  }
}

// Confirmation dialog markup; c = { title, text, ok, irreversible }. Buttons use data-action confirm-yes / confirm-no.
export function renderConfirm(c, t) {
  if (!c) return "";
  return `<div class="modal-backdrop" data-action="confirm-no"></div>
    <div class="modal" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-text">
      <div class="modal-head"><span class="modal-icon">${ico("alert-outline")}</span><h3 id="confirm-title">${escape(c.title)}</h3></div>
      <p id="confirm-text">${escape(c.text)}</p>
      ${c.irreversible ? `<p class="modal-warn">${escape(t.irreversible)}</p>` : ""}
      <div class="modal-actions"><button class="secondary" data-action="confirm-no">${escape(t.cancel)}</button><button class="danger" data-action="confirm-yes">${escape(c.ok)}</button></div>
    </div>`;
}

// ------------------------------------------------------------------ widgets and tables
const EMPTY = () => ({ v: 1, order: [], hidden: [], widths: {}, cols: {}, opts: {} });

export class Layout {
  // widgets: [{ id, width: "full" | "half" }] in default order; tables: { table: { column: visibleByDefault } }
  constructor(key, widgets, tables = {}) {
    this.key = key;
    this.defaults = widgets;
    this.tables = tables;
    this.data = EMPTY();
    this.editing = false;
    this._hass = null;
    this._timer = null;
  }

  async load(hass) {
    this._hass = hass;
    try {
      const res = await hass.callWS({ type: "frontend/get_user_data", key: this.key });
      const v = res?.value;
      if (v && typeof v === "object") this.data = { ...EMPTY(), ...v };
    } catch (err) {
      /* no stored layout (or an older Home Assistant): defaults */
    }
  }

  _save() {
    clearTimeout(this._timer);
    this._timer = setTimeout(() => {
      this._hass?.callWS({ type: "frontend/set_user_data", key: this.key, value: this.data }).catch(() => {});
    }, 300);
  }

  ids() {
    const known = this.defaults.map((w) => w.id);
    const saved = (this.data.order || []).filter((id) => known.includes(id));
    return [...saved, ...known.filter((id) => !saved.includes(id))];
  }

  isHidden(id) {
    return (this.data.hidden || []).includes(id);
  }

  setHidden(id, hidden) {
    const set = new Set(this.data.hidden || []);
    if (hidden) set.add(id);
    else set.delete(id);
    this.data.hidden = [...set];
    this._save();
  }

  // Moves a widget past its next shown neighbour (widgets without content are skipped).
  move(id, delta, shown) {
    const order = this.ids();
    const visible = order.filter((x) => shown.includes(x));
    const pos = visible.indexOf(id);
    const other = visible[pos + delta];
    if (pos < 0 || !other) return;
    const a = order.indexOf(id);
    const b = order.indexOf(other);
    [order[a], order[b]] = [order[b], order[a]];
    this.data.order = order;
    this._save();
  }

  moveBefore(id, target) {
    const order = this.ids().filter((x) => x !== id);
    const at = order.indexOf(target);
    order.splice(at < 0 ? order.length : at, 0, id);
    this.data.order = order;
    this._save();
  }

  width(id) {
    return this.data.widths?.[id] || this.defaults.find((w) => w.id === id)?.width || "full";
  }

  toggleWidth(id) {
    this.data.widths = { ...(this.data.widths || {}), [id]: this.width(id) === "full" ? "half" : "full" };
    this._save();
  }

  colVisible(table, col) {
    const own = this.data.cols?.[table]?.[col];
    return own === undefined ? this.tables[table]?.[col] !== false : !!own;
  }

  toggleCol(table, col) {
    const cols = { ...(this.data.cols || {}) };
    cols[table] = { ...(cols[table] || {}), [col]: !this.colVisible(table, col) };
    this.data.cols = cols;
    this._save();
  }

  // Small per-widget settings (e.g. whether charts are shown), stored with the layout.
  opt(id, key, fallback = false) {
    const v = this.data.opts?.[id]?.[key];
    return v === undefined ? fallback : v;
  }

  setOpt(id, key, value) {
    const opts = { ...(this.data.opts || {}) };
    opts[id] = { ...(opts[id] || {}), [key]: value };
    this.data.opts = opts;
    this._save();
  }

  reset() {
    this.data = EMPTY();
    this._save();
  }
}

// Wraps the panel's cards. widgets: { id: { title, html } }; an empty html means "nothing to show right now".
export function renderWidgets(layout, widgets, t) {
  const shown = layout.ids().filter((id) => widgets[id]?.html);
  const visible = shown.filter((id) => !layout.isHidden(id));
  const edit = layout.editing;
  const items = visible
    .map((id, i) => {
      const w = layout.width(id);
      const bar = edit
        ? `<div class="wbar"><span class="grip" title="${escape(t.widgetDrag)}">${ico("drag")}</span><span class="wtitle">${escape(widgets[id].title)}</span><span class="grow"></span>
            <button class="icon" data-action="w-up" data-w="${id}" ${i === 0 ? "disabled" : ""} title="${escape(t.widgetUp)}" aria-label="${escape(t.widgetUp)}">${ico("arrow-up")}</button>
            <button class="icon" data-action="w-down" data-w="${id}" ${i === visible.length - 1 ? "disabled" : ""} title="${escape(t.widgetDown)}" aria-label="${escape(t.widgetDown)}">${ico("arrow-down")}</button>
            <button class="icon wide-only" data-action="w-width" data-w="${id}" title="${escape(w === "full" ? t.widgetHalf : t.widgetFull)}" aria-label="${escape(w === "full" ? t.widgetHalf : t.widgetFull)}">${ico(w === "full" ? "arrow-collapse-horizontal" : "arrow-expand-horizontal")}</button>
            <button class="icon" data-action="w-hide" data-w="${id}" title="${escape(t.widgetHide)}" aria-label="${escape(t.widgetHide)}">${ico("eye-off-outline")}</button></div>`
        : "";
      return `<section class="widget w-${w} ${edit ? "editing" : ""}" data-widget="${id}">${bar}${widgets[id].html}</section>`;
    })
    .join("");
  const hidden = shown.filter((id) => layout.isHidden(id));
  const tray = edit
    ? `<section class="widget w-full wtray"><div class="wtray-head">${ico("view-dashboard-edit-outline")}<span>${escape(t.layoutHint)}</span><span class="grow"></span>
          <button class="secondary ib" data-action="w-reset">${ico("restore")}${escape(t.layoutReset)}</button></div>
        ${hidden.length ? `<div class="wtray-hidden"><span class="muted">${escape(t.hiddenWidgets)}:</span>${hidden.map((id) => `<button class="secondary ib" data-action="w-show" data-w="${id}">${ico("eye-outline")}${escape(widgets[id].title)}</button>`).join("")}</div>` : ""}
      </section>`
    : "";
  return `${tray}${items}`;
}

// Toolbar button that switches the arrange mode.
export function layoutButton(layout, t) {
  return `<button class="tbtn ${layout.editing ? "on" : ""}" data-action="w-edit" aria-pressed="${layout.editing}" title="${escape(layout.editing ? t.layoutDone : t.layoutEdit)}">${ico(layout.editing ? "check" : "view-dashboard-edit-outline")}<span>${escape(layout.editing ? t.layoutDone : t.layoutEdit)}</span></button>`;
}

// Menu to show or hide the optional columns of a table. cols: [{ key, label }]
export function columnMenu(layout, table, cols, t) {
  const items = cols
    .map(
      (c) =>
        `<label class="colitem"><input type="checkbox" class="switch" data-col-table="${table}" data-col="${c.key}" ${layout.colVisible(table, c.key) ? "checked" : ""}><span>${escape(c.label)}</span></label>`
    )
    .join("");
  return `<details class="menu colmenu"><summary title="${escape(t.columns)}" aria-label="${escape(t.columns)}">${ico("view-column-outline")}<span class="lbl">${escape(t.columns)}</span></summary><div class="menu-list">${items}</div></details>`;
}

// Small donut chart. parts: [{ value, color, label }]; colors are CSS values (theme variables work).
export function donut(parts, { size = 44, center = "", title = "" } = {}) {
  const list = parts.filter((p) => Number(p.value) > 0);
  const total = list.reduce((n, p) => n + Number(p.value), 0);
  const r = 15.9155; // circumference 100
  let offset = 25; // start at 12 o'clock
  const rings = total
    ? list
        .map((p) => {
          const share = (Number(p.value) / total) * 100;
          const gap = list.length > 1 ? Math.min(1.2, share / 3) : 0;
          const ring = `<circle r="${r}" cx="21" cy="21" fill="none" stroke="${p.color}" stroke-width="5.5" stroke-dasharray="${Math.max(share - gap, 0.01)} ${100 - share + gap}" stroke-dashoffset="${offset}"><title>${escape(p.label)}: ${escape(p.value)}</title></circle>`;
          offset -= share;
          return ring;
        })
        .join("")
    : "";
  const label = title || list.map((p) => `${p.label}: ${p.value}`).join(", ");
  return `<svg class="donut" viewBox="0 0 42 42" width="${size}" height="${size}" role="img" aria-label="${escape(label)}">
      <circle r="${r}" cx="21" cy="21" fill="none" stroke="var(--divider-color, #e0e0e0)" stroke-width="5.5"></circle>${rings}
      ${center !== "" ? `<text x="21" y="21" text-anchor="middle" dominant-baseline="central">${escape(center)}</text>` : ""}
    </svg>`;
}

// Rare card actions (clear, reset, …) in a small ⋮ menu instead of large header buttons.
// items: [{ action, icon, label, danger, disabled }]; falsy items are skipped.
export function cardMenu(items, t) {
  const list = items.filter(Boolean);
  if (!list.length) return "";
  const entry = (i) =>
    `<button class="${i.danger ? "danger-item" : ""}" data-action="${i.action}" ${i.disabled ? "disabled" : ""}>${ico(i.icon)}<span class="mi"><span>${escape(i.label)}</span></span></button>`;
  return `<details class="menu rowmenu cardmenu"><summary aria-label="${escape(t.moreActions)}" title="${escape(t.moreActions)}">${ico("dots-vertical")}</summary><div class="menu-list">${list.map(entry).join("")}</div></details>`;
}

// CSS that hides the switched-off columns (cells carry the class c-<column>).
export function columnStyle(layout, table, cols) {
  const off = cols.filter((c) => !layout.colVisible(table, c.key)).map((c) => `table[data-table="${table}"] .c-${c.key}`);
  return off.length ? `<style>${off.join(", ")} { display: none !important; }</style>` : "";
}

// Wires the arrange mode, drag and drop and the column switches. rerender() draws the panel again.
export function bindWidgets(root, layout, rerender) {
  const shown = [...root.querySelectorAll("section.widget[data-widget]")].map((s) => s.dataset.widget);
  const act = {
    "w-edit": () => {
      layout.editing = !layout.editing;
      rerender();
    },
    "w-up": (el) => (layout.move(el.dataset.w, -1, shown), rerender()),
    "w-down": (el) => (layout.move(el.dataset.w, 1, shown), rerender()),
    "w-width": (el) => (layout.toggleWidth(el.dataset.w), rerender()),
    "w-hide": (el) => (layout.setHidden(el.dataset.w, true), rerender()),
    "w-show": (el) => (layout.setHidden(el.dataset.w, false), rerender()),
    "w-reset": () => (layout.reset(), rerender()),
  };
  root.querySelectorAll("[data-action^='w-']").forEach((el) => {
    const fn = act[el.dataset.action];
    if (fn) el.addEventListener("click", () => fn(el));
  });
  // menus open inside their card: flip to the right when there is no room on the left (e.g. next to HA's sidebar)
  root.querySelectorAll("details.menu").forEach((d) =>
    d.addEventListener("toggle", () => {
      const list = d.querySelector(".menu-list");
      if (!d.open || !list) return;
      list.classList.remove("flip");
      const box = (d.closest(".card, section.widget") || root.host || document.body).getBoundingClientRect();
      if (list.getBoundingClientRect().left < Math.max(box.left, 0)) list.classList.add("flip");
    })
  );
  // choosing an entry closes its menu
  root.querySelectorAll("details.menu .menu-list button").forEach((b) => b.addEventListener("click", () => b.closest("details")?.removeAttribute("open")));
  root.querySelectorAll("[data-col-table]").forEach((el) =>
    el.addEventListener("change", () => {
      layout.toggleCol(el.dataset.colTable, el.dataset.col);
      const keep = el.closest("details.colmenu");
      const table = el.dataset.colTable;
      rerender();
      // keep the column menu open while switching several columns
      const again = [...root.querySelectorAll("details.colmenu")].find((d) => d.querySelector(`[data-col-table="${table}"]`));
      if (keep && again) again.open = true;
    })
  );
  if (!layout.editing) return;
  // drag and drop: only from the grip, so text and buttons inside a widget keep working
  root.querySelectorAll("section.widget[data-widget]").forEach((sec) => {
    const grip = sec.querySelector(".grip");
    grip?.addEventListener("pointerdown", () => sec.setAttribute("draggable", "true"));
    sec.addEventListener("dragstart", (ev) => {
      ev.dataTransfer.setData("text/plain", sec.dataset.widget);
      ev.dataTransfer.effectAllowed = "move";
      sec.classList.add("dragging");
    });
    sec.addEventListener("dragend", () => {
      sec.removeAttribute("draggable");
      sec.classList.remove("dragging");
      root.querySelectorAll(".dropto").forEach((n) => n.classList.remove("dropto"));
    });
    sec.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      sec.classList.add("dropto");
    });
    sec.addEventListener("dragleave", () => sec.classList.remove("dropto"));
    sec.addEventListener("drop", (ev) => {
      ev.preventDefault();
      const id = ev.dataTransfer.getData("text/plain");
      if (id && id !== sec.dataset.widget) {
        layout.moveBefore(id, sec.dataset.widget);
        rerender();
      }
    });
  });
}

const WIDGET_STYLE = `
  ha-icon { --mdc-icon-size: 18px; display: inline-flex; flex: none; width: var(--mdc-icon-size); height: var(--mdc-icon-size); }
  .vh { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  tr[hidden] { display: none !important; }

  /* widgets */
  .content.widgets { max-width: 1280px; grid-template-columns: minmax(0, 1fr); align-items: start; }
  .widget { min-width: 0; display: grid; }
  .widget > .card { min-width: 0; }
  .widget.editing { border-radius: var(--ha-card-border-radius, 12px); outline: 2px dashed color-mix(in srgb, var(--primary-color) 45%, transparent); outline-offset: 3px; }
  .widget.dragging { opacity: .45; }
  .widget.dropto { outline-color: var(--primary-color); outline-style: solid; }
  .wbar { display: flex; align-items: center; gap: 4px; padding: 0 2px 6px; color: var(--secondary-text-color); font-size: 13px; }
  .wbar .grip { cursor: grab; display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 6px; --mdc-icon-size: 20px; }
  .wbar .grip:active { cursor: grabbing; }
  .wbar .wtitle { font-weight: 500; color: var(--primary-text-color); }
  .wbar .grow, .wtray-head .grow { flex: 1; }
  .wtray { background: color-mix(in srgb, var(--primary-color) 8%, transparent); border-radius: var(--ha-card-border-radius, 12px); padding: 12px 14px; gap: 10px; }
  .wtray-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 14px; }
  .wtray-hidden { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .toolbar .tbtn { display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 12px; border-radius: 18px; background: transparent; color: inherit; font-size: 14px; border: 1px solid color-mix(in srgb, currentColor 25%, transparent); }
  .toolbar .tbtn.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  @media (min-width: 1100px) {
    .content.widgets { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .widget.w-full, .widget.wtray { grid-column: 1 / -1; }
  }
  @media (max-width: 1099px) {
    .wbar .wide-only { display: none; }
  }

  /* table toolbar: search, filter segments, column menu */
  .tbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin: 4px 0 8px; }
  .tbar .grow { flex: 1; }
  .tbar .segs { margin-top: 0; }
  label.search { display: inline-flex; align-items: center; gap: 6px; flex: 1 1 220px; max-width: 360px; height: 36px; box-sizing: border-box; padding: 0 10px; border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); color: var(--secondary-text-color); }
  label.search input { flex: 1; min-width: 0; border: none; background: transparent; color: var(--primary-text-color); font: inherit; font-size: 14px; outline: none; padding: 0; box-shadow: none; min-height: 0; }
  label.search:focus-within { box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 45%, transparent); }
  select.fsel { height: 36px; box-sizing: border-box; padding: 0 10px; border-radius: 10px; border: none; background: var(--secondary-background-color, #f0f0f0); color: var(--primary-text-color); font-size: 13px; max-width: 220px; }
  .segs { display: inline-flex; flex-wrap: wrap; gap: 4px; padding: 3px; border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); }
  button.seg { display: inline-flex; align-items: center; gap: 6px; background: transparent; color: var(--frieda-text-on-fill); padding: 5px 12px; border-radius: 8px; font-size: 13px; min-height: 0; border: none; }
  button.seg ha-icon { --mdc-icon-size: 16px; }
  button.seg .n { font-size: 11px; padding: 0 6px; border-radius: 8px; background: color-mix(in srgb, var(--secondary-text-color) 14%, transparent); }
  button.seg.on { background: var(--card-background-color, #fff); color: var(--primary-text-color); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
  .chip.ic { display: inline-flex; align-items: center; gap: 4px; }
  .chip.ic ha-icon { --mdc-icon-size: 14px; }

  /* menus (run menu, row menu, column menu) */
  details.menu { position: relative; }
  details.menu > summary { list-style: none; cursor: pointer; user-select: none; }
  details.menu > summary::-webkit-details-marker { display: none; }
  details.menu .menu-list { position: absolute; right: 0; top: calc(100% + 4px); z-index: 5; min-width: 220px; background: var(--card-background-color, #fff); border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; box-shadow: 0 6px 20px rgba(0,0,0,.18); padding: 6px; display: grid; gap: 2px; text-align: left; }
  details.menu .menu-list button { background: none; color: var(--primary-text-color); text-align: left; display: grid; grid-template-columns: 20px minmax(0, 1fr); column-gap: 12px; align-items: start; padding: 9px 10px; border-radius: 8px; font-size: 14px; font-weight: 400; line-height: 1.35; min-height: 0; border: none; }
  details.menu .menu-list button ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); margin-top: 1px; }
  details.menu .menu-list button:hover:not(:disabled) { background: var(--secondary-background-color, #f0f0f0); }
  details.menu .menu-list .mi { display: grid; gap: 2px; }
  details.menu .menu-list .mi > span { font-weight: 500; }
  details.menu .menu-list button small { color: var(--secondary-text-color); font-size: 12px; }
  details.menu .menu-list hr { border: none; border-top: 1px solid var(--divider-color, #e0e0e0); margin: 4px 2px; }
  details.menu .menu-list button.danger-item, details.menu .menu-list button.danger-item ha-icon { color: var(--frieda-text-err); }
  details.menu.rowmenu, details.menu.colmenu { display: inline-block; }
  details.menu.rowmenu > summary { display: inline-grid; place-items: center; width: 32px; height: 32px; padding: 0; border-radius: 50%; background: transparent; color: var(--secondary-text-color); --mdc-icon-size: 20px; }
  details.menu.colmenu > summary { display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 12px; border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); color: var(--frieda-text-on-fill); font-size: 13px; }
  details.menu.rowmenu > summary:hover, details.menu.rowmenu[open] > summary, details.menu.colmenu[open] > summary { background: var(--secondary-background-color, #f0f0f0); color: var(--primary-text-color); filter: none; }
  details.menu.colmenu .menu-list { min-width: 200px; }
  /* the column button stays on the right, also when the toolbar wraps */
  .tbar details.colmenu { margin-left: auto; }
  /* a menu that would leave its card on the left opens to the right instead */
  details.menu .menu-list.flip { right: auto; left: 0; }
  .card .chead details.cardmenu { flex: none; margin-right: -6px; }
  .card .chead details.cardmenu .menu-list { font-size: 14px; font-weight: 400; }
  button.morelink { background: none; color: var(--primary-color); padding: 6px 4px; font-size: 13px; min-height: 0; border: none; display: inline-flex; align-items: center; gap: 4px; }
  label.colitem { display: flex; align-items: center; gap: 10px; padding: 7px 10px; border-radius: 8px; font-size: 14px; cursor: pointer; color: var(--primary-text-color); }
  label.colitem:hover { background: var(--secondary-background-color, #f0f0f0); }
  .scroll.menus { overflow: visible; }

  /* data tables: one line per item, details on click, row menu */
  table.dtable { width: 100%; border-collapse: collapse; font-size: 14px; }
  table.dtable th, table.dtable td { text-align: left; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  table.dtable thead th { position: sticky; top: 0; z-index: 1; background: var(--card-background-color, #fff); color: var(--secondary-text-color); font-size: 12px; font-weight: 500; letter-spacing: .02em; white-space: nowrap; padding: 6px 8px; vertical-align: bottom; }
  table.dtable td { padding: 7px 8px; vertical-align: middle; }
  /* one typography for all tables: main and number columns 14px, secondary columns (time, sender, purpose, …) 13px grey */
  table.dtable td { font-size: 14px; }
  table.dtable td.dim, table.dtable td.dim .fact { font-size: 13px; color: var(--secondary-text-color); }
  /* row tints: failed entries rosé, blocked ones amber (also in the compact layout) */
  table.dtable tbody tr.row-err > td { background: color-mix(in srgb, var(--error-color, #db4437) 7%, transparent); }
  table.dtable tbody tr.row-warn > td { background: color-mix(in srgb, var(--warning-color, #ffa600) 9%, transparent); }
  table.dtable tbody tr[data-search]:hover > td { background: color-mix(in srgb, var(--primary-text-color) 3%, transparent); }
  table.dtable tr.open > td { border-bottom-color: transparent; background: color-mix(in srgb, var(--primary-color) 5%, transparent); }
  table.dtable tr.detail > td { background: color-mix(in srgb, var(--primary-color) 5%, transparent); padding: 2px 12px 12px; }
  table.dtable tr.dayrow > td { padding: 14px 8px 4px; font-size: 12px; font-weight: 500; color: var(--secondary-text-color); border-bottom: none; text-transform: none; }
  /* rows that just arrived through a live update light up once */
  table.dtable tbody tr.fresh > td { animation: frieda-fresh 2.4s ease-out; }
  @keyframes frieda-fresh { from { background-color: color-mix(in srgb, var(--primary-color) 18%, transparent); } }
  table.dtable .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  th button.sort { display: inline-flex; align-items: center; gap: 3px; background: none; color: inherit; font: inherit; padding: 0; min-height: 0; border: none; }
  th button.sort ha-icon { --mdc-icon-size: 14px; opacity: .45; }
  th button.sort.on { color: var(--primary-text-color); }
  th button.sort.on ha-icon { opacity: 1; }
  th.num button.sort { flex-direction: row-reverse; }
  button.rname { display: flex; align-items: center; gap: 6px; width: 100%; background: none; color: inherit; padding: 0; text-align: left; font: inherit; min-height: 0; border: none; }
  button.rname > ha-icon { --mdc-icon-size: 18px; color: var(--secondary-text-color); transition: transform .15s; }
  tr.open button.rname > ha-icon { transform: rotate(90deg); }
  .nm { display: grid; min-width: 0; }
  .nm strong { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .nm small { font-size: 12px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .det { display: grid; gap: 10px; }
  .det .lbl { font-size: 12px; color: var(--secondary-text-color); margin-bottom: 3px; }
  .det pre { margin: 0; font-size: 12px; white-space: pre-wrap; overflow-wrap: anywhere; background: var(--secondary-background-color, #f0f0f0); border-radius: 8px; padding: 8px 10px; }
  .nomatch { margin: 8px 0 0; }
  /* switch: outlined with a grey knob when off, filled with a white knob when on (both 3:1 against the card) */
  input.switch, input[type=checkbox].switch { appearance: none; -webkit-appearance: none; flex: none; width: 32px; height: 18px; min-height: 0; border-radius: 9px; background: color-mix(in srgb, var(--secondary-text-color) 12%, transparent); box-shadow: inset 0 0 0 1.5px var(--secondary-text-color); position: relative; cursor: pointer; margin: 0; padding: 0; border: none; transition: background .15s, box-shadow .15s; vertical-align: middle; }
  input.switch::after { content: ""; position: absolute; top: 4px; left: 4px; width: 10px; height: 10px; border-radius: 50%; background: var(--secondary-text-color); transition: transform .15s, width .15s, height .15s, top .15s, left .15s; }
  input.switch:checked { background: var(--primary-color); box-shadow: none; }
  input.switch:checked::after { top: 2px; left: 2px; width: 14px; height: 14px; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.25); transform: translateX(14px); }
  input.switch:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }

  @media (max-width: 760px) {
    .toolbar .tbtn span { display: none; }
    .toolbar .tbtn { width: 40px; padding: 0; justify-content: center; }
    details.menu.colmenu > summary .lbl { display: none; }
    details.menu .menu-list { right: 0; left: auto; min-width: min(260px, calc(100vw - 48px)); }
  }
  /* narrow widgets (phones, or half width): rows become compact entries; each table places its cells with grid areas */
  .widget { container-type: inline-size; }
  @container (max-width: 720px) {
    label.search { max-width: none; flex-basis: 100%; }
    table.dtable thead { display: none; }
    table.dtable, table.dtable tbody { display: block; }
    table.dtable tbody tr[data-search] { display: grid; align-items: center; column-gap: 6px; padding: 6px 0; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
    table.dtable tbody tr[data-search] > td { display: block; border: none; padding: 1px 0; max-width: none; min-width: 0; }
    table.dtable tr.dayrow, table.dtable tr.dayrow > td { display: block; }
    table.dtable tr.open, table.dtable tr.detail { background: color-mix(in srgb, var(--primary-color) 5%, transparent); }
    table.dtable tr.open > td, table.dtable tr.detail > td, table.dtable tbody tr:hover > td { background: none !important; }
    table.dtable tbody tr.row-err > td, table.dtable tbody tr.row-warn > td { background: none !important; }
    table.dtable tbody tr.fresh { animation: frieda-fresh 2.4s ease-out; }
    table.dtable tbody tr.fresh > td { animation: none; }
    table.dtable tbody tr.row-err { background: color-mix(in srgb, var(--error-color, #db4437) 7%, transparent); border-radius: 10px; padding-left: 4px; padding-right: 4px; }
    table.dtable tbody tr.row-warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 9%, transparent); border-radius: 10px; padding-left: 4px; padding-right: 4px; }
    table.dtable tr.open { border-radius: 10px 10px 0 0; padding-left: 4px; padding-right: 4px; }
    table.dtable tr.detail { display: block; border-radius: 0 0 10px 10px; padding: 0 4px 4px; margin-bottom: 6px; }
    table.dtable tr.detail > td { display: block; border: none; }
    .scroll { overflow: visible; }
    .ilist li { grid-template-columns: 32px minmax(0, 1fr); }
    .ilist .i-sub { grid-row: 2; }
    .ilist .i-chip { grid-column: 2; grid-row: 3; justify-self: start; margin-top: 4px; }
    .ilist .i-ic { grid-row: 1 / span 3; align-self: start; }
  }
  @media (prefers-reduced-motion: reduce) {
    table.dtable tbody tr.fresh, table.dtable tbody tr.fresh > td { animation: none; }
  }
`;

// ------------------------------------------------------------------ styles
const BASE_STYLE = `
  :host { display: block; height: 100%; color: var(--primary-text-color); background: var(--primary-background-color);
    /* tone colours for text and icons, mixed with the text colour so they stay readable in light and dark themes (WCAG AA) */
    --frieda-text-err: color-mix(in srgb, var(--error-color, #db4437) 65%, var(--primary-text-color));
    --frieda-text-ok: color-mix(in srgb, var(--success-color, #43a047) 65%, var(--primary-text-color));
    --frieda-text-info: color-mix(in srgb, var(--info-color, #039be5) 65%, var(--primary-text-color));
    --frieda-text-warn: color-mix(in srgb, var(--warning-color, #ffa600) 50%, var(--primary-text-color));
    --frieda-text-ai: color-mix(in srgb, var(--frieda-ai-color, #8e6bd8) 65%, var(--primary-text-color));
    /* grey text on grey fills (segments, menus, figures) */
    --frieda-text-on-fill: color-mix(in srgb, var(--secondary-text-color) 80%, var(--primary-text-color)); }
  .toolbar { display: flex; align-items: center; gap: 12px; height: 56px; padding: 0 16px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); font-size: 20px; }
  .toolbar .grow { flex: 1; }
  .toolbar img { width: 28px; height: 28px; border-radius: 7px; }
  .content { padding: 16px; max-width: 1100px; margin: 0 auto; display: grid; gap: 16px; }
  .card { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0,0,0,.14)); border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0)); padding: 16px; }
  .card h2 { margin: 0 0 12px; font-size: 18px; font-weight: 500; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .card h2 .grow { flex: 1; }
  /* card head: the heading, then its actions (menus and buttons are not part of the heading) */
  .card .chead { margin: 0 0 12px; font-size: 18px; font-weight: 500; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .card .chead > h2 { flex: 1; min-width: 0; margin: 0; font: inherit; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  h3 { font-size: 13px; font-weight: 500; margin: 14px 0 8px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .04em; }

  /* buttons: primary (default), secondary, danger, link, small, icon, ib (icon + text), round, pill */
  button { font: inherit; font-size: 14px; border: none; border-radius: 6px; padding: 8px 14px; cursor: pointer; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.secondary { background: transparent; color: var(--primary-color); border: 1px solid var(--primary-color); }
  button.danger { background: var(--error-color, #db4437); }
  button.secondary.danger { background: transparent; color: var(--frieda-text-err); border-color: color-mix(in srgb, var(--error-color, #db4437) 60%, transparent); }
  button.link { background: none; color: var(--primary-color); padding: 2px 4px; min-height: 0; }
  button.small { padding: 3px 9px; font-size: 12.5px; }
  button.icon { display: inline-grid; place-items: center; background: transparent; color: var(--secondary-text-color); padding: 4px 6px; border-radius: 8px; }
  button.icon:hover:not(:disabled) { background: var(--secondary-background-color, #f0f0f0); color: var(--primary-text-color); }
  button.ib { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px 6px 10px; }
  button.round { width: 36px; height: 36px; padding: 0; border-radius: 50%; font-size: 22px; line-height: 1; display: inline-grid; place-items: center; flex: none; }
  button.round.small { width: 28px; height: 28px; font-size: 18px; }
  button.pill, .pill { display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 16px 0 12px; border-radius: 18px; font-size: 14px; font-weight: 500; }
  button.morelink { background: none; color: var(--primary-color); padding: 6px 4px; font-size: 13px; min-height: 0; display: inline-flex; align-items: center; gap: 4px; }
  button:disabled { opacity: .5; cursor: default; }
  a.btn { display: inline-flex; align-items: center; text-decoration: none; border-radius: 6px; padding: 3px 9px; font-size: 12.5px; color: var(--primary-color); border: 1px solid var(--primary-color); width: max-content; }

  /* text, chips, badges, dots, notices */
  .muted { color: var(--secondary-text-color); font-size: 13px; }
  code { font-size: 12px; background: var(--secondary-background-color, #f0f0f0); padding: 1px 5px; border-radius: 4px; word-break: break-all; }
  .chip { display: inline-block; padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); font-size: 12px; margin: 2px 4px 2px 0; }
  .badge { font-size: 11px; padding: 1px 7px; border-radius: 8px; background: var(--secondary-background-color, #eee); color: var(--secondary-text-color); white-space: nowrap; }
  .badge.warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 20%, transparent); color: var(--primary-text-color); }
  .badge.err { background: color-mix(in srgb, var(--error-color, #db4437) 16%, transparent); color: var(--primary-text-color); }
  .badges { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--success-color, #43a047); display: inline-block; flex: none; }
  .dot.off { background: var(--disabled-text-color, #bdbdbd); }
  .dot.warn { background: var(--warning-color, #ffa600); }
  .dot.err { background: var(--error-color, #db4437); }
  .error { background: color-mix(in srgb, var(--error-color, #db4437) 12%, transparent); color: var(--frieda-text-err); padding: 10px 12px; border-radius: 8px; }
  .ok { background: color-mix(in srgb, var(--success-color, #43a047) 12%, transparent); padding: 10px 12px; border-radius: 8px; }
  .info { background: color-mix(in srgb, var(--primary-color) 10%, transparent); padding: 10px 12px; border-radius: 8px; font-size: 13px; }
  /* hint after an update: the open page still runs the old code */
  /* pager below a table: page size, range, previous/next */
  .pager { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 10px; padding: 8px 0 0; font-size: 13px; color: var(--secondary-text-color); }
  .pager[hidden] { display: none; }
  .pager .grow { flex: 1; }
  .pager .psize { display: inline-flex; align-items: center; gap: 8px; }
  .pager .psize span { white-space: nowrap; }
  .pager select.fsel { width: auto; min-width: 0; max-width: none; height: 32px; min-height: 32px; padding: 0 8px; font-size: 14px; }
  .pager .prange { font-variant-numeric: tabular-nums; }
  .pager button.icon { padding: 4px; border-radius: 50%; --mdc-icon-size: 20px; }
  .content.widgets > .update-hint { grid-column: 1 / -1; }
  .update-hint { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; --mdc-icon-size: 20px; }
  .update-hint .grow { flex: 1 1 220px; }
  .empty { text-align: center; padding: 18px 8px; display: grid; gap: 10px; justify-items: center; }
  .fact { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
  /* work in progress: small spinner with a text */
  .working { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; color: var(--primary-text-color); min-height: 36px; }
  .spinner { flex: none; width: 16px; height: 16px; box-sizing: border-box; border-radius: 50%; border: 2px solid color-mix(in srgb, var(--primary-color) 25%, transparent); border-top-color: var(--primary-color); animation: frieda-spin .8s linear infinite; }
  @keyframes frieda-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 2.4s; } }
  svg.donut { flex: none; display: block; }
  /* select that looks like a chip (inline choice in tables) */
  label.chipsel { position: relative; display: inline-flex; align-items: center; max-width: 100%; border-radius: 12px; background: var(--secondary-background-color, #f0f0f0); color: var(--primary-text-color); cursor: pointer; transition: background .15s; }
  label.chipsel:hover { background: color-mix(in srgb, var(--primary-color) 12%, var(--secondary-background-color, #f0f0f0)); }
  label.chipsel select { appearance: none; -webkit-appearance: none; border: none; background: transparent; color: inherit; font: inherit; font-size: 12px; padding: 3px 24px 3px 9px; min-height: 0; max-width: 220px; cursor: pointer; text-overflow: ellipsis; }
  label.chipsel select:focus-visible { outline: none; }
  label.chipsel:focus-within { box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 45%, transparent); }
  label.chipsel > ha-icon { position: absolute; right: 6px; pointer-events: none; --mdc-icon-size: 14px; color: var(--secondary-text-color); }
  label.chipsel.on { background: color-mix(in srgb, var(--primary-color) 14%, transparent); }
  label.chipsel.on select { padding-left: 28px; }
  label.chipsel.on > .lead { position: absolute; left: 9px; display: inline-flex; right: auto; --mdc-icon-size: 13px; color: var(--primary-color); }
  /* item list (e.g. the messages a run handled): tinted icon, two text lines, a chip on the right */
  .ilist { list-style: none; margin: 0; padding: 0; border: 1px solid var(--divider-color, #e0e0e0); border-radius: 12px; background: var(--card-background-color, #fff); overflow: hidden; }
  .ilist li { display: grid; grid-template-columns: 32px minmax(0, 1fr) auto; align-items: center; gap: 0 12px; padding: 9px 12px; }
  .ilist li + li { border-top: 1px solid var(--divider-color, #e0e0e0); }
  .ilist .i-ic { grid-row: span 2; display: inline-grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; --mdc-icon-size: 17px; background: var(--secondary-background-color, #f0f0f0); color: var(--secondary-text-color); }
  .ilist .i-main { min-width: 0; font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ilist .i-sub { grid-column: 2; min-width: 0; font-size: 12px; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ilist .i-chip { grid-column: 3; grid-row: 1 / span 2; font-size: 12px; padding: 2px 9px; border-radius: 10px; white-space: nowrap; background: var(--secondary-background-color, #f0f0f0); color: var(--frieda-text-on-fill); }
  .ilist .tone-err .i-ic, .ilist .tone-err .i-chip { background: color-mix(in srgb, var(--error-color, #db4437) 12%, transparent); color: var(--frieda-text-err); }
  .ilist .tone-move .i-ic, .ilist .tone-move .i-chip { background: color-mix(in srgb, var(--info-color, #039be5) 13%, transparent); color: var(--frieda-text-info); }
  .ilist .tone-warn .i-ic, .ilist .tone-warn .i-chip { background: color-mix(in srgb, var(--warning-color, #ffa600) 18%, transparent); color: var(--primary-text-color); }
  .ilist .tone-ai .i-ic, .ilist .tone-ai .i-chip { background: color-mix(in srgb, var(--frieda-ai-color, #8e6bd8) 15%, transparent); color: var(--frieda-text-ai); }
  .ilist .tone-held .i-ic, .ilist .tone-held .i-chip { background: color-mix(in srgb, var(--success-color, #43a047) 14%, transparent); color: var(--frieda-text-ok); }
  .ilist .tone-none .i-main { font-weight: 400; color: var(--secondary-text-color); }
  /* entries that open something (a mail's timeline): chevron at the end */
  .ilist li.go { cursor: pointer; grid-template-columns: 32px minmax(0, 1fr) auto 16px; }
  .ilist li.go::after { content: "›"; grid-column: 4; grid-row: 1 / span 2; color: var(--secondary-text-color); font-size: 18px; line-height: 1; justify-self: end; }
  .ilist li.go:hover { background: color-mix(in srgb, var(--primary-text-color) 3%, transparent); }
  .ilist li.go:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; border-radius: 10px; }
  .ilist .i-more { display: block; padding: 8px 12px 9px 56px; font-size: 12px; color: var(--secondary-text-color); border-top: 1px solid var(--divider-color, #e0e0e0); }
  /* compact list of items (e.g. the messages a run handled) */
  svg.donut text { font-size: 10px; font-weight: 500; fill: var(--primary-text-color); }
  .legend { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12px; color: var(--secondary-text-color); }
  .legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; vertical-align: 0; }
  .fact ha-icon { --mdc-icon-size: 15px; opacity: .85; }

  /* inputs */
  input[type=text], input[type=search], select { font: inherit; font-size: 14px; padding: 7px 10px; border: 1px solid var(--divider-color, #ccc); border-radius: 6px; background: var(--card-background-color, #fff); color: var(--primary-text-color); }

  /* plain tables */
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--divider-color, #e0e0e0); vertical-align: top; }
  th { color: var(--secondary-text-color); font-weight: 500; }
  .scroll { overflow-x: auto; }

  /* key figures */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
  .stat { background: var(--secondary-background-color, #f5f5f5); border-radius: 10px; padding: 10px 12px; }
  .stat .k { font-size: 12px; color: var(--frieda-text-on-fill); }
  .stat .v { font-size: 24px; font-weight: 500; line-height: 1.25; }
  .stat .v small { font-size: 12px; font-weight: 400; }
  .stat .s { font-size: 12px; color: var(--frieda-text-on-fill); }

  /* account tabs */
  .tabs { display: flex; gap: 10px; flex-wrap: wrap; }
  .tab { flex: 1 1 240px; text-align: left; background: var(--card-background-color, #fff); color: var(--primary-text-color); border: 2px solid var(--divider-color, #e0e0e0); border-radius: var(--ha-card-border-radius, 12px); padding: 12px 14px; display: grid; gap: 4px; cursor: pointer; }
  .tab.active { border-color: var(--primary-color); box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 18%, transparent); }
  .tab .label { font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 8px; }
  .tab .meta { color: var(--secondary-text-color); font-size: 12.5px; }

  /* confirmation dialog */
  .modal-backdrop { position: fixed; inset: 0; z-index: 20; background: rgba(0,0,0,.45); }
  .modal { position: fixed; z-index: 21; left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(420px, calc(100vw - 32px)); box-sizing: border-box; padding: 20px; background: var(--card-background-color, #fff); color: var(--primary-text-color); border-radius: var(--ha-dialog-border-radius, 16px); box-shadow: 0 12px 40px rgba(0,0,0,.3); }
  .modal-head { display: flex; align-items: center; gap: 12px; }
  .modal-head h3 { margin: 0; font-size: 18px; font-weight: 500; line-height: 1.3; text-transform: none; letter-spacing: normal; color: var(--primary-text-color); }
  .modal-icon { flex: none; display: inline-grid; place-items: center; width: 40px; height: 40px; border-radius: 50%; background: color-mix(in srgb, var(--error-color, #db4437) 14%, transparent); color: var(--frieda-text-err); --mdc-icon-size: 22px; }
  .modal p { margin: 14px 0 0; font-size: 14px; line-height: 1.45; }
  .modal .modal-warn { margin-top: 8px; color: var(--frieda-text-err); font-size: 13px; font-weight: 500; }
  .modal-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
  .modal-actions button { font-size: 14px; padding: 8px 18px; border-radius: 18px; }
  .modal button:focus-visible, .modal button:focus { outline: 2px solid var(--primary-color); outline-offset: 2px; }

  @media (max-width: 760px) {
    .toolbar { height: 52px; padding: 0 10px; font-size: 18px; }
    .content { padding: 10px; gap: 10px; }
    .card { padding: 12px; }
    .card h2, .card .chead { font-size: 17px; }
    .tabs .tab { flex-basis: 100%; }
    .stat .v { font-size: 22px; }
    button { min-height: 40px; }
    button.small, button.link, button.morelink, a.btn { min-height: 34px; }
    /* small outlined buttons become touch-sized pills instead of tall narrow boxes */
    a.btn, button.small:not(.round):not(.link) { min-height: 36px; padding: 0 16px; font-size: 14px; border-radius: 18px; justify-content: center; }
    button.icon { min-width: 40px; }
    button.round { min-height: 0; width: 42px; height: 42px; }
    button.pill, .pill { height: 42px; border-radius: 21px; }
    input[type=text], input[type=search], select { font-size: 16px; min-height: 42px; }
  }
`;

export const UI_STYLE = BASE_STYLE + WIDGET_STYLE;
