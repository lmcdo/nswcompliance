#!/usr/bin/env python3
"""Download + OCR Waverley DCP Part C - parking pages only."""
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

url = "https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/dcp_2022/Waverley_DCP_2022_Part_C_-_Residential_Development.pdf"
print(f"Downloading {url}...")
r = httpx.get(url, timeout=120.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()
print(f"Downloaded {len(r.content)} bytes")

reader = PdfReader(io.BytesIO(r.content))
# Extract only parking pages: 15-20 (C1.8 Car Parking) and 52-55 (C2.12 Vehicular Access)
pages_to_extract = list(range(15, 21)) + list(range(51, 56))
print(f"Extracting pages: {pages_to_extract}")

writer = PdfWriter()
for i in pages_to_extract:
    if i < len(reader.pages):
        writer.add_page(reader.pages[i])

buf = io.BytesIO()
writer.write(buf)
pdf_bytes = buf.getvalue()

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
    print(page["markdown"])
