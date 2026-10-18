"""Unsubscribe helper: RFC 8058 one-click POST (public HTTPS only) or a mailto request."""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver, ResolveResult
from aiohttp.resolver import DefaultResolver
from yarl import URL

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


_LOCAL_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home.arpa")
_NUMERIC_HOST = re.compile(r"^(0x[0-9a-f]+|[0-9]+)(\.(0x[0-9a-f]+|[0-9]+))*$")


def _looks_numeric(host: str) -> bool:
    labels = [label for label in host.strip("[]").rstrip(".").split(".") if label]
    decoded = []
    for label in labels:
        if label.lower().startswith("xn--"):
            try:
                label = label.encode("ascii").decode("idna")
            except UnicodeError:
                return True  # broken punycode is not a usable host name either
        decoded.append(label)
    return bool(decoded) and all(label.isdigit() for label in decoded)


def check_url(url: str) -> str:
    """Validate an unsubscribe URL and return it in the form the HTTP client will really use.

    The check runs on the URL as yarl/aiohttp normalise it (IDNA/UTS 46): "https://１２７.０.０.１/" (full-width
    digits) becomes 127.0.0.1 there and, as an IP literal, would bypass the public-only resolver. Rules: https on
    the default port, no credentials, no non-public IP literal, no local host names.
    """
    try:
        parsed = URL(url)
        host = parsed.raw_host
        port = parsed.port
    except (ValueError, TypeError, UnicodeError) as err:
        raise UnsubscribeError("Invalid unsubscribe link") from err
    if parsed.scheme.lower() != "https" or not host:
        raise UnsubscribeError("Only https unsubscribe links are supported")
    if parsed.user or parsed.password:
        raise UnsubscribeError("Unsubscribe links with credentials are not allowed")
    if port != 443:
        raise UnsubscribeError("Unsubscribe links must use the standard https port")
    if not host.isascii():
        raise UnsubscribeError("Invalid host name in the unsubscribe link")
    bare = host.strip("[]").rstrip(".").lower()
    try:
        ipaddress.ip_address(bare.split("%", 1)[0])
    except ValueError:
        if bare in ("localhost",) or bare.endswith(_LOCAL_SUFFIXES):
            raise UnsubscribeError("Unsubscribe links to local hosts are not allowed") from None
        if _NUMERIC_HOST.match(bare) or _looks_numeric(host):
            # shorthand IP forms (127.1, 0x7f.0.0.1, 2130706433) or digits of other scripts that only look like
            # an address (e.g. Arabic-Indic); the resolver would catch most of them too
            raise UnsubscribeError("Unsubscribe links must use a host name, not a numeric address") from None
    else:
        if not _public(bare):
            raise UnsubscribeError("Unsubscribe links to non-public addresses are not allowed")
    return str(parsed)


async def async_one_click(url: str, *, ssl_context: Any = None, user_agent: str = "Frieda") -> dict[str, Any]:
    """POST the RFC 8058 one-click body; redirects are not followed and no cookies are kept."""
    url = check_url(url)  # request exactly the normalised URL that was checked
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
    try:
        parts = urlsplit(url)
    except ValueError as err:
        raise UnsubscribeError("Invalid unsubscribe link") from err
    if parts.scheme.lower() != "mailto":
        raise UnsubscribeError("Not a mailto link")
    address = unquote(parts.path).strip()
    if "@" not in address or "," in address or " " in address:
        raise UnsubscribeError("Invalid unsubscribe address")
    query = parse_qs(parts.query)
    subject = (query.get("subject") or ["unsubscribe"])[0][:200] or "unsubscribe"
    body = (query.get("body") or ["unsubscribe"])[0][:500] or "unsubscribe"
    return {"address": address, "subject": subject, "body": body}
