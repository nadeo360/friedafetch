"""Package C wired into Home Assistant: tools, rule action, daily overview, sensor, options."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, DOMAIN, LLM_API_ID
from custom_components.friedafetch.digest import async_send_digest, render_text
from custom_components.friedafetch.mail import parse_message
from custom_components.friedafetch.rules import RuleEngine

from .conftest import APP_PASSWORD, APPLE_ID

NEWSLETTER = parse_message(
    b"From: Shop <news@shop.example>\r\nSubject: Angebote\r\n"
    b"List-Unsubscribe: <mailto:leave@shop.example>, <https://shop.example/u/1>\r\n"
    b"List-Unsubscribe-Post: List-Unsubscribe=One-Click\r\n\r\nHallo"
)
MAILTO_ONLY = parse_message(
    b"From: Shop <news@shop.example>\r\nSubject: Angebote\r\nList-Unsubscribe: <mailto:leave@shop.example>\r\n\r\nx"
)


def _entry(**options) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=APPLE_ID,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options=options,
    )


async def _api(hass: HomeAssistant, entry: MockConfigEntry) -> llm.APIInstance:
    entry.add_to_hass(hass)
    with patch("custom_components.friedafetch.carddav_client.ICloudCardDav.async_search", AsyncMock(return_value=[])):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    ctx = llm.LLMContext(platform="test", context=Context(), language="de", assistant=None, device_id=None)
    return await llm.async_get_api(hass, LLM_API_ID, ctx)


async def _call(api: llm.APIInstance, name: str, **args):
    return await api.async_call_tool(llm.ToolInput(tool_name=name, tool_args=args))


# ------------------------------------------------------------------ rules
async def test_rule_saves_attachments_before_deleting(hass: HomeAssistant) -> None:
    mail = MagicMock()
    mail.async_mailboxes = AsyncMock(return_value=[{"name": "INBOX", "special_use": None}])
    mail.async_search_uids = AsyncMock(return_value=[5])
    mail.async_summaries = AsyncMock(
        return_value=[{"uid": 5, "subject": "Ihre Rechnung", "from": [{"name": "", "email": "bill@shop.example"}]}]
    )
    order: list[str] = []
    mail.async_delete = AsyncMock(side_effect=lambda *a, **k: order.append("delete"))
    saver = AsyncMock(
        side_effect=lambda *a: order.append("save") or [{"status": "saved", "path": "Belege/2026-10/x.pdf"}]
    )
    engine = RuleEngine(hass, "entry-att", mail, attachment_saver=saver)
    await engine.async_create(
        {
            "name": "Belege",
            "conditions": [{"field": "subject", "op": "contains", "value": "rechnung"}],
            "actions": {"delete": True, "save_attachments": True, "attachments_folder": "Belege"},
        }
    )
    report = await engine.async_run(scope="all")
    saver.assert_awaited_once_with("INBOX", 5, "Belege")
    assert order == ["save", "delete"]
    assert report["saved_files"] == ["Belege/2026-10/x.pdf"] and report["actions"][0]["save_attachments"]
    assert engine.history()[0]["saved_files"] == 1

    # without an attachment folder the action is reported as skipped, the rest still runs
    engine.attachment_saver = None
    report = await engine.async_run(scope="all")
    assert any(s["code"] == "attachments_unavailable" for s in report["skipped"])

    # save_attachments alone is a valid action
    rule = await engine.async_create(
        {
            "name": "Nur Anhänge",
            "conditions": [{"field": "from", "op": "contains", "value": "x"}],
            "actions": {"save_attachments": True},
        }
    )
    assert rule["actions"]["save_attachments"] is True


# ------------------------------------------------------------------ tools
async def test_calendar_and_contact_tools(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    api = await _api(hass, _entry())
    with patch(
        "custom_components.friedafetch.caldav_client.ICloudCalDav.async_events", AsyncMock(return_value=[])
    ) as events:
        result = await _call(api, "icloud_find_free_time", duration_minutes=45, weekdays_only=False)
    assert result.error is False, result.data
    assert result.data["count"] >= 1 and events.await_count == 1
    bad = await _call(api, "icloud_find_free_time", duration_minutes=2)
    assert bad.error is True

    contacts = [
        {"uid": "1", "full_name": "Anna", "birthday": "1990-01-01", "emails": [{"value": "a@x.example"}], "phones": []},
        {"uid": "2", "full_name": "Anna B", "emails": [{"value": "a@x.example"}], "phones": []},
    ]
    with patch(
        "custom_components.friedafetch.carddav_client.ICloudCardDav.async_search", AsyncMock(return_value=contacts)
    ):
        birthdays = await _call(api, "icloud_upcoming_birthdays", days=366)
        dupes = await _call(api, "icloud_find_duplicate_contacts")
    assert birthdays.data["count"] == 1 and birthdays.data["birthdays"][0]["name"] == "Anna"
    assert dupes.data["groups"] == 1


async def test_mailbox_stats_tool(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    api = await _api(hass, _entry())
    summaries = [
        {
            "uid": i,
            "seen": False,
            "newsletter": True,
            "subject": "Deal",
            "from": [{"name": "Shop", "email": "news@shop.example"}],
        }
        for i in range(1, 5)
    ]
    with (
        patch("custom_components.friedafetch.mail.ICloudMail.async_search_uids", AsyncMock(return_value=[1, 2, 3, 4])),
        patch("custom_components.friedafetch.mail.ICloudMail.async_summaries", AsyncMock(return_value=summaries)),
    ):
        result = await _call(api, "icloud_mailbox_stats", days=30)
    assert result.error is False, result.data
    assert result.data["messages"] == 4 and result.data["rule_suggestions"][0]["domain"] == "shop.example"


async def test_unsubscribe_tool(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    api = await _api(hass, _entry())
    with (
        patch(
            "custom_components.friedafetch.mail.ICloudMail.async_fetch_raw",
            AsyncMock(return_value=(MagicMock(), NEWSLETTER)),
        ),
        patch(
            "custom_components.friedafetch.llm_api.async_one_click",
            AsyncMock(return_value={"method": "one_click", "status": 200, "host": "shop.example"}),
        ) as one_click,
    ):
        result = await _call(api, "icloud_unsubscribe", uid=7)
    assert result.error is False, result.data
    assert result.data["method"] == "one_click"
    one_click.assert_awaited_once()
    assert one_click.await_args.args[0] == "https://shop.example/u/1"
    audit = hass.config_entries.async_entries(DOMAIN)[0].runtime_data.audit
    assert audit.entries()[0]["tool"] == "icloud_unsubscribe"


async def test_unsubscribe_mailto_respects_send_option(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    api = await _api(hass, _entry(allow_send_mail=False))
    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_fetch_raw",
        AsyncMock(return_value=(MagicMock(), MAILTO_ONLY)),
    ):
        result = await _call(api, "icloud_unsubscribe", uid=7)
    assert result.error is True and "sending e-mails is disabled" in result.data["error"]


async def test_save_attachments_tool_needs_allowed_folder(
    hass: HomeAssistant, mock_discover: AsyncMock, tmp_path: Path
) -> None:
    api = await _api(hass, _entry(attachments_dir=str(tmp_path / "not-allowed")))
    assert "icloud_save_attachments" not in {t.name for t in api.tools}


async def test_save_attachments_tool(hass: HomeAssistant, mock_discover: AsyncMock, tmp_path: Path) -> None:
    hass.config.allowlist_external_dirs.add(str(tmp_path))
    api = await _api(hass, _entry(attachments_dir=str(tmp_path / "frieda")))
    msg = parse_message(
        b"From: Shop <bill@shop.example>\r\nDate: Fri, 16 Oct 2026 10:00:00 +0200\r\nSubject: Rechnung\r\n"
        b'MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary="b"\r\n\r\n--b\r\n'
        b"Content-Type: text/plain\r\n\r\nAnbei\r\n--b\r\n"
        b'Content-Type: application/pdf\r\nContent-Disposition: attachment; filename="Rechnung.pdf"\r\n'
        b"Content-Transfer-Encoding: base64\r\n\r\nJVBERi0xLjcgSGFsbG8=\r\n--b--\r\n"
    )
    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_fetch_raw", AsyncMock(return_value=(MagicMock(), msg))
    ):
        result = await _call(api, "icloud_save_attachments", uid=3, folder="Belege")
    assert result.error is False, result.data
    assert result.data["count"] == 1
    stored = tmp_path / "frieda" / result.data["files"][0]["path"]
    assert stored.read_bytes().startswith(b"%PDF") and "2026-10" in str(stored) and "shop" in stored.name


# --------------------------------------------------------------- overview
def test_render_text() -> None:
    title, text = render_text(
        {
            "unread": [
                {"from": "Chef", "subject": "Budget", "newsletter": False},
                {"from": "Shop", "subject": "Deal", "newsletter": True},
            ],
            "rules": {"Werbung": 4, "Belege": 1},
            "events": [{"summary": "Zahnarzt", "start": "2026-10-17T09:30:00+02:00", "all_day": False}],
            "birthdays": [{"name": "Anna", "in_days": 0}],
        },
        "de",
    )
    assert title == "Frieda – Tagesüberblick"
    assert "2 ungelesene Mails" in text and "Chef: Budget" in text and "Shop: Deal" not in text
    assert "Regeln: 5 Mails verarbeitet" in text and "09:30 Zahnarzt" in text and "Anna (heute)" in text


async def test_send_digest_paths(hass: HomeAssistant) -> None:
    hass.config.language = "de"
    clients = MagicMock()
    clients.options = {"enable_calendar": False, "enable_contacts": False, "enable_mail": False}
    notifications = async_mock_service(hass, "persistent_notification", "create")
    result = await async_send_digest(hass, clients)
    assert result["sent_to"] == "persistent_notification" and len(notifications) == 1

    phone = async_mock_service(hass, "notify", "mobile_app_iphone")
    async_mock_service(
        hass, "ai_task", "generate_data", response={"data": "Guten Morgen! Alles ruhig."}, supports_response=True
    )
    clients.options |= {"digest_notify": "notify.mobile_app_iphone", "digest_ai_task": "ai_task.google"}
    result = await async_send_digest(hass, clients, account="privat")
    assert result["ai"] is True and result["sent_to"] == "notify.mobile_app_iphone"
    assert phone[0].data == {"title": "Frieda – Tagesüberblick (privat)", "message": "Guten Morgen! Alles ruhig."}


async def test_send_digest_service(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    await _api(hass, _entry())
    with patch(
        "custom_components.friedafetch.async_send_digest",
        AsyncMock(return_value={"sent_to": "persistent_notification", "message": "x"}),
    ) as send:
        response = await hass.services.async_call(DOMAIN, "send_digest", {}, blocking=True, return_response=True)
    send.assert_awaited_once()
    assert response["results"][0]["sent_to"] == "persistent_notification"
    with pytest.raises(Exception, match="No loaded Frieda account"):
        await hass.services.async_call(DOMAIN, "send_digest", {"account": "nope"}, blocking=True, return_response=True)


# ------------------------------------------------------------ sensor, push
async def test_birthday_sensor(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    from homeassistant.util import dt as dt_util

    today = dt_util.now().date()
    contacts = [{"uid": "1", "full_name": "Anna", "birthday": f"1990-{today:%m-%d}"}]
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.friedafetch.carddav_client.ICloudCardDav.async_search", AsyncMock(return_value=contacts)
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    states = [s for s in hass.states.async_all("sensor") if s.entity_id.startswith("sensor.frieda")]
    assert len(states) == 1
    assert states[0].state == today.isoformat()
    assert states[0].attributes["names"] == ["Anna"] and states[0].attributes["in_days"] == 0


async def test_push_watcher_is_set_up(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = _entry()
    await _api(hass, entry)
    clients = entry.runtime_data
    assert clients.watcher is not None and clients.rules.push is clients.watcher
    assert clients.rules.automation_status()["push"]["mailbox"] == "INBOX"

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        unique_id="b@icloud.com",
        data={CONF_APPLE_ID: "b@icloud.com", CONF_APP_PASSWORD: "x"},
        options={"rules_push": False},
    )
    entry2.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()
    assert entry2.runtime_data.watcher is None


async def test_extras_options(hass: HomeAssistant, mock_discover: AsyncMock, tmp_path: Path) -> None:
    entry = _entry()
    await _api(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "extras"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "extras"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"digest_time": "7:5x", "attachments_dir": "/etc/nope"}
    )
    assert result["errors"] == {"digest_time": "invalid_time", "attachments_dir": "path_not_allowed"}
    hass.config.allowlist_external_dirs.add(str(tmp_path))
    with patch("custom_components.friedafetch.carddav_client.ICloudCardDav.async_search", AsyncMock(return_value=[])):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"digest_time": "07:30", "digest_notify": "notify.mobile_app_x", "attachments_dir": str(tmp_path)},
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["digest_time"] == "07:30" and entry.options["digest_notify"] == "mobile_app_x"
    assert entry.runtime_data.attachments is not None
    assert await hass.config_entries.async_unload(entry.entry_id)
