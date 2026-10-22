<p align="center">
  <img src="https://raw.githubusercontent.com/nadeo360/friedafetch/main/assets/logo@2x.png" alt="Frieda" width="720">
</p>

<p align="center">
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/nadeo360/friedafetch/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/validate.yml"><img alt="hassfest & HACS" src="https://github.com/nadeo360/friedafetch/actions/workflows/validate.yml/badge.svg"></a>
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/nadeo360/friedafetch/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/security.yml"><img alt="Dependency audit" src="https://github.com/nadeo360/friedafetch/actions/workflows/security.yml/badge.svg"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/nadeo360/friedafetch"><img alt="OpenSSF Scorecard" src="https://api.scorecard.dev/projects/github.com/nadeo360/friedafetch/badge"></a>
  <a href="https://github.com/nadeo360/friedafetch/releases"><img alt="Release" src="https://img.shields.io/github/v/release/nadeo360/friedafetch?display_name=tag"></a>
  <a href="https://github.com/nadeo360/friedafetch/blob/main/LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

<p align="center"><a href="https://github.com/nadeo360/friedafetch/blob/main/README.md">English</a> · <b>Deutsch</b></p>

# Frieda – MCP connector for iCloud

**Frieda** (technischer Name `friedafetch`) ist eine Home-Assistant-Integration (HACS), die **Apple iCloud** per anwendungsspezifischem Passwort anbindet und
**Kalender, Kontakte, E-Mails und Notizen** als Werkzeuge (Tools) für LLMs bereitstellt. Die Tools werden als
Home-Assistant-**LLM-API** registriert und über einen **eigenen MCP-Endpunkt** (`/api/friedafetch`, Streamable HTTP)
sowie optional über die **MCP-Server-Integration** von Home Assistant (Model Context Protocol) an MCP-Clients wie
Claude, ChatGPT-Connectors oder lokale Agenten ausgeliefert. Sie stehen außerdem jedem Home-Assistant-Sprachassistenten
(Assist, Google Generative AI, OpenAI, Ollama …) zur Verfügung, der diese LLM-API aktiviert hat. Posteingangsregeln,
Push und Tagesüberblick bringt die eigene Erweiterung [Frieda Postfach](https://github.com/nadeo360/friedafetch-mail)
mit. Benannt ist das Projekt nach Frieda, der Hündin des Maintainers, die im Logo aus der Wolke schaut.

## Funktionsumfang

| Bereich   | Protokoll          | Lesen                                   | Schreiben                                                     |
|-----------|--------------------|-----------------------------------------|---------------------------------------------------------------|
| Kalender  | CalDAV             | Kalender auflisten, Termine (inkl. Serien) suchen/lesen | Termin anlegen, ändern (inkl. RRULE), löschen       |
| Kontakte  | CardDAV            | Kontakte suchen (Name, Mail, Telefon, Firma …), lesen | Kontakt anlegen, ändern, löschen                    |
| E-Mail    | IMAP + SMTP        | Postfächer, Suche/Filter, Mail lesen (Text, Anhänge-Liste) | Senden/Antworten, gelesen/markiert, verschieben, Papierkorb |
| Notizen   | IMAP-Ordner `Notes`| Notizen auflisten/suchen/lesen          | Notiz anlegen, ändern, löschen                                |
| Regeln    | –                  | mit der Erweiterung [Frieda Postfach](https://github.com/nadeo360/friedafetch-mail) | Posteingangsregeln, Push, Tagesüberblick |
| Auswertungen | alle oben       | Postfach-Statistik, freie Zeitfenster, Geburtstage, doppelte Kontakte | Newsletter abbestellen, Anhänge (Belege) ablegen |

### Wichtiger Hinweis zu Notizen

Apple bietet für **moderne iCloud-Notizen** (CloudKit, Standard seit iOS 9 / „aktualisierte Notizen“) **keine**
Schnittstelle an, die mit einem anwendungsspezifischen Passwort erreichbar wäre. Die Integration kann daher nur
Notizen lesen und schreiben, die im **IMAP-Ordner „Notes“** des iCloud-Mail-Kontos liegen (klassische IMAP-Notizen).
Existiert dieser Ordner nicht, melden die Notiz-Tools das klar zurück. Die übrigen drei Bereiche nutzen offizielle,
stabile Protokolle (CalDAV, CardDAV, IMAP, SMTP) und sind vollständig nutzbar.

## Voraussetzungen

- Home Assistant **2026.10** oder neuer (die Integration nutzt die aktuelle `llm.Tool`-API mit `probatio`-Schemas;
  ältere Versionen ab 2025 funktionieren über den eingebauten `voluptuous`-Fallback, sind aber ungetestet).
- Apple-ID mit aktivierter **Zwei-Faktor-Authentifizierung** und ein **anwendungsspezifisches Passwort**
  (appleid.apple.com → Anmeldung und Sicherheit → App-spezifische Passwörter).
- Für E-Mail/Notizen muss **iCloud Mail** für die Apple-ID aktiviert sein.
- Für MCP-Clients ist **keine** weitere Integration nötig: die Integration bringt einen eigenen Endpunkt mit (siehe
  [Eigener MCP-Endpunkt](#eigener-mcp-endpunkt)). Alternativ liefert auch die Core-Integration
  **„Model Context Protocol Server“** (`mcp_server`) die Tools aus.

## Installation

### HACS (empfohlen)

1. HACS → Integrationen → ⋮ → **Benutzerdefinierte Repositories** → URL dieses Repositories, Kategorie *Integration*.
2. „Frieda“ installieren und Home Assistant neu starten.

### Manuell

Ordner `custom_components/friedafetch` in das `custom_components`-Verzeichnis der Home-Assistant-Konfiguration kopieren
und Home Assistant neu starten.


### Umstieg auf 2.0

Frieda 2.0 ist ein reiner Connector: Posteingangsregeln, Push, Tagesüberblick und Geburtstags-Sensor sind in die
eigene Integration [**Frieda Postfach**](https://github.com/nadeo360/friedafetch-mail) umgezogen. Über HACS
installieren und für das Konto hinzufügen – vorhandene Regeln, Trefferzähler, Verlauf und Automatik-Einstellungen
werden automatisch übernommen. Bis dahin zeigt Frieda für Konten mit gespeicherten Regeln eine Reparaturmeldung, und es
laufen keine Regeln. Die Regel-Tools (`icloud_*_rule`, `icloud_run_rules`, `icloud_daily_overview`) erscheinen wieder,
sobald Frieda Postfach eingerichtet ist.

### Umstieg von „iCloud MCP“ (Versionen bis 1.0.x)

Mit Version 1.1.0 wurde das Projekt in Frieda umbenannt; die Integrations-Domain wechselte von `icloud_mcp` zu
`friedafetch`. Alte Integration entfernen (Einstellungen → Geräte & Dienste → iCloud MCP → Löschen), das
benutzerdefinierte HACS-Repository auf `https://github.com/nadeo360/friedafetch` ändern, Frieda installieren und mit
Apple-ID und App-Passwort neu hinzufügen. Regeln und Optionen werden nicht übernommen; MCP-Clients brauchen den neuen
Endpunkt `/api/friedafetch`. Die Tool-Namen (`icloud_*`) sind unverändert. Bleibt ein alter Ordner
`custom_components/icloud_mcp` liegen, lädt Home Assistant unter Umständen weiter diesen statt der aktuellen Version
(beide melden die Domain `friedafetch`); Frieda erkennt das beim Start und zeigt eine Reparaturmeldung – den dort
genannten Ordner löschen und Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „Frieda“**.
2. Apple-ID und anwendungsspezifisches Passwort eingeben. Die Zugangsdaten werden gegen CalDAV geprüft (Pflicht) und
   gegen IMAP (optional – schlägt IMAP fehl, werden Mail- und Notiz-Tools zunächst deaktiviert).
3. **MCP-Client verbinden:** Entweder den [eigenen MCP-Endpunkt](#eigener-mcp-endpunkt) `/api/friedafetch` verwenden
   (empfohlen, keine weitere Integration nötig) – oder die Core-Integration **„Model Context Protocol Server“**
   (`mcp_server`) hinzufügen und dort unter **Konfigurieren** entweder „alle LLM-APIs“ aktivieren oder in der Liste
   **„iCloud (Kalender, Kontakte, Mail, Notizen)“** zusätzlich zu *Assist* auswählen. Danach sieht jeder verbundene
   MCP-Client die `icloud_*`-Tools.

   > **Hinweis zu `mcp_server_http_transport` (hass-mcp-server):** Diese HACS-Integration bringt einen eigenen,
   > fest verdrahteten Tool-Satz mit und reicht Home-Assistant-LLM-APIs **nicht** durch. Die iCloud-Tools erscheinen
   > dort also nicht. Beide Server können parallel laufen; laut README von hass-mcp-server verwendet dieser dann den
   > Pfad `/api/mcp_http`, während die Core-Integration `/api/mcp` belegt.
4. Optional für Sprachassistenten: In der jeweiligen Conversation-Integration (z. B. Google Generative AI) unter
   „Steuerung von Home Assistant“ die iCloud-LLM-API aktivieren.

### Optionen (Konfigurieren)

Der Optionsdialog hat drei Bereiche: **Tools und Konto**, **Sicherheit und Leitplanken** und **Freigaben**.

| Option                       | Wirkung                                                                 |
|------------------------------|-------------------------------------------------------------------------|
| Kalender-/Kontakt-/E-Mail-/Notiz-Tools | Tool-Gruppen einzeln ein- oder ausblenden                      |
| Nur-Lesen-Modus              | Blendet sämtliche Erstellen/Ändern/Löschen/Senden-Tools aus             |
| Senden von E-Mails erlauben  | Versteckt `icloud_send_mail`, wenn deaktiviert                          |
| Löschen erlauben             | Versteckt alle `icloud_delete_*`-Tools, wenn deaktiviert                |
| Standard-Maximalanzahl       | Standard-Limit für Listen (1–200)                                       |
| Absenderadresse              | `From:` für ausgehende Mails (Standard: Apple-ID; muss ein iCloud-Alias sein) |
| Ordner für Anhänge           | Ablage für `icloud_save_attachments` (und Regeln von Frieda Postfach) (Standard `<media>/frieda`; muss ein erlaubter Pfad sein) |
| Kontobezeichnung             | Kurzname, der bei mehreren Konten als Tool-Suffix dient                      |
| Bereich Sicherheit           | Kontingente, Empfänger-Richtlinie, geschützte Kalender/Postfächer, verborgene Postfächer (siehe Sicherheit) |

Alle Tools tragen MCP-Annotations (`readOnlyHint`, `destructiveHint`), sodass Clients im „nur lesen“-Modus die
schreibenden Tools automatisch weglassen.

Abgeschaltete Fähigkeiten verschwinden nicht stillschweigend: Der LLM-Prompt (und die `instructions` des eigenen
MCP-Endpunkts) nennt, was der Administrator deaktiviert hat, damit die KI dem Nutzer erklären kann, *warum* sie nicht
senden oder löschen kann und wo es sich einschalten lässt (Einstellungen → Geräte & Dienste → Frieda →
Konfigurieren). Ebenso werden aktive Freigaben angekündigt, sodass ein `approval_required`-Ergebnis als „wartet auf
Freigabe“ erklärt wird und nicht als Fehler.

## Eigener MCP-Endpunkt

Die Integration registriert einen eigenen **MCP-Endpunkt (Streamable HTTP)**, der die `icloud_*`-Tools direkt
ausliefert – unabhängig von der Core-Integration `mcp_server` und ohne Umweg über eine LLM-API-Auswahl. Der Endpunkt
ist zustandslos (jede Anfrage enthält genau eine JSON-RPC-Nachricht) und ist aktiv, sobald mindestens ein
iCloud-Config-Entry geladen ist; ohne geladenen Entry antwortet er mit `404`.

| | |
|---|---|
| **URL** | `https://<home-assistant>/api/friedafetch` (bzw. `http://homeassistant.local:8123/api/friedafetch`) |
| **Transport** | MCP Streamable HTTP, nur `POST` (kein SSE-Stream, `GET`/`DELETE` liefern `405`) |
| **Auth** | Home-Assistant-Token als `Authorization: Bearer <token>` |
| **Methoden** | `initialize`, `tools/list`, `tools/call` (Prompts/Ressourcen gibt es hier nicht) |

### Token einrichten

1. In Home Assistant unten links auf das **Profil** klicken → Reiter **Sicherheit**.
2. Unter **Langlebige Zugangstoken** auf **Token erstellen**, einen Namen (z. B. `Claude Frieda`) vergeben.
3. Den angezeigten Token **sofort kopieren** – er wird nur einmal angezeigt. Der Token gilt für den Benutzer, der
   ihn erstellt hat; es ist kein Admin-Konto nötig.

### Claude als Connector

**Claude.ai / Claude Desktop (Custom Connector):** Einstellungen → Connectors → **Custom Connector hinzufügen**,
als URL `https://<home-assistant>/api/friedafetch` eintragen. Claude.ai-Custom-Connectors verlangen nach aktuellem Stand
OAuth oder einen Endpunkt ohne Authentifizierung; einen festen Bearer-Header kann man dort nicht hinterlegen. Dafür
gibt es zwei Wege:

- **Claude Code / Claude Desktop (lokale MCP-Konfiguration):** HTTP-Server mit Header eintragen, z. B. in Claude
  Code:

  ```bash
  claude mcp add --transport http icloud https://<home-assistant>/api/friedafetch --header "Authorization: Bearer <token>"
  ```

  oder in `claude_desktop_config.json` bzw. `.mcp.json`:

  ```json
  {
    "mcpServers": {
      "icloud": {
        "type": "http",
        "url": "https://<home-assistant>/api/friedafetch",
        "headers": { "Authorization": "Bearer <token>" }
      }
    }
  }
  ```

- **Claude.ai Custom Connector mit OAuth:** Home Assistant von außen über HTTPS erreichbar machen (Nabu Casa oder
  eigener Reverse-Proxy) und einen OAuth-fähigen Proxy davor schalten, der den Bearer-Token ergänzt – oder stattdessen
  die Core-Integration `mcp_server` mit `/api/mcp` nutzen, die Claude.ai per OAuth direkt anbindet.

Home Assistant muss für Claude.ai aus dem Internet erreichbar sein (HTTPS); für Claude Code/Desktop auf demselben
Netz reicht die lokale Adresse.

### Andere MCP-Clients

Jeder Client, der Streamable HTTP mit eigenem `Authorization`-Header beherrscht, kann den Endpunkt nutzen. Ein
schneller Test mit `curl`:

```bash
curl -s -X POST https://<home-assistant>/api/friedafetch \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Mehrere iCloud-Konten

Die Integration wird pro Apple-ID einmal hinzugefügt. Das erste Konto behält die einfachen Tool-Namen
(`icloud_list_events`); jedes weitere Konto bekommt ein Suffix aus seiner **Kontobezeichnung** (Option) oder dem
lokalen Teil der Apple-ID, z. B. `icloud_list_events_arbeit`. Die LLM-APIs werden genauso registriert
(`friedafetch`, `friedafetch_arbeit`), das Panel zeigt eine Kontoauswahl. Jedes Konto hat eigene Optionen.

### Hinweise

- Tool-Fehler (nicht gefunden, Authentifizierung, Konflikt …) werden als MCP-Ergebnis mit `isError: true` und einem
  JSON-Objekt `{"error": …, "code": …}` zurückgegeben, nicht als JSON-RPC-Fehler.
- Tool-Annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`) werden mitgeliefert.
- Die Optionen der Integration (Nur-Lesen, Senden/Löschen erlauben, Tool-Gruppen) gelten auch für diesen Endpunkt.
- Die Routen können in Home Assistant nicht wieder entfernt werden; nach dem Entfernen des letzten Config-Entries
  antwortet der Endpunkt daher mit `404`, bis wieder ein Konto eingerichtet ist.

## Tools

| Tool                     | Beschreibung                                                                 |
|--------------------------|------------------------------------------------------------------------------|
| `icloud_list_calendars`  | Kalender mit IDs                                                             |
| `icloud_list_events`     | Termine in einem Zeitraum (Serien werden aufgelöst), optional Textfilter    |
| `icloud_get_event`       | Ein Termin inkl. Details                                                     |
| `icloud_create_event`    | Termin anlegen (ganztägig oder mit Uhrzeit, optional RRULE)                  |
| `icloud_update_event`    | Felder eines Termins ändern (Dauer bleibt erhalten, wenn nur `start` wechselt) |
| `icloud_delete_event`    | Termin löschen                                                               |
| `icloud_search_contacts` | Kontakte suchen (leere Suche = alphabetische Liste)                          |
| `icloud_get_contact`     | Kontakt per UID                                                              |
| `icloud_create_contact`  | Kontakt anlegen                                                              |
| `icloud_update_contact`  | Kontakt ändern (Listenfelder ersetzen die bestehende Liste)                  |
| `icloud_delete_contact`  | Kontakt löschen                                                              |
| `icloud_list_mailboxes`  | Postfächer/Ordner                                                            |
| `icloud_search_mail`     | Mails filtern (Absender, Betreff, Volltext, Zeitraum, ungelesen, markiert)   |
| `icloud_get_mail`        | Mail lesen (Text, optional HTML, Anhangsliste)                               |
| `icloud_send_mail`       | Mail senden oder beantworten (Zitat, In-Reply-To, Kopie in „Sent Messages“)  |
| `icloud_mark_mail`       | gelesen/ungelesen, markiert/unmarkiert – eine oder viele UIDs (`uids`) auf einmal |
| `icloud_move_mail`       | In anderen Ordner verschieben – eine oder viele UIDs mit einem IMAP-Befehl   |
| `icloud_delete_mail`     | In den Papierkorb (bzw. endgültig, wenn schon im Papierkorb) – eine oder viele UIDs |
| `icloud_approval_status` | Ergebnis einer Aktion, die eine Freigabe erforderte                          |
| `icloud_list_notes`      | Notizen auflisten/suchen                                                     |
| `icloud_get_note`        | Notiz lesen                                                                  |
| `icloud_create_note`     | Notiz anlegen                                                                |
| `icloud_update_note`     | Notiz ersetzen (erhält eine neue UID)                                        |
| `icloud_delete_note`     | Notiz löschen                                                                |
| `icloud_mailbox_stats`   | häufigste Absender/Domains, Ungelesen- und Newsletter-Anteil, Abdeckung durch Regeln, Regelvorschläge |
| `icloud_unsubscribe`     | Newsletter abbestellen (Ein-Klick per https oder Abmelde-Mail)              |
| `icloud_save_attachments`| Anhänge einer Mail in `<Ordner>/<Unterordner>/<JJJJ-MM>/` ablegen           |
| `icloud_find_free_time`  | freie Zeitfenster einer bestimmten Länge innerhalb der Arbeitszeit          |
| `icloud_upcoming_birthdays` | Geburtstage der Kontakte in den nächsten Tagen (mit Alter, falls bekannt) |
| `icloud_find_duplicate_contacts` | wahrscheinlich doppelte Kontakte (gleiche Mail, Nummer oder Name)   |

Die Mail-Tools `icloud_mark_mail`, `icloud_move_mail` und `icloud_delete_mail` akzeptieren neben `uid` auch eine Liste
`uids` (bis zu 500) und verarbeiten sie mit einem einzigen IMAP-Befehl – beim Aufräumen von Spam also ein Aufruf statt
einer pro Mail.

Zeitangaben sind ISO 8601; Zeiten ohne Zeitzone werden in der Home-Assistant-Zeitzone interpretiert. Ganztägige
Termine verwenden Datumsangaben (`YYYY-MM-DD`), das Enddatum ist dabei **inklusiv**.

## Panel

Die Integration legt in der Seitenleiste von Home Assistant den Eintrag **„Frieda“** an (nur für Admins; Deutsch
oder Englisch je nach HA-Sprache):

- **Überblick:** ob der MCP-Endpunkt aktiv ist (beide URLs zum Kopieren – für die lokale Adresse und, falls
  eingerichtet, die externe Adresse und Home Assistant Cloud –, Zahl der lesenden und schreibenden Tools, Token-Regel), welche MCP-Clients sich zuletzt verbunden haben (Name und Version aus dem MCP-Handshake), ob der
  MCP-Server von Home Assistant die LLM-API freigibt, und der Zustand von **Frieda Postfach** (läuft, installiert aber
  nicht verbunden, nicht installiert).
- **Nutzung:** Tool-Aufrufe heute, in 7 und 30 Tagen und insgesamt, getrennt nach lesend und schreibend, ein
  14-Tage-Diagramm, die häufigsten Tools, die Herkunft der Aufrufe (Frieda-Endpunkt, HA-MCP-Server, Assist-Agenten)
  und die Kontingente der letzten Stunde. Gespeichert werden nur Zähler, nie Argumente oder Ergebnisse.
- **Freigaben:** offene und entschiedene Anfragen (freigeben oder ablehnen mit einem Tipp, auch aus der Companion-App;
  bis das Ergebnis da ist, zeigt die Anfrage „Wird gesendet …“).
- **Änderungsprotokoll:** alles, was Frieda in iCloud verändert hat, als Tabelle nach Tagen gruppiert (z. B.
  „Mails verschoben · 3 Mails · → Archiv“), mit Suche, Filtern nach Bereich und Auslöser, Ergebnis-Umschalter und
  wählbaren Spalten; ein Klick auf die Zeile zeigt Fehler und Rohparameter, bei Läufen von Frieda Postfach auch die Mails
  mit Link zu ihrem Verlauf.

**Tabs und Widgets:** Drei Tabs halten das Panel übersichtlich – **Überblick** (mit der Nutzung), **Freigaben**
(sichtbar, wenn Freigaben eingeschaltet sind oder es Einträge gibt; der Tab zählt die offenen, damit sie auch von
den anderen Tabs aus auffallen) und **Änderungsprotokoll**. Im Überblick lassen sich die Karten mit **Anordnen** in
der Titelleiste am Griff ziehen (oder per Pfeil verschieben), zwischen voller und halber Breite umschalten und
ausblenden; Tabellen haben ein Menü **Spalten**. Seltene Aktionen wie „Protokoll leeren“ liegen in einem kleinen
⋮-Menü und fragen immer nach. Anordnung und zuletzt gewählter Tab werden pro Home-Assistant-Benutzer in Home Assistant
gespeichert, überstehen also Neustarts und gelten auf allen Geräten.

**Live:** Die Tabellen folgen Änderungen sofort (neue Einträge im Änderungsprotokoll, Freigaben, Ausführungen), ohne
die Seite neu zu laden; neue Zeilen leuchten kurz auf. Nach einem Update bietet das Panel ein Neuladen an, wenn es noch den
alten Code ausführt.

**Seiten:** Lange Tabellen zeigen 5, 10, 25, 50 oder alle Einträge pro Seite (pro Tabelle gemerkt); Suche und
Filter umfassen immer alle Einträge.

**Frieda UI:** Beide Panels nutzen eine gemeinsame Design-Bibliothek (`/friedafetch_static/ui.js`): Farben aus dem
Home-Assistant-Theme, Buttons, Chips, Tabellen, Menüs, Dialoge und Widgets. Frieda Postfach lädt sie von Frieda,
damit alle Module gleich aussehen und sich gleich bedienen. Sie sorgt auch für Barrierefreiheit: Der Fokus bleibt
beim Neuzeichnen an seiner Stelle, Dialoge halten den Fokus, Hinweise und Suchtreffer werden vorgelesen, Symbole
haben Namen für Screenreader, und farbiger Text hält in hellen und dunklen Themes den WCAG-AA-Kontrast ein.

Das Panel kommt ohne externe Bibliotheken aus und spricht über WebSocket-Befehle (`friedafetch/accounts`,
`friedafetch/overview`, `friedafetch/usage/reset`, `friedafetch/approvals/*`, `friedafetch/audit/*`) mit der
Integration.

## Anhänge und Abmelden

- **Anhänge:** `icloud_save_attachments` legt die Anhänge einer Mail unterhalb des Anhang-Ordners ab, nach Monat
  sortiert und als `<Datum>_<Absender>_<Datei>` benannt. Identische Dateien werden nicht doppelt gespeichert, kleine
  Bilder (Logos, Signaturen) übersprungen. Home Assistant muss den Ordner erlauben (Medienordner sind standardmäßig
  erlaubt, andere gehören in `allowlist_external_dirs`).
- **Abmelden:** `icloud_unsubscribe` nutzt den Header `List-Unsubscribe`: zuerst Ein-Klick per https (RFC 8058), sonst
  eine Abmelde-Mail (nur wenn Senden erlaubt ist; zählt zum Sende-Kontingent und braucht eine Freigabe, wenn Senden
  eine braucht). Links, die eine Webseite erfordern, bekommst du zum selbst Öffnen zurück.

## Erweiterungen

Frieda handelt nur, wenn ein KI-Client oder du sie aufrufst. Alles, was selbstständig läuft, steckt in Erweiterungen,
die sich an ein Frieda-Konto hängen, dessen Verbindung und Leitplanken nutzen und ihm ihre Tools hinzufügen:

- [**Frieda Postfach**](https://github.com/nadeo360/friedafetch-mail) (`friedafetch_mail`): Posteingangsregeln mit
  Push (IMAP IDLE), Belege per Regel, Tagesüberblick, Geburtstags-Sensor und die Regel-Tools.

## Sicherheit

- Nur ein **anwendungsspezifisches Passwort** wird verwendet; es ist jederzeit bei Apple widerrufbar und wird in
  Diagnosedaten geschwärzt. Verbindungen gehen ausschließlich per TLS an Apple-Endpunkte, es gibt keine Telemetrie.
- MCP-Endpunkt und Panel sind durch Home-Assistant-Tokens bzw. Admin-Rechte geschützt; Tool-Gruppen, Nur-Lesen,
  Senden und Löschen sind einzeln abschaltbar.
- **Leitplanken (Optionen → Sicherheit):** Stundenkontingente je Konto für Mail verschieben/löschen/markieren,
  gesendete Mails und gelöschte Termine/Kontakte/Notizen; eine Empfänger-Richtlinie beim Senden (beliebig, nur
  bekannte Kontakte oder eine Allowlist aus Adressen/Domains) mit Empfänger-Obergrenze und optionalem BCC-Verbot;
  geschützte Kalender und Postfächer, die KI-Clients nur lesen dürfen, sowie verborgene Postfächer, die gar nicht
  angeboten werden. Blockierte Aufrufe liefern `code: "blocked"`.
- **Änderungsprotokoll:** Jeder schreibende Tool-Aufruf und jeder Regellauf mit Treffern oder Fehlern (markiert als
  manuell oder automatisch) wird mit Zeit, Client, HA-Benutzer, Tool,
  gekürzten Parametern (ohne Mail-Inhalte) und Ergebnis in der Karte „Änderungsprotokoll“ des Panels protokolliert und als
  Ereignis `friedafetch_action` gefeuert; eine Automation kann dich so z. B. bei Massenlöschungen benachrichtigen.
- **Freigaben (Human-in-the-Loop, Optionen → Freigaben):** Senden, Löschen und Mail-Massenaktionen oberhalb einer
  Schwelle können geparkt statt ausgeführt werden. Home Assistant zeigt eine Benachrichtigung (optional ein Push mit
  Freigeben/Ablehnen-Buttons auf dem Handy), die Karte „Freigaben“ im Panel listet die Anfrage; nach Freigabe führt
  Home Assistant die Aktion aus und die KI liest das Ergebnis mit `icloud_approval_status`. Anfragen verfallen nach
  einstellbarer Zeit.
- **Verzögertes Senden (Optionen → Freigaben, standardmäßig aus):** E-Mails von Assistenten warten einige Sekunden
  (z. B. 60), bevor sie rausgehen. Bis dahin zeigt die Karte „Freigaben“ sie mit „Jetzt senden“ und „Abbrechen“, die
  Benachrichtigung hat einen Abbrechen-Button. Empfänger und Kontingente werden sofort und beim Senden noch einmal
  geprüft. Ohne Wirkung, wenn das Senden ohnehin freigegeben werden muss.
- **Dauerhafter Zustand:** Stunden-Kontingente, aktive Injection-Sperren und die Liste der Freigaben überstehen
  Neustarts und Neuladen; ein Neustart füllt also kein Kontingent auf und hebt keine Sperre auf. Anfragen, die bei
  einem Neustart noch offen waren, lassen sich danach nicht mehr ausführen: Sie werden als abgelaufen geschlossen
  (eine verzögerte Mail als abgebrochen, also nicht gesendet).
- **Endpunkt-Profile:** Neben `/api/friedafetch` gibt es `/api/friedafetch/readonly`, das nur Tools ohne jede
  Schreibwirkung ausliefert – der richtige Endpunkt für Experimente oder weniger vertrauenswürdige Agenten. Die Option
  „MCP-Endpunkt nur für Admin-Tokens“ weist Nicht-Admin-Tokens ab; Anfragen sind auf 1 MiB begrenzt.
- **Schutz vor Prompt-Injection:** Betreffzeilen, Mail-Texte, Notizen und Termintexte werden von unsichtbaren und
  Bidi-Steuerzeichen befreit, in den Tool-Antworten als Fremdinhalt gekennzeichnet und auf typische Injektionsmuster
  geprüft; Treffer werden mit `suspicious: true` und `warnings` markiert. Der LLM-Prompt weist das Modell an,
  Anweisungen aus solchen Inhalten nie zu befolgen.
- **Injection-Sperre (Optionen → Sicherheit, standardmäßig an):** Hat ein Tool solche markierten Inhalte geliefert,
  darf derselbe Aufrufer (Plattform und HA-Benutzer) eine Zeit lang (Standard 15 Minuten) nicht senden, löschen,
  abmelden oder löschende/verschiebende Regeln anlegen: Der Aufruf wird zur Freigabe geparkt oder, ohne aktivierte
  Freigaben, blockiert. Der Überblick im Panel zeigt aktive Sperren. Das verhindert den klassischen Angriff, bei dem
  eine Mail sagt „leite alles an … weiter“.
- **Regeln sind auch Massenaktionen:** Mit Frieda Postfach folgen Regeln, die löschen oder verschieben, sowie echte
  Läufe über das ganze Postfach den Freigaben („Löschen freigeben“, Massenschwelle). Unbeaufsichtigte Läufe (Takt,
  Push) und von einer KI angestoßene Läufe ändern höchstens 100 Mails (50 Löschungen) pro Lauf und zählen gegen das
  Stundenkontingent für Mail-Änderungen; der Rest folgt im nächsten Lauf. Die KI-Sortierung zählt gegen dasselbe
  Kontingent.
- **Lieferkette:** Jeder Commit läuft durch Tests, Ruff mit Bandit-Regeln, Bandit, CodeQL, pip-audit, hassfest und
  HACS-Validierung; GitHub Actions sind auf Commit-SHAs gepinnt, der `main`-Branch ist geschützt, OpenSSF Scorecard
  bewertet das Repository laufend, Dependabot und GitHub-Sicherheitswarnungen sind aktiv. Releases werden von GitHub
  Actions gebaut und mit signierter Build-Provenance (Sigstore) und einer CycloneDX-SBOM veröffentlicht; HACS
  installiert genau dieses signierte Paket (`gh attestation verify friedafetch.zip --repo nadeo360/friedafetch`). Details und Meldeweg für Sicherheitslücken: [SECURITY.md](https://github.com/nadeo360/friedafetch/blob/main/SECURITY.md).

Beispiel-Automation auf das Protokoll-Ereignis:

```yaml
automation:
  - alias: Warnung bei Massenlöschung durch KI
    triggers:
      - trigger: event
        event_type: friedafetch_action
    conditions:
      - "{{ trigger.event.data.action == 'delete' and (trigger.event.data.details.count | default(1)) > 10 }}"
    actions:
      - action: notify.mobile_app_iphone
        data:
          message: "{{ trigger.event.data.client }} hat {{ trigger.event.data.details.count }} Mails gelöscht"
```

## Technik

- **Kein Caching von Zugangsdaten außerhalb des Config-Entries**; das Passwort wird in Diagnosen geschwärzt.
- CalDAV/CardDAV sind direkt mit `aiohttp` umgesetzt (Principal-Discovery, `calendar-query`, `addressbook-multiget`,
  ETag-gesicherte Updates). Kontakte werden lokal gecacht und per CTag/ETag inkrementell synchronisiert.
- Serientermine werden mit `python-dateutil` aufgelöst (RRULE, EXDATE, RDATE, verschobene Einzeltermine).
- vCards werden mit einem eigenen, verlustfreien Parser bearbeitet: unbekannte Felder (Foto, Apple-Erweiterungen)
  bleiben beim Ändern erhalten.
- IMAP über `aioimaplib` (eine serialisierte Verbindung mit automatischem Reconnect), SMTP über `aiosmtplib`
  (STARTTLS, Port 587).
- Der eigene MCP-Endpunkt (`mcp_http.py`) nutzt das `mcp`-SDK in der Version, die auch die Core-Integration
  `mcp_server` verwendet, und baut die Tool-Schemas mit `probatio.to_openapi` aus den `llm.Tool`-Parametern.
- Abhängigkeiten sind auf die Versionen gepinnt, die Home Assistant 2026.10 selbst verwendet (`icalendar`, `aioimaplib`,
  `mcp`, `anyio`).

## Entwicklung

Wie du Fehler meldest, Ideen einbringst und Pull Requests schickst: [CONTRIBUTING.md](https://github.com/nadeo360/friedafetch/blob/main/CONTRIBUTING.md).

Die Architektur von Frieda und Frieda Postfach beschreibt das arc42-Dokument [docs/architecture.de.md](https://github.com/nadeo360/friedafetch/blob/main/docs/architecture.de.md).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_dev.txt
pytest
ruff check . && ruff format .
```

Home Assistant 2026.10 benötigt Python ≥ 3.14.2.

Die Typprüfung ist `basedpyright` (requirements/types.txt); Befunde von vor ihrer Einführung stehen in
`.basedpyright/baseline.json`, nur neue lassen sie scheitern.

### Releases

`scripts/release.py VERSION --notes NOTES.md` veröffentlicht aus einem sauberen `dev`: Es hält an, wenn `origin/main`
Commits hat, die `dev` fehlen, setzt die Version im Manifest, führt ruff und die Tests aus, schiebt `main` per
Fast-Forward nach und pusht, wartet, bis jeder CI-Lauf dieses Commits bestanden hat, legt das GitHub-Release mit den
Notizen an (Deutsch, `---`, Englisch) und prüft danach das Zip, das der Release-Workflow anhängt – Prüfsumme, Version
und jede Datei gegen den getaggten Quellstand. `--dry-run` prüft und testet nur; `--draft` gibt ein Gerüst für die
Notizen aus den Commits seit dem letzten Release aus.
Ein CI-Lauf, den GitHub fünf Minuten nach dem Ende seines letzten Jobs noch als laufend zeigt, zählt nach seinen
Jobs (GitHub schließt einen Lauf manchmal nie ab). Bricht das Skript beim Warten trotzdem ab, setzt `--resume`
dieselbe Version später fort: Es prüft, dass es den Tag noch nicht gibt und `main` der gepushte Commit ist, wartet
erneut auf die CI, legt das Release an und prüft das Zip.

### Grafiken

`assets/*.svg` sind die Quellen; `scripts/build_icons.py` rendert alle PNG-Varianten (Icon, @2x, helles/dunkles Logo)
nach `assets/` und in den Ordner `custom_components/friedafetch/brand/`, aus dem Home Assistant (ab 2026.3) und HACS
das Icon der Integration direkt laden. `--check` prüft in der CI, ob die Dateien aktuell sind.

## Hinweis zum Einsatz von KI

Diese Integration ist mit erheblicher Unterstützung eines KI-Programmierassistenten (Claude von Anthropic) entstanden,
auf Basis der Anforderungen und Entscheidungen des Maintainers. Jede Änderung ist durch die automatisierte Test-Suite
und die oben beschriebenen Sicherheitsprüfungen abgedeckt; alle Releases wurden vom Maintainer gegen ein echtes
iCloud-Konto geprüft. Fehler und Ideen bitte als GitHub-Issue melden – sie werden von einem Menschen gelesen.

## Rechtliche Hinweise

Apple, iCloud, iPhone, iPad, Mac und macOS sind Marken von Apple Inc.; Home Assistant ist eine Marke der Open Home
Foundation; „Model Context Protocol“ und „Claude“ sind Marken von Anthropic, PBC. **Dies ist ein unabhängiges
Community-Projekt und steht in keiner Verbindung zu Apple, der Open Home Foundation, Nabu Casa, Anthropic oder HACS
und wird von ihnen weder unterstützt noch empfohlen.** Die Nutzung von iCloud über diese Integration unterliegt den
iCloud-Nutzungsbedingungen von Apple; für deren Einhaltung bist du verantwortlich. Die Software wird ohne Gewähr
bereitgestellt, liest und verändert in deinem Auftrag persönliche Daten und gibt sie an die von dir verbundenen
KI-Clients weiter. Vollständige Hinweise, Drittlizenzen (u. a. das unter GPL-3.0 stehende `aioimaplib`) und
Haftungsausschluss: [NOTICE.md](https://github.com/nadeo360/friedafetch/blob/main/NOTICE.md).

## Lizenz

MIT – siehe [LICENSE](https://github.com/nadeo360/friedafetch/blob/main/LICENSE) und [NOTICE.md](https://github.com/nadeo360/friedafetch/blob/main/NOTICE.md).
