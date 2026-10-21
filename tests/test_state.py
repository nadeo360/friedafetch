"""Quotas, injection locks and approvals survive restarts; delayed sending."""

from __future__ import annotations

import asyncio
import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import aioimaplib
import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.friedafetch.const import (
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_APPROVAL_SEND,
    CONF_LIMIT_MAIL_SEND,
    CONF_SEND_DELAY,
    DOMAIN,
    LLM_API_ID,
)
from custom_components.friedafetch.guard import QUOTA_MAIL_SEND, Guard
from custom_components.friedafetch.llm_api import API_PROMPT, capability_hints
from custom_components.friedafetch.mail import ICloudMail, MailError

from .conftest import APP_PASSWORD, APPLE_ID

SEND = "custom_components.friedafetch.mail.ICloudMail.async_send"
MAIL = {"to": ["a@b.c"], "subject": "Hi", "body": "Text"}


async def _setup(hass: HomeAssistant, **options) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options=options,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _ctx() -> llm.LLMContext:
    return llm.LLMContext(platform="claude", context=Context(), language="de", assistant=None, device_id=None)


def test_guard_export_and_restore_keep_the_last_hour() -> None:
    clock = {"t": 5000.0}
    guard = Guard({CONF_LIMIT_MAIL_SEND: 3}, clock=lambda: clock["t"])
    guard.consume(QUOTA_MAIL_SEND, 2)
    data = guard.export(wall=1_000_000.0)
    # a new process: other monotonic clock, 10 minutes later
    other = Guard({CONF_LIMIT_MAIL_SEND: 3}, clock=lambda: 42.0)
    other.restore(data, wall=1_000_600.0)
    assert other.used(QUOTA_MAIL_SEND) == 2
    # older than an hour, from the future, or broken: ignored
    late = Guard({}, clock=lambda: 42.0)
    late.restore(data, wall=1_004_000.0)
    late.restore({QUOTA_MAIL_SEND: [[2_000_000.0, 5], ["x", 1], [1]], "unknown": [[1, 1]]}, wall=1_000_600.0)
    late.restore("nonsense")
    assert late.used(QUOTA_MAIL_SEND) == 0


async def test_quota_and_lock_survive_a_reload(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = await _setup(hass, **{CONF_LIMIT_MAIL_SEND: 1})
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    with patch(SEND, new_callable=AsyncMock, return_value={"message_id": "<m@x>"}) as send:
        first = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
        assert first.error is False and send.await_count == 1
        until = entry.runtime_data.lock_source("claude:-", "icloud_get_mail")

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

        clients = entry.runtime_data
        assert clients.guard.used(QUOTA_MAIL_SEND) == 1
        assert clients.locked_until("claude:-") == until
        api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
        second = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
        assert second.error is True and second.data["code"] == "blocked"
        assert send.await_count == 1


async def test_open_approvals_are_closed_by_a_restart(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client
) -> None:
    entry = await _setup(hass, **{CONF_APPROVAL_SEND: True})
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    with patch(SEND, new_callable=AsyncMock) as send:
        parked = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
        request_id = parked.data["request_id"]
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        send.assert_not_awaited()

    status = entry.runtime_data.approvals.status(request_id)
    assert status["status"] == "expired" and status["decided_by"] == "restart"
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/approvals/list"})
    msg = await ws.receive_json()
    assert msg["result"]["requests"][0]["id"] == request_id
    assert entry.runtime_data.approvals.pending_count == 0


async def test_delayed_sending_goes_out_after_the_delay(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = await _setup(hass, **{CONF_SEND_DELAY: 30})
    assert "delay of 30 seconds" in capability_hints(entry.options)
    assert "delay" not in API_PROMPT
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    with patch(SEND, new_callable=AsyncMock, return_value={"message_id": "<m@x>"}) as send:
        result = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
        assert result.error is False and result.data["code"] == "scheduled"
        request_id = result.data["request_id"]
        send.assert_not_awaited()
        assert entry.runtime_data.approvals.status(request_id)["reason"] == "delay"

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
        await hass.async_block_till_done()
        send.assert_awaited_once()
    status = entry.runtime_data.approvals.status(request_id)
    assert status["status"] == "executed" and status["decided_by"] == "delay"


async def test_delayed_sending_can_be_cancelled(hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client) -> None:
    entry = await _setup(hass, **{CONF_SEND_DELAY: 60})
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    with patch(SEND, new_callable=AsyncMock) as send:
        result = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
        ws = await hass_ws_client(hass)
        await ws.send_json(
            {
                "id": 1,
                "type": "friedafetch/approvals/decide",
                "request_id": result.data["request_id"],
                "decision": "deny",
            }
        )
        msg = await ws.receive_json()
        assert msg["result"]["request"]["status"] == "cancelled"
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
        await hass.async_block_till_done()
        send.assert_not_awaited()
    # a pending delayed mail is not sent after a restart either
    with patch(SEND, new_callable=AsyncMock) as send:
        later = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=120))
        await hass.async_block_till_done()
        send.assert_not_awaited()
    assert entry.runtime_data.approvals.status(later.data["request_id"])["status"] == "cancelled"


async def test_delayed_sending_checks_the_policy_at_once(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    await _setup(hass, **{CONF_SEND_DELAY: 30, CONF_LIMIT_MAIL_SEND: 1})
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    no_subject = await api.async_call_tool(
        llm.ToolInput(tool_name="icloud_send_mail", tool_args={"to": ["a@b.c"], "body": "x"})
    )
    assert no_subject.error is True and no_subject.data["code"] == "failed"


async def test_approval_wins_over_delay(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = await _setup(hass, **{CONF_SEND_DELAY: 30, CONF_APPROVAL_SEND: True})
    assert "delay" not in capability_hints(entry.options)
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    result = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
    assert result.data["code"] == "approval_required"


def _mail(shared: dict | None = None) -> ICloudMail:
    return ICloudMail(
        "u@icloud.com",
        "pw",
        from_address="u@icloud.com",
        imap_host="h",
        imap_port=993,
        smtp_host="s",
        smtp_port=587,
        shared=shared,
    )


async def test_connections_of_one_account_share_the_mailbox_list() -> None:
    shared: dict = {}
    first, second = _mail(shared), _mail(shared)
    boxes = [{"name": "INBOX", "delimiter": "/", "flags": [], "special_use": None}]
    first._shared["mailboxes"] = boxes  # noqa: SLF001 - as if the first connection had listed them
    second._run = AsyncMock()  # noqa: SLF001
    assert await second.async_mailboxes() is boxes
    second._run.assert_not_awaited()  # noqa: SLF001


def _open(closing: bool = False) -> SimpleNamespace:
    return SimpleNamespace(transport=SimpleNamespace(is_closing=lambda: closing))


async def test_broken_connection_is_replaced_at_once() -> None:
    """Regression: a connection broken off kept aioimaplib's state, so every command waited for its timeout."""
    mail = _mail()
    broken = SimpleNamespace(get_state=lambda: "SELECTED", logout=AsyncMock(), noop=AsyncMock(), protocol=_open(True))
    fresh = SimpleNamespace(get_state=lambda: "AUTH", protocol=_open())
    mail._client = broken  # noqa: SLF001
    mail._last_used = time.monotonic()  # noqa: SLF001 - used a moment ago
    with patch.object(ICloudMail, "_connect", AsyncMock(return_value=fresh)):
        assert await mail._ensure() is fresh  # noqa: SLF001
    broken.noop.assert_not_awaited()
    await mail.async_close()


async def test_command_timeout_reconnects_once() -> None:
    """aioimaplib's command timeout is no aioimaplib.Error: it is retried on a new connection like the others."""
    mail = _mail()
    calls = 0

    async def op(client: object) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise aioimaplib.CommandTimeout(SimpleNamespace())
        return "ok"

    with patch.object(ICloudMail, "_ensure", AsyncMock(return_value=SimpleNamespace())):
        assert await mail._run(op) == "ok"  # noqa: SLF001

        async def never(client: object) -> str:
            raise aioimaplib.CommandTimeout(SimpleNamespace())  # every try: a clear message, not the command

        with pytest.raises(MailError, match="no answer from the server in time"):
            await mail._run(never)  # noqa: SLF001


async def test_idle_connection_is_replaced_without_waiting_for_logout() -> None:
    mail = _mail()
    gate = asyncio.Event()

    async def slow_logout():
        await gate.wait()  # a dead connection never answers

    stale = SimpleNamespace(get_state=lambda: "SELECTED", logout=slow_logout, protocol=_open())
    fresh = SimpleNamespace(get_state=lambda: "AUTH", protocol=_open())
    mail._client = stale  # noqa: SLF001
    mail._last_used = -10_000.0  # noqa: SLF001 - idle for hours
    with patch.object(ICloudMail, "_connect", AsyncMock(return_value=fresh)):
        assert await asyncio.wait_for(mail._ensure(), 1) is fresh  # noqa: SLF001
    assert len(mail._closing) == 1  # noqa: SLF001 - the logout runs in the background
    gate.set()
    await mail.async_close()
    assert not mail._closing  # noqa: SLF001


async def test_open_approval_expires_on_time(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    """Regression: the expiry timer ran in a worker thread and failed, so requests never expired."""
    entry = await _setup(hass, **{CONF_APPROVAL_SEND: True})
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    with patch(SEND, new_callable=AsyncMock) as send:
        parked = await api.async_call_tool(llm.ToolInput(tool_name="icloud_send_mail", tool_args=MAIL))
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=16))
        await hass.async_block_till_done()
        send.assert_not_awaited()
    assert entry.runtime_data.approvals.status(parked.data["request_id"])["status"] == "expired"
