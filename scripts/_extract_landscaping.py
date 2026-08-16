#!/usr/bin/env python3
"""Search council DCPs for landscaping/deep soil controls."""
import sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

COUNCILS = {
    "blacktown": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/BLACKTOWN/Blacktown%20DCP%202015.pdf",
    "penrith": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/PENRITH/Penrith%20DCP%202014.pdf",
    "campbelltown": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/CAMPBELLTOWN/Campbelltown%20Sustainable%20City%20DCP%202015.pdf",
    "liverpool": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/LIVERPOOL/Liverpool%20DCP%202008.pdf",
    "hornsby": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/HORNSBY/Hornsby%20DCP%202013.pdf",
    "northern_beaches": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15/Warringah%20DCP%202011%20-%20as%20amended%207%20May%202016.pdf",
    "parramatta": "https://www.cityofparramatta.nsw.gov.au/files/assets/public/v/1/development/parramatta-dcp-2023.pdf",
    "ku_ring_gai": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai%20DCP%20-%20Adopted%2020%20September%202016.pdf",
}

council = sys.argv[1] if len(sys.argv) > 1 else "blacktown"
url = COUNCILS[council]

print(f"Downloading {council} DCP...")
r = httpx.get(url, timeout=300.0, follow_redirects=True)
r.raise_for_status()
print(f"Downloaded {len(r.content)} bytes")
reader = PdfReader(io.BytesIO(r.content))
print(f"Total pages: {len(reader.pages)}")

print(f"\n--- Searching for landscaping/deep soil sections ---")
hits = 0
for i in range(len(reader.pages)):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    has_landscape = "landscap" in lower or "deep soil" in lower
    has_number = "%" in lower or "percent" in lower or "minimum" in lower
    if has_landscape and has_number:
        preview = text[:500].strip().replace("\n", " | ")
        print(f"\nPage {i}: {preview[:400]}")
        hits += 1

if hits == 0:
    # Broader search
    print("\nNo hits with strict filter. Trying broader search...")
    for i in range(len(reader.pages)):
        text = reader.pages[i].extract_text() or ""
        lower = text.lower()
        if "landscap" in lower and ("area" in lower or "zone" in lower or "table" in lower):
            preview = text[:400].strip().replace("\n", " | ")
            print(f"\nPage {i}: {preview[:300]}")
            hits += 1

print(f"\nTotal hits: {hits}")
