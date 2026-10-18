"""Live updates for the panels.

Whatever changes an account's data (a new change-log entry, an approval, a counted tool call, a lock) sends a short
signal with the account and the topic. Open panels subscribe through the websocket and reload only that part, so
their tables follow without polling.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

SIGNAL_PANEL = f"{DOMAIN}_panel_changed"

# topics: audit (change log), approvals, usage (counters and quotas), overview (clients, locks)
TOPICS = ("audit", "approvals", "usage", "overview")


@callback
def async_notify(hass: HomeAssistant, entry_id: str | None, topic: str) -> None:
    """Tell open panels that a part of an account (or of all accounts, entry_id None) changed."""
    async_dispatcher_send(hass, SIGNAL_PANEL, entry_id, topic)
