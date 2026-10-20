"""Browser tests of both panels against the dev preview (example data, no Home Assistant needed).

The preview is built once per run (both working trees: this repository and Frieda Postfach next to it, or the path in
POSTFACH_DIR) and served on a free local port. pytest-playwright provides the browsers; run them with
``--browser chromium --browser webkit``. WebKit is the engine of Safari and of the Home Assistant app on iPhone and iPad.
"""

from __future__ import annotations

import functools
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, Page

HERE = Path(__file__).resolve().parent
PREVIEW = HERE.parent
POSTFACH = Path(os.environ.get("POSTFACH_DIR") or PREVIEW.parent.parent.parent / "friedafetch-mail")

DESKTOP = {"viewport": {"width": 1400, "height": 900}}
PHONE = {"viewport": {"width": 393, "height": 852}, "device_scale_factor": 3, "has_touch": True}


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture(scope="session")
def site(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """The built preview, served locally; yields its base URL."""
    out = tmp_path_factory.mktemp("preview")
    build = [sys.executable, str(PREVIEW / "build.py"), "--postfach", str(POSTFACH), "--out", str(out)]
    subprocess.run(build, check=True)  # noqa: S603 - this repository's own build script
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


class Panel:
    """One loaded panel page: its problems (script errors, missing icons) and helpers for its shadow DOM."""

    def __init__(self, page: Page, host: str) -> None:
        self.page = page
        self.host = host
        self.problems: list[str] = []
        page.on("pageerror", lambda err: self.problems.append(f"page error: {err}"))
        page.on("console", lambda msg: msg.type == "error" and self.problems.append(f"console: {msg.text}"))

    def js(self, body: str, arg: Any = None) -> Any:
        """Runs body with `root` (the panel's shadow root), `el` (the panel) and `arg`; may await."""
        return self.page.evaluate(
            f"async (arg) => {{ const el = document.querySelector('{self.host}'); const root = el.shadowRoot; "
            f"const wait = (ms = 300) => new Promise((r) => setTimeout(r, ms)); {body} }}",
            arg,
        )

    def click(self, selector: str, wait: int = 300) -> None:
        self.js(f"root.querySelector({selector!r}).click(); await wait({wait});")

    def text(self, selector: str) -> str:
        return self.js(f"return root.querySelector({selector!r})?.textContent.trim() ?? null;")

    def count(self, selector: str) -> int:
        return self.js(f"return root.querySelectorAll({selector!r}).length;")


@pytest.fixture
def open_panel(browser: Browser, site: str) -> Any:
    """open_panel("postfach", "scene=pick", phone=False, dark=False) -> Panel, ready to use."""
    contexts = []

    def _open(name: str, query: str = "", *, phone: bool = False, dark: bool = False) -> Panel:
        context = browser.new_context(**(PHONE if phone else DESKTOP))
        contexts.append(context)
        page = context.new_page()
        panel = Panel(page, "friedafetch-panel" if name == "frieda" else "friedafetch-mail-panel")
        params = "&".join(p for p in (query, "dark=1" if dark else "") if p)
        page.goto(f"{site}/{name}.html?{params}")
        page.wait_for_function("document.title === 'ready'", timeout=20000)
        return panel

    yield _open
    for context in contexts:
        context.close()
