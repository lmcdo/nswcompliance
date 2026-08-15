#!/usr/bin/env python3
"""Extract parking rates from Blacktown DCP S3 mirror."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/BLACKTOWN/Blacktown%20DCP%202015.pdf"
print(f"Downloading {url[:80]}...")
r = httpx.get(url, timeout=300.0, follow_redirects=True)
r.raise_for_status()
print(f"Downloaded {len(r.content)} bytes")

reader = PdfReader(io.BytesIO(r.content))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking rate pages
print("\n--- Searching for parking rate tables ---")
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    if any(kw in lower for kw in ["parking rate", "car parking", "spaces per", "table 6"]):
        if any(kw2 in lower for kw2 in ["dwelling", "residential", "rate", "schedule", "minimum", "table"]):
            preview = text[:300].strip().replace("\n", " ")
            print(f"\nPage {i}: {preview}")
