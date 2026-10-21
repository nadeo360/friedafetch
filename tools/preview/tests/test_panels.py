"""Frieda's panel in the browser: every scenario loads cleanly, and what broke before stays fixed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

INDEX = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def _scenarios(panel: str) -> list[str]:
    """The scenarios of the preview's menu (index.html), so new ones are tested without listing them twice."""
    block = INDEX.split(f"    {panel}: [", 1)[1].split("\n    ],", 1)[0]
    return re.findall(r'\["([^"]*)",', block)


SCENARIOS = [("frieda", q) for q in _scenarios("frieda")]


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


@pytest.mark.parametrize("name", ["frieda"])
def test_dark_theme_loads_cleanly(open_panel, name: str) -> None:
    panel = open_panel(name, dark=True, phone=True)
    assert panel.problems == []
    assert panel.page.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1


def test_tabs_follow_the_arrow_keys(open_panel) -> None:
    panel = open_panel("frieda")
    selected = panel.js(
        'const tab = root.querySelector(\'[role="tab"][aria-selected="true"]\'); tab.focus();'
        "tab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })); await wait(400);"
        'return [root.querySelector(\'[role="tab"][aria-selected="true"]\').dataset.tab, root.activeElement?.dataset.tab];'
    )
    assert selected == ["approvals", "approvals"]


def test_frieda_counts_pending_approvals_on_its_tab(open_panel) -> None:
    panel = open_panel("frieda", "approvals=1")
    assert panel.text('[data-tab="approvals"] .tbadge [aria-hidden]') == "2"
