"""Diagnostics support for Frieda."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ICloudConfigEntry
from .const import CONF_APP_PASSWORD
from .llm_api import build_tools

TO_REDACT = {CONF_APP_PASSWORD}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ICloudConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    clients = entry.runtime_data
    calendars: list[dict[str, Any]] | str
    try:
        calendars = [c.to_dict() for c in await clients.caldav.async_calendars()]
    except Exception as err:  # noqa: BLE001
        calendars = f"error: {err}"
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "tools": [t.name for t in build_tools(clients)],
        "calendars": calendars,
        "extensions": sorted(clients.extensions),
        # what the IMAP server offers (CONDSTORE lets Frieda Postfach ask only for changed flags)
        "imap": {"capabilities": clients.mail.capabilities, "condstore": clients.mail.condstore},
    }
