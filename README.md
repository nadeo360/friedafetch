# iCloud MCP für Home Assistant

Eine Home-Assistant-Integration (HACS), die **Apple iCloud** per anwendungsspezifischem Passwort anbindet und
**Kalender, Kontakte, E-Mails und Notizen** als Werkzeuge (Tools) für LLMs bereitstellt. Die Tools werden als
Home-Assistant-**LLM-API** registriert und über einen **eigenen MCP-Endpunkt** (`/api/icloud_mcp`, Streamable HTTP)
sowie optional über die **MCP-Server-Integration** von Home Assistant (Model Context Protocol) an MCP-Clients wie
Claude, ChatGPT-Connectors oder lokale Agenten ausgeliefert. Sie stehen außerdem jedem Home-Assistant-Sprachassistenten
(Assist, Google Generative AI, OpenAI, Ollama …) zur Verfügung, der diese LLM-API aktiviert hat.

## Funktionsumfang

| Bereich   | Protokoll          | Lesen                                   | Schreiben                                                     |
|-----------|--------------------|-----------------------------------------|---------------------------------------------------------------|
| Kalender  | CalDAV             | Kalender auflisten, Termine (inkl. Serien) suchen/lesen | Termin anlegen, ändern (inkl. RRULE), löschen       |
| Kontakte  | CardDAV            | Kontakte suchen (Name, Mail, Telefon, Firma …), lesen | Kontakt anlegen, ändern, löschen                    |
| E-Mail    | IMAP + SMTP        | Postfächer, Suche/Filter, Mail lesen (Text, Anhänge-Liste) | Senden/Antworten, gelesen/markiert, verschieben, Papierkorb |
| Notizen   | IMAP-Ordner `Notes`| Notizen auflisten/suchen/lesen          | Notiz anlegen, ändern, löschen                                |
| Regeln    | HA-Storage + IMAP  | Posteingangsregeln auflisten            | Regeln anlegen/ändern/löschen, automatisch oder auf Abruf ausführen |

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
2. „iCloud MCP“ installieren und Home Assistant neu starten.

### Manuell

Ordner `custom_components/icloud_mcp` in das `custom_components`-Verzeichnis der Home-Assistant-Konfiguration kopieren
und Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „iCloud MCP“**.
2. Apple-ID und anwendungsspezifisches Passwort eingeben. Die Zugangsdaten werden gegen CalDAV geprüft (Pflicht) und
   gegen IMAP (optional – schlägt IMAP fehl, werden Mail- und Notiz-Tools zunächst deaktiviert).
3. **MCP-Client verbinden:** Entweder den [eigenen MCP-Endpunkt](#eigener-mcp-endpunkt) `/api/icloud_mcp` verwenden
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

| Option                       | Wirkung                                                                 |
|------------------------------|-------------------------------------------------------------------------|
| Kalender-/Kontakt-/E-Mail-/Notiz-Tools | Tool-Gruppen einzeln ein- oder ausblenden                      |
| Nur-Lesen-Modus              | Blendet sämtliche Erstellen/Ändern/Löschen/Senden-Tools aus             |
| Senden von E-Mails erlauben  | Versteckt `icloud_send_mail`, wenn deaktiviert                          |
| Löschen erlauben             | Versteckt alle `icloud_delete_*`-Tools, wenn deaktiviert                |
| Standard-Maximalanzahl       | Standard-Limit für Listen (1–200)                                       |
| Absenderadresse              | `From:` für ausgehende Mails (Standard: Apple-ID; muss ein iCloud-Alias sein) |
| Regeln automatisch anwenden  | Posteingangsregeln periodisch auf neue Mails anwenden (Standard: an)        |
| Intervall für Regeln         | Minuten zwischen zwei automatischen Läufen (Standard 5, 1–240)              |

Alle Tools tragen MCP-Annotations (`readOnlyHint`, `destructiveHint`), sodass Clients im „nur lesen“-Modus die
schreibenden Tools automatisch weglassen.

## Eigener MCP-Endpunkt

Die Integration registriert einen eigenen **MCP-Endpunkt (Streamable HTTP)**, der die `icloud_*`-Tools direkt
ausliefert – unabhängig von der Core-Integration `mcp_server` und ohne Umweg über eine LLM-API-Auswahl. Der Endpunkt
ist zustandslos (jede Anfrage enthält genau eine JSON-RPC-Nachricht) und ist aktiv, sobald mindestens ein
iCloud-Config-Entry geladen ist; ohne geladenen Entry antwortet er mit `404`.

| | |
|---|---|
| **URL** | `https://<home-assistant>/api/icloud_mcp` (bzw. `http://homeassistant.local:8123/api/icloud_mcp`) |
| **Transport** | MCP Streamable HTTP, nur `POST` (kein SSE-Stream, `GET`/`DELETE` liefern `405`) |
| **Auth** | Home-Assistant-Token als `Authorization: Bearer <token>` |
| **Methoden** | `initialize`, `tools/list`, `tools/call` (Prompts/Ressourcen gibt es hier nicht) |

### Token einrichten

1. In Home Assistant unten links auf das **Profil** klicken → Reiter **Sicherheit**.
2. Unter **Langlebige Zugangstoken** auf **Token erstellen**, einen Namen (z. B. `Claude iCloud MCP`) vergeben.
3. Den angezeigten Token **sofort kopieren** – er wird nur einmal angezeigt. Der Token gilt für den Benutzer, der
   ihn erstellt hat; es ist kein Admin-Konto nötig.

### Claude als Connector

**Claude.ai / Claude Desktop (Custom Connector):** Einstellungen → Connectors → **Custom Connector hinzufügen**,
als URL `https://<home-assistant>/api/icloud_mcp` eintragen. Claude.ai-Custom-Connectors verlangen nach aktuellem Stand
OAuth oder einen Endpunkt ohne Authentifizierung; einen festen Bearer-Header kann man dort nicht hinterlegen. Dafür
gibt es zwei Wege:

- **Claude Code / Claude Desktop (lokale MCP-Konfiguration):** HTTP-Server mit Header eintragen, z. B. in Claude
  Code:

  ```bash
  claude mcp add --transport http icloud https://<home-assistant>/api/icloud_mcp --header "Authorization: Bearer <token>"
  ```

  oder in `claude_desktop_config.json` bzw. `.mcp.json`:

  ```json
  {
    "mcpServers": {
      "icloud": {
        "type": "http",
        "url": "https://<home-assistant>/api/icloud_mcp",
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
curl -s -X POST https://<home-assistant>/api/icloud_mcp \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Mehrere iCloud-Konten

Sind mehrere iCloud-Konten eingerichtet, werden die Tools aller Konten auf demselben Endpunkt zusammengeführt. Das
zuerst angelegte Konto behält die normalen Tool-Namen (`icloud_list_events`), jedes weitere Konto bekommt ein Suffix
aus seiner Entry-ID (`icloud_list_events_1a2b3c4d`); die Tool-Beschreibung nennt die zugehörige Apple-ID.

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
| `icloud_list_rules`      | Posteingangsregeln inkl. Trefferzähler und letztem Lauf                      |
| `icloud_create_rule`     | Regel anlegen (Bedingungen + Aktionen)                                        |
| `icloud_update_rule`     | Regel ändern, aktivieren/deaktivieren, umsortieren                            |
| `icloud_delete_rule`     | Regel löschen                                                                |
| `icloud_run_rules`       | Regeln jetzt anwenden (`scope` all/new, `dry_run` zeigt nur an)              |
| `icloud_list_notes`      | Notizen auflisten/suchen                                                     |
| `icloud_get_note`        | Notiz lesen                                                                  |
| `icloud_create_note`     | Notiz anlegen                                                                |
| `icloud_update_note`     | Notiz ersetzen (erhält eine neue UID)                                        |
| `icloud_delete_note`     | Notiz löschen                                                                |

Die Mail-Tools `icloud_mark_mail`, `icloud_move_mail` und `icloud_delete_mail` akzeptieren neben `uid` auch eine Liste
`uids` (bis zu 500) und verarbeiten sie mit einem einzigen IMAP-Befehl – beim Aufräumen von Spam also ein Aufruf statt
einer pro Mail.

Zeitangaben sind ISO 8601; Zeiten ohne Zeitzone werden in der Home-Assistant-Zeitzone interpretiert. Ganztägige
Termine verwenden Datumsangaben (`YYYY-MM-DD`), das Enddatum ist dabei **inklusiv**.

## Posteingangsregeln

iCloud bietet keine Schnittstelle für seine serverseitigen Mail-Regeln. Die Integration führt deshalb **eigene
Regeln** aus, die in Home Assistant gespeichert werden (`.storage/icloud_mcp.rules.<entry>`):

- **Bedingungen** auf `from`, `to`, `cc`, `subject` oder `any` mit `contains`, `equals`, `starts_with`, `ends_with`,
  `domain` (Absender-Domain inkl. Subdomains) oder `regex`; Verknüpfung `all` (Standard) oder `any`.
- **Aktionen:** `move_to` (Ordner), `mark_seen`, `flag`, `delete` (Papierkorb) und `stop` (Standard: weitere Regeln
  für diese Mail überspringen). Löschen über Regeln ist nur erlaubt, wenn die Option „Löschen erlauben“ aktiv ist.
- **Automatik:** Standardmäßig alle 5 Minuten, nur für **neue** Mails seit dem letzten Lauf. Beim allerersten Lauf wird
  nur die Ausgangsbasis gesetzt; Bestandsmails werden nicht angefasst. Dafür gibt es `icloud_run_rules` mit
  `scope: "all"` (prüft die neuesten bis zu 2000 Mails) und `dry_run: true` zum Vorschauen.
- **Ausführung:** Treffer werden pro Aktion gesammelt und mit den Batch-Befehlen in wenigen IMAP-Kommandos erledigt.

Beispiel-Regel (als Tool-Aufruf):

```json
{
  "name": "Newsletter archivieren",
  "conditions": [{"field": "from", "op": "domain", "value": "newsletter.example.com"}],
  "actions": {"move_to": "Archive", "mark_seen": true}
}
```

Die Regeln greifen nur, solange Home Assistant läuft; auf dem iPhone ohne HA-Verbindung passiert nichts.

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

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_dev.txt
pytest
ruff check . && ruff format .
```

Home Assistant 2026.10 benötigt Python ≥ 3.14.2.

## Lizenz

MIT
