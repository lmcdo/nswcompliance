#!/usr/bin/env python3
"""Extract parking rates from Parramatta DCP 2023 PDF."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://www.cityofparramatta.nsw.gov.au/files/assets/public/v/1/development/parramatta-dcp-2023.pdf"
print(f"Downloading {url[:80]}...")
r = httpx.get(url, timeout=300.0, follow_redirects=True,
              headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
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
    if any(kw in lower for kw in ["parking rate", "car parking", "spaces per"]):
        if any(kw2 in lower for kw2 in ["dwelling", "residential", "table", "schedule", "minimum"]):
            preview = text[:300].strip().replace("\n", " ")
            print(f"\nPage {i}: {preview}")
