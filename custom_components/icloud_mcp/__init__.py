"""iCloud MCP: expose iCloud calendars, contacts, mail and notes as LLM/MCP tools."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import client_context

from .caldav_client import ICloudCalDav
from .carddav_client import ICloudCardDav
from .const import (
    CALDAV_URL,
    CARDDAV_URL,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_FROM_ADDRESS,
    DOMAIN,
    IMAP_HOST,
    IMAP_PORT,
    LLM_API_ID,
    LLM_API_NAME,
    NOTES_MAILBOX,
    REQUEST_TIMEOUT,
    SMTP_HOST,
    SMTP_PORT,
)
from .dav import DavAuthError, DavClient, DavError
from .llm_api import ICloudClients, ICloudLLMAPI
from .mail import ICloudMail
from .mcp_http import STREAMABLE_API
from .mcp_http import async_register as async_register_mcp_http
from .notes import ICloudNotes

_LOGGER = logging.getLogger(__name__)

type ICloudConfigEntry = ConfigEntry[ICloudClients]


def build_clients(hass: HomeAssistant, entry: ConfigEntry) -> ICloudClients:
    """Create the iCloud clients for a config entry."""
    apple_id: str = entry.data[CONF_APPLE_ID]
    password: str = entry.data[CONF_APP_PASSWORD]
    session = async_get_clientsession(hass)
    dav = DavClient(session, apple_id, password, timeout=REQUEST_TIMEOUT)
    tz = dt_util.get_default_time_zone()
    mail = ICloudMail(
        apple_id,
        password,
        from_address=entry.options.get(CONF_FROM_ADDRESS) or entry.data.get(CONF_FROM_ADDRESS) or apple_id,
        imap_host=IMAP_HOST,
        imap_port=IMAP_PORT,
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        timeout=REQUEST_TIMEOUT,
        ssl_context=client_context(),
    )
    return ICloudClients(
        caldav=ICloudCalDav(dav, CALDAV_URL, tz),
        carddav=ICloudCardDav(dav, CARDDAV_URL),
        mail=mail,
        notes=ICloudNotes(mail, NOTES_MAILBOX),
        options=dict(entry.options),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ICloudConfigEntry) -> bool:
    """Set up iCloud MCP from a config entry."""
    clients = build_clients(hass, entry)

    try:
        await clients.caldav.async_discover()
    except DavAuthError as err:
        raise ConfigEntryAuthFailed("iCloud rejected the app-specific password") from err
    except DavError as err:
        raise ConfigEntryNotReady(f"Cannot reach iCloud: {err}") from err

    entry.runtime_data = clients

    apple_id = entry.data[CONF_APPLE_ID]
    try:
        api = ICloudLLMAPI(hass, clients, api_id=LLM_API_ID, name=LLM_API_NAME)
        unregister = llm.async_register_api(hass, api)
    except HomeAssistantError:
        # a second iCloud account: register under a distinct id
        api_id = f"{LLM_API_ID}_{entry.entry_id[:8]}"
        api = ICloudLLMAPI(hass, clients, api_id=api_id, name=f"{LLM_API_NAME} ({apple_id})")
        try:
            unregister = llm.async_register_api(hass, api)
        except HomeAssistantError as err:
            raise ConfigEntryError(f"LLM API '{api_id}' already registered") from err
    entry.async_on_unload(unregister)
    entry.async_on_unload(clients.mail.async_close)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Own Streamable-HTTP MCP endpoint (registered once; serves the tools of all loaded entries)
    integration = await async_get_integration(hass, DOMAIN)
    async_register_mcp_http(hass, str(integration.version or "0.0.0"))
    _LOGGER.info("iCloud MCP ready; LLM API '%s' registered, MCP endpoint at %s", api.id, STREAMABLE_API)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ICloudConfigEntry) -> bool:
    """Unload a config entry (on_unload callbacks do the work)."""
    return True
