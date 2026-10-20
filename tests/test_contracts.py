"""The shapes of the panel's websocket answers, with realistic data (tests/contract.py explains why).

After an intended change: UPDATE_CONTRACTS=1 pytest tests/test_contracts.py, then bring the dev preview's mock in line.
"""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, CONF_APPROVAL_SEND, DOMAIN
from custom_components.friedafetch.usage import async_get_usage

from .conftest import APP_PASSWORD, APPLE_ID
from .contract import assert_contract


async def test_panel_answers_keep_their_shape(hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={CONF_APPROVAL_SEND: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    clients = entry.runtime_data
    # some activity: an approval waiting, change-log entries (one with mails, one failed), usage
    await clients.approvals.async_request(
        tool_name="icloud_send_mail",
        action="send",
        reason="approval",
        summary="„Angebot“ → bob@example.com",
        params={"to": ["bob@example.com"], "subject": "Angebot"},
        runner=AsyncMock(),
        client="Claude",
        user_id=None,
    )
    await clients.audit.async_record(
        tool="icloud_run_rules",
        action="rules",
        params={"scope": "new"},
        result="ok",
        client="rules (push)",
        details={"checked": 1, "matched": 1, "trigger": "push", "mails": [{"message_id": "<1@x>", "subject": "Hi"}]},
    )
    await clients.audit.async_record(
        tool="icloud_create_event", action="write", params={"summary": "x"}, result="error", error="not found"
    )
    usage = await async_get_usage(hass)
    await usage.async_record(entry.entry_id, "icloud_search_mail", write=False, ok=True, source="friedafetch")
    await usage.async_record(entry.entry_id, "icloud_send_mail", write=True, ok=False, source="mcp_server")

    ws = await hass_ws_client(hass)
    for i, (command, extra) in enumerate(
        [
            ("friedafetch/accounts", {}),
            ("friedafetch/overview", {"entry_id": entry.entry_id}),
            ("friedafetch/approvals/list", {"entry_id": entry.entry_id}),
            ("friedafetch/audit/list", {"entry_id": entry.entry_id}),
        ],
        start=1,
    ):
        with patch(
            "custom_components.friedafetch.mail.ICloudMail.async_mailboxes",
            new_callable=AsyncMock,
            return_value=[{"name": "INBOX", "special_use": None}],
        ):
            await ws.send_json({"id": i, "type": command, **extra})
            msg = await ws.receive_json()
        assert msg["success"], (command, msg)
        assert_contract(command, msg["result"])
