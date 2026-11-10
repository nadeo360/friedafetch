"""What other people can see: diagnostics (pasted into public issues) and stored attachments (media browser)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant.components.repairs import repairs_flow_manager
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from custom_components.friedafetch.attachments import async_check_legacy_attachments, move_tree
from custom_components.friedafetch.caldav_client import CalendarInfo
from custom_components.friedafetch.const import DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA
from custom_components.friedafetch.diagnostics import async_get_config_entry_diagnostics

from .conftest import APP_PASSWORD, APPLE_ID
from .test_extras import _api, _entry


async def test_diagnostics_name_no_one(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = _entry(
        from_address="me@example.com",
        account_label="stefan",
        send_allowlist="anna@example.com\nfamily.example",
        approval_notify="mobile_app_stefans_iphone",
        protected_calendars=["Familie"],
        protected_mailboxes=["Arzt"],
        hidden_mailboxes=["Bank"],
        attachments_dir="/media/stefan/belege",
        max_results=40,
    )
    await _api(hass, entry)
    calendar = CalendarInfo(id="secret-id", name="Familie", color="#ff0000", description="Termine mit Anna", href="/x/")
    with patch(
        "custom_components.friedafetch.caldav_client.ICloudCalDav.async_calendars", AsyncMock(return_value=[calendar])
    ):
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    text = json.dumps(diagnostics)
    for private in (APPLE_ID, APP_PASSWORD, "me@example.com", "anna@example.com", "family.example", "stefan",
                    "Familie", "Arzt", "Bank", "/media/stefan", "secret-id", "Anna"):  # fmt: skip
        assert private not in text, private
    assert diagnostics["entry"]["options"]["max_results"] == 40  # settings without a person stay readable
    assert diagnostics["calendars"][0]["color"] == "#ff0000"


async def test_attachments_go_to_a_folder_no_media_source_shows(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = _entry()
    await _api(hass, entry)
    base = entry.runtime_data.attachments.base
    assert base == Path(hass.config.path("frieda_attachments"))
    assert all(not str(base).startswith(str(Path(m))) for m in (hass.config.media_dirs or {}).values())


def _legacy(hass: HomeAssistant, tmp_path: Path) -> Path:
    hass.config.media_dirs = {"local": str(tmp_path / "media")}
    old = tmp_path / "media" / "frieda" / "Belege" / "2026-10"
    old.mkdir(parents=True)
    (old / "rechnung.pdf").write_bytes(b"%PDF one")
    return tmp_path / "media" / "frieda"


async def _fix(hass: HomeAssistant, choice: str) -> dict:
    assert await async_setup_component(hass, "repairs", {})
    manager = repairs_flow_manager(hass)
    assert manager is not None
    result = await manager.async_init(DOMAIN, data={"issue_id": ISSUE_ATTACHMENTS_IN_MEDIA})
    assert result["type"] is FlowResultType.MENU and result["menu_options"] == ["move", "keep"]
    assert result["description_placeholders"]["target"].endswith("frieda_attachments")
    return await manager.async_configure(result["flow_id"], {"next_step_id": choice})


async def test_old_attachments_move_into_the_own_folder(
    hass: HomeAssistant, mock_discover: AsyncMock, tmp_path: Path
) -> None:
    old = _legacy(hass, tmp_path)
    await _api(hass, _entry())
    await async_check_legacy_attachments(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA) is not None
    result = await _fix(hass, "move")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    moved = Path(hass.config.path("frieda_attachments")) / "Belege" / "2026-10" / "rechnung.pdf"
    assert moved.read_bytes() == b"%PDF one" and not old.exists()
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA) is None
    await async_check_legacy_attachments(hass)  # nothing left there: no new repair
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA) is None


async def test_old_attachments_stay_on_purpose(hass: HomeAssistant, mock_discover: AsyncMock, tmp_path: Path) -> None:
    old = _legacy(hass, tmp_path)
    entry = _entry()
    await _api(hass, entry)
    await async_check_legacy_attachments(hass)
    result = await _fix(hass, "keep")
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["attachments_dir"] == str(old)  # chosen now, and named in the options
    assert (old / "Belege" / "2026-10" / "rechnung.pdf").exists()
    await async_check_legacy_attachments(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA) is None


def test_moving_keeps_both_when_names_meet(tmp_path: Path) -> None:
    source, target = tmp_path / "a", tmp_path / "b"
    for folder, content in ((source, b"new"), (target, b"old")):
        folder.mkdir()
        (folder / "x.pdf").write_bytes(content)
    (source / "same.pdf").write_bytes(b"same")
    (target / "same.pdf").write_bytes(b"same")
    assert move_tree(source, target) == 1
    assert sorted(p.name for p in target.iterdir()) == ["same.pdf", "x-1.pdf", "x.pdf"]
    assert (target / "x-1.pdf").read_bytes() == b"new" and not source.exists()
