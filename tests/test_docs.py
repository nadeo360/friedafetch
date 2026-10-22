"""The architecture documentation: its diagrams render, and English and German say the same."""

from __future__ import annotations

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def _blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, re.S)


def test_diagrams_have_no_statement_separator() -> None:
    """A ";" ends a Mermaid statement: text after it breaks the diagram (arc42 6.5 did not render)."""
    for name in ("architecture.md", "architecture.de.md"):
        for i, block in enumerate(_blocks((DOCS / name).read_text(encoding="utf-8"))):
            bad = [line.strip() for line in block.splitlines() if ";" in line]
            assert not bad, f"{name}, diagram {i + 1}: {bad}"


def test_both_languages_alike() -> None:
    en = (DOCS / "architecture.md").read_text(encoding="utf-8")
    de = (DOCS / "architecture.de.md").read_text(encoding="utf-8")
    assert len(_blocks(en)) == len(_blocks(de))
    for row in (r"^\| ADR-\d+", r"^\| Q\d+[a-z]?", r"^#{2,3} "):
        assert len(re.findall(row, en, re.M)) == len(re.findall(row, de, re.M)), row
    state = re.compile(r"Frieda \d+\.\d+\.\d+, Frieda Postfach \d+\.\d+\.\d+")
    assert state.search(en).group(0) == state.search(de).group(0)  # type: ignore[union-attr]
