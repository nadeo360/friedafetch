"""CalDAV client against a mocked iCloud server."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.friedafetch.caldav_client import CalendarError, ICloudCalDav
from custom_components.friedafetch.dav import DavClient

TZ = ZoneInfo("Europe/Berlin")
HOME = "https://p01-caldav.icloud.com/123/calendars/"
CAL = f"{HOME}ABC-123/"

CALENDARS = """<?xml version="1.0" encoding="UTF-8"?>
<multistatus xmlns="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav" xmlns:A="http://apple.com/ns/ical/" xmlns:CS="http://calendarserver.org/ns/">
 <response><href>/123/calendars/</href><propstat><prop><resourcetype><collection/></resourcetype></prop><status>HTTP/1.1 200 OK</status></propstat></response>
 <response><href>/123/calendars/inbox/</href><propstat><prop><resourcetype><collection/><C:schedule-inbox/></resourcetype></prop><status>HTTP/1.1 200 OK</status></propstat></response>
 <response><href>/123/calendars/ABC-123/</href><propstat><prop>
   <displayname>Familie</displayname>
   <resourcetype><collection/><C:calendar/></resourcetype>
   <C:supported-calendar-component-set><C:comp name="VEVENT"/></C:supported-calendar-component-set>
   <A:calendar-color>#FF2968FF</A:calendar-color><A:calendar-order>1</A:calendar-order>
   <CS:getctag>ctag1</CS:getctag>
 </prop><status>HTTP/1.1 200 OK</status></propstat></response>
 <response><href>/123/calendars/TASKS/</href><propstat><prop>
   <displayname>Erinnerungen</displayname>
   <resourcetype><collection/><C:calendar/></resourcetype>
   <C:supported-calendar-component-set><C:comp name="VTODO"/></C:supported-calendar-component-set>
 </prop><status>HTTP/1.1 200 OK</status></propstat></response>
</multistatus>"""

ICS_SINGLE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Apple Inc.//iCloud//EN
BEGIN:VEVENT
UID:EVENT-1
DTSTART;TZID=Europe/Berlin:20261020T140000
DTEND;TZID=Europe/Berlin:20261020T150000
SUMMARY:Zahnarzt
LOCATION:Praxis
END:VEVENT
END:VCALENDAR
"""

ICS_RECURRING = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Apple Inc.//iCloud//EN
BEGIN:VEVENT
UID:EVENT-2
DTSTART;TZID=Europe/Berlin:20261019T080000
DTEND;TZID=Europe/Berlin:20261019T083000
RRULE:FREQ=DAILY;COUNT=10
EXDATE;TZID=Europe/Berlin:20261021T080000
SUMMARY:Standup
END:VEVENT
BEGIN:VEVENT
UID:EVENT-2
RECURRENCE-ID;TZID=Europe/Berlin:20261022T080000
DTSTART;TZID=Europe/Berlin:20261022T090000
DTEND;TZID=Europe/Berlin:20261022T093000
SUMMARY:Standup (verschoben)
END:VEVENT
END:VCALENDAR
"""

ICS_ALLDAY = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Apple Inc.//iCloud//EN
BEGIN:VEVENT
UID:EVENT-3
DTSTART;VALUE=DATE:20261024
DTEND;VALUE=DATE:20261026
SUMMARY:Wochenendtrip
END:VEVENT
END:VCALENDAR
"""


def _report(*ics: str) -> str:
    items = "".join(
        f'<response><href>/123/calendars/ABC-123/{i}.ics</href><propstat><prop><getetag>"e{i}"</getetag>'
        f"<C:calendar-data><![CDATA[{data}]]></C:calendar-data></prop><status>HTTP/1.1 200 OK</status></propstat></response>"
        for i, data in enumerate(ics)
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><multistatus xmlns="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">{items}</multistatus>'


@pytest.fixture
def client(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> ICloudCalDav:
    dav = DavClient(async_get_clientsession(hass), "user", "pw")
    cal = ICloudCalDav(dav, "https://caldav.icloud.com/", TZ)
    cal._home = HOME  # skip discovery
    aioclient_mock.request("PROPFIND", HOME, status=207, text=CALENDARS)
    return cal


def _calls(aioclient_mock: AiohttpClientMocker, method: str) -> list:
    return [c for c in aioclient_mock.mock_calls if c[0] == method]


async def test_calendars_filters_non_event_collections(client: ICloudCalDav) -> None:
    calendars = await client.async_calendars()
    assert [c.id for c in calendars] == ["ABC-123"]
    assert calendars[0].name == "Familie"
    assert calendars[0].color == "#FF2968"
    assert calendars[0].to_dict()["id"] == "ABC-123"


async def test_events_expand_recurrence_with_exdate_and_override(
    client: ICloudCalDav, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.request("REPORT", CAL, status=207, text=_report(ICS_SINGLE, ICS_RECURRING, ICS_ALLDAY))
    events = await client.async_events(
        None, datetime(2026, 10, 19, 0, 0, tzinfo=TZ), datetime(2026, 10, 26, 0, 0, tzinfo=TZ)
    )
    report = _calls(aioclient_mock, "REPORT")[0]
    assert b'time-range start="20261018T220000Z"' in report[2]
    summaries = [(e["start"], e["summary"]) for e in events]
    standups = [s for s in summaries if s[1].startswith("Standup")]
    assert len(standups) == 6  # 19..25 minus the 21st (EXDATE)
    assert ("2026-10-21T08:00+02:00", "Standup") not in standups
    assert ("2026-10-22T08:00+02:00", "Standup") not in standups
    assert ("2026-10-22T09:00+02:00", "Standup (verschoben)") in standups
    single = next(e for e in events if e["uid"] == "EVENT-1")
    assert single["start"] == "2026-10-20T14:00+02:00"
    assert single["end"] == "2026-10-20T15:00+02:00"
    assert single["location"] == "Praxis"
    assert single["recurring"] is False
    allday = next(e for e in events if e["uid"] == "EVENT-3")
    assert allday["all_day"] is True
    assert allday["start"] == "2026-10-24"
    assert allday["end"] == "2026-10-25"  # inclusive end for the LLM
    starts = [e["start"] for e in events]
    assert starts == sorted(
        starts, key=lambda s: datetime.fromisoformat(s) if "T" in s else datetime.fromisoformat(s + "T00:00+02:00")
    )


async def test_events_query_filter(client: ICloudCalDav, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.request("REPORT", CAL, status=207, text=_report(ICS_SINGLE, ICS_RECURRING))
    events = await client.async_events(
        ["Familie"], datetime(2026, 10, 19, tzinfo=TZ), datetime(2026, 10, 26, tzinfo=TZ), query="zahn"
    )
    assert [e["summary"] for e in events] == ["Zahnarzt"]


async def test_create_event_puts_ics(client: ICloudCalDav, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.request(
        "PUT",
        re.compile(r"https://p01-caldav\.icloud\.com/123/calendars/ABC-123/.+\.ics"),
        status=201,
        headers={"ETag": '"new"'},
    )
    result = await client.async_create_event(
        "ABC-123",
        "Test",
        datetime(2026, 11, 1, 10, 0, tzinfo=TZ),
        None,
        description="Beschreibung",
        rrule="FREQ=WEEKLY;BYDAY=MO",
    )
    put = _calls(aioclient_mock, "PUT")
    assert len(put) == 1
    body = put[0][2].decode()
    assert put[0][3]["If-None-Match"] == "*"
    assert "SUMMARY:Test" in body
    assert "DTSTART:20261101T090000Z" in body  # 10:00 Berlin (CET) == 09:00Z
    assert "DTEND:20261101T100000Z" in body
    assert "RRULE:FREQ=WEEKLY;BYDAY=MO" in body
    assert "DESCRIPTION:Beschreibung" in body
    assert result["summary"] == "Test"
    assert result["start"] == "2026-11-01T10:00+01:00"
    assert result["end"] == "2026-11-01T11:00+01:00"
    assert result["etag"] == '"new"'


async def test_create_allday_event(client: ICloudCalDav, aioclient_mock: AiohttpClientMocker) -> None:
    from datetime import date

    aioclient_mock.request("PUT", re.compile(r".*\.ics"), status=201)
    result = await client.async_create_event("ABC-123", "Urlaub", date(2026, 12, 24), date(2026, 12, 26))
    body = _calls(aioclient_mock, "PUT")[0][2].decode()
    assert "DTSTART;VALUE=DATE:20261224" in body
    assert "DTEND;VALUE=DATE:20261227" in body  # exclusive on the wire
    assert result["all_day"] is True
    assert result["end"] == "2026-12-26"  # inclusive for the LLM


async def test_create_event_invalid_rrule(client: ICloudCalDav) -> None:
    with pytest.raises(CalendarError):
        await client.async_create_event(
            "ABC-123", "x", datetime(2026, 11, 1, 10, tzinfo=TZ), None, rrule="FREQ=SOMETIMES"
        )


async def test_update_and_delete_event(client: ICloudCalDav, aioclient_mock: AiohttpClientMocker) -> None:
    href = f"{CAL}EVENT-1.ics"
    aioclient_mock.request("GET", href, status=200, text=ICS_SINGLE, headers={"ETag": '"e1"'})
    aioclient_mock.request("PUT", href, status=204, headers={"ETag": '"e2"'})
    result = await client.async_update_event(
        "ABC-123", "EVENT-1", summary="Zahnarzt (neu)", start=datetime(2026, 10, 21, 16, 0, tzinfo=TZ)
    )
    put = _calls(aioclient_mock, "PUT")[0]
    body = put[2].decode()
    assert put[3]["If-Match"] == '"e1"'
    assert "SUMMARY:Zahnarzt (neu)" in body
    assert "SEQUENCE:1" in body
    assert result["start"] == "2026-10-21T16:00+02:00"
    assert result["end"] == "2026-10-21T17:00+02:00"  # duration kept
    assert result["etag"] == '"e2"'

    aioclient_mock.request("DELETE", href, status=204)
    await client.async_delete_event("ABC-123", "EVENT-1")
    delete = _calls(aioclient_mock, "DELETE")[0]
    assert delete[3]["If-Match"] == '"e1"'
