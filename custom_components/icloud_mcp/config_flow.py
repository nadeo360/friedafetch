"""Config flow for iCloud MCP."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import client_context

from .caldav_client import ICloudCalDav
from .const import (
    CALDAV_URL,
    CONF_ALLOW_DELETE,
    CONF_ALLOW_SEND_MAIL,
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_ENABLE_CALENDAR,
    CONF_ENABLE_CONTACTS,
    CONF_ENABLE_MAIL,
    CONF_ENABLE_NOTES,
    CONF_FROM_ADDRESS,
    CONF_MAX_RESULTS,
    CONF_READ_ONLY,
    CONF_RULES_AUTO,
    CONF_RULES_INTERVAL,
    DEFAULT_ALLOW_DELETE,
    DEFAULT_ALLOW_SEND_MAIL,
    DEFAULT_ENABLE_CALENDAR,
    DEFAULT_ENABLE_CONTACTS,
    DEFAULT_ENABLE_MAIL,
    DEFAULT_ENABLE_NOTES,
    DEFAULT_MAX_RESULTS,
    DEFAULT_READ_ONLY,
    DEFAULT_RULES_AUTO,
    DEFAULT_RULES_INTERVAL,
    DOMAIN,
    IMAP_HOST,
    IMAP_PORT,
    MAX_RESULTS_LIMIT,
    MAX_RULES_INTERVAL,
    MIN_RULES_INTERVAL,
    REQUEST_TIMEOUT,
    SMTP_HOST,
    SMTP_PORT,
)
from .dav import DavAuthError, DavClient, DavError
from .mail import ICloudMail, MailAuthError, MailError
from .schema import vol

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_APPLE_ID): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_APP_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
        ),
    }
)
STEP_REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_APP_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
        ),
    }
)


class CannotConnect(Exception):
    """iCloud not reachable."""


class InvalidAuth(Exception):
    """Credentials rejected."""


async def validate_credentials(hass: HomeAssistant, apple_id: str, password: str) -> dict[str, Any]:
    """Validate the credentials against CalDAV (mandatory) and IMAP (optional)."""
    session = async_get_clientsession(hass)
    dav = DavClient(session, apple_id, password, timeout=REQUEST_TIMEOUT)
    caldav = ICloudCalDav(dav, CALDAV_URL, dt_util.get_default_time_zone())
    try:
        await caldav.async_discover()
    except DavAuthError as err:
        raise InvalidAuth from err
    except DavError as err:
        raise CannotConnect from err

    mail = ICloudMail(
        apple_id,
        password,
        from_address=apple_id,
        imap_host=IMAP_HOST,
        imap_port=IMAP_PORT,
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        timeout=REQUEST_TIMEOUT,
        ssl_context=client_context(),
    )
    mail_ok = True
    try:
        await mail.async_test_login()
    except (MailAuthError, MailError) as err:
        _LOGGER.warning("iCloud Mail login failed, mail/notes tools will be disabled: %s", err)
        mail_ok = False
    return {"mail_available": mail_ok}


def _normalize_apple_id(value: str) -> str:
    return value.strip().lower()


class ICloudMcpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ICloudMcpOptionsFlow:
        return ICloudMcpOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            apple_id = _normalize_apple_id(user_input[CONF_APPLE_ID])
            password = user_input[CONF_APP_PASSWORD].strip()
            await self.async_set_unique_id(apple_id)
            self._abort_if_unique_id_configured()
            try:
                info = await validate_credentials(self.hass, apple_id, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating iCloud credentials")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=apple_id,
                    data={
                        CONF_APPLE_ID: apple_id,
                        CONF_APP_PASSWORD: password,
                        CONF_FROM_ADDRESS: apple_id,
                    },
                    options={
                        CONF_ENABLE_CALENDAR: DEFAULT_ENABLE_CALENDAR,
                        CONF_ENABLE_CONTACTS: DEFAULT_ENABLE_CONTACTS,
                        CONF_ENABLE_MAIL: info["mail_available"],
                        CONF_ENABLE_NOTES: info["mail_available"],
                        CONF_READ_ONLY: DEFAULT_READ_ONLY,
                        CONF_ALLOW_SEND_MAIL: DEFAULT_ALLOW_SEND_MAIL,
                        CONF_ALLOW_DELETE: DEFAULT_ALLOW_DELETE,
                        CONF_MAX_RESULTS: DEFAULT_MAX_RESULTS,
                    },
                )
        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None
        apple_id = self._reauth_entry.data[CONF_APPLE_ID]
        if user_input is not None:
            password = user_input[CONF_APP_PASSWORD].strip()
            try:
                await validate_credentials(self.hass, apple_id, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={CONF_APP_PASSWORD: password},
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            description_placeholders={"apple_id": apple_id},
            errors=errors,
        )


class ICloudMcpOptionsFlow(OptionsFlow):
    """Options: which tool groups are exposed and safety switches."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_MAX_RESULTS] = int(user_input.get(CONF_MAX_RESULTS, DEFAULT_MAX_RESULTS))
            user_input[CONF_RULES_INTERVAL] = int(user_input.get(CONF_RULES_INTERVAL, DEFAULT_RULES_INTERVAL))
            if not user_input.get(CONF_FROM_ADDRESS):
                user_input[CONF_FROM_ADDRESS] = self.config_entry.data[CONF_APPLE_ID]
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        data = self.config_entry.data
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENABLE_CALENDAR, default=opts.get(CONF_ENABLE_CALENDAR, DEFAULT_ENABLE_CALENDAR)
                ): BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_CONTACTS, default=opts.get(CONF_ENABLE_CONTACTS, DEFAULT_ENABLE_CONTACTS)
                ): BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_MAIL, default=opts.get(CONF_ENABLE_MAIL, DEFAULT_ENABLE_MAIL)
                ): BooleanSelector(),
                vol.Required(
                    CONF_ENABLE_NOTES, default=opts.get(CONF_ENABLE_NOTES, DEFAULT_ENABLE_NOTES)
                ): BooleanSelector(),
                vol.Required(CONF_READ_ONLY, default=opts.get(CONF_READ_ONLY, DEFAULT_READ_ONLY)): BooleanSelector(),
                vol.Required(
                    CONF_ALLOW_SEND_MAIL, default=opts.get(CONF_ALLOW_SEND_MAIL, DEFAULT_ALLOW_SEND_MAIL)
                ): BooleanSelector(),
                vol.Required(
                    CONF_ALLOW_DELETE, default=opts.get(CONF_ALLOW_DELETE, DEFAULT_ALLOW_DELETE)
                ): BooleanSelector(),
                vol.Required(CONF_MAX_RESULTS, default=opts.get(CONF_MAX_RESULTS, DEFAULT_MAX_RESULTS)): NumberSelector(
                    NumberSelectorConfig(min=1, max=MAX_RESULTS_LIMIT, step=1, mode=NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_RULES_AUTO, default=opts.get(CONF_RULES_AUTO, DEFAULT_RULES_AUTO)): BooleanSelector(),
                vol.Required(
                    CONF_RULES_INTERVAL, default=opts.get(CONF_RULES_INTERVAL, DEFAULT_RULES_INTERVAL)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_RULES_INTERVAL, max=MAX_RULES_INTERVAL, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_FROM_ADDRESS,
                    default=opts.get(CONF_FROM_ADDRESS) or data.get(CONF_FROM_ADDRESS) or data[CONF_APPLE_ID],
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
