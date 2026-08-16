#!/usr/bin/env python3
"""
Search multiple council DCPs for landscaping/deep soil controls.
Uses R2 chapter PDFs where available, S3 mirrors for full DCPs.
"""
import sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Council → list of (label, url) to try
SOURCES = {
    "canterbury_bankstown_bankstown": (
        "CB DCP 2023 Ch5.1 Bankstown",
        "http://webdocs.bankstown.nsw.gov.au/api/publish?documentPath=aHR0cDovL2lzaGFyZS9zaXRlcy9QbGFubmluZy9QbGFubmluZyBQb2xpY3kvRENQL0RDUCAyMDIzL0NoYXB0ZXIgNS4xL0NoYXB0ZXIgNS4xIEJhbmtzdG93biBDQkQgYW5kIEZyYW1lLnBkZg%3D%3D",
    ),
    "canterbury_bankstown_canterbury": (
        "CB DCP 2023 Ch5.2 Canterbury",
        "http://webdocs.bankstown.nsw.gov.au/api/publish?documentPath=aHR0cDovL2lzaGFyZS9zaXRlcy9QbGFubmluZy9QbGFubmluZyBQb2xpY3kvRENQL0RDUCAyMDIzL0NoYXB0ZXIgNS4yL0NoYXB0ZXIgNS4yIENhbnRlcmJ1cnkgVG93biBDZW50cmUucGRm",
    ),
    "waverley": (
        "Waverley DCP 2022",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/WAVERLEY/Waverley%20DCP%202022.pdf",
    ),
    "woollahra": (
        "Woollahra DCP 2015",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/WOOLLAHRA/Woollahra%20DCP%202015.pdf",
    ),
    "cumberland": (
        "Cumberland DCP 2021",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/CUMBERLAND/Cumberland%20DCP%202021.pdf",
    ),
    "randwick": (
        "Randwick DCP 2013",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/RANDWICK/Randwick%20DCP%202013.pdf",
    ),
    "georges_river": (
        "Georges River DCP 2021",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/GEORGES-RIVER/Georges%20River%20DCP%202021.pdf",
    ),
    "sutherland_shire": (
        "Sutherland DCP 2015",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/SUTHERLAND/Sutherland%20Shire%20DCP%202015.pdf",
    ),
    "bayside": (
        "Bayside DCP 2022",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/BAYSIDE/Bayside%20DCP%202022.pdf",
    ),
    "hornsby": (
        "Hornsby DCP 2013",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/HORNSBY/Hornsby%20DCP%202013.pdf",
    ),
}

council = sys.argv[1] if len(sys.argv) > 1 else list(SOURCES.keys())[0]
label, url = SOURCES[council]

print(f"Downloading {label}...")
try:
    r = httpx.get(url, timeout=300.0, follow_redirects=True)
    r.raise_for_status()
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)

print(f"Downloaded {len(r.content)} bytes")
reader = PdfReader(io.BytesIO(r.content))
print(f"Total pages: {len(reader.pages)}")

print(f"\n--- Searching for landscaping/deep soil sections ---")
hits = 0
for i in range(len(reader.pages)):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    has_landscape = "landscap" in lower or "deep soil" in lower
    has_number = "%" in text or "percent" in lower or any(c.isdigit() for c in text[:200])
    if has_landscape and ("%" in text or "minimum" in lower or "deep soil" in lower or "area" in lower):
        preview = text.strip().replace("\n", " | ")
        print(f"\n=== Page {i} ===")
        print(preview[:600])
        hits += 1

if hits == 0:
    print("\nNo hits. Dumping all page headers...")
    for i in range(min(20, len(reader.pages))):
        text = (reader.pages[i].extract_text() or "")[:150].strip().replace("\n", " | ")
        print(f"  Page {i}: {text}")

print(f"\nTotal hits: {hits}")
