"""Small async WebDAV helper used for iCloud CalDAV and CardDAV."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import aiohttp

_LOGGER = logging.getLogger(__name__)

NS_DAV = "DAV:"
NS_CALDAV = "urn:ietf:params:xml:ns:caldav"
NS_CARDDAV = "urn:ietf:params:xml:ns:carddav"
NS_CS = "http://calendarserver.org/ns/"
NS_APPLE = "http://apple.com/ns/ical/"


def tag(ns: str, name: str) -> str:
    """Return a Clark-notation tag."""
    return f"{{{ns}}}{name}"


class DavError(Exception):
    """Generic WebDAV error."""


class DavAuthError(DavError):
    """Authentication failed (401/403)."""


class DavNotFoundError(DavError):
    """Resource not found (404)."""


class DavConflictError(DavError):
    """Precondition failed, e.g. ETag mismatch (412)."""


@dataclass
class DavResponse:
    """One <D:response> of a multistatus body."""

    href: str
    status: int | None = None
    props: dict[str, ET.Element] = field(default_factory=dict)

    def text(self, ns: str, name: str) -> str | None:
        el = self.props.get(tag(ns, name))
        if el is None:
            return None
        return (el.text or "").strip() or None

    def hrefs(self, ns: str, name: str) -> list[str]:
        el = self.props.get(tag(ns, name))
        if el is None:
            return []
        return [
            urljoin(self.href, (h.text or "").strip()) for h in el.iter(tag(NS_DAV, "href")) if (h.text or "").strip()
        ]

    def has_resourcetype(self, ns: str, name: str) -> bool:
        el = self.props.get(tag(NS_DAV, "resourcetype"))
        if el is None:
            return False
        return el.find(tag(ns, name)) is not None

    @property
    def etag(self) -> str | None:
        return self.text(NS_DAV, "getetag")

    @property
    def path(self) -> str:
        return urlsplit(self.href).path


def _status_code(text: str | None) -> int | None:
    if not text:
        return None
    parts = text.split()
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return None


def parse_multistatus(xml_text: str, request_url: str) -> list[DavResponse]:
    """Parse a 207 multistatus body."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        raise DavError(f"Invalid multistatus XML: {err}") from err
    responses: list[DavResponse] = []
    for resp in root.iter(tag(NS_DAV, "response")):
        href_el = resp.find(tag(NS_DAV, "href"))
        if href_el is None or not (href_el.text or "").strip():
            continue
        href = urljoin(request_url, href_el.text.strip())
        item = DavResponse(href=href)
        status_el = resp.find(tag(NS_DAV, "status"))
        if status_el is not None:
            item.status = _status_code(status_el.text)
        for propstat in resp.findall(tag(NS_DAV, "propstat")):
            ps_status = _status_code(propstat.findtext(tag(NS_DAV, "status")) or "")
            if ps_status is not None and ps_status >= 300:
                continue
            prop = propstat.find(tag(NS_DAV, "prop"))
            if prop is None:
                continue
            for child in prop:
                item.props[child.tag] = child
            if item.status is None:
                item.status = ps_status
        responses.append(item)
    return responses


class DavClient:
    """Thin WebDAV client with Basic auth."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        timeout: int = 30,
    ) -> None:
        self._session = session
        self._auth = aiohttp.BasicAuth(username, password)
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def request(
        self,
        method: str,
        url: str,
        *,
        data: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        depth: str | None = None,
    ) -> tuple[int, dict[str, str], str]:
        hdrs: dict[str, str] = {"User-Agent": "HomeAssistant-iCloudMCP/0.1"}
        if depth is not None:
            hdrs["Depth"] = depth
        if headers:
            hdrs.update(headers)
        if isinstance(data, str):
            data = data.encode("utf-8")
        try:
            async with self._session.request(
                method,
                url,
                data=data,
                headers=hdrs,
                auth=self._auth,
                timeout=self._timeout,
                allow_redirects=True,
            ) as resp:
                text = (await resp.read()).decode("utf-8", errors="replace")
                status = resp.status
                resp_headers = {k: v for k, v in resp.headers.items()}
        except aiohttp.ClientError as err:
            raise DavError(f"{method} {url} failed: {err}") from err
        except TimeoutError as err:
            raise DavError(f"{method} {url} timed out") from err

        if status in (401, 403):
            raise DavAuthError(f"{method} {url}: HTTP {status}")
        if status == 404:
            raise DavNotFoundError(f"{method} {url}: not found")
        if status == 412:
            raise DavConflictError(f"{method} {url}: precondition failed")
        if status >= 400:
            snippet = text[:300].replace("\n", " ")
            raise DavError(f"{method} {url}: HTTP {status} {snippet}")
        return status, resp_headers, text

    async def propfind(self, url: str, props: list[tuple[str, str]], depth: str = "0") -> list[DavResponse]:
        namespaces: dict[str, str] = {NS_DAV: "D"}
        for ns, _ in props:
            if ns not in namespaces:
                namespaces[ns] = f"N{len(namespaces)}"
        ns_decl = " ".join(f'xmlns:{p}="{ns}"' for ns, p in namespaces.items())
        prop_xml = "".join(f"<{namespaces[ns]}:{name}/>" for ns, name in props)
        body = f'<?xml version="1.0" encoding="utf-8"?><D:propfind {ns_decl}><D:prop>{prop_xml}</D:prop></D:propfind>'
        status, _, text = await self.request(
            "PROPFIND",
            url,
            data=body,
            depth=depth,
            headers={"Content-Type": "application/xml; charset=utf-8"},
        )
        if status != 207:
            raise DavError(f"PROPFIND {url}: unexpected HTTP {status}")
        return parse_multistatus(text, url)

    async def report(self, url: str, body: str, depth: str = "1") -> list[DavResponse]:
        status, _, text = await self.request(
            "REPORT",
            url,
            data=body,
            depth=depth,
            headers={"Content-Type": "application/xml; charset=utf-8"},
        )
        if status != 207:
            raise DavError(f"REPORT {url}: unexpected HTTP {status}")
        return parse_multistatus(text, url)

    async def get(self, url: str) -> tuple[str, str | None]:
        _, headers, text = await self.request("GET", url)
        return text, headers.get("ETag")

    async def put(
        self,
        url: str,
        data: str,
        content_type: str,
        *,
        etag: str | None = None,
        create: bool = False,
    ) -> str | None:
        headers = {"Content-Type": content_type}
        if create:
            headers["If-None-Match"] = "*"
        elif etag:
            headers["If-Match"] = etag
        _, resp_headers, _ = await self.request("PUT", url, data=data, headers=headers)
        return resp_headers.get("ETag")

    async def delete(self, url: str, etag: str | None = None) -> None:
        headers = {"If-Match": etag} if etag else None
        await self.request("DELETE", url, headers=headers)

    # ------------------------------------------------------------ discovery
    async def current_user_principal(self, base_url: str) -> str:
        responses = await self.propfind(base_url, [(NS_DAV, "current-user-principal")], depth="0")
        for resp in responses:
            hrefs = resp.hrefs(NS_DAV, "current-user-principal")
            if hrefs:
                return hrefs[0]
        raise DavError(f"No current-user-principal found at {base_url}")

    async def home_set(self, principal_url: str, ns: str, name: str) -> str:
        responses = await self.propfind(principal_url, [(ns, name)], depth="0")
        for resp in responses:
            hrefs = resp.hrefs(ns, name)
            if hrefs:
                return hrefs[0]
        raise DavError(f"No {name} found at {principal_url}")
