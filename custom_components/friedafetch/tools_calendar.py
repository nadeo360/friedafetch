"""Calendar tools (CalDAV)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

from .const import (
    MAX_RESULTS_LIMIT,
)
from .guard import QUOTA_ITEM_DELETE
from .schema import vol
from .tool_base import ICloudTool
from .util import clamp

_LOGGER = logging.getLogger(__name__)


class ListCalendars(ICloudTool):
    name = "icloud_list_calendars"
    feature = "calendar"
    description = "List the user's iCloud calendars with their ids. Use the id in the other calendar tools."
    parameters = vol.Schema({})

    async def run(self, hass, args):
        calendars = await self.clients.caldav.async_calendars(force=True)
        return {"calendars": [c.to_dict() for c in calendars]}


class ListEvents(ICloudTool):
    name = "icloud_list_events"
    feature = "calendar"
    description = (
        "List calendar events in a time range (recurring events are expanded). Default range: today until 7 days ahead. "
        "Dates are ISO 8601 (e.g. 2026-10-20 or 2026-10-20T14:00:00); naive times use the Home Assistant time zone."
    )
    parameters = vol.Schema(
        {
            vol.Optional("calendar_ids", description="Restrict to these calendar ids (default: all calendars)"): [str],
            vol.Optional("start", description="Range start (ISO 8601). Default: now"): str,
            vol.Optional("end", description="Range end (ISO 8601). Default: start + 7 days"): str,
            vol.Optional("query", description="Text filter on summary/description/location"): str,
            vol.Optional("limit", description="Maximum number of events"): int,
        }
    )

    async def run(self, hass, args):
        now = dt_util.now()
        start = self._dt(args.get("start"), now)
        end = self._dt(args.get("end"))
        from .util import to_datetime  # noqa: PLC0415

        start_dt = to_datetime(start, self.tz)
        end_dt = to_datetime(end, self.tz, end=True) if end is not None else start_dt + timedelta(days=7)
        if end_dt <= start_dt:
            raise ValueError("end must be after start")
        events = await self.clients.caldav.async_events(
            args.get("calendar_ids") or None,
            start_dt,
            end_dt,
            query=args.get("query"),
            limit=clamp(args.get("limit"), self.clients.max_results, MAX_RESULTS_LIMIT),
        )
        return {
            "start": start_dt.isoformat(timespec="minutes"),
            "end": end_dt.isoformat(timespec="minutes"),
            "count": len(events),
            "events": events,
        }


class GetEvent(ICloudTool):
    name = "icloud_get_event"
    feature = "calendar"
    description = "Get the full details of one calendar event by calendar id and event uid."
    parameters = vol.Schema({vol.Required("calendar_id"): str, vol.Required("uid"): str})

    async def run(self, hass, args):
        return await self.clients.caldav.async_get_event(args["calendar_id"], args["uid"])


class CreateEvent(ICloudTool):
    name = "icloud_create_event"
    feature = "calendar"
    writes = True
    description = (
        "Create a calendar event. For all-day events pass dates (YYYY-MM-DD) for start and end (end inclusive). "
        "For timed events pass ISO 8601 date-times; end defaults to start + 1 hour. Optional RRULE for recurrence, e.g. FREQ=WEEKLY;BYDAY=MO."
    )
    parameters = vol.Schema(
        {
            vol.Required("calendar_id", description="Target calendar id (see icloud_list_calendars)"): str,
            vol.Required("summary", description="Event title"): str,
            vol.Required("start", description="Start (ISO 8601 date or date-time)"): str,
            vol.Optional("end", description="End (ISO 8601). All-day: last day inclusive"): str,
            vol.Optional("description"): str,
            vol.Optional("location"): str,
            vol.Optional("rrule", description="iCalendar recurrence rule without the RRULE: prefix"): str,
            vol.Optional("url"): str,
        }
    )

    async def run(self, hass, args):
        await self._check_calendar(args["calendar_id"])
        start = self._dt(args["start"])
        end = self._dt(args.get("end"))
        if end is not None and isinstance(start, datetime) != isinstance(end, datetime):
            raise ValueError("start and end must both be dates (all-day) or both be date-times")
        return await self.clients.caldav.async_create_event(
            args["calendar_id"],
            args["summary"],
            start,
            end,
            description=args.get("description"),
            location=args.get("location"),
            rrule=args.get("rrule"),
            url=args.get("url"),
        )


class UpdateEvent(ICloudTool):
    name = "icloud_update_event"
    feature = "calendar"
    writes = True
    description = (
        "Update fields of an existing calendar event (only the provided fields change; pass an empty string to clear "
        "description/location/url/rrule). Changing only start keeps the original duration."
    )
    parameters = vol.Schema(
        {
            vol.Required("calendar_id"): str,
            vol.Required("uid"): str,
            vol.Optional("summary"): str,
            vol.Optional("start"): str,
            vol.Optional("end"): str,
            vol.Optional("description"): str,
            vol.Optional("location"): str,
            vol.Optional("rrule"): str,
            vol.Optional("url"): str,
        }
    )

    async def run(self, hass, args):
        await self._check_calendar(args["calendar_id"])
        start = self._dt(args.get("start"))
        end = self._dt(args.get("end"))
        if start is not None and end is not None and isinstance(start, datetime) != isinstance(end, datetime):
            raise ValueError("start and end must both be dates (all-day) or both be date-times")
        return await self.clients.caldav.async_update_event(
            args["calendar_id"],
            args["uid"],
            summary=args.get("summary"),
            start=start,
            end=end,
            description=args.get("description"),
            location=args.get("location"),
            rrule=args.get("rrule"),
            url=args.get("url"),
        )


class DeleteEvent(ICloudTool):
    name = "icloud_delete_event"
    feature = "calendar"
    writes = True
    deletes = True
    description = "Delete a calendar event (all occurrences if recurring). Confirm with the user before deleting."
    parameters = vol.Schema({vol.Required("calendar_id"): str, vol.Required("uid"): str})

    async def run(self, hass, args):
        await self._check_calendar(args["calendar_id"])
        self.clients.guard.check_quota(QUOTA_ITEM_DELETE)
        await self.clients.caldav.async_delete_event(args["calendar_id"], args["uid"])
        self.clients.guard.consume(QUOTA_ITEM_DELETE)
        return {"deleted": True, "uid": args["uid"], "calendar_id": args["calendar_id"]}


# ============================================================== contacts
