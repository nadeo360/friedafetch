"""Detection of stale copies of the integration under custom_components."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, DOMAIN
from custom_components.friedafetch.install_check import (
    ISSUE_STALE_COPY,
    ISSUE_WRONG_FOLDER,
    async_check_install,
    scan_install,
)

from .conftest import APP_PASSWORD, APPLE_ID


def _integration(root: Path, name: str, domain: str | None = DOMAIN) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    if domain is not None:
        (folder / "manifest.json").write_text(json.dumps({"domain": domain, "version": "1.0.0"}), encoding="utf-8")
    return folder


@pytest.fixture
def custom_components(tmp_path: Path) -> Path:
    return tmp_path / "custom_components"


def test_scan_clean(custom_components: Path) -> None:
    loaded = _integration(custom_components, DOMAIN)
    _integration(custom_components, "hacs", domain="hacs")
    _integration(custom_components, "no_manifest", domain=None)
    broken = _integration(custom_components, "broken", domain=None)
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")
    (custom_components / "README.txt").write_text("a file, not a folder", encoding="utf-8")

    check = scan_install(loaded)
    assert check.stale == ()
    assert check.expected == loaded
    assert check.expected_exists


def test_scan_finds_leftover_icloud_mcp(custom_components: Path) -> None:
    loaded = _integration(custom_components, DOMAIN)
    old = _integration(custom_components, "icloud_mcp")
    _integration(custom_components, "icloud_mcp_real_old", domain="icloud_mcp")

    check = scan_install(loaded)
    assert check.stale == (old,)
    assert check.expected_exists


def test_scan_loaded_from_wrong_folder(custom_components: Path) -> None:
    loaded = _integration(custom_components, "icloud_mcp")

    check = scan_install(loaded)
    assert check.stale == (loaded,)
    assert check.expected == custom_components / DOMAIN
    assert not check.expected_exists


def test_scan_loaded_from_wrong_folder_shadowing_new_install(custom_components: Path) -> None:
    loaded = _integration(custom_components, "icloud_mcp")
    _integration(custom_components, DOMAIN)

    check = scan_install(loaded)
    assert check.stale == (loaded,)
    assert check.expected_exists


async def test_no_issue_for_clean_install(hass: HomeAssistant, custom_components: Path) -> None:
    loaded = _integration(custom_components, DOMAIN)
    await async_check_install(hass, loaded)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, ISSUE_STALE_COPY) is None
    assert registry.async_get_issue(DOMAIN, ISSUE_WRONG_FOLDER) is None


async def test_issue_for_stale_copy_and_cleared_after_removal(
    hass: HomeAssistant, custom_components: Path, caplog: pytest.LogCaptureFixture
) -> None:
    loaded = _integration(custom_components, DOMAIN)
    old = _integration(custom_components, "icloud_mcp")

    await async_check_install(hass, loaded)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_STALE_COPY)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_key == ISSUE_STALE_COPY
    assert not issue.is_fixable
    assert str(old) in issue.translation_placeholders["paths"]
    assert issue.translation_placeholders["expected"] == str(loaded)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_WRONG_FOLDER) is None
    assert str(old) in caplog.text
    assert "Delete the extra folder" in caplog.text

    # the user deletes the folder and restarts: the issue disappears
    (old / "manifest.json").unlink()
    old.rmdir()
    await async_check_install(hass, loaded)
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_STALE_COPY) is None


async def test_issue_for_wrong_folder(
    hass: HomeAssistant, custom_components: Path, caplog: pytest.LogCaptureFixture
) -> None:
    loaded = _integration(custom_components, "icloud_mcp")

    await async_check_install(hass, loaded)
    registry = ir.async_get(hass)
    issue = registry.async_get_issue(DOMAIN, ISSUE_WRONG_FOLDER)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders["paths"] == f"`{loaded}`"
    assert issue.translation_placeholders["expected"] == str(custom_components / DOMAIN)
    assert registry.async_get_issue(DOMAIN, ISSUE_STALE_COPY) is None
    assert "Reinstall Frieda via HACS" in caplog.text

    # after reinstalling via HACS the old folder is reported as a stale copy instead
    _integration(custom_components, DOMAIN)
    await async_check_install(hass, loaded)
    assert registry.async_get_issue(DOMAIN, ISSUE_WRONG_FOLDER) is None
    assert registry.async_get_issue(DOMAIN, ISSUE_STALE_COPY) is not None


async def test_scan_runs_in_executor(hass: HomeAssistant, custom_components: Path) -> None:
    loaded = _integration(custom_components, DOMAIN)
    with patch.object(hass, "async_add_executor_job", wraps=hass.async_add_executor_job) as executor:
        await async_check_install(hass, loaded)
    assert executor.call_args.args == (scan_install, loaded)


def test_translations_cover_issues() -> None:
    base = Path(__file__).parent.parent / "custom_components" / DOMAIN
    for name in ("strings.json", "translations/en.json", "translations/de.json"):
        issues = json.loads((base / name).read_text(encoding="utf-8"))["issues"]
        for key in (ISSUE_STALE_COPY, ISSUE_WRONG_FOLDER):
            assert issues[key]["title"], (name, key)
            assert "{paths}" in issues[key]["description"], (name, key)
            assert "{expected}" in issues[key]["description"], (name, key)


async def test_setup_runs_check_once_without_issue(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=APPLE_ID,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.friedafetch.async_check_install", wraps=async_check_install) as check:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    check.assert_awaited_once()
    # the repository itself only contains custom_components/friedafetch
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_STALE_COPY) is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_WRONG_FOLDER) is None


async def test_setup_survives_failing_check(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=APPLE_ID,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.friedafetch.async_check_install", side_effect=RuntimeError("boom")):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
