"""Usage counters: how many tool calls each account served (reading/writing, per day, per tool, per source).

Only counts are kept, never arguments or results. The counters live in one store for the
whole instance; MCP clients that announced themselves on the Frieda endpoint are remembered
by name so the panel can show who is connected.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.usage"
DAYS_KEPT = 31
MAX_TOOLS = 60
MAX_CLIENTS = 20
SAVE_DELAY = 15

DATA_USAGE: HassKey[UsageStats] = HassKey(f"{DOMAIN}_usage")

_EMPTY = {"read": 0, "write": 0, "error": 0}


def _now() -> datetime:
    return dt_util.now()


class UsageStats:
    """Counters for all accounts of this instance."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {"accounts": {}, "clients": {}}
        self._loaded = False

    async def async_load(self) -> None:
        if self._loaded:
            return
        data = await self._store.async_load() or {}
        self._data = {"accounts": dict(data.get("accounts") or {}), "clients": dict(data.get("clients") or {})}
        self._loaded = True

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self._data, SAVE_DELAY)

    def _account(self, entry_id: str) -> dict[str, Any]:
        acc = self._data["accounts"].setdefault(entry_id, {})
        acc.setdefault("since", _now().isoformat(timespec="seconds"))
        acc.setdefault("total", dict(_EMPTY))
        acc.setdefault("days", {})
        acc.setdefault("tools", {})
        acc.setdefault("sources", {})
        acc.setdefault("last", None)
        return acc

    async def async_record(self, entry_id: str, tool: str, *, write: bool, ok: bool, source: str | None) -> None:
        """Count one tool call."""
        await self.async_load()
        acc = self._account(entry_id)
        now = _now()
        kind = "write" if write else "read"
        day = acc["days"].setdefault(now.date().isoformat(), dict(_EMPTY))
        for bucket in (acc["total"], day):
            bucket[kind] = int(bucket.get(kind, 0)) + 1
            if not ok:
                bucket["error"] = int(bucket.get("error", 0)) + 1
        tools = acc["tools"]
        tools[tool] = int(tools.get(tool, 0)) + 1
        if len(tools) > MAX_TOOLS:
            del tools[min(tools, key=tools.get)]
        src = source or "unknown"
        acc["sources"][src] = int(acc["sources"].get(src, 0)) + 1
        acc["last"] = {"time": now.isoformat(timespec="seconds"), "tool": tool, "source": src, "ok": ok}
        cutoff = (now.date() - timedelta(days=DAYS_KEPT - 1)).isoformat()
        for key in [d for d in acc["days"] if d < cutoff]:
            del acc["days"][key]
        self._save()

    async def async_note_client(self, name: str, version: str | None, profile: str) -> None:
        """Remember an MCP client that initialised a session on the Frieda endpoint."""
        await self.async_load()
        name = (name or "unknown")[:80]
        now = _now().isoformat(timespec="seconds")
        clients = self._data["clients"]
        known = clients.get(name) or {"first_seen": now}
        clients[name] = {**known, "version": (version or "")[:40] or None, "profile": profile, "last_seen": now}
        if len(clients) > MAX_CLIENTS:
            del clients[min(clients, key=lambda n: clients[n].get("last_seen") or "")]
        self._save()

    def clients(self) -> list[dict[str, Any]]:
        items = [{"name": name, **info} for name, info in self._data["clients"].items()]
        return sorted(items, key=lambda c: c.get("last_seen") or "", reverse=True)

    def summary(self, entry_id: str, days: int = 14) -> dict[str, Any]:
        """Totals for today, 7 and 30 days, a per-day series and the most used tools."""
        acc = self._data["accounts"].get(entry_id)
        if not acc:
            return {
                "since": None,
                "today": dict(_EMPTY),
                "week": dict(_EMPTY),
                "month": dict(_EMPTY),
                "total": dict(_EMPTY),
                "series": [],
                "tools": [],
                "sources": {},
                "last": None,
            }
        today = _now().date()

        def window(n: int) -> dict[str, int]:
            out = dict(_EMPTY)
            for offset in range(n):
                bucket = acc["days"].get((today - timedelta(days=offset)).isoformat()) or {}
                for key in out:
                    out[key] += int(bucket.get(key, 0))
            return out

        series = []
        for offset in range(days - 1, -1, -1):
            day: date = today - timedelta(days=offset)
            bucket = acc["days"].get(day.isoformat()) or {}
            series.append({"date": day.isoformat(), **{k: int(bucket.get(k, 0)) for k in _EMPTY}})
        tools = sorted(acc["tools"].items(), key=lambda kv: kv[1], reverse=True)[:8]
        return {
            "since": acc.get("since"),
            "today": window(1),
            "week": window(7),
            "month": window(30),
            "total": {k: int(acc["total"].get(k, 0)) for k in _EMPTY},
            "series": series,
            "tools": [{"tool": name, "count": count} for name, count in tools],
            "sources": dict(acc["sources"]),
            "last": acc.get("last"),
        }

    async def async_reset(self, entry_id: str) -> None:
        await self.async_load()
        self._data["accounts"].pop(entry_id, None)
        self._save()


async def async_get_usage(hass: HomeAssistant) -> UsageStats:
    """The instance-wide usage counters (created and loaded on first use)."""
    stats = hass.data.get(DATA_USAGE)
    if stats is None:
        stats = hass.data[DATA_USAGE] = UsageStats(hass)
    await stats.async_load()
    return stats
