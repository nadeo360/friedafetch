"""Detect stale copies of Frieda under custom_components (e.g. a leftover custom_components/icloud_mcp).

Home Assistant maps custom integrations by the domain in manifest.json, not by the folder name. A second folder
whose manifest also says "friedafetch" (typically an old icloud_mcp folder that HACS updated before the rename)
can therefore silently shadow the real installation in custom_components/friedafetch.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_STALE_COPY = "stale_copy"
ISSUE_WRONG_FOLDER = "wrong_folder"


@dataclass(frozen=True, slots=True)
class InstallCheck:
    """Result of scanning custom_components for copies of this integration."""

    loaded: Path
    expected: Path
    stale: tuple[Path, ...]
    expected_exists: bool


def _manifest_domain(folder: Path) -> str | None:
    try:
        data = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data.get("domain") if isinstance(data, dict) else None


def scan_install(loaded: Path) -> InstallCheck:
    """Find every folder next to ``loaded`` that claims our domain but is not custom_components/<DOMAIN>.

    Blocking (file system access): run in the executor.
    """
    root = loaded.parent
    expected = root / DOMAIN
    stale: set[Path] = set()
    if loaded.name != DOMAIN:
        stale.add(loaded)
    try:
        folders = [p for p in root.iterdir() if p.is_dir() and p.name != DOMAIN]
    except OSError as err:
        _LOGGER.debug("Cannot scan %s for duplicate installations: %s", root, err)
        folders = []
    for folder in folders:
        if _manifest_domain(folder) == DOMAIN:
            stale.add(folder)
    return InstallCheck(
        loaded=loaded,
        expected=expected,
        stale=tuple(sorted(stale)),
        expected_exists=_manifest_domain(expected) == DOMAIN,
    )


async def async_check_install(hass: HomeAssistant, loaded: Path | None = None) -> InstallCheck:
    """Raise (or clear) a repair issue when another folder claims the friedafetch domain."""
    check = await hass.async_add_executor_job(scan_install, loaded or Path(__file__).parent)
    if not check.stale:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_STALE_COPY)
        ir.async_delete_issue(hass, DOMAIN, ISSUE_WRONG_FOLDER)
        return check

    # The only copy lives in a wrong folder: deleting it alone would remove Frieda, so reinstall first.
    issue = ISSUE_STALE_COPY if check.expected_exists else ISSUE_WRONG_FOLDER
    other = ISSUE_WRONG_FOLDER if issue == ISSUE_STALE_COPY else ISSUE_STALE_COPY
    paths = ", ".join(f"`{p}`" for p in check.stale)
    ir.async_delete_issue(hass, DOMAIN, other)
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue,
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=issue,
        translation_placeholders={
            "paths": paths,
            "loaded": str(check.loaded),
            "expected": str(check.expected),
        },
        learn_more_url="https://github.com/nadeo360/friedafetch#upgrading-from-icloud-mcp-versions-up-to-10x",
    )
    if issue == ISSUE_STALE_COPY:
        _LOGGER.warning(
            "Further copies of Frieda found: %s. Home Assistant may load one of them instead of %s "
            "(currently loaded from %s). Delete the extra folder(s) and restart Home Assistant",
            ", ".join(str(p) for p in check.stale),
            check.expected,
            check.loaded,
        )
    else:
        _LOGGER.warning(
            "Frieda is loaded from %s instead of %s. Reinstall Frieda via HACS, then delete %s and restart "
            "Home Assistant",
            check.loaded,
            check.expected,
            ", ".join(str(p) for p in check.stale),
        )
    return check
