"""Sidebar panel and websocket API."""

from unittest.mock import AsyncMock, patch

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, DOMAIN

from .conftest import APP_PASSWORD, APPLE_ID

MAILBOXES = [{"name": "INBOX", "special_use": None}, {"name": "Archive", "special_use": None}]


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=APPLE_ID, data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_panel_registered_and_removed(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = await _setup(hass)
    panels = hass.data[frontend.DATA_PANELS]
    assert "friedafetch" in panels
    assert panels["friedafetch"].require_admin is True
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert "friedafetch" not in hass.data[frontend.DATA_PANELS]


async def test_static_panel_served(hass: HomeAssistant, mock_discover: AsyncMock, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    resp = await client.get("/friedafetch_static/panel.js")
    assert resp.status == 200
    body = await resp.text()
    assert "friedafetch-panel" in body
    assert "friedafetch/rules/run" in body


async def test_websocket_rule_lifecycle(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client: WebSocketGenerator
) -> None:
    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_mailboxes", new_callable=AsyncMock, return_value=MAILBOXES
    ):
        entry = await _setup(hass)
        ws = await hass_ws_client(hass)

        await ws.send_json({"id": 1, "type": "friedafetch/accounts"})
        msg = await ws.receive_json()
        account = msg["result"]["accounts"][0]
        assert msg["success"] and account["entry_id"] == entry.entry_id
        assert account["label"] == "test"
        assert account["rules_total"] == 0 and account["rules_enabled"] == 0
        assert account["rules_auto"] is True and account["mail_enabled"] is True

        await ws.send_json({"id": 2, "type": "friedafetch/mailboxes"})
        msg = await ws.receive_json()
        assert msg["result"]["mailboxes"] == ["INBOX", "Archive"]

        await ws.send_json(
            {
                "id": 3,
                "type": "friedafetch/rules/create",
                "rule": {
                    "name": "Rechnungen",
                    "conditions": [{"field": "subject", "op": "contains", "value": "rechnung"}],
                    "actions": {"move_to": "Archive"},
                },
            }
        )
        msg = await ws.receive_json()
        assert msg["success"], msg
        rule_id = msg["result"]["rule"]["id"]

        await ws.send_json(
            {"id": 4, "type": "friedafetch/rules/update", "rule_id": rule_id, "changes": {"enabled": False}}
        )
        msg = await ws.receive_json()
        assert msg["success"] and msg["result"]["rule"]["enabled"] is False

        await ws.send_json({"id": 5, "type": "friedafetch/rules/list"})
        msg = await ws.receive_json()
        assert [r["id"] for r in msg["result"]["rules"]] == [rule_id]
        assert msg["result"]["last_run"] is None

        # invalid rule -> rule_error
        await ws.send_json(
            {
                "id": 6,
                "type": "friedafetch/rules/create",
                "rule": {
                    "name": "x",
                    "conditions": [{"field": "subject", "op": "contains", "value": "a"}],
                    "actions": {},
                },
            }
        )
        msg = await ws.receive_json()
        assert msg["success"] is False and msg["error"]["code"] == "rule_error"

        # unknown rule -> not_found
        await ws.send_json({"id": 7, "type": "friedafetch/rules/delete", "rule_id": "nope"})
        msg = await ws.receive_json()
        assert msg["success"] is False and msg["error"]["code"] == "not_found"

        with patch(
            "custom_components.friedafetch.rules.RuleEngine.async_run",
            new_callable=AsyncMock,
            return_value={
                "scope": "all",
                "dry_run": True,
                "checked": 0,
                "matched": 0,
                "actions": [],
                "skipped": [],
                "errors": [],
            },
        ) as run:
            await ws.send_json({"id": 8, "type": "friedafetch/rules/run", "scope": "all", "dry_run": True})
            msg = await ws.receive_json()
        assert msg["success"] and msg["result"]["dry_run"] is True
        run.assert_awaited_once_with(scope="all", dry_run=True, mailbox=None, rule_ids=None)

        await ws.send_json({"id": 9, "type": "friedafetch/rules/delete", "rule_id": rule_id})
        msg = await ws.receive_json()
        assert msg["success"] and msg["result"]["deleted"] is True


async def test_websocket_requires_admin(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client: WebSocketGenerator, hass_admin_user
) -> None:
    await _setup(hass)
    hass_admin_user.groups = []
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/rules/list"})
    msg = await ws.receive_json()
    assert msg["success"] is False and msg["error"]["code"] == "unauthorized"
