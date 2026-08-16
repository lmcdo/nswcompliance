#!/usr/bin/env python3
"""Extract specific pages from council DCPs for landscaping detail."""
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
    "ku_ring_gai": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai%20DCP%20-%20Adopted%2020%20September%202016.pdf",
}

council = sys.argv[1]
pages = [int(p) for p in sys.argv[2].split(",")]
url = COUNCILS[council]

print(f"Downloading {council} DCP...")
r = httpx.get(url, timeout=300.0, follow_redirects=True)
r.raise_for_status()
reader = PdfReader(io.BytesIO(r.content))
print(f"Total pages: {len(reader.pages)}")

for p in pages:
    text = reader.pages[p].extract_text() or ""
    print(f"\n{'='*60}")
    print(f"=== Page {p} ===")
    print(f"{'='*60}")
    print(text)
