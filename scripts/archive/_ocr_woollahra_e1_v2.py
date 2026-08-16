#!/usr/bin/env python3
"""Download + OCR Woollahra DCP Chapter E1 Parking and Access."""
import base64, os, sys, io
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader, PdfWriter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

urls = [
    "https://www.woollahra.nsw.gov.au/files/assets/public/v/1/building-and-development/documents/chapter-e1-parking-and-access-may-2024.pdf",
    "https://www.woollahra.nsw.gov.au/files/assets/public/v/6/plans-policies-publications/development-control-plans/chapter-e1-parking-and-access-23may2025.pdf",
    "https://www.woollahra.nsw.gov.au/__data/assets/pdf_file/0016/212209/Woollahra_DCP_2015_-_Repealed_2_January_2020_-_Chapter_E1_Parking_and_Access.pdf",
]

pdf_bytes = None
for url in urls:
    print(f"Trying {url[:80]}...")
    try:
        r = httpx.get(url, timeout=60.0, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        r.raise_for_status()
        pdf_bytes = r.content
        print(f"Downloaded {len(pdf_bytes)} bytes")
        break
    except Exception as e:
        print(f"Failed: {e}")

if not pdf_bytes:
    print("All URLs failed")
    sys.exit(1)

reader = PdfReader(io.BytesIO(pdf_bytes))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for Table 1 / parking rate pages
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    if any(kw in text.lower() for kw in ["table 1", "parking rate", "maximum", "dwelling house"]):
        print(f"Page {i}: {text[:150].strip()}")

# OCR the whole thing if small
if total_pages <= 40:
    b64 = base64.b64encode(pdf_bytes).decode()
    print(f"\nOCRing full document...")
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
        if any(kw in md.lower() for kw in ["table 1", "parking rate", "maximum", "dwelling", "car space"]):
            print(f"\n--- Page {page['index']} ---")
            print(md[:4000])
