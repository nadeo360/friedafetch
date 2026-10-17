"""iCloud CalDAV client (events)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, tzinfo
from typing import Any
from urllib.parse import quote, urlsplit
from xml.sax.saxutils import escape as xml_escape

from dateutil import rrule as du_rrule
from icalendar import Calendar, Event, vRecur, vText

from .dav import (
    NS_APPLE,
    NS_CALDAV,
    NS_CS,
    NS_DAV,
    DavClient,
    DavError,
    DavNotFoundError,
    DavResponse,
    tag,
)
from .util import isoformat, to_datetime

_LOGGER = logging.getLogger(__name__)

_CALENDAR_CACHE_TTL = 300
PRODID = "-//Home Assistant//iCloud MCP//EN"


class CalendarError(Exception):
    """Calendar operation failed."""


class CalendarNotFound(CalendarError):
    """Calendar or event not found."""


@dataclass
class CalendarInfo:
    """A CalDAV calendar collection."""

    id: str
    href: str
    name: str
    color: str | None = None
    description: str | None = None
    order: int | None = None
    supports_events: bool = True
    ctag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "description": self.description,
        }


@dataclass
class EventRecord:
    """A VEVENT resource with its location on the server."""

    href: str
    etag: str | None
    calendar: Calendar


def _calendar_id_from_href(href: str) -> str:
    path = urlsplit(href).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def _as_utc_or_date(value: datetime | date) -> datetime | date:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value
    return value


def _ical_dt(value: datetime | date) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return value.strftime("%Y%m%dT000000Z")


class ICloudCalDav:
    """Async CalDAV access to the user's iCloud calendars."""

    def __init__(self, dav: DavClient, base_url: str, tz: tzinfo) -> None:
        self._dav = dav
        self._base_url = base_url
        self._tz = tz
        self._principal: str | None = None
        self._home: str | None = None
        self._calendars: list[CalendarInfo] = []
        self._calendars_fetched = 0.0

    # ----------------------------------------------------------- discovery
    async def async_discover(self) -> str:
        """Discover the principal and calendar home. Returns the home URL."""
        if self._home:
            return self._home
        self._principal = await self._dav.current_user_principal(self._base_url)
        self._home = await self._dav.home_set(self._principal, NS_CALDAV, "calendar-home-set")
        _LOGGER.debug("CalDAV home: %s", self._home)
        return self._home

    async def async_calendars(self, force: bool = False) -> list[CalendarInfo]:
        """Return the list of calendars supporting events (cached)."""
        now = time.monotonic()
        if not force and self._calendars and now - self._calendars_fetched < _CALENDAR_CACHE_TTL:
            return self._calendars
        home = await self.async_discover()
        responses = await self._dav.propfind(
            home,
            [
                (NS_DAV, "displayname"),
                (NS_DAV, "resourcetype"),
                (NS_CALDAV, "supported-calendar-component-set"),
                (NS_CALDAV, "calendar-description"),
                (NS_APPLE, "calendar-color"),
                (NS_APPLE, "calendar-order"),
                (NS_CS, "getctag"),
            ],
            depth="1",
        )
        calendars: list[CalendarInfo] = []
        for resp in responses:
            if not resp.has_resourcetype(NS_CALDAV, "calendar"):
                continue
            comp_el = resp.props.get(tag(NS_CALDAV, "supported-calendar-component-set"))
            components = (
                [c.get("name", "") for c in comp_el.iter(tag(NS_CALDAV, "comp"))] if comp_el is not None else ["VEVENT"]
            )
            if components and "VEVENT" not in components:
                continue
            name = resp.text(NS_DAV, "displayname") or _calendar_id_from_href(resp.href)
            order_txt = resp.text(NS_APPLE, "calendar-order")
            color = resp.text(NS_APPLE, "calendar-color")
            calendars.append(
                CalendarInfo(
                    id=_calendar_id_from_href(resp.href),
                    href=resp.href if resp.href.endswith("/") else resp.href + "/",
                    name=name,
                    color=color[:7] if color else None,
                    description=resp.text(NS_CALDAV, "calendar-description"),
                    order=int(order_txt) if order_txt and order_txt.isdigit() else None,
                    ctag=resp.text(NS_CS, "getctag"),
                )
            )
        calendars.sort(key=lambda c: (c.order if c.order is not None else 999, c.name.lower()))
        self._calendars = calendars
        self._calendars_fetched = now
        return calendars

    async def async_get_calendar(self, calendar_id: str) -> CalendarInfo:
        calendars = await self.async_calendars()
        wanted = calendar_id.strip().lower()
        for cal in calendars:
            if cal.id.lower() == wanted:
                return cal
        for cal in calendars:
            if cal.name.lower() == wanted:
                return cal
        # maybe the cache is stale
        for cal in await self.async_calendars(force=True):
            if cal.id.lower() == wanted or cal.name.lower() == wanted:
                return cal
        raise CalendarNotFound(f"Calendar '{calendar_id}' not found")

    # --------------------------------------------------------------- query
    async def async_events(
        self,
        calendar_ids: list[str] | None,
        start: datetime,
        end: datetime,
        query: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return expanded event instances between start and end."""
        if calendar_ids:
            calendars = [await self.async_get_calendar(cid) for cid in calendar_ids]
        else:
            calendars = await self.async_calendars()
        results: list[dict[str, Any]] = []
        for cal in calendars:
            try:
                records = await self._query_range(cal, start, end)
            except DavError as err:
                _LOGGER.warning("Calendar %s query failed: %s", cal.name, err)
                continue
            for record in records:
                results.extend(self._expand(record, cal, start, end))
        if query:
            q = query.lower()
            results = [
                ev
                for ev in results
                if q in " ".join(str(ev.get(k) or "") for k in ("summary", "description", "location")).lower()
            ]
        results.sort(key=lambda ev: ev["_sort"])
        for ev in results:
            ev.pop("_sort", None)
        return results[:limit]

    async def _query_range(self, cal: CalendarInfo, start: datetime, end: datetime) -> list[EventRecord]:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
            "<D:prop><D:getetag/><C:calendar-data/></D:prop>"
            '<C:filter><C:comp-filter name="VCALENDAR"><C:comp-filter name="VEVENT">'
            f'<C:time-range start="{_ical_dt(start)}" end="{_ical_dt(end)}"/>'
            "</C:comp-filter></C:comp-filter></C:filter></C:calendar-query>"
        )
        responses = await self._dav.report(cal.href, body, depth="1")
        return self._records(responses)

    def _records(self, responses: list[DavResponse]) -> list[EventRecord]:
        records: list[EventRecord] = []
        for resp in responses:
            data = resp.text(NS_CALDAV, "calendar-data")
            if not data:
                continue
            try:
                calendar = Calendar.from_ical(data)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Cannot parse calendar data at %s: %s", resp.href, err)
                continue
            records.append(EventRecord(href=resp.href, etag=resp.etag, calendar=calendar))
        return records

    async def async_find_event(self, cal: CalendarInfo, uid: str) -> EventRecord:
        """Locate an event by UID (direct href first, then a UID query)."""
        direct = f"{cal.href}{quote(uid, safe='')}.ics"
        try:
            text, etag = await self._dav.get(direct)
            return EventRecord(href=direct, etag=etag, calendar=Calendar.from_ical(text))
        except DavNotFoundError:
            pass
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Direct GET %s failed: %s", direct, err)
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
            "<D:prop><D:getetag/><C:calendar-data/></D:prop>"
            '<C:filter><C:comp-filter name="VCALENDAR"><C:comp-filter name="VEVENT">'
            f'<C:prop-filter name="UID"><C:text-match collation="i;octet">{xml_escape(uid)}</C:text-match></C:prop-filter>'
            "</C:comp-filter></C:comp-filter></C:filter></C:calendar-query>"
        )
        records = self._records(await self._dav.report(cal.href, body, depth="1"))
        for record in records:
            for comp in record.calendar.walk("VEVENT"):
                if str(comp.get("UID", "")) == uid:
                    return record
        raise CalendarNotFound(f"Event '{uid}' not found in calendar '{cal.name}'")

    async def async_get_event(self, calendar_id: str, uid: str) -> dict[str, Any]:
        cal = await self.async_get_calendar(calendar_id)
        record = await self.async_find_event(cal, uid)
        master = self._master(record.calendar)
        if master is None:
            raise CalendarNotFound(f"Event '{uid}' has no VEVENT")
        result = self._event_dict(master, cal)
        result.pop("_sort", None)
        result["etag"] = record.etag
        overrides = [
            self._event_dict(c, cal) for c in record.calendar.walk("VEVENT") if c.get("RECURRENCE-ID") is not None
        ]
        if overrides:
            result["modified_occurrences"] = overrides
        return result

    # --------------------------------------------------------------- write
    async def async_create_event(
        self,
        calendar_id: str,
        summary: str,
        start: datetime | date,
        end: datetime | date | None,
        *,
        description: str | None = None,
        location: str | None = None,
        rrule: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        cal = await self.async_get_calendar(calendar_id)
        uid = str(uuid.uuid4()).upper()
        event = Event()
        event.add("uid", uid)
        now = datetime.now(UTC)
        event.add("dtstamp", now)
        event.add("created", now)
        event.add("last-modified", now)
        event.add("sequence", 0)
        self._apply_times(event, start, end)
        event.add("summary", summary)
        if description:
            event.add("description", description)
        if location:
            event.add("location", location)
        if url:
            event.add("url", url)
        if rrule:
            event.add("rrule", self._parse_rrule(rrule))
        calendar = Calendar()
        calendar.add("prodid", PRODID)
        calendar.add("version", "2.0")
        calendar.add_component(event)
        href = f"{cal.href}{uid}.ics"
        etag = await self._dav.put(
            href, calendar.to_ical().decode("utf-8"), "text/calendar; charset=utf-8", create=True
        )
        result = self._event_dict(event, cal)
        result.pop("_sort", None)
        result["etag"] = etag
        return result

    async def async_update_event(
        self,
        calendar_id: str,
        uid: str,
        *,
        summary: str | None = None,
        start: datetime | date | None = None,
        end: datetime | date | None = None,
        description: str | None = None,
        location: str | None = None,
        rrule: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        cal = await self.async_get_calendar(calendar_id)
        record = await self.async_find_event(cal, uid)
        master = self._master(record.calendar)
        if master is None:
            raise CalendarNotFound(f"Event '{uid}' has no VEVENT")
        if summary is not None:
            master["SUMMARY"] = vText(summary)
        for key, value in (("DESCRIPTION", description), ("LOCATION", location), ("URL", url)):
            if value is None:
                continue
            master.pop(key, None)
            if value != "":
                master.add(key.lower(), value)
        if start is not None or end is not None:
            old_start = master.decoded("DTSTART") if master.get("DTSTART") else None
            old_end = (
                master.decoded("DTEND")
                if master.get("DTEND")
                else (old_start + master.decoded("DURATION") if master.get("DURATION") and old_start else None)
            )
            new_start = start if start is not None else old_start
            new_end = end if end is not None else old_end
            if (
                new_end is not None
                and start is not None
                and end is None
                and old_start is not None
                and old_end is not None
            ):
                # keep the original duration when only the start moves
                if isinstance(new_start, datetime) and isinstance(old_start, datetime):
                    new_end = new_start + (old_end - old_start)
                elif not isinstance(new_start, datetime) and not isinstance(old_start, datetime):
                    new_end = new_start + (old_end - old_start) - timedelta(days=1)
            if (
                new_end is not None
                and not isinstance(new_start, datetime)
                and isinstance(old_end, date)
                and not isinstance(old_end, datetime)
                and end is None
                and start is None
            ):
                new_end = old_end - timedelta(days=1)
            master.pop("DTSTART", None)
            master.pop("DTEND", None)
            master.pop("DURATION", None)
            self._apply_times(master, new_start, new_end, end_is_exclusive=(end is None and start is None))
        if rrule is not None:
            master.pop("RRULE", None)
            if rrule != "":
                master.add("rrule", self._parse_rrule(rrule))
        seq = master.get("SEQUENCE")
        master.pop("SEQUENCE", None)
        master.add("sequence", (int(seq) if seq is not None else 0) + 1)
        now = datetime.now(UTC)
        master.pop("DTSTAMP", None)
        master.add("dtstamp", now)
        master.pop("LAST-MODIFIED", None)
        master.add("last-modified", now)
        etag = await self._dav.put(
            record.href,
            record.calendar.to_ical().decode("utf-8"),
            "text/calendar; charset=utf-8",
            etag=record.etag,
        )
        result = self._event_dict(master, cal)
        result.pop("_sort", None)
        result["etag"] = etag
        return result

    async def async_delete_event(self, calendar_id: str, uid: str) -> None:
        cal = await self.async_get_calendar(calendar_id)
        record = await self.async_find_event(cal, uid)
        await self._dav.delete(record.href, etag=record.etag)

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _parse_rrule(rrule: str) -> vRecur:
        text = rrule.strip()
        if text.upper().startswith("RRULE:"):
            text = text[6:]
        try:
            du_rrule.rrulestr(text, dtstart=datetime(2000, 1, 1))
        except (ValueError, TypeError) as err:
            raise CalendarError(f"Invalid RRULE {rrule!r}: {err}") from err
        return vRecur.from_ical(text)

    def _apply_times(
        self,
        event: Event,
        start: datetime | date,
        end: datetime | date | None,
        end_is_exclusive: bool = False,
    ) -> None:
        all_day = not isinstance(start, datetime)
        if all_day:
            start_d = start if isinstance(start, date) else start.date()
            if end is None:
                end_d = start_d + timedelta(days=1)
            else:
                end_d = end if not isinstance(end, datetime) else end.date()
                if not end_is_exclusive:
                    end_d = end_d + timedelta(days=1)
            if end_d <= start_d:
                end_d = start_d + timedelta(days=1)
            event.add("dtstart", start_d)
            event.add("dtend", end_d)
            return
        start_dt = to_datetime(start, self._tz)
        if end is None:
            end_dt = start_dt + timedelta(hours=1)
        else:
            end_dt = to_datetime(end, self._tz)
        if end_dt <= start_dt:
            raise CalendarError("End must be after start")
        event.add("dtstart", start_dt.astimezone(UTC))
        event.add("dtend", end_dt.astimezone(UTC))

    @staticmethod
    def _master(calendar: Calendar) -> Event | None:
        events = list(calendar.walk("VEVENT"))
        for ev in events:
            if ev.get("RECURRENCE-ID") is None:
                return ev
        return events[0] if events else None

    def _event_dict(
        self,
        ev: Event,
        cal: CalendarInfo,
        instance_start: datetime | date | None = None,
        instance_end: datetime | date | None = None,
    ) -> dict[str, Any]:
        start = instance_start if instance_start is not None else (ev.decoded("DTSTART") if ev.get("DTSTART") else None)
        if instance_end is not None:
            end = instance_end
        elif ev.get("DTEND"):
            end = ev.decoded("DTEND")
        elif ev.get("DURATION") and start is not None:
            end = start + ev.decoded("DURATION")
        else:
            end = None
        all_day = start is not None and not isinstance(start, datetime)
        if all_day and isinstance(end, date) and not isinstance(end, datetime):
            end_out: date | datetime | None = end - timedelta(days=1)
        else:
            end_out = end
        rec_id = ev.get("RECURRENCE-ID")
        result: dict[str, Any] = {
            "uid": str(ev.get("UID", "")),
            "calendar_id": cal.id,
            "calendar_name": cal.name,
            "summary": str(ev.get("SUMMARY", "")) or None,
            "description": str(ev["DESCRIPTION"]) if ev.get("DESCRIPTION") else None,
            "location": str(ev["LOCATION"]) if ev.get("LOCATION") else None,
            "start": isoformat(start, self._tz),
            "end": isoformat(end_out, self._tz),
            "all_day": all_day,
            "recurring": ev.get("RRULE") is not None or rec_id is not None,
            "rrule": ev["RRULE"].to_ical().decode() if ev.get("RRULE") else None,
            "recurrence_id": isoformat(ev.decoded("RECURRENCE-ID"), self._tz) if rec_id is not None else None,
            "status": str(ev["STATUS"]) if ev.get("STATUS") else None,
            "url": str(ev["URL"]) if ev.get("URL") else None,
        }
        sort_key = to_datetime(start, self._tz) if start is not None else datetime.max.replace(tzinfo=self._tz)
        result["_sort"] = sort_key
        return result

    def _expand(self, record: EventRecord, cal: CalendarInfo, start: datetime, end: datetime) -> list[dict[str, Any]]:
        """Expand a VEVENT resource into instances overlapping [start, end)."""
        events = list(record.calendar.walk("VEVENT"))
        if not events:
            return []
        master = self._master(record.calendar)
        overrides: dict[Any, Event] = {}
        for ev in events:
            if ev.get("RECURRENCE-ID") is not None:
                rid = ev.decoded("RECURRENCE-ID")
                overrides[self._key(rid)] = ev
        out: list[dict[str, Any]] = []
        if master is None:
            return out
        m_start = master.decoded("DTSTART") if master.get("DTSTART") else None
        if m_start is None:
            return out
        if master.get("DTEND"):
            duration = master.decoded("DTEND") - m_start
        elif master.get("DURATION"):
            duration = master.decoded("DURATION")
        else:
            duration = timedelta(days=1) if not isinstance(m_start, datetime) else timedelta(0)

        def overlaps(s: datetime | date, e: datetime | date) -> bool:
            s_dt = to_datetime(s, self._tz)
            e_dt = to_datetime(e, self._tz) if isinstance(e, datetime) else to_datetime(e, self._tz)
            if e_dt <= s_dt:
                e_dt = s_dt + timedelta(minutes=1)
            return s_dt < end and e_dt > start

        if master.get("RRULE") is None and not master.get("RDATE"):
            m_end = m_start + duration
            if overlaps(m_start, m_end):
                out.append(self._event_dict(master, cal))
            for ov in overrides.values():
                o_start = ov.decoded("DTSTART")
                o_end = ov.decoded("DTEND") if ov.get("DTEND") else o_start + duration
                if overlaps(o_start, o_end):
                    out.append(self._event_dict(ov, cal))
            return out

        # recurring: expand with dateutil
        all_day = not isinstance(m_start, datetime)
        dtstart = to_datetime(m_start, self._tz)
        rule_text = master["RRULE"].to_ical().decode()
        try:
            ruleset = du_rrule.rruleset()
            ruleset.rrule(du_rrule.rrulestr(rule_text, dtstart=dtstart))
        except (ValueError, TypeError) as err:
            _LOGGER.debug("Cannot expand RRULE %s: %s", rule_text, err)
            out.append(self._event_dict(master, cal))
            return out
        for prop in (
            master.get("EXDATE", [])
            if isinstance(master.get("EXDATE"), list)
            else ([master.get("EXDATE")] if master.get("EXDATE") else [])
        ):
            for dt in prop.dts:
                ruleset.exdate(to_datetime(dt.dt, self._tz))
        for prop in (
            master.get("RDATE", [])
            if isinstance(master.get("RDATE"), list)
            else ([master.get("RDATE")] if master.get("RDATE") else [])
        ):
            for dt in prop.dts:
                ruleset.rdate(to_datetime(dt.dt, self._tz))
        window_start = start - duration if duration > timedelta(0) else start - timedelta(days=1)
        count = 0
        for occ in ruleset.between(window_start, end, inc=True):
            count += 1
            if count > 1000:
                break
            key = self._key(occ.date() if all_day else occ)
            if key in overrides:
                ov = overrides.pop(key)
                o_start = ov.decoded("DTSTART")
                o_end = ov.decoded("DTEND") if ov.get("DTEND") else o_start + duration
                if overlaps(o_start, o_end):
                    out.append(self._event_dict(ov, cal))
                continue
            inst_start: datetime | date = occ.date() if all_day else occ.astimezone(self._tz)
            inst_end = inst_start + duration
            if overlaps(inst_start, inst_end):
                out.append(self._event_dict(master, cal, inst_start, inst_end))
        # overrides moved into the window from outside
        for ov in overrides.values():
            o_start = ov.decoded("DTSTART")
            o_end = ov.decoded("DTEND") if ov.get("DTEND") else o_start + duration
            if overlaps(o_start, o_end):
                out.append(self._event_dict(ov, cal))
        return out

    def _key(self, value: datetime | date) -> Any:
        if isinstance(value, datetime):
            return to_datetime(value, self._tz).astimezone(UTC).replace(microsecond=0)
        return value
