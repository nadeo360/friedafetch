"""Inbox rule engine."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import llm
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.friedafetch.const import CONF_APP_PASSWORD, CONF_APPLE_ID, DOMAIN, LLM_API_ID
from custom_components.friedafetch.rules import Condition, Rule, RuleEngine, RuleError, RuleNotFound

from .conftest import APP_PASSWORD, APPLE_ID

NEWSLETTER = {
    "uid": 11,
    "subject": "Wochen-Newsletter: Angebote",
    "from": [{"name": "Shop News", "email": "news@shop.example.com"}],
    "to": [{"name": "", "email": "me@icloud.com"}],
    "cc": [],
}
BOSS = {
    "uid": 12,
    "subject": "Wichtig: Budget",
    "from": [{"name": "Chef", "email": "chef@firma.example"}],
    "to": [{"name": "", "email": "me@icloud.com"}],
    "cc": [],
}
SPAM = {
    "uid": 13,
    "subject": "You WON a prize!!!",
    "from": [{"name": "", "email": "x@spam.example.org"}],
    "to": [],
    "cc": [],
}


def test_conditions() -> None:
    assert Condition("from", "domain", "shop.example.com").matches(NEWSLETTER)
    assert Condition("from", "domain", "example.com").matches(NEWSLETTER)  # subdomain
    assert not Condition("from", "domain", "example.org").matches(NEWSLETTER)
    assert Condition("subject", "contains", "newsletter").matches(NEWSLETTER)
    assert Condition("any", "contains", "chef@").matches(BOSS)
    assert Condition("subject", "regex", r"won .* prize").matches(SPAM)
    assert Condition("subject", "starts_with", "wichtig").matches(BOSS)
    with pytest.raises(RuleError):
        Condition("body", "contains", "x").validate()
    with pytest.raises(RuleError):
        Condition("subject", "regex", "(").validate()


def test_rule_validation() -> None:
    rule = Rule.from_dict({"name": "", "conditions": [], "actions": {}})
    with pytest.raises(RuleError):
        rule.validate()
    rule = Rule.from_dict(
        {
            "name": "x",
            "conditions": [{"field": "subject", "op": "contains", "value": "a"}],
            "actions": {"move_to": "A", "delete": True},
        }
    )
    with pytest.raises(RuleError):
        rule.validate()
    rule = Rule.from_dict(
        {
            "name": "x",
            "conditions": [{"field": "subject", "op": "contains", "value": "a"}],
            "actions": {"mark_seen": True},
        }
    )
    rule.validate()
    assert rule.to_dict()["actions"]["stop"] is True


def _mail(uids: list[int], summaries: list[dict]) -> MagicMock:
    mail = MagicMock()
    mail.async_mailboxes = AsyncMock(
        return_value=[{"name": n, "special_use": None} for n in ("INBOX", "Archive", "Junk", "Deleted Messages")]
    )
    mail.async_search_uids = AsyncMock(return_value=list(uids))
    mail.async_summaries = AsyncMock(side_effect=lambda box, wanted: [s for s in summaries if s["uid"] in wanted])
    mail.async_set_flags = AsyncMock(return_value={})
    mail.async_move = AsyncMock(return_value={})
    mail.async_delete = AsyncMock(return_value={})
    return mail


async def test_engine_crud_and_persistence(hass: HomeAssistant) -> None:
    mail = _mail([], [])
    engine = RuleEngine(hass, "entry1", mail)
    created = await engine.async_create(
        {
            "name": "Newsletter",
            "conditions": [{"field": "from", "op": "domain", "value": "shop.example.com"}],
            "actions": {"move_to": "Archive", "mark_seen": True},
        }
    )
    assert created["id"] and created["enabled"] is True
    with pytest.raises(RuleError):
        await engine.async_create(
            {
                "name": "bad",
                "conditions": [{"field": "subject", "op": "contains", "value": "x"}],
                "actions": {"move_to": "Nope"},
            }
        )
    updated = await engine.async_update(created["id"], {"name": "News", "actions": {"flag": True}})
    assert updated["name"] == "News"
    assert updated["actions"] == {
        "move_to": "Archive",
        "mark_seen": True,
        "flag": True,
        "delete": False,
        "stop": True,
        "save_attachments": False,
        "attachments_folder": None,
    }
    with pytest.raises(RuleNotFound):
        await engine.async_update("nope", {"name": "x"})
    await hass.async_block_till_done()

    # a fresh engine instance loads the stored rules
    engine2 = RuleEngine(hass, "entry1", mail)
    rules = await engine2.async_list()
    assert [r["name"] for r in rules] == ["News"]
    await engine2.async_delete(created["id"])
    assert await engine2.async_list() == []


async def test_engine_run_batches_actions(hass: HomeAssistant) -> None:
    mail = _mail([11, 12, 13], [NEWSLETTER, BOSS, SPAM])
    engine = RuleEngine(hass, "entry2", mail)
    await engine.async_create(
        {
            "name": "Newsletter",
            "conditions": [{"field": "from", "op": "domain", "value": "shop.example.com"}],
            "actions": {"move_to": "Archive", "mark_seen": True},
        }
    )
    await engine.async_create(
        {
            "name": "Spam",
            "conditions": [{"field": "subject", "op": "regex", "value": r"won .* prize"}],
            "actions": {"delete": True},
        }
    )
    await engine.async_create(
        {
            "name": "Chef",
            "conditions": [{"field": "from", "op": "contains", "value": "chef@firma"}],
            "actions": {"flag": True, "stop": False},
        }
    )

    # first "new" run only sets the baseline
    report = await engine.async_run(scope="new")
    assert report["checked"] == 0 and report["skipped"]
    mail.async_move.assert_not_awaited()

    # dry run over everything: plans but does not execute
    report = await engine.async_run(scope="all", dry_run=True)
    assert report["matched"] == 3
    assert {a["rule"] for a in report["actions"]} == {"Newsletter", "Spam", "Chef"}
    mail.async_move.assert_not_awaited()
    mail.async_delete.assert_not_awaited()

    # real run: batched calls
    report = await engine.async_run(scope="all")
    assert report["matched"] == 3 and not report["errors"]
    mail.async_set_flags.assert_any_await("INBOX", [11], seen=True)
    mail.async_set_flags.assert_any_await("INBOX", [12], flagged=True)
    mail.async_delete.assert_awaited_once_with("INBOX", [13])
    mail.async_move.assert_awaited_once_with("INBOX", [11], "Archive")
    rules = await engine.async_list()
    assert {r["name"]: r["hits"] for r in rules} == {"Newsletter": 1, "Spam": 1, "Chef": 1}

    # new mail arrives: only uids above the baseline are inspected
    mail.async_search_uids.return_value = [11, 12, 13, 14]
    new_spam = dict(SPAM, uid=14)
    mail.async_summaries.side_effect = lambda box, wanted: [
        s for s in [NEWSLETTER, BOSS, SPAM, new_spam] if s["uid"] in wanted
    ]
    mail.async_delete.reset_mock()
    report = await engine.async_run(scope="new")
    assert report["checked"] == 1 and report["matched"] == 1
    mail.async_delete.assert_awaited_once_with("INBOX", [14])


async def test_engine_respects_allow_delete(hass: HomeAssistant) -> None:
    mail = _mail([13], [SPAM])
    engine = RuleEngine(hass, "entry3", mail, allow_delete=False)
    await engine.async_create(
        {
            "name": "Spam",
            "conditions": [{"field": "subject", "op": "contains", "value": "prize"}],
            "actions": {"delete": True},
        }
    )
    report = await engine.async_run(scope="all")
    mail.async_delete.assert_not_awaited()
    assert report["skipped"] and "disabled" in report["skipped"][0]["reason"]


async def test_rule_tools_via_api(hass: HomeAssistant, mock_discover: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=APPLE_ID, data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD}
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.friedafetch.mail.ICloudMail.async_mailboxes",
        new_callable=AsyncMock,
        return_value=[{"name": "INBOX", "special_use": None}, {"name": "Archive", "special_use": None}],
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        ctx = llm.LLMContext(platform="test", context=Context(), language="de", assistant=None, device_id=None)
        api = await llm.async_get_api(hass, LLM_API_ID, ctx)
        names = {t.name for t in api.tools}
        assert {
            "icloud_list_rules",
            "icloud_create_rule",
            "icloud_update_rule",
            "icloud_delete_rule",
            "icloud_run_rules",
        } <= names

        result = await api.async_call_tool(
            llm.ToolInput(
                tool_name="icloud_create_rule",
                tool_args={
                    "name": "Archiv",
                    "conditions": [{"field": "subject", "op": "contains", "value": "rechnung"}],
                    "actions": {"move_to": "Archive"},
                },
            )
        )
        assert result.error is False, result.data
        rule_id = result.data["id"]
        listed = await api.async_call_tool(llm.ToolInput(tool_name="icloud_list_rules", tool_args={}))
        assert [r["id"] for r in listed.data["rules"]] == [rule_id]

        bad = await api.async_call_tool(
            llm.ToolInput(
                tool_name="icloud_create_rule",
                tool_args={
                    "name": "x",
                    "conditions": [{"field": "subject", "op": "contains", "value": "a"}],
                    "actions": {},
                },
            )
        )
        assert bad.error is True and bad.data["code"] == "failed"

        missing = await api.async_call_tool(llm.ToolInput(tool_name="icloud_delete_rule", tool_args={"rule_id": "zzz"}))
        assert missing.error is True and missing.data["code"] == "not_found"


async def test_last_run_persists_and_dry_run_does_not_count(hass: HomeAssistant) -> None:
    mail = _mail([11], [NEWSLETTER])
    engine = RuleEngine(hass, "entry-persist", mail)
    await engine.async_create(
        {
            "name": "News",
            "conditions": [{"field": "from", "op": "domain", "value": "shop.example.com"}],
            "actions": {"mark_seen": True},
        }
    )
    await engine.async_run(scope="all", dry_run=True)
    assert engine.last_run is None  # previews are not a "last run"
    await engine.async_run(scope="all", trigger="auto")
    assert engine.last_run["trigger"] == "auto" and engine.last_run["matched"] == 1
    assert "+" in engine.last_run["finished"] and ":" in engine.last_run["finished"][-6:]  # +02:00, Safari-safe
    engine.note_check("ran", None)
    await hass.async_block_till_done()

    reloaded = RuleEngine(hass, "entry-persist", mail)
    await reloaded.async_load()
    assert reloaded.last_run["trigger"] == "auto"
    assert reloaded.last_run["finished"] == engine.last_run["finished"]


async def test_automation_status(hass: HomeAssistant) -> None:
    from datetime import datetime, timedelta

    engine = RuleEngine(hass, "entry-auto", _mail([], []))
    await engine.async_load()
    assert engine.automation_status()["enabled"] is False
    nxt = datetime.now().astimezone() + timedelta(minutes=5)
    engine.set_automation(True, 5, nxt)
    status = engine.automation_status()
    assert status["enabled"] and status["interval"] == 5 and status["next_run"] == nxt.isoformat(timespec="seconds")
    assert status["idle_reason"] == "no_enabled_rules"
    engine.note_check("no_enabled_rules", nxt + timedelta(minutes=5))
    status = engine.automation_status()
    assert status["last_check"]["result"] == "no_enabled_rules"
    assert status["next_run"] == (nxt + timedelta(minutes=5)).isoformat(timespec="seconds")


async def test_timer_ticks_are_visible(hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={"rules_interval": 5},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    rules = entry.runtime_data.rules
    assert rules.auto_enabled and rules.next_run

    # no rules: the tick is recorded as "nothing to do"
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5, seconds=1))
    await hass.async_block_till_done()
    assert rules.last_check["result"] == "no_enabled_rules"

    # with an enabled rule the tick runs the engine and is marked as automatic
    with (
        patch(
            "custom_components.friedafetch.mail.ICloudMail.async_mailboxes",
            new_callable=AsyncMock,
            return_value=[{"name": "INBOX", "special_use": None}, {"name": "Archive", "special_use": None}],
        ),
        patch(
            "custom_components.friedafetch.mail.ICloudMail.async_search_uids",
            new_callable=AsyncMock,
            return_value=[1, 2],
        ),
    ):
        await rules.async_create(
            {
                "name": "x",
                "conditions": [{"field": "subject", "op": "contains", "value": "a"}],
                "actions": {"move_to": "Archive"},
            }
        )
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=10, seconds=2))
        await hass.async_block_till_done()
    assert rules.last_check["result"] == "ran"
    assert rules.last_run["trigger"] == "auto"

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/rules/list"})
    msg = await ws.receive_json()
    automation = msg["result"]["automation"]
    assert automation["enabled"] and automation["interval"] == 5 and automation["next_run"]
    assert automation["last_check"]["result"] == "ran" and automation["idle_reason"] is None


async def test_run_history_merges_idle_auto_runs(hass: HomeAssistant) -> None:
    mail = _mail([11, 12], [NEWSLETTER, BOSS])
    audit = MagicMock()
    audit.async_record = AsyncMock()
    engine = RuleEngine(hass, "entry-history", mail, audit=audit)
    await engine.async_create(
        {
            "name": "News",
            "conditions": [{"field": "from", "op": "domain", "value": "shop.example.com"}],
            "actions": {"mark_seen": True},
        }
    )
    await engine.async_run(scope="new", trigger="auto")  # baseline
    await engine.async_run(scope="new", trigger="auto")  # idle
    await engine.async_run(scope="new", trigger="auto")  # idle, merged
    await engine.async_run(scope="all", dry_run=True)  # previews are not recorded
    history = engine.history()
    assert len(history) == 1 and history[0]["idle"] and history[0]["runs"] == 3

    # a run with hits starts a new entry and is written to the activity log with its trigger
    mail.async_search_uids.return_value = [11, 12, 13]
    mail.async_summaries.side_effect = lambda box, wanted: [
        s for s in [NEWSLETTER, BOSS, dict(NEWSLETTER, uid=13)] if s["uid"] in wanted
    ]
    await engine.async_run(scope="new", trigger="auto")
    await engine.async_run(scope="new", trigger="auto")  # idle again: new merged entry
    history = engine.history()
    assert [h["runs"] for h in history] == [1, 1, 3]
    assert history[1]["matched"] == 1 and history[1]["rules"] == {"News": 1} and history[1]["trigger"] == "auto"
    audit.async_record.assert_awaited_once()
    kwargs = audit.async_record.await_args.kwargs
    assert kwargs["client"] == "rules (auto)" and kwargs["details"]["trigger"] == "auto"

    # manual runs are never merged and the history survives a reload
    await engine.async_run(scope="new")
    await engine.async_run(scope="new")
    assert [h["trigger"] for h in engine.history()][:2] == ["manual", "manual"]
    await hass.async_block_till_done()
    reloaded = RuleEngine(hass, "entry-history", mail)
    await reloaded.async_load()
    assert len(reloaded.history(200)) == 5
    await reloaded.async_clear_history()
    assert reloaded.history() == []


async def test_run_history_records_errors(hass: HomeAssistant) -> None:
    from custom_components.friedafetch.mail import MailError

    mail = _mail([11], [NEWSLETTER])
    mail.async_search_uids.side_effect = MailError("IMAP timeout")
    audit = MagicMock()
    audit.async_record = AsyncMock()
    engine = RuleEngine(hass, "entry-history-err", mail, audit=audit)
    await engine.async_create(
        {
            "name": "News",
            "conditions": [{"field": "from", "op": "domain", "value": "shop.example.com"}],
            "actions": {"mark_seen": True},
        }
    )
    await engine.async_run(scope="new", trigger="auto")
    await engine.async_run(scope="new", trigger="auto")
    history = engine.history()
    assert len(history) == 2 and history[0]["errors"] == ["IMAP timeout"] and not history[0]["idle"]
    # failed automatic runs show up in the activity log even without hits
    assert audit.async_record.await_count == 2
    assert audit.async_record.await_args.kwargs["result"] == "error"


async def test_history_websocket(hass: HomeAssistant, mock_discover: AsyncMock, hass_ws_client) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=APPLE_ID,
        data={CONF_APPLE_ID: APPLE_ID, CONF_APP_PASSWORD: APP_PASSWORD},
        options={"rules_auto": False},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    rules = entry.runtime_data.rules
    rules._history = [
        {"id": 1, "trigger": "auto", "matched": 0, "idle": True, "runs": 4},
        {"id": 2, "trigger": "manual", "matched": 2, "idle": False, "runs": 1},
    ]
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "friedafetch/rules/history", "entry_id": entry.entry_id, "limit": 1})
    msg = await ws.receive_json()
    assert msg["success"] and msg["result"]["total"] == 2
    assert [r["id"] for r in msg["result"]["runs"]] == [2]
    await ws.send_json({"id": 2, "type": "friedafetch/rules/history/clear", "entry_id": entry.entry_id})
    msg = await ws.receive_json()
    assert msg["success"] and rules.history() == []
