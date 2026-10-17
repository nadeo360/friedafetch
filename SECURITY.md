# Security

*English · [Deutsch weiter unten](#sicherheit)*

## Reporting a vulnerability

Please do **not** open public issues for security problems. Use GitHub's private reporting instead:
**Security → Report a vulnerability** in this repository. You will get a response within 7 days; confirmed issues
are fixed in a release and described in the changelog without naming the reporter unless you wish otherwise.

## Supported versions

Only the latest release is supported. Older versions do not receive fixes.

## Security model of the integration

- **Credentials:** only an *app-specific password* of the Apple ID is used; it can be revoked at appleid.apple.com at
  any time. It is stored in the Home Assistant config entry (`.storage/core.config_entries`, readable only by the HA
  process) and redacted in diagnostics.
- **Connections:** the integration only talks to Apple endpoints (`caldav.icloud.com`, `contacts.icloud.com`,
  `imap.mail.me.com`, `smtp.mail.me.com` and their partitions `pXX-*.icloud.com`), always over TLS with the
  certificate store managed by Home Assistant. There is no telemetry and no third-party service.
- **Access to the tools:** the built-in MCP endpoint `/api/icloud_mcp` requires a Home Assistant access token
  (Bearer). The LLM API is only offered to the assistants/MCP servers an admin explicitly enables. The rules panel in
  the sidebar and its WebSocket commands are restricted to admin users.
- **Limiting the blast radius:** options allow switching off tool groups, enabling a read-only mode and forbidding
  sending e-mails and deleting separately. All tools carry MCP annotations (`readOnlyHint`, `destructiveHint`) so
  clients can recognise writing tools and ask for confirmation. Deleting means "move to trash" by default.
- **Input:** all tool parameters are validated against schemas; regex conditions in rules are length-limited and
  compiled before saving. Server responses (XML, vCard, e-mail) are parsed with the Python standard library; mail
  content is passed to the AI as text only.

## Checks in the repository

Every commit and pull request automatically runs:

- **tests** against the pinned Home Assistant release and **Ruff** including the Bandit rule set (`S`),
- **Bandit** as a separate static analysis,
- **CodeQL** via GitHub code scanning (default setup, Python and JavaScript, on every push and weekly),
- **pip-audit** against the runtime requirements from the manifest (daily as well); known, demonstrably
  non-applicable findings are excluded in the workflow with a justification (currently CVE-2026-59951: it concerns
  stateful MCP sessions only, this integration's endpoint is stateless),
- **hassfest** and **HACS validation**,
- **Dependabot** for Python dependencies and GitHub Actions; security alerts are enabled for the repository.

---

# Sicherheit

*[English above](#security) · Deutsch*

## Sicherheitslücke melden

Bitte **keine** öffentlichen Issues für Sicherheitsprobleme. Nutze stattdessen die private Meldung über GitHub:
**Security → Report a vulnerability** in diesem Repository. Du bekommst innerhalb von 7 Tagen eine Rückmeldung;
bestätigte Lücken werden mit einem Release behoben und im Changelog ohne Nennung der meldenden Person beschrieben,
sofern nicht anders gewünscht.

## Unterstützte Versionen

Es wird jeweils das neueste Release unterstützt. Ältere Versionen erhalten keine Korrekturen.

## Sicherheitsmodell der Integration

- **Zugangsdaten:** Es wird ausschließlich ein *anwendungsspezifisches Passwort* der Apple-ID verwendet, das jederzeit
  unter appleid.apple.com widerrufen werden kann. Das Passwort liegt im Config-Entry von Home Assistant
  (`.storage/core.config_entries`, nur für den HA-Prozess lesbar) und wird in Diagnosedaten geschwärzt.
- **Verbindungen:** Die Integration spricht nur Apple-Endpunkte an (`caldav.icloud.com`, `contacts.icloud.com`,
  `imap.mail.me.com`, `smtp.mail.me.com` und deren Partitionen `pXX-*.icloud.com`), immer über TLS mit dem von
  Home Assistant verwalteten Zertifikatsspeicher. Es gibt keine Telemetrie und keine Dritt-Dienste.
- **Zugriff auf die Tools:** Der eigene MCP-Endpunkt `/api/icloud_mcp` verlangt einen Home-Assistant-Zugriffstoken
  (Bearer). Die LLM-API wird nur den Assistenten/MCP-Servern angeboten, die der Admin ausdrücklich dafür freischaltet.
  Das Regel-Panel in der Seitenleiste und die zugehörigen WebSocket-Befehle sind Admin-Benutzern vorbehalten.
- **Begrenzung des Schadenspotenzials:** Über die Optionen lassen sich Tool-Gruppen abschalten, ein
  Nur-Lesen-Modus aktivieren sowie das Senden von E-Mails und das Löschen getrennt verbieten. Alle Tools tragen
  MCP-Annotationen (`readOnlyHint`, `destructiveHint`), sodass Clients schreibende Werkzeuge erkennen und
  Rückfragen stellen können. Löschen bedeutet standardmäßig „in den Papierkorb“.
- **Eingaben:** Alle Tool-Parameter werden gegen Schemas validiert; Regex-Bedingungen in Regeln sind längenbegrenzt
  und werden vor dem Speichern kompiliert. Serverantworten (XML, vCard, E-Mail) werden mit der Python-Standardbibliothek
  geparst, Mail-Inhalte werden nur als Text an die KI weitergegeben.

## Prüfungen im Repository

Jeder Commit und jeder Pull Request durchläuft automatisch:

- **Tests** gegen die gepinnte Home-Assistant-Version und **Ruff** inklusive Sicherheitsregeln (Bandit-Regelsatz `S`),
- **Bandit** als eigenständige statische Analyse,
- **CodeQL** über GitHubs Code-Scanning (Default Setup, Python und JavaScript, bei jedem Push und wöchentlich),
- **pip-audit** gegen die Laufzeitabhängigkeiten aus dem Manifest (zusätzlich täglich); bekannte, nachweislich nicht
  zutreffende Meldungen werden im Workflow mit Begründung ausgenommen (derzeit CVE-2026-59951: betrifft nur
  zustandsbehaftete MCP-Sitzungen, der Endpunkt dieser Integration arbeitet zustandslos),
- **hassfest** und **HACS-Validierung**,
- **Dependabot** für Python-Abhängigkeiten und GitHub Actions; Sicherheitswarnungen sind für das Repository aktiviert.
