"""WebDAV multistatus parsing and discovery."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.icloud_mcp.dav import NS_CALDAV, DavAuthError, DavClient, DavNotFoundError, parse_multistatus

MULTISTATUS = """<?xml version="1.0" encoding="UTF-8"?>
<multistatus xmlns="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
 <response>
  <href>/</href>
  <propstat>
   <prop><current-user-principal><href>https://p01-caldav.icloud.com/123/principal/</href></current-user-principal></prop>
   <status>HTTP/1.1 200 OK</status>
  </propstat>
 </response>
</multistatus>"""

HOME = """<?xml version="1.0" encoding="UTF-8"?>
<multistatus xmlns="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
 <response>
  <href>/123/principal/</href>
  <propstat>
   <prop><C:calendar-home-set><href>/123/calendars/</href></C:calendar-home-set></prop>
   <status>HTTP/1.1 200 OK</status>
  </propstat>
  <propstat>
   <prop><C:calendar-user-address-set/></prop>
   <status>HTTP/1.1 404 Not Found</status>
  </propstat>
 </response>
</multistatus>"""


def test_parse_multistatus_resolves_relative_hrefs() -> None:
    responses = parse_multistatus(HOME, "https://p01-caldav.icloud.com/123/principal/")
    assert responses[0].href == "https://p01-caldav.icloud.com/123/principal/"
    assert responses[0].hrefs(NS_CALDAV, "calendar-home-set") == ["https://p01-caldav.icloud.com/123/calendars/"]
    assert responses[0].status == 200
    # 404 propstat entries are ignored
    assert "{urn:ietf:params:xml:ns:caldav}calendar-user-address-set" not in responses[0].props


async def test_discovery_and_errors(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    client = DavClient(async_get_clientsession(hass), "user", "pw")
    aioclient_mock.request("PROPFIND", "https://caldav.icloud.com/", status=207, text=MULTISTATUS)
    aioclient_mock.request("PROPFIND", "https://p01-caldav.icloud.com/123/principal/", status=207, text=HOME)
    principal = await client.current_user_principal("https://caldav.icloud.com/")
    assert principal == "https://p01-caldav.icloud.com/123/principal/"
    home = await client.home_set(principal, NS_CALDAV, "calendar-home-set")
    assert home == "https://p01-caldav.icloud.com/123/calendars/"
    method, _, data, headers = aioclient_mock.mock_calls[0]
    assert method == "PROPFIND"
    assert headers["Depth"] == "0"
    assert b"current-user-principal" in data

    aioclient_mock.clear_requests()
    aioclient_mock.request("PROPFIND", "https://caldav.icloud.com/", status=401, text="")
    with pytest.raises(DavAuthError):
        await client.current_user_principal("https://caldav.icloud.com/")

    aioclient_mock.clear_requests()
    aioclient_mock.request("GET", "https://caldav.icloud.com/x.ics", status=404, text="")
    with pytest.raises(DavNotFoundError):
        await client.get("https://caldav.icloud.com/x.ics")
