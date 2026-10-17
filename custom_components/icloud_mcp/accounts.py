"""Helpers for running several iCloud accounts side by side."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify

from .const import CONF_ACCOUNT_LABEL, CONF_APPLE_ID


def account_label(entry: ConfigEntry) -> str:
    """Short identifier of an account used in tool names and API ids.

    Taken from the options (``account_label``) or derived from the local part of the Apple ID.
    """
    label = str(entry.options.get(CONF_ACCOUNT_LABEL) or "").strip()
    if not label:
        apple_id = str(entry.data.get(CONF_APPLE_ID, "")).strip()
        label = apple_id.split("@", 1)[0] or entry.entry_id[:8]
    slug = slugify(label, separator="_")
    return slug or entry.entry_id[:8]
