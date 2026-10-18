/* Panel styles (Home Assistant theme variables, mobile layout). Loaded by panel.js. */

export const STYLE = `
  :host { display: block; height: 100%; color: var(--primary-text-color); background: var(--primary-background-color); }
  .toolbar { display: flex; align-items: center; gap: 12px; height: 56px; padding: 0 16px; background: var(--app-header-background-color, var(--primary-color)); color: var(--app-header-text-color, #fff); font-size: 20px; }
  .toolbar .grow { flex: 1; }
  .toolbar img { width: 28px; height: 28px; border-radius: 7px; }
  .content { padding: 16px; max-width: 1100px; margin: 0 auto; display: grid; gap: 16px; }
  .card { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0,0,0,.14)); border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0)); padding: 16px; min-width: 0; }
  .card h2 { margin: 0 0 12px; font-size: 18px; font-weight: 500; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .card h2 .grow { flex: 1; }
  h3 { font-size: 13px; font-weight: 500; margin: 14px 0 8px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .04em; }
  button { font: inherit; border: none; border-radius: 6px; padding: 8px 14px; cursor: pointer; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.secondary { background: transparent; color: var(--primary-color); border: 1px solid var(--primary-color); }
  button.danger { background: var(--error-color, #db4437); }
  button.link { background: none; color: var(--primary-color); padding: 2px 4px; }
  button.small { padding: 3px 9px; font-size: 12.5px; }
  button:disabled { opacity: .5; cursor: default; }
  a.btn { display: inline-flex; align-items: center; text-decoration: none; border-radius: 6px; padding: 3px 9px; font-size: 12.5px; color: var(--primary-color); border: 1px solid var(--primary-color); }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--divider-color, #e0e0e0); vertical-align: top; }
  th { color: var(--secondary-text-color); font-weight: 500; }
  .muted { color: var(--secondary-text-color); font-size: 13px; }
  .chip { display: inline-block; padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); font-size: 12px; margin: 2px 4px 2px 0; }
  input[type=text], select { font: inherit; padding: 7px 10px; border: 1px solid var(--divider-color, #ccc); border-radius: 6px; background: var(--card-background-color, #fff); color: var(--primary-text-color); min-width: 0; }
  .error { background: color-mix(in srgb, var(--error-color, #db4437) 12%, transparent); color: var(--error-color, #db4437); padding: 10px 12px; border-radius: 8px; }
  .info { background: color-mix(in srgb, var(--primary-color) 10%, transparent); padding: 10px 12px; border-radius: 8px; font-size: 13px; }
  .scroll { overflow-x: auto; }
  code { font-size: 12px; background: var(--secondary-background-color, #f0f0f0); padding: 1px 5px; border-radius: 4px; word-break: break-all; }
  .badge { font-size: 11px; padding: 1px 7px; border-radius: 8px; background: var(--secondary-background-color, #eee); color: var(--secondary-text-color); white-space: nowrap; }
  .badge.warn { background: color-mix(in srgb, var(--warning-color, #ffa600) 20%, transparent); color: var(--primary-text-color); }
  .badge.err { background: color-mix(in srgb, var(--error-color, #db4437) 16%, transparent); color: var(--primary-text-color); }
  .badges { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--success-color, #43a047); display: inline-block; flex: none; }
  .dot.off { background: var(--disabled-text-color, #bdbdbd); }
  .dot.warn { background: var(--warning-color, #ffa600); }
  .dot.err { background: var(--error-color, #db4437); }
  /* accounts */
  .tabs { display: flex; gap: 10px; flex-wrap: wrap; }
  .tab { flex: 1 1 240px; text-align: left; background: var(--card-background-color, #fff); color: var(--primary-text-color); border: 2px solid var(--divider-color, #e0e0e0); border-radius: var(--ha-card-border-radius, 12px); padding: 12px 14px; display: grid; gap: 4px; }
  .tab.active { border-color: var(--primary-color); box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 18%, transparent); }
  .tab .label { font-weight: 600; font-size: 15px; display: flex; align-items: center; gap: 8px; }
  .tab .meta { color: var(--secondary-text-color); font-size: 12.5px; }
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
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
  .stat { background: var(--secondary-background-color, #f5f5f5); border-radius: 10px; padding: 10px 12px; }
  .stat .k { font-size: 12px; color: var(--secondary-text-color); }
  .stat .v { font-size: 26px; font-weight: 500; line-height: 1.2; }
  .stat .s { font-size: 12px; color: var(--secondary-text-color); }
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
  .fbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; align-items: center; }
  .fbar input { flex: 1 1 200px; }
  .fbar .count { margin-left: auto; }
  .day { font-size: 12px; font-weight: 600; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .05em; margin: 14px 0 4px; }
  .day:first-child { margin-top: 0; }
  .ev { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; gap: 2px 10px; padding: 9px 4px; border-bottom: 1px solid var(--divider-color, #e0e0e0); align-items: start; }
  .ev .ico { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--primary-color) 12%, transparent); color: var(--primary-color); grid-row: span 2; }
  .ev .ico ha-icon { --mdc-icon-size: 17px; }
  .ev.bad .ico { background: color-mix(in srgb, var(--error-color, #db4437) 14%, transparent); color: var(--error-color, #db4437); }
  .ev .what { font-weight: 500; font-size: 14px; }
  .ev .what .chip { font-weight: 400; }
  .ev .when { font-size: 12.5px; color: var(--secondary-text-color); white-space: nowrap; text-align: right; }
  .ev .who { font-size: 12.5px; color: var(--secondary-text-color); }
  .ev .side { text-align: right; }
  .ev details { grid-column: 2 / -1; font-size: 12.5px; }
  .ev details summary { cursor: pointer; color: var(--primary-color); width: max-content; }
  .ev pre { margin: 6px 0 0; padding: 8px; background: var(--secondary-background-color, #f5f5f5); border-radius: 6px; white-space: pre-wrap; word-break: break-word; font-size: 12px; }
  .ev .errtext { grid-column: 2 / -1; font-size: 12.5px; color: var(--error-color, #db4437); }
  .hidden { display: none !important; }
  @media (max-width: 760px) {
    .toolbar { height: 52px; padding: 0 10px; font-size: 18px; }
    .content { padding: 10px; gap: 10px; }
    .card { padding: 12px; }
    .card h2 { font-size: 17px; }
    .usage-grid { grid-template-columns: 1fr; }
    .tabs .tab { flex-basis: 100%; }
    .stat .v { font-size: 22px; }
    button { min-height: 40px; }
    button.small, button.link, a.btn { min-height: 34px; }
    .fbar select { flex: 1 1 45%; }
    table.stack, table.stack tbody, table.stack tr, table.stack td { display: block; width: 100%; box-sizing: border-box; }
    table.stack thead { display: none; }
    table.stack tr { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 10px; padding: 8px 10px; margin-bottom: 10px; }
    table.stack td { border: none; padding: 4px 0; white-space: normal !important; }
    table.stack td[data-label]::before { content: attr(data-label); display: block; font-size: 11px; letter-spacing: .04em; text-transform: uppercase; color: var(--secondary-text-color); margin-bottom: 2px; }
    table.stack td[data-label=""]::before { display: none; }
    table.stack td.actions { display: flex; flex-wrap: wrap; gap: 6px; padding-top: 8px; }
  }
`;
