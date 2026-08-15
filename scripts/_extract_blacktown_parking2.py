#!/usr/bin/env python3
"""Extract residential parking rates from Blacktown DCP pages 34-40."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/BLACKTOWN/Blacktown%20DCP%202015.pdf"
print("Downloading...")
r = httpx.get(url, timeout=300.0, follow_redirects=True)
r.raise_for_status()

reader = PdfReader(io.BytesIO(r.content))

# Print pages 34-40 in full
for i in range(34, 42):
    text = reader.pages[i].extract_text() or ""
    print(f"\n{'='*60}")
    print(f"=== Page {i} ===")
    print(f"{'='*60}")
    print(text[:3000])
