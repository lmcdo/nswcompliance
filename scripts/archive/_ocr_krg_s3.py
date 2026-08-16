#!/usr/bin/env python3
"""Download Ku-ring-gai DCP from S3 mirror + OCR parking section."""
import base64, os, sys, io
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader, PdfWriter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

url = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai%20DCP%202016.pdf"
print(f"Downloading {url[:80]}...")
try:
    r = httpx.get(url, timeout=120.0, follow_redirects=True)
    r.raise_for_status()
    pdf_bytes = r.content
    print(f"Downloaded {len(pdf_bytes)} bytes")
except Exception as e:
    print(f"Failed: {e}")
    sys.exit(1)

reader = PdfReader(io.BytesIO(pdf_bytes))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking section
parking_pages = []
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    if any(kw in text.lower() for kw in ["parking rate", "parking schedule", "spaces per", "car parking"]):
        parking_pages.append(i)
        if len(parking_pages) <= 10:
            preview = text[:120].strip().replace("\n", " ")
            print(f"Page {i}: {preview}")

print(f"\nTotal parking pages: {len(parking_pages)}")

if parking_pages:
    start = max(0, min(parking_pages) - 1)
    end = min(total_pages, max(parking_pages) + 2, start + 30)
    print(f"Extracting pages {start}-{end}")

    writer = PdfWriter()
    for i in range(start, end):
        writer.add_page(reader.pages[i])

    buf = io.BytesIO()
    writer.write(buf)
    extract_bytes = buf.getvalue()

    if len(reader.pages) > 500:
        # Too many pages, just scan text
        print(f"\nLarge document ({total_pages} pages). Scanning text only for parking table...")
        for i in parking_pages[:20]:
            text = reader.pages[i].extract_text() or ""
            if any(kw in text.lower() for kw in ["dwelling house", "residential flat", "dual occupancy", "schedule"]):
                print(f"\n=== Page {i} ===")
                print(text[:2000])
    else:
        b64 = base64.b64encode(extract_bytes).decode()
        print(f"OCRing {len(extract_bytes)} bytes...")
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
            md = page["markdown"]
            if any(kw in md.lower() for kw in ["dwelling", "residential", "parking", "schedule", "table"]):
                print(f"\n--- Page {page['index']} ---")
                print(md[:3000])
