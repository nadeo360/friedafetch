"""Own Model Context Protocol endpoint (Streamable HTTP) for the iCloud tools.

The Home Assistant core integration ``mcp_server`` only serves LLM APIs that
have been selected in its config entry, and third-party MCP servers such as
``mcp_server_http_transport`` do not pass LLM APIs through at all. This module
therefore registers a dedicated endpoint that serves the tools from
:func:`llm_api.build_tools` directly:

- ``POST /api/icloud_mcp``: Streamable HTTP endpoint (stateless). Every request
  carries exactly one JSON-RPC message; the response is returned as JSON.
  Authentication is the normal Home Assistant bearer token (a long-lived
  access token works for MCP clients).

The transport mirrors ``homeassistant/components/mcp_server/http.py``: a
short-lived MCP ``Server`` from the ``mcp`` SDK is run for the duration of the
request and talks to the HTTP handler through a pair of in-memory streams.

Routes cannot be removed from the aiohttp router once registered, so the view
is registered once per Home Assistant instance. It looks up the loaded config
entries on every request: unloading an entry removes its tools, and with no
entry loaded the endpoint answers 404.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, get_args

import anyio
from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden, HTTPNotFound, HTTPRequestEntityTooLarge
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util import dt as dt_util
from mcp import JSONRPCRequest, types
from mcp.server import InitializationOptions, Server
from mcp.shared.message import SessionMessage

from .accounts import account_label
from .const import CONF_APPLE_ID, CONF_ENDPOINT_ADMIN_ONLY, DEFAULT_ENDPOINT_ADMIN_ONLY, DOMAIN
from .llm_api import API_PROMPT, ICloudClients, build_tools, capability_hints
from .schema import vol

_LOGGER = logging.getLogger(__name__)

STREAMABLE_API = f"/api/{DOMAIN}"
READONLY_API = f"{STREAMABLE_API}/readonly"
MAX_BODY_BYTES = 1024 * 1024  # 1 MiB is plenty for JSON-RPC tool calls
PROFILES = ("full", "readonly")
SERVER_NAME = "icloud-mcp"
TIMEOUT = 120  # seconds; IMAP searches can be slow

DATA_MCP_HTTP = f"{DOMAIN}_mcp_http"

KNOWN_MCP_METHODS: frozenset[str] = frozenset(
    req_cls.model_fields["method"].default
    for req_cls in get_args(types.ClientRequestType)
    if "method" in req_cls.model_fields
)


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


def _format_tool(served: ServedTool) -> types.Tool:
    """Convert a Home Assistant LLM tool into an MCP tool description."""
    tool = served.tool
    input_schema = vol.to_openapi(tool.parameters, openapi_version="3.1.0")
    mcp_schema: dict[str, Any] = {"type": "object", "properties": input_schema.get("properties", {})}
    if required := input_schema.get("required"):
        mcp_schema["required"] = required

    annotations: types.ToolAnnotations | None = None
    if (ann := getattr(tool, "annotations", None)) is not None:
        annotations = types.ToolAnnotations(
            readOnlyHint=ann.read_only,
            destructiveHint=ann.destructive,
            idempotentHint=ann.idempotent,
            openWorldHint=ann.open_world,
        )
    return types.Tool(
        name=served.name,
        title=getattr(tool, "title", None),
        description=served.description,
        inputSchema=mcp_schema,
        annotations=annotations,
    )


def _text_result(data: Any, *, is_error: bool) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, default=str))],
        isError=is_error,
    )


def _error_result(message: str, code: str = "failed") -> types.CallToolResult:
    return _text_result({"error": message, "code": code}, is_error=True)


async def async_call_served_tool(
    hass: HomeAssistant, served: ServedTool, arguments: dict[str, Any], context: Context
) -> types.CallToolResult:
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


def create_server(
    hass: HomeAssistant, context: Context, version: str, profile: str = "full"
) -> tuple[Server, InitializationOptions]:
    """Create an MCP server that serves the tools of all loaded iCloud entries."""
    server = Server[Any](SERVER_NAME, version=version, instructions=_instructions(hass, profile))

    @server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def handle_list_tools() -> list[types.Tool]:
        return [_format_tool(served) for served in async_served_tools(hass, profile)]

    @server.call_tool(validate_input=False)  # type: ignore[untyped-decorator]
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> types.CallToolResult:
        arguments = arguments or {}
        _LOGGER.debug("MCP tool call: %s(%s)", name, arguments)
        for served in async_served_tools(hass, profile):
            if served.name == name:
                return await async_call_served_tool(hass, served, arguments, context)
        return _error_result(f"Unknown tool: {name}", "unknown_tool")

    # version is set explicitly, so this does not touch package metadata (no executor needed)
    return server, server.create_initialization_options()


# --------------------------------------------------------------------------- transport


@dataclass
class Streams:
    """Pairs of in-memory streams between the HTTP handler and the MCP server."""

    read_stream: MemoryObjectReceiveStream[SessionMessage | Exception]
    read_stream_writer: MemoryObjectSendStream[SessionMessage | Exception]
    write_stream: MemoryObjectSendStream[SessionMessage]
    write_stream_reader: MemoryObjectReceiveStream[SessionMessage]

    async def aclose(self) -> None:
        await self.read_stream.aclose()
        await self.read_stream_writer.aclose()
        await self.write_stream.aclose()
        await self.write_stream_reader.aclose()


@asynccontextmanager
async def create_streams() -> AsyncGenerator[Streams]:
    """Create a fresh pair of streams for one request."""
    read_stream_writer, read_stream = anyio.create_memory_object_stream[SessionMessage | Exception](0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream[SessionMessage](0)
    streams = Streams(
        read_stream=read_stream,
        read_stream_writer=read_stream_writer,
        write_stream=write_stream,
        write_stream_reader=write_stream_reader,
    )
    try:
        yield streams
    finally:
        await streams.aclose()


def _jsonrpc_error(request_id: Any, code: int, message: str, data: Any = None) -> web.Response:
    error = types.JSONRPCError(
        jsonrpc="2.0", id=request_id, error=types.ErrorData(code=code, message=message, data=data)
    )
    return web.json_response(data=error.model_dump(by_alias=True, exclude_none=True))


async def async_handle_streamable_message(
    request: web.Request, context: Context, profile: str = "full"
) -> web.StreamResponse:
    """Process one JSON-RPC message with a short-lived stateless MCP server."""
    hass: HomeAssistant = request.app[KEY_HASS]
    data: MCPHttpData | None = hass.data.get(DATA_MCP_HTTP)
    if data is None or not _loaded_entries(hass):
        raise HTTPNotFound(text="iCloud MCP is not configured")
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
        json_data = await request.json()
        message = types.JSONRPCMessage.model_validate(json_data)
    except ValueError as err:
        _LOGGER.debug("Failed to parse message as JSON-RPC message: %s", err)
        raise HTTPBadRequest(text="Request must be a JSON-RPC message") from err

    _LOGGER.debug("Received MCP client message: %s", message)

    # Notifications and responses are acknowledged only
    if not isinstance(message.root, JSONRPCRequest):
        return web.Response(status=HTTPStatus.ACCEPTED)

    if message.root.method not in KNOWN_MCP_METHODS:
        return _jsonrpc_error(message.root.id, types.METHOD_NOT_FOUND, "Method not found", message.root.method)

    server, options = create_server(hass, context, data.version, profile)

    async with create_streams() as streams:

        async def run_server() -> None:
            await server.run(streams.read_stream, streams.write_stream, options, stateless=True)

        async with asyncio.timeout(TIMEOUT), anyio.create_task_group() as tg:
            tg.start_soon(run_server)
            await streams.read_stream_writer.send(SessionMessage(message))
            session_message = await anext(streams.write_stream_reader)
            tg.cancel_scope.cancel()

    _LOGGER.debug("Sending MCP response: %s", session_message)
    return web.json_response(data=session_message.message.model_dump(by_alias=True, exclude_none=True))


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
        _LOGGER.info("iCloud MCP endpoints registered at %s and %s", STREAMABLE_API, READONLY_API)
