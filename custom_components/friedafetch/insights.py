"""Read-only evaluations on top of the iCloud data: mailbox statistics, birthdays, duplicates, free time."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Any

# Apple stores birthdays without a year with this placeholder year.
_NO_YEAR = {1604, 1900}


def _domain(address: str) -> str:
    return address.rsplit("@", 1)[-1].lower() if "@" in address else ""


def mailbox_stats(
    summaries: Iterable[dict[str, Any]],
    *,
    covered: Callable[[dict[str, Any]], str | None] | None = None,
    top: int = 15,
    suggest_min: int = 3,
) -> dict[str, Any]:
    """Aggregate message summaries by sender and domain and suggest rule candidates.

    ``covered`` returns the name of a rule that already matches a summary (or None).
    """
    total = unread = newsletters = 0
    senders: dict[str, dict[str, Any]] = {}
    domains: dict[str, dict[str, Any]] = {}
    for s in summaries:
        total += 1
        seen = bool(s.get("seen"))
        news = bool(s.get("newsletter"))
        unread += not seen
        newsletters += news
        sender = (s.get("from") or [{}])[0]
        email = (sender.get("email") or "").lower()
        if not email:
            continue
        rule = covered(s) if covered else None
        entry = senders.setdefault(
            email,
            {
                "email": email,
                "name": sender.get("name") or "",
                "count": 0,
                "unread": 0,
                "newsletter": 0,
                "covered_by": None,
            },
        )
        dom = domains.setdefault(
            _domain(email),
            {"domain": _domain(email), "count": 0, "unread": 0, "newsletter": 0, "senders": set(), "covered": 0},
        )
        for item in (entry, dom):
            item["count"] += 1
            item["unread"] += not seen
            item["newsletter"] += news
        dom["senders"].add(email)
        if rule:
            entry["covered_by"] = rule
            dom["covered"] += 1
    top_senders = sorted(senders.values(), key=lambda e: (-e["count"], e["email"]))[:top]
    top_domains = sorted(domains.values(), key=lambda e: (-e["count"], e["domain"]))[:top]
    suggestions = [
        {
            "domain": d["domain"],
            "messages": d["count"],
            "unread": d["unread"],
            "reason": "newsletter" if d["newsletter"] * 2 >= d["count"] else "frequent",
        }
        for d in sorted(domains.values(), key=lambda e: (-e["count"], e["domain"]))
        if d["count"] >= suggest_min
        and d["covered"] == 0
        and d["domain"]
        and (d["newsletter"] * 2 >= d["count"] or d["unread"] * 2 >= d["count"])
    ][:top]
    return {
        "messages": total,
        "unread": unread,
        "newsletters": newsletters,
        "newsletter_share": round(newsletters / total, 2) if total else 0.0,
        "top_senders": [{**e, "newsletter": e["newsletter"] > 0} for e in top_senders],
        "top_domains": [
            {k: (len(v) if k == "senders" else v) for k, v in d.items() if k != "covered"}
            | {"covered": d["covered"] > 0}
            for d in top_domains
        ],
        "rule_suggestions": suggestions,
    }


def _parse_birthday(value: str | None) -> tuple[int | None, int, int] | None:
    if not value:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value) or re.fullmatch(r"(-)-(\d{2})-(\d{2})", value)
    if not m:
        return None
    year = None if m.group(1) == "-" else int(m.group(1))
    if year in _NO_YEAR:
        year = None
    return year, int(m.group(2)), int(m.group(3))


def _next_occurrence(month: int, day: int, today: date) -> date:
    for year in (today.year, today.year + 1, today.year + 2):
        try:
            candidate = date(year, month, day)
        except ValueError:  # 29 February in a non-leap year -> 28 February
            candidate = date(year, month, 28)
        if candidate >= today:
            return candidate
    return date(today.year + 1, month, min(day, 28))


def upcoming_birthdays(contacts: Iterable[dict[str, Any]], today: date, days: int = 30) -> list[dict[str, Any]]:
    """Birthdays within the next ``days`` days (including today), soonest first."""
    result: list[dict[str, Any]] = []
    for c in contacts:
        parsed = _parse_birthday(c.get("birthday"))
        if parsed is None:
            continue
        year, month, day = parsed
        nxt = _next_occurrence(month, day, today)
        delta = (nxt - today).days
        if delta > days:
            continue
        result.append(
            {
                "uid": c.get("uid"),
                "name": c.get("full_name") or "",
                "date": nxt.isoformat(),
                "in_days": delta,
                "turns": (nxt.year - year) if year else None,
                "birthday": c.get("birthday"),
            }
        )
    result.sort(key=lambda b: (b["in_days"], b["name"].lower()))
    return result


def _norm_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[-9:] if len(digits) >= 7 else ""


def _norm_name(value: str | None) -> str:
    return " ".join(sorted(re.sub(r"[^\w ]", " ", (value or "").lower()).split()))


def duplicate_contacts(contacts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group contacts that share an e-mail address, a phone number or the same name."""
    items = [c for c in contacts if c.get("uid")]
    parent = {c["uid"]: c["uid"] for c in items}
    reasons: dict[frozenset[str], set[str]] = defaultdict(set)

    def find(u: str) -> str:
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    keys: dict[tuple[str, str], list[str]] = defaultdict(list)
    for c in items:
        for e in c.get("emails") or []:
            if e.get("value"):
                keys[("email", e["value"].strip().lower())].append(c["uid"])
        for ph in c.get("phones") or []:
            if norm := _norm_phone(ph.get("value", "")):
                keys[("phone", norm)].append(c["uid"])
        if (name := _norm_name(c.get("full_name"))) and len(name) > 2:
            keys[("name", name)].append(c["uid"])
    for (kind, _), uids in keys.items():
        uniq = sorted(set(uids))
        if len(uniq) < 2:
            continue
        for other in uniq[1:]:
            parent[find(other)] = find(uniq[0])
        reasons[frozenset(uniq)].add(kind)
    groups: dict[str, list[str]] = defaultdict(list)
    for c in items:
        groups[find(c["uid"])].append(c["uid"])
    by_uid = {c["uid"]: c for c in items}
    result = []
    for members in groups.values():
        if len(members) < 2:
            continue
        member_set = set(members)
        why = sorted({r for key, kinds in reasons.items() if key <= member_set for r in kinds})
        result.append(
            {
                "reasons": why,
                "contacts": [
                    {
                        "uid": u,
                        "name": by_uid[u].get("full_name"),
                        "emails": [e.get("value") for e in by_uid[u].get("emails") or []],
                        "phones": [p.get("value") for p in by_uid[u].get("phones") or []],
                        "organization": by_uid[u].get("organization"),
                    }
                    for u in sorted(members)
                ],
            }
        )
    result.sort(key=lambda g: -len(g["contacts"]))
    return result


def _parse_clock(value: str | None, default: time) -> time:
    if not value:
        return default
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", value.strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise ValueError(f"Invalid time of day '{value}' (expected HH:MM)")
    return time(int(m.group(1)), int(m.group(2)))


def free_slots(
    events: Iterable[dict[str, Any]],
    *,
    start: datetime,
    end: datetime,
    duration: timedelta,
    tz: tzinfo,
    day_start: str | None = None,
    day_end: str | None = None,
    weekdays_only: bool = True,
    include_all_day: bool = False,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Free time windows of at least ``duration`` inside working hours that do not overlap busy events."""
    if duration <= timedelta(0):
        raise ValueError("duration must be positive")
    t_start = _parse_clock(day_start, time(8, 0))
    t_end = _parse_clock(day_end, time(18, 0))
    if t_end <= t_start:
        raise ValueError("day_end must be after day_start")
    busy: list[tuple[datetime, datetime]] = []
    for ev in events:
        if ev.get("transparent") or (ev.get("status") or "").upper() == "CANCELLED":
            continue
        if ev.get("all_day"):
            if not include_all_day:
                continue
            s_day = date.fromisoformat(ev["start"][:10])
            e_day = date.fromisoformat((ev.get("end") or ev["start"])[:10]) + timedelta(days=1)
            busy.append((datetime.combine(s_day, time(0), tz), datetime.combine(e_day, time(0), tz)))
            continue
        if not ev.get("start") or not ev.get("end"):
            continue
        busy.append((datetime.fromisoformat(ev["start"]), datetime.fromisoformat(ev["end"])))
    busy.sort()
    slots: list[dict[str, Any]] = []
    day = start.astimezone(tz).date()
    last_day = end.astimezone(tz).date()
    while day <= last_day and len(slots) < limit:
        if not (weekdays_only and day.weekday() >= 5):
            window_start = max(datetime.combine(day, t_start, tz), start)
            window_end = min(datetime.combine(day, t_end, tz), end)
            cursor = window_start
            for b_start, b_end in busy:
                if b_end <= cursor or b_start >= window_end:
                    continue
                if b_start - cursor >= duration:
                    slots.append(_slot(cursor, b_start))
                cursor = max(cursor, b_end)
                if len(slots) >= limit:
                    break
            if window_end - cursor >= duration and len(slots) < limit:
                slots.append(_slot(cursor, window_end))
        day += timedelta(days=1)
    return slots[:limit]


def _slot(a: datetime, b: datetime) -> dict[str, Any]:
    return {
        "start": a.isoformat(timespec="minutes"),
        "end": b.isoformat(timespec="minutes"),
        "minutes": int((b - a).total_seconds() // 60),
    }
