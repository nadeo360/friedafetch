"""Incremental UID search and UIDVALIDITY tracking."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.friedafetch.mail import ICloudMail, MailError


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


def _fake_client(caps: set[str], **commands) -> SimpleNamespace:
    protocol = SimpleNamespace(capabilities=set(caps), capability=AsyncMock())
    return SimpleNamespace(protocol=protocol, get_state=lambda: "AUTH", **commands)


async def _with(mail: ICloudMail, client: SimpleNamespace) -> None:
    mail._ensure = AsyncMock(return_value=client)  # noqa: SLF001
    await mail._learn_capabilities(client)  # noqa: SLF001


async def test_capabilities_after_login_and_condstore() -> None:
    mail = _mail()
    assert mail.capabilities == [] and mail.condstore is False
    await _with(mail, _fake_client({"IMAP4rev1", "condstore", "IDLE"}))
    assert mail.capabilities == ["CONDSTORE", "IDLE", "IMAP4REV1"] and mail.condstore is True
    await _with(mail, _fake_client({"IMAP4rev1", "QRESYNC"}))
    assert mail.condstore is True  # QRESYNC includes CONDSTORE
    await _with(mail, _fake_client({"IMAP4rev1", "IDLE"}))
    assert mail.condstore is False


async def test_status_without_and_with_the_open_mailbox() -> None:
    mail = _mail()
    status = AsyncMock(
        return_value=SimpleNamespace(
            result="OK",
            lines=[b'"INBOX" (MESSAGES 12 UNSEEN 3 UIDNEXT 120 UIDVALIDITY 77 HIGHESTMODSEQ 9001)', b"STATUS done"],
        )
    )
    client = _fake_client({"IMAP4rev1", "CONDSTORE"}, status=status)
    await _with(mail, client)
    assert await mail.async_status("INBOX") == {
        "messages": 12,
        "unseen": 3,
        "uidnext": 120,
        "uidvalidity": 77,
        "highestmodseq": 9001,
    }
    assert "HIGHESTMODSEQ" in status.await_args.args[1]

    # the open mailbox: opened again and its unread ones counted (STATUS may be stale there)
    mail._selected = "INBOX"  # noqa: SLF001
    client.select = AsyncMock(
        return_value=SimpleNamespace(
            result="OK",
            lines=[b"12 EXISTS", b"OK [UIDVALIDITY 77] ok", b"OK [UIDNEXT 120] ok", b"OK [HIGHESTMODSEQ 9002] ok"],
        )
    )
    client.uid_search = AsyncMock(return_value=SimpleNamespace(result="OK", lines=[b"5 9", b"SEARCH completed"]))
    assert await mail.async_status("INBOX") == {
        "messages": 12,
        "uidvalidity": 77,
        "uidnext": 120,
        "highestmodseq": 9002,
        "unseen": 2,
    }
    assert client.select.await_args.args == ('"INBOX" (CONDSTORE)',)  # obliges the server to name HIGHESTMODSEQ


async def test_flags_of_messages_and_changes_since() -> None:
    mail = _mail()
    uid = AsyncMock(
        return_value=SimpleNamespace(
            result="OK",
            lines=[b"* 1 FETCH (UID 5 FLAGS (\\Seen) MODSEQ (9010))", b"* 2 FETCH (UID 9 FLAGS ())", b"FETCH done"],
        )
    )
    client = _fake_client({"IMAP4rev1"}, uid=uid, select=AsyncMock(return_value=SimpleNamespace(result="OK", lines=[])))
    await _with(mail, client)
    assert await mail.async_flags("INBOX", [5, 9, 11]) == {5: ["\\Seen"], 9: []}  # 11 is gone
    assert uid.await_args.args == ("fetch", "5,9,11", "(UID FLAGS)")
    with pytest.raises(MailError):  # no CONDSTORE: no changes-only query
        await mail.async_flags("INBOX", changed_since=9000)
    await _with(mail, _fake_client({"CONDSTORE"}, uid=uid, select=client.select))
    await mail.async_flags("INBOX", changed_since=9000)
    assert uid.await_args.args == ("fetch", "1:*", "(UID FLAGS) (CHANGEDSINCE 9000)")


async def test_status_opens_plainly_when_select_condstore_is_refused() -> None:
    mail = _mail()
    answers = [
        SimpleNamespace(result="BAD", lines=[b"Invalid arguments"]),
        SimpleNamespace(result="OK", lines=[b"7 EXISTS", b"OK [UIDVALIDITY 77] ok", b"OK [UIDNEXT 50] ok"]),
    ]
    client = _fake_client(
        {"IMAP4rev1", "CONDSTORE"},
        select=AsyncMock(side_effect=answers),
        uid_search=AsyncMock(return_value=SimpleNamespace(result="OK", lines=[b"3", b"SEARCH completed"])),
    )
    await _with(mail, client)
    mail._selected = "INBOX"  # noqa: SLF001
    assert await mail.async_status("INBOX") == {"messages": 7, "uidvalidity": 77, "uidnext": 50, "unseen": 1}
    assert [c.args for c in client.select.await_args_list] == [('"INBOX" (CONDSTORE)',), ('"INBOX"',)]


async def test_a_quiet_connection_is_checked_instead_of_logging_in_again() -> None:
    import time  # noqa: PLC0415

    mail = _mail()
    client = _fake_client({"IMAP4rev1"}, noop=AsyncMock(return_value=SimpleNamespace(result="OK", lines=[])))
    client.get_state = lambda: "SELECTED"
    mail._client = client  # noqa: SLF001
    mail._last_used = time.monotonic() - 10 * 60  # noqa: SLF001 - quiet for 10 minutes (one look)
    mail._connect = AsyncMock()  # noqa: SLF001
    assert await mail._ensure() is client  # noqa: SLF001
    mail._connect.assert_not_awaited()  # noqa: SLF001
    client.noop = AsyncMock(side_effect=TimeoutError)  # closed by the server meanwhile
    mail._connect.return_value = "new"  # noqa: SLF001
    assert await mail._ensure() == "new"  # noqa: SLF001


def test_vanished_lines() -> None:
    from custom_components.friedafetch.mail import _VANISHED_RE  # noqa: PLC0415

    assert _VANISHED_RE.match("(EARLIER) 41,43:45").group(1) == "41,43:45"
    assert _VANISHED_RE.match("* VANISHED (EARLIER) 7").group(1) == "7"
    assert _VANISHED_RE.match("1 FETCH (UID 2 FLAGS ())") is None
