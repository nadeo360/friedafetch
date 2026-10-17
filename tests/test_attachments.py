"""Storing attachments safely."""

from pathlib import Path

import pytest

from custom_components.friedafetch.attachments import (
    AttachmentError,
    safe_name,
    safe_subfolder,
    store_attachments,
)

PDF = b"%PDF-1.7 " + b"x" * 1000


def test_safe_names() -> None:
    assert safe_name("../../etc/passwd") == "etc_passwd"
    assert safe_name("  .hidden ") == "hidden"
    assert safe_name("Rechnung März 2026.pdf") == "Rechnung März 2026.pdf"
    assert safe_subfolder("../Belege/./Strom/..") == ["Belege", "Strom"]
    assert safe_subfolder("/abs/path") == ["abs", "path"]


def test_store_attachments(tmp_path: Path) -> None:
    files = [
        ("Rechnung.pdf", "application/pdf", PDF),
        ("logo.png", "image/png", b"\x89PNG" + b"0" * 100),  # small image: skipped
        ("leer.txt", "text/plain", b""),
    ]
    result = store_attachments(tmp_path, files, subfolder="Belege", month="2026-10", prefix="2026-10-17_shop")
    assert [r["status"] for r in result] == ["saved", "skipped", "skipped"]
    assert result[0]["path"] == "Belege/2026-10/2026-10-17_shop_Rechnung.pdf"
    assert (tmp_path / result[0]["path"]).read_bytes() == PDF
    # same content again: not duplicated; different content with the same name: numbered
    again = store_attachments(tmp_path, files[:1], subfolder="Belege", month="2026-10", prefix="2026-10-17_shop")
    assert again[0]["status"] == "exists"
    other = store_attachments(
        tmp_path,
        [("Rechnung.pdf", "application/pdf", PDF + b"!")],
        subfolder="Belege",
        month="2026-10",
        prefix="2026-10-17_shop",
    )
    assert other[0]["path"].endswith("_Rechnung-1.pdf")
    # type filter
    only_png = store_attachments(tmp_path, files[:2], subfolder=None, month="2026-10", prefix="", types=["png"])
    assert [r["status"] for r in only_png] == ["skipped", "saved"]


def test_store_attachments_stays_inside_base(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    result = store_attachments(
        base, [("a.pdf", "application/pdf", PDF)], subfolder="../../outside", month="..", prefix=""
    )
    stored = (base / result[0]["path"]).resolve()
    assert base.resolve() in stored.parents
    with pytest.raises(AttachmentError):
        # a symlink inside the base that points outside is refused
        (base / "link").symlink_to(tmp_path)
        store_attachments(base, [("a.pdf", "application/pdf", PDF)], subfolder="link", month="2026-10", prefix="")
