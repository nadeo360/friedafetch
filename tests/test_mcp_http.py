"""Own Streamable-HTTP MCP endpoint."""

from __future__ import annotations

import json
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.icloud_mcp.carddav_client import ContactNotFound
from custom_components.icloud_mcp.const import CONF_APP_PASSWORD, CONF_APPLE_ID, CONF_READ_ONLY, DOMAIN
from custom_components.icloud_mcp.mcp_http import STREAMABLE_API

from .conftest import APP_PASSWORD, APPLE_ID

HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def _entry(apple_id: str = APPLE_ID, **options: Any) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=apple_id,
        unique_id=apple_id,
        data={CONF_APPLE_ID: apple_id, CONF_APP_PASSWORD: APP_PASSWORD},
        options=options,
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> MockConfigEntry:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def entry(hass: HomeAssistant, mock_discover: AsyncMock) -> MockConfigEntry:
    """A loaded iCloud entry."""
    return await _setup(hass, _entry())


async def _rpc(client, method: str, params: dict[str, Any] | None = None, *, msg_id: int = 1) -> dict[str, Any]:
    body: dict[str, Any] = {"jsonrpc": "2.0", "id": msg_id, "method": method}
    if params is not None:
        body["params"] = params
    response = await client.post(STREAMABLE_API, json=body, headers=HEADERS)
    assert response.status == HTTPStatus.OK, await response.text()
    data = await response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == msg_id
    return data


async def _call_tool(client, name: str, arguments: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    data = await _rpc(client, "tools/call", {"name": name, "arguments": arguments}, msg_id=7)
    result = data["result"]
    assert result["content"][0]["type"] == "text"
    return result["isError"], json.loads(result["content"][0]["text"])


async def test_initialize(hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator) -> None:
    client = await hass_client()
    data = await _rpc(
        client,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"},
        },
    )
    result = data["result"]
    assert result["serverInfo"]["name"] == "icloud-mcp"
    manifest = json.loads((Path(__file__).parents[1] / "custom_components/icloud_mcp/manifest.json").read_text())
    assert result["serverInfo"]["version"] == manifest["version"]
    assert "tools" in result["capabilities"]
    assert "iCloud" in result["instructions"]
    assert result["protocolVersion"]

    # the client's "initialized" notification is acknowledged only
    response = await client.post(
        STREAMABLE_API, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=HEADERS
    )
    assert response.status == HTTPStatus.ACCEPTED


async def test_tools_list(hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator) -> None:
    client = await hass_client()
    data = await _rpc(client, "tools/list")
    tools = {tool["name"]: tool for tool in data["result"]["tools"]}
    assert len(tools) == 28
    assert "icloud_list_calendars" in tools
    assert "icloud_delete_mail" in tools

    get_event = tools["icloud_get_event"]
    assert get_event["inputSchema"]["type"] == "object"
    assert get_event["inputSchema"]["properties"]["calendar_id"] == {"type": "string"}
    assert sorted(get_event["inputSchema"]["required"]) == ["calendar_id", "uid"]
    assert get_event["annotations"]["readOnlyHint"] is True
    assert get_event["annotations"]["destructiveHint"] is False
    assert get_event["description"]

    list_events = tools["icloud_list_events"]
    assert list_events["inputSchema"]["properties"]["calendar_ids"]["type"] == "array"
    assert "required" not in list_events["inputSchema"]

    delete = tools["icloud_delete_contact"]
    assert delete["annotations"]["readOnlyHint"] is False
    assert delete["annotations"]["destructiveHint"] is True

    assert tools["icloud_list_calendars"]["inputSchema"] == {"type": "object", "properties": {}}


async def test_tools_list_respects_options(hass: HomeAssistant, mock_discover: AsyncMock, hass_client) -> None:
    await _setup(hass, _entry(**{CONF_READ_ONLY: True}))
    client = await hass_client()
    data = await _rpc(client, "tools/list")
    names = {tool["name"] for tool in data["result"]["tools"]}
    assert "icloud_list_calendars" in names
    assert "icloud_delete_contact" not in names
    assert "icloud_send_mail" not in names
    assert all(tool["annotations"]["readOnlyHint"] for tool in data["result"]["tools"])


async def test_tools_call(hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator) -> None:
    client = await hass_client()

    with patch(
        "custom_components.icloud_mcp.carddav_client.ICloudCardDav.async_search",
        new_callable=AsyncMock,
        return_value=[{"uid": "1", "full_name": "Max Mustermann"}],
    ) as search:
        is_error, payload = await _call_tool(client, "icloud_search_contacts", {"query": "max", "limit": 5})
    search.assert_awaited_once_with("max", limit=5)
    assert is_error is False
    assert payload == {"count": 1, "contacts": [{"uid": "1", "full_name": "Max Mustermann"}]}

    # ToolResult.error -> isError
    with patch(
        "custom_components.icloud_mcp.carddav_client.ICloudCardDav.async_get",
        new_callable=AsyncMock,
        side_effect=ContactNotFound("Contact 'x' not found"),
    ):
        is_error, payload = await _call_tool(client, "icloud_get_contact", {"uid": "x"})
    assert is_error is True
    assert payload["code"] == "not_found"

    # schema validation: missing required argument / wrong type
    is_error, payload = await _call_tool(client, "icloud_get_contact", {})
    assert is_error is True
    assert payload["code"] == "invalid_arguments"
    is_error, payload = await _call_tool(client, "icloud_search_contacts", {"query": "x", "limit": "viele"})
    assert is_error is True
    assert payload["code"] == "invalid_arguments"

    # unknown tool
    is_error, payload = await _call_tool(client, "icloud_nope", {})
    assert is_error is True
    assert payload["code"] == "unknown_tool"


async def test_tools_call_mail(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    client = await hass_client()
    with patch(
        "custom_components.icloud_mcp.mail.ICloudMail.async_mailboxes",
        new_callable=AsyncMock,
        return_value=[{"name": "INBOX", "unread": 2}],
    ):
        is_error, payload = await _call_tool(client, "icloud_list_mailboxes", {})
    assert is_error is False
    assert payload["mailboxes"] == [{"name": "INBOX", "unread": 2}]


async def test_requires_auth(hass: HomeAssistant, entry: MockConfigEntry, hass_client_no_auth) -> None:
    client = await hass_client_no_auth()
    response = await client.post(
        STREAMABLE_API, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=HEADERS
    )
    assert response.status == HTTPStatus.UNAUTHORIZED

    response = await client.post(
        STREAMABLE_API,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={**HEADERS, "Authorization": "Bearer not-a-token"},
    )
    assert response.status == HTTPStatus.UNAUTHORIZED


async def test_protocol_errors(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    client = await hass_client()

    # unknown method -> JSON-RPC error, HTTP 200
    data = await _rpc(client, "does/not/exist")
    assert data["error"]["code"] == -32601

    # not JSON-RPC
    response = await client.post(STREAMABLE_API, json={"hello": "world"}, headers=HEADERS)
    assert response.status == HTTPStatus.BAD_REQUEST

    # missing accept / wrong content type
    response = await client.post(
        STREAMABLE_API, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers={"Accept": "text/plain"}
    )
    assert response.status == HTTPStatus.BAD_REQUEST
    response = await client.post(
        STREAMABLE_API, data="x", headers={"Accept": "application/json", "Content-Type": "text/plain"}
    )
    assert response.status == HTTPStatus.BAD_REQUEST

    # stateless: no SSE stream, no session termination
    response = await client.get(STREAMABLE_API)
    assert response.status == HTTPStatus.METHOD_NOT_ALLOWED
    response = await client.delete(STREAMABLE_API)
    assert response.status == HTTPStatus.METHOD_NOT_ALLOWED


async def test_unload_disables_endpoint(hass: HomeAssistant, entry: MockConfigEntry, hass_client) -> None:
    client = await hass_client()
    await _rpc(client, "tools/list")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    response = await client.post(
        STREAMABLE_API, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=HEADERS
    )
    assert response.status == HTTPStatus.NOT_FOUND

    # reloading registers nothing twice and serves again
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    data = await _rpc(client, "tools/list")
    assert len(data["result"]["tools"]) == 28


async def test_two_accounts_merge_tools(hass: HomeAssistant, mock_discover: AsyncMock, hass_client) -> None:
    first = await _setup(hass, _entry())
    second = await _setup(hass, _entry("other@icloud.com"))
    client = await hass_client()
    data = await _rpc(client, "tools/list")
    tools = {tool["name"]: tool for tool in data["result"]["tools"]}
    assert len(tools) == 56
    suffix = "_other"  # derived from other@icloud.com
    assert "icloud_list_calendars" in tools
    assert f"icloud_list_calendars{suffix}" in tools
    assert "other@icloud.com" in tools[f"icloud_list_calendars{suffix}"]["description"]

    # the suffixed tool is dispatched to the second account's clients
    with (
        patch.object(first.runtime_data.carddav, "async_search", AsyncMock(return_value=[])) as search_first,
        patch.object(second.runtime_data.carddav, "async_search", AsyncMock(return_value=[])) as search_second,
    ):
        is_error, _ = await _call_tool(client, f"icloud_search_contacts{suffix}", {"query": "x"})
    assert is_error is False
    search_first.assert_not_awaited()
    search_second.assert_awaited_once_with("x", limit=50)

    # after unloading the first entry the second one keeps its (suffixed) names
    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()
    data = await _rpc(client, "tools/list")
    names = {tool["name"] for tool in data["result"]["tools"]}
    assert names == {t for t in tools if not t.endswith(suffix)}


async def test_readonly_profile_and_admin_only(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_client, hass_admin_user
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={"endpoint_admin_only": True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client()

    # read-only profile lists only non-writing tools
    resp = await client.post(
        "/api/icloud_mcp/readonly",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert resp.status == 200
    tools = (await resp.json())["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "icloud_list_events" in names and "icloud_search_mail" in names
    assert not any(
        n.startswith(
            (
                "icloud_create_",
                "icloud_delete_",
                "icloud_update_",
                "icloud_send_",
                "icloud_move_",
                "icloud_mark_",
                "icloud_run_",
            )
        )
        for n in names
    )
    assert all(t["annotations"]["readOnlyHint"] for t in tools)
    # calling a writing tool through the read-only profile is unknown there
    resp = await client.post(
        "/api/icloud_mcp/readonly",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "icloud_delete_contact", "arguments": {"uid": "x"}},
        },
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    body = await resp.json()
    assert body["result"]["isError"] is True and "Unknown tool" in body["result"]["content"][0]["text"]

    # oversized bodies are rejected
    resp = await client.post(
        "/api/icloud_mcp",
        data=b"{" + b" " * (1024 * 1024 + 10) + b"}",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert resp.status == 413

    # non-admin tokens are refused when admin-only is set
    hass_admin_user.groups = []
    resp = await client.post(
        "/api/icloud_mcp",
        json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    assert resp.status == 403
