"""Both panels in the browser: every scenario loads cleanly, and what broke before stays fixed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

INDEX = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def _scenarios(panel: str) -> list[str]:
    """The scenarios of the preview's menu (index.html), so new ones are tested without listing them twice."""
    block = INDEX.split(f"    {panel}: [", 1)[1].split("\n    ],", 1)[0]
    return re.findall(r'\["([^"]*)",', block)


SCENARIOS = [("frieda", q) for q in _scenarios("frieda")] + [("postfach", q) for q in _scenarios("postfach")]


@pytest.mark.parametrize("phone", [False, True], ids=["desktop", "phone"])
@pytest.mark.parametrize(("name", "query"), SCENARIOS, ids=[f"{n}:{q or 'start'}" for n, q in SCENARIOS])
def test_scenario_loads_cleanly(open_panel, name: str, query: str, phone: bool) -> None:
    """No script error, no missing icon, no error box, and nothing wider than a phone."""
    panel = open_panel(name, query, phone=phone)
    assert panel.problems == []
    assert panel.page.evaluate("document.body.dataset.err || null") is None
    assert panel.count(".content .error") == 0, panel.text(".content .error")
    if phone:
        overflow = panel.page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"{overflow}px wider than the screen"


@pytest.mark.parametrize("name", ["frieda", "postfach"])
def test_dark_theme_loads_cleanly(open_panel, name: str) -> None:
    panel = open_panel(name, dark=True, phone=True)
    assert panel.problems == []
    assert panel.page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1


# ------------------------------------------------------------------ re-rating
def test_rerate_from_an_opened_mail_shows_progress(open_panel) -> None:
    panel = open_panel("postfach", "tick=2000")
    panel.click('.rtop [data-action="tl-rerate"]')
    panel.click('[data-action="confirm-yes"]', 600)
    assert panel.text(".rhead .rr") == "wird bewertet"
    assert panel.count(".mlist .rr") == 1
    assert "Neu bewerten: 0 von 1" in panel.text(".lhead .batch")


def test_rerate_from_the_ai_log_shows_progress_too(open_panel) -> None:
    """A mail opened outside the activity (AI log, runs, a link) goes the same way (1.0.22)."""
    panel = open_panel("postfach", "tab=aiu&tick=2000")
    panel.click('[data-action="aiu-mail"]', 1200)
    panel.click('.sheet [data-action="tl-rerate"]')
    panel.click('[data-action="confirm-yes"]', 600)
    assert panel.text(".sheet .rr") == "wird bewertet"
    assert "Neu bewerten" in panel.text('section[data-widget="batch"] .batch')


def test_rerating_adds_to_the_timeline(open_panel) -> None:
    panel = open_panel("postfach", "tick=200")
    panel.click('.rtop [data-action="tl-rerate"]')
    panel.click('[data-action="confirm-yes"]', 1500)
    steps = panel.js("return [...root.querySelectorAll('.reader ol.tl li .what strong')].map((n) => n.textContent);")
    assert steps[-1].startswith("Erneut bewertet")


def test_a_closed_result_stays_closed_after_reopening(open_panel) -> None:
    """Closing "rated again" is remembered per user (1.0.23)."""
    panel = open_panel("postfach", "tick=200")
    panel.click('.rtop [data-action="tl-rerate"]')
    panel.click('[data-action="confirm-yes"]', 1200)
    panel.click('[data-action="batch-hide"]', 500)
    reopened = panel.js(
        "const hass = el._hass; el.remove(); const again = document.createElement('friedafetch-mail-panel');"
        "again.narrow = false; again.panel = {}; document.body.appendChild(again); again.hass = hass; await wait(2000);"
        "return { loaded: !!again.shadowRoot.querySelector('.mlist'), notice: !!again.shadowRoot.querySelector('.batch') };"
    )
    assert reopened == {"loaded": True, "notice": False}


def test_rerate_waits_for_the_hourly_limit_and_goes_on(open_panel) -> None:
    """At the hourly limit the batch waits for the next hour instead of stopping (1.0.24)."""
    panel = open_panel("postfach", "waitafter=1&tick=400")
    panel.click('[data-action="act-pick"]')
    panel.click('[data-action="act-all"]')
    panel.click('.actbar [data-action="act-rerate"]')
    panel.click('[data-action="confirm-yes"]', 100)
    panel.js("for (let i = 0; i < 50 && !root.querySelector('.lhead .batch.wait'); i++) await wait(100);")
    waiting = panel.text(".lhead .batch.wait") or ""
    assert "Stundenlimit erreicht" in waiting and "von selbst weiter" in waiting
    panel.js("for (let i = 0; i < 100 && !root.querySelector('.lhead .batch.done'); i++) await wait(100);")
    assert panel.count(".lhead .batch.wait") == 0
    assert "Neu bewertet" in panel.text(".lhead .batch")


# ------------------------------------------------------------------ activity
def test_unsure_ratings_have_their_own_view(open_panel) -> None:
    panel = open_panel("postfach")
    panel.click('.rail [data-action="act-view"][data-v="unsure"]', 600)
    assert panel.text(".lhead h2") == "Unsicher"
    assert panel.count(".mlist li.m") == 2 == panel.count(".mlist .uns")


def test_read_and_flagged_as_the_mailbox_has_it(open_panel) -> None:
    """Unread mails stand out, flagged ones carry a flag; the opened mail says it too (CONDSTORE sync)."""
    panel = open_panel("postfach")
    assert panel.count(".mlist li.m.unread") == 3 and panel.count(".mlist li.m.unread .ud") == 3
    assert panel.count(".mlist li.m .fl") >= 1
    label = panel.js("return root.querySelector('.mlist li.m.unread .mitem').getAttribute('aria-label');")
    assert label.endswith("ungelesen") or "ungelesen, markiert" in label
    chips = panel.text(".rhead .chips")
    assert "ungelesen" in chips and "markiert" in chips  # the first mail: personal, still unread


def test_a_mail_that_left_the_inbox_keeps_its_last_state(open_panel) -> None:
    """Moved away on another device: read / flagged stay as last seen instead of vanishing (1.0.26)."""
    panel = open_panel("postfach")
    flagged = panel.js(
        "const li = [...root.querySelectorAll('.mlist li.m')].find((l) => l.textContent.includes('Elternabend'));"
        "return !!li.querySelector('.fl');"
    )
    assert flagged


def test_views_for_unread_and_flagged(open_panel) -> None:
    panel = open_panel("postfach")
    panel.click('.rail [data-action="act-view"][data-v="unread"]', 600)
    assert panel.text(".lhead h2") == "Ungelesen" and panel.count(".mlist li.m") == panel.count(".mlist li.m.unread")
    panel.click('.rail [data-action="act-view"][data-v="flagged"]', 600)
    assert panel.count(".mlist li.m") == panel.count(".mlist li.m .fl") > 0


def test_a_rule_from_the_open_mail(open_panel) -> None:
    panel = open_panel("postfach")
    panel.click('.rtop [data-action="rule-from-mail"]', 600)
    assert panel.js("return el._s.tab;") == "rules"
    assert panel.js("return root.querySelector('#rule-name, [id^=\"rule-name\"]')?.value || el._s.editing.name;") == (
        "Mails von Erika Mustermann"
    )
    assert panel.js("return el._s.editing.conditions[0].value;") == "erika@example.com"


def test_acting_on_the_open_mail(open_panel) -> None:
    """Archive from the reading pane: the timeline shows it; flag with the keyboard (s)."""
    panel = open_panel("postfach")
    panel.click('.rtop [data-action="mail-act"][data-v="archive"]', 1200)
    steps = panel.js("return [...root.querySelectorAll('.reader ol.tl li .what strong')].map((n) => n.textContent);")
    assert steps[-1] == "Von dir archiviert"
    assert panel.count('.rtop [data-action="mail-act"][data-v="inbox"]') == 1  # now it offers the way back
    panel.js("root.querySelector('.mlist [data-action=\"act-open\"]').focus();")
    panel.page.keyboard.press("j")
    panel.js("await wait(600);")
    first = panel.js("return el._s.act.open;")
    assert first != "<test-frieda@example>"
    flagged = panel.js("return !!el._actItem(el._s.act.open).state?.flagged;")
    panel.page.keyboard.press("s")
    panel.js("await wait(900);")
    assert panel.js("return !!el._actItem(el._s.act.open).state?.flagged;") is not flagged


def test_the_text_of_a_mail_on_request(open_panel) -> None:
    panel = open_panel("postfach", "textslow=50")
    panel.click('[data-action="mail-text"]', 500)
    assert "Beispieltext der Vorschau" in panel.text(".mtext .body")


def test_a_correction_asks_for_the_new_categorys_action(open_panel) -> None:
    panel = open_panel("postfach")
    panel.js(
        "const s = root.querySelector('.reader select.catsel'); s.value = 'Newsletter & Werbung';"
        "s.dispatchEvent(new Event('change')); await wait(700);"
    )
    assert "Newsletter & Werbung" in panel.text(".askline")
    panel.click('[data-action="apply-yes"]', 900)
    assert panel.count(".askline") == 0 and panel.count(".content .error") == 0


def test_accuracy_check_with_another_ai_entity(open_panel) -> None:
    panel = open_panel("postfach", "tab=ai&aislow=300")
    panel.js(
        "const s = root.querySelector('[data-action=\"check-entity\"]'); s.value = 'ai_task.lokales_modell';"
        "s.dispatchEvent(new Event('change'));"
    )
    panel.click('[data-action="ai-check"]', 900)
    result = panel.text(".check-res")
    assert "1 von 1 richtig (100 %)" in result and "lokales_modell" in result


def test_picking_a_day_selects_its_mails(open_panel) -> None:
    panel = open_panel("postfach", "volume=1")
    panel.click('[data-action="act-pick"]')
    panel.click('.daypicks [data-action="act-day"]', 500)
    today = panel.js("return Number(root.querySelector('.daypicks .seg .n').textContent);")
    assert panel.text(".actbar span") == f"{today} ausgewählt"
    assert panel.text(".pickinfo strong") == f"{today} Mails ausgewählt"


def test_rule_mails_cannot_be_picked(open_panel) -> None:
    panel = open_panel("postfach")
    panel.click('[data-action="act-pick"]')
    label = panel.js(
        "return root.querySelector('[data-action=\"act-open\"][aria-disabled=\"true\"]').getAttribute('aria-label');"
    )
    assert "von einer Regel erledigt" in label


def test_the_list_loads_more_while_scrolling(open_panel) -> None:
    panel = open_panel("postfach", "volume=1")
    assert panel.count("li.m") == 50
    panel.js("const s = root.querySelector('.lscroll'); s.scrollTop = s.scrollHeight; await wait(800);")
    assert panel.count("li.m") == 100


def test_opening_a_mail_looks_up_where_it_is(open_panel) -> None:
    panel = open_panel("postfach", "scene=loc")
    assert panel.text(".loc .lt").startswith("Liegt jetzt in Archiv")
    assert "verschoben" in panel.text(".loc .note")


# ------------------------------------------------------------------ dropdowns and touch
def test_a_dropdown_does_not_get_the_focus_back_on_touch(open_panel, browser_name: str) -> None:
    """On phones a focused dropdown opens again: after a choice it must not be focused (1.0.23)."""
    panel = open_panel("postfach", phone=True)
    coarse = panel.page.evaluate("matchMedia('(pointer: coarse)').matches")
    if not coarse:
        pytest.skip(f"{browser_name} does not report a touch pointer here")
    result = panel.js(
        "const sel = root.querySelector('[data-action=\"act-viewsel\"]'); sel.focus(); sel.value = 'k:ai';"
        "sel.dispatchEvent(new Event('change', { bubbles: true })); await wait(800);"
        "return { view: root.querySelector('[data-action=\"act-viewsel\"]').value, focused: root.activeElement?.tagName || null };"
    )
    assert result == {"view": "k:ai", "focused": None}


def test_background_results_wait_for_an_open_dropdown(open_panel) -> None:
    panel = open_panel("postfach", "locslow=1500")
    panel.js("[...root.querySelectorAll('[data-action=\"act-open\"]')][5].click(); await wait(700);")
    kept = panel.js(
        "const sel = root.querySelector('.catsel'); sel.focus(); await wait(2000); const kept = sel.isConnected;"
        "sel.blur(); await wait(900); return { kept, after: root.querySelector('.loc .lt').textContent };"
    )
    assert kept["kept"] is True
    assert kept["after"].startswith("Liegt jetzt in")


# ------------------------------------------------------------------ category assistant
def test_the_assistant_turns_words_into_a_category(open_panel) -> None:
    panel = open_panel("postfach", "tab=ai")
    panel.click('[data-action="assist-open"]')
    assert panel.js("return root.activeElement?.id;") == "as-input"
    panel.click('[data-action="assist-chip"]', 1400)
    assert panel.js("return root.querySelector('#as-name').value;") == "Steuer & Finanzamt"
    assert panel.js("return root.querySelector('#as-move').value;") == "Archive"
    panel.click('[data-action="assist-apply"]', 600)
    assert panel.count(".sheet.assist") == 0
    assert "Steuer & Finanzamt" in panel.js(
        "return [...root.querySelectorAll('.ai-cat strong')].map((n) => n.textContent);"
    )


# ------------------------------------------------------------------ tabs
def test_tabs_follow_the_arrow_keys(open_panel) -> None:
    panel = open_panel("postfach")
    selected = panel.js(
        'const tab = root.querySelector(\'[role="tab"][aria-selected="true"]\'); tab.focus();'
        "tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })); await wait(400);"
        'return [root.querySelector(\'[role="tab"][aria-selected="true"]\').dataset.tab, root.activeElement?.dataset.tab];'
    )
    assert selected == ["rules", "rules"]


def test_frieda_counts_pending_approvals_on_its_tab(open_panel) -> None:
    panel = open_panel("frieda", "approvals=1")
    assert panel.text('[data-tab="approvals"] .tbadge [aria-hidden]') == "2"
