# Dev preview

A static preview of the Frieda and Frieda Postfach panels with **example data** (no real accounts, mails or AI
calls). The panels are the unchanged code of the working trees; `build.py` only points Frieda Postfach's import of
Frieda UI at the copy next to it.

```bash
python3 tools/preview/build.py                      # expects ../friedafetch-mail next to this repository
python3 -m http.server -d tools/preview/dist 8767   # then open http://127.0.0.1:8767/local.html
```

- `index.html` – the control bar (panel, light/dark, desktop/iPhone width, scenario).
- `frieda.html` – Frieda's panel with mock websocket data; `?tab=…` starts on a tab, `?scene=…` opens a scenario,
  `?dark=1` the dark theme, `?update=1` simulates a newer version on the server.
- Frieda Postfach's page, its example backend and its scenarios live in that repository (`tools/preview/postfach.html`,
  `mock-postfach.js`, `scenarios.json`): each repository keeps the examples and tests of its own panel.
- `harness.py` – the shared harness of the browser tests (build, local server, browsers), used by both repositories.
- The versions shown in the example data come from both `manifest.json` files (`build.py` fills them in).
- `dist/` is generated and not committed.

## Browser tests

`tests/` loads every scenario of Frieda's panel in Chromium and WebKit (the engine of Safari and of the Home Assistant
app on iPhone and iPad), on desktop and phone sizes, and checks what broke before. Frieda Postfach's panel has its own
tests in its repository, on the same harness. A change in one repository therefore never fails the other's CI.
Locally:

```bash
pip install --require-hashes -r requirements/ui.txt && python -m playwright install chromium webkit
cd tools/preview && python -m pytest -n auto --browser chromium --browser webkit   # POSTFACH_DIR=… if not ../friedafetch-mail
```
