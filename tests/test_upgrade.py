"""Updating from older versions: what they stored still loads, and the panel gets complete answers.

The stored data has the shapes older releases wrote (from their code in git): change-log entries of 1.1.0, usage
counters of 2.0.1 and a pending approval saved by 2.0.5 before a restart. After the update every answer of the panel
must still have the shape of tests/contracts/ws.json.
"""

import json
from typing import Any
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, CONF_APPROVAL_SEND, DOMAIN

from .conftest import APP_PASSWORD, APPLE_ID
from .contract import CONTRACTS, check

ENTRY_ID = "frieda_upgrade_entry"


def _stored(key: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"version": 1, "minor_version": 1, "key": key, "data": data}


AUDIT_1_1 = [
    {
        "id": 1,
        "time": "2026-10-10T08:00:00+00:00",
        "entry_id": ENTRY_ID,
        "account": APPLE_ID,
        "tool": "icloud_move_mail",
        "action": "write",
        "params": {"uids": [5, 6], "target_mailbox": "Archive"},
        "result": "ok",
        "error": None,
        "client": "friedafetch",
        "user_id": None,
        "user": None,
        "details": {"count": 2},
    },
    {
        "id": 2,
        "time": "2026-10-10T09:00:00+00:00",
        "entry_id": ENTRY_ID,
        "account": APPLE_ID,
        "tool": "icloud_delete_mail",
        "action": "delete",
        "params": {"uids": [1]},
        "result": "blocked",
        "error": "Hourly limit reached",
        "client": "mcp_server",
        "user_id": None,
        "user": None,
        "details": {},
    },
]
USAGE_2_0_1 = {
    "accounts": {
        ENTRY_ID: {
            "since": "2026-10-01T00:00:00+00:00",
            "total": {"read": 10, "write": 2, "error": 1},
            "days": {"2026-10-10": {"read": 3, "write": 1, "error": 0}},
            "tools": {"icloud_search_mail": 8, "icloud_move_mail": 4},
            "sources": {"friedafetch": 9, "mcp_server": 3},
            "last": {
                "time": "2026-10-10T09:00:00+00:00",
                "tool": "icloud_move_mail",
                "source": "friedafetch",
                "ok": True,
            },
        }
    },
    "clients": {"Claude": {"version": "1.0", "profile": "full", "last_seen": "2026-10-10T09:00:00+00:00"}},
}
PENDING_2_0_5 = {
    "id": "ab12cd34",
    "tool": "icloud_send_mail",
    "action": "send",
    "reason": "approval",
    "summary": "„Angebot“ → bob@example.com",
    "params": {"to": ["bob@example.com"], "subject": "Angebot"},
    "created": "2026-10-10T09:00:00+00:00",
    "expires": "2026-10-10T09:30:00+00:00",
    "status": "pending",
    "client": "Claude",
    "user_id": None,
    "decided_by": None,
    "decided_at": None,
    "result": None,
    "error": None,
}


async def test_update_keeps_change_log_usage_and_approvals(
    hass: HomeAssistant, mock_discover: AsyncMock, hass_storage, hass_ws_client
) -> None:
    hass_storage[f"{DOMAIN}.audit.{ENTRY_ID}"] = _stored(f"{DOMAIN}.audit.{ENTRY_ID}", {"entries": AUDIT_1_1, "seq": 2})
    hass_storage[f"{DOMAIN}.usage"] = _stored(f"{DOMAIN}.usage", USAGE_2_0_1)
    hass_storage[f"{DOMAIN}.state.{ENTRY_ID}"] = _stored(f"{DOMAIN}.state.{ENTRY_ID}", {"approvals": [PENDING_2_0_5]})
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=ENTRY_ID,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={CONF_APPROVAL_SEND: True},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ws = await hass_ws_client(hass)
    answers = {}
    for i, (command, extra) in enumerate(
        [
            ("friedafetch/accounts", {}),
            ("friedafetch/overview", {"entry_id": ENTRY_ID}),
            ("friedafetch/approvals/list", {"entry_id": ENTRY_ID}),
            ("friedafetch/audit/list", {"entry_id": ENTRY_ID}),
        ],
        start=1,
    ):
        await ws.send_json({"id": i, "type": command, **extra})
        msg = await ws.receive_json()
        assert msg["success"], (command, msg)
        answers[command] = msg["result"]

    contracts = json.loads(CONTRACTS.read_text())
    problems = [f"{cmd}: {p}" for cmd, answer in answers.items() for p in check(contracts[cmd], answer)]
    assert problems == []
    # the old entries are there, the approval that a restart interrupted is closed and logged
    tools = [e["tool"] for e in answers["friedafetch/audit/list"]["entries"]]
    assert "icloud_move_mail" in tools and "icloud_delete_mail" in tools
    request = answers["friedafetch/approvals/list"]["requests"][0]
    assert request["id"] == "ab12cd34" and request["status"] != "pending"
    assert answers["friedafetch/overview"]["usage"]["total"]["read"] == 10
    assert answers["friedafetch/overview"]["clients"][0]["name"] == "Claude"
