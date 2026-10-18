"""Mail tools (IMAP/SMTP), unsubscribe, attachments and mailbox statistics."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .attachments import AttachmentError
from .const import (
    CONF_ALLOW_SEND_MAIL,
    CONF_APPROVAL_SEND,
    CONF_READ_ONLY,
    DEFAULT_ALLOW_SEND_MAIL,
    DEFAULT_APPROVAL_SEND,
    DEFAULT_READ_ONLY,
    MAX_RESULTS_LIMIT,
)
from .guard import QUOTA_MAIL_MODIFY, QUOTA_MAIL_SEND
from .insights import mailbox_stats
from .mail import list_unsubscribe
from .schema import vol
from .tool_base import ICloudTool
from .unsubscribe import UnsubscribeError, async_one_click, parse_mailto
from .util import UNTRUSTED_NOTICE, clamp

_LOGGER = logging.getLogger(__name__)


class ListMailboxes(ICloudTool):
    name = "icloud_list_mailboxes"
    feature = "mail"
    description = "List the mailboxes (folders) of the iCloud mail account."
    parameters = vol.Schema({})

    async def run(self, hass, args):
        boxes = self.clients.guard.filter_mailboxes(await self.clients.mail.async_mailboxes(force=True))
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
            self._mailbox(args),
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
            self._mailbox(args),
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
        guard = self.clients.guard
        guard.check_quota(QUOTA_MAIL_SEND)
        known: set[str] | None = None
        if guard.requires_contacts:
            known = {
                e["value"]
                for c in await self.clients.carddav.async_search(None, limit=100000)
                for e in c.get("emails", [])
                if e.get("value")
            }
        guard.check_recipients(args.get("to") or [], args.get("cc"), args.get("bcc"), known)
        if args.get("reply_to_uid") is not None:
            self._mailbox(args, "reply_to_mailbox")
        result = await self.clients.mail.async_send(
            to=list(args.get("to") or []),
            subject=args.get("subject") or "",
            body=args["body"],
            cc=args.get("cc"),
            bcc=args.get("bcc"),
            html=bool(args.get("html")),
            reply_to_mailbox=args.get("reply_to_mailbox"),
            reply_to_uid=args.get("reply_to_uid"),
        )
        guard.consume(QUOTA_MAIL_SEND)
        return result


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
        box, uids = args.get("mailbox") or "INBOX", _uids(args)
        self.clients.guard.check_mailbox_writable(box)
        self.clients.guard.check_quota(QUOTA_MAIL_MODIFY, len(uids))
        result = await self.clients.mail.async_set_flags(box, uids, seen=args.get("seen"), flagged=args.get("flagged"))
        self.clients.guard.consume(QUOTA_MAIL_MODIFY, len(uids))
        return result


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
        box, uids = args.get("mailbox") or "INBOX", _uids(args)
        self.clients.guard.check_mailbox_writable(box)
        self.clients.guard.check_mailbox_visible(args["target_mailbox"])
        self.clients.guard.check_quota(QUOTA_MAIL_MODIFY, len(uids))
        result = await self.clients.mail.async_move(box, uids, args["target_mailbox"])
        self.clients.guard.consume(QUOTA_MAIL_MODIFY, len(uids))
        return result


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
        box, uids = args.get("mailbox") or "INBOX", _uids(args)
        self.clients.guard.check_mailbox_writable(box)
        self.clients.guard.check_quota(QUOTA_MAIL_MODIFY, len(uids))
        result = await self.clients.mail.async_delete(box, uids)
        self.clients.guard.consume(QUOTA_MAIL_MODIFY, len(uids))
        return result


# ============================================================== insights


class MailboxStats(ICloudTool):
    name = "icloud_mailbox_stats"
    feature = "mail"
    description = (
        "Analyse a mailbox: messages, unread and newsletter share, top senders and domains (with the inbox rule "
        "that already covers them) and rule suggestions for frequent, uncovered senders. Use it before proposing "
        "new inbox rules."
    )
    parameters = vol.Schema(
        {
            vol.Optional("mailbox", description="Default INBOX"): str,
            vol.Optional("days", description="Only messages of the last N days (default 90, max 730)"): int,
            vol.Optional("max_messages", description="Newest messages inspected (default 1000, max 3000)"): int,
        }
    )

    async def run(self, hass, args):
        box = self._mailbox(args)
        days = clamp(args.get("days"), 90, 730)
        cap = clamp(args.get("max_messages"), 1000, 3000)
        since = dt_util.now() - timedelta(days=days)
        uids = await self.clients.mail.async_search_uids(box, ["SINCE", since.strftime("%d-%b-%Y")])
        uids = sorted(uids)[-cap:]
        summaries: list[dict[str, Any]] = []
        for i in range(0, len(uids), 200):
            summaries.extend(await self.clients.mail.async_summaries(box, uids[i : i + 200]))
        covered = None
        for ext in self.clients.extensions.values():
            matcher = getattr(ext, "rule_matcher", None)
            if matcher is not None:
                covered = matcher(box)
                break
        stats = mailbox_stats(summaries, covered=covered)
        return {"mailbox": box, "days": days, "inspected": len(summaries), "content_notice": UNTRUSTED_NOTICE, **stats}


class Unsubscribe(ICloudTool):
    name = "icloud_unsubscribe"
    feature = "mail"
    writes = True
    description = (
        "Unsubscribe from a newsletter using the List-Unsubscribe information of one message: one-click https "
        "(RFC 8058) is preferred, otherwise an unsubscribe e-mail is sent (needs 'Allow sending e-mails'). Links "
        "that need a web page are returned for the user to open. Confirm with the user first."
    )
    parameters = vol.Schema(
        {
            vol.Required("uid", description="Message uid of a newsletter"): int,
            vol.Optional("mailbox", description="Default INBOX"): str,
        }
    )

    def is_critical(self, args):
        return True  # contacts a third party on the user's behalf

    def approval_reason(self, args):
        reason = super().approval_reason(args)
        if (
            reason is None
            and self.clients.approvals is not None
            and self.clients.options.get(CONF_APPROVAL_SEND, DEFAULT_APPROVAL_SEND)
        ):
            return "send"
        return reason

    async def run(self, hass, args):
        from homeassistant.util.ssl import client_context  # noqa: PLC0415

        box = self._mailbox(args)
        guard = self.clients.guard
        guard.check_quota(QUOTA_MAIL_SEND)
        _, msg = await self.clients.mail.async_fetch_raw(box, int(args["uid"]))
        info = list_unsubscribe(msg)
        if not info:
            raise UnsubscribeError("This message has no unsubscribe information (List-Unsubscribe header)")
        if info["one_click"]:
            result = await async_one_click(info["https"][0], ssl_context=client_context())
        elif info["mailto"]:
            if self.clients.options.get(CONF_READ_ONLY, DEFAULT_READ_ONLY) or not self.clients.options.get(
                CONF_ALLOW_SEND_MAIL, DEFAULT_ALLOW_SEND_MAIL
            ):
                raise UnsubscribeError(
                    "Unsubscribing needs an e-mail here, but sending e-mails is disabled in the options"
                    + (f"; the user can open {info['https'][0]} instead" if info["https"] else "")
                )
            target = parse_mailto(info["mailto"][0])
            sent = await self.clients.mail.async_send(
                to=[target["address"]], subject=target["subject"], body=target["body"]
            )
            result = {"method": "mailto", "to": target["address"], "message_id": sent.get("message_id")}
        elif info["https"]:
            return {
                "method": "manual",
                "url": info["https"][0],
                "note": "This sender only offers a web page; give the link to the user to open it themselves.",
            }
        else:
            raise UnsubscribeError("No supported unsubscribe method found")
        guard.consume(QUOTA_MAIL_SEND)
        return {"uid": int(args["uid"]), "mailbox": box, **result}


class SaveAttachments(ICloudTool):
    name = "icloud_save_attachments"
    feature = "mail"
    writes = True
    description = (
        "Store the attachments of an e-mail in the Home Assistant attachment folder (e.g. receipts and invoices), "
        "sorted into <folder>/<YYYY-MM>/. Small images (logos) are skipped unless types are given."
    )
    parameters = vol.Schema(
        {
            vol.Required("uid"): int,
            vol.Optional("mailbox", description="Default INBOX"): str,
            vol.Optional("folder", description="Subfolder, e.g. 'Belege' or 'Rechnungen/Strom'"): str,
            vol.Optional("types", description="Only these file types, e.g. ['pdf']"): [str],
        }
    )

    async def run(self, hass, args):
        if self.clients.attachments is None:
            raise AttachmentError("No attachment folder is configured (options → Extras)")
        box = self._mailbox(args)
        files = await self.clients.attachments.async_save(box, int(args["uid"]), args.get("folder"), args.get("types"))
        return {
            "uid": int(args["uid"]),
            "folder": str(self.clients.attachments.base),
            "count": sum(1 for f in files if f["status"] == "saved"),
            "files": files,
        }


# ============================================================= approvals
