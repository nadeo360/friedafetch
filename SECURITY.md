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
- **Access to the tools:** the built-in MCP endpoint `/api/friedafetch` requires a Home Assistant access token
  (Bearer). The LLM API is only offered to the assistants/MCP servers an admin explicitly enables. The rules panel in
  the sidebar and its WebSocket commands are restricted to admin users.
- **Limiting the blast radius:** options allow switching off tool groups, enabling a read-only mode and forbidding
  sending e-mails and deleting separately. Hourly quotas, a recipient policy (contacts/allowlist), protected
  calendars and mailboxes and hidden mailboxes further bound what a connected client can do; every writing call is
  written to a per-account audit log and fired as the `friedafetch_action` event. Optional approvals park sending,
  deleting and mass actions until an admin approves them (notification, actionable push or panel); the read-only
  endpoint profile `/api/friedafetch/readonly` and the admin-only switch restrict what a token can reach. All tools carry MCP annotations (`readOnlyHint`, `destructiveHint`) so
  clients can recognise writing tools and ask for confirmation. Deleting means "move to trash" by default.
- **Untrusted content:** mail, note and event texts are sanitised (invisible/bidi characters), labelled as third-party
  content and scanned for prompt-injection patterns (`suspicious`/`warnings` flags).
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

## Threat model (summary)

| Threat | Mitigation |
|--------|------------|
| Stolen or leaked Home Assistant token used against the MCP endpoint | Tokens can be revoked in HA; optional admin-only restriction; read-only profile for less trusted clients; quotas limit damage per hour; every writing call is audited. |
| Prompt injection via e-mail, notes or calendar content making the AI act against the user | Content is sanitised, labelled as third-party data and scanned for injection patterns (`suspicious`); the prompt forbids following embedded instructions; approvals and quotas bound the consequences. |
| Runaway or buggy agent deleting or sending in bulk | Hourly quotas, recipient policy, protected/hidden areas, approvals for sending/deleting/mass actions, trash instead of permanent deletion, audit log and `friedafetch_action` events for alerting. |
| Compromised dependency or build | Pinned dependencies with pip-audit, Bandit/Ruff/CodeQL, GitHub Actions pinned to commit SHAs, OpenSSF Scorecard, SBOM and signed build provenance for release assets, Dependabot, protected `main` branch. |
| Loss of the app-specific password from HA storage | The password is only as safe as the HA instance; keep HA updated, use strong admin passwords/2FA, revoke the app-specific password at Apple if in doubt. |

## Verifying a release

Release assets are built by GitHub Actions and carry a signed build provenance attestation (Sigstore). Verify:

```bash
gh attestation verify friedafetch.zip --repo nadeo360/friedafetch
```

A CycloneDX SBOM (`sbom.cdx.json`) listing the runtime dependencies is attached to every release.

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
- **Zugriff auf die Tools:** Der eigene MCP-Endpunkt `/api/friedafetch` verlangt einen Home-Assistant-Zugriffstoken
  (Bearer). Die LLM-API wird nur den Assistenten/MCP-Servern angeboten, die der Admin ausdrücklich dafür freischaltet.
  Das Regel-Panel in der Seitenleiste und die zugehörigen WebSocket-Befehle sind Admin-Benutzern vorbehalten.
- **Begrenzung des Schadenspotenzials:** Über die Optionen lassen sich Tool-Gruppen abschalten, ein
  Nur-Lesen-Modus aktivieren sowie das Senden von E-Mails und das Löschen getrennt verbieten. Stundenkontingente,
  eine Empfänger-Richtlinie (Kontakte/Allowlist), geschützte Kalender und Postfächer sowie verborgene Postfächer
  begrenzen zusätzlich, was ein verbundener Client tun kann; jeder schreibende Aufruf landet im Aktivitätsprotokoll
  des Kontos und wird als Ereignis `friedafetch_action` gefeuert. Optionale Freigaben parken Senden, Löschen und
  Massenaktionen, bis ein Admin sie freigibt (Benachrichtigung, Push mit Buttons oder Panel); das Nur-Lese-Profil
  `/api/friedafetch/readonly` und der Admin-only-Schalter begrenzen, was ein Token erreicht. Alle Tools tragen
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

## Bedrohungsmodell (Kurzfassung)

| Bedrohung | Gegenmaßnahme |
|-----------|---------------|
| Gestohlener oder geleakter Home-Assistant-Token gegen den MCP-Endpunkt | Tokens sind in HA widerrufbar; optionale Admin-only-Beschränkung; Nur-Lese-Profil für weniger vertrauenswürdige Clients; Kontingente begrenzen den Schaden pro Stunde; jeder schreibende Aufruf wird protokolliert. |
| Prompt-Injection über Mail-, Notiz- oder Kalenderinhalte, die die KI gegen den Nutzer handeln lässt | Inhalte werden bereinigt, als Fremddaten gekennzeichnet und auf Injektionsmuster geprüft (`suspicious`); der Prompt verbietet das Befolgen eingebetteter Anweisungen; Freigaben und Kontingente begrenzen die Folgen. |
| Außer Kontrolle geratener oder fehlerhafter Agent, der massenhaft löscht oder sendet | Stundenkontingente, Empfänger-Richtlinie, geschützte/verborgene Bereiche, Freigaben für Senden/Löschen/Massenaktionen, Papierkorb statt endgültigem Löschen, Aktivitätsprotokoll und Ereignisse `friedafetch_action` zur Alarmierung. |
| Kompromittierte Abhängigkeit oder Build | Gepinnte Abhängigkeiten mit pip-audit, Bandit/Ruff/CodeQL, GitHub Actions auf Commit-SHAs gepinnt, OpenSSF Scorecard, SBOM und signierte Build-Provenance für Release-Artefakte, Dependabot, geschützter `main`-Branch. |
| Verlust des App-Passworts aus dem HA-Speicher | Das Passwort ist nur so sicher wie die HA-Instanz; HA aktuell halten, starke Admin-Passwörter/2FA nutzen, im Zweifel das App-Passwort bei Apple widerrufen. |

## Release prüfen

Release-Artefakte werden von GitHub Actions gebaut und tragen eine signierte Build-Provenance (Sigstore). Prüfung:

```bash
gh attestation verify friedafetch.zip --repo nadeo360/friedafetch
```

Jedem Release liegt eine CycloneDX-SBOM (`sbom.cdx.json`) der Laufzeitabhängigkeiten bei.
