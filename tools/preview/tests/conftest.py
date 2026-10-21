"""Browser tests of Frieda's panel against the dev preview (example data, no Home Assistant needed); see harness.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import open_panel, site  # noqa: E402, F401 - the fixtures of the shared harness
