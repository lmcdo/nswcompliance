#!/usr/bin/env python3
"""OCR just the Table 4 page from Waverley DCP Part B."""
import base64, os, sys, io
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader, PdfWriter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

url = "https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/dcp_2022/Waverley_DCP_2022_Part_B_-_General_Provisions.pdf"
print(f"Downloading...")
r = httpx.get(url, timeout=120.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()
print(f"Downloaded {len(r.content)} bytes")

reader = PdfReader(io.BytesIO(r.content))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Table 4 is on the page with "Table 4 Car Parking Rates" - around page 65
# Search for it
for i in range(60, 75):
    text = reader.pages[i].extract_text() or ""
    if "Table 4" in text and "parking" in text.lower():
        print(f"Found 'Table 4' on page {i}: {text[:200]}")

# Extract pages 63-67 (the table might span 2 pages)
writer = PdfWriter()
for i in range(62, 68):
    writer.add_page(reader.pages[i])

buf = io.BytesIO()
writer.write(buf)
pdf_bytes = buf.getvalue()

b64 = base64.b64encode(pdf_bytes).decode()
print(f"OCRing {len(pdf_bytes)} bytes...")
resp = httpx.post(
    "https://api.mistral.ai/v1/ocr",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "model": "mistral-ocr-latest",
        "document": {"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"},
        "include_image_base64": True,
    },
    timeout=300.0,
)
resp.raise_for_status()
data = resp.json()
for page in data.get("pages", []):
    print(f"\n--- Page {page['index']} ---")
    md = page["markdown"]
    # Print full content, including any image refs
    print(md)
