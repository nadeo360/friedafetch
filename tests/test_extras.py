"""Insight, unsubscribe and attachment tools wired into Home Assistant."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, DOMAIN, LLM_API_ID
from custom_components.friedafetch.mail import parse_message

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


async def test_attachment_folder_option(hass: HomeAssistant, mock_discover: AsyncMock, tmp_path: Path) -> None:
    entry = _entry()
    await _api(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "tools"})
    form = {
        "enable_calendar": True,
        "enable_contacts": True,
        "enable_mail": True,
        "enable_notes": True,
        "read_only": False,
        "allow_send_mail": True,
        "allow_delete": True,
        "max_results": 50,
        "attachments_dir": "/etc/nope",
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], form)
    assert result["errors"] == {"attachments_dir": "path_not_allowed"}
    hass.config.allowlist_external_dirs.add(str(tmp_path))
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], form | {"attachments_dir": str(tmp_path)}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.runtime_data.attachments is not None


async def test_extension_tools_and_rule_matcher(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    """Extensions contribute tools (gated by the core options) and rule coverage for the statistics."""
    from custom_components.friedafetch.llm_api import ICloudTool
    from custom_components.friedafetch.schema import vol

    class Hello(ICloudTool):
        name = "icloud_hello"
        feature = "mail"
        description = "test"
        parameters = vol.Schema({})

        async def run(self, hass, args):
            return {"ok": True}

    class Writer(Hello):
        name = "icloud_hello_write"
        writes = True

    entry = _entry(read_only=True)
    await _api(hass, entry)
    ext = MagicMock(tool_classes=[Hello, Writer], rule_matcher=lambda box: lambda s: "Abo")
    entry.runtime_data.extensions["mail"] = ext
    ctx = llm.LLMContext(platform="test", context=Context(), language="de", assistant=None, device_id=None)
    api = await llm.async_get_api(hass, LLM_API_ID, ctx)
    names = {t.name for t in api.tools}
    assert "icloud_hello" in names and "icloud_hello_write" not in names  # read-only hides writing extension tools
    summaries = [{"uid": 1, "seen": True, "newsletter": True, "from": [{"name": "", "email": "n@shop.example"}]}]
    with (
        patch("custom_components.friedafetch.mail.ICloudMail.async_search_uids", AsyncMock(return_value=[1])),
        patch("custom_components.friedafetch.mail.ICloudMail.async_summaries", AsyncMock(return_value=summaries)),
    ):
        stats = await _call(api, "icloud_mailbox_stats")
    assert stats.data["top_senders"][0]["covered_by"] == "Abo"


async def test_moved_rules_repair_issue(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    from homeassistant.helpers import issue_registry as ir

    entry = _entry()
    entry.add_to_hass(hass)
    storage = Path(hass.config.path(".storage"))
    await hass.async_add_executor_job(lambda: storage.mkdir(parents=True, exist_ok=True))
    await hass.async_add_executor_job((storage / f"{DOMAIN}.rules.{entry.entry_id}").write_text, "{}")
    with patch("custom_components.friedafetch.carddav_client.ICloudCardDav.async_search", AsyncMock(return_value=[])):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"rules_moved_{entry.entry_id}")
    assert issue is not None and issue.translation_key == "rules_moved"
