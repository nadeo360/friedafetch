"""Contact tools (CardDAV)."""

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


_CONTACT_FIELDS = {
    vol.Optional("given_name"): str,
    vol.Optional("family_name"): str,
    vol.Optional("additional_names"): str,
    vol.Optional("prefix"): str,
    vol.Optional("suffix"): str,
    vol.Optional("full_name", description="Display name; derived from the name parts when omitted"): str,
    vol.Optional("nickname"): str,
    vol.Optional("organization"): str,
    vol.Optional("department"): str,
    vol.Optional("title", description="Job title"): str,
    vol.Optional("emails", description="List of {value, label}; label e.g. home/work/other"): [
        vol.Any(str, {vol.Required("value"): str, vol.Optional("label"): str})
    ],
    vol.Optional("phones", description="List of {value, label}; label e.g. mobile/home/work/main/fax"): [
        vol.Any(str, {vol.Required("value"): str, vol.Optional("label"): str})
    ],
    vol.Optional("urls"): [vol.Any(str, {vol.Required("value"): str, vol.Optional("label"): str})],
    vol.Optional("addresses"): [
        {
            vol.Optional("label"): str,
            vol.Optional("street"): str,
            vol.Optional("city"): str,
            vol.Optional("region"): str,
            vol.Optional("postal_code"): str,
            vol.Optional("country"): str,
            vol.Optional("po_box"): str,
            vol.Optional("extended"): str,
        }
    ],
    vol.Optional("birthday", description="YYYY-MM-DD"): str,
    vol.Optional("note"): str,
}


class SearchContacts(ICloudTool):
    name = "icloud_search_contacts"
    feature = "contacts"
    description = "Search iCloud contacts by name, e-mail, phone number, company or note. Empty query lists all contacts alphabetically."
    parameters = vol.Schema({vol.Optional("query", description="Search text"): str, vol.Optional("limit"): int})

    async def run(self, hass, args):
        contacts = await self.clients.carddav.async_search(
            args.get("query"), limit=clamp(args.get("limit"), self.clients.max_results, MAX_RESULTS_LIMIT)
        )
        return {"count": len(contacts), "contacts": contacts}


class GetContact(ICloudTool):
    name = "icloud_get_contact"
    feature = "contacts"
    description = "Get a single contact by uid."
    parameters = vol.Schema({vol.Required("uid"): str})

    async def run(self, hass, args):
        return await self.clients.carddav.async_get(args["uid"])


class CreateContact(ICloudTool):
    name = "icloud_create_contact"
    feature = "contacts"
    writes = True
    description = "Create a new iCloud contact. Provide at least a name, organization or e-mail."
    parameters = vol.Schema(_CONTACT_FIELDS)

    async def run(self, hass, args):
        if not any(
            args.get(k) for k in ("given_name", "family_name", "full_name", "organization", "emails", "nickname")
        ):
            raise ValueError("Provide at least a name, organization or e-mail address")
        return await self.clients.carddav.async_create(args)


class UpdateContact(ICloudTool):
    name = "icloud_update_contact"
    feature = "contacts"
    writes = True
    description = (
        "Update an existing contact. Only provided fields change; list fields (emails, phones, urls, addresses) "
        "replace the existing list completely, so include entries that should be kept."
    )
    parameters = vol.Schema({vol.Required("uid"): str, **_CONTACT_FIELDS})

    async def run(self, hass, args):
        uid = args.pop("uid")
        if not args:
            raise ValueError("No fields to update")
        return await self.clients.carddav.async_update(uid, args)


class DeleteContact(ICloudTool):
    name = "icloud_delete_contact"
    feature = "contacts"
    writes = True
    deletes = True
    description = "Delete a contact permanently. Confirm with the user before deleting."
    parameters = vol.Schema({vol.Required("uid"): str})

    async def run(self, hass, args):
        self.clients.guard.check_quota(QUOTA_ITEM_DELETE)
        await self.clients.carddav.async_delete(args["uid"])
        self.clients.guard.consume(QUOTA_ITEM_DELETE)
        return {"deleted": True, "uid": args["uid"]}


# ================================================================== mail
