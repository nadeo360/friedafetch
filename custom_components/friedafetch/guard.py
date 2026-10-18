"""Guard rails for writing tools: quotas, recipient policy and protected areas."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Iterable
from typing import Any

from .const import (
    CONF_HIDDEN_MAILBOXES,
    CONF_LIMIT_ITEM_DELETE,
    CONF_LIMIT_MAIL_MODIFY,
    CONF_LIMIT_MAIL_SEND,
    CONF_PROTECTED_CALENDARS,
    CONF_PROTECTED_MAILBOXES,
    CONF_SEND_ALLOW_BCC,
    CONF_SEND_ALLOWLIST,
    CONF_SEND_MAX_RECIPIENTS,
    CONF_SEND_POLICY,
    DEFAULT_LIMIT_ITEM_DELETE,
    DEFAULT_LIMIT_MAIL_MODIFY,
    DEFAULT_LIMIT_MAIL_SEND,
    DEFAULT_SEND_ALLOW_BCC,
    DEFAULT_SEND_MAX_RECIPIENTS,
    DEFAULT_SEND_POLICY,
)

WINDOW_SECONDS = 3600
QUOTA_MAIL_MODIFY = "mail_modify"
QUOTA_MAIL_SEND = "mail_send"
QUOTA_ITEM_DELETE = "item_delete"

_LIMIT_OPTIONS = {
    QUOTA_MAIL_MODIFY: (CONF_LIMIT_MAIL_MODIFY, DEFAULT_LIMIT_MAIL_MODIFY),
    QUOTA_MAIL_SEND: (CONF_LIMIT_MAIL_SEND, DEFAULT_LIMIT_MAIL_SEND),
    QUOTA_ITEM_DELETE: (CONF_LIMIT_ITEM_DELETE, DEFAULT_LIMIT_ITEM_DELETE),
}


class PolicyError(Exception):
    """A write was blocked by the configured guard rails."""


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.replace(";", ",").split(",") if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def _norm(value: str) -> str:
    return value.strip().lower()


class Guard:
    """Evaluates the security options of one account."""

    def __init__(self, options: dict[str, Any], clock=time.monotonic) -> None:
        self._options = options
        self._clock = clock
        self._windows: dict[str, deque[tuple[float, int]]] = {k: deque() for k in _LIMIT_OPTIONS}
        self.on_change: Any | None = None  # called after every consume, so the usage survives a restart

    # ------------------------------------------------------------- quotas
    def limit(self, category: str) -> int:
        key, default = _LIMIT_OPTIONS[category]
        try:
            return max(0, int(self._options.get(key, default)))
        except (TypeError, ValueError):
            return default

    def used(self, category: str) -> int:
        now = self._clock()
        window = self._windows[category]
        while window and now - window[0][0] > WINDOW_SECONDS:
            window.popleft()
        return sum(n for _, n in window)

    def check_quota(self, category: str, amount: int = 1) -> None:
        limit = self.limit(category)
        if limit == 0:
            return
        used = self.used(category)
        if used + amount > limit:
            raise PolicyError(
                f"Hourly limit reached for {category.replace('_', ' ')}: {used}/{limit} used, "
                f"{amount} more requested. Raise the limit in the integration options or wait."
            )

    def consume(self, category: str, amount: int = 1) -> None:
        if amount > 0:
            self._windows[category].append((self._clock(), amount))
            if self.on_change is not None:
                self.on_change()

    def export(self, wall: float | None = None) -> dict[str, list[list[float]]]:
        """Usage of the last hour with wall-clock times (for storage)."""
        now, wall = self._clock(), time.time() if wall is None else wall
        return {
            category: [[round(wall - (now - t), 3), n] for t, n in window if now - t <= WINDOW_SECONDS]
            for category, window in self._windows.items()
        }

    def restore(self, data: Any, wall: float | None = None) -> None:
        """Take over stored usage, so a restart or reload does not refill the hourly quotas."""
        if not isinstance(data, dict):
            return
        now, wall = self._clock(), time.time() if wall is None else wall
        for category, items in data.items():
            window = self._windows.get(category)
            if window is None or not isinstance(items, list):
                continue
            for item in items:
                try:
                    stamp, amount = float(item[0]), int(item[1])
                except (TypeError, ValueError, IndexError):
                    continue
                age = wall - stamp
                if 0 <= age <= WINDOW_SECONDS and amount > 0:
                    window.append((now - age, amount))

    def quota_status(self) -> dict[str, dict[str, int]]:
        return {c: {"used": self.used(c), "limit": self.limit(c)} for c in _LIMIT_OPTIONS}

    # --------------------------------------------------------- recipients
    def check_recipients(
        self, to: Iterable[str], cc: Iterable[str] | None, bcc: Iterable[str] | None, known: set[str] | None
    ) -> None:
        to_l, cc_l, bcc_l = list(to), list(cc or []), list(bcc or [])
        recipients = [*to_l, *cc_l, *bcc_l]
        if not recipients:
            raise PolicyError("At least one recipient is required")
        max_rcpt = int(self._options.get(CONF_SEND_MAX_RECIPIENTS, DEFAULT_SEND_MAX_RECIPIENTS) or 0)
        if max_rcpt and len(recipients) > max_rcpt:
            raise PolicyError(f"Too many recipients ({len(recipients)}); the limit is {max_rcpt}")
        if bcc_l and not self._options.get(CONF_SEND_ALLOW_BCC, DEFAULT_SEND_ALLOW_BCC):
            raise PolicyError("BCC recipients are not allowed by the integration options")
        policy = str(self._options.get(CONF_SEND_POLICY, DEFAULT_SEND_POLICY) or DEFAULT_SEND_POLICY)
        if policy == "any":
            return
        allow = {_norm(a) for a in _as_list(self._options.get(CONF_SEND_ALLOWLIST))}
        known_set = {_norm(k) for k in (known or set())}
        rejected: list[str] = []
        for addr in recipients:
            a = _norm(addr)
            if "<" in a and ">" in a:
                a = a[a.index("<") + 1 : a.index(">")]
            domain = a.rsplit("@", 1)[-1] if "@" in a else ""
            ok = False
            if policy in ("contacts", "allowlist") and a in known_set and policy == "contacts":
                ok = True
            if a in allow or (domain and (domain in allow or f"@{domain}" in allow)):
                ok = True
            if any(domain.endswith("." + d.lstrip("@")) for d in allow if d):
                ok = True
            if not ok:
                rejected.append(addr)
        if rejected:
            what = "known contacts or the allowlist" if policy == "contacts" else "the allowlist"
            raise PolicyError(f"Recipients not permitted by the send policy ({what}): {', '.join(rejected)}")

    @property
    def requires_contacts(self) -> bool:
        return str(self._options.get(CONF_SEND_POLICY, DEFAULT_SEND_POLICY)) == "contacts"

    # ----------------------------------------------------- protected areas
    def _in(self, key: str, *candidates: str | None) -> bool:
        values = {_norm(v) for v in _as_list(self._options.get(key))}
        return any(_norm(c) in values for c in candidates if c)

    def check_calendar_writable(self, calendar_id: str | None, calendar_name: str | None = None) -> None:
        if self._in(CONF_PROTECTED_CALENDARS, calendar_id, calendar_name):
            raise PolicyError(f"Calendar '{calendar_name or calendar_id}' is protected (read-only)")

    def is_mailbox_hidden(self, mailbox: str | None) -> bool:
        return self._in(CONF_HIDDEN_MAILBOXES, mailbox)

    def check_mailbox_visible(self, mailbox: str | None) -> None:
        if self.is_mailbox_hidden(mailbox):
            raise PolicyError(f"Mailbox '{mailbox}' is not available")

    def check_mailbox_writable(self, mailbox: str | None) -> None:
        self.check_mailbox_visible(mailbox)
        if self._in(CONF_PROTECTED_MAILBOXES, mailbox):
            raise PolicyError(f"Mailbox '{mailbox}' is protected (read-only)")

    def filter_mailboxes(self, boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [b for b in boxes if not self.is_mailbox_hidden(b.get("name"))]
