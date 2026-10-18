"""The in-memory contacts cache keeps every vCard encrypted (AES-GCM, per-process key)."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.exceptions import InvalidTag

from custom_components.friedafetch.carddav_client import NS_CARDDAV, AddressBookInfo, ICloudCardDav


def _card(i: int) -> str:
    return (
        "BEGIN:VCARD\r\nVERSION:3.0\r\n"
        f"UID:UID-{i}\r\nFN:Erika Musterfrau {i}\r\nN:Musterfrau;Erika {i};;;\r\n"
        f"EMAIL;TYPE=INTERNET:erika{i}@example.com\r\nTEL;TYPE=CELL:+49 170 {i:07d}\r\nEND:VCARD\r\n"
    )


def _response(i: int) -> SimpleNamespace:
    data = _card(i)
    return SimpleNamespace(
        href=f"/book/{i}.vcf", etag=f'"{i}"', text=lambda ns, name, d=data: d if ns == NS_CARDDAV else None
    )


def _client(count: int) -> tuple[ICloudCardDav, AddressBookInfo]:
    client = ICloudCardDav(MagicMock(), "https://contacts.example/")
    book = AddressBookInfo(id="card", href="/book/", name="Kontakte")
    client._ingest(book, [_response(i) for i in range(count)])  # noqa: SLF001
    client.async_sync = AsyncMock(return_value=list(book.records.values()))
    return client, book


async def test_cache_holds_no_readable_contact_data() -> None:
    client, book = _client(3)
    record = book.records["/book/1.vcf"]
    assert record.uid == "UID-1"
    assert b"Musterfrau" not in record._sealed and b"erika1@" not in record._sealed  # noqa: SLF001
    assert "Musterfrau" not in repr(record) and "erika" not in repr(book)
    assert record.vcard.full_name == "Erika Musterfrau 1"  # decrypts on demand

    found = await client.async_search("erika1@", limit=5)
    assert [c["uid"] for c in found] == ["UID-1"]
    assert (await client.async_get("uid-2"))["uid"] == "UID-2"


async def test_ciphertext_is_bound_to_key_and_record() -> None:
    _, book = _client(2)
    one, two = book.records["/book/0.vcf"], book.records["/book/1.vcf"]
    other_process, _ = _client(1)
    with pytest.raises(InvalidTag):  # another key (e.g. after a restart) cannot read it
        other_process._sealer.open(one._sealed, one.href.encode())  # noqa: SLF001
    with pytest.raises(InvalidTag):  # a blob moved to another record is rejected
        two.sealer.open(one._sealed, two.href.encode())  # noqa: SLF001


async def test_update_writes_back_encrypted() -> None:
    client, book = _client(1)
    client._dav.put = AsyncMock(return_value='"new"')  # noqa: SLF001
    result = await client.async_update("UID-0", {"full_name": "Erika Neu"})
    record = book.records["/book/0.vcf"]
    assert result["full_name"] == "Erika Neu" and record.etag == '"new"'
    assert record.vcard.full_name == "Erika Neu" and b"Erika Neu" not in record._sealed  # noqa: SLF001


async def test_search_stays_fast_with_many_contacts() -> None:
    client, _ = _client(2000)
    start = time.perf_counter()
    found = await client.async_search("musterfrau 1999", limit=5)
    elapsed = time.perf_counter() - start
    assert found and found[0]["uid"] == "UID-1999"
    assert elapsed < 2.0, f"search over 2000 encrypted contacts took {elapsed:.2f}s"
