"""Note tools (IMAP 'Notes' mailbox)."""

from __future__ import annotations

import logging

from .const import (
    MAX_RESULTS_LIMIT,
)
from .guard import QUOTA_ITEM_DELETE
from .schema import vol
from .tool_base import ICloudTool
from .util import clamp

_LOGGER = logging.getLogger(__name__)


class ListNotes(ICloudTool):
    name = "icloud_list_notes"
    feature = "notes"
    description = "List or search notes stored in the account's IMAP Notes folder (newest first)."
    parameters = vol.Schema({vol.Optional("query"): str, vol.Optional("limit"): int})

    async def run(self, hass, args):
        notes = await self.clients.notes.async_list(
            args.get("query"), limit=clamp(args.get("limit"), self.clients.max_results, MAX_RESULTS_LIMIT)
        )
        return {"count": len(notes), "notes": notes}


class GetNote(ICloudTool):
    name = "icloud_get_note"
    feature = "notes"
    description = "Read a note (title and text) by uid."
    parameters = vol.Schema({vol.Required("uid"): int})

    async def run(self, hass, args):
        return await self.clients.notes.async_get(int(args["uid"]))


class CreateNote(ICloudTool):
    name = "icloud_create_note"
    feature = "notes"
    writes = True
    description = "Create a new note with a title and plain-text body."
    parameters = vol.Schema({vol.Required("title"): str, vol.Required("body"): str})

    async def run(self, hass, args):
        return await self.clients.notes.async_create(args["title"], args["body"])


class UpdateNote(ICloudTool):
    name = "icloud_update_note"
    feature = "notes"
    writes = True
    description = "Replace title and/or body of a note. The note gets a new uid afterwards."
    parameters = vol.Schema({vol.Required("uid"): int, vol.Optional("title"): str, vol.Optional("body"): str})

    async def run(self, hass, args):
        if args.get("title") is None and args.get("body") is None:
            raise ValueError("Provide title and/or body")
        return await self.clients.notes.async_update(int(args["uid"]), title=args.get("title"), body=args.get("body"))


class DeleteNote(ICloudTool):
    name = "icloud_delete_note"
    feature = "notes"
    writes = True
    deletes = True
    description = "Delete a note permanently. Confirm with the user first."
    parameters = vol.Schema({vol.Required("uid"): int})

    async def run(self, hass, args):
        self.clients.guard.check_quota(QUOTA_ITEM_DELETE)
        result = await self.clients.notes.async_delete(int(args["uid"]))
        self.clients.guard.consume(QUOTA_ITEM_DELETE)
        return result
