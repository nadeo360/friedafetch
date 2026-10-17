"""Mailbox statistics, birthdays, duplicate contacts and free time slots."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from custom_components.friedafetch.insights import duplicate_contacts, free_slots, mailbox_stats, upcoming_birthdays

TZ = ZoneInfo("Europe/Berlin")


def _mail(sender: str, seen: bool = True, newsletter: bool = False) -> dict:
    return {"from": [{"name": sender.split("@")[0], "email": sender}], "seen": seen, "newsletter": newsletter}


def test_mailbox_stats_and_suggestions() -> None:
    summaries = (
        [_mail("news@shop.example", seen=False, newsletter=True)] * 5
        + [_mail("chef@firma.example")] * 4
        + [_mail("info@covered.example", newsletter=True)] * 3
    )
    stats = mailbox_stats(summaries, covered=lambda s: "Abo" if "covered" in s["from"][0]["email"] else None)
    assert stats["messages"] == 12 and stats["unread"] == 5 and stats["newsletters"] == 8
    assert stats["top_senders"][0]["email"] == "news@shop.example"
    covered = {d["domain"]: d["covered"] for d in stats["top_domains"]}
    assert covered == {"shop.example": False, "firma.example": False, "covered.example": True}
    # newsletters that no rule handles are suggested; read mail from a person is not
    assert [s["domain"] for s in stats["rule_suggestions"]] == ["shop.example"]
    assert stats["rule_suggestions"][0]["reason"] == "newsletter"


def test_upcoming_birthdays() -> None:
    today = date(2026, 10, 17)
    contacts = [
        {"uid": "1", "full_name": "Anna", "birthday": "1990-10-17"},
        {"uid": "2", "full_name": "Ben", "birthday": "1604-10-20"},  # Apple: year unknown
        {"uid": "3", "full_name": "Cleo", "birthday": "--11-01"},
        {"uid": "4", "full_name": "Dora", "birthday": "1980-03-01"},  # too far away
        {"uid": "5", "full_name": "Emil", "birthday": "bogus"},
        {"uid": "6", "full_name": "Fritz"},
    ]
    result = upcoming_birthdays(contacts, today, days=30)
    assert [(b["name"], b["in_days"], b["turns"]) for b in result] == [
        ("Anna", 0, 36),
        ("Ben", 3, None),
        ("Cleo", 15, None),
    ]
    # 29 February is celebrated on 28 February in other years
    leap = upcoming_birthdays([{"uid": "7", "full_name": "Lea", "birthday": "2000-02-29"}], date(2027, 2, 20), days=10)
    assert leap[0]["date"] == "2027-02-28"


def test_duplicate_contacts() -> None:
    contacts = [
        {"uid": "a", "full_name": "Max Muster", "emails": [{"value": "max@example.com"}], "phones": []},
        {"uid": "b", "full_name": "Maximilian", "emails": [{"value": "MAX@example.com"}], "phones": []},
        {"uid": "c", "full_name": "Muster Max", "emails": [], "phones": [{"value": "+49 170 1234567"}]},
        {"uid": "d", "full_name": "Zoe", "emails": [], "phones": [{"value": "0170/1234567"}]},
        {"uid": "e", "full_name": "Single", "emails": [{"value": "single@example.com"}], "phones": []},
    ]
    groups = duplicate_contacts(contacts)
    assert len(groups) == 1
    assert {c["uid"] for c in groups[0]["contacts"]} == {"a", "b", "c", "d"}
    assert set(groups[0]["reasons"]) == {"email", "name", "phone"}


def test_free_slots() -> None:
    start = datetime(2026, 10, 19, 7, 0, tzinfo=TZ)  # Monday
    events = [
        {"start": "2026-10-19T09:00:00+02:00", "end": "2026-10-19T10:30:00+02:00", "all_day": False},
        {"start": "2026-10-19T12:00:00+02:00", "end": "2026-10-19T17:30:00+02:00", "all_day": False},
        {"start": "2026-10-19T10:30:00+02:00", "end": "2026-10-19T11:00:00+02:00", "transparent": True},
        {"start": "2026-10-19", "end": "2026-10-19", "all_day": True},
    ]
    slots = free_slots(events, start=start, end=start + timedelta(days=1), duration=timedelta(minutes=60), tz=TZ)
    assert [(s["start"][11:16], s["end"][11:16]) for s in slots] == [("08:00", "09:00"), ("10:30", "12:00")]
    # weekends are skipped by default, all-day events can be made busy
    weekend = free_slots(
        [],
        start=datetime(2026, 10, 24, 0, 0, tzinfo=TZ),
        end=datetime(2026, 10, 25, 23, 0, tzinfo=TZ),
        duration=timedelta(minutes=30),
        tz=TZ,
    )
    assert weekend == []
    busy_day = free_slots(
        events,
        start=start,
        end=start + timedelta(hours=12),
        duration=timedelta(minutes=30),
        tz=TZ,
        include_all_day=True,
    )
    assert busy_day == []
    with pytest.raises(ValueError):
        free_slots([], start=start, end=start, duration=timedelta(minutes=30), tz=TZ, day_start="25:00")
