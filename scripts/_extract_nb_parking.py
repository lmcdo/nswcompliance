#!/usr/bin/env python3
"""Extract parking rates from Warringah DCP (Northern Beaches) S3 mirror."""
import os, sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Try S3 mirror first
urls = [
    "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15/Warringah%20DCP%202011%20-%20as%20amended%207%20May%202016.pdf",
    "https://www.austlii.edu.au/au/other/nsw/NSWEPIDCP/2020/6.pdf",
]

pdf_bytes = None
for url in urls:
    print(f"Trying {url[:80]}...")
    try:
        r = httpx.get(url, timeout=300.0, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        r.raise_for_status()
        pdf_bytes = r.content
        print(f"Downloaded {len(pdf_bytes)} bytes")
        break
    except Exception as e:
        print(f"Failed: {type(e).__name__}: {e}")

if not pdf_bytes:
    print("All sources failed")
    sys.exit(1)

reader = PdfReader(io.BytesIO(pdf_bytes))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for Appendix 1 / parking rate table
print("\n--- Searching for parking rates ---")
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    if "appendix 1" in lower or ("car parking" in lower and any(kw in lower for kw in ["dwelling", "table", "rate", "spaces"])):
        preview = text[:400].strip().replace("\n", " ")
        print(f"\nPage {i}: {preview}")
