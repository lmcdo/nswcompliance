#!/usr/bin/env python3
"""Extract Appendix 1 parking from Warringah DCP."""
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

# Print pages 148-153 (around Appendix 1)
for i in range(148, 154):
    text = reader.pages[i].extract_text() or ""
    print(f"\n{'='*60}")
    print(f"=== Page {i} ===")
    print(f"{'='*60}")
    print(text)
