"""Frieda: expose iCloud calendars, contacts, mail and notes as LLM/MCP tools."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import client_context

from .accounts import account_label
from .approvals import ApprovalManager
from .audit import AuditLog
from .caldav_client import ICloudCalDav
from .carddav_client import ICloudCardDav
from .const import (
    CALDAV_URL,
    CARDDAV_URL,
    CONF_ALLOW_DELETE,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_APPROVAL_DELETE,
    CONF_APPROVAL_MASS,
    CONF_APPROVAL_NOTIFY,
    CONF_APPROVAL_SEND,
    CONF_APPROVAL_TIMEOUT,
    CONF_ENABLE_MAIL,
    CONF_FROM_ADDRESS,
    CONF_READ_ONLY,
    CONF_RULES_AUTO,
    CONF_RULES_INTERVAL,
    DEFAULT_ALLOW_DELETE,
    DEFAULT_APPROVAL_DELETE,
    DEFAULT_APPROVAL_MASS,
    DEFAULT_APPROVAL_SEND,
    DEFAULT_APPROVAL_TIMEOUT,
    DEFAULT_ENABLE_MAIL,
    DEFAULT_READ_ONLY,
    DEFAULT_RULES_AUTO,
    DEFAULT_RULES_INTERVAL,
    DOMAIN,
    IMAP_HOST,
    IMAP_PORT,
    LLM_API_ID,
    LLM_API_NAME,
    MAX_RULES_INTERVAL,
    MIN_RULES_INTERVAL,
    MOBILE_ACTION_EVENT,
    NOTES_MAILBOX,
    REQUEST_TIMEOUT,
    SMTP_HOST,
    SMTP_PORT,
)
from .dav import DavAuthError, DavClient, DavError
from .frontend import async_remove_frontend, async_setup_frontend
from .guard import Guard
from .llm_api import ICloudClients, ICloudLLMAPI
from .mail import ICloudMail
from .mcp_http import STREAMABLE_API
from .mcp_http import async_register as async_register_mcp_http
from .notes import ICloudNotes
from .rules import RuleEngine
from .util import clamp

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
    """Set up Frieda from a config entry."""
    clients = build_clients(hass, entry)

    try:
        await clients.caldav.async_discover()
    except DavAuthError as err:
        raise ConfigEntryAuthFailed("iCloud rejected the app-specific password") from err
    except DavError as err:
        raise ConfigEntryNotReady(f"Cannot reach iCloud: {err}") from err

    entry.runtime_data = clients

    # inbox rules (stored in HA, applied by this integration)
    opts = entry.options
    clients.guard = Guard(dict(opts))
    audit = AuditLog(hass, entry.entry_id, entry.data[CONF_APPLE_ID])
    await audit.async_load()
    clients.audit = audit
    if (
        opts.get(CONF_APPROVAL_SEND, DEFAULT_APPROVAL_SEND)
        or opts.get(CONF_APPROVAL_DELETE, DEFAULT_APPROVAL_DELETE)
        or int(opts.get(CONF_APPROVAL_MASS, DEFAULT_APPROVAL_MASS) or 0) > 0
    ):
        approvals = ApprovalManager(
            hass,
            entry.entry_id,
            entry.data[CONF_APPLE_ID],
            audit=audit,
            notify_service=opts.get(CONF_APPROVAL_NOTIFY),
            timeout_minutes=int(opts.get(CONF_APPROVAL_TIMEOUT, DEFAULT_APPROVAL_TIMEOUT) or DEFAULT_APPROVAL_TIMEOUT),
            language=hass.config.language or "en",
        )
        clients.approvals = approvals
        entry.async_on_unload(hass.bus.async_listen(MOBILE_ACTION_EVENT, approvals.handle_mobile_action))
        entry.async_on_unload(approvals.shutdown)
    rules = RuleEngine(
        hass,
        entry.entry_id,
        clients.mail,
        allow_delete=opts.get(CONF_ALLOW_DELETE, DEFAULT_ALLOW_DELETE),
        guard=clients.guard,
        audit=audit,
    )
    await rules.async_load()
    clients.rules = rules
    if (
        opts.get(CONF_ENABLE_MAIL, DEFAULT_ENABLE_MAIL)
        and opts.get(CONF_RULES_AUTO, DEFAULT_RULES_AUTO)
        and not opts.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)
    ):
        minutes = clamp(opts.get(CONF_RULES_INTERVAL), DEFAULT_RULES_INTERVAL, MAX_RULES_INTERVAL)
        minutes = max(MIN_RULES_INTERVAL, minutes)

        async def _apply_rules(_now: datetime) -> None:
            if not rules.has_enabled_rules:
                return
            try:
                report = await rules.async_run(scope="new")
            except Exception as err:  # noqa: BLE001 - keep the timer alive
                _LOGGER.warning("Automatic inbox rules failed: %s", err)
                return
            if report["matched"]:
                _LOGGER.info("Inbox rules: %s messages checked, %s matched", report["checked"], report["matched"])

        entry.async_on_unload(async_track_time_interval(hass, _apply_rules, timedelta(minutes=minutes)))

    apple_id = entry.data[CONF_APPLE_ID]
    label = account_label(entry)
    try:
        api = ICloudLLMAPI(hass, clients, api_id=LLM_API_ID, name=LLM_API_NAME, account=apple_id)
        unregister = llm.async_register_api(hass, api)
    except HomeAssistantError:
        # a further iCloud account: register under a distinct, readable id
        api_id = f"{LLM_API_ID}_{label}"
        api = ICloudLLMAPI(hass, clients, api_id=api_id, name=f"{LLM_API_NAME} – {label}", account=apple_id)
        try:
            unregister = llm.async_register_api(hass, api)
        except HomeAssistantError as err:
            raise ConfigEntryError(f"LLM API '{api_id}' already registered") from err
    entry.async_on_unload(unregister)
    entry.async_on_unload(clients.mail.async_close)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Sidebar panel + websocket API for managing the rules
    try:
        await async_setup_frontend(hass, str((await async_get_integration(hass, DOMAIN)).version or "0"))
    except Exception as err:  # noqa: BLE001 - the panel is optional
        _LOGGER.warning("Could not register the Frieda panel: %s", err)

    # Own Streamable-HTTP MCP endpoint (registered once; serves the tools of all loaded entries)
    integration = await async_get_integration(hass, DOMAIN)
    async_register_mcp_http(hass, str(integration.version or "0.0.0"))
    _LOGGER.info("Frieda ready; LLM API '%s' registered, MCP endpoint at %s", api.id, STREAMABLE_API)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ICloudConfigEntry) -> bool:
    """Unload a config entry (on_unload callbacks do the rest)."""
    others = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED
    ]
    if not others:
        async_remove_frontend(hass)
    return True
