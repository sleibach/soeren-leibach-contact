#!/usr/bin/env python3
"""Generate the contact-page QR code (PNG + SVG) and decode it independently.

Usage:
    python scripts/build_qr.py [URL]      # defaults to public_url in contact.json

Outputs:
    qr/soeren-leibach-contact-qr.png   >= 1200 px wide, integer module scaling
    qr/soeren-leibach-contact-qr.svg

The QR encodes only the page URL. Plain square modules, navy on opaque white,
4-module quiet zone, error correction level H. After writing, the PNG is
decoded with zbarimg (ZBar, independent of the segno encoder) and must match.
"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "qr"
PNG = OUT_DIR / "soeren-leibach-contact-qr.png"
SVG = OUT_DIR / "soeren-leibach-contact-qr.svg"

NAVY, WHITE = "#002B4D", "#FFFFFF"
QUIET_ZONE = 4
MIN_PNG_WIDTH = 1200


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else json.loads(
        (ROOT / "contact.json").read_text(encoding="utf-8"))["public_url"]
    if not url.startswith("https://"):
        sys.exit(f"Refusing non-HTTPS URL: {url}")

    qr = segno.make(url, error="h", boost_error=False, micro=False)
    modules = qr.symbol_size(scale=1, border=QUIET_ZONE)[0]
    scale = math.ceil(MIN_PNG_WIDTH / modules)

    OUT_DIR.mkdir(exist_ok=True)
    qr.save(PNG, kind="png", scale=scale, border=QUIET_ZONE, dark=NAVY, light=WHITE)
    qr.save(SVG, kind="svg", scale=10, border=QUIET_ZONE, dark=NAVY, light=WHITE,
            title=f"QR code: {url}", unit="px")

    print(f"URL:      {url}")
    print(f"Version:  {qr.version}, error correction {qr.error}")
    print(f"Modules:  {modules} incl. {QUIET_ZONE}-module quiet zone; "
          f"PNG {modules * scale}px ({scale}px/module)")

    if not shutil.which("zbarimg"):
        sys.exit("zbarimg not found (brew install zbar) - QR NOT verified")
    decoded = subprocess.run(["zbarimg", "--quiet", "--raw", str(PNG)],
                             capture_output=True, text=True).stdout.strip()
    if decoded != url:
        sys.exit(f"QR verification FAILED: decoded {decoded!r}")
    print(f"Verified: zbarimg decodes PNG to {decoded}")


if __name__ == "__main__":
    main()
