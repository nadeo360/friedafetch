"""Frieda: expose iCloud calendars, contacts, mail and notes as LLM/MCP tools."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
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
    CONF_ALLOW_DELETE,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_APPROVAL_DELETE,
    CONF_APPROVAL_MASS,
    CONF_APPROVAL_NOTIFY,
    CONF_APPROVAL_SEND,
    CONF_APPROVAL_TIMEOUT,
    CONF_ATTACHMENTS_DIR,
    CONF_DIGEST_TIME,
    CONF_ENABLE_MAIL,
    CONF_FROM_ADDRESS,
    CONF_READ_ONLY,
    CONF_RULES_AUTO,
    CONF_RULES_INTERVAL,
    CONF_RULES_PUSH,
    DEFAULT_ALLOW_DELETE,
    DEFAULT_APPROVAL_DELETE,
    DEFAULT_APPROVAL_MASS,
    DEFAULT_APPROVAL_SEND,
    DEFAULT_APPROVAL_TIMEOUT,
    DEFAULT_ATTACHMENTS_SUBDIR,
    DEFAULT_ENABLE_MAIL,
    DEFAULT_READ_ONLY,
    DEFAULT_RULES_AUTO,
    DEFAULT_RULES_INTERVAL,
    DEFAULT_RULES_PUSH,
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
    SERVICE_SEND_DIGEST,
    SMTP_HOST,
    SMTP_PORT,
)
from .dav import DavAuthError, DavClient, DavError
from .digest import async_send_digest
from .frontend import async_remove_frontend, async_setup_frontend
from .guard import Guard
from .idle import MailWatcher
from .install_check import async_check_install
from .llm_api import ICloudClients, ICloudLLMAPI
from .mail import ICloudMail
from .mcp_http import STREAMABLE_API
from .mcp_http import async_register as async_register_mcp_http
from .notes import ICloudNotes
from .rules import RuleEngine
from .schema import vol
from .util import clamp

_LOGGER = logging.getLogger(__name__)

type ICloudConfigEntry = ConfigEntry[ICloudClients]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


PLATFORMS = [Platform.SENSOR]
SEND_DIGEST_SCHEMA = vol.Schema({vol.Optional("account"): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (once per start): install check and services."""
    try:
        await async_check_install(hass)
    except Exception as err:  # noqa: BLE001 - the check must never block the setup
        _LOGGER.debug("Install location check failed: %s", err)

    async def _send_digest(call: ServiceCall) -> ServiceResponse:
        wanted = (call.data.get("account") or "").strip().lower()
        results = []
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            label = account_label(entry)
            if wanted and wanted not in (label.lower(), str(entry.data.get(CONF_APPLE_ID, "")).lower(), entry.entry_id):
                continue
            result = await async_send_digest(hass, entry.runtime_data, label if _multiple(hass) else "")
            results.append({"account": label, "sent_to": result["sent_to"], "message": result["message"]})
        if not results:
            raise HomeAssistantError(f"No loaded Frieda account matches '{wanted}'")
        return {"results": results}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_DIGEST,
        _send_digest,
        schema=SEND_DIGEST_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


def _multiple(hass: HomeAssistant) -> bool:
    return len(hass.config_entries.async_loaded_entries(DOMAIN)) > 1


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
        interval = timedelta(minutes=minutes)
        rules.set_automation(True, minutes, dt_util.now() + interval)

        async def _apply_rules(now: datetime) -> None:
            next_run = dt_util.as_local(now) + interval
            if not rules.has_enabled_rules:
                rules.note_check("no_enabled_rules", next_run)
                return
            try:
                report = await rules.async_run(scope="new", trigger="auto")
            except Exception as err:  # noqa: BLE001 - keep the timer alive
                _LOGGER.warning("Automatic inbox rules failed: %s", err)
                rules.note_check("error", next_run, str(err))
                return
            rules.note_check("error" if report["errors"] else "ran", next_run)
            if report["matched"]:
                _LOGGER.info("Inbox rules: %s messages checked, %s matched", report["checked"], report["matched"])

        entry.async_on_unload(async_track_time_interval(hass, _apply_rules, interval))

        if opts.get(CONF_RULES_PUSH, DEFAULT_RULES_PUSH):

            async def _on_new_mail() -> None:
                if not any(r.mailbox == "INBOX" for r in rules.enabled_rules()):
                    return
                report = await rules.async_run(scope="new", trigger="push", mailbox="INBOX")
                rules.note_check("error" if report["errors"] else "ran", None)

            watcher = MailWatcher(
                username=entry.data[CONF_APPLE_ID],
                password=entry.data[CONF_APP_PASSWORD],
                host=IMAP_HOST,
                port=IMAP_PORT,
                on_new_mail=_on_new_mail,
                ssl_context=client_context(),
                timeout=REQUEST_TIMEOUT,
            )
            clients.watcher = watcher
            rules.push = watcher
            watcher.start(lambda coro, name: entry.async_create_background_task(hass, coro, name))
            entry.async_on_unload(watcher.async_stop)
    else:
        rules.set_automation(False, None, None)

    # attachments (tool + rule action) and the daily overview
    if opts.get(CONF_ENABLE_MAIL, DEFAULT_ENABLE_MAIL):
        base = await hass.async_add_executor_job(_attachment_base, hass, opts.get(CONF_ATTACHMENTS_DIR))
        if base is not None:
            clients.attachments = AttachmentStore(hass, clients.mail, base)
            rules.attachment_saver = clients.attachments.async_save
        elif opts.get(CONF_ATTACHMENTS_DIR):
            _LOGGER.warning(
                "Attachment folder %s is not allowed; add it to allowlist_external_dirs", opts[CONF_ATTACHMENTS_DIR]
            )
    if digest_time := _parse_clock(opts.get(CONF_DIGEST_TIME)):

        async def _digest(now: datetime) -> None:
            try:
                await async_send_digest(hass, clients, account_label(entry) if _multiple(hass) else "")
            except Exception as err:  # noqa: BLE001 - keep the schedule alive
                _LOGGER.warning("Daily overview failed: %s", err)

        entry.async_on_unload(
            async_track_time_change(hass, _digest, hour=digest_time[0], minute=digest_time[1], second=0)
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _parse_clock(value: Any) -> tuple[int, int] | None:
    """'07:30' -> (7, 30); empty or invalid -> None."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        hour, minute = (int(x) for x in text.split(":")[:2])
    except ValueError:
        _LOGGER.warning("Invalid time for the daily overview: %s (expected HH:MM)", text)
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute
