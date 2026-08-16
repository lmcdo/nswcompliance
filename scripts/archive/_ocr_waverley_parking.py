#!/usr/bin/env python3
"""Download + OCR Waverley DCP Part C for parking rates."""
import base64
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import httpx

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

# Try downloading Waverley Part C (residential)
url = "https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/dcp_2022/Waverley_DCP_2022_Part_C_-_Residential_Development.pdf"
print(f"Downloading {url}...")
try:
    r = httpx.get(url, timeout=120.0, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    pdf_bytes = r.content
    print(f"Downloaded {len(pdf_bytes)} bytes")
except Exception as e:
    print(f"Download failed: {e}")
    sys.exit(1)

# Check size - split if needed
from pypdf import PdfReader, PdfWriter
import io

reader = PdfReader(io.BytesIO(pdf_bytes))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking-related pages
parking_pages = []
for i, page in enumerate(reader.pages):
    text = page.extract_text() or ""
    if any(kw in text.lower() for kw in ["car parking", "parking rate", "parking provision", "parking space"]):
        parking_pages.append(i)

print(f"Pages mentioning parking: {parking_pages}")

if not parking_pages:
    # Try broader search
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if "parking" in text.lower():
            parking_pages.append(i)
    print(f"Pages mentioning 'parking' at all: {parking_pages}")

# Extract relevant range
if parking_pages:
    start = max(0, min(parking_pages) - 1)
    end = min(total_pages, max(parking_pages) + 2)
    print(f"Extracting pages {start}-{end}")

    writer = PdfWriter()
    for i in range(start, end):
        writer.add_page(reader.pages[i])

    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()
    print(f"Extracted PDF: {len(pdf_bytes)} bytes, {end-start} pages")

b64 = base64.b64encode(pdf_bytes).decode()

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
    print(page["markdown"][:4000])
