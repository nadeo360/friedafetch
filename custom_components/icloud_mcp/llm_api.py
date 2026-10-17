"""LLM API exposing iCloud data as tools (consumed by the MCP Server integration)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonObjectType

from .caldav_client import CalendarError, CalendarNotFound, ICloudCalDav
from .carddav_client import ContactError, ContactNotFound, ICloudCardDav
from .const import (
    CONF_ALLOW_DELETE,
    CONF_ALLOW_SEND_MAIL,
    CONF_ENABLE_CALENDAR,
    CONF_ENABLE_CONTACTS,
    CONF_ENABLE_MAIL,
    CONF_ENABLE_NOTES,
    CONF_MAX_RESULTS,
    CONF_READ_ONLY,
    DEFAULT_ALLOW_DELETE,
    DEFAULT_ALLOW_SEND_MAIL,
    DEFAULT_ENABLE_CALENDAR,
    DEFAULT_ENABLE_CONTACTS,
    DEFAULT_ENABLE_MAIL,
    DEFAULT_ENABLE_NOTES,
    DEFAULT_MAX_RESULTS,
    DEFAULT_READ_ONLY,
    DOMAIN,
    LLM_API_ID,
    LLM_API_NAME,
    MAX_RESULTS_LIMIT,
)
from .dav import DavAuthError, DavConflictError, DavError, DavNotFoundError
from .mail import ICloudMail, MailAuthError, MailboxNotFound, MailError, MessageNotFound
from .notes import ICloudNotes
from .rules import FIELDS, MATCH_MODES, OPS, RuleEngine, RuleError, RuleNotFound
from .schema import vol
from .util import clamp, parse_datetime

_LOGGER = logging.getLogger(__name__)

_READ_ONLY = (
    llm.ToolAnnotations(read_only=True, destructive=False, idempotent=True) if hasattr(llm, "ToolAnnotations") else None
)
_WRITE = (
    llm.ToolAnnotations(read_only=False, destructive=False, idempotent=False)
    if hasattr(llm, "ToolAnnotations")
    else None
)
_DESTRUCTIVE = (
    llm.ToolAnnotations(read_only=False, destructive=True, idempotent=True) if hasattr(llm, "ToolAnnotations") else None
)


class ICloudClients:
    """Container for the per-config-entry clients."""

    def __init__(
        self,
        *,
        caldav: ICloudCalDav,
        carddav: ICloudCardDav,
        mail: ICloudMail,
        notes: ICloudNotes,
        options: dict[str, Any],
        rules: RuleEngine | None = None,
    ) -> None:
        self.caldav = caldav
        self.carddav = carddav
        self.mail = mail
        self.notes = notes
        self.options = options
        self.rules = rules

    @property
    def max_results(self) -> int:
        return clamp(self.options.get(CONF_MAX_RESULTS), DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT)


def _result(data: dict[str, Any], error: bool = False) -> Any:
    if hasattr(llm, "ToolResult"):
        return llm.ToolResult(data=data, error=error)
    return data


ToolFunc = Callable[["ICloudTool", HomeAssistant, dict[str, Any]], Awaitable[dict[str, Any]]]


class ICloudTool(llm.Tool):
    """Base class: common error handling for all iCloud tools."""

    integration = DOMAIN
    feature: str = ""
    writes: bool = False
    deletes: bool = False
    sends_mail: bool = False

    def __init__(self, clients: ICloudClients) -> None:
        self.clients = clients
        if _READ_ONLY is not None:
            self.annotations = _DESTRUCTIVE if self.deletes else (_WRITE if self.writes else _READ_ONLY)

    @property
    def tz(self):
        return dt_util.get_default_time_zone()

    async def async_call(
        self, hass: HomeAssistant, tool_input: llm.ToolInput, llm_context: llm.LLMContext
    ) -> llm.ToolResult | JsonObjectType:
        args = dict(tool_input.tool_args or {})
        try:
            data = await self.run(hass, args)
        except (
            CalendarNotFound,
            ContactNotFound,
            MessageNotFound,
            MailboxNotFound,
            DavNotFoundError,
            RuleNotFound,
        ) as err:
            return _result({"error": str(err), "code": "not_found"}, error=True)
        except (DavAuthError, MailAuthError) as err:
            _LOGGER.warning("iCloud authentication failed: %s", err)
            return _result(
                {
                    "error": "iCloud authentication failed. Check the app-specific password in the integration settings.",
                    "code": "auth",
                },
                error=True,
            )
        except DavConflictError as err:
            return _result(
                {"error": f"The item changed on the server in the meantime, please retry: {err}", "code": "conflict"},
                error=True,
            )
        except (CalendarError, ContactError, MailError, DavError, RuleError, ValueError) as err:
            return _result({"error": str(err), "code": "failed"}, error=True)
        except HomeAssistantError as err:
            return _result({"error": str(err), "code": "failed"}, error=True)
        return _result(data)

    async def run(self, hass: HomeAssistant, args: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _dt(self, value: str | None, default: datetime | None = None):
        if value is None or value == "":
            return default
        return parse_datetime(value, self.tz)


# ============================================================== calendar
class ListCalendars(ICloudTool):
    name = "icloud_list_calendars"
    feature = "calendar"
    description = "List the user's iCloud calendars with their ids. Use the id in the other calendar tools."
    parameters = vol.Schema({})

    async def run(self, hass, args):
        calendars = await self.clients.caldav.async_calendars(force=True)
        return {"calendars": [c.to_dict() for c in calendars]}


class ListEvents(ICloudTool):
    name = "icloud_list_events"
    feature = "calendar"
    description = (
        "List calendar events in a time range (recurring events are expanded). Default range: today until 7 days ahead. "
        "Dates are ISO 8601 (e.g. 2026-10-20 or 2026-10-20T14:00:00); naive times use the Home Assistant time zone."
    )
    parameters = vol.Schema(
        {
            vol.Optional("calendar_ids", description="Restrict to these calendar ids (default: all calendars)"): [str],
            vol.Optional("start", description="Range start (ISO 8601). Default: now"): str,
            vol.Optional("end", description="Range end (ISO 8601). Default: start + 7 days"): str,
            vol.Optional("query", description="Text filter on summary/description/location"): str,
            vol.Optional("limit", description="Maximum number of events"): int,
        }
    )

    async def run(self, hass, args):
        now = dt_util.now()
        start = self._dt(args.get("start"), now)
        end = self._dt(args.get("end"))
        from .util import to_datetime  # noqa: PLC0415

        start_dt = to_datetime(start, self.tz)
        end_dt = to_datetime(end, self.tz, end=True) if end is not None else start_dt + timedelta(days=7)
        if end_dt <= start_dt:
            raise ValueError("end must be after start")
        events = await self.clients.caldav.async_events(
            args.get("calendar_ids") or None,
            start_dt,
            end_dt,
            query=args.get("query"),
            limit=clamp(args.get("limit"), self.clients.max_results, MAX_RESULTS_LIMIT),
        )
        return {
            "start": start_dt.isoformat(timespec="minutes"),
            "end": end_dt.isoformat(timespec="minutes"),
            "count": len(events),
            "events": events,
        }


class GetEvent(ICloudTool):
    name = "icloud_get_event"
    feature = "calendar"
    description = "Get the full details of one calendar event by calendar id and event uid."
    parameters = vol.Schema({vol.Required("calendar_id"): str, vol.Required("uid"): str})

    async def run(self, hass, args):
        return await self.clients.caldav.async_get_event(args["calendar_id"], args["uid"])


class CreateEvent(ICloudTool):
    name = "icloud_create_event"
    feature = "calendar"
    writes = True
    description = (
        "Create a calendar event. For all-day events pass dates (YYYY-MM-DD) for start and end (end inclusive). "
        "For timed events pass ISO 8601 date-times; end defaults to start + 1 hour. Optional RRULE for recurrence, e.g. FREQ=WEEKLY;BYDAY=MO."
    )
    parameters = vol.Schema(
        {
            vol.Required("calendar_id", description="Target calendar id (see icloud_list_calendars)"): str,
            vol.Required("summary", description="Event title"): str,
            vol.Required("start", description="Start (ISO 8601 date or date-time)"): str,
            vol.Optional("end", description="End (ISO 8601). All-day: last day inclusive"): str,
            vol.Optional("description"): str,
            vol.Optional("location"): str,
            vol.Optional("rrule", description="iCalendar recurrence rule without the RRULE: prefix"): str,
            vol.Optional("url"): str,
        }
    )

    async def run(self, hass, args):
        start = self._dt(args["start"])
        end = self._dt(args.get("end"))
        if end is not None and isinstance(start, datetime) != isinstance(end, datetime):
            raise ValueError("start and end must both be dates (all-day) or both be date-times")
        return await self.clients.caldav.async_create_event(
            args["calendar_id"],
            args["summary"],
            start,
            end,
            description=args.get("description"),
            location=args.get("location"),
            rrule=args.get("rrule"),
            url=args.get("url"),
        )


class UpdateEvent(ICloudTool):
    name = "icloud_update_event"
    feature = "calendar"
    writes = True
    description = (
        "Update fields of an existing calendar event (only the provided fields change; pass an empty string to clear "
        "description/location/url/rrule). Changing only start keeps the original duration."
    )
    parameters = vol.Schema(
        {
            vol.Required("calendar_id"): str,
            vol.Required("uid"): str,
            vol.Optional("summary"): str,
            vol.Optional("start"): str,
            vol.Optional("end"): str,
            vol.Optional("description"): str,
            vol.Optional("location"): str,
            vol.Optional("rrule"): str,
            vol.Optional("url"): str,
        }
    )

    async def run(self, hass, args):
        start = self._dt(args.get("start"))
        end = self._dt(args.get("end"))
        if start is not None and end is not None and isinstance(start, datetime) != isinstance(end, datetime):
            raise ValueError("start and end must both be dates (all-day) or both be date-times")
        return await self.clients.caldav.async_update_event(
            args["calendar_id"],
            args["uid"],
            summary=args.get("summary"),
            start=start,
            end=end,
            description=args.get("description"),
            location=args.get("location"),
            rrule=args.get("rrule"),
            url=args.get("url"),
        )


class DeleteEvent(ICloudTool):
    name = "icloud_delete_event"
    feature = "calendar"
    writes = True
    deletes = True
    description = "Delete a calendar event (all occurrences if recurring). Confirm with the user before deleting."
    parameters = vol.Schema({vol.Required("calendar_id"): str, vol.Required("uid"): str})

    async def run(self, hass, args):
        await self.clients.caldav.async_delete_event(args["calendar_id"], args["uid"])
        return {"deleted": True, "uid": args["uid"], "calendar_id": args["calendar_id"]}


# ============================================================== contacts
_CONTACT_FIELDS = {
    vol.Optional("given_name"): str,
    vol.Optional("family_name"): str,
    vol.Optional("additional_names"): str,
    vol.Optional("prefix"): str,
    vol.Optional("suffix"): str,
    vol.Optional("full_name", description="Display name; derived from the name parts when omitted"): str,
    vol.Optional("nickname"): str,
    vol.Optional("organization"): str,
    vol.Optional("department"): str,
    vol.Optional("title", description="Job title"): str,
    vol.Optional("emails", description="List of {value, label}; label e.g. home/work/other"): [
        vol.Any(str, {vol.Required("value"): str, vol.Optional("label"): str})
    ],
    vol.Optional("phones", description="List of {value, label}; label e.g. mobile/home/work/main/fax"): [
        vol.Any(str, {vol.Required("value"): str, vol.Optional("label"): str})
    ],
    vol.Optional("urls"): [vol.Any(str, {vol.Required("value"): str, vol.Optional("label"): str})],
    vol.Optional("addresses"): [
        {
            vol.Optional("label"): str,
            vol.Optional("street"): str,
            vol.Optional("city"): str,
            vol.Optional("region"): str,
            vol.Optional("postal_code"): str,
            vol.Optional("country"): str,
            vol.Optional("po_box"): str,
            vol.Optional("extended"): str,
        }
    ],
    vol.Optional("birthday", description="YYYY-MM-DD"): str,
    vol.Optional("note"): str,
}


class SearchContacts(ICloudTool):
    name = "icloud_search_contacts"
    feature = "contacts"
    description = "Search iCloud contacts by name, e-mail, phone number, company or note. Empty query lists all contacts alphabetically."
    parameters = vol.Schema({vol.Optional("query", description="Search text"): str, vol.Optional("limit"): int})

    async def run(self, hass, args):
        contacts = await self.clients.carddav.async_search(
            args.get("query"), limit=clamp(args.get("limit"), self.clients.max_results, MAX_RESULTS_LIMIT)
        )
        return {"count": len(contacts), "contacts": contacts}


class GetContact(ICloudTool):
    name = "icloud_get_contact"
    feature = "contacts"
    description = "Get a single contact by uid."
    parameters = vol.Schema({vol.Required("uid"): str})

    async def run(self, hass, args):
        return await self.clients.carddav.async_get(args["uid"])


class CreateContact(ICloudTool):
    name = "icloud_create_contact"
    feature = "contacts"
    writes = True
    description = "Create a new iCloud contact. Provide at least a name, organization or e-mail."
    parameters = vol.Schema(_CONTACT_FIELDS)

    async def run(self, hass, args):
        if not any(
            args.get(k) for k in ("given_name", "family_name", "full_name", "organization", "emails", "nickname")
        ):
            raise ValueError("Provide at least a name, organization or e-mail address")
        return await self.clients.carddav.async_create(args)


class UpdateContact(ICloudTool):
    name = "icloud_update_contact"
    feature = "contacts"
    writes = True
    description = (
        "Update an existing contact. Only provided fields change; list fields (emails, phones, urls, addresses) "
        "replace the existing list completely, so include entries that should be kept."
    )
    parameters = vol.Schema({vol.Required("uid"): str, **_CONTACT_FIELDS})

    async def run(self, hass, args):
        uid = args.pop("uid")
        if not args:
            raise ValueError("No fields to update")
        return await self.clients.carddav.async_update(uid, args)


class DeleteContact(ICloudTool):
    name = "icloud_delete_contact"
    feature = "contacts"
    writes = True
    deletes = True
    description = "Delete a contact permanently. Confirm with the user before deleting."
    parameters = vol.Schema({vol.Required("uid"): str})

    async def run(self, hass, args):
        await self.clients.carddav.async_delete(args["uid"])
        return {"deleted": True, "uid": args["uid"]}


# ================================================================== mail
class ListMailboxes(ICloudTool):
    name = "icloud_list_mailboxes"
    feature = "mail"
    description = "List the mailboxes (folders) of the iCloud mail account."
    parameters = vol.Schema({})

    async def run(self, hass, args):
        boxes = await self.clients.mail.async_mailboxes(force=True)
        return {"mailboxes": [{k: v for k, v in b.items() if k != "flags"} for b in boxes]}


class SearchMail(ICloudTool):
    name = "icloud_search_mail"
    feature = "mail"
    description = (
        "Search or list e-mails in a mailbox (newest first) and return header summaries. "
        "Without filters the most recent messages are returned. Dates as YYYY-MM-DD."
    )
    parameters = vol.Schema(
        {
            vol.Optional("mailbox", description="Mailbox name, default INBOX"): str,
            vol.Optional("query", description="Full-text search (subject/body)"): str,
            vol.Optional("sender", description="Filter by sender address or name"): str,
            vol.Optional("recipient"): str,
            vol.Optional("subject"): str,
            vol.Optional("since", description="Only messages on/after this date"): str,
            vol.Optional("before", description="Only messages before this date"): str,
            vol.Optional("unseen_only"): bool,
            vol.Optional("flagged_only"): bool,
            vol.Optional("limit"): int,
        }
    )

    async def run(self, hass, args):
        from .util import to_datetime  # noqa: PLC0415

        since = self._dt(args.get("since"))
        before = self._dt(args.get("before"))
        messages = await self.clients.mail.async_search(
            args.get("mailbox") or "INBOX",
            query=args.get("query"),
            sender=args.get("sender"),
            recipient=args.get("recipient"),
            subject=args.get("subject"),
            since=to_datetime(since, self.tz) if since else None,
            before=to_datetime(before, self.tz) if before else None,
            unseen_only=bool(args.get("unseen_only")),
            flagged_only=bool(args.get("flagged_only")),
            limit=clamp(args.get("limit"), min(25, self.clients.max_results), MAX_RESULTS_LIMIT),
        )
        return {"mailbox": args.get("mailbox") or "INBOX", "count": len(messages), "messages": messages}


class GetMail(ICloudTool):
    name = "icloud_get_mail"
    feature = "mail"
    description = "Read one e-mail (headers, text body, attachment list) by mailbox and uid."
    parameters = vol.Schema(
        {
            vol.Required("uid"): int,
            vol.Optional("mailbox", description="Default INBOX"): str,
            vol.Optional("prefer_html", description="Return the HTML body instead of plain text"): bool,
            vol.Optional("max_chars", description="Truncate body to this many characters (default 20000)"): int,
            vol.Optional("include_headers", description="Also return the raw header block (diagnostics)"): bool,
        }
    )

    async def run(self, hass, args):
        return await self.clients.mail.async_get_message(
            args.get("mailbox") or "INBOX",
            int(args["uid"]),
            prefer_html=bool(args.get("prefer_html")),
            max_chars=clamp(args.get("max_chars"), 20000, 200000),
            include_headers=bool(args.get("include_headers")),
        )


class SendMail(ICloudTool):
    name = "icloud_send_mail"
    feature = "mail"
    writes = True
    sends_mail = True
    description = (
        "Send an e-mail from the user's iCloud account, optionally as a reply to an existing message "
        "(reply_to_uid + reply_to_mailbox; the subject then defaults to 'Re: ...' and the original is quoted). "
        "Always confirm recipients and content with the user before sending."
    )
    parameters = vol.Schema(
        {
            vol.Required("to", description="Recipient e-mail addresses"): [str],
            vol.Optional("subject"): str,
            vol.Required("body", description="Message text (plain text unless html=true)"): str,
            vol.Optional("cc"): [str],
            vol.Optional("bcc"): [str],
            vol.Optional("html", description="Body is HTML"): bool,
            vol.Optional("reply_to_uid"): int,
            vol.Optional("reply_to_mailbox"): str,
        }
    )

    async def run(self, hass, args):
        if not args.get("subject") and args.get("reply_to_uid") is None:
            raise ValueError("subject is required for a new e-mail")
        return await self.clients.mail.async_send(
            to=list(args.get("to") or []),
            subject=args.get("subject") or "",
            body=args["body"],
            cc=args.get("cc"),
            bcc=args.get("bcc"),
            html=bool(args.get("html")),
            reply_to_mailbox=args.get("reply_to_mailbox"),
            reply_to_uid=args.get("reply_to_uid"),
        )


_UID_PARAMS = {
    vol.Optional("uid", description="A single message uid"): int,
    vol.Optional("uids", description="Several message uids; processed in one IMAP command"): [int],
    vol.Optional("mailbox", description="Default INBOX"): str,
}


def _uids(args: dict[str, Any]) -> list[int]:
    values: list[int] = []
    if args.get("uid") is not None:
        values.append(int(args["uid"]))
    values.extend(int(u) for u in (args.get("uids") or []))
    if not values:
        raise ValueError("Provide uid or uids")
    return values


class MarkMail(ICloudTool):
    name = "icloud_mark_mail"
    feature = "mail"
    writes = True
    description = (
        "Mark one or many e-mails as read/unread and/or flagged/unflagged. "
        "Pass all affected uids in 'uids' at once instead of calling the tool per message."
    )
    parameters = vol.Schema({**_UID_PARAMS, vol.Optional("seen"): bool, vol.Optional("flagged"): bool})

    async def run(self, hass, args):
        if args.get("seen") is None and args.get("flagged") is None:
            raise ValueError("Provide seen and/or flagged")
        return await self.clients.mail.async_set_flags(
            args.get("mailbox") or "INBOX", _uids(args), seen=args.get("seen"), flagged=args.get("flagged")
        )


class MoveMail(ICloudTool):
    name = "icloud_move_mail"
    feature = "mail"
    writes = True
    description = (
        "Move one or many e-mails to another mailbox (e.g. Archive or Junk). "
        "Pass all affected uids in 'uids' at once; they are moved with a single IMAP command."
    )
    parameters = vol.Schema({**_UID_PARAMS, vol.Required("target_mailbox"): str})

    async def run(self, hass, args):
        return await self.clients.mail.async_move(args.get("mailbox") or "INBOX", _uids(args), args["target_mailbox"])


class DeleteMail(ICloudTool):
    name = "icloud_delete_mail"
    feature = "mail"
    writes = True
    deletes = True
    description = (
        "Move one or many e-mails to the trash (or delete permanently when already in the trash). "
        "Pass all affected uids in 'uids' at once; they are deleted with a single IMAP command. Confirm with the user first."
    )
    parameters = vol.Schema(dict(_UID_PARAMS))

    async def run(self, hass, args):
        return await self.clients.mail.async_delete(args.get("mailbox") or "INBOX", _uids(args))


# ================================================================= rules
_CONDITION = {
    vol.Required("field", description="Which header to test: from, to, cc, subject or any"): vol.In(FIELDS),
    vol.Required("op", description="contains, equals, starts_with, ends_with, domain (sender domain) or regex"): vol.In(
        OPS
    ),
    vol.Required("value", description="Text to compare with (case-insensitive)"): str,
}
_ACTIONS = {
    vol.Optional("move_to", description="Target mailbox name (see icloud_list_mailboxes)"): str,
    vol.Optional("mark_seen", description="Mark as read (true) or unread (false)"): bool,
    vol.Optional("flag", description="Flag (true) or unflag (false)"): bool,
    vol.Optional("delete", description="Move to the trash"): bool,
    vol.Optional("stop", description="Stop evaluating further rules for a matching message (default true)"): bool,
}


class RuleTool(ICloudTool):
    """Base for rule tools: requires the rule engine."""

    @property
    def rules(self) -> RuleEngine:
        if self.clients.rules is None:
            raise ValueError("Inbox rules are not available (mail tools disabled)")
        return self.clients.rules


class ListRules(RuleTool):
    name = "icloud_list_rules"
    feature = "mail"
    description = (
        "List the inbox rules managed by Home Assistant (with ids, conditions, actions, hit counters) and the last run."
    )
    parameters = vol.Schema({})

    async def run(self, hass, args):
        return {"rules": await self.rules.async_list(), "last_run": self.rules.last_run}


class CreateRule(RuleTool):
    name = "icloud_create_rule"
    feature = "mail"
    writes = True
    description = (
        "Create an inbox rule that Home Assistant applies to new e-mails (and on demand to the whole mailbox). "
        "Example: move everything from newsletter@example.com to 'Archive'. Rules are evaluated in order."
    )
    parameters = vol.Schema(
        {
            vol.Required("name"): str,
            vol.Required("conditions", description="One or more conditions"): [_CONDITION],
            vol.Required("actions"): _ACTIONS,
            vol.Optional("match", description="all (default) or any of the conditions"): vol.In(MATCH_MODES),
            vol.Optional("enabled"): bool,
            vol.Optional("mailbox", description="Mailbox the rule watches, default INBOX"): str,
        }
    )

    async def run(self, hass, args):
        return await self.rules.async_create(args)


class UpdateRule(RuleTool):
    name = "icloud_update_rule"
    feature = "mail"
    writes = True
    description = "Change an inbox rule (only the provided fields change; conditions replace the list). 'position' reorders the rule."
    parameters = vol.Schema(
        {
            vol.Required("rule_id"): str,
            vol.Optional("name"): str,
            vol.Optional("conditions"): [_CONDITION],
            vol.Optional("actions"): _ACTIONS,
            vol.Optional("match"): vol.In(MATCH_MODES),
            vol.Optional("enabled"): bool,
            vol.Optional("mailbox"): str,
            vol.Optional("position", description="New index in the rule order (0 = first)"): int,
        }
    )

    async def run(self, hass, args):
        rule_id = args.pop("rule_id")
        if not args:
            raise ValueError("No fields to update")
        return await self.rules.async_update(rule_id, args)


class DeleteRule(RuleTool):
    name = "icloud_delete_rule"
    feature = "mail"
    writes = True
    description = "Delete an inbox rule."
    parameters = vol.Schema({vol.Required("rule_id"): str})

    async def run(self, hass, args):
        await self.rules.async_delete(args["rule_id"])
        return {"deleted": True, "rule_id": args["rule_id"]}


class RunRules(RuleTool):
    name = "icloud_run_rules"
    feature = "mail"
    writes = True
    description = (
        "Apply the inbox rules now. scope 'all' (default) checks the newest messages of the mailbox, "
        "'new' only messages since the last automatic run. dry_run=true only reports what would happen."
    )
    parameters = vol.Schema(
        {
            vol.Optional("scope"): vol.In(["new", "all"]),
            vol.Optional("dry_run"): bool,
            vol.Optional("mailbox"): str,
            vol.Optional("rule_ids", description="Only these rules"): [str],
            vol.Optional("limit", description="Newest messages to inspect for scope 'all' (default 2000)"): int,
        }
    )

    async def run(self, hass, args):
        return await self.rules.async_run(
            scope=args.get("scope") or "all",
            dry_run=bool(args.get("dry_run")),
            mailbox=args.get("mailbox"),
            rule_ids=args.get("rule_ids"),
            limit=clamp(args.get("limit"), 2000, 2000),
        )


# ================================================================= notes
class ListNotes(ICloudTool):
    name = "icloud_list_notes"
    feature = "notes"
    description = "List or search notes stored in the account's IMAP Notes folder (newest first)."
    parameters = vol.Schema({vol.Optional("query"): str, vol.Optional("limit"): int})

    async def run(self, hass, args):
        notes = await self.clients.notes.async_list(
            args.get("query"), limit=clamp(args.get("limit"), self.clients.max_results, MAX_RESULTS_LIMIT)
        )
        return {"count": len(notes), "notes": notes}


class GetNote(ICloudTool):
    name = "icloud_get_note"
    feature = "notes"
    description = "Read a note (title and text) by uid."
    parameters = vol.Schema({vol.Required("uid"): int})

    async def run(self, hass, args):
        return await self.clients.notes.async_get(int(args["uid"]))


class CreateNote(ICloudTool):
    name = "icloud_create_note"
    feature = "notes"
    writes = True
    description = "Create a new note with a title and plain-text body."
    parameters = vol.Schema({vol.Required("title"): str, vol.Required("body"): str})

    async def run(self, hass, args):
        return await self.clients.notes.async_create(args["title"], args["body"])


class UpdateNote(ICloudTool):
    name = "icloud_update_note"
    feature = "notes"
    writes = True
    description = "Replace title and/or body of a note. The note gets a new uid afterwards."
    parameters = vol.Schema({vol.Required("uid"): int, vol.Optional("title"): str, vol.Optional("body"): str})

    async def run(self, hass, args):
        if args.get("title") is None and args.get("body") is None:
            raise ValueError("Provide title and/or body")
        return await self.clients.notes.async_update(int(args["uid"]), title=args.get("title"), body=args.get("body"))


class DeleteNote(ICloudTool):
    name = "icloud_delete_note"
    feature = "notes"
    writes = True
    deletes = True
    description = "Delete a note permanently. Confirm with the user first."
    parameters = vol.Schema({vol.Required("uid"): int})

    async def run(self, hass, args):
        return await self.clients.notes.async_delete(int(args["uid"]))


ALL_TOOLS: list[type[ICloudTool]] = [
    ListCalendars,
    ListEvents,
    GetEvent,
    CreateEvent,
    UpdateEvent,
    DeleteEvent,
    SearchContacts,
    GetContact,
    CreateContact,
    UpdateContact,
    DeleteContact,
    ListMailboxes,
    SearchMail,
    GetMail,
    SendMail,
    MarkMail,
    MoveMail,
    DeleteMail,
    ListRules,
    CreateRule,
    UpdateRule,
    DeleteRule,
    RunRules,
    ListNotes,
    GetNote,
    CreateNote,
    UpdateNote,
    DeleteNote,
]

_FEATURE_OPTION = {
    "calendar": (CONF_ENABLE_CALENDAR, DEFAULT_ENABLE_CALENDAR),
    "contacts": (CONF_ENABLE_CONTACTS, DEFAULT_ENABLE_CONTACTS),
    "mail": (CONF_ENABLE_MAIL, DEFAULT_ENABLE_MAIL),
    "notes": (CONF_ENABLE_NOTES, DEFAULT_ENABLE_NOTES),
}


def build_tools(clients: ICloudClients) -> list[llm.Tool]:
    """Instantiate the tools allowed by the options."""
    opts = clients.options
    read_only = opts.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
    allow_send = opts.get(CONF_ALLOW_SEND_MAIL, DEFAULT_ALLOW_SEND_MAIL)
    allow_delete = opts.get(CONF_ALLOW_DELETE, DEFAULT_ALLOW_DELETE)
    tools: list[llm.Tool] = []
    for cls in ALL_TOOLS:
        key, default = _FEATURE_OPTION[cls.feature]
        if not opts.get(key, default):
            continue
        if read_only and cls.writes:
            continue
        if cls.deletes and not allow_delete:
            continue
        if cls.sends_mail and not allow_send:
            continue
        tools.append(cls(clients))
    return tools


API_PROMPT = (
    "You have access to the user's Apple iCloud account: calendars (CalDAV), contacts (CardDAV), "
    "e-mail (IMAP/SMTP) and IMAP notes. Times are in the user's time zone ({tz}); the current local time is {now}. "
    "Use icloud_list_calendars first to learn calendar ids. Ask for confirmation before sending e-mails or deleting anything."
)


class ICloudLLMAPI(llm.API):
    """The iCloud LLM API registered with Home Assistant."""

    def __init__(
        self, hass: HomeAssistant, clients: ICloudClients, api_id: str = LLM_API_ID, name: str = LLM_API_NAME
    ) -> None:
        super().__init__(hass=hass, id=api_id, name=name)
        self.clients = clients

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        now = dt_util.now()
        prompt = API_PROMPT.format(tz=now.tzname() or str(now.tzinfo), now=now.isoformat(timespec="minutes"))
        return llm.APIInstance(
            api=self,
            api_prompt=prompt,
            llm_context=llm_context,
            tools=build_tools(self.clients),
        )
