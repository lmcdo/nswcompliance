#!/usr/bin/env python3
"""Extract parking schedule from Ku-ring-gai DCP S3 mirror."""
import os, sys, io
from pathlib import Path
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai%20DCP%202016.pdf"
print(f"Downloading...")
r = httpx.get(url, timeout=180.0, follow_redirects=True)
r.raise_for_status()
print(f"Downloaded {len(r.content)} bytes")

reader = PdfReader(io.BytesIO(r.content))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Find Part 22 / parking schedule pages
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    if "22" in text and any(kw in text.lower() for kw in ["part 22", "parking schedule", "schedule of parking"]):
        preview = text[:200].strip().replace("\n", " ")
        print(f"\nPage {i}: {preview}")
    elif "parking schedule" in text.lower() or "schedule of parking" in text.lower():
        preview = text[:200].strip().replace("\n", " ")
        print(f"\nPage {i} (schedule): {preview}")

# Also search for the table with dwelling-specific rates
print("\n--- Searching for parking rate table ---")
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    if ("dwelling house" in lower or "dwelling houses" in lower) and ("parking" in lower or "space" in lower) and ("rate" in lower or "schedule" in lower or "minimum" in lower):
        print(f"\nPage {i}:")
        print(text[:1500])
