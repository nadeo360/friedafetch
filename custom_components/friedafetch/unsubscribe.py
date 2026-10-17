"""Unsubscribe helper: RFC 8058 one-click POST (public HTTPS only) or a mailto request."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver, ResolveResult
from aiohttp.resolver import DefaultResolver

ONE_CLICK_BODY = "List-Unsubscribe=One-Click"
TIMEOUT = 15


class UnsubscribeError(Exception):
    """Unsubscribing is not possible or failed."""


def _public(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.split("%", 1)[0])
    except ValueError:
        return False
    return addr.is_global and not addr.is_multicast


class PublicResolver(AbstractResolver):
    """Resolver that refuses private, loopback, link-local and other non-public addresses.

    Unsubscribe links come from untrusted e-mail; this prevents requests into the local network,
    also when DNS answers change between checks (the connection uses exactly these addresses).
    """

    def __init__(self) -> None:
        self._resolver = DefaultResolver()

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> list[ResolveResult]:
        results = await self._resolver.resolve(host, port, family)
        public = [r for r in results if _public(r["host"])]
        if not public:
            raise OSError(f"{host} does not resolve to a public address")
        return public

    async def close(self) -> None:
        await self._resolver.close()


def check_url(url: str) -> str:
    """Validate an unsubscribe URL: https, no credentials, no IP literal outside the public internet."""
    parts = urlsplit(url)
    if parts.scheme.lower() != "https" or not parts.hostname:
        raise UnsubscribeError("Only https unsubscribe links are supported")
    if parts.username or parts.password:
        raise UnsubscribeError("Unsubscribe links with credentials are not allowed")
    if parts.port not in (None, 443):
        raise UnsubscribeError("Unsubscribe links must use the standard https port")
    host = parts.hostname
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if host.lower() in ("localhost",) or host.lower().endswith(
            (".local", ".localhost", ".internal", ".lan", ".home.arpa")
        ):
            raise UnsubscribeError("Unsubscribe links to local hosts are not allowed") from None
    else:
        if not _public(host):
            raise UnsubscribeError("Unsubscribe links to non-public addresses are not allowed")
    return url


async def async_one_click(url: str, *, ssl_context: Any = None, user_agent: str = "Frieda") -> dict[str, Any]:
    """POST the RFC 8058 one-click body; redirects are not followed and no cookies are kept."""
    check_url(url)
    connector = aiohttp.TCPConnector(resolver=PublicResolver(), ssl=ssl_context if ssl_context is not None else True)
    async with aiohttp.ClientSession(
        connector=connector, cookie_jar=aiohttp.DummyCookieJar(), timeout=aiohttp.ClientTimeout(total=TIMEOUT)
    ) as session:
        try:
            async with session.post(
                url,
                data=ONE_CLICK_BODY,
                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": user_agent},
                allow_redirects=False,
            ) as resp:
                status = resp.status
        except (aiohttp.ClientError, OSError, TimeoutError) as err:
            raise UnsubscribeError(f"Unsubscribe request failed: {err}") from err
    if status >= 400:
        raise UnsubscribeError(f"The sender rejected the unsubscribe request (HTTP {status})")
    return {"method": "one_click", "status": status, "host": urlsplit(url).hostname}


def parse_mailto(url: str) -> dict[str, str]:
    """Split a mailto: URL into address, subject and body."""
    parts = urlsplit(url)
    if parts.scheme.lower() != "mailto":
        raise UnsubscribeError("Not a mailto link")
    address = unquote(parts.path).strip()
    if "@" not in address or "," in address or " " in address:
        raise UnsubscribeError("Invalid unsubscribe address")
    query = parse_qs(parts.query)
    subject = (query.get("subject") or ["unsubscribe"])[0][:200] or "unsubscribe"
    body = (query.get("body") or ["unsubscribe"])[0][:500] or "unsubscribe"
    return {"address": address, "subject": subject, "body": body}
