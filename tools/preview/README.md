# Dev preview

A static preview of the Frieda and Frieda Postfach panels with **example data** (no real accounts, mails or AI
calls). The panels are the unchanged code of the working trees; `build.py` only points Frieda Postfach's import of
Frieda UI at the copy next to it.

```bash
python3 tools/preview/build.py                      # expects ../friedafetch-mail next to this repository
python3 -m http.server -d tools/preview/dist 8767   # then open http://127.0.0.1:8767/local.html
```

- `index.html` – the control bar (panel, light/dark, desktop/iPhone width, scenario).
- `frieda.html`, `postfach.html` – the panels with mock websocket data; `?tab=…` starts on a tab, `?scene=…` opens a
  scenario, `?dark=1` the dark theme, `?update=1` simulates a newer version on the server, `?volume=1` (Postfach) a
  busy mailbox with about 100 mails a day.
- `mock-postfach.js` – the example backend of Frieda Postfach. Activity, runs, AI ratings and the AI log are built from
  the same example mails, so every view tells the same story; it also answers the commands of the panel (rules,
  re-rating, timeline, location, category assistant). Frieda's change log links to mails of it.
- The versions shown in the example data come from both `manifest.json` files (`build.py` fills them in).
- `dist/` is generated and not committed.
