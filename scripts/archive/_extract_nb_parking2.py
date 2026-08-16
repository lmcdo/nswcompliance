#!/usr/bin/env python3
"""Check if Warringah DCP PDF has extractable text."""
import sys, io
import httpx
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15/Warringah%20DCP%202011%20-%20as%20amended%207%20May%202016.pdf"
print("Downloading...")
r = httpx.get(url, timeout=300.0, follow_redirects=True)
r.raise_for_status()

reader = PdfReader(io.BytesIO(r.content))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Check first 10 pages for any text
for i in range(min(10, total_pages)):
    text = reader.pages[i].extract_text() or ""
    print(f"Page {i}: {len(text)} chars — {text[:200].strip()}")

# Check pages near end (Appendix 1 usually at the end)
for i in range(max(0, total_pages-20), total_pages):
    text = reader.pages[i].extract_text() or ""
    if len(text) > 50:
        print(f"Page {i}: {len(text)} chars — {text[:200].strip()}")
