"""iCloud Mail access via IMAP (aioimaplib) and SMTP (aiosmtplib)."""

from __future__ import annotations

import asyncio
import base64
import email
import logging
import re
import ssl
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.utils import format_datetime, getaddresses, make_msgid, parsedate_to_datetime
from typing import Any

import aioimaplib
import aiosmtplib

from .util import UNTRUSTED_NOTICE, detect_injection, html_to_text, sanitize_text, text_to_html

_LOGGER = logging.getLogger(__name__)
_UIDVALIDITY_RE = re.compile(r"UIDVALIDITY (\d+)", re.IGNORECASE)
_HIGHESTMODSEQ_RE = re.compile(r"HIGHESTMODSEQ (\d+)", re.IGNORECASE)
_STATUS_ITEMS_RE = re.compile(r"\(([^()]*)\)\s*$")

_FETCH_START_RE = re.compile(rb"^\*?\s*(\d+) FETCH \((.*)$", re.DOTALL)
_LITERAL_RE = re.compile(rb"\{(\d+)\}\s*$")
_LIST_RE = re.compile(rb'^\((?P<flags>[^)]*)\)\s+(?P<delim>"[^"]*"|NIL)\s+(?P<name>.+)$')
_IDLE_RECONNECT_AFTER = 8 * 60
_DEFAULT_WINDOW = 500  # messages inspected when filtering client-side
MAX_BATCH = 500  # uids per STORE/MOVE/COPY command

HEADER_FIELDS = (
    "FROM TO CC SUBJECT DATE MESSAGE-ID IN-REPLY-TO REFERENCES CONTENT-TYPE "
    "LIST-UNSUBSCRIBE LIST-UNSUBSCRIBE-POST LIST-ID PRECEDENCE"
)


class MailError(Exception):
    """Generic mail error."""


class MailAuthError(MailError):
    """Login failed."""


class MailboxNotFound(MailError):
    """Mailbox not found."""


class MessageNotFound(MailError):
    """Message not found."""


# ------------------------------------------------------------- utf-7 names
def encode_utf7(name: str) -> str:
    """Encode a mailbox name using IMAP modified UTF-7."""
    out: list[str] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            data = "".join(buffer).encode("utf-16-be")
            b64 = base64.b64encode(data).decode("ascii").rstrip("=").replace("/", ",")
            out.append(f"&{b64}-")
            buffer.clear()

    for ch in name:
        code = ord(ch)
        if 0x20 <= code <= 0x7E:
            flush()
            out.append("&-" if ch == "&" else ch)
        else:
            buffer.append(ch)
    flush()
    return "".join(out)


def decode_utf7(name: str) -> str:
    """Decode an IMAP modified UTF-7 mailbox name."""
    result: list[str] = []
    i = 0
    while i < len(name):
        ch = name[i]
        if ch != "&":
            result.append(ch)
            i += 1
            continue
        end = name.find("-", i)
        if end < 0:
            result.append(name[i:])
            break
        chunk = name[i + 1 : end]
        if not chunk:
            result.append("&")
        else:
            b64 = chunk.replace(",", "/")
            b64 += "=" * (-len(b64) % 4)
            try:
                result.append(base64.b64decode(b64).decode("utf-16-be"))
            except Exception:  # noqa: BLE001
                result.append(name[i : end + 1])
        i = end + 1
    return "".join(result)


def quote_mailbox(name: str) -> str:
    encoded = encode_utf7(name)
    return '"' + encoded.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _decode_header_value(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:  # noqa: BLE001
        return value.strip()


def parse_message(data: bytes) -> Message:
    """Parse raw RFC 822 bytes with the modern (RFC 5322) header policy."""
    return email.message_from_bytes(data, policy=policy.default)


def _raw_values(msg: Message, name: str) -> list[str]:
    """Header values exactly as received, without the (sometimes crashing) structured parsing of the policy.

    The modern policy parses address headers on access; a header such as ``From: "`` makes the standard library
    raise IndexError there – also in ``get_all``. ``raw_items`` returns the stored strings untouched.
    """
    wanted = name.lower()
    return [str(value) for key, value in msg.raw_items() if key.lower() == wanted]


def header_text(msg: Message, name: str) -> str | None:
    """Return a decoded, unfolded header value regardless of the policy in use."""
    try:
        value = msg[name]
    except Exception:  # noqa: BLE001 - defective header
        value = None
    if value is None:
        raw = _raw_values(msg, name)
        text = _decode_header_value(raw[0]) if raw else None
        return " ".join(text.split()) or None if text else None
    text = str(value)
    if "=?" in text:
        text = _decode_header_value(text) or text
    return " ".join(text.split()) or None


def _addresses(msg: Message, header: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    try:
        values = msg.get_all(header, [])
        for value in values:
            addresses = getattr(value, "addresses", None)
            if addresses is None:
                raise AttributeError
            for addr in addresses:
                if not addr.addr_spec and not addr.display_name:
                    continue
                out.append({"name": addr.display_name or "", "email": addr.addr_spec})
        return out
    except Exception:  # noqa: BLE001 - fall back to the legacy parser on the raw header text
        out = []
        for name, addr in getaddresses(_raw_values(msg, header)):
            if not addr and not name:
                continue
            out.append({"name": _decode_header_value(name) or "", "email": addr})
        return out


def parse_date_header(value: str | None) -> datetime | None:
    """Parse a Date header into an aware datetime (None when missing or invalid)."""
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat(timespec="minutes")


@dataclass
class FetchItem:
    """One parsed FETCH response item."""

    seq: int
    uid: int | None = None
    flags: list[str] | None = None
    internaldate: str | None = None
    size: int | None = None
    literals: dict[str, bytes] | None = None  # section -> data

    def literal(self) -> bytes:
        """Return the first literal (header or body)."""
        if not self.literals:
            return b""
        return next(iter(self.literals.values()))


def parse_fetch(lines: list[Any]) -> list[FetchItem]:
    """Parse aioimaplib FETCH response lines (bytes with interleaved literals)."""
    items: list[FetchItem] = []
    current: FetchItem | None = None
    pending_section: str | None = None
    text_buffer = b""

    def finish(text: bytes) -> None:
        if current is None:
            return
        if m := re.search(rb"\bUID (\d+)", text):
            current.uid = int(m.group(1))
        if m := re.search(rb"FLAGS \(([^)]*)\)", text):
            current.flags = [f.decode(errors="replace") for f in m.group(1).split()]
        if m := re.search(rb'INTERNALDATE "([^"]+)"', text):
            current.internaldate = m.group(1).decode(errors="replace")
        if m := re.search(rb"RFC822\.SIZE (\d+)", text):
            current.size = int(m.group(1))

    for raw in lines:
        if isinstance(raw, bytearray):
            raw = bytes(raw)
        if not isinstance(raw, bytes):
            continue
        if pending_section is not None and current is not None:
            current.literals = current.literals or {}
            current.literals[pending_section] = raw
            pending_section = None
            continue
        start = _FETCH_START_RE.match(raw)
        if start:
            finish(text_buffer)
            if current is not None:
                items.append(current)
            current = FetchItem(seq=int(start.group(1)))
            text_buffer = start.group(2)
        elif current is not None:
            text_buffer += b" " + raw
        else:
            continue
        lit = _LITERAL_RE.search(text_buffer)
        if lit:
            head = text_buffer[: lit.start()].rstrip()
            sec = re.search(rb"(BODY\[[^\]]*\]|RFC822(?:\.\w+)?|BINARY\[[^\]]*\])\s*$", head)
            pending_section = sec.group(1).decode() if sec else f"literal{len(current.literals or {})}"
            text_buffer = head
    finish(text_buffer)
    if current is not None:
        items.append(current)
    return items


def _message_summary(item: FetchItem, msg: Message, mailbox: str) -> dict[str, Any]:
    flags = item.flags or []
    summary = _summary_fields(item, msg, mailbox, flags)
    warnings = detect_injection(summary["subject"], *(a.get("name") for a in summary["from"]))
    if warnings:
        summary["suspicious"] = True
        summary["warnings"] = warnings
    return summary


def _summary_fields(item: FetchItem, msg: Message, mailbox: str, flags: list[str]) -> dict[str, Any]:
    return {
        "uid": item.uid,
        "mailbox": mailbox,
        "subject": sanitize_text(header_text(msg, "Subject")),
        "from": _addresses(msg, "From"),
        "to": _addresses(msg, "To"),
        "cc": _addresses(msg, "Cc"),
        "date": _parse_date(header_text(msg, "Date")),
        "seen": "\\Seen" in flags,
        "flagged": "\\Flagged" in flags,
        "answered": "\\Answered" in flags,
        "size": item.size,
        "message_id": header_text(msg, "Message-ID"),
        "in_reply_to": header_text(msg, "In-Reply-To"),
        "newsletter": is_newsletter(msg),
    }


def is_newsletter(msg: Message) -> bool:
    """Bulk mail: has an unsubscribe link, a mailing list id or Precedence bulk/list."""
    if msg.get("List-Unsubscribe") or msg.get("List-Id"):
        return True
    return (header_text(msg, "Precedence") or "").strip().lower() in ("bulk", "list", "junk")


def list_unsubscribe(msg: Message) -> dict[str, Any] | None:
    """Parse List-Unsubscribe / List-Unsubscribe-Post (RFC 2369, RFC 8058)."""
    value = header_text(msg, "List-Unsubscribe")
    if not value:
        return None
    entries = re.findall(r"<\s*([^>\s]+)\s*>", value)
    mailto = [e for e in entries if e.lower().startswith("mailto:")]
    https = [e for e in entries if e.lower().startswith("https://")]
    post = (header_text(msg, "List-Unsubscribe-Post") or "").replace(" ", "").lower()
    return {
        "mailto": mailto[:3],
        "https": https[:3],
        "one_click": bool(https) and post == "list-unsubscribe=one-click",
    }


def iter_attachments(msg: Message) -> list[tuple[str, str, bytes]]:
    """Return (filename, content_type, payload) of every attachment."""
    found: list[tuple[str, str, bytes]] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        disposition = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if "attachment" in disposition or (filename and ctype not in ("text/plain", "text/html")):
            payload = part.get_payload(decode=True) or b""
            found.append((_decode_header_value(filename) or "", ctype, payload))
    return found


def raw_headers(data: bytes, limit: int = 4000) -> str:
    """Return the raw header block of a message (for diagnostics)."""
    head = data.split(b"\r\n\r\n", 1)[0] if b"\r\n\r\n" in data else data.split(b"\n\n", 1)[0]
    return head.decode("utf-8", errors="replace")[:limit]


def extract_body(msg: Message, prefer_html: bool = False) -> tuple[str, str, list[dict[str, Any]]]:
    """Return (text, content_type, attachments)."""
    attachments: list[dict[str, Any]] = []
    plain: str | None = None
    html: str | None = None
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        disposition = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if "attachment" in disposition or (filename and ctype not in ("text/plain", "text/html")):
            payload = part.get_payload(decode=True) or b""
            attachments.append(
                {"filename": _decode_header_value(filename) or "", "content_type": ctype, "size": len(payload)}
            )
            continue
        if ctype in ("text/plain", "text/html"):
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            try:
                text = payload.decode(charset, errors="replace")
            except LookupError:
                text = payload.decode("utf-8", errors="replace")
            if ctype == "text/plain" and plain is None:
                plain = text
            elif ctype == "text/html" and html is None:
                html = text
    if prefer_html and html is not None:
        return html, "text/html", attachments
    if plain is not None and plain.strip():
        return plain, "text/plain", attachments
    if html is not None:
        return html_to_text(html), "text/plain", attachments
    return "", "text/plain", attachments


class ICloudMail:
    """Serialised access to one IMAP connection plus SMTP sending."""

    def __init__(
        self,
        username: str,
        password: str,
        *,
        from_address: str,
        imap_host: str,
        imap_port: int,
        smtp_host: str,
        smtp_port: int,
        timeout: int = 30,
        ssl_context: ssl.SSLContext | None = None,
        shared: dict[str, Any] | None = None,
    ) -> None:
        self._username = username
        self._password = password
        self.from_address = from_address
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._timeout = timeout
        self._ssl_context = ssl_context
        self._client: aioimaplib.IMAP4_SSL | None = None
        self._selected: str | None = None
        self._last_used = 0.0
        self._lock = asyncio.Lock()
        # facts about the account that all connections of it share (the mailbox list)
        self._shared: dict[str, Any] = shared if shared is not None else {}
        self._uidvalidity: dict[str, int] = {}
        self._closing: set[asyncio.Task] = set()

    # ---------------------------------------------------------- connection
    async def _connect(self) -> aioimaplib.IMAP4_SSL:
        client = aioimaplib.IMAP4_SSL(
            host=self._imap_host, port=self._imap_port, timeout=self._timeout, ssl_context=self._ssl_context
        )
        try:
            await client.wait_hello_from_server()
            response = await client.login(self._username, self._password)
        except (TimeoutError, OSError, aioimaplib.Error, aioimaplib.Abort) as err:
            raise MailError(f"IMAP connection failed: {err}") from err
        if response.result != "OK":
            raise MailAuthError("IMAP login failed - check Apple ID and app-specific password")
        await self._learn_capabilities(client)
        self._selected = None
        self._last_used = time.monotonic()
        return client

    async def _learn_capabilities(self, client: aioimaplib.IMAP4_SSL) -> None:
        """What the server offers once logged in (servers often name more than before the login)."""
        try:
            await asyncio.wait_for(client.protocol.capability(), self._timeout)
        except Exception as err:  # noqa: BLE001 - the list from the greeting stays
            _LOGGER.debug("IMAP CAPABILITY after login failed: %s", err)
        self._shared["capabilities"] = sorted({str(c).upper() for c in client.protocol.capabilities or ()})

    @property
    def capabilities(self) -> list[str]:
        """The server's IMAP capabilities, as seen after the last login (empty before the first one)."""
        return list(self._shared.get("capabilities") or [])

    @property
    def condstore(self) -> bool:
        """The server keeps a change counter per mailbox (RFC 7162: CONDSTORE, or QRESYNC that includes it)."""
        caps = set(self.capabilities)
        return "CONDSTORE" in caps or "QRESYNC" in caps

    async def _ensure(self) -> aioimaplib.IMAP4_SSL:
        now = time.monotonic()
        if self._client is not None:
            state = self._client.get_state()
            if state in ("AUTH", "SELECTED") and now - self._last_used < _IDLE_RECONNECT_AFTER:
                return self._client
            self._discard()
        self._client = await self._connect()
        return self._client

    def _discard(self) -> None:
        """Forget an idle connection and log it out in the background.

        The server has usually closed it already, so waiting for the logout would only delay the caller.
        """
        client, self._client, self._selected = self._client, None, None
        if client is None:
            return
        task = asyncio.get_running_loop().create_task(self._quiet_logout(client))
        self._closing.add(task)
        task.add_done_callback(self._closing.discard)

    @staticmethod
    async def _quiet_logout(client: aioimaplib.IMAP4_SSL) -> None:
        try:
            await asyncio.wait_for(client.logout(), 5)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("IMAP logout of an idle connection failed (ignored)")

    async def _drop(self) -> None:
        client, self._client, self._selected = self._client, None, None
        if client is None:
            return
        try:
            await asyncio.wait_for(client.logout(), 5)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("IMAP logout failed (ignored)")

    async def async_close(self) -> None:
        async with self._lock:
            await self._drop()
        if self._closing:
            await asyncio.gather(*self._closing, return_exceptions=True)

    async def async_test_login(self) -> None:
        """Validate the credentials (used by the config flow)."""
        async with self._lock:
            client = await self._connect()
            self._client = client
            await self._drop()

    async def _run(self, func, *args, retry: bool = True):
        """Run an IMAP operation with one reconnect retry."""
        async with self._lock:
            try:
                client = await self._ensure()
                result = await func(client, *args)
                self._last_used = time.monotonic()
                return result
            except (MailAuthError, MailboxNotFound, MessageNotFound):
                raise
            except (TimeoutError, OSError, aioimaplib.Error, aioimaplib.Abort, MailError) as err:
                await self._drop()
                if not retry:
                    raise MailError(f"IMAP operation failed: {err}") from err
                _LOGGER.debug("IMAP operation failed, reconnecting: %s", err)
                client = await self._ensure()
                try:
                    result = await func(client, *args)
                except (TimeoutError, OSError, aioimaplib.Error, aioimaplib.Abort) as err2:
                    await self._drop()
                    raise MailError(f"IMAP operation failed: {err2}") from err2
                self._last_used = time.monotonic()
                return result

    async def _select(self, client: aioimaplib.IMAP4_SSL, mailbox: str) -> None:
        if self._selected == mailbox:
            return
        response = await client.select(quote_mailbox(mailbox))
        if response.result != "OK":
            self._selected = None
            raise MailboxNotFound(f"Mailbox '{mailbox}' not found or cannot be opened")
        self._selected = mailbox
        for line in response.lines:
            match = _UIDVALIDITY_RE.search(
                bytes(line).decode(errors="replace") if isinstance(line, (bytes, bytearray)) else str(line)
            )
            if match:
                self._uidvalidity[mailbox] = int(match.group(1))
                break

    # ---------------------------------------------------------- mailboxes
    async def async_mailboxes(self, force: bool = False) -> list[dict[str, Any]]:
        cached = self._shared.get("mailboxes")
        if cached is not None and not force:
            return cached

        async def op(client: aioimaplib.IMAP4_SSL) -> list[dict[str, Any]]:
            response = await client.list('""', '"*"')
            if response.result != "OK":
                raise MailError("LIST failed")
            boxes: list[dict[str, Any]] = []
            for line in response.lines:
                if not isinstance(line, (bytes, bytearray)):
                    continue
                m = _LIST_RE.match(bytes(line).strip())
                if not m:
                    continue
                name = m.group("name").decode("utf-8", errors="replace").strip()
                if name.startswith('"') and name.endswith('"'):
                    name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                flags = [f.decode() for f in m.group("flags").split()]
                if "\\Noselect" in flags or "\\NonExistent" in flags:
                    continue
                delim = m.group("delim").decode().strip('"')
                special = next(
                    (
                        f[1:].lower()
                        for f in flags
                        if f in ("\\Sent", "\\Trash", "\\Drafts", "\\Junk", "\\Archive", "\\All", "\\Flagged")
                    ),
                    None,
                )
                boxes.append(
                    {
                        "name": decode_utf7(name),
                        "delimiter": delim if delim != "NIL" else None,
                        "flags": flags,
                        "special_use": special,
                    }
                )
            return boxes

        boxes = await self._run(op)
        # iCloud fallbacks when SPECIAL-USE flags are missing
        fallbacks = {
            "sent": ("Sent Messages", "Sent"),
            "trash": ("Deleted Messages", "Trash"),
            "drafts": ("Drafts",),
            "junk": ("Junk", "Spam"),
        }
        for special, names in fallbacks.items():
            if any(b["special_use"] == special for b in boxes):
                continue
            for box in boxes:
                if box["name"] in names:
                    box["special_use"] = special
                    break
        self._shared["mailboxes"] = boxes
        return boxes

    async def async_special_mailbox(self, special: str) -> str | None:
        for box in await self.async_mailboxes():
            if box["special_use"] == special:
                return box["name"]
        return None

    async def async_mailbox_exists(self, name: str) -> bool:
        return any(b["name"] == name for b in await self.async_mailboxes())

    # ------------------------------------------------------------- search
    async def async_search(
        self,
        mailbox: str = "INBOX",
        *,
        query: str | None = None,
        sender: str | None = None,
        recipient: str | None = None,
        subject: str | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        unseen_only: bool = False,
        flagged_only: bool = False,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        criteria: list[str] = []
        local_filters: list[tuple[str, str]] = []

        def add_text(key: str, value: str | None) -> None:
            if not value:
                return
            value = value.strip()
            if value.isascii() and '"' not in value and "\\" not in value:
                criteria.extend([key, f'"{value}"'])
            else:
                local_filters.append((key, value.lower()))

        add_text("FROM", sender)
        add_text("TO", recipient)
        add_text("SUBJECT", subject)
        add_text("TEXT", query)
        if unseen_only:
            criteria.append("UNSEEN")
        if flagged_only:
            criteria.append("FLAGGED")
        if since:
            criteria.extend(["SINCE", since.strftime("%d-%b-%Y")])
        if before:
            criteria.extend(["BEFORE", before.strftime("%d-%b-%Y")])
        if not criteria:
            criteria.append("ALL")

        async def op(client: aioimaplib.IMAP4_SSL) -> list[dict[str, Any]]:
            await self._select(client, mailbox)
            response = await client.uid_search(*criteria, charset="utf-8")
            if response.result != "OK":
                response = await client.uid_search(*criteria, charset=None)
            if response.result != "OK":
                raise MailError(f"SEARCH failed: {response.lines}")
            uids: list[int] = []
            for line in response.lines:
                if isinstance(line, (bytes, bytearray)):
                    text = bytes(line).decode(errors="replace")
                    if text.upper().startswith("SEARCH"):
                        continue
                    uids.extend(int(x) for x in text.split() if x.isdigit())
            if not uids:
                return []
            uids.sort(reverse=True)
            window = uids[: max(limit * 4, _DEFAULT_WINDOW) if local_filters else limit]
            results = await self._fetch_summaries(client, mailbox, window)
            if local_filters:

                def keep(summary: dict[str, Any]) -> bool:
                    for key, needle in local_filters:
                        if key == "FROM":
                            hay = " ".join(f"{a['name']} {a['email']}" for a in summary["from"])
                        elif key == "TO":
                            hay = " ".join(f"{a['name']} {a['email']}" for a in summary["to"] + summary["cc"])
                        elif key == "SUBJECT":
                            hay = summary["subject"]
                        else:
                            hay = f"{summary['subject']} " + " ".join(
                                f"{a['name']} {a['email']}" for a in summary["from"] + summary["to"]
                            )
                        if needle not in hay.lower():
                            return False
                    return True

                results = [s for s in results if keep(s)]
            return results[:limit]

        return await self._run(op)

    async def _fetch_summaries(
        self, client: aioimaplib.IMAP4_SSL, mailbox: str, uids: list[int]
    ) -> list[dict[str, Any]]:
        if not uids:
            return []
        uid_set = ",".join(str(u) for u in uids)
        response = await client.uid(
            "fetch", uid_set, f"(UID FLAGS RFC822.SIZE BODY.PEEK[HEADER.FIELDS ({HEADER_FIELDS})])"
        )
        if response.result != "OK":
            raise MailError(f"FETCH failed: {response.lines[-1] if response.lines else ''}")
        summaries: list[dict[str, Any]] = []
        for item in parse_fetch(response.lines):
            if item.uid is None:
                continue
            msg = parse_message(item.literal())
            summaries.append(_message_summary(item, msg, mailbox))
        order = {uid: i for i, uid in enumerate(uids)}
        summaries.sort(key=lambda s: order.get(s["uid"], 1_000_000))
        return summaries

    async def async_search_uids(self, mailbox: str, criteria: list[str]) -> list[int]:
        """Return the uids matching IMAP search criteria (ascending)."""

        async def op(client: aioimaplib.IMAP4_SSL) -> list[int]:
            await self._select(client, mailbox)
            response = await client.uid_search(*criteria, charset=None)
            if response.result != "OK":
                raise MailError(f"SEARCH failed: {response.lines}")
            uids: list[int] = []
            for line in response.lines:
                if isinstance(line, (bytes, bytearray)):
                    text = bytes(line).decode(errors="replace")
                    if text.upper().startswith("SEARCH"):
                        continue
                    uids.extend(int(x) for x in text.split() if x.isdigit())
            return sorted(set(uids))

        return await self._run(op)

    async def async_new_uids(self, mailbox: str, after_uid: int) -> list[int]:
        """UIDs above ``after_uid`` – asks the server only for the new range instead of every message."""
        uids = await self.async_search_uids(mailbox, ["UID", f"{max(0, int(after_uid)) + 1}:*"])
        # "n:*" always includes the highest message, even when its uid is below n
        return [u for u in uids if u > after_uid]

    async def async_last_uid(self, mailbox: str) -> int:
        """Highest UID of a mailbox (0 when empty) – a cheap starting point for 'only new mail'."""
        uids = await self.async_search_uids(mailbox, ["UID", "*"])
        return max(uids) if uids else 0

    async def async_status(self, mailbox: str) -> dict[str, int]:
        """Counters of a mailbox: messages, unseen, uidnext, uidvalidity, and highestmodseq with CONDSTORE.

        STATUS answers without opening the mailbox. For the mailbox this connection has open, STATUS may be out of
        date (RFC 3501), so it is opened again and its unread messages are counted instead – with CONDSTORE as
        "SELECT mailbox (CONDSTORE)", the form that obliges the server to name HIGHESTMODSEQ.
        """
        names = "MESSAGES UNSEEN UIDNEXT UIDVALIDITY" + (" HIGHESTMODSEQ" if self.condstore else "")

        async def op(client: aioimaplib.IMAP4_SSL) -> dict[str, int]:
            if self._selected == mailbox:
                self._selected = None
                target = quote_mailbox(mailbox) + (" (CONDSTORE)" if self.condstore else "")
                response = await client.select(target)
                if response.result != "OK":
                    raise MailboxNotFound(f"Mailbox '{mailbox}' not found or cannot be opened")
                self._selected = mailbox
                out: dict[str, int] = {}
                for line in response.lines:
                    text = bytes(line).decode(errors="replace") if isinstance(line, (bytes, bytearray)) else str(line)
                    upper = text.upper()
                    if upper.endswith(" EXISTS") and text.split()[0].isdigit():
                        out["messages"] = int(text.split()[0])
                    for key, regex in (("uidvalidity", _UIDVALIDITY_RE), ("highestmodseq", _HIGHESTMODSEQ_RE)):
                        if m := regex.search(text):
                            out[key] = int(m.group(1))
                    if m := re.search(r"UIDNEXT (\d+)", text, re.IGNORECASE):
                        out["uidnext"] = int(m.group(1))
                unseen = await client.uid_search("UNSEEN", charset=None)
                if unseen.result != "OK":
                    raise MailError(f"SEARCH failed: {unseen.lines}")
                out["unseen"] = sum(
                    len([x for x in bytes(line).decode(errors="replace").split() if x.isdigit()])
                    for line in unseen.lines
                    if isinstance(line, (bytes, bytearray)) and not bytes(line).upper().startswith(b"SEARCH")
                )
                return out
            response = await client.status(quote_mailbox(mailbox), f"({names})")
            if response.result != "OK":
                raise MailboxNotFound(f"Mailbox '{mailbox}' not found or cannot be opened")
            for line in response.lines:
                text = bytes(line).decode(errors="replace") if isinstance(line, (bytes, bytearray)) else str(line)
                if m := _STATUS_ITEMS_RE.search(text):
                    tokens = m.group(1).split()
                    return {k.lower(): int(v) for k, v in zip(tokens[::2], tokens[1::2], strict=False) if v.isdigit()}
            raise MailError(f"STATUS gave no counters: {response.lines}")

        return await self._run(op)

    async def async_flags(
        self, mailbox: str, uids: list[int] | None = None, *, changed_since: int | None = None
    ) -> dict[int, list[str]]:
        """Flags of messages by UID: of the given ones, or (CONDSTORE) of all whose flags changed since a modseq.

        A message missing from the answer to a list of UIDs is no longer in the mailbox (moved or deleted).
        """
        if changed_since is not None and not self.condstore:
            raise MailError("The server does not support CONDSTORE")
        if changed_since is None and not uids:
            return {}
        uid_set = "1:*" if changed_since is not None else ",".join(str(int(u)) for u in uids or [])
        parts = "(UID FLAGS)" + (f" (CHANGEDSINCE {int(changed_since)})" if changed_since is not None else "")

        async def op(client: aioimaplib.IMAP4_SSL) -> dict[int, list[str]]:
            await self._select(client, mailbox)
            response = await client.uid("fetch", uid_set, parts)
            if response.result != "OK":
                raise MailError(f"FETCH failed: {response.lines[-1] if response.lines else ''}")
            return {item.uid: list(item.flags or []) for item in parse_fetch(response.lines) if item.uid is not None}

        return await self._run(op)

    def uidvalidity(self, mailbox: str) -> int | None:
        """UIDVALIDITY seen when the mailbox was last opened; a change means all UIDs were renumbered."""
        return self._uidvalidity.get(mailbox)

    async def async_summaries(self, mailbox: str, uids: list[int]) -> list[dict[str, Any]]:
        """Return header summaries for the given uids."""
        if not uids:
            return []

        async def op(client: aioimaplib.IMAP4_SSL) -> list[dict[str, Any]]:
            await self._select(client, mailbox)
            return await self._fetch_summaries(client, mailbox, list(uids))

        return await self._run(op)

    async def async_recent(
        self, mailbox: str = "INBOX", limit: int = 25, unseen_only: bool = False
    ) -> list[dict[str, Any]]:
        return await self.async_search(mailbox, unseen_only=unseen_only, limit=limit)

    # ---------------------------------------------------------- messages
    async def async_fetch_raw(self, mailbox: str, uid: int) -> tuple[FetchItem, Message]:
        async def op(client: aioimaplib.IMAP4_SSL) -> tuple[FetchItem, Message]:
            await self._select(client, mailbox)
            response = await client.uid("fetch", str(uid), "(UID FLAGS RFC822.SIZE BODY.PEEK[])")
            if response.result != "OK":
                raise MailError("FETCH failed")
            items = [i for i in parse_fetch(response.lines) if i.uid == uid]
            if not items or not items[0].literal():
                raise MessageNotFound(f"Message {uid} not found in '{mailbox}'")
            item = items[0]
            return item, parse_message(item.literal())

        return await self._run(op)

    async def async_get_message(
        self,
        mailbox: str,
        uid: int,
        *,
        prefer_html: bool = False,
        max_chars: int = 20000,
        include_headers: bool = False,
    ) -> dict[str, Any]:
        item, msg = await self.async_fetch_raw(mailbox, uid)
        result = _message_summary(item, msg, mailbox)
        body, ctype, attachments = extract_body(msg, prefer_html=prefer_html)
        body = sanitize_text(body)
        truncated = len(body) > max_chars
        warnings = list(result.get("warnings") or [])
        warnings += [w for w in detect_injection(body[: max(max_chars, 20000)]) if w not in warnings]
        if warnings:
            result["suspicious"] = True
            result["warnings"] = warnings
        result["content_notice"] = UNTRUSTED_NOTICE
        result.update(
            {
                "body": body[:max_chars],
                "body_content_type": ctype,
                "body_truncated": truncated,
                "attachments": attachments,
                "references": header_text(msg, "References"),
                "unsubscribe": list_unsubscribe(msg),
            }
        )
        if include_headers:
            result["raw_headers"] = raw_headers(item.literal())
        return result

    @staticmethod
    def _uid_set(uids: int | list[int]) -> tuple[list[int], str]:
        """Normalise a uid or list of uids into a sorted list and an IMAP uid set."""
        values = sorted({int(u) for u in ([uids] if isinstance(uids, int) else uids)})
        if not values:
            raise MailError("No message uids given")
        if len(values) > MAX_BATCH:
            raise MailError(f"Too many messages in one call (max {MAX_BATCH})")
        return values, ",".join(str(u) for u in values)

    async def async_set_flags(
        self, mailbox: str, uids: int | list[int], *, seen: bool | None = None, flagged: bool | None = None
    ) -> dict[str, Any]:
        """Set/clear flags on one or many messages with a single STORE per flag."""
        values, uid_set = self._uid_set(uids)

        async def op(client: aioimaplib.IMAP4_SSL) -> dict[str, Any]:
            await self._select(client, mailbox)
            for flag, value in (("\\Seen", seen), ("\\Flagged", flagged)):
                if value is None:
                    continue
                response = await client.uid(
                    "store", uid_set, "+FLAGS.SILENT" if value else "-FLAGS.SILENT", f"({flag})"
                )
                if response.result != "OK":
                    raise MailError(f"STORE failed: {response.lines}")
            return {"uids": values, "count": len(values), "mailbox": mailbox, "seen": seen, "flagged": flagged}

        return await self._run(op)

    async def async_move(self, mailbox: str, uids: int | list[int], target: str) -> dict[str, Any]:
        """Move one or many messages with a single MOVE (or COPY+STORE+EXPUNGE)."""
        if not await self.async_mailbox_exists(target):
            raise MailboxNotFound(f"Target mailbox '{target}' not found")
        values, uid_set = self._uid_set(uids)

        async def op(client: aioimaplib.IMAP4_SSL) -> dict[str, Any]:
            await self._select(client, mailbox)
            if client.has_capability("MOVE"):
                response = await client.uid("move", uid_set, quote_mailbox(target))
                if response.result != "OK":
                    raise MailError(f"MOVE failed: {response.lines}")
            else:
                response = await client.uid("copy", uid_set, quote_mailbox(target))
                if response.result != "OK":
                    raise MailError(f"COPY failed: {response.lines}")
                await client.uid("store", uid_set, "+FLAGS.SILENT", "(\\Deleted)")
                await client.expunge()
            return {"uids": values, "count": len(values), "from_mailbox": mailbox, "to_mailbox": target}

        return await self._run(op)

    async def async_delete(self, mailbox: str, uids: int | list[int], permanent: bool = False) -> dict[str, Any]:
        """Move messages to the trash (or expunge them) in one round trip."""
        trash = await self.async_special_mailbox("trash")
        if not permanent and trash and trash != mailbox:
            result = await self.async_move(mailbox, uids, trash)
            result["action"] = "moved_to_trash"
            return result
        values, uid_set = self._uid_set(uids)

        async def op(client: aioimaplib.IMAP4_SSL) -> dict[str, Any]:
            await self._select(client, mailbox)
            response = await client.uid("store", uid_set, "+FLAGS.SILENT", "(\\Deleted)")
            if response.result != "OK":
                raise MailError(f"STORE failed: {response.lines}")
            await client.expunge()
            return {"uids": values, "count": len(values), "mailbox": mailbox, "action": "deleted"}

        return await self._run(op)

    async def async_append(self, mailbox: str, message: bytes, flags: str | None = "\\Seen") -> None:
        async def op(client: aioimaplib.IMAP4_SSL) -> None:
            response = await client.append(message, mailbox=quote_mailbox(mailbox), flags=flags)
            if response.result != "OK":
                raise MailError(f"APPEND failed: {response.lines}")

        await self._run(op)

    # --------------------------------------------------------------- send
    async def async_send(
        self,
        *,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        html: bool = False,
        reply_to_mailbox: str | None = None,
        reply_to_uid: int | None = None,
    ) -> dict[str, Any]:
        if not to and not cc and not bcc:
            raise MailError("At least one recipient is required")
        msg = EmailMessage(policy=policy.SMTP)
        msg["From"] = self.from_address
        if to:
            msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg["Date"] = format_datetime(datetime.now(UTC))
        msg["Message-ID"] = make_msgid(domain=self.from_address.split("@")[-1] or "icloud.com")
        quoted: str | None = None
        if reply_to_uid is not None:
            _, original = await self.async_fetch_raw(reply_to_mailbox or "INBOX", reply_to_uid)
            orig_id = header_text(original, "Message-ID") or ""
            if orig_id:
                msg["In-Reply-To"] = orig_id
                refs = header_text(original, "References") or ""
                msg["References"] = f"{refs} {orig_id}".strip()
            if not subject:
                orig_subject = header_text(original, "Subject") or ""
                del msg["Subject"]
                msg["Subject"] = orig_subject if orig_subject.lower().startswith("re:") else f"Re: {orig_subject}"
            orig_text, _, _ = extract_body(original)
            if orig_text:
                quoted = "\n".join(f"> {line}" for line in orig_text.splitlines()[:200])
        if html:
            msg.set_content(html_to_text(body))
            msg.add_alternative(body, subtype="html")
        else:
            text = body if quoted is None else f"{body}\n\n{quoted}"
            msg.set_content(text)
            msg.add_alternative(text_to_html(text), subtype="html")
        recipients = [*to, *(cc or []), *(bcc or [])]
        try:
            await aiosmtplib.send(
                msg,
                hostname=self._smtp_host,
                port=self._smtp_port,
                start_tls=True,
                username=self._username,
                password=self._password,
                recipients=recipients,
                timeout=self._timeout,
                tls_context=self._ssl_context,
            )
        except aiosmtplib.SMTPAuthenticationError as err:
            raise MailAuthError(f"SMTP authentication failed: {err}") from err
        except (aiosmtplib.SMTPException, OSError, TimeoutError) as err:
            raise MailError(f"Sending failed: {err}") from err
        sent_box = await self.async_special_mailbox("sent")
        if sent_box:
            try:
                await self.async_append(sent_box, msg.as_bytes())
            except MailError as err:
                _LOGGER.debug("Could not store sent message: %s", err)
        if reply_to_uid is not None:
            try:

                async def op(client: aioimaplib.IMAP4_SSL) -> None:
                    await self._select(client, reply_to_mailbox or "INBOX")
                    await client.uid("store", str(reply_to_uid), "+FLAGS.SILENT", "(\\Answered)")

                await self._run(op)
            except MailError:
                pass
        return {
            "message_id": msg["Message-ID"],
            "to": to,
            "cc": cc or [],
            "bcc": bcc or [],
            "subject": msg["Subject"],
            "stored_in": sent_box,
        }
