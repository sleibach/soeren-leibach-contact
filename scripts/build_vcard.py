#!/usr/bin/env python3
"""Build the portrait JPEG and the vCard 3.0 file from contact.json.

Usage:
    python scripts/build_vcard.py path/to/profilePicture.png

Outputs (deterministic for the same inputs):
    site/assets/portrait.jpg   portrait for the page and the vCard
    site/soeren-leibach.vcf    vCard 3.0, photo embedded as base64 JPEG
"""
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
CONTACT = ROOT / "contact.json"
PORTRAIT_OUT = ROOT / "site" / "assets" / "portrait.jpg"
VCARD_OUT = ROOT / "site" / "soeren-leibach.vcf"

MAX_EDGE = 512        # target longest edge in pixels (never upscaled)
JPEG_QUALITY = 90
FOLD_OCTETS = 75      # RFC 2425 §5.8.1: lines SHOULD NOT exceed 75 octets


def build_portrait(src: Path) -> bytes:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.getchannel("A"))
            im = bg
        else:
            im = im.convert("RGB")
        scale = min(1.0, MAX_EDGE / max(im.size))
        if scale < 1.0:
            size = (round(im.width * scale), round(im.height * scale))
            im = im.resize(size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        # Baseline (non-progressive) JPEG, no metadata: widest decoder support.
        im.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True,
                progressive=False, subsampling="4:4:4")
        return buf.getvalue()


def escape(value: str) -> str:
    """Escape a TEXT value per RFC 2426 §4."""
    return (value.replace("\\", "\\\\").replace(";", "\\;")
                 .replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n"))


def fold(line: str) -> str:
    """Fold to <=75 octets per line without splitting UTF-8 sequences."""
    out, current, limit = [], b"", FOLD_OCTETS
    for ch in line:
        enc = ch.encode("utf-8")
        if len(current) + len(enc) > limit:
            out.append(current)
            current = b""
            limit = FOLD_OCTETS - 1  # continuation lines start with one space
        current += enc
    out.append(current)
    return "\r\n ".join(part.decode("utf-8") for part in out)


def build_vcard(c: dict, jpeg: bytes) -> str:
    given, family = c["given_name"], c["family_name"]
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{escape(family)};{escape(given)};;;",
        f"FN:{escape(f'{given} {family}')}",
        f"ORG:{escape(c['organization'])}",
        f"TITLE:{escape(c['title'])}",
        f"EMAIL;TYPE=INTERNET,WORK,PREF:{c['email']}",
    ]
    if c.get("url"):
        lines.append(f"URL:{c['url']}")
    lines.append("PHOTO;ENCODING=b;TYPE=JPEG:" + base64.b64encode(jpeg).decode("ascii"))
    lines.append("END:VCARD")
    return "".join(fold(line) + "\r\n" for line in lines)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).expanduser()
    if not src.is_file():
        sys.exit(f"Portrait not found: {src}")
    contact = json.loads(CONTACT.read_text(encoding="utf-8"))

    jpeg = build_portrait(src)
    PORTRAIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    PORTRAIT_OUT.write_bytes(jpeg)

    vcard = build_vcard(contact, jpeg)
    VCARD_OUT.write_bytes(vcard.encode("utf-8"))  # bytes: keep CRLF untouched

    with Image.open(io.BytesIO(jpeg)) as im:
        print(f"{PORTRAIT_OUT.relative_to(ROOT)}: {im.size[0]}x{im.size[1]}, {len(jpeg):,} bytes")
    print(f"{VCARD_OUT.relative_to(ROOT)}: {len(vcard.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    main()
