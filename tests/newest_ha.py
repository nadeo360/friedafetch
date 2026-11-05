"""Early pytest plugin (`-p tests.newest_ha`) for the daily run against the newest Home Assistant.

pytest-homeassistant-custom-component follows Home Assistant with a delay and pins the version it was made for, so
that run installs the newest release over it. Importing Home Assistant first gives it the chance to redirect what it
replaced (httpx in 2026.11); what moved inside it for the plugin is put back here.
"""

from __future__ import annotations

import homeassistant.components.logger as logger

if not hasattr(logger, "_clear_logger_overwrites"):  # moved to logger.helpers in 2026.11
    from homeassistant.components.logger.helpers import _clear_logger_overwrites

    logger._clear_logger_overwrites = _clear_logger_overwrites  # noqa: SLF001
