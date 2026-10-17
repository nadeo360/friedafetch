"""Human-in-the-loop approvals for critical tool calls.

A gated tool call is parked as a pending request, announced as a persistent
notification (and optionally as an actionable mobile notification) and only
executed once an admin approves it in the panel or on the phone.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later

from .audit import sanitize_params
from .const import APPROVAL_ACTION_PREFIX, DOMAIN

if TYPE_CHECKING:
    from .audit import AuditLog

_LOGGER = logging.getLogger(__name__)
_KEEP_DECIDED = 50


class ApprovalError(Exception):
    """Unknown or already decided request."""


@dataclass
class ApprovalRequest:
    """One parked tool call."""

    id: str
    tool: str
    action: str
    reason: str
    summary: str
    params: dict[str, Any]
    created: str
    expires: str
    status: str = "pending"  # pending | executed | failed | denied | expired
    client: str | None = None
    user_id: str | None = None
    decided_by: str | None = None
    decided_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    _runner: Any = field(default=None, repr=False, compare=False)
    _cancel_expiry: Any = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class ApprovalManager:
    """Keeps pending requests of one account and executes them on approval."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        account: str,
        *,
        audit: AuditLog | None,
        notify_service: str | None,
        timeout_minutes: int,
        language: str = "en",
    ) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._account = account
        self._audit = audit
        self._notify = (notify_service or "").strip().removeprefix("notify.") or None
        self._timeout = max(1, int(timeout_minutes))
        self._lang = "de" if (language or "").lower().startswith("de") else "en"
        self._requests: dict[str, ApprovalRequest] = {}

    # ----------------------------------------------------------- texts
    def _t(self, key: str, **kw: Any) -> str:
        texts = {
            "de": {
                "title": "Frieda: Freigabe erforderlich",
                "body": "{client} möchte „{tool}“ ausführen ({reason}):\n{summary}\n\nKonto: {account}. Gültig bis {expires}.",
                "approve": "Freigeben",
                "deny": "Ablehnen",
                "reason_send": "E-Mail senden",
                "reason_delete": "Löschen",
                "reason_mass": "Massenaktion",
            },
            "en": {
                "title": "Frieda: approval required",
                "body": "{client} wants to run “{tool}” ({reason}):\n{summary}\n\nAccount: {account}. Valid until {expires}.",
                "approve": "Approve",
                "deny": "Deny",
                "reason_send": "send e-mail",
                "reason_delete": "delete",
                "reason_mass": "mass action",
            },
        }
        return texts[self._lang][key].format(**kw)

    # --------------------------------------------------------- requests
    async def async_request(
        self,
        *,
        tool_name: str,
        action: str,
        reason: str,
        summary: str,
        params: dict[str, Any],
        runner: Any,
        client: str | None,
        user_id: str | None,
    ) -> dict[str, Any]:
        """Park a call and announce it. Returns the tool result for the caller."""
        now = datetime.now(UTC)
        expires = now + timedelta(minutes=self._timeout)
        req = ApprovalRequest(
            id=secrets.token_hex(4),
            tool=tool_name,
            action=action,
            reason=reason,
            summary=summary,
            params=sanitize_params(params),
            created=now.isoformat(timespec="seconds"),
            expires=expires.isoformat(timespec="seconds"),
            client=client,
            user_id=user_id,
        )
        req._runner = runner  # noqa: SLF001
        self._requests[req.id] = req
        self._trim()
        req._cancel_expiry = async_call_later(  # noqa: SLF001
            self._hass, self._timeout * 60, lambda _now, rid=req.id: self._hass.async_create_task(self._expire(rid))
        )
        await self._announce(req)
        if self._audit is not None:
            await self._audit.async_record(
                tool=tool_name,
                action=action,
                params=params,
                result="pending",
                client=client,
                user_id=user_id,
                details={"approval_id": req.id, "reason": reason},
            )
        return {
            "code": "approval_required",
            "request_id": req.id,
            "expires": req.expires,
            "reason": reason,
            "message": (
                "This action requires approval by the Home Assistant admin (notification or the 'Frieda' "
                "panel). It will be executed automatically once approved; check the outcome with "
                f"icloud_approval_status(request_id='{req.id}'). Do not retry the call."
            ),
        }

    async def _announce(self, req: ApprovalRequest) -> None:
        reason = self._t(f"reason_{req.reason}") if req.reason in ("send", "delete", "mass") else req.reason
        expires_local = datetime.fromisoformat(req.expires).astimezone().strftime("%H:%M")
        body = self._t(
            "body",
            client=req.client or "MCP client",
            tool=req.tool,
            reason=reason,
            summary=req.summary,
            account=self._account,
            expires=expires_local,
        )
        persistent_notification.async_create(
            self._hass,
            body + "\n\n→ /friedafetch",
            title=self._t("title"),
            notification_id=f"{DOMAIN}_approval_{req.id}",
        )
        if self._notify and self._hass.services.has_service("notify", self._notify):
            try:
                await self._hass.services.async_call(
                    "notify",
                    self._notify,
                    {
                        "title": self._t("title"),
                        "message": body,
                        "data": {
                            "tag": f"{DOMAIN}_approval_{req.id}",
                            "actions": [
                                {"action": f"{APPROVAL_ACTION_PREFIX}APPROVE_{req.id}", "title": self._t("approve")},
                                {
                                    "action": f"{APPROVAL_ACTION_PREFIX}DENY_{req.id}",
                                    "title": self._t("deny"),
                                    "destructive": True,
                                },
                            ],
                        },
                    },
                    blocking=False,
                )
            except Exception as err:  # noqa: BLE001 - the persistent notification remains
                _LOGGER.warning("Could not send approval notification via notify.%s: %s", self._notify, err)

    def _dismiss(self, req: ApprovalRequest) -> None:
        persistent_notification.async_dismiss(self._hass, f"{DOMAIN}_approval_{req.id}")
        if self._notify and self._hass.services.has_service("notify", self._notify):
            self._hass.async_create_task(
                self._hass.services.async_call(
                    "notify",
                    self._notify,
                    {"message": "clear_notification", "data": {"tag": f"{DOMAIN}_approval_{req.id}"}},
                    blocking=False,
                )
            )

    def _trim(self) -> None:
        decided = [r for r in self._requests.values() if r.status != "pending"]
        for old in decided[: max(0, len(decided) - _KEEP_DECIDED)]:
            self._requests.pop(old.id, None)

    def _get_pending(self, request_id: str) -> ApprovalRequest:
        req = self._requests.get(request_id)
        if req is None:
            raise ApprovalError(f"Approval request '{request_id}' not found")
        if req.status != "pending":
            raise ApprovalError(f"Approval request '{request_id}' is already {req.status}")
        return req

    def _finish(self, req: ApprovalRequest, status: str, decided_by: str | None) -> None:
        req.status = status
        req.decided_by = decided_by
        req.decided_at = datetime.now(UTC).isoformat(timespec="seconds")
        if req._cancel_expiry:  # noqa: SLF001
            req._cancel_expiry()  # noqa: SLF001
            req._cancel_expiry = None  # noqa: SLF001
        req._runner = None  # noqa: SLF001
        self._dismiss(req)

    async def async_approve(self, request_id: str, decided_by: str | None) -> ApprovalRequest:
        req = self._get_pending(request_id)
        runner = req._runner  # noqa: SLF001
        try:
            result = await runner()
            req.result = result if isinstance(result, dict) else {"result": result}
            self._finish(req, "executed", decided_by)
            audit_result, error = "ok", None
        except Exception as err:  # noqa: BLE001 - report instead of crash
            req.error = str(err)
            self._finish(req, "failed", decided_by)
            audit_result, error = "error", str(err)
        if self._audit is not None:
            await self._audit.async_record(
                tool=req.tool,
                action=req.action,
                params=req.params,
                result=audit_result,
                client=f"approved:{decided_by or 'unknown'}",
                user_id=req.user_id,
                error=error,
                details={
                    "approval_id": req.id,
                    **(
                        {
                            k: v
                            for k, v in (req.result or {}).items()
                            if k in ("count", "deleted", "message_id", "uid", "uids")
                        }
                    ),
                },
            )
        return req

    async def async_deny(self, request_id: str, decided_by: str | None) -> ApprovalRequest:
        req = self._get_pending(request_id)
        self._finish(req, "denied", decided_by)
        if self._audit is not None:
            await self._audit.async_record(
                tool=req.tool,
                action=req.action,
                params=req.params,
                result="blocked",
                client=f"denied:{decided_by or 'unknown'}",
                user_id=req.user_id,
                error="denied by the user",
                details={"approval_id": req.id},
            )
        return req

    async def _expire(self, request_id: str) -> None:
        req = self._requests.get(request_id)
        if req is None or req.status != "pending":
            return
        self._finish(req, "expired", None)
        if self._audit is not None:
            await self._audit.async_record(
                tool=req.tool,
                action=req.action,
                params=req.params,
                result="blocked",
                client="expired",
                user_id=req.user_id,
                error="approval request expired",
                details={"approval_id": req.id},
            )

    def status(self, request_id: str) -> dict[str, Any]:
        req = self._requests.get(request_id)
        if req is None:
            raise ApprovalError(f"Approval request '{request_id}' not found")
        return req.to_dict()

    def list(self) -> list[dict[str, Any]]:
        items = sorted(self._requests.values(), key=lambda r: r.created, reverse=True)
        return [r.to_dict() for r in items]

    @property
    def pending_count(self) -> int:
        return sum(1 for r in self._requests.values() if r.status == "pending")

    # ----------------------------------------------- mobile notifications
    @callback
    def handle_mobile_action(self, event: Event) -> None:
        """React to an actionable notification button (approve/deny)."""
        action = str(event.data.get("action") or "")
        if not action.startswith(APPROVAL_ACTION_PREFIX):
            return
        verb, _, request_id = action.removeprefix(APPROVAL_ACTION_PREFIX).partition("_")
        if request_id not in self._requests:
            return
        decided_by = f"mobile:{event.context.user_id or 'unknown'}"
        if verb == "APPROVE":
            self._hass.async_create_task(self._safe(self.async_approve(request_id, decided_by)))
        elif verb == "DENY":
            self._hass.async_create_task(self._safe(self.async_deny(request_id, decided_by)))

    async def _safe(self, coro: Any) -> None:
        try:
            await coro
        except ApprovalError as err:
            _LOGGER.debug("Mobile approval action ignored: %s", err)

    def shutdown(self) -> None:
        for req in self._requests.values():
            if req._cancel_expiry:  # noqa: SLF001
                req._cancel_expiry()  # noqa: SLF001
