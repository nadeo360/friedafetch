"""Push delivery via IMAP IDLE: run the inbox rules seconds after new mail arrives.

The watcher keeps its own IMAP connection (independent of the tool connection) and only reacts to
EXISTS notifications; the periodic timer stays active as a fallback.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import aioimaplib

from .mail import quote_mailbox

_LOGGER = logging.getLogger(__name__)

IDLE_RENEW = 25 * 60  # seconds; servers drop IDLE after 29 minutes
DEBOUNCE = 5.0  # seconds to wait for further messages before running the rules
BACKOFF_START = 15.0
BACKOFF_MAX = 600.0


def _has_new_mail(lines: Any) -> bool:
    for line in lines or []:
        text = bytes(line).decode(errors="replace") if isinstance(line, (bytes, bytearray)) else str(line)
        if text.upper().rstrip().endswith("EXISTS"):
            return True
    return False


class MailWatcher:
    """Waits for new messages in one mailbox and calls ``on_new_mail`` (debounced)."""

    def __init__(
        self,
        *,
        username: str,
        password: str,
        host: str,
        port: int,
        on_new_mail: Callable[[], Awaitable[None]],
        mailbox: str = "INBOX",
        ssl_context: ssl.SSLContext | None = None,
        timeout: int = 30,
        debounce: float = DEBOUNCE,
    ) -> None:
        self._username = username
        self._password = password
        self._host = host
        self._port = port
        self._on_new_mail = on_new_mail
        self.mailbox = mailbox
        self._ssl_context = ssl_context
        self._timeout = timeout
        self._debounce = debounce
        self._task: asyncio.Task | None = None
        self._pending: asyncio.TimerHandle | None = None
        self._client: aioimaplib.IMAP4_SSL | None = None
        self._running = False
        self.state = "stopped"  # stopped | connecting | listening | error | unsupported
        self.since: str | None = None
        self.last_push: str | None = None
        self.error: str | None = None

    def status(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "mailbox": self.mailbox,
            "since": self.since,
            "last_push": self.last_push,
            "error": self.error,
        }

    def start(self, create_task: Callable[..., asyncio.Task]) -> None:
        if self._running:
            return
        self._running = True
        self._task = create_task(self._loop(), "friedafetch_imap_idle")

    async def async_stop(self) -> None:
        self._running = False
        if self._pending is not None:
            self._pending.cancel()
            self._pending = None
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                _LOGGER.debug("IMAP IDLE task stopped")
            self._task = None
        await self._logout()
        self.state = "stopped"

    async def _logout(self) -> None:
        client, self._client = self._client, None
        if client is None:
            return
        try:
            if client.has_pending_idle():
                client.idle_done()
            await asyncio.wait_for(client.logout(), 5)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("IDLE connection logout failed (ignored)")

    def _set(self, state: str, error: str | None = None) -> None:
        if state != self.state:
            self.since = datetime.now().astimezone().isoformat(timespec="seconds")
        self.state = state
        self.error = error

    def _schedule(self) -> None:
        self.last_push = datetime.now().astimezone().isoformat(timespec="seconds")
        loop = asyncio.get_running_loop()
        if self._pending is not None:
            self._pending.cancel()
        self._pending = loop.call_later(self._debounce, lambda: loop.create_task(self._fire()))

    async def _fire(self) -> None:
        self._pending = None
        try:
            await self._on_new_mail()
        except Exception as err:  # noqa: BLE001 - keep listening
            _LOGGER.warning("Push-triggered inbox rules failed: %s", err)

    async def _connect(self) -> aioimaplib.IMAP4_SSL:
        client = aioimaplib.IMAP4_SSL(
            host=self._host, port=self._port, timeout=self._timeout, ssl_context=self._ssl_context
        )
        await client.wait_hello_from_server()
        response = await client.login(self._username, self._password)
        if response.result != "OK":
            raise PermissionError("IMAP login failed")
        response = await client.select(quote_mailbox(self.mailbox))
        if response.result != "OK":
            raise LookupError(f"Mailbox '{self.mailbox}' cannot be opened")
        return client

    async def _loop(self) -> None:
        backoff = BACKOFF_START
        while self._running:
            self._set("connecting")
            try:
                self._client = await self._connect()
                if not self._client.has_capability("IDLE"):
                    self._set("unsupported", "The server does not support IMAP IDLE")
                    await self._logout()
                    return
                self._set("listening")
                backoff = BACKOFF_START
                await self._listen(self._client)
            except asyncio.CancelledError:
                raise
            except PermissionError as err:
                self._set("error", str(err))
                await self._logout()
                return  # wrong password: the regular setup raises reauth
            except Exception as err:  # noqa: BLE001 - reconnect with backoff
                self._set("error", str(err) or err.__class__.__name__)
                _LOGGER.debug("IMAP IDLE connection lost, retrying in %ss: %s", backoff, err)
                await self._logout()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)

    async def _listen(self, client: aioimaplib.IMAP4_SSL) -> None:
        while self._running:
            idle = await client.idle_start(timeout=IDLE_RENEW)
            while client.has_pending_idle():
                lines = await client.wait_server_push()
                if lines == aioimaplib.STOP_WAIT_SERVER_PUSH:
                    client.idle_done()
                    await asyncio.wait_for(idle, self._timeout)
                    break
                if _has_new_mail(lines):
                    self._schedule()
            if client.get_state() not in ("AUTH", "SELECTED"):
                raise ConnectionError("IMAP connection closed")
