#!/usr/bin/env python3
"""Download + OCR Waverley DCP Part B7 Transport for parking rates."""
import base64
import os
import sys
import io
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader, PdfWriter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

# Try Part B
urls = [
    "https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/dcp_2022/Waverley_DCP_2022_Part_B_-_General_Provisions.pdf",
    "https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/dcp_2022/Waverley_DCP_2022_Part_B7_-_Transport.pdf",
]

for url in urls:
    print(f"Trying {url}...")
    try:
        r = httpx.get(url, timeout=120.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        print(f"Downloaded {len(r.content)} bytes")
        pdf_bytes = r.content
        break
    except Exception as e:
        print(f"Failed: {e}")
        pdf_bytes = None

if not pdf_bytes:
    print("All URLs failed")
    sys.exit(1)

reader = PdfReader(io.BytesIO(pdf_bytes))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking/transport pages
parking_pages = []
for i, page in enumerate(reader.pages):
    text = page.extract_text() or ""
    if any(kw in text.lower() for kw in ["parking rate", "table 4", "car parking space", "b7"]):
        parking_pages.append(i)

print(f"Pages with parking/B7 keywords: {parking_pages}")

if parking_pages:
    start = max(0, min(parking_pages) - 1)
    end = min(total_pages, max(parking_pages) + 2)
else:
    # Just OCR all if small enough
    start = 0
    end = min(total_pages, 50)

print(f"Extracting pages {start}-{end}")
writer = PdfWriter()
for i in range(start, end):
    writer.add_page(reader.pages[i])

buf = io.BytesIO()
writer.write(buf)
extract_bytes = buf.getvalue()

b64 = base64.b64encode(extract_bytes).decode()
print("OCRing with Mistral...")
resp = httpx.post(
    "https://api.mistral.ai/v1/ocr",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "model": "mistral-ocr-latest",
        "document": {"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"},
    },
    timeout=300.0,
)
resp.raise_for_status()
data = resp.json()
for page in data.get("pages", []):
    print(f"\n--- Page {page['index']} ---")
    print(page["markdown"])
