"""Insight tools across calendars and contacts: free time, birthdays, duplicates."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.util import dt as dt_util

from .insights import duplicate_contacts, free_slots, upcoming_birthdays
from .schema import vol
from .tool_base import ICloudTool
from .util import clamp

_LOGGER = logging.getLogger(__name__)


class FindFreeTime(ICloudTool):
    name = "icloud_find_free_time"
    feature = "calendar"
    description = (
        "Find free time slots of a given length in the user's calendars, e.g. to propose meeting times. "
        "Only working hours (default 08:00-18:00) and weekdays are considered unless changed. "
        "All-day and 'free' (transparent) events do not block time."
    )
    parameters = vol.Schema(
        {
            vol.Required("duration_minutes", description="Length of the wanted slot in minutes"): int,
            vol.Optional("start", description="Search from (ISO 8601). Default: now"): str,
            vol.Optional("end", description="Search until (ISO 8601). Default: start + 7 days"): str,
            vol.Optional("calendar_ids", description="Only consider these calendars (default: all)"): [str],
            vol.Optional("day_start", description="Earliest time of day, HH:MM (default 08:00)"): str,
            vol.Optional("day_end", description="Latest time of day, HH:MM (default 18:00)"): str,
            vol.Optional("weekdays_only", description="Skip Saturdays and Sundays (default true)"): bool,
            vol.Optional("include_all_day", description="Treat all-day events as busy (default false)"): bool,
            vol.Optional("limit", description="Maximum number of slots (default 10)"): int,
        }
    )

    async def run(self, hass, args):
        from .util import to_datetime  # noqa: PLC0415

        duration = int(args["duration_minutes"])
        if not 5 <= duration <= 24 * 60:
            raise ValueError("duration_minutes must be between 5 and 1440")
        start = to_datetime(self._dt(args.get("start"), dt_util.now()), self.tz)
        start = max(start, dt_util.now())
        end = self._dt(args.get("end"))
        end_dt = to_datetime(end, self.tz, end=True) if end is not None else start + timedelta(days=7)
        if end_dt <= start:
            raise ValueError("end must be after start")
        if end_dt - start > timedelta(days=62):
            raise ValueError("The search range is limited to 62 days")
        events = await self.clients.caldav.async_events(args.get("calendar_ids") or None, start, end_dt, limit=2000)
        slots = free_slots(
            events,
            start=start,
            end=end_dt,
            duration=timedelta(minutes=duration),
            tz=self.tz,
            day_start=args.get("day_start"),
            day_end=args.get("day_end"),
            weekdays_only=args.get("weekdays_only", True),
            include_all_day=bool(args.get("include_all_day")),
            limit=clamp(args.get("limit"), 10, 50),
        )
        return {"duration_minutes": duration, "count": len(slots), "slots": slots}


class UpcomingBirthdays(ICloudTool):
    name = "icloud_upcoming_birthdays"
    feature = "contacts"
    description = "List the birthdays of the user's contacts in the coming days (with the age they turn, if known)."
    parameters = vol.Schema({vol.Optional("days", description="Look ahead this many days (default 30, max 366)"): int})

    async def run(self, hass, args):
        days = clamp(args.get("days"), 30, 366)
        contacts = await self.clients.carddav.async_search(None, limit=100000)
        items = upcoming_birthdays(contacts, dt_util.now().date(), days=days)
        return {"days": days, "count": len(items), "birthdays": items}


class FindDuplicateContacts(ICloudTool):
    name = "icloud_find_duplicate_contacts"
    feature = "contacts"
    description = (
        "Find contacts that are probably duplicates (same e-mail address, phone number or name). "
        "Merging is done with icloud_update_contact and icloud_delete_contact after confirming with the user."
    )
    parameters = vol.Schema({vol.Optional("limit", description="Maximum number of groups (default 50)"): int})

    async def run(self, hass, args):
        contacts = await self.clients.carddav.async_search(None, limit=100000)
        groups = duplicate_contacts(contacts)
        limit = clamp(args.get("limit"), 50, 500)
        return {"contacts": len(contacts), "groups": len(groups), "duplicates": groups[:limit]}
