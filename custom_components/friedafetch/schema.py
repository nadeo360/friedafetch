"""Schema library shim: Home Assistant 2026.10+ uses probatio, older releases voluptuous."""

from __future__ import annotations

try:  # pragma: no cover - depends on the HA version
    import probatio as vol  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    import voluptuous as vol  # type: ignore[no-redef]

__all__ = ["vol"]
