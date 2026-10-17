"""Audit log: tool calls are recorded, blocked calls included, events fired."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.icloud_mcp.const import (
    AUDIT_EVENT,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_LIMIT_MAIL_MODIFY,
    CONF_PROTECTED_MAILBOXES,
    DOMAIN,
    LLM_API_ID,
)

from .conftest import APP_PASSWORD, APPLE_ID


async def test_tool_calls_are_audited_and_guarded(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={CONF_LIMIT_MAIL_MODIFY: 3, CONF_PROTECTED_MAILBOXES: ["Steuer"]},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    events = async_capture_events(hass, AUDIT_EVENT)
    ctx = llm.LLMContext(
        platform="test-client", context=Context(user_id=None), language="de", assistant=None, device_id=None
    )
    api = await llm.async_get_api(hass, LLM_API_ID, ctx)

    with patch(
        "custom_components.icloud_mcp.mail.ICloudMail.async_delete",
        new_callable=AsyncMock,
        return_value={"uids": [1, 2], "count": 2, "action": "moved_to_trash"},
    ) as delete:
        ok = await api.async_call_tool(llm.ToolInput(tool_name="icloud_delete_mail", tool_args={"uids": [1, 2]}))
        assert ok.error is False
        # quota: 3 per hour, 2 used -> 2 more are blocked, 1 more is fine
        blocked = await api.async_call_tool(llm.ToolInput(tool_name="icloud_delete_mail", tool_args={"uids": [3, 4]}))
        assert blocked.error is True and blocked.data["code"] == "blocked"
        assert "limit" in blocked.data["error"].lower()
        # protected mailbox
        protected = await api.async_call_tool(
            llm.ToolInput(tool_name="icloud_delete_mail", tool_args={"uid": 9, "mailbox": "Steuer"})
        )
        assert protected.error is True and protected.data["code"] == "blocked"
        assert delete.await_count == 1
    # reads are not audited
    with patch(
        "custom_components.icloud_mcp.carddav_client.ICloudCardDav.async_search",
        new_callable=AsyncMock,
        return_value=[],
    ):
        await api.async_call_tool(llm.ToolInput(tool_name="icloud_search_contacts", tool_args={"query": "x"}))
    await hass.async_block_till_done()

    assert [e.data["result"] for e in events] == ["ok", "blocked", "blocked"]
    assert events[0].data["tool"] == "icloud_delete_mail"
    assert events[0].data["client"] == "test-client"
    assert events[0].data["details"]["count"] == 2
    assert events[0].data["params"]["uids"] == [1, 2]

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "icloud_mcp/audit/list"})
    msg = await ws.receive_json()
    assert msg["success"]
    entries = msg["result"]["entries"]
    assert len(entries) == 3 and entries[0]["result"] == "blocked"  # newest first
    assert msg["result"]["quota"]["mail_modify"] == {"used": 2, "limit": 3}
    await ws.send_json({"id": 2, "type": "icloud_mcp/audit/list", "result": "blocked"})
    msg = await ws.receive_json()
    assert len(msg["result"]["entries"]) == 2
    await ws.send_json({"id": 3, "type": "icloud_mcp/audit/clear"})
    msg = await ws.receive_json()
    assert msg["success"]
    await ws.send_json({"id": 4, "type": "icloud_mcp/audit/list"})
    msg = await ws.receive_json()
    assert msg["result"]["entries"] == []


async def test_send_mail_policy_and_body_not_logged(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={"send_policy": "allowlist", "send_allowlist": ["example.org"]},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    events = async_capture_events(hass, AUDIT_EVENT)
    ctx = llm.LLMContext(platform="test", context=Context(), language="de", assistant=None, device_id=None)
    api = await llm.async_get_api(hass, LLM_API_ID, ctx)
    with patch(
        "custom_components.icloud_mcp.mail.ICloudMail.async_send",
        new_callable=AsyncMock,
        return_value={"message_id": "<1@x>", "to": ["a@example.org"], "subject": "Hi"},
    ) as send:
        blocked = await api.async_call_tool(
            llm.ToolInput(
                tool_name="icloud_send_mail", tool_args={"to": ["x@evil.test"], "subject": "Hi", "body": "secret body"}
            )
        )
        assert blocked.error is True and blocked.data["code"] == "blocked"
        ok = await api.async_call_tool(
            llm.ToolInput(
                tool_name="icloud_send_mail",
                tool_args={"to": ["a@example.org"], "subject": "Hi", "body": "secret body"},
            )
        )
        assert ok.error is False
    assert send.await_count == 1
    await hass.async_block_till_done()
    assert [e.data["result"] for e in events] == ["blocked", "ok"]
    assert "body" not in events[1].data["params"]
    assert events[1].data["params"]["body_chars"] == len("secret body")
    assert events[1].data["action"] == "send"
