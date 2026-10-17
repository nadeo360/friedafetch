"""Integration setup, LLM API registration and tool dispatch."""

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.icloud_mcp.const import (
    CONF_ALLOW_DELETE,
    CONF_ALLOW_SEND_MAIL,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_ENABLE_NOTES,
    CONF_READ_ONLY,
    DOMAIN,
    LLM_API_ID,
)

from .conftest import APP_PASSWORD, APPLE_ID


def _entry(**options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=APPLE_ID,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options=options,
    )


def _context(hass: HomeAssistant) -> llm.LLMContext:
    return llm.LLMContext(platform="test", context=Context(), language="de", assistant=None, device_id=None)


async def test_setup_registers_llm_api(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    api = await llm.async_get_api(hass, LLM_API_ID, _context(hass))
    names = {t.name for t in api.tools}
    assert "icloud_list_calendars" in names
    assert "icloud_send_mail" in names
    assert "icloud_delete_contact" in names
    assert "icloud_create_note" in names
    assert "iCloud" in api.api_prompt
    # every tool is tagged with the integration and has annotations
    for tool in api.tools:
        assert tool.integration == DOMAIN
        assert tool.annotations is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert LLM_API_ID not in [a.id for a in llm.async_get_apis(hass)]


async def test_options_restrict_tools(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = _entry(**{CONF_READ_ONLY: True, CONF_ENABLE_NOTES: False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    api = await llm.async_get_api(hass, LLM_API_ID, _context(hass))
    names = {t.name for t in api.tools}
    assert names == {
        "icloud_list_calendars",
        "icloud_list_events",
        "icloud_get_event",
        "icloud_search_contacts",
        "icloud_get_contact",
        "icloud_list_mailboxes",
        "icloud_search_mail",
        "icloud_get_mail",
    }
    assert all(t.annotations.read_only for t in api.tools)


async def test_no_send_no_delete(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = _entry(**{CONF_ALLOW_SEND_MAIL: False, CONF_ALLOW_DELETE: False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    api = await llm.async_get_api(hass, LLM_API_ID, _context(hass))
    names = {t.name for t in api.tools}
    assert "icloud_send_mail" not in names
    assert not any(n.startswith("icloud_delete_") for n in names)
    assert "icloud_create_event" in names


async def test_tool_call_and_error_mapping(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    api = await llm.async_get_api(hass, LLM_API_ID, _context(hass))

    with patch(
        "custom_components.icloud_mcp.carddav_client.ICloudCardDav.async_search",
        new_callable=AsyncMock,
        return_value=[{"uid": "1", "full_name": "Max"}],
    ) as search:
        result = await api.async_call_tool(
            llm.ToolInput(tool_name="icloud_search_contacts", tool_args={"query": "max", "limit": 5})
        )
    search.assert_awaited_once_with("max", limit=5)
    assert result.error is False
    assert result.data == {"count": 1, "contacts": [{"uid": "1", "full_name": "Max"}]}

    from custom_components.icloud_mcp.carddav_client import ContactNotFound

    with patch(
        "custom_components.icloud_mcp.carddav_client.ICloudCardDav.async_get",
        new_callable=AsyncMock,
        side_effect=ContactNotFound("Contact 'x' not found"),
    ):
        result = await api.async_call_tool(llm.ToolInput(tool_name="icloud_get_contact", tool_args={"uid": "x"}))
    assert result.error is True
    assert result.data["code"] == "not_found"

    # invalid date -> handled error, not an exception
    result = await api.async_call_tool(llm.ToolInput(tool_name="icloud_list_events", tool_args={"start": "gestern"}))
    assert result.error is True
    assert "ISO 8601" in result.data["error"]


async def test_auth_failure_triggers_reauth(hass: HomeAssistant) -> None:
    from custom_components.icloud_mcp.dav import DavAuthError

    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.icloud_mcp.caldav_client.ICloudCalDav.async_discover",
        new_callable=AsyncMock,
        side_effect=DavAuthError("401"),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"].get("source") == "reauth" for f in flows)
