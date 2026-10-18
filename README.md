# Sören Leibach – speaker contact page

A static contact page for the SAP TechEd “Partner Voice” session on SAP Document AI.
Attendees scan a QR code, open the page, and tap **Save my contact** to import a
vCard (with portrait) on iPhone or Android.

**Live page:** https://sleibach.github.io/soeren-leibach-contact/
**vCard:** https://sleibach.github.io/soeren-leibach-contact/soeren-leibach.vcf

The QR code encodes **only the page URL**, not the contact data, so contact details
and the portrait can change later without reprinting the QR.

> Personal page. Not an official SAP or adesso service.

## Layout

```
contact.json                  single source of truth for contact fields + public URL
site/                         everything that is published (and nothing else)
  index.html, styles.css      static page, no JS, no external fonts, no tracking
  soeren-leibach.vcf          vCard 3.0, portrait embedded (PHOTO;ENCODING=b;TYPE=JPEG)
  assets/portrait.jpg         300×300 JPEG, quality 92 (native size of the source photo)
qr/
  soeren-leibach-contact-qr.png   1225 px, 25 px/module, navy #002B4D on white, EC level H
  soeren-leibach-contact-qr.svg   vector equivalent
scripts/
  build_vcard.py              original portrait → portrait.jpg + .vcf
  build_qr.py                 URL → PNG + SVG, then decodes the PNG with zbarimg
  verify.py                   vCard validation; --live checks the deployed site
.github/workflows/pages.yml   deploys site/ to GitHub Pages on push to main
```

The source portrait (your LinkedIn photo, downloaded once to the git-ignored
`source/` folder) is **not** committed; only the derived JPEG is published. The
page never loads images from LinkedIn at runtime. The script never upscales: it
scales down to at most 512 px. LinkedIn only provided a 300×300 file, so for a
sharper contact photo, rerun it with a higher-resolution original.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
brew install zbar            # independent QR decoder used for verification
```

## Updating details or the portrait

1. Edit `contact.json` (name, title, email, URL), and update the same text in
   `site/index.html`.
2. Rebuild the portrait and vCard from the **original** image (not a thumbnail):
   ```sh
   .venv/bin/python scripts/build_vcard.py source/linkedin-profile.jpg   # or a higher-res original
   .venv/bin/python scripts/verify.py
   ```
3. Commit and push to `main`. The workflow redeploys automatically. Then run
   `.venv/bin/python scripts/verify.py --live`.

**Do not regenerate or reprint the QR for content changes.** The QR only needs
to change if the public URL changes. Keep the repository name, owner and Pages
settings as they are so already-presented QR codes keep working. Renaming or
deleting the repo, or adding a custom domain, would change or break the URL.

## Regenerating the QR

Only if `public_url` in `contact.json` changes:

```sh
.venv/bin/python scripts/build_qr.py            # uses public_url
```

The script fails unless zbarimg decodes the PNG back to exactly the same URL.
Properties: QR version 6, error correction H, plain square modules, 4-module
quiet zone, navy on opaque white, integer module scaling.
The SVG was verified by rendering it in Chrome and decoding with zbarimg. ImageMagick's
built-in SVG renderer draws it incorrectly, so check SVG exports in a browser or
your design tool, not ImageMagick.

## Deployment

GitHub Pages is set to **Build and deployment → Source: GitHub Actions**. Every
push to `main` that touches `site/` runs `.github/workflows/pages.yml`, which
uploads `site/` with `actions/upload-pages-artifact` and publishes it with
`actions/deploy-pages`. All links in the page are relative, so it works under the
`/soeren-leibach-contact/` project subpath. GitHub Pages serves `.vcf` as
`text/x-vcard` (verified), which iOS Safari and Android recognise as a contact file.

## Testing

Automated (`scripts/verify.py --live`, `scripts/build_qr.py`):
- Page, portrait and `.vcf` return HTTP 200 with the expected content types.
- The live `.vcf` is byte-identical to the local build and isn't an HTML error page.
- vCard 3.0 syntax: CRLF line endings, lines folded at ≤75 octets (UTF-8 safe),
  required properties present, text escaped, Unicode preserved, photo decodes as JPEG.
- The QR PNG decodes (ZBar) to exactly the public URL.

Manual – iPhone:
1. Open the Camera app and point it at the QR, then tap the banner. Safari opens the page.
2. Tap **Save my contact**. A contact preview appears.
3. Tap **Create New Contact** (or *Add to Existing*) and save.
4. Open Contacts and check the name, title, company, email, LinkedIn URL and **portrait**.

Manual – Android (Chrome + Google Contacts):
1. Scan with the Camera app or Google Lens, then open the link in Chrome.
2. Tap **Save my contact**. The `.vcf` downloads. Tap the download notification or
   *Open*, and pick **Contacts**.
3. Choose the account to save to and confirm the import.
4. Open the contact and check all fields and the **portrait**. Some OEM contact
   apps behave differently, so test on the device types you expect attendees to use.

Also: tap **Email me** (opens a mail draft) and **LinkedIn**.

## Public data

Everything in `site/` is public on the internet, and the repository is public,
including its Git history. That covers the name, job title, employer, work email,
LinkedIn URL and portrait. The page sets `noindex` to discourage search engines,
but that isn't access control, and anyone with the URL or QR can download the
vCard. Removing data later from the current version doesn't remove copies that
were already saved, cached or archived, or that are still in Git history. Don't
add a phone number or private address unless you're happy for them to be
permanently public.
