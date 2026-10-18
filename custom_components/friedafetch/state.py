"""Runtime state of one account that must survive restarts: quotas, injection locks and approvals."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
SAVE_DELAY = 2  # seconds; several changes in a row are written once


class AccountState:
    """Collects the parts from their owners and writes them shortly after every change."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.state.{entry_id}")
        self._parts: dict[str, Callable[[], Any]] = {}

    async def async_load(self) -> dict[str, Any]:
        data = await self._store.async_load()
        return data if isinstance(data, dict) else {}

    def register(self, key: str, export: Callable[[], Any]) -> None:
        self._parts[key] = export

    @callback
    def changed(self) -> None:
        self._store.async_delay_save(self._data, SAVE_DELAY)

    async def async_flush(self) -> None:
        """Write now (on unload), so a reload reads the latest state."""
        await self._store.async_save(self._data())

    async def async_remove(self) -> None:
        await self._store.async_remove()

    def _data(self) -> dict[str, Any]:
        return {key: export() for key, export in self._parts.items()}
