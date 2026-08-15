#!/usr/bin/env python3
"""Extract Part 22R Car Parking Rates pages from Ku-ring-gai DCP."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai%20DCP%202016.pdf"
print("Downloading...")
r = httpx.get(url, timeout=180.0, follow_redirects=True)
r.raise_for_status()

reader = PdfReader(io.BytesIO(r.content))
total_pages = len(reader.pages)

# Print pages 588-600 (around Part 22R)
for i in range(588, min(600, total_pages)):
    text = reader.pages[i].extract_text() or ""
    print(f"\n{'='*60}")
    print(f"=== Page {i} ===")
    print(f"{'='*60}")
    print(text[:3000])
