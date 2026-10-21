"""The mocks answer like the real backends: every field of tests/contracts/ws.json (in both repositories) is there.

The contracts are written by each repository's tests/test_contracts.py from real answers; a field the backend added
and the mock lacks fails here, so the preview cannot fall behind unnoticed.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

PREVIEW = Path(__file__).resolve().parent.parent
POSTFACH = Path(os.environ.get("POSTFACH_DIR") or PREVIEW.parent.parent.parent / "friedafetch-mail")

_spec = importlib.util.spec_from_file_location("contract", PREVIEW.parent.parent / "tests" / "contract.py")
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)

# what each command is asked in the mock (the mock's example data, not the backend test's)
REQUESTS = {
    "friedafetch/accounts": {},
    "friedafetch/overview": {"entry_id": "e1"},
    "friedafetch/approvals/list": {"entry_id": "e1"},
    "friedafetch/audit/list": {"entry_id": "e1"},
    "friedafetch_mail/accounts": {},
    "friedafetch_mail/mailboxes": {},
    "friedafetch_mail/rules/list": {},
    "friedafetch_mail/rules/history": {},
    "friedafetch_mail/rules/run": {"scope": "all", "dry_run": True},
    "friedafetch_mail/ai": {},
    "friedafetch_mail/activity/list": {},
    "friedafetch_mail/activity/select": {},
    "friedafetch_mail/mail/timeline": {"message_id": "<ratenkredit@example>"},
    "friedafetch_mail/mail/locate": {"message_id": "<ratenkredit@example>"},
    "friedafetch_mail/ai/assist": {"conversation": [{"role": "user", "text": "Alles vom Steuerberater, ins Archiv"}]},
    "friedafetch_mail/ai/assist/test": {"proposal": {"name": "Steuer", "description": "Finanzamt"}},
    "friedafetch_mail/ai/check": {},
    "friedafetch_mail/mail/act": {"keys": ["<test-frieda@example>"], "action": "flag"},
    "friedafetch_mail/mail/text": {"message_id": "<ratenkredit@example>"},
}
CONTRACTS = {
    "frieda": PREVIEW.parent.parent / "tests" / "contracts" / "ws.json",
    "postfach": Path(POSTFACH) / "tests" / "contracts" / "ws.json",
}


@pytest.mark.parametrize("name", ["frieda", "postfach"])
def test_the_mock_answers_like_the_backend(open_panel, name: str) -> None:
    if not CONTRACTS[name].exists():
        pytest.skip(f"{CONTRACTS[name]} does not exist yet (that repository has no contract)")
    contracts = json.loads(CONTRACTS[name].read_text(encoding="utf-8"))
    missing = sorted(set(contracts) - set(REQUESTS))
    assert not missing, f"add a request for {missing} to REQUESTS (and an answer to the mock)"
    panel = open_panel(name, "approvals=1" if name == "frieda" else "")
    problems = []
    for command, shape in contracts.items():
        answer = panel.js("return await el._hass.callWS(arg);", {"type": command, **REQUESTS[command]})
        problems += [f"{command}: {p}" for p in contract.check(shape, answer)]
    assert problems == [], "the mock lacks what the backend sends:\n" + "\n".join(problems)
