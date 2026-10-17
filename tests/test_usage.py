"""Usage counters, MCP client tracking and the overview websocket command."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.carddav_client import ContactNotFound
from custom_components.friedafetch.usage import DAYS_KEPT, UsageStats

from .test_mcp_http import _call_tool, _entry, _rpc, _setup


async def test_usage_stats_counts_and_windows(hass: HomeAssistant) -> None:
    stats = UsageStats(hass)
    await stats.async_record("e1", "icloud_search_mail", write=False, ok=True, source="friedafetch")
    await stats.async_record("e1", "icloud_search_mail", write=False, ok=False, source="friedafetch")
    await stats.async_record("e1", "icloud_move_mail", write=True, ok=True, source="openai_conversation")
    summary = stats.summary("e1")
    assert summary["today"] == {"read": 2, "write": 1, "error": 1}
    assert summary["week"] == summary["month"] == summary["total"] == summary["today"]
    assert summary["tools"][0] == {"tool": "icloud_search_mail", "count": 2}
    assert summary["sources"] == {"friedafetch": 2, "openai_conversation": 1}
    assert summary["last"]["tool"] == "icloud_move_mail" and summary["last"]["ok"] is True
    assert len(summary["series"]) == 14 and summary["series"][-1]["read"] == 2
    assert stats.summary("other")["total"] == {"read": 0, "write": 0, "error": 0}

    # old days are dropped, totals stay
    old = (dt_util.now().date() - timedelta(days=DAYS_KEPT + 3)).isoformat()
    stats._data["accounts"]["e1"]["days"][old] = {"read": 5, "write": 0, "error": 0}
    await stats.async_record("e1", "icloud_get_mail", write=False, ok=True, source=None)
    assert old not in stats._data["accounts"]["e1"]["days"]
    assert stats.summary("e1")["sources"]["unknown"] == 1

    await stats.async_reset("e1")
    assert stats.summary("e1")["since"] is None


async def test_usage_stats_clients(hass: HomeAssistant) -> None:
    stats = UsageStats(hass)
    await stats.async_note_client("claude-code", "2.1", "full")
    await stats.async_note_client("inspector", None, "readonly")
    await stats.async_note_client("claude-code", "2.2", "full")
    clients = stats.clients()
    assert {c["name"] for c in clients} == {"claude-code", "inspector"}
    claude = next(c for c in clients if c["name"] == "claude-code")
    assert claude["version"] == "2.2" and claude["first_seen"] <= claude["last_seen"]


async def test_tool_calls_are_counted_and_overview(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_client, hass_ws_client
) -> None:
    entry: MockConfigEntry = await _setup(hass, _entry())
    client = await hass_client()
    await _rpc(
        client,
        "initialize",
        {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "claude-code", "version": "2.1"}},
    )
    with patch(
        "custom_components.friedafetch.carddav_client.ICloudCardDav.async_search",
        new_callable=AsyncMock,
        return_value=[],
    ):
        assert (await _call_tool(client, "icloud_search_contacts", {"query": "max"}))[0] is False
    with patch(
        "custom_components.friedafetch.carddav_client.ICloudCardDav.async_get",
        new_callable=AsyncMock,
        side_effect=ContactNotFound("nope"),
    ):
        assert (await _call_tool(client, "icloud_get_contact", {"uid": "x"}))[0] is True

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/overview"})
    msg = await ws.receive_json()
    assert msg["success"], msg
    result = msg["result"]
    assert result["entry_id"] == entry.entry_id
    endpoint = result["endpoint"]
    assert endpoint["active"] is True and endpoint["path"] == "/api/friedafetch"
    assert endpoint["tools"] == endpoint["tools_readonly"] + endpoint["tools_write"] and endpoint["tools_write"] > 0
    assert result["llm_api"] == ["friedafetch"]
    assert result["ha_mcp_server"] == {"installed": False, "selected": False}
    assert result["postfach"]["state"] == "not_installed"
    usage = result["usage"]
    assert usage["today"] == {"read": 2, "write": 0, "error": 1}
    assert usage["sources"] == {"friedafetch": 2}
    assert result["clients"][0]["name"] == "claude-code" and result["clients"][0]["profile"] == "full"

    # an extension that reports its status is shown as running
    entry.runtime_data.extensions["mail"] = SimpleNamespace(
        tool_classes=[], status=lambda: {"rules_total": 2, "rules_enabled": 1, "auto": True, "interval": 5}
    )
    await ws.send_json({"id": 2, "type": "friedafetch/overview"})
    postfach = (await ws.receive_json())["result"]["postfach"]
    assert postfach["state"] == "running" and postfach["status"]["rules_total"] == 2

    await ws.send_json({"id": 3, "type": "friedafetch/usage/reset"})
    assert (await ws.receive_json())["success"]
    await ws.send_json({"id": 4, "type": "friedafetch/overview"})
    assert (await ws.receive_json())["result"]["usage"]["total"]["read"] == 0


async def test_overview_sees_ha_mcp_server(hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client) -> None:
    await _setup(hass, _entry())
    MockConfigEntry(domain="mcp_server", data={"llm_hass_api": ["assist", "friedafetch"]}).add_to_hass(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/overview"})
    assert (await ws.receive_json())["result"]["ha_mcp_server"] == {"installed": True, "selected": True}
