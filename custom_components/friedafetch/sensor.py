"""Sensors: upcoming birthdays of the iCloud contacts."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .accounts import account_label
from .const import CONF_APPLE_ID, CONF_ENABLE_CONTACTS, DEFAULT_ENABLE_CONTACTS, DOMAIN
from .insights import upcoming_birthdays

_LOGGER = logging.getLogger(__name__)
LOOKAHEAD_DAYS = 30
UPDATE_INTERVAL = timedelta(hours=6)


async def async_setup_entry(
    hass: HomeAssistant, entry: Any, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    if not entry.options.get(CONF_ENABLE_CONTACTS, DEFAULT_ENABLE_CONTACTS):
        return
    clients = entry.runtime_data

    async def _update() -> list[dict[str, Any]]:
        try:
            contacts = await clients.carddav.async_search(None, limit=100000)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        return upcoming_birthdays(contacts, dt_util.now().date(), days=LOOKAHEAD_DAYS)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name=f"{DOMAIN} birthdays",
        update_method=_update,
        update_interval=UPDATE_INTERVAL,
    )
    await coordinator.async_refresh()  # a failed first refresh must not block the account
    async_add_entities([BirthdaySensor(coordinator, entry)])


class BirthdaySensor(CoordinatorEntity[DataUpdateCoordinator[list[dict[str, Any]]]], SensorEntity):
    """Date of the next birthday; the attributes list everyone in the next 30 days."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_birthday"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:cake-variant"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: Any) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_next_birthday"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Frieda ({account_label(entry)})",
            manufacturer="Frieda",
            model=entry.data.get(CONF_APPLE_ID),
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> date | None:
        items = self.coordinator.data or []
        return date.fromisoformat(items[0]["date"]) if items else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self.coordinator.data or []
        first = items[0] if items else None
        same_day = [b["name"] for b in items if first and b["date"] == first["date"]]
        return {
            "names": same_day,
            "in_days": first["in_days"] if first else None,
            "turns": first["turns"] if first else None,
            "upcoming": [{k: b[k] for k in ("name", "date", "in_days", "turns")} for b in items[:15]],
        }
