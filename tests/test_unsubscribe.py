"""Unsubscribe helper: header parsing and the SSRF guard."""

import socket
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.friedafetch.mail import is_newsletter, list_unsubscribe, parse_message
from custom_components.friedafetch.unsubscribe import PublicResolver, UnsubscribeError, check_url, parse_mailto

NEWSLETTER = (
    b"From: Shop <news@shop.example>\r\nSubject: Angebote\r\n"
    b"List-Unsubscribe: <mailto:leave@shop.example?subject=stop>, <https://shop.example/u/123>\r\n"
    b"List-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n\r\nHallo"
)


def test_list_unsubscribe_and_newsletter() -> None:
    msg = parse_message(NEWSLETTER)
    assert is_newsletter(msg)
    info = list_unsubscribe(msg)
    assert info == {
        "mailto": ["mailto:leave@shop.example?subject=stop"],
        "https": ["https://shop.example/u/123"],
        "one_click": True,
    }
    plain = parse_message(b"From: a@b.example\r\nSubject: hi\r\n\r\nx")
    assert not is_newsletter(plain) and list_unsubscribe(plain) is None
    bulk = parse_message(b"From: a@b.example\r\nPrecedence: bulk\r\n\r\nx")
    assert is_newsletter(bulk)


@pytest.mark.parametrize(
    "url",
    [
        "http://shop.example/u",
        "https://user:pw@shop.example/u",
        "https://shop.example:8443/u",
        "https://localhost/u",
        "https://printer.local/u",
        "https://192.168.1.10/u",
        "https://127.0.0.1/u",
        "https://[::1]/u",
        "ftp://shop.example/u",
    ],
)
def test_check_url_rejects(url: str) -> None:
    with pytest.raises(UnsubscribeError):
        check_url(url)


def test_check_url_accepts_public() -> None:
    assert check_url("https://shop.example/u?id=1") == "https://shop.example/u?id=1"
    assert check_url("https://8.8.8.8/u")


def test_parse_mailto() -> None:
    assert parse_mailto("mailto:leave@shop.example?subject=stop%20now") == {
        "address": "leave@shop.example",
        "subject": "stop now",
        "body": "unsubscribe",
    }
    with pytest.raises(UnsubscribeError):
        parse_mailto("mailto:a@x.example,b@y.example")
    with pytest.raises(UnsubscribeError):
        parse_mailto("https://shop.example")


async def test_public_resolver_drops_private_addresses() -> None:
    resolver = PublicResolver()
    answers = [
        {"hostname": "evil.example", "host": "10.0.0.5", "port": 443, "family": socket.AF_INET, "proto": 0, "flags": 0},
        {
            "hostname": "evil.example",
            "host": "93.184.216.34",
            "port": 443,
            "family": socket.AF_INET,
            "proto": 0,
            "flags": 0,
        },
    ]
    with patch.object(resolver._resolver, "resolve", AsyncMock(return_value=answers)):
        result = await resolver.resolve("evil.example", 443)
    assert [r["host"] for r in result] == ["93.184.216.34"]
    with patch.object(resolver._resolver, "resolve", AsyncMock(return_value=answers[:1])), pytest.raises(OSError):
        await resolver.resolve("evil.example", 443)
    await resolver.close()
