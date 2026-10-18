<p align="center">
  <img src="https://raw.githubusercontent.com/nadeo360/friedafetch/main/assets/logo@2x.png" alt="Frieda" width="720">
</p>

<p align="center">
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/nadeo360/friedafetch/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/validate.yml"><img alt="hassfest & HACS" src="https://github.com/nadeo360/friedafetch/actions/workflows/validate.yml/badge.svg"></a>
  <a href="https://github.com/nadeo360/friedafetch/security/code-scanning"><img alt="CodeQL" src="https://img.shields.io/badge/CodeQL-default%20setup-2ea44f"></a>
  <a href="https://github.com/nadeo360/friedafetch/actions/workflows/security.yml"><img alt="Dependency audit" src="https://github.com/nadeo360/friedafetch/actions/workflows/security.yml/badge.svg"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/nadeo360/friedafetch"><img alt="OpenSSF Scorecard" src="https://api.scorecard.dev/projects/github.com/nadeo360/friedafetch/badge"></a>
  <a href="https://github.com/nadeo360/friedafetch/releases"><img alt="Release" src="https://img.shields.io/github/v/release/nadeo360/friedafetch?display_name=tag"></a>
  <a href="https://github.com/nadeo360/friedafetch/blob/main/LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

<p align="center"><b>English</b> · <a href="https://github.com/nadeo360/friedafetch/blob/main/README.de.md">Deutsch</a></p>

# Frieda – MCP connector for iCloud

**Frieda** (technical name `friedafetch`) is a Home Assistant integration (HACS) that connects **Apple iCloud** with an app-specific password and exposes
**calendars, contacts, e-mail and notes** as tools for LLMs. The tools are registered as a Home Assistant
**LLM API**, so they are available to every conversation agent that enables the API (Assist, Google Generative AI,
OpenAI, Ollama …) and to any **MCP client** (Claude, ChatGPT connectors, local agents) through Home Assistant's
MCP Server integration or the integration's own MCP endpoint. Inbox rules, push delivery and a daily overview
come with the separate extension [Frieda Postfach](https://github.com/nadeo360/friedafetch-mail).
The project is named after the maintainer's dog Frieda, who looks out of the cloud in the logo.

## Features

| Area      | Protocol            | Read                                                        | Write                                                            |
|-----------|---------------------|-------------------------------------------------------------|------------------------------------------------------------------|
| Calendar  | CalDAV              | list calendars, search/read events (recurrences expanded)   | create, update (incl. RRULE) and delete events                   |
| Contacts  | CardDAV             | search (name, mail, phone, company …) and read contacts     | create, update and delete contacts                               |
| E-mail    | IMAP + SMTP         | mailboxes, search/filter, read mail (text, attachment list) | send/reply, mark read/flagged, move, trash – many uids at once   |
| Notes     | IMAP folder `Notes` | list/search/read notes                                      | create, update and delete notes                                  |
| Rules     | –                   | with the extension [Frieda Postfach](https://github.com/nadeo360/friedafetch-mail) | inbox rules, push, daily overview          |
| Insights  | all of the above    | mailbox statistics, free time slots, birthdays, duplicate contacts | unsubscribe from newsletters, store attachments (receipts) |

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


### Upgrading to 2.0

Frieda 2.0 is a pure connector: inbox rules, push delivery, the daily overview and the birthday sensor moved to the
separate integration [**Frieda Postfach**](https://github.com/nadeo360/friedafetch-mail). Install it via HACS and add
it for your account; existing rules, hit counters, run history and automation settings are picked up automatically.
Until then Frieda shows a repair notice for accounts with stored rules, and no rules run. The rule tools
(`icloud_*_rule`, `icloud_run_rules`, `icloud_daily_overview`) appear again as soon as Frieda Postfach is set up.

### Upgrading from “iCloud MCP” (versions up to 1.0.x)

The project was renamed to Frieda with version 1.1.0; the integration domain changed from `icloud_mcp` to
`friedafetch`. Remove the old integration (Settings → Devices & services → iCloud MCP → Delete), update the HACS
custom repository to `https://github.com/nadeo360/friedafetch`, install Frieda and add it again with the Apple ID
and app-specific password. Rules and options are not migrated; MCP clients need the new endpoint
`/api/friedafetch`. The tool names (`icloud_*`) are unchanged. If an old `custom_components/icloud_mcp` folder is left
behind, Home Assistant may keep loading it instead of the current version (both declare the domain `friedafetch`);
Frieda detects this at startup and shows a repair issue – delete the folder named there and restart Home Assistant.

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

The options dialog has three sections: **Tools and account**, **Security and guard rails** and **Approvals**.

| Option                                   | Effect                                                                   |
|------------------------------------------|--------------------------------------------------------------------------|
| Calendar / Contact / E-mail / Note tools | show or hide tool groups                                                 |
| Read-only mode                           | hides every create/update/delete/send tool                               |
| Allow sending e-mails                    | hides `icloud_send_mail` when disabled                                   |
| Allow deleting                           | hides all `icloud_delete_*` tools (except rule deletion) when disabled   |
| Default maximum number of results        | default list limit (1–200)                                               |
| Sender address                           | `From:` for outgoing mail (default: Apple ID; must be an iCloud alias)   |
| Attachment folder                        | where `icloud_save_attachments` (and Frieda Postfach rules) store files (default `<media>/frieda`; must be an allowed path) |
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
the panel offers an account selector. Each account has its own options.

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
| `icloud_approval_status` | outcome of an action that required human approval                           |
| `icloud_mailbox_stats`   | top senders/domains, unread and newsletter share, rule coverage and rule suggestions |
| `icloud_unsubscribe`     | unsubscribe from a newsletter (one-click https or unsubscribe e-mail)       |
| `icloud_save_attachments`| store the attachments of a mail in `<folder>/<subfolder>/<YYYY-MM>/`        |
| `icloud_find_free_time`  | free slots of a given length within working hours                           |
| `icloud_upcoming_birthdays` | birthdays of the contacts in the coming days (with age, if known)        |
| `icloud_find_duplicate_contacts` | probable duplicates (same e-mail, phone or name)                    |
| `icloud_list_notes`      | list/search notes                                                           |
| `icloud_get_note`        | read a note                                                                 |
| `icloud_create_note`     | create a note                                                               |
| `icloud_update_note`     | replace a note (it gets a new uid)                                          |
| `icloud_delete_note`     | delete a note                                                               |

Times are ISO 8601; naive times are interpreted in the Home Assistant time zone. All-day events use dates
(`YYYY-MM-DD`) with an **inclusive** end date. The mail tools `icloud_mark_mail`, `icloud_move_mail` and
`icloud_delete_mail` accept a `uids` list (up to 500) and process it with a single IMAP command, so cleaning up spam
is one call instead of one per message.

## Panel

The integration adds **"Frieda"** to the Home Assistant sidebar (admins only, German/English following the HA
language):

- **Overview:** whether the MCP endpoint is active (both URLs to copy – for the local address and, if set up, the
  external address and Home Assistant Cloud –, number of reading and writing tools, token rule), the MCP clients that connected recently (name and version from the MCP handshake), whether the LLM API is
  exposed by Home Assistant's own MCP server, and the state of **Frieda Postfach** (running, installed but not linked,
  not installed).
- **Usage:** tool calls today, in 7 and 30 days and in total, split into reading and writing, a 14-day chart, the most
  used tools, where the calls came from (Frieda endpoint, HA MCP server, Assist agents) and the hourly quotas. Only
  counters are stored, never arguments or results.
- **Approvals:** pending and decided requests (approve or deny with one tap, also from the companion app; the request
  shows "Sending …" until the result is in).
- **Change log:** everything Frieda changed in iCloud as a table grouped by day (e.g. "Mail moved · 3 messages ·
  → Archive"), with search, filters for area and trigger, a result switch and selectable columns; a click on a row
  shows the error and the raw parameters, and for runs of Frieda Postfach the messages with a link to their timeline.

**Widgets:** the cards are widgets. **Arrange** in the title bar lets you drag them by the handle (or move them with
the arrows), switch them between full and half width and hide them; tables offer a **Columns** menu. Rare actions
such as clearing the log sit in a small ⋮ menu and always ask for confirmation. The layout is stored per Home
Assistant user in Home Assistant itself, so it survives restarts and follows you to other devices.

**Live:** the tables follow changes right away (new change-log entries, approvals, runs), without reloading the page;
new rows light up briefly. After an update the panel offers a reload when it still runs the old code.

**Pages:** long tables show 5, 10, 25, 50 or all entries per page (remembered per table); search and filters
always cover all entries.

**Frieda UI:** both panels use one shared design library (`/friedafetch_static/ui.js`): colours from the Home
Assistant theme, buttons, chips, tables, menus, dialogs and widgets. Frieda Postfach loads it from Frieda, so every
module looks and behaves the same. It also covers accessibility: the focus stays in place when a panel redraws,
dialogs keep the focus inside, notices and search hits are read out, symbols have names for screen readers, and
coloured text keeps WCAG AA contrast in light and dark themes.

The panel has no external dependencies and talks to the integration via WebSocket commands (`friedafetch/accounts`,
`friedafetch/overview`, `friedafetch/usage/reset`, `friedafetch/approvals/*`, `friedafetch/audit/*`).

## Attachments and unsubscribing

- **Attachments:** `icloud_save_attachments` stores the attachments of a mail below the attachment folder, sorted by
  month and named `<date>_<sender>_<file>`. Identical files are not stored twice, small images (logos, signatures)
  are skipped. Home Assistant must allow the folder (media folders are allowed by default, others go into
  `allowlist_external_dirs`).
- **Unsubscribe:** `icloud_unsubscribe` uses the `List-Unsubscribe` header: one-click https (RFC 8058) first, then an
  unsubscribe e-mail (only when sending is allowed; it counts against the sending quota and needs approval if
  sending does). Links that require a web page are returned for you to open.

## Extensions

Frieda only acts when an AI client or you call it. Everything that runs on its own lives in extensions that attach to
a Frieda account, reuse its connection and guard rails, and add their tools to it:

- [**Frieda Postfach**](https://github.com/nadeo360/friedafetch-mail) (`friedafetch_mail`): inbox rules with push
  delivery (IMAP IDLE), receipts via rules, the daily overview, a birthday sensor and the rule tools.

## Security

- Only an **app-specific password** is used; it can be revoked at Apple any time and is redacted in diagnostics.
  Connections go exclusively over TLS to Apple endpoints; there is no telemetry.
- The MCP endpoint and the panel are protected by Home Assistant tokens and admin rights; tool groups, read-only
  mode, sending and deleting can be switched off individually.
- **Guard rails (options → Security):** hourly quotas per account for mail moves/deletions/flag changes, sent mails
  and deleted events/contacts/notes; a recipient policy for sending (any address, known contacts, or an allowlist of
  addresses/domains) with a recipient cap and optional BCC ban; protected calendars and mailboxes that AI clients may
  only read, and hidden mailboxes that are not exposed at all. Blocked calls return `code: "blocked"`.
- **Change log:** every writing tool call and every rule run with hits or errors (marked manual or automatic) is recorded (time, client, Home Assistant user, tool,
  shortened parameters without message bodies, result) in the "Change log" card of the panel and fired as the event
  `friedafetch_action`, so an automation can notify you, e.g. when more than ten mails are deleted at once.
- **Approvals (human in the loop, options → Approvals):** sending, deleting and mass mail actions above a threshold
  can be parked instead of executed. Home Assistant shows a notification (optionally an actionable push on your phone
  with Approve/Deny) and the "Approvals" card in the panel lists the request; after approval Home Assistant runs the
  action and the AI reads the outcome with `icloud_approval_status`. Requests expire after a configurable time.
- **Delayed sending (options → Approvals, default off):** e-mails from assistants wait a few seconds (e.g. 60) before
  they go out. Until then the "Approvals" card shows them with "Send now" and "Cancel", and the notification has a
  Cancel button. Recipients and quotas are checked at once and again when the mail is sent. Without effect when sending
  needs approval anyway.
- **Persistent state:** the hourly quotas, active injection locks and the list of approvals survive restarts and
  reloads, so a restart neither refills a quota nor lifts a lock. Requests that were still open at a restart cannot
  be executed afterwards: they are closed as expired (a delayed mail as cancelled, i.e. not sent).
- **Endpoint profiles:** besides `/api/friedafetch` there is `/api/friedafetch/readonly`, which serves only tools that
  cannot change anything – the right endpoint for experiments or less trusted agents. The option "MCP endpoint only
  for administrator tokens" refuses non-admin tokens; request bodies are capped at 1 MiB.
- **Prompt-injection defence:** subjects, bodies, notes and event texts are stripped of invisible/bidi characters,
  marked as third-party content in the tool results, and scanned for typical injection patterns; hits are flagged
  with `suspicious: true` and `warnings`. The LLM prompt instructs the model never to follow instructions found in
  such content.
- **Injection lock (options → Security, default on):** once a tool returned such flagged content, the same caller
  (platform and Home Assistant user) may not send, delete, unsubscribe or create deleting/moving rules for a while
  (default 15 minutes): the call is parked for approval, or blocked if approvals are off. The panel overview shows
  active locks. This stops the classic attack where a mail says “forward everything to …”.
- **Rules are mass actions too:** with Frieda Postfach, rules that delete or move and real runs over the whole
  mailbox follow the approvals (“approve deleting”, mass threshold). Unattended runs (timer, push) and runs requested
  by an AI change at most 100 messages (50 deletions) per run and count against the hourly quota for mail changes;
  the rest follows in the next run. AI sorting counts against the same quota.
- **Supply chain:** every commit runs tests, Ruff with the Bandit rule set, Bandit, CodeQL, pip-audit, hassfest and
  HACS validation; GitHub Actions are pinned to commit SHAs, the `main` branch is protected, OpenSSF Scorecard rates
  the repository continuously, Dependabot and GitHub security alerts are enabled. Releases are built by GitHub
  Actions and published with signed build provenance (Sigstore) and a CycloneDX SBOM; HACS installs exactly this
  signed package (`gh attestation verify friedafetch.zip --repo nadeo360/friedafetch`). Details and the disclosure process: [SECURITY.md](https://github.com/nadeo360/friedafetch/blob/main/SECURITY.md).

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

The architecture of Frieda and Frieda Postfach is described in the arc42 document [docs/architecture.md](https://github.com/nadeo360/friedafetch/blob/main/docs/architecture.md).

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
`aioimaplib`) and the liability disclaimer: [NOTICE.md](https://github.com/nadeo360/friedafetch/blob/main/NOTICE.md).

## License

MIT – see [LICENSE](https://github.com/nadeo360/friedafetch/blob/main/LICENSE) and [NOTICE.md](https://github.com/nadeo360/friedafetch/blob/main/NOTICE.md).
