/* Panel styles (Home Assistant theme variables, mobile layout). Loaded by panel.js. */

export const STYLE = `
  input[type=text], select { font: inherit; padding: 7px 10px; border: 1px solid var(--divider-color, #ccc); border-radius: 6px; background: var(--card-background-color, #fff); color: var(--primary-text-color); min-width: 0; }
  /* accounts */
  /* overview */
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
  .tile { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 12px 14px; display: grid; gap: 8px; align-content: start; min-width: 0; }
  .tile .head { display: flex; align-items: center; gap: 8px; font-weight: 600; }
  .tile .head ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
  .tile .head .state { font-weight: 400; color: var(--secondary-text-color); font-size: 13px; }
  .tile .head .grow { flex: 1; }
  .url { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 2px 6px; font-size: 13px; }
  .url .lbl { grid-column: 1 / -1; color: var(--secondary-text-color); font-size: 12px; }
  .url code { padding: 4px 6px; }
  .line { font-size: 13px; display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
  .clients { display: grid; gap: 4px; }
  .client { display: flex; gap: 4px 8px; align-items: center; flex-wrap: wrap; font-size: 13px; }
  .client .name { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .client .seen { margin-left: auto; white-space: nowrap; }
  /* usage */
  .usage-grid { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 16px; }
  .chart { display: flex; align-items: flex-end; gap: 4px; height: 120px; padding-top: 6px; border-bottom: 1px solid var(--divider-color, #e0e0e0); }
  .chart .col { flex: 1; display: flex; flex-direction: column-reverse; height: 100%; min-width: 0; }
  .chart .r { background: color-mix(in srgb, var(--primary-color) 35%, transparent); border-radius: 0 0 3px 3px; }
  .chart .w { background: var(--primary-color); border-radius: 3px 3px 0 0; }
  .chart .col.solo .r { border-radius: 3px; }
  .axis { display: flex; gap: 4px; font-size: 10.5px; color: var(--secondary-text-color); margin-top: 3px; }
  .axis span { flex: 1; text-align: center; min-width: 0; overflow: hidden; }
  .legend { display: flex; gap: 12px; font-size: 12px; color: var(--secondary-text-color); margin-top: 6px; }
  .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; vertical-align: -1px; }
  .bars { display: grid; gap: 6px; }
  .bar { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 8px; font-size: 13px; }
  .bar .track { grid-column: 1 / -1; height: 6px; border-radius: 3px; background: var(--secondary-background-color, #eee); overflow: hidden; }
  .bar .fill { height: 100%; background: var(--primary-color); border-radius: 3px; }
  .bar .fill.ro { background: color-mix(in srgb, var(--primary-color) 45%, transparent); }
  /* activity */
  .hidden { display: none !important; }
  @media (max-width: 760px) {
    .usage-grid { grid-template-columns: 1fr; }
    button.small, button.link, a.btn { min-height: 34px; }
    table.stack, table.stack tbody, table.stack tr, table.stack td { display: block; width: 100%; box-sizing: border-box; }
    table.stack thead { display: none; }
    table.stack tr { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 8px 10px; margin-bottom: 10px; }
    table.stack td { border: none; padding: 4px 0; white-space: normal !important; }
    table.stack td[data-label]::before { content: attr(data-label); display: block; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; color: var(--secondary-text-color); margin-bottom: 2px; }
    table.stack td[data-label=""]::before { display: none; }
    table.stack td.actions { display: flex; flex-wrap: wrap; gap: 6px; padding-top: 8px; }
  }
  .ltable .c-ico { width: 36px; }
  .ltable .aico { display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: color-mix(in srgb, var(--primary-color) 12%, transparent); color: var(--primary-color); --mdc-icon-size: 16px; }
  .ltable tr.error .aico, .ltable tr.blocked .aico { background: color-mix(in srgb, var(--error-color, #db4437) 14%, transparent); color: var(--error-color, #db4437); }
  .ltable .c-time { width: 56px; text-align: left; }
  .ltable .c-what { min-width: 220px; }
  .ltable .c-res { white-space: nowrap; }
  .ltable .fact { display: inline-flex; align-items: center; gap: 4px; }
  .ltable tr.ok .res { color: var(--success-color, #43a047); }
  .ltable tr.error .res { color: var(--error-color, #db4437); }
  .ltable tr.blocked .res { color: var(--warning-color, #ffa600); }
  .errtext { display: flex; gap: 4px; align-items: center; font-size: 13px; color: var(--error-color, #db4437); overflow-wrap: anywhere; }
  @container (max-width: 720px) {
    .ltable tbody tr[data-search] { grid-template-columns: 36px minmax(0, 1fr) auto; }
    .ltable .c-ico { grid-column: 1; grid-row: 1 / 3; }
    .ltable .c-what { grid-column: 2; grid-row: 1; min-width: 0; }
    .ltable .c-time { grid-column: 3; grid-row: 1; width: auto; text-align: right; }
    .ltable .c-who { grid-column: 2; grid-row: 2; font-size: 12px; }
    .ltable .c-res { grid-column: 3; grid-row: 2; justify-self: end; }
    .ltable .c-area { display: none; }
  }
`;
