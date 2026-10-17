"""Sidebar panel and WebSocket API: accounts, activity log and approvals."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .accounts import account_label
from .approvals import ApprovalError
from .const import (
    CONF_ALLOW_DELETE,
    CONF_ALLOW_SEND_MAIL,
    CONF_APPLE_ID,
    CONF_ENABLE_MAIL,
    CONF_READ_ONLY,
    DEFAULT_ALLOW_DELETE,
    DEFAULT_ALLOW_SEND_MAIL,
    DEFAULT_ENABLE_MAIL,
    DEFAULT_READ_ONLY,
    DOMAIN,
)
from .mail import MailError
from .schema import vol

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "friedafetch"
STATIC_URL = f"/{DOMAIN}_static"
WEBCOMPONENT = "friedafetch-panel"
DATA_FRONTEND: HassKey[bool] = HassKey(f"{DOMAIN}_frontend")


async def async_setup_frontend(hass: HomeAssistant, version: str) -> None:
    """Register static files, the sidebar panel and the websocket commands (once)."""
    if hass.data.get(DATA_FRONTEND):
        return
    hass.data[DATA_FRONTEND] = True
    static_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(static_dir), cache_headers=False)])
    for command in (
        ws_accounts,
        ws_mailboxes,
        ws_audit_list,
        ws_audit_clear,
        ws_approvals_list,
        ws_approvals_decide,
    ):
        websocket_api.async_register_command(hass, command)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=WEBCOMPONENT,
        sidebar_title="Frieda" if (hass.config.language or "en").lower().startswith("de") else "Frieda",
        sidebar_icon="mdi:shield-check-outline",
        module_url=f"{STATIC_URL}/panel.js?v={version}",
        embed_iframe=False,
        require_admin=True,
    )
    _LOGGER.debug("Frieda panel registered at /%s", PANEL_URL_PATH)


@callback
def async_remove_frontend(hass: HomeAssistant) -> None:
    """Remove the panel when the last config entry is unloaded."""
    if not hass.data.get(DATA_FRONTEND):
        return
    hass.data[DATA_FRONTEND] = False
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)


# ------------------------------------------------------------------ helpers
def _loaded_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    return [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.state is ConfigEntryState.LOADED and getattr(e, "runtime_data", None) is not None
    ]


class FriedaWsError(Exception):
    """Websocket request cannot be served."""


def _account(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry:
    entries = _loaded_entries(hass)
    if not entries:
        raise FriedaWsError("No iCloud account is set up")
    return next((e for e in entries if e.entry_id == entry_id), entries[0]) if entry_id else entries[0]


def _ws_errors(func):
    """Translate engine errors into websocket errors."""

    async def wrapper(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
        try:
            await func(hass, connection, msg)
        except ApprovalError as err:
            connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, str(err))
        except (FriedaWsError, MailError, ValueError) as err:
            connection.send_error(msg["id"], "frieda_error", str(err))

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ----------------------------------------------------------------- commands
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/accounts"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_accounts(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """List configured iCloud accounts with their security state."""
    accounts: list[dict[str, Any]] = []
    for entry in _loaded_entries(hass):
        clients = entry.runtime_data
        opts = entry.options
        accounts.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "apple_id": entry.data.get(CONF_APPLE_ID),
                "label": account_label(entry),
                "mail_enabled": bool(opts.get(CONF_ENABLE_MAIL, DEFAULT_ENABLE_MAIL)),
                "read_only": bool(opts.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)),
                "allow_delete": bool(opts.get(CONF_ALLOW_DELETE, DEFAULT_ALLOW_DELETE)),
                "allow_send": bool(opts.get(CONF_ALLOW_SEND_MAIL, DEFAULT_ALLOW_SEND_MAIL)),
                "approvals_enabled": clients.approvals is not None,
                "approvals_pending": clients.approvals.pending_count if clients.approvals else 0,
                "extensions": sorted(clients.extensions),
            }
        )
    connection.send_result(msg["id"], {"accounts": accounts})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/mailboxes", vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_mailboxes(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """List mailbox names of an account."""
    entry = _account(hass, msg.get("entry_id"))
    boxes = await entry.runtime_data.mail.async_mailboxes()
    connection.send_result(msg["id"], {"mailboxes": [b["name"] for b in boxes]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/audit/list",
        vol.Optional("entry_id"): str,
        vol.Optional("limit"): int,
        vol.Optional("result"): vol.In(["ok", "error", "blocked"]),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_audit_list(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Return the latest audit entries of an account plus the quota status."""
    entry = _account(hass, msg.get("entry_id"))
    clients = entry.runtime_data
    audit = clients.audit
    if audit is None:
        connection.send_result(msg["id"], {"entries": [], "quota": {}})
        return
    await audit.async_load()
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "entries": audit.entries(limit=max(1, min(int(msg.get("limit") or 100), 500)), result=msg.get("result")),
            "quota": clients.guard.quota_status(),
        },
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/audit/clear", vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_audit_clear(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Clear the audit log of an account."""
    entry = _account(hass, msg.get("entry_id"))
    if entry.runtime_data.audit is not None:
        await entry.runtime_data.audit.async_clear()
    connection.send_result(msg["id"], {"cleared": True})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/approvals/list", vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_approvals_list(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """List pending and recently decided approval requests."""
    entry = _account(hass, msg.get("entry_id"))
    approvals = entry.runtime_data.approvals
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "enabled": approvals is not None,
            "requests": approvals.list() if approvals else [],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/approvals/decide",
        vol.Optional("entry_id"): str,
        vol.Required("request_id"): str,
        vol.Required("decision"): vol.In(["approve", "deny"]),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_approvals_decide(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Approve or deny a parked action."""
    entry = _account(hass, msg.get("entry_id"))
    approvals = entry.runtime_data.approvals
    if approvals is None:
        raise FriedaWsError("Approvals are not enabled for this account")
    decided_by = connection.user.name or connection.user.id
    if msg["decision"] == "approve":
        req = await approvals.async_approve(msg["request_id"], decided_by)
    else:
        req = await approvals.async_deny(msg["request_id"], decided_by)
    connection.send_result(msg["id"], {"request": req.to_dict()})
