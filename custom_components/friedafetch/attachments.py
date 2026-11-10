"""Store e-mail attachments below their folder (receipts, invoices): by default one of its own in the configuration
folder, which no media source shows."""

from __future__ import annotations

import hashlib
import re
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any

from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_ATTACHMENTS_DIR,
    DEFAULT_ATTACHMENTS_DIR,
    DOMAIN,
    ISSUE_ATTACHMENTS_IN_MEDIA,
    LEGACY_ATTACHMENTS_SUBDIR,
)

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
MIN_IMAGE_BYTES = 20 * 1024  # smaller images are usually logos or signatures
_UNSAFE = re.compile(r"[^\w.\- ]+", re.UNICODE)


class AttachmentError(Exception):
    """Attachments cannot be stored."""


def safe_name(value: str, fallback: str = "attachment", max_len: int = 80) -> str:
    """A single, harmless path segment."""
    name = _UNSAFE.sub("_", value or "").strip(" ._")
    name = re.sub(r"_+", "_", name)
    return (name or fallback)[:max_len]


def safe_subfolder(value: str | None) -> list[str]:
    """Split a user-given subfolder into safe segments (no '..', no absolute paths)."""
    if not value:
        return []
    segments = [s for s in re.split(r"[\\/]+", value) if s and s not in (".", "..")]
    return [safe_name(s, "folder", 60) for s in segments][:4]


def wanted(filename: str, content_type: str, size: int, types: list[str] | None) -> str | None:
    """Return a skip reason, or None when the attachment should be stored."""
    if size == 0:
        return "empty"
    if size > MAX_ATTACHMENT_BYTES:
        return "too_large"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if types:
        allowed = {t.lower().lstrip(".") for t in types}
        if ext not in allowed and content_type.split("/")[-1].lower() not in allowed:
            return "type"
    elif content_type.startswith("image/") and size < MIN_IMAGE_BYTES:
        return "small_image"
    return None


def store_attachments(
    base: Path,
    files: list[tuple[str, str, bytes]],
    *,
    subfolder: str | None,
    month: str,
    prefix: str,
    types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Write attachments to base/subfolder/month (blocking: run in the executor)."""
    base = base.resolve()
    target = base.joinpath(*safe_subfolder(subfolder), safe_name(month, "undated")).resolve()
    if base != target and base not in target.parents:
        raise AttachmentError("Target folder is outside the attachment folder")
    results: list[dict[str, Any]] = []
    created = False
    for filename, ctype, payload in files:
        reason = wanted(filename, ctype, len(payload), types)
        if reason:
            results.append({"filename": filename, "status": "skipped", "reason": reason, "size": len(payload)})
            continue
        if not created:
            target.mkdir(parents=True, exist_ok=True)
            created = True
        stem = safe_name(f"{prefix}_{Path(filename).stem}" if prefix else Path(filename).stem)
        suffix = safe_name(Path(filename).suffix.lstrip("."), "", 10)
        digest = hashlib.sha256(payload).hexdigest()
        path = target / (f"{stem}.{suffix}" if suffix else stem)
        n = 1
        status = "saved"
        while path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() == digest:
                status = "exists"
                break
            path = target / (f"{stem}-{n}.{suffix}" if suffix else f"{stem}-{n}")
            n += 1
        if status == "saved":
            path.write_bytes(payload)
        results.append(
            {"filename": filename, "status": status, "path": str(path.relative_to(base)), "size": len(payload)}
        )
    return results


class AttachmentStore:
    """Fetches a message and stores its attachments below ``base`` (used by the tool and the rules)."""

    def __init__(self, hass: Any, mail: Any, base: Path) -> None:
        self._hass = hass
        self._mail = mail
        self.base = base

    async def async_save(
        self, mailbox: str, uid: int, folder: str | None = None, types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        from email.utils import parseaddr  # noqa: PLC0415

        from .mail import header_text, iter_attachments, parse_date_header  # noqa: PLC0415

        _, msg = await self._mail.async_fetch_raw(mailbox, uid)
        files = iter_attachments(msg)
        if not files:
            return []
        when = parse_date_header(header_text(msg, "Date"))
        sender = parseaddr(header_text(msg, "From") or "")[1]
        sender_part = sender.split("@")[-1].split(".")[-2] if sender.count(".") else sender.split("@")[0]
        prefix = f"{when:%Y-%m-%d}_{sender_part}" if when else sender_part
        month = f"{when:%Y-%m}" if when else "undated"
        return await self._hass.async_add_executor_job(
            lambda: store_attachments(self.base, files, subfolder=folder, month=month, prefix=prefix, types=types)
        )


# ------------------------------------------------------- the old default folder (<media>/frieda, until 2.0.27)
def legacy_folder(hass: Any) -> Path:
    media = (hass.config.media_dirs or {}).get("local") or hass.config.path("media")
    return Path(media) / LEGACY_ATTACHMENTS_SUBDIR


def has_files(folder: Path) -> bool:
    """Whether a folder holds any file (blocking)."""
    return folder.is_dir() and any(p.is_file() and not p.is_symlink() for p in folder.rglob("*"))


def move_tree(source: Path, target: Path) -> int:
    """Move stored attachments into another folder (blocking). A file that is there already in the same form is not
    kept twice; another one of the same name gets a number. Links are left alone."""
    moved = 0
    for path in sorted(p for p in source.rglob("*") if p.is_file() and not p.is_symlink()):
        dest = target / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if dest.read_bytes() == path.read_bytes():
                path.unlink()
                continue
            n = 1
            while (numbered := dest.with_name(f"{dest.stem}-{n}{dest.suffix}")).exists():
                n += 1
            dest = numbered
        shutil.move(path, dest)
        moved += 1
    for folder in sorted((p for p in source.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        with suppress(OSError):
            folder.rmdir()  # only empty ones
    with suppress(OSError):
        source.rmdir()
    return moved


def entries_on_default(hass: Any) -> list[Any]:
    """The Frieda accounts without a chosen attachment folder (they used the old default)."""
    return [e for e in hass.config_entries.async_entries(DOMAIN) if not e.options.get(CONF_ATTACHMENTS_DIR)]


async def async_check_legacy_attachments(hass: Any) -> None:
    """Attachments stored before 2.0.28 in <media>/frieda are visible to every user in the media browser: a repair
    offers to move them into Frieda's own folder, or to keep that folder on purpose."""
    old = legacy_folder(hass)
    if entries_on_default(hass) and await hass.async_add_executor_job(has_files, old):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ATTACHMENTS_IN_MEDIA,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_ATTACHMENTS_IN_MEDIA,
            translation_placeholders={"folder": str(old), "target": hass.config.path(DEFAULT_ATTACHMENTS_DIR)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_ATTACHMENTS_IN_MEDIA)
