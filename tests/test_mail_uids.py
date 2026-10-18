"""Incremental UID search and UIDVALIDITY tracking."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.friedafetch.mail import ICloudMail


def _mail() -> ICloudMail:
    return ICloudMail(
        "u@icloud.com", "pw", from_address="u@icloud.com", imap_host="h", imap_port=993, smtp_host="s", smtp_port=587
    )


async def test_new_uids_asks_for_the_range_only() -> None:
    mail = _mail()
    mail.async_search_uids = AsyncMock(return_value=[41])  # "n:*" returns the highest mail even if it is old
    assert await mail.async_new_uids("INBOX", 41) == []
    mail.async_search_uids.assert_awaited_once_with("INBOX", ["UID", "42:*"])
    mail.async_search_uids = AsyncMock(return_value=[42, 43])
    assert await mail.async_new_uids("INBOX", 41) == [42, 43]
    mail.async_search_uids = AsyncMock(return_value=[7, 9])
    assert await mail.async_last_uid("INBOX") == 9
    mail.async_search_uids.assert_awaited_once_with("INBOX", ["UID", "*"])
    mail.async_search_uids = AsyncMock(return_value=[])
    assert await mail.async_last_uid("INBOX") == 0


async def test_select_remembers_uidvalidity() -> None:
    mail = _mail()
    client = SimpleNamespace(
        select=AsyncMock(
            return_value=SimpleNamespace(
                result="OK", lines=[b"FLAGS (\\Seen)", b"OK [UIDVALIDITY 1234567] UIDs valid", b"OK [UIDNEXT 99]"]
            )
        )
    )
    assert mail.uidvalidity("INBOX") is None
    await mail._select(client, "INBOX")  # noqa: SLF001
    assert mail.uidvalidity("INBOX") == 1234567
