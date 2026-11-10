"""Repairs with a fix: attachments still in the media folder (the default until 2.0.27)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow, RepairsFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .attachments import entries_on_default, legacy_folder, move_tree
from .const import CONF_ATTACHMENTS_DIR, DEFAULT_ATTACHMENTS_DIR, DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA


class AttachmentsInMediaFlow(RepairsFlow):
    """Move the attachments into Frieda's own folder, or keep the media folder on purpose."""

    def _placeholders(self) -> dict[str, str]:
        return {"folder": str(legacy_folder(self.hass)), "target": self.hass.config.path(DEFAULT_ATTACHMENTS_DIR)}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        return self.async_show_menu(
            step_id="init", menu_options=["move", "keep"], description_placeholders=self._placeholders()
        )

    async def async_step_move(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        moved = await self.hass.async_add_executor_job(
            move_tree, legacy_folder(self.hass), Path(self.hass.config.path(DEFAULT_ATTACHMENTS_DIR))
        )
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA)
        return self.async_create_entry(data={"moved": moved})

    async def async_step_keep(self, user_input: dict[str, Any] | None = None) -> RepairsFlowResult:
        folder = str(legacy_folder(self.hass))
        for entry in entries_on_default(self.hass):
            self.hass.config_entries.async_update_entry(
                entry, options={**entry.options, CONF_ATTACHMENTS_DIR: folder}
            )  # chosen on purpose now: the option names the folder (and says who can see it)
        ir.async_delete_issue(self.hass, DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA)
        return self.async_create_entry(data={})


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None) -> RepairsFlow:
    if issue_id == ISSUE_ATTACHMENTS_IN_MEDIA:
        return AttachmentsInMediaFlow()
    return ConfirmRepairFlow()
