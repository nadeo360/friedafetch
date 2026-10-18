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
    for module in ("i18n.js", "styles.js", "ui.js"):  # loaded by panel.js with the same version query
        resp = await client.get(f"/friedafetch_static/{module}?v=1")
        assert resp.status == 200 and "export const" in await resp.text()
    # the design library that Frieda Postfach and later extensions import from here
    lib = await (await client.get("/friedafetch_static/ui.js")).text()
    for name in (
        "UI_API",
        "UI_STYLE",
        "Layout",
        "renderWidgets",
        "columnMenu",
        "cardMenu",
        "renderConfirm",
        "frontend/set_user_data",
    ):
        assert name in lib


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


async def test_base_urls_lists_local_external_and_cloud(hass: HomeAssistant) -> None:
    """The overview offers every address of this instance once: local, external and Home Assistant Cloud."""
    from custom_components.friedafetch.frontend import _base_urls  # noqa: PLC0415

    hass.config.internal_url = "http://192.168.1.118:8123"
    hass.config.external_url = "https://home.example.org"
    with patch("homeassistant.helpers.network._get_cloud_url", return_value="https://abc.ui.nabu.casa"):
        assert _base_urls(hass) == [
            {"kind": "local", "url": "http://192.168.1.118:8123"},
            {"kind": "external", "url": "https://home.example.org"},
            {"kind": "cloud", "url": "https://abc.ui.nabu.casa"},
        ]
    # without an external address and Home Assistant Cloud only the local address remains
    hass.config.external_url = None
    assert _base_urls(hass) == [{"kind": "local", "url": "http://192.168.1.118:8123"}]
    # an external address that is the Home Assistant Cloud address is listed once
    hass.config.external_url = "https://abc.ui.nabu.casa"
    with patch("homeassistant.helpers.network._get_cloud_url", return_value="https://abc.ui.nabu.casa"):
        assert [u["kind"] for u in _base_urls(hass)] == ["local", "external"]


async def test_subscribe_sends_live_updates(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client: WebSocketGenerator
) -> None:
    """Open panels learn which part of which account changed, and stop hearing about it after unsubscribing."""
    entry = await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/subscribe"})
    assert (await ws.receive_json())["success"]

    await entry.runtime_data.audit.async_record(tool="icloud_move_mail", action="move", params={}, result="ok")
    event = await ws.receive_json()
    assert event["id"] == 1 and event["event"] == {"entry_id": entry.entry_id, "topic": "audit"}

    await entry.runtime_data.usage.async_record(entry.entry_id, "icloud_list_events", write=False, ok=True, source=None)
    assert (await ws.receive_json())["event"]["topic"] == "usage"

    await ws.send_json({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    assert (await ws.receive_json())["success"]
    await entry.runtime_data.audit.async_record(tool="icloud_move_mail", action="move", params={}, result="ok")
    await ws.send_json({"id": 3, "type": "ping"})
    assert (await ws.receive_json())["type"] == "pong"  # no event arrived in between


async def test_accounts_report_the_served_version(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client: WebSocketGenerator
) -> None:
    """Open panels compare it with the code they loaded and offer a reload after an update."""
    await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/accounts"})
    result = (await ws.receive_json())["result"]
    panel = hass.data[frontend.DATA_PANELS]["friedafetch"]
    assert result["version"] and panel.config["_panel_custom"]["module_url"].endswith(f"?v={result['version']}")
