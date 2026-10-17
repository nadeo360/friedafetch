"""Minimal vCard 3.0 parser/serializer tailored to iCloud CardDAV.

Only the properties exposed through the MCP tools are interpreted; everything
else (PHOTO, X-* extensions, ...) is preserved verbatim so that updates do not
destroy data we do not understand.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

_FOLD_LIMIT = 75

# Labels iCloud/macOS Contacts use for custom labels, e.g. ``_$!<Home>!$_``.
_ABLABEL_RE = re.compile(r"^_\$!<(.+)>!\$_$")
_IGNORED_TYPES = {"pref", "internet", "voice", "x400"}


def _unescape(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            if nxt in ("n", "N"):
                out.append("\n")
            elif nxt in (",", ";", "\\"):
                out.append(nxt)
            else:
                out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "").replace(",", "\\,").replace(";", "\\;")


def _split_unescaped(value: str, sep: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            cur.append(ch)
            cur.append(value[i + 1])
            i += 2
            continue
        if ch == sep:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw:
            continue
        if raw[0] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _fold(line: str) -> str:
    encoded = line.encode("utf-8")
    if len(encoded) <= _FOLD_LIMIT:
        return line
    out: list[str] = []
    cur = b""
    for ch in line:
        b = ch.encode("utf-8")
        limit = _FOLD_LIMIT if not out else _FOLD_LIMIT - 1
        if len(cur) + len(b) > limit:
            out.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    if cur:
        out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)


@dataclass
class Property:
    """A single vCard content line."""

    name: str  # upper-cased for comparisons
    value: str  # escaped raw value as it appears in the vCard
    params: dict[str, list[str]] = field(default_factory=dict)
    group: str | None = None
    raw_name: str | None = None  # original casing (Apple writes e.g. X-ABLabel)

    @property
    def text(self) -> str:
        """Unescaped text value."""
        return _unescape(self.value)

    @property
    def components(self) -> list[str]:
        """Unescaped structured components (for N, ADR, ORG)."""
        return [_unescape(part) for part in _split_unescaped(self.value, ";")]

    @property
    def types(self) -> list[str]:
        return [t.lower() for t in self.params.get("TYPE", [])]

    @property
    def preferred(self) -> bool:
        return "pref" in self.types or "PREF" in self.params

    def serialize(self) -> str:
        name = self.raw_name or self.name
        head = name if not self.group else f"{self.group}.{name}"
        parts = [head]
        for key, values in self.params.items():
            for val in values:
                if any(c in val for c in (";", ":", ",")):
                    val = f'"{val}"'
                parts.append(f"{key}={val}")
        return _fold(";".join(parts) + ":" + self.value)

    @classmethod
    def parse(cls, line: str) -> Property:
        # split at first ':' outside of quotes
        in_quotes = False
        idx = -1
        for i, ch in enumerate(line):
            if ch == '"':
                in_quotes = not in_quotes
            elif ch == ":" and not in_quotes:
                idx = i
                break
        if idx < 0:
            raise ValueError(f"Invalid vCard line: {line!r}")
        head, value = line[:idx], line[idx + 1 :]
        # split head by ';' outside quotes
        segments: list[str] = []
        cur: list[str] = []
        in_quotes = False
        for ch in head:
            if ch == '"':
                in_quotes = not in_quotes
                continue
            if ch == ";" and not in_quotes:
                segments.append("".join(cur))
                cur = []
            else:
                cur.append(ch)
        segments.append("".join(cur))
        name = segments[0]
        group: str | None = None
        if "." in name:
            group, name = name.split(".", 1)
        params: dict[str, list[str]] = {}
        for seg in segments[1:]:
            if not seg:
                continue
            if "=" in seg:
                key, val = seg.split("=", 1)
                params.setdefault(key.upper(), []).extend(v for v in val.split(",") if v != "")
            else:  # vCard 2.1 style bare type
                params.setdefault("TYPE", []).append(seg)
        return cls(name=name.upper(), value=value, params=params, group=group, raw_name=name)


def _label_for(prop: Property, labels: dict[str, str]) -> str | None:
    if prop.group and prop.group in labels:
        return labels[prop.group]
    for t in prop.types:
        if t not in _IGNORED_TYPES:
            return t
    return None


def _normalize_date(value: str) -> str:
    v = value.strip()
    if re.fullmatch(r"\d{8}", v):
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
    if re.fullmatch(r"--\d{4}", v):  # year-less (vCard 4 style)
        return f"--{v[2:4]}-{v[4:6]}"
    return v[:10]


class VCard:
    """A parsed vCard."""

    def __init__(self, props: list[Property] | None = None) -> None:
        self.props: list[Property] = props or []

    # ------------------------------------------------------------------ parsing
    @classmethod
    def parse(cls, text: str) -> VCard:
        cards = cls.parse_all(text)
        if not cards:
            raise ValueError("No VCARD found")
        return cards[0]

    @classmethod
    def parse_all(cls, text: str) -> list[VCard]:
        cards: list[VCard] = []
        current: list[Property] | None = None
        for line in _unfold(text):
            upper = line.upper()
            if upper.startswith("BEGIN:VCARD"):
                current = []
                continue
            if upper.startswith("END:VCARD"):
                if current is not None:
                    cards.append(cls(current))
                current = None
                continue
            if current is None:
                continue
            try:
                prop = Property.parse(line)
            except ValueError:
                continue
            if prop.name in ("VERSION", "PRODID"):
                continue
            current.append(prop)
        return cards

    def serialize(self) -> str:
        lines = ["BEGIN:VCARD", "VERSION:3.0", "PRODID:-//Home Assistant//iCloud MCP//EN"]
        lines.extend(p.serialize() for p in self.props)
        lines.append("END:VCARD")
        return "\r\n".join(lines) + "\r\n"

    # ------------------------------------------------------------ prop access
    def get(self, name: str) -> Property | None:
        name = name.upper()
        return next((p for p in self.props if p.name == name), None)

    def get_all(self, name: str) -> list[Property]:
        name = name.upper()
        return [p for p in self.props if p.name == name]

    def remove_all(self, name: str) -> None:
        name = name.upper()
        removed_groups = {p.group for p in self.props if p.name == name and p.group}
        self.props = [p for p in self.props if p.name != name]
        # drop orphaned X-ABLabel entries
        used_groups = {p.group for p in self.props if p.group and p.name != "X-ABLABEL"}
        self.props = [
            p
            for p in self.props
            if not (p.name == "X-ABLABEL" and p.group in removed_groups and p.group not in used_groups)
        ]

    def set_single(self, name: str, value: str, params: dict[str, list[str]] | None = None) -> None:
        name = name.upper()
        self.remove_all(name)
        self.props.append(Property(name=name, value=value, params=params or {}))

    def _next_group(self) -> str:
        used = {p.group for p in self.props if p.group}
        n = 1
        while f"item{n}" in used:
            n += 1
        return f"item{n}"

    def add_typed(self, name: str, value: str, label: str | None) -> None:
        """Add EMAIL/TEL/URL with a label (home/work/mobile/custom)."""
        params: dict[str, list[str]] = {}
        std = {"home", "work", "cell", "mobile", "main", "fax", "pager", "other"}
        group: str | None = None
        if label:
            lab = label.strip()
            if lab.lower() in std:
                params["TYPE"] = ["CELL" if lab.lower() == "mobile" else lab.upper()]
            else:
                group = self._next_group()
        if name.upper() == "EMAIL":
            params.setdefault("TYPE", []).insert(0, "INTERNET")
        prop = Property(name=name.upper(), value=_escape(value), params=params, group=group)
        self.props.append(prop)
        if group and label:
            self.props.append(
                Property(name="X-ABLABEL", value=_escape(label.strip()), group=group, raw_name="X-ABLabel")
            )

    def add_address(self, addr: dict[str, Any]) -> None:
        comps = [
            addr.get("po_box", "") or "",
            addr.get("extended", "") or "",
            addr.get("street", "") or "",
            addr.get("city", "") or "",
            addr.get("region", "") or "",
            addr.get("postal_code", "") or "",
            addr.get("country", "") or "",
        ]
        params: dict[str, list[str]] = {}
        label = addr.get("type") or addr.get("label")
        if label:
            params["TYPE"] = [str(label).upper()]
        self.props.append(Property(name="ADR", value=";".join(_escape(c) for c in comps), params=params))

    # ------------------------------------------------------------ convenience
    @property
    def uid(self) -> str | None:
        p = self.get("UID")
        return p.text if p else None

    def ensure_uid(self) -> str:
        if not self.uid:
            self.set_single("UID", str(uuid.uuid4()).upper())
        return self.uid or ""

    @property
    def full_name(self) -> str | None:
        p = self.get("FN")
        return p.text if p else None

    def set_name(
        self,
        given: str | None = None,
        family: str | None = None,
        additional: str | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
        full_name: str | None = None,
    ) -> None:
        existing = self.get("N")
        comps = existing.components if existing else ["", "", "", "", ""]
        comps = (comps + [""] * 5)[:5]
        if family is not None:
            comps[0] = family
        if given is not None:
            comps[1] = given
        if additional is not None:
            comps[2] = additional
        if prefix is not None:
            comps[3] = prefix
        if suffix is not None:
            comps[4] = suffix
        self.set_single("N", ";".join(_escape(c) for c in comps))
        if full_name is None:
            full_name = " ".join(part for part in (comps[3], comps[1], comps[2], comps[0], comps[4]) if part)
        if full_name:
            self.set_single("FN", _escape(full_name))

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        labels = {
            p.group: (_ABLABEL_RE.sub(r"\1", p.text).lower()) for p in self.props if p.name == "X-ABLABEL" and p.group
        }
        n = self.get("N")
        comps = (n.components + [""] * 5)[:5] if n else [""] * 5
        org = self.get("ORG")
        org_comps = org.components if org else []
        bday = self.get("BDAY")
        result: dict[str, Any] = {
            "uid": self.uid,
            "full_name": self.full_name,
            "family_name": comps[0] or None,
            "given_name": comps[1] or None,
            "additional_names": comps[2] or None,
            "prefix": comps[3] or None,
            "suffix": comps[4] or None,
            "nickname": (self.get("NICKNAME").text if self.get("NICKNAME") else None),
            "organization": org_comps[0] if org_comps else None,
            "department": org_comps[1] if len(org_comps) > 1 and org_comps[1] else None,
            "title": self.get("TITLE").text if self.get("TITLE") else None,
            "emails": [
                {"label": _label_for(p, labels), "value": p.text, "preferred": p.preferred}
                for p in self.get_all("EMAIL")
            ],
            "phones": [
                {"label": _label_for(p, labels), "value": p.text, "preferred": p.preferred} for p in self.get_all("TEL")
            ],
            "addresses": [],
            "urls": [{"label": _label_for(p, labels), "value": p.text} for p in self.get_all("URL")],
            "birthday": _normalize_date(bday.text) if bday else None,
            "note": self.get("NOTE").text if self.get("NOTE") else None,
        }
        for p in self.get_all("ADR"):
            c = (p.components + [""] * 7)[:7]
            result["addresses"].append(
                {
                    "label": _label_for(p, labels),
                    "po_box": c[0] or None,
                    "extended": c[1] or None,
                    "street": c[2] or None,
                    "city": c[3] or None,
                    "region": c[4] or None,
                    "postal_code": c[5] or None,
                    "country": c[6] or None,
                }
            )
        if include_raw:
            result["raw"] = self.serialize()
        return result

    def matches(self, query: str) -> bool:
        """Case-insensitive substring match across the common fields."""
        q = query.lower().strip()
        if not q:
            return True
        haystack: list[str] = []
        for name in ("FN", "N", "NICKNAME", "ORG", "EMAIL", "TEL", "NOTE", "TITLE", "ADR"):
            haystack.extend(p.text for p in self.get_all(name))
        joined = " ".join(haystack).lower()
        if q in joined:
            return True
        # phone number match ignoring formatting
        digits = re.sub(r"\D", "", q).lstrip("0")
        if len(digits) >= 4:
            tel_digits = " ".join(re.sub(r"\D", "", p.text) for p in self.get_all("TEL"))
            if digits in tel_digits:
                return True
        return all(tok in joined for tok in q.split())


def escape_text(value: str) -> str:
    """Public helper for escaped single values."""
    return _escape(value)
