# iCloud MCP für Home Assistant

Eine Home-Assistant-Integration (HACS), die **Apple iCloud** per anwendungsspezifischem Passwort anbindet und
**Kalender, Kontakte, E-Mails und Notizen** als Werkzeuge (Tools) für LLMs bereitstellt. Die Tools werden als
Home-Assistant-**LLM-API** registriert und damit automatisch über die **MCP-Server-Integration** von Home Assistant
(Model Context Protocol) an MCP-Clients wie Claude, ChatGPT-Connectors oder lokale Agenten ausgeliefert. Sie stehen
außerdem jedem Home-Assistant-Sprachassistenten (Assist, Google Generative AI, OpenAI, Ollama …) zur Verfügung, der
diese LLM-API aktiviert hat.

## Funktionsumfang

| Bereich   | Protokoll          | Lesen                                   | Schreiben                                                     |
|-----------|--------------------|-----------------------------------------|---------------------------------------------------------------|
| Kalender  | CalDAV             | Kalender auflisten, Termine (inkl. Serien) suchen/lesen | Termin anlegen, ändern (inkl. RRULE), löschen       |
| Kontakte  | CardDAV            | Kontakte suchen (Name, Mail, Telefon, Firma …), lesen | Kontakt anlegen, ändern, löschen                    |
| E-Mail    | IMAP + SMTP        | Postfächer, Suche/Filter, Mail lesen (Text, Anhänge-Liste) | Senden/Antworten, gelesen/markiert, verschieben, Papierkorb |
| Notizen   | IMAP-Ordner `Notes`| Notizen auflisten/suchen/lesen          | Notiz anlegen, ändern, löschen                                |

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
- Die Home-Assistant-Integration **„Model Context Protocol Server“** (`mcp_server`), um die Tools per MCP nach außen zu geben.

## Installation

### HACS (empfohlen)

1. HACS → Integrationen → ⋮ → **Benutzerdefinierte Repositories** → URL dieses Repositories, Kategorie *Integration*.
2. „iCloud MCP“ installieren und Home Assistant neu starten.

### Manuell

Ordner `custom_components/icloud_mcp` in das `custom_components`-Verzeichnis der Home-Assistant-Konfiguration kopieren
und Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „iCloud MCP“**.
2. Apple-ID und anwendungsspezifisches Passwort eingeben. Die Zugangsdaten werden gegen CalDAV geprüft (Pflicht) und
   gegen IMAP (optional – schlägt IMAP fehl, werden Mail- und Notiz-Tools zunächst deaktiviert).
3. **MCP-Server verbinden:** Die Core-Integration **„Model Context Protocol Server“** (`mcp_server`) hinzufügen,
   falls noch nicht vorhanden, und dort unter **Konfigurieren** entweder „alle LLM-APIs“ aktivieren oder in der Liste
   **„iCloud (Kalender, Kontakte, Mail, Notizen)“** zusätzlich zu *Assist* auswählen. Danach sieht jeder verbundene
   MCP-Client die `icloud_*`-Tools.

   > **Hinweis zu `mcp_server_http_transport` (hass-mcp-server):** Diese HACS-Integration bringt einen eigenen,
   > fest verdrahteten Tool-Satz mit und reicht Home-Assistant-LLM-APIs **nicht** durch. Die iCloud-Tools erscheinen
   > dort also nicht. Beide Server können parallel laufen; laut README von hass-mcp-server verwendet dieser dann den
   > Pfad `/api/mcp_http`, während die Core-Integration `/api/mcp` belegt.
4. Optional für Sprachassistenten: In der jeweiligen Conversation-Integration (z. B. Google Generative AI) unter
   „Steuerung von Home Assistant“ die iCloud-LLM-API aktivieren.

### Optionen (Konfigurieren)

| Option                       | Wirkung                                                                 |
|------------------------------|-------------------------------------------------------------------------|
| Kalender-/Kontakt-/E-Mail-/Notiz-Tools | Tool-Gruppen einzeln ein- oder ausblenden                      |
| Nur-Lesen-Modus              | Blendet sämtliche Erstellen/Ändern/Löschen/Senden-Tools aus             |
| Senden von E-Mails erlauben  | Versteckt `icloud_send_mail`, wenn deaktiviert                          |
| Löschen erlauben             | Versteckt alle `icloud_delete_*`-Tools, wenn deaktiviert                |
| Standard-Maximalanzahl       | Standard-Limit für Listen (1–200)                                       |
| Absenderadresse              | `From:` für ausgehende Mails (Standard: Apple-ID; muss ein iCloud-Alias sein) |

Alle Tools tragen MCP-Annotations (`readOnlyHint`, `destructiveHint`), sodass Clients im „nur lesen“-Modus die
schreibenden Tools automatisch weglassen.

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
| `icloud_mark_mail`       | gelesen/ungelesen, markiert/unmarkiert                                        |
| `icloud_move_mail`       | In anderen Ordner verschieben                                                 |
| `icloud_delete_mail`     | In den Papierkorb (bzw. endgültig, wenn schon im Papierkorb)                 |
| `icloud_list_notes`      | Notizen auflisten/suchen                                                     |
| `icloud_get_note`        | Notiz lesen                                                                  |
| `icloud_create_note`     | Notiz anlegen                                                                |
| `icloud_update_note`     | Notiz ersetzen (erhält eine neue UID)                                        |
| `icloud_delete_note`     | Notiz löschen                                                                |

Zeitangaben sind ISO 8601; Zeiten ohne Zeitzone werden in der Home-Assistant-Zeitzone interpretiert. Ganztägige
Termine verwenden Datumsangaben (`YYYY-MM-DD`), das Enddatum ist dabei **inklusiv**.

## Technik

- **Kein Caching von Zugangsdaten außerhalb des Config-Entries**; das Passwort wird in Diagnosen geschwärzt.
- CalDAV/CardDAV sind direkt mit `aiohttp` umgesetzt (Principal-Discovery, `calendar-query`, `addressbook-multiget`,
  ETag-gesicherte Updates). Kontakte werden lokal gecacht und per CTag/ETag inkrementell synchronisiert.
- Serientermine werden mit `python-dateutil` aufgelöst (RRULE, EXDATE, RDATE, verschobene Einzeltermine).
- vCards werden mit einem eigenen, verlustfreien Parser bearbeitet: unbekannte Felder (Foto, Apple-Erweiterungen)
  bleiben beim Ändern erhalten.
- IMAP über `aioimaplib` (eine serialisierte Verbindung mit automatischem Reconnect), SMTP über `aiosmtplib`
  (STARTTLS, Port 587).
- Abhängigkeiten sind auf die Versionen gepinnt, die Home Assistant 2026.10 selbst verwendet (`icalendar`, `aioimaplib`).

## Entwicklung

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_dev.txt
pytest
ruff check . && ruff format .
```

Home Assistant 2026.10 benötigt Python ≥ 3.14.2.

## Lizenz

MIT
