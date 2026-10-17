"""Apple Notes via the IMAP 'Notes' mailbox.

Only notes that are stored in the IMAP account are reachable this way. Notes
that were upgraded to the modern iCloud Notes format (CloudKit) are not
exposed by Apple through any app-password accessible protocol.
"""

from __future__ import annotations

import email
import logging
import uuid
from datetime import UTC, datetime
from email import policy
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from typing import Any

import aioimaplib

from .mail import (
    HEADER_FIELDS,
    ICloudMail,
    MailboxNotFound,
    MessageNotFound,
    _decode_header_value,
    _parse_date,
    extract_body,
    parse_fetch,
)
from .util import text_to_html

_LOGGER = logging.getLogger(__name__)

NOTE_HEADERS = f"{HEADER_FIELDS} X-UNIVERSALLY-UNIQUE-IDENTIFIER X-UNIFORM-TYPE-IDENTIFIER X-MAIL-CREATED-DATE"


class NotesUnavailable(MailboxNotFound):
    """The account has no IMAP notes mailbox."""


class ICloudNotes:
    """Read/write notes stored in the IMAP Notes folder."""

    def __init__(self, mail: ICloudMail, mailbox: str = "Notes") -> None:
        self._mail = mail
        self._mailbox = mailbox

    async def async_available(self) -> bool:
        return await self._mail.async_mailbox_exists(self._mailbox)

    async def _require(self) -> None:
        if not await self.async_available():
            raise NotesUnavailable(
                "The iCloud account has no IMAP 'Notes' mailbox. Modern iCloud Notes are not accessible with an app-specific password."
            )

    def _summary(self, item: Any, msg: Any) -> dict[str, Any]:
        note_uid = (msg.get("X-Universally-Unique-Identifier") or "").strip() or None
        created = _parse_date(msg.get("X-Mail-Created-Date"))
        return {
            "uid": item.uid,
            "note_id": note_uid,
            "title": _decode_header_value(msg.get("Subject")) or "(ohne Titel)",
            "created": created,
            "modified": _parse_date(msg.get("Date")) or created,
        }

    async def async_list(self, query: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        await self._require()

        async def op(client: aioimaplib.IMAP4_SSL) -> list[dict[str, Any]]:
            await self._mail._select(client, self._mailbox)  # noqa: SLF001
            response = await client.uid_search("ALL", charset=None)
            uids: list[int] = []
            for line in response.lines:
                if isinstance(line, (bytes, bytearray)):
                    text = bytes(line).decode(errors="replace")
                    if not text.upper().startswith("SEARCH"):
                        uids.extend(int(x) for x in text.split() if x.isdigit())
            if not uids:
                return []
            uids.sort(reverse=True)
            fetch_uids = uids if query else uids[:limit]
            response = await client.uid(
                "fetch", ",".join(map(str, fetch_uids)), f"(UID FLAGS BODY.PEEK[HEADER.FIELDS ({NOTE_HEADERS})])"
            )
            notes: list[dict[str, Any]] = []
            for item in parse_fetch(response.lines):
                if item.uid is None:
                    continue
                msg = email.message_from_bytes(item.literal(), policy=policy.compat32)
                notes.append(self._summary(item, msg))
            return notes

        notes = await self._mail._run(op)  # noqa: SLF001
        if query:
            q = query.lower()
            matched = [n for n in notes if q in n["title"].lower()]
            if len(matched) < limit:
                # search bodies of the remaining notes (bounded)
                for note in notes:
                    if note in matched or len(matched) >= limit:
                        continue
                    try:
                        full = await self.async_get(note["uid"])
                    except MessageNotFound:
                        continue
                    if q in (full.get("body") or "").lower():
                        matched.append(note)
            notes = matched
        notes.sort(key=lambda n: n.get("modified") or "", reverse=True)
        return notes[:limit]

    async def async_get(self, uid: int) -> dict[str, Any]:
        await self._require()
        item, msg = await self._mail.async_fetch_raw(self._mailbox, uid)
        result = self._summary(item, msg)
        body, ctype, _ = extract_body(msg)
        result["body"] = body
        return result

    def _build(self, title: str, body: str, note_id: str | None = None, created: datetime | None = None) -> bytes:
        msg = EmailMessage(policy=policy.SMTP)
        now = datetime.now(UTC)
        msg["From"] = self._mail.from_address
        msg["Subject"] = title
        msg["Date"] = format_datetime(now)
        msg["Message-ID"] = make_msgid(domain="icloud.com")
        msg["X-Uniform-Type-Identifier"] = "com.apple.mail-note"
        msg["X-Universally-Unique-Identifier"] = note_id or str(uuid.uuid4()).upper()
        msg["X-Mail-Created-Date"] = format_datetime(created or now)
        msg["Content-Transfer-Encoding"] = "quoted-printable"
        html = text_to_html(f"{title}\n{body}" if not body.startswith(title) else body)
        msg.set_content(html, subtype="html", cte="quoted-printable")
        return msg.as_bytes()

    async def async_create(self, title: str, body: str) -> dict[str, Any]:
        await self._require()
        raw = self._build(title, body)
        await self._mail.async_append(self._mailbox, raw, flags="\\Seen")
        notes = await self.async_list(limit=5)
        for note in notes:
            if note["title"] == title:
                return note
        return {"title": title, "created": datetime.now(UTC).isoformat(timespec="minutes")}

    async def async_update(self, uid: int, title: str | None = None, body: str | None = None) -> dict[str, Any]:
        await self._require()
        current = await self.async_get(uid)
        new_title = title if title is not None else current["title"]
        new_body = body if body is not None else current.get("body", "")
        created = None
        if current.get("created"):
            try:
                created = datetime.fromisoformat(current["created"])
            except ValueError:
                created = None
        raw = self._build(new_title, new_body, note_id=current.get("note_id"), created=created)
        await self._mail.async_append(self._mailbox, raw, flags="\\Seen")
        await self._mail.async_delete(self._mailbox, uid, permanent=True)
        notes = await self.async_list(limit=5)
        for note in notes:
            if note["title"] == new_title:
                return note
        return {"title": new_title}

    async def async_delete(self, uid: int) -> dict[str, Any]:
        await self._require()
        return await self._mail.async_delete(self._mailbox, uid, permanent=True)
