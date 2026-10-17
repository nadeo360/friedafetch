"""Config and options flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.const import (
    CONF_APP_PASSWORD,
    CONF_APPLE_ID,
    CONF_ENABLE_MAIL,
    CONF_ENABLE_NOTES,
    CONF_FROM_ADDRESS,
    CONF_MAX_RESULTS,
    CONF_READ_ONLY,
    DOMAIN,
)
from custom_components.friedafetch.dav import DavAuthError, DavError
from custom_components.friedafetch.mail import MailAuthError

from .conftest import APP_PASSWORD, APPLE_ID


async def test_user_flow_success(hass: HomeAssistant, mock_discover: AsyncMock, mock_mail_login: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch("custom_components.friedafetch.async_setup_entry", return_value=True) as setup:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_APPLE_ID: " Test@iCloud.com ", CONF_APP_PASSWORD: APP_PASSWORD}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == APPLE_ID
    assert result["data"] == {CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD, CONF_FROM_ADDRESS: APPLE_ID}
    assert result["options"][CONF_ENABLE_MAIL] is True
    assert result["result"].unique_id == APPLE_ID
    assert setup.call_count == 1


async def test_user_flow_mail_unavailable_disables_mail(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with (
        patch(
            "custom_components.friedafetch.mail.ICloudMail.async_test_login",
            new_callable=AsyncMock,
            side_effect=MailAuthError("no"),
        ),
        patch("custom_components.friedafetch.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_ENABLE_MAIL] is False
    assert result["options"][CONF_ENABLE_NOTES] is False


async def test_user_flow_errors(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(
        "custom_components.friedafetch.caldav_client.ICloudCalDav.async_discover",
        new_callable=AsyncMock,
        side_effect=DavAuthError("401"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: "wrong"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(
        "custom_components.friedafetch.caldav_client.ICloudCalDav.async_discover",
        new_callable=AsyncMock,
        side_effect=DavError("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD}
        )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_already_configured(hass: HomeAssistant, mock_discover: AsyncMock, mock_mail_login: AsyncMock) -> None:
    MockConfigEntry(
        domain=DOMAIN, unique_id=APPLE_ID, data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: "x"}
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(hass: HomeAssistant, mock_discover: AsyncMock, mock_mail_login: AsyncMock) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=APPLE_ID, data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: "old"})
    entry.add_to_hass(hass)
    with patch("custom_components.friedafetch.async_setup_entry", return_value=True):
        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_APP_PASSWORD: "new-pass"})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_APP_PASSWORD] == "new-pass"


async def test_options_flow(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=APPLE_ID, data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: "x"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"tools", "security", "approvals", "rules"}

    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "tools"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "tools"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "enable_calendar": True,
            "enable_contacts": False,
            "enable_mail": True,
            "enable_notes": False,
            CONF_READ_ONLY: True,
            "allow_send_mail": True,
            "allow_delete": False,
            CONF_MAX_RESULTS: 20.0,
            "account_label": "Privat Konto",
            CONF_FROM_ADDRESS: "",
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_READ_ONLY] is True
    assert entry.options[CONF_MAX_RESULTS] == 20
    assert entry.options["account_label"] == "privat_konto"
    assert entry.options[CONF_FROM_ADDRESS] == APPLE_ID

    # security section keeps the other options and normalises the allowlist
    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_mailboxes",
        new_callable=AsyncMock,
        return_value=[{"name": "INBOX", "special_use": None}, {"name": "Steuer", "special_use": None}],
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "security"})
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "security"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "limit_mail_modify": 100.0,
                "limit_mail_send": 5.0,
                "limit_item_delete": 10.0,
                "send_policy": "allowlist",
                "send_allowlist": "Family@Example.com; example.org",
                "send_max_recipients": 3.0,
                "send_allow_bcc": False,
                "endpoint_admin_only": True,
                "protected_calendars": ["work"],
                "protected_mailboxes": ["Steuer"],
                "hidden_mailboxes": [],
            },
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["send_allowlist"] == ["family@example.com", "example.org"]
    assert entry.options["limit_mail_send"] == 5
    assert entry.options["protected_mailboxes"] == ["Steuer"]
    assert entry.options[CONF_READ_ONLY] is True  # kept from the tools section

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "rules"})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"rules_auto": False, "rules_interval": 15.0}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["rules_interval"] == 15 and entry.options["rules_auto"] is False

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "approvals"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "approvals"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "approval_send": True,
            "approval_delete": False,
            "approval_mass": 25.0,
            "approval_notify": "notify.mobile_app_iphone",
            "approval_timeout": 30.0,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["approval_send"] is True
    assert entry.options["approval_mass"] == 25
    assert entry.options["approval_notify"] == "mobile_app_iphone"
    assert entry.options["endpoint_admin_only"] is True
