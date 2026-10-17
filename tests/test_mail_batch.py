"""Batch operations on several message uids."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, DOMAIN, LLM_API_ID
from custom_components.friedafetch.mail import ICloudMail, MailError

from .conftest import APP_PASSWORD, APPLE_ID


def _mail() -> ICloudMail:
    return ICloudMail("u", "p", from_address="u@icloud.com", imap_host="h", imap_port=993, smtp_host="s", smtp_port=587)


def test_uid_set_normalises_and_limits() -> None:
    assert ICloudMail._uid_set(5) == ([5], "5")
    assert ICloudMail._uid_set([3, 1, 3, 2]) == ([1, 2, 3], "1,2,3")
    with pytest.raises(MailError):
        ICloudMail._uid_set([])
    with pytest.raises(MailError):
        ICloudMail._uid_set(list(range(600)))


async def test_move_many_uses_single_move_command() -> None:
    mail = _mail()
    client = MagicMock()
    client.has_capability.return_value = True
    client.uid = AsyncMock(return_value=MagicMock(result="OK", lines=[]))
    mail._mailboxes = [{"name": "Junk", "delimiter": "/", "flags": [], "special_use": "junk"}]

    async def run(func, *args, retry=True):
        mail._selected = "INBOX"
        return await func(client, *args)

    with patch.object(mail, "_run", run):
        result = await mail.async_move("INBOX", [12, 7, 9], "Junk")
    client.uid.assert_awaited_once_with("move", "7,9,12", '"Junk"')
    assert result == {"uids": [7, 9, 12], "count": 3, "from_mailbox": "INBOX", "to_mailbox": "Junk"}


async def test_delete_many_moves_to_trash_in_one_call() -> None:
    mail = _mail()
    mail._mailboxes = [{"name": "Deleted Messages", "delimiter": "/", "flags": [], "special_use": "trash"}]
    with patch.object(mail, "async_move", AsyncMock(return_value={"uids": [1, 2], "count": 2})) as move:
        result = await mail.async_delete("INBOX", [2, 1])
    move.assert_awaited_once_with("INBOX", [2, 1], "Deleted Messages")
    assert result["action"] == "moved_to_trash"


async def test_tools_accept_uid_lists(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=APPLE_ID, data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ctx = llm.LLMContext(platform="test", context=Context(), language="de", assistant=None, device_id=None)
    api = await llm.async_get_api(hass, LLM_API_ID, ctx)

    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_delete",
        new_callable=AsyncMock,
        return_value={"uids": [1, 2, 3], "count": 3, "action": "moved_to_trash"},
    ) as delete:
        result = await api.async_call_tool(
            llm.ToolInput(tool_name="icloud_delete_mail", tool_args={"uids": [1, 2], "uid": 3, "mailbox": "INBOX"})
        )
    delete.assert_awaited_once_with("INBOX", [3, 1, 2])
    assert result.error is False
    assert result.data["count"] == 3

    result = await api.async_call_tool(llm.ToolInput(tool_name="icloud_mark_mail", tool_args={"seen": True}))
    assert result.error is True
    assert "uid" in result.data["error"]
