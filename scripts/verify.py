#!/usr/bin/env python3
"""Validate the vCard locally and, optionally, the live deployment.

Usage:
    python scripts/verify.py              # local checks only
    python scripts/verify.py --live       # also check public_url over HTTPS
"""
import base64
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
VCF_NAME = "soeren-leibach.vcf"
failures = []


def check(ok: bool, label: str) -> None:
    print(("PASS  " if ok else "FAIL  ") + label)
    if not ok:
        failures.append(label)


def validate_vcard(raw: bytes, where: str) -> None:
    check(raw.startswith(b"BEGIN:VCARD\r\n"), f"{where}: starts with BEGIN:VCARD + CRLF")
    check(raw.endswith(b"END:VCARD\r\n"), f"{where}: ends with END:VCARD + CRLF")
    check(b"\n" not in raw.replace(b"\r\n", b""), f"{where}: CRLF line endings only")
    physical = raw.split(b"\r\n")[:-1]
    check(all(len(l) <= 75 for l in physical), f"{where}: every physical line <= 75 octets")
    try:
        text = raw.decode("utf-8")
        check(True, f"{where}: valid UTF-8")
    except UnicodeDecodeError:
        check(False, f"{where}: valid UTF-8")
        return
    unfolded = re.sub(r"\r\n[ \t]", "", text).split("\r\n")[:-1]
    props = {}
    for line in unfolded:
        name = line.split(":", 1)[0].split(";", 1)[0].upper()
        props.setdefault(name, []).append(line)
    for req in ("VERSION", "N", "FN", "ORG", "TITLE", "EMAIL", "PHOTO"):
        check(req in props, f"{where}: has {req}")
    check(props.get("VERSION") == ["VERSION:3.0"], f"{where}: VERSION:3.0")
    check("FN:Sören Leibach" in props.get("FN", []), f"{where}: FN preserves Unicode (Sören)")
    photo = props.get("PHOTO", [""])[0]
    check(photo.startswith("PHOTO;ENCODING=b;TYPE=JPEG:"), f"{where}: PHOTO;ENCODING=b;TYPE=JPEG")
    check("VALUE=URI" not in photo.upper(), f"{where}: no PHOTO;VALUE=URI")
    try:
        data = base64.b64decode(photo.split(":", 1)[1], validate=True)
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            check(im.format == "JPEG", f"{where}: embedded photo decodes as JPEG {im.size[0]}x{im.size[1]}")
    except Exception as exc:  # noqa: BLE001
        check(False, f"{where}: embedded photo decodes ({exc})")


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "contact-page-verify"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, resp.headers.get("Content-Type", ""), resp.read()


def main() -> None:
    contact = json.loads((ROOT / "contact.json").read_text(encoding="utf-8"))
    validate_vcard((ROOT / "site" / VCF_NAME).read_bytes(), "local vcf")

    if "--live" in sys.argv:
        base = contact["public_url"]
        status, ctype, body = fetch(base)
        check(status == 200 and "text/html" in ctype, f"live page {base} -> {status} {ctype}")
        html = body.decode("utf-8")
        check(f'href="{VCF_NAME}"' in html, "live page links to the .vcf")
        check(f'href="mailto:{contact["email"]}"' in html, "live page has mailto fallback")
        for path, expect in (("assets/portrait.jpg", "image/jpeg"), (VCF_NAME, "vcard")):
            status, ctype, body = fetch(urljoin(base, path))
            check(status == 200 and expect in ctype, f"live {path} -> {status} {ctype}")
            if path == VCF_NAME:
                check(b"<html" not in body[:500].lower(), "live vcf is not an HTML page")
                check(body == (ROOT / "site" / VCF_NAME).read_bytes(), "live vcf identical to local build")
                validate_vcard(body, "live vcf")

    print(f"\n{len(failures)} failure(s)" if failures else "\nAll checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
