"""Inbox rules evaluated and executed by the integration.

iCloud exposes no API for its server-side mail rules, so rules live in Home
Assistant storage and are applied by this integration: periodically to new
messages and on demand to a whole mailbox.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .mail import ICloudMail, MailboxNotFound, MailError

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
FIELDS = ("from", "to", "cc", "subject", "any")
OPS = ("contains", "equals", "starts_with", "ends_with", "domain", "regex")
MATCH_MODES = ("all", "any")
MAX_RULES = 100
MAX_SCAN_ALL = 2000  # newest messages inspected for scope="all"
_SUMMARY_CHUNK = 200


class RuleError(Exception):
    """Invalid rule definition."""


class RuleNotFound(RuleError):
    """Rule id unknown."""


@dataclass
class Condition:
    field: str
    op: str
    value: str

    def validate(self) -> None:
        if self.field not in FIELDS:
            raise RuleError(f"Unknown condition field '{self.field}' (allowed: {', '.join(FIELDS)})")
        if self.op not in OPS:
            raise RuleError(f"Unknown condition operator '{self.op}' (allowed: {', '.join(OPS)})")
        if not isinstance(self.value, str) or not self.value.strip():
            raise RuleError("Condition value must be a non-empty string")
        if self.op == "regex":
            if len(self.value) > 200:
                raise RuleError("Regex too long (max 200 characters)")
            try:
                re.compile(self.value, re.IGNORECASE)
            except re.error as err:
                raise RuleError(f"Invalid regex {self.value!r}: {err}") from err

    def matches(self, summary: dict[str, Any]) -> bool:
        haystacks = _field_values(summary, self.field)
        needle = self.value.strip().lower()
        for hay in haystacks:
            text = hay.lower()
            if self.op == "contains" and needle in text:
                return True
            if self.op == "equals" and text == needle:
                return True
            if self.op == "starts_with" and text.startswith(needle):
                return True
            if self.op == "ends_with" and text.endswith(needle):
                return True
            if self.op == "domain":
                dom = needle.lstrip("@")
                for addr in re.findall(r"[\w.+-]+@([\w.-]+)", text):
                    if addr == dom or addr.endswith("." + dom):
                        return True
            if self.op == "regex" and re.search(self.value, hay, re.IGNORECASE):
                return True
        return False


def _field_values(summary: dict[str, Any], fld: str) -> list[str]:
    def addresses(key: str) -> list[str]:
        return [f"{a.get('name', '')} <{a.get('email', '')}>" for a in summary.get(key) or []]

    if fld == "subject":
        return [summary.get("subject") or ""]
    if fld in ("from", "to", "cc"):
        return addresses(fld)
    return [summary.get("subject") or "", *addresses("from"), *addresses("to"), *addresses("cc")]


@dataclass
class Actions:
    move_to: str | None = None
    mark_seen: bool | None = None
    flag: bool | None = None
    delete: bool = False
    stop: bool = True

    def validate(self) -> None:
        if self.move_to is not None and not str(self.move_to).strip():
            raise RuleError("move_to must be a mailbox name")
        if self.delete and self.move_to:
            raise RuleError("A rule cannot both move and delete a message")
        if not any((self.move_to, self.mark_seen is not None, self.flag is not None, self.delete)):
            raise RuleError("A rule needs at least one action (move_to, mark_seen, flag or delete)")


@dataclass
class Rule:
    id: str
    name: str
    conditions: list[Condition]
    actions: Actions
    match: str = "all"
    enabled: bool = True
    mailbox: str = "INBOX"
    created: str | None = None
    hits: int = 0

    def validate(self) -> None:
        if not self.name.strip():
            raise RuleError("Rule name must not be empty")
        if self.match not in MATCH_MODES:
            raise RuleError("match must be 'all' or 'any'")
        if not self.conditions:
            raise RuleError("A rule needs at least one condition")
        for cond in self.conditions:
            cond.validate()
        self.actions.validate()

    def matches(self, summary: dict[str, Any]) -> bool:
        results = (c.matches(summary) for c in self.conditions)
        return all(results) if self.match == "all" else any(results)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        conds = [Condition(**{k: c.get(k) for k in ("field", "op", "value")}) for c in data.get("conditions", [])]
        act = data.get("actions") or {}
        actions = Actions(
            move_to=act.get("move_to"),
            mark_seen=act.get("mark_seen"),
            flag=act.get("flag"),
            delete=bool(act.get("delete", False)),
            stop=bool(act.get("stop", True)),
        )
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex[:8]),
            name=str(data.get("name", "")),
            conditions=conds,
            actions=actions,
            match=str(data.get("match", "all")),
            enabled=bool(data.get("enabled", True)),
            mailbox=str(data.get("mailbox") or "INBOX"),
            created=data.get("created"),
            hits=int(data.get("hits", 0) or 0),
        )


class RuleEngine:
    """Stores rules in HA storage and applies them to mailboxes."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        mail: ICloudMail,
        *,
        allow_delete: bool = True,
        guard: Any | None = None,
        audit: Any | None = None,
    ) -> None:
        self._hass = hass
        self._mail = mail
        self._guard = guard
        self._audit = audit
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.rules.{entry_id}")
        self._rules: list[Rule] = []
        self._last_uid: dict[str, int] = {}
        self._loaded = False
        self._lock = asyncio.Lock()
        self.allow_delete = allow_delete
        self.last_run: dict[str, Any] | None = None

    # ------------------------------------------------------------ storage
    async def async_load(self) -> None:
        if self._loaded:
            return
        data = await self._store.async_load() or {}
        self._rules = [Rule.from_dict(r) for r in data.get("rules", [])]
        self._last_uid = {k: int(v) for k, v in (data.get("last_uid") or {}).items()}
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save({"rules": [r.to_dict() for r in self._rules], "last_uid": self._last_uid})

    # -------------------------------------------------------------- CRUD
    async def async_list(self) -> list[dict[str, Any]]:
        await self.async_load()
        return [r.to_dict() for r in self._rules]

    def _get(self, rule_id: str) -> Rule:
        for rule in self._rules:
            if rule.id == rule_id:
                return rule
        raise RuleNotFound(f"Rule '{rule_id}' not found")

    async def async_create(self, data: dict[str, Any]) -> dict[str, Any]:
        await self.async_load()
        if len(self._rules) >= MAX_RULES:
            raise RuleError(f"Too many rules (max {MAX_RULES})")
        rule = Rule.from_dict({**data, "id": uuid.uuid4().hex[:8], "created": _now_iso(), "hits": 0})
        rule.validate()
        await self._check_mailboxes(rule)
        self._rules.append(rule)
        await self._save()
        return rule.to_dict()

    async def async_update(self, rule_id: str, data: dict[str, Any]) -> dict[str, Any]:
        await self.async_load()
        rule = self._get(rule_id)
        merged = rule.to_dict()
        for key in ("name", "match", "enabled", "mailbox", "conditions"):
            if key in data and data[key] is not None:
                merged[key] = data[key]
        if "actions" in data and data["actions"] is not None:
            merged["actions"] = {**merged["actions"], **{k: v for k, v in data["actions"].items() if v is not None}}
        if data.get("position") is not None:
            pos = max(0, min(int(data["position"]), len(self._rules) - 1))
        else:
            pos = self._rules.index(rule)
        updated = Rule.from_dict(merged)
        updated.validate()
        await self._check_mailboxes(updated)
        self._rules.remove(rule)
        self._rules.insert(pos, updated)
        await self._save()
        return updated.to_dict()

    async def async_delete(self, rule_id: str) -> None:
        await self.async_load()
        rule = self._get(rule_id)
        self._rules.remove(rule)
        await self._save()

    async def _check_mailboxes(self, rule: Rule) -> None:
        try:
            boxes = {b["name"] for b in await self._mail.async_mailboxes()}
        except MailError as err:
            _LOGGER.debug("Cannot verify mailboxes for rule: %s", err)
            return
        if rule.mailbox not in boxes:
            raise RuleError(f"Mailbox '{rule.mailbox}' does not exist")
        if self._guard is not None:
            try:
                self._guard.check_mailbox_writable(rule.mailbox)
                if rule.actions.move_to:
                    self._guard.check_mailbox_visible(rule.actions.move_to)
            except Exception as err:  # noqa: BLE001 - PolicyError lives in guard.py
                raise RuleError(str(err)) from err
        if rule.actions.move_to and rule.actions.move_to not in boxes:
            raise RuleError(f"Target mailbox '{rule.actions.move_to}' does not exist (see icloud_list_mailboxes)")

    # ---------------------------------------------------------------- run
    @property
    def has_enabled_rules(self) -> bool:
        return any(r.enabled for r in self._rules)

    async def async_run(
        self,
        *,
        scope: str = "new",
        dry_run: bool = False,
        mailbox: str | None = None,
        rule_ids: list[str] | None = None,
        limit: int = MAX_SCAN_ALL,
    ) -> dict[str, Any]:
        """Apply rules. scope 'new' = messages since the last run, 'all' = newest messages."""
        await self.async_load()
        if scope not in ("new", "all"):
            raise RuleError("scope must be 'new' or 'all'")
        async with self._lock:
            rules = [r for r in self._rules if r.enabled and (not rule_ids or r.id in rule_ids)]
            mailboxes = [mailbox] if mailbox else sorted({r.mailbox for r in rules}) or ["INBOX"]
            report: dict[str, Any] = {
                "scope": scope,
                "dry_run": dry_run,
                "started": _now_iso(),
                "checked": 0,
                "matched": 0,
                "actions": [],
                "skipped": [],
                "errors": [],
            }
            for box in mailboxes:
                box_rules = [r for r in rules if r.mailbox == box]
                if self._guard is not None:
                    try:
                        self._guard.check_mailbox_writable(box)
                    except Exception as err:  # noqa: BLE001
                        report["skipped"].append({"mailbox": box, "code": "protected", "reason": str(err)})
                        continue
                try:
                    await self._run_mailbox(box, box_rules, scope, dry_run, limit, report)
                except (MailError, MailboxNotFound) as err:
                    report["errors"].append({"mailbox": box, "error": str(err)})
            if not dry_run:
                await self._save()
            report["finished"] = _now_iso()
            self.last_run = {k: v for k, v in report.items() if k != "actions"} | {"actions": len(report["actions"])}
            if self._audit is not None and not dry_run and report["matched"]:
                try:
                    await self._audit.async_record(
                        tool="icloud_run_rules",
                        action="rules",
                        params={"scope": scope, "mailboxes": mailboxes},
                        result="ok" if not report["errors"] else "error",
                        client="rules",
                        error="; ".join(e.get("error", "") for e in report["errors"]) or None,
                        details={
                            "checked": report["checked"],
                            "matched": report["matched"],
                            "actions": len(report["actions"]),
                        },
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Audit logging of rule run failed: %s", err)
            return report

    async def _run_mailbox(
        self,
        box: str,
        rules: list[Rule],
        scope: str,
        dry_run: bool,
        limit: int,
        report: dict[str, Any],
    ) -> None:
        uids = await self._mail.async_search_uids(box, ["ALL"])
        if not uids:
            return
        max_uid = max(uids)
        last = self._last_uid.get(box)
        if scope == "new":
            if last is None:
                # first run: establish a baseline instead of processing the backlog
                if not dry_run:
                    self._last_uid[box] = max_uid
                report["skipped"].append(
                    {"mailbox": box, "code": "baseline", "reason": "baseline set, run again or use scope 'all'"}
                )
                return
            candidates = [u for u in uids if u > last]
        else:
            candidates = sorted(uids, reverse=True)[: max(1, min(limit, MAX_SCAN_ALL))]
        if not dry_run and scope == "new":
            self._last_uid[box] = max_uid
        if not candidates or not rules:
            report["checked"] += len(candidates)
            return

        summaries: list[dict[str, Any]] = []
        candidates.sort()
        for i in range(0, len(candidates), _SUMMARY_CHUNK):
            summaries.extend(await self._mail.async_summaries(box, candidates[i : i + _SUMMARY_CHUNK]))
        report["checked"] += len(summaries)

        # decide per message
        plan: dict[int, dict[str, Any]] = {}
        for summary in summaries:
            uid = summary["uid"]
            decision: dict[str, Any] = {"rules": [], "seen": None, "flag": None, "move_to": None, "delete": False}
            for rule in rules:
                if not rule.matches(summary):
                    continue
                decision["rules"].append(rule)
                act = rule.actions
                if act.mark_seen is not None:
                    decision["seen"] = act.mark_seen
                if act.flag is not None:
                    decision["flag"] = act.flag
                if act.delete:
                    if self.allow_delete:
                        decision["delete"] = True
                    else:
                        report["skipped"].append(
                            {
                                "uid": uid,
                                "rule": rule.name,
                                "code": "delete_disabled",
                                "reason": "deleting is disabled in the options",
                            }
                        )
                if act.move_to and not decision["move_to"] and not decision["delete"]:
                    decision["move_to"] = act.move_to
                if act.stop or act.move_to or act.delete:
                    break
            if decision["rules"]:
                plan[uid] = decision
                report["matched"] += 1
                for rule in decision["rules"]:
                    report["actions"].append(
                        {
                            "uid": uid,
                            "mailbox": box,
                            "rule": rule.name,
                            "rule_id": rule.id,
                            "subject": summary.get("subject"),
                            "from": [a.get("email") for a in summary.get("from") or []],
                            "move_to": decision["move_to"],
                            "delete": decision["delete"],
                            "mark_seen": decision["seen"],
                            "flag": decision["flag"],
                        }
                    )
                    if not dry_run:
                        rule.hits += 1
        if dry_run or not plan:
            return

        # execute in batches: flags first (while the messages are still here), then moves/deletes
        for seen in (True, False):
            group = [u for u, d in plan.items() if d["seen"] is seen]
            if group:
                await self._safe(report, self._mail.async_set_flags(box, group, seen=seen))
        for flag in (True, False):
            group = [u for u, d in plan.items() if d["flag"] is flag]
            if group:
                await self._safe(report, self._mail.async_set_flags(box, group, flagged=flag))
        deletes = [u for u, d in plan.items() if d["delete"]]
        if deletes:
            await self._safe(report, self._mail.async_delete(box, deletes))
        targets: dict[str, list[int]] = {}
        for uid, d in plan.items():
            if d["move_to"] and not d["delete"]:
                targets.setdefault(d["move_to"], []).append(uid)
        for target, group in targets.items():
            await self._safe(report, self._mail.async_move(box, group, target))

    @staticmethod
    async def _safe(report: dict[str, Any], coro: Any) -> None:
        try:
            await coro
        except (MailError, MailboxNotFound) as err:
            report["errors"].append({"error": str(err)})


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
