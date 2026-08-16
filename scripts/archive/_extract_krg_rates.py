#!/usr/bin/env python3
"""Extract parking rates from Ku-ring-gai DCP per-dev-type chapters."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai%20DCP%202016.pdf"
print("Downloading (cached if recent)...")
r = httpx.get(url, timeout=180.0, follow_redirects=True)
r.raise_for_status()

reader = PdfReader(io.BytesIO(r.content))

# Pages with parking provision for each dev type
target_pages = [126, 127, 160, 161, 162, 195, 196, 197, 238, 239, 240, 280, 281, 282]

for i in target_pages:
    if i < len(reader.pages):
        text = reader.pages[i].extract_text() or ""
        if any(kw in text.lower() for kw in ["parking provision", "parking space", "car space", "number of space"]):
            print(f"\n{'='*60}")
            print(f"=== Page {i} ===")
            print(f"{'='*60}")
            print(text[:2500])
