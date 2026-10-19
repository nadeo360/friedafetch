# Contributing to Frieda

*Deutsche Fassung weiter unten.*

Thanks for wanting to help! Frieda is maintained by one person in their spare time – bug reports, ideas and pull
requests are welcome, answers may take a few days.

## Reporting bugs and ideas

- Please use the issue templates (**Issues → New issue**). They ask for the versions of Frieda, Frieda Postfach and
  Home Assistant, what you did and what happened.
- A log excerpt helps a lot: **Settings → System → Logs**, filter for `friedafetch`.
- **Never post** app-specific passwords, tokens, mail contents or addresses you do not want to make public. Remove
  personal data from logs and screenshots.
- **Security problems do not belong in an issue** – please report them privately as described in
  [SECURITY.md](SECURITY.md).

## Pull requests

- For larger changes please open an issue first, so we can agree on the approach before you invest time.
- Fork the repository, create a branch from `main` and open the pull request against `main`. Small, focused pull
  requests are easier to review.
- The CI must be green: Ruff (lint and format), the test suite, hassfest, HACS validation, Bandit, CodeQL and
  pip-audit.
- Changes in behaviour come with tests. Please update the README (English and German) and, where it matters, the
  architecture document [docs/architecture.md](docs/architecture.md).
- Texts of the options flow live in `strings.json`, `translations/en.json` and `translations/de.json` – keep all three
  in sync.
- Panel changes use the shared design library *Frieda UI* (`custom_components/friedafetch/frontend/ui.js`) and are
  checked in light and dark themes and at phone width. Information must not depend on hovering.
- By contributing you agree that your contribution is published under the [MIT license](LICENSE).

## Development setup

Home Assistant 2026.10 needs Python ≥ 3.14.2.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_dev.txt
pytest
ruff check custom_components tests && ruff format custom_components tests
```

- CI installs its tools from hash-pinned lock files in `requirements/`. After changing `requirements_dev.txt`, a
  `requirements/*.in` file or the requirements in `manifest.json`, run `scripts/lock_requirements.sh` (needs
  [uv](https://docs.astral.sh/uv/)) and commit the updated `requirements/*.txt`.
- Icons and logos: `assets/*.svg` are the sources, `scripts/build_icons.py` renders the PNG variants.
- Frieda Postfach (the automation) lives in its own repository,
  [nadeo360/friedafetch-mail](https://github.com/nadeo360/friedafetch-mail).

## Code of conduct

Please be friendly and constructive – see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

# Mitmachen bei Frieda

Danke, dass du helfen möchtest! Frieda wird von einer Person in der Freizeit gepflegt – Fehlermeldungen, Ideen und
Pull Requests sind willkommen, Antworten können ein paar Tage dauern.

## Fehler und Ideen melden

- Bitte nutze die Vorlagen (**Issues → New issue**). Sie fragen nach den Versionen von Frieda, Frieda Postfach und
  Home Assistant, was du gemacht hast und was passiert ist.
- Ein Log-Auszug hilft sehr: **Einstellungen → System → Protokolle**, nach `friedafetch` filtern.
- **Niemals posten:** app-spezifische Passwörter, Tokens, Mail-Inhalte oder Adressen, die nicht öffentlich werden
  sollen. Entferne persönliche Daten aus Logs und Screenshots.
- **Sicherheitsprobleme gehören nicht in ein Issue** – bitte privat melden, wie in [SECURITY.md](SECURITY.md)
  beschrieben.

## Pull Requests

- Bei größeren Änderungen bitte zuerst ein Issue öffnen, damit wir den Weg abstimmen, bevor du Zeit investierst.
- Repository forken, Zweig von `main` anlegen und den Pull Request gegen `main` stellen. Kleine, fokussierte Pull
  Requests lassen sich leichter prüfen.
- Die CI muss grün sein: Ruff (Lint und Format), Tests, hassfest, HACS-Validierung, Bandit, CodeQL und pip-audit.
- Geändertes Verhalten kommt mit Tests. Bitte README (englisch und deutsch) und, wo es zählt, das Architektur-Dokument
  [docs/architecture.de.md](docs/architecture.de.md) aktualisieren.
- Texte der Options-Dialoge stehen in `strings.json`, `translations/en.json` und `translations/de.json` – alle drei
  synchron halten.
- Panel-Änderungen nutzen die gemeinsame Design-Bibliothek *Frieda UI* (`custom_components/friedafetch/frontend/ui.js`)
  und werden hell, dunkel und in Handybreite geprüft. Informationen dürfen nicht nur beim Überfahren mit der Maus
  sichtbar sein.
- Mit deinem Beitrag stimmst du zu, dass er unter der [MIT-Lizenz](LICENSE) veröffentlicht wird.

## Entwicklungsumgebung

Home Assistant 2026.10 braucht Python ≥ 3.14.2.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_dev.txt
pytest
ruff check custom_components tests && ruff format custom_components tests
```

- Die CI installiert ihre Werkzeuge aus hash-gesperrten Dateien in `requirements/`. Nach Änderungen an
  `requirements_dev.txt`, einer `requirements/*.in` oder den Anforderungen in `manifest.json` bitte
  `scripts/lock_requirements.sh` ausführen (braucht [uv](https://docs.astral.sh/uv/)) und die aktualisierten
  `requirements/*.txt` mit committen.
- Icons und Logos: Quellen sind `assets/*.svg`, `scripts/build_icons.py` erzeugt die PNG-Varianten.
- Frieda Postfach (die Automatik) liegt in einem eigenen Repository,
  [nadeo360/friedafetch-mail](https://github.com/nadeo360/friedafetch-mail).

## Verhaltenskodex

Bitte freundlich und konstruktiv bleiben – siehe [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
