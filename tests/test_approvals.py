"""Human-in-the-loop approvals."""

from unittest.mock import AsyncMock, patch

from homeassistant.components import persistent_notification
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.friedafetch.const import (
    AUDIT_EVENT,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_APPROVAL_DELETE,
    CONF_APPROVAL_MASS,
    CONF_APPROVAL_NOTIFY,
    CONF_APPROVAL_SEND,
    DOMAIN,
    LLM_API_ID,
    MOBILE_ACTION_EVENT,
)

from .conftest import APP_PASSWORD, APPLE_ID


async def _setup(hass: HomeAssistant, **options) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={CONF_APPROVAL_SEND: True, CONF_APPROVAL_DELETE: True, CONF_APPROVAL_MASS: 5, **options},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _ctx() -> llm.LLMContext:
    return llm.LLMContext(platform="claude", context=Context(), language="de", assistant=None, device_id=None)


async def test_send_is_parked_and_executed_on_approval(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client
) -> None:
    await _setup(hass)
    events = async_capture_events(hass, AUDIT_EVENT)
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    assert "icloud_approval_status" in {t.name for t in api.tools}

    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_send",
        new_callable=AsyncMock,
        return_value={"message_id": "<m@x>", "to": ["a@b.c"], "subject": "Hi"},
    ) as send:
        parked = await api.async_call_tool(
            llm.ToolInput(tool_name="icloud_send_mail", tool_args={"to": ["a@b.c"], "subject": "Hi", "body": "Text"})
        )
        assert parked.error is False
        assert parked.data["code"] == "approval_required"
        request_id = parked.data["request_id"]
        send.assert_not_awaited()
        # a persistent notification was created
        notifications = persistent_notification._async_get_or_create_notifications(hass)  # noqa: SLF001
        assert any(request_id in nid for nid in notifications)

        status = await api.async_call_tool(
            llm.ToolInput(tool_name="icloud_approval_status", tool_args={"request_id": request_id})
        )
        assert status.data["status"] == "pending" and status.data["reason"] == "send"

        ws = await hass_ws_client(hass)
        await ws.send_json({"id": 1, "type": "friedafetch/approvals/list"})
        msg = await ws.receive_json()
        assert msg["result"]["enabled"] and msg["result"]["requests"][0]["id"] == request_id

        await ws.send_json(
            {"id": 2, "type": "friedafetch/approvals/decide", "request_id": request_id, "decision": "approve"}
        )
        msg = await ws.receive_json()
        assert msg["success"], msg
        assert msg["result"]["request"]["status"] == "executed"
        assert msg["result"]["request"]["result"]["message_id"] == "<m@x>"
        send.assert_awaited_once()

        status = await api.async_call_tool(
            llm.ToolInput(tool_name="icloud_approval_status", tool_args={"request_id": request_id})
        )
        assert status.data["status"] == "executed"
        # deciding twice fails
        await ws.send_json(
            {"id": 3, "type": "friedafetch/approvals/decide", "request_id": request_id, "decision": "deny"}
        )
        msg = await ws.receive_json()
        assert msg["success"] is False and msg["error"]["code"] == "not_found"
    await hass.async_block_till_done()
    assert [e.data["result"] for e in events] == ["pending", "ok"]
    assert events[1].data["client"].startswith("approved:")
    assert request_id not in persistent_notification._async_get_or_create_notifications(hass)  # noqa: SLF001


async def test_deny_and_mass_threshold(hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client) -> None:
    await _setup(hass)
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_move", new_callable=AsyncMock, return_value={"count": 2}
    ) as move:
        # below the threshold: executes directly
        ok = await api.async_call_tool(
            llm.ToolInput(tool_name="icloud_move_mail", tool_args={"uids": [1, 2], "target_mailbox": "Archive"})
        )
        assert ok.error is False and move.await_count == 1
        # above the threshold: parked
        parked = await api.async_call_tool(
            llm.ToolInput(
                tool_name="icloud_move_mail", tool_args={"uids": [1, 2, 3, 4, 5, 6], "target_mailbox": "Archive"}
            )
        )
        assert parked.data["code"] == "approval_required" and parked.data["reason"] == "mass"
        ws = await hass_ws_client(hass)
        await ws.send_json(
            {
                "id": 1,
                "type": "friedafetch/approvals/decide",
                "request_id": parked.data["request_id"],
                "decision": "deny",
            }
        )
        msg = await ws.receive_json()
        assert msg["result"]["request"]["status"] == "denied"
        assert move.await_count == 1


async def test_mobile_action_and_notify_service(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    calls = []

    async def fake_notify(call):
        calls.append(call.data)

    hass.services.async_register("notify", "mobile_app_test", fake_notify)
    await _setup(hass, **{CONF_APPROVAL_NOTIFY: "notify.mobile_app_test"})
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    with patch(
        "custom_components.friedafetch.carddav_client.ICloudCardDav.async_delete", new_callable=AsyncMock
    ) as delete:
        parked = await api.async_call_tool(llm.ToolInput(tool_name="icloud_delete_contact", tool_args={"uid": "c1"}))
        await hass.async_block_till_done()
        request_id = parked.data["request_id"]
        assert calls and calls[0]["data"]["actions"][0]["action"] == f"FRIEDAFETCH_APPROVE_{request_id}"
        hass.bus.async_fire(MOBILE_ACTION_EVENT, {"action": f"FRIEDAFETCH_APPROVE_{request_id}"})
        await hass.async_block_till_done()
        delete.assert_awaited_once_with("c1")
    # clear_notification was sent to the phone
    assert any(c.get("message") == "clear_notification" for c in calls)


async def test_no_approvals_when_disabled(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=APPLE_ID, data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    api = await llm.async_get_api(hass, LLM_API_ID, _ctx())
    assert "icloud_approval_status" not in {t.name for t in api.tools}
    assert entry.runtime_data.approvals is None
