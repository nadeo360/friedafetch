"""IMAP IDLE watcher."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aioimaplib
import pytest

from custom_components.friedafetch.idle import MailWatcher, _has_new_mail


@pytest.fixture(autouse=True)
def no_imap_idle() -> None:
    """These tests exercise the watcher itself (overrides the global stub)."""
    return


def test_has_new_mail() -> None:
    assert _has_new_mail([b"12 EXISTS"])
    assert _has_new_mail(["3 RECENT", "13 EXISTS"])
    assert not _has_new_mail([b"5 EXPUNGE", b"1 FETCH (FLAGS (\\Seen))"])
    assert not _has_new_mail(None)


def _client(pushes: list, idle_supported: bool = True) -> MagicMock:
    client = MagicMock()
    client.has_capability.return_value = idle_supported
    pending = {"on": False}

    async def idle_start(timeout):
        pending["on"] = True
        fut = asyncio.get_running_loop().create_future()
        fut.set_result(None)
        return fut

    async def wait_server_push():
        if pushes:
            return pushes.pop(0)
        await asyncio.sleep(3600)

    def idle_done():
        pending["on"] = False

    client.idle_start = idle_start
    client.wait_server_push = wait_server_push
    client.idle_done = idle_done
    client.has_pending_idle = lambda: pending["on"]
    client.get_state.return_value = "SELECTED"
    client.logout = AsyncMock()
    return client


async def test_new_mail_triggers_callback_once() -> None:
    calls = AsyncMock()
    watcher = MailWatcher(username="u", password="p", host="h", port=993, on_new_mail=calls, debounce=0.05)
    client = _client([[b"7 EXISTS"], [b"8 EXISTS"], [b"2 EXPUNGE"]])
    with patch.object(MailWatcher, "_connect", AsyncMock(return_value=client)):
        watcher.start(lambda coro, name: asyncio.get_running_loop().create_task(coro))
        await asyncio.sleep(0.2)
        assert watcher.state == "listening"
        assert watcher.status()["last_push"] is not None
        calls.assert_awaited_once()  # two EXISTS within the debounce window -> one run
        await watcher.async_stop()
    assert watcher.state == "stopped"


async def test_idle_restarts_after_renewal_timeout() -> None:
    calls = AsyncMock()
    watcher = MailWatcher(username="u", password="p", host="h", port=993, on_new_mail=calls, debounce=0.01)
    client = _client([aioimaplib.STOP_WAIT_SERVER_PUSH, [b"1 EXISTS"]])
    with patch.object(MailWatcher, "_connect", AsyncMock(return_value=client)):
        watcher.start(lambda coro, name: asyncio.get_running_loop().create_task(coro))
        await asyncio.sleep(0.1)
        calls.assert_awaited_once()
        await watcher.async_stop()


async def test_unsupported_server_and_bad_login() -> None:
    watcher = MailWatcher(username="u", password="p", host="h", port=993, on_new_mail=AsyncMock())
    with patch.object(MailWatcher, "_connect", AsyncMock(return_value=_client([], idle_supported=False))):
        watcher.start(lambda coro, name: asyncio.get_running_loop().create_task(coro))
        await asyncio.sleep(0.05)
    assert watcher.state == "unsupported"
    await watcher.async_stop()

    watcher = MailWatcher(username="u", password="p", host="h", port=993, on_new_mail=AsyncMock())
    with patch.object(MailWatcher, "_connect", AsyncMock(side_effect=PermissionError("IMAP login failed"))):
        watcher.start(lambda coro, name: asyncio.get_running_loop().create_task(coro))
        await asyncio.sleep(0.05)
    assert watcher.state == "error" and "login" in watcher.error
    await watcher.async_stop()


async def test_connection_errors_back_off_and_retry() -> None:
    watcher = MailWatcher(username="u", password="p", host="h", port=993, on_new_mail=AsyncMock())
    connect = AsyncMock(side_effect=[OSError("network down"), _client([])])
    with (
        patch.object(MailWatcher, "_connect", connect),
        patch("custom_components.friedafetch.idle.BACKOFF_START", 0.01),
    ):
        watcher.start(lambda coro, name: asyncio.get_running_loop().create_task(coro))
        await asyncio.sleep(0.1)
        assert connect.await_count == 2 and watcher.state == "listening"
        await watcher.async_stop()
