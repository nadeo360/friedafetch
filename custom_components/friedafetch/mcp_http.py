"""Own Model Context Protocol endpoint (Streamable HTTP) for the iCloud tools.

The Home Assistant core integration ``mcp_server`` only serves LLM APIs that
have been selected in its config entry, and third-party MCP servers such as
``mcp_server_http_transport`` do not pass LLM APIs through at all. This module
therefore registers a dedicated endpoint that serves the tools from
:func:`llm_api.build_tools` directly:

- ``POST /api/friedafetch``: Streamable HTTP endpoint (stateless). Every request
  carries exactly one JSON-RPC message; the response is returned as JSON.
  Authentication is the normal Home Assistant bearer token (a long-lived
  access token works for MCP clients).

The endpoint speaks the small stateless part of the protocol itself (JSON-RPC:
``initialize``, ``ping``, ``tools/list``, ``tools/call``) and does not import the
``mcp`` SDK: Home Assistant pins that package for its own integrations, so its
major versions arrive with a Home Assistant update and must not take this
integration down (mcp 2.0 did, with Home Assistant 2026.11).

Routes cannot be removed from the aiohttp router once registered, so the view
is registered once per Home Assistant instance. It looks up the loaded config
entries on every request: unloading an entry removes its tools, and with no
entry loaded the endpoint answers 404.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound, HTTPRequestEntityTooLarge
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util import dt as dt_util

from .accounts import account_label
from .const import CONF_APPLE_ID, CONF_ENDPOINT_ADMIN_ONLY, DEFAULT_ENDPOINT_ADMIN_ONLY, DOMAIN
from .llm_api import API_PROMPT, ICloudClients, build_tools, capability_hints
from .schema import vol
from .usage import async_get_usage

_LOGGER = logging.getLogger(__name__)

STREAMABLE_API = f"/api/{DOMAIN}"
READONLY_API = f"{STREAMABLE_API}/readonly"
MAX_BODY_BYTES = 1024 * 1024  # 1 MiB is plenty for JSON-RPC tool calls
PROFILES = ("full", "readonly")
SERVER_NAME = "frieda"
TIMEOUT = 120  # seconds; IMAP searches can be slow

DATA_MCP_HTTP = f"{DOMAIN}_mcp_http"

# The revisions of the ``initialize`` handshake, oldest first. Clients of the 2026-07-28 revision start with
# ``server/discover``; they get METHOD_NOT_FOUND like any unknown method and fall back to this handshake.
PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


@dataclass(slots=True)
class MCPHttpData:
    """Per-instance state kept in ``hass.data``."""

    version: str
    registered: bool = False


@dataclass(slots=True)
class ServedTool:
    """A tool as it is exposed on the endpoint (name may be namespaced per account)."""

    name: str
    tool: llm.Tool
    entry: ConfigEntry

    @property
    def description(self) -> str:
        base = self.tool.description or ""
        if self.name != self.tool.name:
            return f"{base} (iCloud account: {self.entry.data.get(CONF_APPLE_ID)})".strip()
        return base


# --------------------------------------------------------------------------- tools


def _loaded_entries(hass: HomeAssistant) -> list[ConfigEntry]:
    """Return the loaded config entries that have clients attached, oldest first."""
    entries = [e for e in hass.config_entries.async_loaded_entries(DOMAIN) if isinstance(e.runtime_data, ICloudClients)]
    entries.sort(key=lambda e: e.created_at)
    return entries


def _tool_suffix(entry: ConfigEntry) -> str:
    return f"_{account_label(entry)}"


def _is_read_only(tool: Any) -> bool:
    ann = getattr(tool, "annotations", None)
    if ann is not None:
        return bool(getattr(ann, "read_only", False))
    return not getattr(tool, "writes", False)


@callback
def async_served_tools(hass: HomeAssistant, profile: str = "full") -> list[ServedTool]:
    """Collect the tools of all loaded entries.

    With one account the tools keep their plain names. With several accounts
    the oldest entry keeps the plain names and every further entry gets a
    suffix derived from its account label (options) or Apple ID so that names stay unique.
    """
    served: list[ServedTool] = []
    for index, entry in enumerate(_loaded_entries(hass)):
        suffix = "" if index == 0 else _tool_suffix(entry)
        for tool in build_tools(entry.runtime_data):
            if profile == "readonly" and not _is_read_only(tool):
                continue
            served.append(ServedTool(name=f"{tool.name}{suffix}", tool=tool, entry=entry))
    return served


def _admin_only(hass: HomeAssistant) -> bool:
    """The endpoint requires admin tokens as soon as one account demands it."""
    return any(e.options.get(CONF_ENDPOINT_ADMIN_ONLY, DEFAULT_ENDPOINT_ADMIN_ONLY) for e in _loaded_entries(hass))


def _format_tool(served: ServedTool) -> dict[str, Any]:
    """Convert a Home Assistant LLM tool into an MCP tool description."""
    tool = served.tool
    input_schema = vol.to_openapi(tool.parameters, openapi_version="3.1.0")
    mcp_schema: dict[str, Any] = {"type": "object", "properties": input_schema.get("properties", {})}
    if required := input_schema.get("required"):
        mcp_schema["required"] = required

    described: dict[str, Any] = {"name": served.name, "description": served.description, "inputSchema": mcp_schema}
    if title := getattr(tool, "title", None):
        described["title"] = title
    if (ann := getattr(tool, "annotations", None)) is not None:
        hints = {
            "readOnlyHint": ann.read_only,
            "destructiveHint": ann.destructive,
            "idempotentHint": ann.idempotent,
            "openWorldHint": ann.open_world,
        }
        described["annotations"] = {k: v for k, v in hints.items() if v is not None}
    return described


def _text_result(data: Any, *, is_error: bool) -> dict[str, Any]:
    text = json.dumps(data, ensure_ascii=False, default=str)
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _error_result(message: str, code: str = "failed") -> dict[str, Any]:
    return _text_result({"error": message, "code": code}, is_error=True)


async def async_call_served_tool(
    hass: HomeAssistant, served: ServedTool, arguments: dict[str, Any], context: Context
) -> dict[str, Any]:
    """Validate the arguments and run a tool, mapping the result to MCP."""
    tool = served.tool
    try:
        args = tool.parameters(arguments)
    except vol.Invalid as err:
        return _error_result(f"Invalid arguments: {err}", "invalid_arguments")

    llm_context = llm.LLMContext(platform=DOMAIN, context=context, language="*", assistant=None, device_id=None)
    tool_input = llm.ToolInput(tool_name=tool.name, tool_args=args)
    try:
        result = await tool.async_call(hass, tool_input, llm_context)
    except vol.Invalid as err:
        return _error_result(f"Invalid arguments: {err}", "invalid_arguments")
    except HomeAssistantError as err:
        return _error_result(str(err))
    except Exception as err:  # noqa: BLE001 - a failing tool is an answer to the client, not a broken endpoint
        _LOGGER.exception("Tool %s failed", served.name)
        return _error_result(str(err))

    if isinstance(result, llm.ToolResult):
        return _text_result(result.data, is_error=bool(result.error))
    # legacy: plain JSON object
    return _text_result(result, is_error=False)


# --------------------------------------------------------------------------- server


def _instructions(hass: HomeAssistant, profile: str = "full") -> str:
    now = dt_util.now()
    accounts = ", ".join(e.data.get(CONF_APPLE_ID, "") for e in _loaded_entries(hass)) or "(default)"
    prompt = API_PROMPT.format(
        tz=now.tzname() or str(now.tzinfo), now=now.isoformat(timespec="minutes"), account=accounts
    )
    if profile == "readonly":
        return prompt + " This endpoint is read-only: no tool here can change anything."
    entries = _loaded_entries(hass)
    for entry in entries:
        hints = capability_hints(entry.runtime_data.options, account_label(entry) if len(entries) > 1 else "")
        if hints:
            prompt += " " + hints
    return prompt


async def _call_tool(
    hass: HomeAssistant, params: dict[str, Any], context: Context, profile: str
) -> dict[str, Any] | None:
    """The result of ``tools/call``; None when the parameters are not a tool call."""
    name, arguments = params.get("name"), params.get("arguments") or {}
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return None
    _LOGGER.debug("MCP tool call: %s(%s)", name, arguments)
    served = next((s for s in async_served_tools(hass, profile) if s.name == name), None)
    if served is None:
        return _error_result(f"Unknown tool: {name}", "unknown_tool")
    try:
        async with asyncio.timeout(TIMEOUT):
            return await async_call_served_tool(hass, served, arguments, context)
    except TimeoutError:
        return _error_result(f"No answer within {TIMEOUT} seconds", "timeout")


# --------------------------------------------------------------------------- transport


async def _note_client(hass: HomeAssistant, params: dict[str, Any], profile: str) -> None:
    """Remember which MCP client connected (name and version from ``initialize``)."""
    info = params.get("clientInfo") if isinstance(params, dict) else None
    if not isinstance(info, dict):
        return
    try:
        stats = await async_get_usage(hass)
        await stats.async_note_client(
            str(info.get("name") or ""), info.get("version") and str(info["version"]), profile
        )
    except Exception as err:  # noqa: BLE001 - bookkeeping must never break the endpoint
        _LOGGER.debug("Could not record MCP client: %s", err)


def _is_request_id(value: Any) -> bool:
    return isinstance(value, str | int) and not isinstance(value, bool)


def _kind_of(message: Any) -> str | None:
    """Tell "request", "notification" and "response" apart; None for anything that is no JSON-RPC 2.0 message."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return None
    if isinstance(message.get("method"), str):
        if not isinstance(message.get("params") or {}, dict):
            return None
        if "id" not in message:
            return "notification"
        return "request" if _is_request_id(message["id"]) else None
    return "response" if _is_request_id(message.get("id")) and ("result" in message or "error" in message) else None


def _jsonrpc_result(request_id: Any, result: dict[str, Any]) -> web.Response:
    return web.json_response({"jsonrpc": "2.0", "id": request_id, "result": result})


def _jsonrpc_error(request_id: Any, code: int, message: str, data: Any = None) -> web.Response:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return web.json_response({"jsonrpc": "2.0", "id": request_id, "error": error})


def _initialize_result(hass: HomeAssistant, params: dict[str, Any], version: str, profile: str) -> dict[str, Any]:
    requested = params.get("protocolVersion")
    return {
        # the client's revision when it is known, else the newest one: the client then decides whether it can go on
        "protocolVersion": requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[-1],
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": SERVER_NAME, "version": version},
        "instructions": _instructions(hass, profile),
    }


async def async_handle_streamable_message(
    request: web.Request, context: Context, profile: str = "full"
) -> web.StreamResponse:
    """Process one JSON-RPC message."""
    hass: HomeAssistant = request.app[KEY_HASS]
    data: MCPHttpData | None = hass.data.get(DATA_MCP_HTTP)
    if data is None or not _loaded_entries(hass):
        raise HTTPNotFound(text="Frieda is not configured")
    if _admin_only(hass):
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            raise HTTPForbidden(text="This MCP endpoint is restricted to administrator tokens")
    if (request.content_length or 0) > MAX_BODY_BYTES:
        raise HTTPRequestEntityTooLarge(max_size=MAX_BODY_BYTES, actual_size=request.content_length or 0)

    if CONTENT_TYPE_JSON not in request.headers.get("accept", ""):
        raise HTTPBadRequest(text=f"Client must accept {CONTENT_TYPE_JSON}")
    if request.content_type != CONTENT_TYPE_JSON:
        raise HTTPBadRequest(text=f"Content-Type must be {CONTENT_TYPE_JSON}")
    try:
        message = await request.json()
    except ValueError as err:
        _LOGGER.debug("Failed to parse message as JSON-RPC message: %s", err)
        raise HTTPBadRequest(text="Request must be a JSON-RPC message") from err
    kind = _kind_of(message)
    if kind is None:
        raise HTTPBadRequest(text="Request must be a JSON-RPC message")

    _LOGGER.debug("Received MCP client message: %s", message)

    # Notifications and responses are acknowledged only
    if kind != "request":
        return web.Response(status=HTTPStatus.ACCEPTED)

    request_id, method, params = message["id"], message["method"], message.get("params") or {}
    if method == "initialize":
        await _note_client(hass, params, profile)
        return _jsonrpc_result(request_id, _initialize_result(hass, params, data.version, profile))
    if method == "ping":
        return _jsonrpc_result(request_id, {})
    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": [_format_tool(s) for s in async_served_tools(hass, profile)]})
    if method == "tools/call":
        result = await _call_tool(hass, params, context, profile)
        if result is None:
            return _jsonrpc_error(request_id, INVALID_PARAMS, "Invalid params")
        return _jsonrpc_result(request_id, result)
    return _jsonrpc_error(request_id, METHOD_NOT_FOUND, "Method not found", method)


class ICloudMCPStreamableView(HomeAssistantView):
    """Streamable HTTP endpoint serving the iCloud tools (full profile)."""

    name = f"{DOMAIN}:streamable"
    url = STREAMABLE_API
    requires_auth = True
    profile = "full"

    async def post(self, request: web.Request) -> web.StreamResponse:
        """Handle a JSON-RPC message."""
        return await async_handle_streamable_message(request, self.context(request), self.profile)

    async def get(self, request: web.Request) -> web.StreamResponse:
        """Server-initiated streams are not supported (stateless server)."""
        return web.Response(status=HTTPStatus.METHOD_NOT_ALLOWED, text="GET is not supported; POST JSON-RPC messages")

    async def delete(self, request: web.Request) -> web.StreamResponse:
        """Sessions are stateless, there is nothing to terminate."""
        return web.Response(status=HTTPStatus.METHOD_NOT_ALLOWED, text="Sessions are stateless")


# --------------------------------------------------------------------------- registration


class ICloudMCPReadOnlyView(ICloudMCPStreamableView):
    """Read-only profile: only tools that cannot change anything."""

    name = f"{DOMAIN}:streamable_readonly"
    url = READONLY_API
    profile = "readonly"


@callback
def async_register(hass: HomeAssistant, version: str) -> None:
    """Register the endpoint once per Home Assistant instance."""
    data: MCPHttpData | None = hass.data.get(DATA_MCP_HTTP)
    if data is None:
        data = hass.data[DATA_MCP_HTTP] = MCPHttpData(version=version)
    if not data.registered:
        hass.http.register_view(ICloudMCPStreamableView())
        hass.http.register_view(ICloudMCPReadOnlyView())
        data.registered = True
        _LOGGER.info("Frieda endpoints registered at %s and %s", STREAMABLE_API, READONLY_API)
