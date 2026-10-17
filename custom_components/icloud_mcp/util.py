"""Shared helpers."""

from __future__ import annotations

import html
import re
from datetime import date, datetime, time, timedelta, tzinfo
from html.parser import HTMLParser
from typing import Any


class _TextExtractor(HTMLParser):
    _BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "table"}
    _SKIP = {"script", "style", "head", "title"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self._SKIP:
            self._skip += 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip()


def html_to_text(markup: str) -> str:
    """Convert HTML to readable plain text."""
    parser = _TextExtractor()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:  # noqa: BLE001 - be lenient with broken markup
        return re.sub(r"<[^>]+>", "", markup)
    return parser.text()


def text_to_html(text: str) -> str:
    """Wrap plain text into minimal HTML."""
    body = html.escape(text).replace("\n", "<br>\n")
    return f"<html><body><div>{body}</div></body></html>"


def parse_datetime(value: str, tz: tzinfo) -> datetime | date:
    """Parse an ISO 8601 string from the LLM.

    Returns a ``date`` for date-only values and a timezone-aware ``datetime``
    otherwise (naive values are interpreted in ``tz``).
    """
    raw = value.strip()
    if not raw:
        raise ValueError("empty date/time")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return date.fromisoformat(raw)
    raw = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as err:
        raise ValueError(f"Invalid ISO 8601 date/time: {value!r}") from err
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed


def to_datetime(value: datetime | date, tz: tzinfo, end: bool = False) -> datetime:
    """Coerce a date into a datetime at start (or end) of day."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=tz)
    base = datetime.combine(value, time.min, tzinfo=tz)
    return base + timedelta(days=1) if end else base


def isoformat(value: datetime | date | None, tz: tzinfo) -> str | None:
    """Format for tool output: dates as YYYY-MM-DD, datetimes in local tz."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=tz)
        return value.astimezone(tz).isoformat(timespec="minutes")
    return value.isoformat()


def clamp(value: int | None, default: int, maximum: int) -> int:
    if value is None:
        return default
    return max(1, min(int(value), maximum))
