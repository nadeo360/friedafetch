"""Audit log of writing actions, persisted in Home Assistant storage and mirrored as events."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import AUDIT_EVENT, AUDIT_MAX_ENTRIES, DOMAIN

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
_MAX_STR = 200
_DROP_KEYS = {"body", "html", "raw_headers", "password", "app_password"}


def sanitize_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Shorten tool arguments for the log; bodies are replaced by their length."""
    out: dict[str, Any] = {}
    for key, value in (params or {}).items():
        if key in _DROP_KEYS:
            out[f"{key}_chars"] = len(str(value)) if value is not None else 0
            continue
        if isinstance(value, str):
            out[key] = value if len(value) <= _MAX_STR else value[:_MAX_STR] + "…"
        elif isinstance(value, list):
            out[key] = value[:50] if len(value) <= 50 else [*value[:50], f"… (+{len(value) - 50})"]
        elif isinstance(value, dict):
            out[key] = sanitize_params(value)
        else:
            out[key] = value
    return out


class AuditLog:
    """Ring buffer of the last actions of one account."""

    def __init__(self, hass: HomeAssistant, entry_id: str, account: str, max_entries: int = AUDIT_MAX_ENTRIES) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._account = account
        self._max = max_entries
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.audit.{entry_id}")
        self._entries: list[dict[str, Any]] = []
        self._loaded = False
        self._seq = 0

    async def async_load(self) -> None:
        if self._loaded:
            return
        data = await self._store.async_load() or {}
        self._entries = list(data.get("entries", []))[-self._max :]
        self._seq = int(data.get("seq", len(self._entries)))
        self._loaded = True

    def _data(self) -> dict[str, Any]:
        return {"entries": self._entries, "seq": self._seq}

    async def _user_name(self, user_id: str | None) -> str | None:
        if not user_id:
            return None
        try:
            user = await self._hass.auth.async_get_user(user_id)
        except Exception:  # noqa: BLE001
            return None
        return user.name if user else None

    async def async_record(
        self,
        *,
        tool: str,
        action: str,
        params: dict[str, Any] | None,
        result: str,
        client: str | None = None,
        user_id: str | None = None,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append an entry, persist it and fire the Home Assistant event."""
        await self.async_load()
        self._seq += 1
        entry = {
            "id": self._seq,
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            "entry_id": self._entry_id,
            "account": self._account,
            "tool": tool,
            "action": action,
            "params": sanitize_params(params),
            "result": result,  # ok | error | blocked
            "error": error,
            "client": client,
            "user_id": user_id,
            "user": await self._user_name(user_id),
            "details": details or {},
        }
        self._entries.append(entry)
        if len(self._entries) > self._max:
            del self._entries[: len(self._entries) - self._max]
        self._store.async_delay_save(self._data, 2)
        self._hass.bus.async_fire(
            AUDIT_EVENT, {k: v for k, v in entry.items() if k != "details"} | {"details": details or {}}
        )
        return entry

    def entries(self, limit: int = 100, result: str | None = None) -> list[dict[str, Any]]:
        items = [e for e in self._entries if result is None or e.get("result") == result]
        return list(reversed(items[-limit:]))

    async def async_clear(self) -> None:
        await self.async_load()
        self._entries = []
        await self._store.async_save(self._data())
