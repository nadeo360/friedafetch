<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img src="assets/logo.svg" alt="Frieda" width="720">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/nadeo360/friedafetch/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/validate.yml"><img alt="hassfest & HACS" src="https://github.com/nadeo360/friedafetch/actions/workflows/validate.yml/badge.svg"></a>
  <a href="https://github.com/nadeo360/friedafetch/security/code-scanning"><img alt="CodeQL" src="https://img.shields.io/badge/CodeQL-default%20setup-2ea44f"></a>
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/security.yml"><img alt="Dependency audit" src="https://github.com/nadeo360/friedafetch/actions/workflows/security.yml/badge.svg"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/nadeo360/friedafetch"><img alt="OpenSSF Scorecard" src="https://api.scorecard.dev/projects/github.com/nadeo360/friedafetch/badge"></a>
  <a href="https://github.com/nadeo360/friedafetch/releases"><img alt="Release" src="https://img.shields.io/github/v/release/nadeo360/friedafetch?display_name=tag"></a>
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

<p align="center"><b>English</b> · <a href="README.de.md">Deutsch</a></p>

# Frieda – MCP connector for iCloud

**Frieda** (technical name `friedafetch`) is a Home Assistant integration (HACS) that connects **Apple iCloud** with an app-specific password and exposes
**calendars, contacts, e-mail and notes** as tools for LLMs. The tools are registered as a Home Assistant
**LLM API**, so they are available to every conversation agent that enables the API (Assist, Google Generative AI,
OpenAI, Ollama …) and to any **MCP client** (Claude, ChatGPT connectors, local agents) through Home Assistant's
MCP Server integration or the integration's own MCP endpoint. Inbox rules can be managed in a sidebar panel.
The project is named after the maintainer's dog Frieda, who looks out of the cloud in the logo.

## Features

| Area      | Protocol            | Read                                                        | Write                                                            |
|-----------|---------------------|-------------------------------------------------------------|------------------------------------------------------------------|
| Calendar  | CalDAV              | list calendars, search/read events (recurrences expanded)   | create, update (incl. RRULE) and delete events                   |
| Contacts  | CardDAV             | search (name, mail, phone, company …) and read contacts     | create, update and delete contacts                               |
| E-mail    | IMAP + SMTP         | mailboxes, search/filter, read mail (text, attachment list) | send/reply, mark read/flagged, move, trash – many uids at once   |
| Notes     | IMAP folder `Notes` | list/search/read notes                                      | create, update and delete notes                                  |
| Rules     | HA storage + IMAP   | list inbox rules                                            | create/update/delete rules, run them automatically or on demand  |

### Important note on Notes

Apple offers **no interface** for modern iCloud Notes (CloudKit, the default since iOS 9 / "upgraded notes") that
works with an app-specific password. The integration can therefore only read and write notes stored in the
**IMAP folder `Notes`** of the iCloud mail account (classic IMAP notes). If that folder does not exist, the note tools
say so. The other areas use official, stable protocols (CalDAV, CardDAV, IMAP, SMTP) and are fully usable.

## Requirements

- Home Assistant **2026.10** or newer (the integration uses the current `llm.Tool` API with `probatio` schemas; older
  2025 releases work through the built-in `voluptuous` fallback but are untested).
- An Apple ID with **two-factor authentication** and an **app-specific password**
  (appleid.apple.com → Sign-In and Security → App-Specific Passwords).
- **iCloud Mail** must be enabled for the Apple ID if you want e-mail and notes.
- Optional: Home Assistant's **Model Context Protocol Server** integration (`mcp_server`) if you prefer it over the
  built-in endpoint.

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ → **Custom repositories** → URL of this repository, category *Integration*.
2. Install "Frieda" and restart Home Assistant.

### Manual

Copy `custom_components/friedafetch` into the `custom_components` directory of your Home Assistant configuration and
restart Home Assistant.


### Upgrading from “iCloud MCP” (versions up to 1.0.x)

The project was renamed to Frieda with version 1.1.0; the integration domain changed from `icloud_mcp` to
`friedafetch`. Remove the old integration (Settings → Devices & services → iCloud MCP → Delete), update the HACS
custom repository to `https://github.com/nadeo360/friedafetch`, install Frieda and add it again with the Apple ID
and app-specific password. Rules and options are not migrated; MCP clients need the new endpoint
`/api/friedafetch`. The tool names (`icloud_*`) are unchanged.

## Setup

1. **Settings → Devices & services → Add integration → "Frieda"**.
2. Enter the Apple ID and the app-specific password. Credentials are validated against CalDAV (mandatory) and IMAP
   (optional – if IMAP fails, the mail and note tools start disabled).
3. Connect an MCP client, either via the **built-in endpoint** (see below) or via the core
   **Model Context Protocol Server** integration: there, under *Configure*, enable "all LLM APIs" or select
   **"iCloud (Calendar, Contacts, Mail, Notes)"** in addition to *Assist*.
4. Optional for voice assistants: enable the iCloud LLM API in the conversation integration (e.g. Google Generative
   AI) under "Control Home Assistant".

> **Note on `mcp_server_http_transport` (hass-mcp-server):** that HACS integration ships its own fixed tool set and
> does **not** forward Home Assistant LLM APIs, so the iCloud tools do not appear there. Use the built-in endpoint
> or the core MCP Server integration instead; both can run side by side.

### Options (Configure)

The options dialog has four sections: **Tools and account**, **Security and guard rails**, **Approvals** and **Inbox rules**.

| Option                                   | Effect                                                                   |
|------------------------------------------|--------------------------------------------------------------------------|
| Calendar / Contact / E-mail / Note tools | show or hide tool groups                                                 |
| Read-only mode                           | hides every create/update/delete/send tool                               |
| Allow sending e-mails                    | hides `icloud_send_mail` when disabled                                   |
| Allow deleting                           | hides all `icloud_delete_*` tools (except rule deletion) when disabled   |
| Default maximum number of results        | default list limit (1–200)                                               |
| Sender address                           | `From:` for outgoing mail (default: Apple ID; must be an iCloud alias)   |
| Apply inbox rules automatically          | run rules periodically on new mail (default: on)                         |
| Interval for automatic rules             | minutes between automatic runs (default 5, 1–240)                        |
| Account label                            | short name used as tool suffix when several accounts are configured      |
| Security section                         | quotas, recipient policy, protected calendars/mailboxes, hidden mailboxes (see Security) |

All tools carry MCP annotations (`readOnlyHint`, `destructiveHint`) so that clients in read-only mode can drop the
writing tools automatically.

Capabilities you switch off are not hidden silently: the LLM prompt (and the `instructions` of the built-in MCP
endpoint) lists what the administrator disabled, so the assistant can tell the user *why* it cannot send or delete
and where to enable it (Settings → Devices & services → Frieda → Configure). Likewise, active approvals are
announced so that an `approval_required` result is explained as "waiting for approval", not as an error.

## Built-in MCP endpoint

The integration serves its tools directly at **`POST /api/friedafetch`** (MCP Streamable HTTP, stateless) and
authenticates with Home Assistant access tokens – no additional integration required.

1. In Home Assistant open your profile → **Security → Long-lived access tokens → Create token**.
2. Configure the client with the URL `https://<your-home-assistant>/api/friedafetch` and the header
   `Authorization: Bearer <token>`.

For Claude Code (`~/.claude.json`) or Claude Desktop (`claude_desktop_config.json`) this looks like:

```json
{
  "mcpServers": {
    "icloud": {
      "type": "http",
      "url": "https://<your-home-assistant>/api/friedafetch",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

`GET /api/friedafetch` answers with a short status (name, version, tool count). Server-initiated streams and
sessions are not needed; every POST is handled on its own.

### Several iCloud accounts

Add the integration once per Apple ID. The first account keeps the plain tool names (`icloud_list_events`); every
further account gets a suffix derived from its **account label** (option) or the local part of its Apple ID, for
example `icloud_list_events_work`. The LLM APIs are registered the same way (`friedafetch`, `friedafetch_work`), and
the rules panel offers an account selector. Each account has its own rules and options.

## Tools

| Tool                     | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| `icloud_list_calendars`  | calendars with ids                                                          |
| `icloud_list_events`     | events in a time range (recurrences expanded), optional text filter        |
| `icloud_get_event`       | one event with details                                                      |
| `icloud_create_event`    | create an event (all-day or timed, optional RRULE)                          |
| `icloud_update_event`    | change fields of an event (duration kept when only `start` changes)        |
| `icloud_delete_event`    | delete an event                                                             |
| `icloud_search_contacts` | search contacts (empty query = alphabetical list)                           |
| `icloud_get_contact`     | contact by uid                                                              |
| `icloud_create_contact`  | create a contact                                                            |
| `icloud_update_contact`  | change a contact (list fields replace the existing list)                    |
| `icloud_delete_contact`  | delete a contact                                                            |
| `icloud_list_mailboxes`  | mailboxes/folders                                                           |
| `icloud_search_mail`     | filter mail (sender, subject, full text, date range, unseen, flagged)       |
| `icloud_get_mail`        | read a mail (text, optional HTML, attachment list, optional raw headers)    |
| `icloud_send_mail`       | send or reply (quote, In-Reply-To, copy in the sent folder)                 |
| `icloud_mark_mail`       | read/unread, flagged/unflagged – one or many uids (`uids`) at once          |
| `icloud_move_mail`       | move to another folder – one or many uids with a single IMAP command        |
| `icloud_delete_mail`     | move to trash (or delete permanently when already in trash) – one or many uids |
| `icloud_list_rules`      | inbox rules with hit counters and the last run                              |
| `icloud_create_rule`     | create a rule (conditions + actions)                                        |
| `icloud_update_rule`     | change, enable/disable or reorder a rule                                    |
| `icloud_delete_rule`     | delete a rule                                                               |
| `icloud_run_rules`       | apply rules now (`scope` all/new, `dry_run` only reports)                   |
| `icloud_approval_status` | outcome of an action that required human approval                           |
| `icloud_list_notes`      | list/search notes                                                           |
| `icloud_get_note`        | read a note                                                                 |
| `icloud_create_note`     | create a note                                                               |
| `icloud_update_note`     | replace a note (it gets a new uid)                                          |
| `icloud_delete_note`     | delete a note                                                               |

Times are ISO 8601; naive times are interpreted in the Home Assistant time zone. All-day events use dates
(`YYYY-MM-DD`) with an **inclusive** end date. The mail tools `icloud_mark_mail`, `icloud_move_mail` and
`icloud_delete_mail` accept a `uids` list (up to 500) and process it with a single IMAP command, so cleaning up spam
is one call instead of one per message.

## Inbox rules

iCloud offers no API for its server-side mail rules, so the integration runs **its own rules**, stored in Home
Assistant (`.storage/friedafetch.rules.<entry>`):

- **Conditions** on `from`, `to`, `cc`, `subject` or `any` with `contains`, `equals`, `starts_with`, `ends_with`,
  `domain` (sender domain incl. subdomains) or `regex`; combined with `all` (default) or `any`.
- **Actions:** `move_to` (folder), `mark_seen`, `flag`, `delete` (trash) and `stop` (default: skip further rules for
  this message). Deleting through rules requires the "Allow deleting" option.
- **Automation:** every 5 minutes by default, only for **new** mail since the last run. The very first run only sets
  the baseline; existing mail is left alone. Use `icloud_run_rules` with `scope: "all"` (newest 2000 messages) and
  `dry_run: true` for a preview.
- **Execution:** matches are grouped per action and executed with the batch commands in a few IMAP round trips.

Example rule (as a tool call):

```json
{
  "name": "Archive newsletters",
  "conditions": [{"field": "from", "op": "domain", "value": "newsletter.example.com"}],
  "actions": {"move_to": "Archive", "mark_seen": true}
}
```

Rules only run while Home Assistant is running; nothing happens on the phone without a connection to HA.

### Management panel

The integration adds **"Frieda"** to the Home Assistant sidebar (admins only, German/English following the HA
language). Rules can be created, edited, reordered, enabled/disabled and deleted; dry runs and real runs show a
per-message report. Rules are listed compactly and expand on click (or all at once); a new rule opens its editor
in place and scrolls it into view. The "Runs" card lists every manual and automatic run (consecutive automatic runs
without hits are merged), and the "Runs" and "Activity" tables can be filtered per column (text, selection, or
numbers such as `>0`). Accounts are shown as cards with rule counts, hit totals, automation state and last run; one click switches between them, and rules can be copied to another account. The panel is optimised for phones (stacked cards instead of tables, large touch targets, approvals with one tap in
the Home Assistant companion app), has no external dependencies and talks to the integration via WebSocket commands
(`friedafetch/rules/*`, `friedafetch/approvals/*`, `friedafetch/audit/*`).

## Security

- Only an **app-specific password** is used; it can be revoked at Apple any time and is redacted in diagnostics.
  Connections go exclusively over TLS to Apple endpoints; there is no telemetry.
- The MCP endpoint and the panel are protected by Home Assistant tokens and admin rights; tool groups, read-only
  mode, sending and deleting can be switched off individually.
- **Guard rails (options → Security):** hourly quotas per account for mail moves/deletions/flag changes, sent mails
  and deleted events/contacts/notes; a recipient policy for sending (any address, known contacts, or an allowlist of
  addresses/domains) with a recipient cap and optional BCC ban; protected calendars and mailboxes that AI clients may
  only read, and hidden mailboxes that are not exposed at all. Blocked calls return `code: "blocked"`.
- **Activity log:** every writing tool call and every rule run with hits or errors (marked manual or automatic) is recorded (time, client, Home Assistant user, tool,
  shortened parameters without message bodies, result) in the "Activity" card of the panel and fired as the event
  `friedafetch_action`, so an automation can notify you, e.g. when more than ten mails are deleted at once.
- **Approvals (human in the loop, options → Approvals):** sending, deleting and mass mail actions above a threshold
  can be parked instead of executed. Home Assistant shows a notification (optionally an actionable push on your phone
  with Approve/Deny) and the "Approvals" card in the panel lists the request; after approval Home Assistant runs the
  action and the AI reads the outcome with `icloud_approval_status`. Requests expire after a configurable time.
- **Endpoint profiles:** besides `/api/friedafetch` there is `/api/friedafetch/readonly`, which serves only tools that
  cannot change anything – the right endpoint for experiments or less trusted agents. The option "MCP endpoint only
  for administrator tokens" refuses non-admin tokens; request bodies are capped at 1 MiB.
- **Prompt-injection defence:** subjects, bodies, notes and event texts are stripped of invisible/bidi characters,
  marked as third-party content in the tool results, and scanned for typical injection patterns; hits are flagged
  with `suspicious: true` and `warnings`. The LLM prompt instructs the model never to follow instructions found in
  such content.
- **Supply chain:** every commit runs tests, Ruff with the Bandit rule set, Bandit, CodeQL, pip-audit, hassfest and
  HACS validation; GitHub Actions are pinned to commit SHAs, the `main` branch is protected, OpenSSF Scorecard rates
  the repository continuously, Dependabot and GitHub security alerts are enabled. Releases are built by GitHub
  Actions and published with signed build provenance (Sigstore) and a CycloneDX SBOM; HACS installs exactly this
  signed package (`gh attestation verify friedafetch.zip --repo nadeo360/friedafetch`). Details and the disclosure process: [SECURITY.md](SECURITY.md).

Example automation on the audit event:

```yaml
automation:
  - alias: Warn on mass deletion by AI
    triggers:
      - trigger: event
        event_type: friedafetch_action
    conditions:
      - "{{ trigger.event.data.action == 'delete' and (trigger.event.data.details.count | default(1)) > 10 }}"
    actions:
      - action: notify.mobile_app_iphone
        data:
          message: "{{ trigger.event.data.client }} deleted {{ trigger.event.data.details.count }} mails"
```

## Technical notes

- Credentials live only in the config entry; the password is redacted in diagnostics.
- CalDAV/CardDAV are implemented directly on `aiohttp` (principal discovery, `calendar-query`,
  `addressbook-multiget`, ETag-protected updates). Contacts are cached locally and synchronised incrementally via
  CTag/ETag.
- Recurring events are expanded with `python-dateutil` (RRULE, EXDATE, RDATE, moved occurrences).
- vCards are handled by a small lossless parser: unknown fields (photo, Apple extensions) survive updates.
- IMAP via `aioimaplib` (one serialised connection with automatic reconnect), SMTP via `aiosmtplib` (STARTTLS, 587).
- Packages that Home Assistant ships itself (`icalendar`, `aioimaplib`, `aiosmtplib`, `mcp`, `anyio`) are declared
  as minimum versions and follow the HA release, as hassfest requires.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_dev.txt
pytest
ruff check . && ruff format .
```

Home Assistant 2026.10 requires Python ≥ 3.14.2.

### Artwork

`assets/*.svg` are the sources; `scripts/build_icons.py` renders every PNG variant (icon, @2x, light/dark logo) into
`assets/` and into `custom_components/friedafetch/brand/`, from where Home Assistant (2026.3+) and HACS load the
integration's icon directly. `--check` verifies in CI that the files are current.

## About the use of AI

This integration was developed with substantial help from an AI coding assistant (Anthropic's Claude), working from
the maintainer's requirements and decisions. Every change is covered by the automated test suite and the security
checks described above, and all releases were reviewed and tested by the maintainer against a real iCloud account.
Please report bugs and ideas via GitHub issues – they are read by a human.

## Legal notices

Apple, iCloud, iPhone, iPad, Mac and macOS are trademarks of Apple Inc.; Home Assistant is a trademark of the Open
Home Foundation; "Model Context Protocol" and "Claude" are trademarks of Anthropic, PBC. **This is an independent
community project and is not affiliated with, endorsed or supported by Apple, the Open Home Foundation, Nabu Casa,
Anthropic or HACS.** Using iCloud through this integration is subject to Apple's iCloud terms; you are responsible
for complying with them. The software comes without warranty, reads and changes personal data on your behalf and
hands it to the AI clients you connect. Full notices, third-party licenses (including the GPL-3.0 licensed
`aioimaplib`) and the liability disclaimer: [NOTICE.md](NOTICE.md).

## License

MIT – see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
