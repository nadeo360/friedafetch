# Sicherheit

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
