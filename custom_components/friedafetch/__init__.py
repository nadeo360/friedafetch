"""Frieda: expose iCloud calendars, contacts, mail and notes as LLM/MCP tools."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import client_context

from .accounts import account_label
from .approvals import ApprovalManager
from .attachments import AttachmentStore
from .audit import AuditLog
from .caldav_client import ICloudCalDav
from .carddav_client import ICloudCardDav
from .const import (
    CALDAV_URL,
    CARDDAV_URL,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_APPROVAL_DELETE,
    CONF_APPROVAL_MASS,
    CONF_APPROVAL_NOTIFY,
    CONF_APPROVAL_SEND,
    CONF_APPROVAL_TIMEOUT,
    CONF_ATTACHMENTS_DIR,
    CONF_ENABLE_MAIL,
    CONF_FROM_ADDRESS,
    CONF_SEND_DELAY,
    DEFAULT_APPROVAL_DELETE,
    DEFAULT_APPROVAL_MASS,
    DEFAULT_APPROVAL_SEND,
    DEFAULT_APPROVAL_TIMEOUT,
    DEFAULT_ATTACHMENTS_SUBDIR,
    DEFAULT_ENABLE_MAIL,
    DEFAULT_SEND_DELAY,
    DOMAIN,
    IMAP_HOST,
    IMAP_PORT,
    LLM_API_ID,
    LLM_API_NAME,
    MOBILE_ACTION_EVENT,
    NOTES_MAILBOX,
    REQUEST_TIMEOUT,
    SMTP_HOST,
    SMTP_PORT,
)
from .dav import DavAuthError, DavClient, DavError
from .frontend import async_remove_frontend, async_setup_frontend
from .guard import Guard
from .install_check import async_check_install
from .llm_api import ICloudClients, ICloudLLMAPI
from .mail import ICloudMail
from .mcp_http import STREAMABLE_API
from .mcp_http import async_register as async_register_mcp_http
from .notes import ICloudNotes
from .state import AccountState
from .usage import async_get_usage

_LOGGER = logging.getLogger(__name__)

type ICloudConfigEntry = ConfigEntry[ICloudClients]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


# Extensions (e.g. Frieda Postfach) listen to these to attach to an account after it (re)loaded.
SIGNAL_ACCOUNT_READY = f"{DOMAIN}_account_ready"
SIGNAL_ACCOUNT_UNLOADED = f"{DOMAIN}_account_unloaded"
EXTENSION_MAIL_DOMAIN = "friedafetch_mail"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (once per start): install check."""
    try:
        await async_check_install(hass)
    except Exception as err:  # noqa: BLE001 - the check must never block the setup
        _LOGGER.debug("Install location check failed: %s", err)
    return True


def _attachment_base(hass: HomeAssistant, configured: str | None) -> Path | None:
    """The folder for stored attachments, if Home Assistant allows writing there (blocking)."""
    if configured:
        base = Path(configured)
    else:
        media = (hass.config.media_dirs or {}).get("local") or hass.config.path("media")
        base = Path(media) / DEFAULT_ATTACHMENTS_SUBDIR
    if not base.is_absolute():
        base = Path(hass.config.path(str(base)))
    if not hass.config.is_allowed_path(str(base)):
        return None
    return base


def build_clients(hass: HomeAssistant, entry: ConfigEntry) -> ICloudClients:
    """Create the iCloud clients for a config entry."""
    apple_id: str = entry.data[CONF_APPLE_ID]
    password: str = entry.data[CONF_APP_PASSWORD]
    session = async_get_clientsession(hass)
    dav = DavClient(session, apple_id, password, timeout=REQUEST_TIMEOUT)
    tz = dt_util.get_default_time_zone()

    shared: dict[str, Any] = {}  # mailbox list, shared by all connections of the account

    def new_mail() -> ICloudMail:
        """A further, independent IMAP/SMTP client for the same account (e.g. for background automation)."""
        return ICloudMail(
            apple_id,
            password,
            from_address=entry.options.get(CONF_FROM_ADDRESS) or entry.data.get(CONF_FROM_ADDRESS) or apple_id,
            imap_host=IMAP_HOST,
            imap_port=IMAP_PORT,
            smtp_host=SMTP_HOST,
            smtp_port=SMTP_PORT,
            timeout=REQUEST_TIMEOUT,
            ssl_context=client_context(),
            shared=shared,
        )

    mail = new_mail()
    clients = ICloudClients(
        caldav=ICloudCalDav(dav, CALDAV_URL, tz),
        carddav=ICloudCardDav(dav, CARDDAV_URL),
        mail=mail,
        notes=ICloudNotes(mail, NOTES_MAILBOX),
        options=dict(entry.options),
    )
    clients.mail_factory = new_mail
    return clients


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
    # quotas, injection locks and approvals survive restarts and reloads
    state = AccountState(hass, entry.entry_id)
    stored = await state.async_load()
    clients.guard = Guard(dict(opts))
    clients.guard.restore(stored.get("quotas"))
    clients.guard.on_change = state.changed
    state.register("quotas", clients.guard.export)
    clients.restore_locks(stored.get("locks"))
    clients.on_change = state.changed
    state.register("locks", clients.export_locks)
    entry.async_on_unload(state.async_flush)
    audit = AuditLog(hass, entry.entry_id, entry.data[CONF_APPLE_ID])
    await audit.async_load()
    clients.audit = audit
    if (
        opts.get(CONF_APPROVAL_SEND, DEFAULT_APPROVAL_SEND)
        or opts.get(CONF_APPROVAL_DELETE, DEFAULT_APPROVAL_DELETE)
        or int(opts.get(CONF_APPROVAL_MASS, DEFAULT_APPROVAL_MASS) or 0) > 0
        or int(opts.get(CONF_SEND_DELAY, DEFAULT_SEND_DELAY) or 0) > 0
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
        await approvals.async_record_interrupted(approvals.restore(stored.get("approvals")))
        approvals.on_change = state.changed
        state.register("approvals", approvals.export)
        entry.async_on_unload(hass.bus.async_listen(MOBILE_ACTION_EVENT, approvals.handle_mobile_action))
        entry.async_on_unload(approvals.shutdown)
    clients.entry_id = entry.entry_id
    clients.usage = await async_get_usage(hass)

    # attachments (tool icloud_save_attachments; extensions may use the store too)
    if opts.get(CONF_ENABLE_MAIL, DEFAULT_ENABLE_MAIL):
        base = await hass.async_add_executor_job(_attachment_base, hass, opts.get(CONF_ATTACHMENTS_DIR))
        if base is not None:
            clients.attachments = AttachmentStore(hass, clients.mail, base)
        elif opts.get(CONF_ATTACHMENTS_DIR):
            _LOGGER.warning(
                "Attachment folder %s is not allowed; add it to allowlist_external_dirs", opts[CONF_ATTACHMENTS_DIR]
            )

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
    async_dispatcher_send(hass, SIGNAL_ACCOUNT_READY, entry.entry_id)

    async def _check_moved_rules(_hass: HomeAssistant) -> None:
        await _async_check_moved_rules(hass, entry)

    entry.async_on_unload(async_at_started(hass, _check_moved_rules))
    return True


async def _async_check_moved_rules(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Inbox rules moved to Frieda Postfach (2.0): point users with existing rules to it."""
    issue_id = f"rules_moved_{entry.entry_id}"
    stored = Path(hass.config.path(".storage", f"{DOMAIN}.rules.{entry.entry_id}"))
    has_rules = await hass.async_add_executor_job(stored.exists)
    if has_rules and EXTENSION_MAIL_DOMAIN not in hass.config.components:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="rules_moved",
            translation_placeholders={"account": account_label(entry)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


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
    async_dispatcher_send(hass, SIGNAL_ACCOUNT_UNLOADED, entry.entry_id)
    return True
