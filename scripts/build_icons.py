#!/usr/bin/env python3
"""Render all icon and logo variants from the SVG sources.

Sources (edit these, then run the script):
    assets/icon.svg        square app icon
    assets/logo.svg        wide logo for light backgrounds
    assets/logo-dark.svg   wide logo for dark backgrounds

Outputs:
    assets/icon.png (256), assets/icon@2x.png (512)
    assets/logo.png (1040 wide), assets/logo@2x.png (2080), assets/logo-dark.png
    custom_components/friedafetch/brand/{icon,icon@2x,logo,logo@2x,dark_logo,dark_logo@2x}.png
        (Home Assistant >= 2026.3 serves these itself via /api/brands/integration/friedafetch/...;
         icon 256/512 px, logo 128/256 px high, same conventions as the former brands repository)
    custom_components/friedafetch/frontend/icon.svg   copy of the icon served next to the panel

Usage:
    python scripts/build_icons.py            # (re)build everything
    python scripts/build_icons.py --check    # exit 1 if any output is missing or out of date
    python scripts/build_icons.py --check --only icons   # CI: logos contain text and depend on fonts

Requires: pip install resvg-py pillow
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from io import BytesIO
from pathlib import Path

try:
    import resvg_py
    from PIL import Image, ImageChops
except ImportError as err:  # pragma: no cover
    sys.exit(f"Missing dependency: {err}. Run: pip install resvg-py pillow")

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
BRAND = ROOT / "custom_components" / "friedafetch" / "brand"
FRONTEND_ICON = ROOT / "custom_components" / "friedafetch" / "frontend" / "icon.svg"

ICON_SVG = ASSETS / "icon.svg"
LOGO_SVG = ASSETS / "logo.svg"
LOGO_DARK_SVG = ASSETS / "logo-dark.svg"

# sizes as in the brands conventions
BRAND_LOGO_HEIGHTS = (128, 256)


def render(svg: Path, width: int) -> Image.Image:
    """Rasterise an SVG to a transparent RGBA image of the given width."""
    png = resvg_py.svg_to_bytes(svg_path=str(svg), width=width)
    return Image.open(BytesIO(bytes(png))).convert("RGBA")


def to_png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def resize_height(image: Image.Image, height: int) -> Image.Image:
    width = round(image.width * height / image.height)
    return image.resize((width, height), Image.LANCZOS)


def build() -> dict[Path, bytes]:
    """Return every output path with its intended content."""
    out: dict[Path, bytes] = {}
    icon256 = render(ICON_SVG, 256)
    icon512 = render(ICON_SVG, 512)
    logo = render(LOGO_SVG, 1040)
    logo2x = render(LOGO_SVG, 2080)
    logo_dark = render(LOGO_DARK_SVG, 1040)
    logo_dark2x = render(LOGO_DARK_SVG, 2080)

    out[ASSETS / "icon.png"] = to_png_bytes(icon256)
    out[ASSETS / "icon@2x.png"] = to_png_bytes(icon512)
    out[ASSETS / "logo.png"] = to_png_bytes(logo)
    out[ASSETS / "logo@2x.png"] = to_png_bytes(logo2x)
    out[ASSETS / "logo-dark.png"] = to_png_bytes(logo_dark)

    out[BRAND / "icon.png"] = to_png_bytes(icon256)
    out[BRAND / "icon@2x.png"] = to_png_bytes(icon512)
    out[BRAND / "logo.png"] = to_png_bytes(resize_height(logo2x, BRAND_LOGO_HEIGHTS[0]))
    out[BRAND / "logo@2x.png"] = to_png_bytes(resize_height(logo2x, BRAND_LOGO_HEIGHTS[1]))
    out[BRAND / "dark_logo.png"] = to_png_bytes(resize_height(logo_dark2x, BRAND_LOGO_HEIGHTS[0]))
    out[BRAND / "dark_logo@2x.png"] = to_png_bytes(resize_height(logo_dark2x, BRAND_LOGO_HEIGHTS[1]))

    out[FRONTEND_ICON] = ICON_SVG.read_bytes()
    return out


# PNG encoders and rasterisers differ slightly between platforms, so the check compares pixels with a small
# tolerance instead of bytes: same size, no channel differs by more than MAX_CHANNEL_DIFF, tiny mean difference.
MAX_CHANNEL_DIFF = 8
MAX_MEAN_DIFF = 0.5


def same_image(expected: bytes, actual: bytes) -> bool:
    try:
        a = Image.open(BytesIO(expected)).convert("RGBA")
        b = Image.open(BytesIO(actual)).convert("RGBA")
    except OSError:
        return False
    if a.size != b.size:
        return False
    diff = ImageChops.difference(a, b)
    extrema = diff.getextrema()
    if max(hi for _, hi in extrema) > MAX_CHANNEL_DIFF:
        return False
    hist = diff.convert("L").histogram()
    total = sum(hist)
    mean = sum(i * n for i, n in enumerate(hist)) / total if total else 0.0
    return math.isfinite(mean) and mean <= MAX_MEAN_DIFF


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify outputs instead of writing them")
    parser.add_argument(
        "--only",
        choices=("all", "icons", "logos"),
        default="all",
        help="icons = files rendered from icon.svg only (font independent, used in CI); logos = the wide logos",
    )
    args = parser.parse_args()

    for src in (ICON_SVG, LOGO_SVG, LOGO_DARK_SVG):
        if not src.exists():
            return f"Missing source: {src.relative_to(ROOT)}" and 1

    outputs = build()
    if args.only != "all":
        is_logo = lambda path: "logo" in path.name  # noqa: E731
        outputs = {p: d for p, d in outputs.items() if is_logo(p) == (args.only == "logos")}
    stale: list[str] = []
    for path, data in outputs.items():
        rel = path.relative_to(ROOT)
        if args.check:
            if not path.exists():
                stale.append(f"{rel} (missing)")
            elif path.suffix == ".png":
                if not same_image(data, path.read_bytes()):
                    stale.append(f"{rel} (pixels differ)")
            elif path.read_bytes() != data:
                stale.append(str(rel))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        size = ""
        if path.suffix == ".png":
            with Image.open(path) as im:
                size = f" {im.width}x{im.height}"
        print(f"wrote {rel}{size} ({len(data)} bytes, {digest(data)})")

    if args.check:
        if stale:
            print("Out of date (run scripts/build_icons.py):")
            print("\n".join(f"  {s}" for s in stale))
            return 1
        print(f"All {len(outputs)} icon/logo files are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
