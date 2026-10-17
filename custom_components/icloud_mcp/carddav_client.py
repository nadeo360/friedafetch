"""iCloud CardDAV client (contacts)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlsplit
from xml.sax.saxutils import escape as xml_escape

from .dav import NS_CARDDAV, NS_CS, NS_DAV, DavClient, DavError, DavResponse
from .vcard import VCard, escape_text

_LOGGER = logging.getLogger(__name__)

_MULTIGET_CHUNK = 50
_ADDRESSBOOK_CACHE_TTL = 600
_SYNC_MIN_INTERVAL = 20  # seconds between ctag checks


class ContactError(Exception):
    """Contact operation failed."""


class ContactNotFound(ContactError):
    """Contact not found."""


@dataclass
class AddressBookInfo:
    """A CardDAV address book collection."""

    id: str
    href: str
    name: str
    ctag: str | None = None
    records: dict[str, ContactRecord] = field(default_factory=dict)  # href -> record
    last_sync: float = 0.0


@dataclass
class ContactRecord:
    """A vCard resource with its server location."""

    href: str
    etag: str | None
    vcard: VCard
    addressbook: AddressBookInfo

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        data = self.vcard.to_dict(include_raw=include_raw)
        data["etag"] = self.etag
        data["addressbook_id"] = self.addressbook.id
        return data


def apply_contact_fields(vcard: VCard, fields: dict[str, Any]) -> None:
    """Apply tool-level fields to a vCard (lists replace, scalars overwrite)."""
    name_keys = ("given_name", "family_name", "additional_names", "prefix", "suffix", "full_name")
    if any(k in fields for k in name_keys):
        vcard.set_name(
            given=fields.get("given_name"),
            family=fields.get("family_name"),
            additional=fields.get("additional_names"),
            prefix=fields.get("prefix"),
            suffix=fields.get("suffix"),
            full_name=fields.get("full_name"),
        )
    if "nickname" in fields:
        _set_or_remove(vcard, "NICKNAME", fields["nickname"])
    if "title" in fields:
        _set_or_remove(vcard, "TITLE", fields["title"])
    if "note" in fields:
        _set_or_remove(vcard, "NOTE", fields["note"])
    if "birthday" in fields:
        value = fields["birthday"]
        if value:
            vcard.set_single("BDAY", str(value).strip(), {"VALUE": ["date"]})
        else:
            vcard.remove_all("BDAY")
    if "organization" in fields or "department" in fields:
        existing = vcard.get("ORG")
        comps = existing.components if existing else []
        org = fields.get("organization", comps[0] if comps else "")
        dept = fields.get("department", comps[1] if len(comps) > 1 else "")
        if org or dept:
            vcard.set_single("ORG", ";".join(escape_text(c or "") for c in (org, dept) if c is not None))
        else:
            vcard.remove_all("ORG")
    for key, prop in (("emails", "EMAIL"), ("phones", "TEL"), ("urls", "URL")):
        if key not in fields:
            continue
        vcard.remove_all(prop)
        for item in fields[key] or []:
            if isinstance(item, str):
                value, label = item, None
            else:
                value = str(item.get("value", "")).strip()
                label = item.get("label") or item.get("type")
            if value:
                vcard.add_typed(prop, value, label)
    if "addresses" in fields:
        vcard.remove_all("ADR")
        for addr in fields["addresses"] or []:
            if isinstance(addr, dict) and any(v for k, v in addr.items() if k not in ("label", "type")):
                vcard.add_address(addr)
    if not vcard.get("FN"):
        # FN is mandatory in vCard 3.0 - derive something sensible
        org = vcard.get("ORG")
        email = vcard.get("EMAIL")
        fallback = (org.components[0] if org and org.components else None) or (email.text if email else "Unbekannt")
        vcard.set_single("FN", escape_text(fallback))


def _set_or_remove(vcard: VCard, prop: str, value: Any) -> None:
    if value is None or value == "":
        vcard.remove_all(prop)
    else:
        vcard.set_single(prop, escape_text(str(value)))


class ICloudCardDav:
    """Async CardDAV access with an ETag-based local cache."""

    def __init__(self, dav: DavClient, base_url: str) -> None:
        self._dav = dav
        self._base_url = base_url
        self._principal: str | None = None
        self._home: str | None = None
        self._books: list[AddressBookInfo] = []
        self._books_fetched = 0.0

    async def async_discover(self) -> str:
        if self._home:
            return self._home
        self._principal = await self._dav.current_user_principal(self._base_url)
        self._home = await self._dav.home_set(self._principal, NS_CARDDAV, "addressbook-home-set")
        _LOGGER.debug("CardDAV home: %s", self._home)
        return self._home

    async def async_addressbooks(self, force: bool = False) -> list[AddressBookInfo]:
        now = time.monotonic()
        if not force and self._books and now - self._books_fetched < _ADDRESSBOOK_CACHE_TTL:
            return self._books
        home = await self.async_discover()
        responses = await self._dav.propfind(
            home,
            [(NS_DAV, "displayname"), (NS_DAV, "resourcetype"), (NS_CS, "getctag")],
            depth="1",
        )
        books: list[AddressBookInfo] = []
        existing = {b.href: b for b in self._books}
        for resp in responses:
            if not resp.has_resourcetype(NS_CARDDAV, "addressbook"):
                continue
            href = resp.href if resp.href.endswith("/") else resp.href + "/"
            book_id = urlsplit(href).path.rstrip("/").rsplit("/", 1)[-1]
            if href in existing:
                book = existing[href]
                book.name = resp.text(NS_DAV, "displayname") or book_id
            else:
                book = AddressBookInfo(id=book_id, href=href, name=resp.text(NS_DAV, "displayname") or book_id)
            books.append(book)
        if not books:
            raise ContactError("No address book found in iCloud account")
        self._books = books
        self._books_fetched = now
        return books

    # ---------------------------------------------------------------- sync
    async def async_sync(self, force: bool = False) -> list[ContactRecord]:
        """Synchronise the local cache with the server and return all records."""
        books = await self.async_addressbooks()
        for book in books:
            await self._sync_book(book, force)
        return [rec for book in books for rec in book.records.values()]

    async def _sync_book(self, book: AddressBookInfo, force: bool) -> None:
        now = time.monotonic()
        if not force and book.records and now - book.last_sync < _SYNC_MIN_INTERVAL:
            return
        ctag_resp = await self._dav.propfind(book.href, [(NS_CS, "getctag")], depth="0")
        ctag = ctag_resp[0].text(NS_CS, "getctag") if ctag_resp else None
        if not force and ctag and ctag == book.ctag and book.records:
            book.last_sync = now
            return
        listing = await self._dav.propfind(book.href, [(NS_DAV, "getetag"), (NS_DAV, "resourcetype")], depth="1")
        server: dict[str, str | None] = {}
        for resp in listing:
            if resp.has_resourcetype(NS_DAV, "collection"):
                continue
            if not resp.path.lower().endswith(".vcf") and resp.etag is None:
                continue
            server[resp.href] = resp.etag
        to_fetch = [
            href
            for href, etag in server.items()
            if href not in book.records or book.records[href].etag != etag or etag is None
        ]
        for href in list(book.records):
            if href not in server:
                del book.records[href]
        for i in range(0, len(to_fetch), _MULTIGET_CHUNK):
            chunk = to_fetch[i : i + _MULTIGET_CHUNK]
            await self._multiget(book, chunk)
        book.ctag = ctag
        book.last_sync = time.monotonic()

    async def _multiget(self, book: AddressBookInfo, hrefs: list[str]) -> None:
        href_xml = "".join(f"<D:href>{xml_escape(urlsplit(h).path)}</D:href>" for h in hrefs)
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<C:addressbook-multiget xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">'
            "<D:prop><D:getetag/><C:address-data/></D:prop>"
            f"{href_xml}</C:addressbook-multiget>"
        )
        responses = await self._dav.report(book.href, body, depth="1")
        self._ingest(book, responses)

    def _ingest(self, book: AddressBookInfo, responses: list[DavResponse]) -> None:
        for resp in responses:
            data = resp.text(NS_CARDDAV, "address-data")
            if not data:
                continue
            try:
                vcard = VCard.parse(data)
            except ValueError:
                continue
            book.records[resp.href] = ContactRecord(href=resp.href, etag=resp.etag, vcard=vcard, addressbook=book)

    # --------------------------------------------------------------- read
    async def async_search(self, query: str | None, limit: int = 50) -> list[dict[str, Any]]:
        records = await self.async_sync()
        q = (query or "").strip()
        matches = [r for r in records if r.vcard.matches(q)] if q else list(records)
        matches.sort(key=lambda r: (r.vcard.full_name or "").lower())
        return [r.to_dict() for r in matches[:limit]]

    async def _find(self, uid: str) -> ContactRecord:
        wanted = uid.strip()
        for attempt in (False, True):
            records = await self.async_sync(force=attempt)
            for rec in records:
                if rec.vcard.uid and rec.vcard.uid.lower() == wanted.lower():
                    return rec
        raise ContactNotFound(f"Contact '{uid}' not found")

    async def async_get(self, uid: str) -> dict[str, Any]:
        return (await self._find(uid)).to_dict()

    # -------------------------------------------------------------- write
    async def async_create(self, fields: dict[str, Any], addressbook_id: str | None = None) -> dict[str, Any]:
        books = await self.async_addressbooks()
        book = books[0]
        if addressbook_id:
            book = next((b for b in books if b.id == addressbook_id or b.name == addressbook_id), None)
            if book is None:
                raise ContactError(f"Address book '{addressbook_id}' not found")
        vcard = VCard()
        uid = str(uuid.uuid4()).upper()
        vcard.set_single("UID", uid)
        apply_contact_fields(vcard, fields)
        href = f"{book.href}{quote(uid, safe='')}.vcf"
        etag = await self._dav.put(href, vcard.serialize(), "text/vcard; charset=utf-8", create=True)
        record = ContactRecord(href=href, etag=etag, vcard=vcard, addressbook=book)
        book.records[href] = record
        book.ctag = None  # force re-check on next sync
        return record.to_dict()

    async def async_update(self, uid: str, fields: dict[str, Any]) -> dict[str, Any]:
        record = await self._find(uid)
        apply_contact_fields(record.vcard, fields)
        try:
            etag = await self._dav.put(
                record.href, record.vcard.serialize(), "text/vcard; charset=utf-8", etag=record.etag
            )
        except DavError:
            record.addressbook.ctag = None
            raise
        record.etag = etag
        record.addressbook.ctag = None
        return record.to_dict()

    async def async_delete(self, uid: str) -> None:
        record = await self._find(uid)
        await self._dav.delete(record.href, etag=record.etag)
        record.addressbook.records.pop(record.href, None)
        record.addressbook.ctag = None
