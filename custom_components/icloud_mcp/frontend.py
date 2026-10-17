"""Sidebar panel and WebSocket API for managing inbox rules."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import CONF_APPLE_ID, DOMAIN
from .mail import MailError
from .rules import RuleEngine, RuleError, RuleNotFound
from .schema import vol

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "icloud-mcp"
STATIC_URL = f"/{DOMAIN}_static"
WEBCOMPONENT = "icloud-mcp-rules-panel"
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
        ws_rules_list,
        ws_rules_create,
        ws_rules_update,
        ws_rules_delete,
        ws_rules_run,
    ):
        websocket_api.async_register_command(hass, command)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=WEBCOMPONENT,
        sidebar_title="iCloud Regeln" if (hass.config.language or "en").lower().startswith("de") else "iCloud Rules",
        sidebar_icon="mdi:email-fast-outline",
        module_url=f"{STATIC_URL}/panel.js?v={version}",
        embed_iframe=False,
        require_admin=True,
    )
    _LOGGER.debug("iCloud MCP panel registered at /%s", PANEL_URL_PATH)


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


def _engine(hass: HomeAssistant, entry_id: str | None) -> tuple[ConfigEntry, RuleEngine]:
    entries = _loaded_entries(hass)
    if not entries:
        raise RuleError("No iCloud account is set up")
    entry = next((e for e in entries if e.entry_id == entry_id), entries[0]) if entry_id else entries[0]
    rules = entry.runtime_data.rules
    if rules is None:
        raise RuleError("Rules are not available for this account")
    return entry, rules


def _ws_errors(func):
    """Translate engine errors into websocket errors."""

    async def wrapper(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
        try:
            await func(hass, connection, msg)
        except RuleNotFound as err:
            connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, str(err))
        except (RuleError, MailError, ValueError) as err:
            connection.send_error(msg["id"], "rule_error", str(err))

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ----------------------------------------------------------------- commands
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/accounts"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_accounts(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """List configured iCloud accounts."""
    connection.send_result(
        msg["id"],
        {
            "accounts": [
                {"entry_id": e.entry_id, "title": e.title, "apple_id": e.data.get(CONF_APPLE_ID)}
                for e in _loaded_entries(hass)
            ]
        },
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/mailboxes", vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_mailboxes(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """List mailbox names of an account."""
    entry, _ = _engine(hass, msg.get("entry_id"))
    boxes = await entry.runtime_data.mail.async_mailboxes()
    connection.send_result(msg["id"], {"mailboxes": [b["name"] for b in boxes]})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/rules/list", vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_rules_list(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """List rules."""
    entry, rules = _engine(hass, msg.get("entry_id"))
    connection.send_result(
        msg["id"],
        {"entry_id": entry.entry_id, "rules": await rules.async_list(), "last_run": rules.last_run},
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/rules/create", vol.Optional("entry_id"): str, vol.Required("rule"): dict}
)
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_rules_create(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Create a rule."""
    _, rules = _engine(hass, msg.get("entry_id"))
    connection.send_result(msg["id"], {"rule": await rules.async_create(msg["rule"])})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/rules/update",
        vol.Optional("entry_id"): str,
        vol.Required("rule_id"): str,
        vol.Required("changes"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_rules_update(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Update a rule."""
    _, rules = _engine(hass, msg.get("entry_id"))
    connection.send_result(msg["id"], {"rule": await rules.async_update(msg["rule_id"], msg["changes"])})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/rules/delete", vol.Optional("entry_id"): str, vol.Required("rule_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_rules_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Delete a rule."""
    _, rules = _engine(hass, msg.get("entry_id"))
    await rules.async_delete(msg["rule_id"])
    connection.send_result(msg["id"], {"deleted": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/rules/run",
        vol.Optional("entry_id"): str,
        vol.Optional("scope"): vol.In(["new", "all"]),
        vol.Optional("dry_run"): bool,
        vol.Optional("mailbox"): str,
        vol.Optional("rule_ids"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_ws_errors
async def ws_rules_run(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Run rules now."""
    _, rules = _engine(hass, msg.get("entry_id"))
    report = await rules.async_run(
        scope=msg.get("scope") or "all",
        dry_run=bool(msg.get("dry_run")),
        mailbox=msg.get("mailbox"),
        rule_ids=msg.get("rule_ids"),
    )
    connection.send_result(msg["id"], report)
