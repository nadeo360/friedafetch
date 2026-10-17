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
    assert "friedafetch/approvals/decide" in body


async def test_websocket_accounts(hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client) -> None:
    entry = await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/accounts"})
    msg = await ws.receive_json()
    account = msg["result"]["accounts"][0]
    assert msg["success"] and account["entry_id"] == entry.entry_id
    assert account["label"] == "test" and account["mail_enabled"] is True
    assert account["extensions"] == [] and "rules_total" not in account
    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_mailboxes",
        new_callable=AsyncMock,
        return_value=[{"name": "INBOX", "special_use": None}, {"name": "Archive", "special_use": None}],
    ):
        await ws.send_json({"id": 2, "type": "friedafetch/mailboxes"})
        msg = await ws.receive_json()
    assert msg["result"]["mailboxes"] == ["INBOX", "Archive"]
    await ws.send_json({"id": 3, "type": "friedafetch/rules/list"})
    msg = await ws.receive_json()
    assert msg["success"] is False  # moved to Frieda Postfach


async def test_websocket_requires_admin(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client: WebSocketGenerator, hass_admin_user
) -> None:
    await _setup(hass)
    hass_admin_user.groups = []
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/accounts"})
    msg = await ws.receive_json()
    assert msg["success"] is False and msg["error"]["code"] == "unauthorized"
