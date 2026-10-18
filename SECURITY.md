# Security

*English · [Deutsch weiter unten](#sicherheit)*

## Reporting a vulnerability

Please do **not** open public issues for security problems. Use GitHub's private reporting instead:
**Security → Report a vulnerability** in this repository
([direct link](https://github.com/nadeo360/friedafetch/security/advisories/new)). You will get a response within 7 days; confirmed issues
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
  content and scanned for prompt-injection patterns (`suspicious`/`warnings` flags). The **injection lock** then holds
  back critical calls of the same caller (send, delete, unsubscribe, deleting/moving rules, real rule runs) for a
  configurable time: parked for approval, or blocked when approvals are off.
- **Rules and AI sorting are bounded:** rule tools that create deleting/moving rules or run rules over the whole
  mailbox follow the approvals; unattended and AI-requested rule runs are capped per run (100 changes, 50 deletions)
  and, like AI sorting, count against the hourly mail-change quota.
- **Delayed sending and persistent state:** optionally, e-mails from assistants wait a configurable time (up to ten
  minutes) and can be cancelled in the panel or from the notification. Quota usage, injection locks and approval
  requests are stored per account in Home Assistant's `.storage` (`friedafetch.state.<entry>`; approval parameters
  shortened as in the audit log), so restarts neither refill quotas nor lift locks. Requests left open by a restart
  are closed and never executed later.
- **Input:** all tool parameters are validated against schemas; regex conditions in rules are length-limited,
  compiled before saving and refused when they could block Home Assistant (nested repetition such as `(a+)+`, or
  measured as too slow on hostile headers); stored patterns are checked again before use and only see the first
  300 characters of a header. Parsers of third-party data are fuzzed with Hypothesis. Server responses (XML, vCard, e-mail) are parsed with the Python standard library; mail
  content is passed to the AI as text only.
- **Contacts cache:** contacts are cached only in memory and every vCard is encrypted there (AES-256-GCM with a
  random key per process that is never stored); nothing of it is written to disk or included in diagnostics.
- **Usage counters:** the panel's usage card stores only counts (per day, tool and source) and the name and version an
  MCP client announces in its handshake (`.storage/friedafetch.usage`); no arguments, results or mail content.

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
| Prompt injection via e-mail, notes or calendar content making the AI act against the user | Content is sanitised, labelled as third-party data and scanned for injection patterns (`suspicious`); the prompt forbids following embedded instructions; the injection lock holds back sending/deleting of the same caller afterwards; approvals and quotas bound the consequences. |
| Runaway or buggy agent deleting or sending in bulk | Hourly quotas, recipient policy, protected/hidden areas, approvals for sending/deleting/mass actions, trash instead of permanent deletion, approvals and per-run caps also for rules, audit log and `friedafetch_action` events for alerting. |
| Compromised dependency or build | Pinned dependencies with pip-audit, Bandit/Ruff/CodeQL, GitHub Actions pinned to commit SHAs, OpenSSF Scorecard, SBOM and signed build provenance for release assets, Dependabot, protected `main` branch. |
| Malicious unsubscribe links in e-mail used to reach the local network (SSRF) | The link is checked in the exact form the HTTP client uses (IDNA/UTS 46 normalisation, so full-width or other-script digits cannot hide 127.0.0.1); only https on port 443, no credentials, no local host names and no numeric shorthand hosts; the connection uses a resolver that drops private, loopback and link-local addresses (also against DNS rebinding); no redirects, no cookies, fixed request body; links without one-click support are never fetched. |
| Attachments written outside the intended folder | Folder must be allowed by Home Assistant; subfolders and file names are reduced to safe segments; the resolved target must stay below the attachment folder (symlinks included); size limit 25 MB per file. |
| Loss of the app-specific password from HA storage | The password is only as safe as the HA instance; keep HA updated, use strong admin passwords/2FA, revoke the app-specific password at Apple if in doubt. |

## Verifying a release

Release assets are built by GitHub Actions and carry a signed build provenance attestation (Sigstore). Verify:

```bash
gh attestation verify friedafetch.zip --repo nadeo360/friedafetch
```

The signature also comes with the release: `friedafetch.zip.sigstore.json` (Sigstore bundle, for offline checks with
`gh attestation verify friedafetch.zip --repo nadeo360/friedafetch --bundle friedafetch.zip.sigstore.json`) and
`friedafetch.zip.intoto.jsonl` (the SLSA provenance).

A CycloneDX SBOM (`sbom.cdx.json`) listing the runtime dependencies is attached to every release.

---

# Sicherheit

*[English above](#security) · Deutsch*

## Sicherheitslücke melden

Bitte **keine** öffentlichen Issues für Sicherheitsprobleme. Nutze stattdessen die private Meldung über GitHub:
**Security → Report a vulnerability** in diesem Repository
([direkter Link](https://github.com/nadeo360/friedafetch/security/advisories/new)). Du bekommst innerhalb von 7 Tagen eine Rückmeldung;
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
  begrenzen zusätzlich, was ein verbundener Client tun kann; jeder schreibende Aufruf landet im Änderungsprotokoll
  des Kontos und wird als Ereignis `friedafetch_action` gefeuert. Optionale Freigaben parken Senden, Löschen und
  Massenaktionen, bis ein Admin sie freigibt (Benachrichtigung, Push mit Buttons oder Panel); das Nur-Lese-Profil
  `/api/friedafetch/readonly` und der Admin-only-Schalter begrenzen, was ein Token erreicht. Alle Tools tragen
  MCP-Annotationen (`readOnlyHint`, `destructiveHint`), sodass Clients schreibende Werkzeuge erkennen und
  Rückfragen stellen können. Löschen bedeutet standardmäßig „in den Papierkorb“.
- **Injection-Sperre:** Liefert ein Tool Inhalte mit `suspicious`-Markierung, hält Frieda kritische Aufrufe desselben
  Aufrufers (Senden, Löschen, Abmelden, löschende/verschiebende Regeln, echte Regelläufe) eine einstellbare Zeit lang
  zurück: zur Freigabe geparkt oder, ohne Freigaben, blockiert.
- **Regeln und KI-Sortierung sind begrenzt:** Regel-Tools, die löschende/verschiebende Regeln anlegen oder Regeln über
  das ganze Postfach anwenden, folgen den Freigaben; unbeaufsichtigte und von einer KI angestoßene Regelläufe sind pro
  Lauf begrenzt (100 Änderungen, 50 Löschungen) und zählen – wie die KI-Sortierung – gegen das Stundenkontingent.
- **Eingaben:** Alle Tool-Parameter werden gegen Schemas validiert; Regex-Bedingungen in Regeln sind längenbegrenzt,
  werden vor dem Speichern kompiliert und abgelehnt, wenn sie Home Assistant blockieren könnten (verschachtelte
  Wiederholung wie `(a+)+` oder gemessen zu langsam auf feindlichen Kopfzeilen); gespeicherte Muster werden vor der
  Nutzung erneut geprüft und sehen nur die ersten 300 Zeichen einer Kopfzeile. Parser für Fremddaten werden mit
  Hypothesis gefuzzt. Serverantworten (XML, vCard, E-Mail) werden mit der Python-Standardbibliothek
  geparst, Mail-Inhalte werden nur als Text an die KI weitergegeben.
- **Kontakte-Cache:** Kontakte werden nur im Speicher zwischengespeichert, jede vCard dort verschlüsselt (AES-256-GCM
  mit einem zufälligen Schlüssel pro Prozess, der nie gespeichert wird); nichts davon landet auf der Platte oder in
  Diagnosedaten.
- **Nutzungszähler:** Die Karte „Nutzung“ speichert nur Zahlen (pro Tag, Tool und Herkunft) sowie Name und Version,
  die ein MCP-Client im Handshake meldet (`.storage/friedafetch.usage`); keine Argumente, Ergebnisse oder Mail-Inhalte.

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
| Prompt-Injection über Mail-, Notiz- oder Kalenderinhalte, die die KI gegen den Nutzer handeln lässt | Inhalte werden bereinigt, als Fremddaten gekennzeichnet und auf Injektionsmuster geprüft (`suspicious`); der Prompt verbietet das Befolgen eingebetteter Anweisungen; die Injection-Sperre hält danach Senden/Löschen desselben Aufrufers zurück; Freigaben und Kontingente begrenzen die Folgen. |
| Außer Kontrolle geratener oder fehlerhafter Agent, der massenhaft löscht oder sendet | Stundenkontingente, Empfänger-Richtlinie, geschützte/verborgene Bereiche, Freigaben für Senden/Löschen/Massenaktionen, Freigaben und Obergrenzen pro Lauf auch für Regeln, Papierkorb statt endgültigem Löschen, Änderungsprotokoll und Ereignisse `friedafetch_action` zur Alarmierung. |
| Kompromittierte Abhängigkeit oder Build | Gepinnte Abhängigkeiten mit pip-audit, Bandit/Ruff/CodeQL, GitHub Actions auf Commit-SHAs gepinnt, OpenSSF Scorecard, SBOM und signierte Build-Provenance für Release-Artefakte, Dependabot, geschützter `main`-Branch. |
| Präparierte Abmelde-Links in Mails, die ins lokale Netz zielen (SSRF) | Der Link wird in genau der Form geprüft, die der HTTP-Client verwendet (IDNA/UTS-46-Normalisierung, damit vollbreite oder fremdschriftliche Ziffern kein 127.0.0.1 verstecken); nur https auf Port 443, keine Zugangsdaten, keine lokalen Hostnamen und keine numerischen Kurzformen; die Verbindung nutzt einen Resolver, der private, Loopback- und Link-Local-Adressen verwirft (auch gegen DNS-Rebinding); keine Weiterleitungen, keine Cookies, fester Request-Inhalt; Links ohne Ein-Klick-Unterstützung werden nie aufgerufen. |
| Anhänge, die außerhalb des vorgesehenen Ordners landen | Ordner muss von Home Assistant erlaubt sein; Unterordner und Dateinamen werden auf sichere Bestandteile reduziert; das aufgelöste Ziel muss unterhalb des Anhang-Ordners liegen (auch bei Symlinks); Größenlimit 25 MB pro Datei. |
| Verlust des App-Passworts aus dem HA-Speicher | Das Passwort ist nur so sicher wie die HA-Instanz; HA aktuell halten, starke Admin-Passwörter/2FA nutzen, im Zweifel das App-Passwort bei Apple widerrufen. |

## Release prüfen

Release-Artefakte werden von GitHub Actions gebaut und tragen eine signierte Build-Provenance (Sigstore). Prüfung:

```bash
gh attestation verify friedafetch.zip --repo nadeo360/friedafetch
```

Die Signatur liegt auch am Release: `friedafetch.zip.sigstore.json` (Sigstore-Bundle, für die Prüfung ohne Netz mit
`--bundle friedafetch.zip.sigstore.json`) und `friedafetch.zip.intoto.jsonl` (die SLSA-Provenance).

Jedem Release liegt eine CycloneDX-SBOM (`sbom.cdx.json`) der Laufzeitabhängigkeiten bei.
