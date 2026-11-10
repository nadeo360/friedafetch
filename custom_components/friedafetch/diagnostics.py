"""Diagnostics support for Frieda."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ICloudConfigEntry
from .const import (
    CONF_ACCOUNT_LABEL,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_APPROVAL_NOTIFY,
    CONF_ATTACHMENTS_DIR,
    CONF_FROM_ADDRESS,
    CONF_HIDDEN_MAILBOXES,
    CONF_PROTECTED_CALENDARS,
    CONF_PROTECTED_MAILBOXES,
    CONF_SEND_ALLOWLIST,
)
from .llm_api import build_tools

# diagnostics get pasted into public issues: nothing that names the account, its people, folders or calendars
TO_REDACT = {
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_FROM_ADDRESS,
    CONF_ACCOUNT_LABEL,
    CONF_SEND_ALLOWLIST,
    CONF_APPROVAL_NOTIFY,
    CONF_PROTECTED_CALENDARS,
    CONF_PROTECTED_MAILBOXES,
    CONF_HIDDEN_MAILBOXES,
    CONF_ATTACHMENTS_DIR,
}
CALENDAR_REDACT = {"id", "name", "description"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ICloudConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    clients = entry.runtime_data
    calendars: list[dict[str, Any]] | str
    try:
        calendars = [async_redact_data(c.to_dict(), CALENDAR_REDACT) for c in await clients.caldav.async_calendars()]
    except Exception as err:  # noqa: BLE001
        calendars = f"error: {err}"
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "tools": [t.name for t in build_tools(clients)],
        "calendars": calendars,
        "extensions": sorted(clients.extensions),
        # what the IMAP server offers (CONDSTORE lets Frieda Postfach ask only for changed flags)
        "imap": {"capabilities": clients.mail.capabilities, "condstore": clients.mail.condstore},
    }
