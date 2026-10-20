#!/usr/bin/env python3
"""Builds the dev preview of the Frieda and Frieda Postfach panels with example data.

The panels are taken unchanged from the working trees of both repositories; only the absolute import of Frieda UI
(/friedafetch_static/ui.js, served by Home Assistant) is pointed at the copy next to it. The result in dist/ is a
static site: serve it locally with

    python3 -m http.server -d tools/preview/dist 8767     # then open http://127.0.0.1:8767/local.html

or publish dist/ as a page. Usage: python3 tools/preview/build.py [--postfach ../friedafetch-mail] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRIEDA = HERE.parent.parent
PANEL_FILES = ("panel.js", "styles.js", "i18n.js", "icon.svg")


def git_state(repo: Path) -> dict[str, object]:
    """Branch, commit and the latest commit subjects of a repository."""

    def git(*args: str) -> str:
        # fixed git commands on the two working trees (no user input)
        cmd = ["git", "-C", str(repo), *args]
        return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603

    log = git("log", "-8", "--format=%h%x09%cI%x09%s")
    return {
        "branch": git("branch", "--show-current"),
        "commit": git("rev-parse", "--short", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "log": [
            dict(zip(("commit", "time", "subject"), line.split("\t", 2), strict=False)) for line in log.splitlines()
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--postfach", type=Path, default=FRIEDA.parent / "friedafetch-mail")
    parser.add_argument("--out", type=Path, default=HERE / "dist")
    args = parser.parse_args()
    out: Path = args.out
    shutil.rmtree(out, ignore_errors=True)
    (out / "frieda").mkdir(parents=True)
    (out / "postfach").mkdir()

    frieda_src = FRIEDA / "custom_components" / "friedafetch" / "frontend"
    for name in (*PANEL_FILES, "ui.js"):
        shutil.copy2(frieda_src / name, out / "frieda" / name)

    postfach_src = args.postfach / "custom_components" / "friedafetch_mail" / "frontend"
    for name in PANEL_FILES:
        shutil.copy2(postfach_src / name, out / "postfach" / name)
    panel = out / "postfach" / "panel.js"
    text = panel.read_text(encoding="utf-8")
    if "/friedafetch_static/ui.js" not in text:
        raise SystemExit("Frieda Postfach no longer imports /friedafetch_static/ui.js – update build.py")
    panel.write_text(text.replace("/friedafetch_static/ui.js", "../frieda/ui.js"), encoding="utf-8")

    # one key per build for every panel import, so browsers never keep files of an older build
    build = format(int(datetime.now().timestamp()), "x")
    versions = {
        "__FRIEDA_VERSION__": json.loads((FRIEDA / "custom_components" / "friedafetch" / "manifest.json").read_text())[
            "version"
        ],
        "__POSTFACH_VERSION__": json.loads(
            (args.postfach / "custom_components" / "friedafetch_mail" / "manifest.json").read_text()
        )["version"],
    }
    # the example backends (mock-*.js) and clickable drafts of ideas that are not in the panels yet (draft-*.js)
    pages = [HERE / "frieda.html", HERE / "postfach.html", *HERE.glob("mock-*.js"), *HERE.glob("draft-*.js")]
    for src in pages:
        text = src.read_text(encoding="utf-8").replace("__BUILD__", build)
        for key, value in versions.items():  # the example data shows the versions of the working trees
            text = text.replace(key, value)
        (out / src.name).write_text(text, encoding="utf-8")
    page = (HERE / "index.html").read_text(encoding="utf-8")
    (out / "index.html").write_text(page, encoding="utf-8")
    # the published page gets its document skeleton from the host; locally it needs one
    (out / "local.html").write_text(
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
        f"{page}</body></html>",
        encoding="utf-8",
    )

    state = {
        "built": datetime.now().astimezone().isoformat(timespec="seconds"),
        "frieda": git_state(FRIEDA),
        "postfach": git_state(args.postfach),
    }
    (out / "version.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"dev preview in {out}: Frieda {state['frieda']['commit']}, Postfach {state['postfach']['commit']}")


if __name__ == "__main__":
    main()
