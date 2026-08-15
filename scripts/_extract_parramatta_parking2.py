#!/usr/bin/env python3
"""Extract Part 6 parking rate table from Parramatta DCP 2023."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://www.cityofparramatta.nsw.gov.au/files/assets/public/v/1/development/parramatta-dcp-2023.pdf"
print("Downloading...")
r = httpx.get(url, timeout=300.0, follow_redirects=True,
              headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
r.raise_for_status()

reader = PdfReader(io.BytesIO(r.content))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Find "Part 6" pages with parking rates
print("\n--- Searching for Part 6 parking rate table ---")
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    if "part 6" in lower or "traffic and transport" in lower:
        if any(kw in lower for kw in ["table", "rate", "dwelling", "parking rate", "spaces"]):
            print(f"\n{'='*60}")
            print(f"=== Page {i} ===")
            print(f"{'='*60}")
            print(text[:3000])
