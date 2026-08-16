#!/usr/bin/env python3
"""Extract Part 22R.1 Car Parking Rates from Ku-ring-gai DCP S3 mirror."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai%20DCP%202016.pdf"
print("Downloading...")
r = httpx.get(url, timeout=180.0, follow_redirects=True)
r.raise_for_status()
print(f"Downloaded {len(r.content)} bytes")

reader = PdfReader(io.BytesIO(r.content))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for Part 22R.1 / general parking rate table
print("\n--- Searching for Part 22R.1 / general parking rates ---")
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    if "22r" in lower or "part 22r" in lower:
        print(f"\nPage {i} (22R ref):")
        print(text[:2000])
        print("---")
    elif "car parking rate" in lower and ("table" in lower or "schedule" in lower or "rate" in lower):
        preview = text[:300].strip().replace("\n", " ")
        print(f"\nPage {i} (parking rate table): {preview}")
