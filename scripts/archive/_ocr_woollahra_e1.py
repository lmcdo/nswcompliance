#!/usr/bin/env python3
"""OCR Woollahra DCP Chapter E1 for parking rates."""
import base64, os, sys, io
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader, PdfWriter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

# Try the S3 draft first (already downloaded)
pdf_path = r"C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\009d1a7a-47b3-4160-92cf-d0aa1f1b716b\tool-results\webfetch-1778405613438-9ez5f3.pdf"

reader = PdfReader(pdf_path)
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking/E1 pages
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    if any(kw in text.lower() for kw in ["parking", "table 1", "e1", "car space"]):
        print(f"Page {i}: {text[:120].strip()}")

# If it's small enough, OCR all of it
if total_pages <= 50:
    with open(pdf_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    print(f"\nOCRing full document ({total_pages} pages)...")
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
        if any(kw in md.lower() for kw in ["parking", "table 1", "dwelling", "car space", "maximum"]):
            print(f"\n--- Page {page['index']} ---")
            print(md[:3000])
else:
    # Extract parking pages only
    parking_pages = []
    for i in range(total_pages):
        text = reader.pages[i].extract_text() or ""
        if "parking" in text.lower() or "table 1" in text.lower():
            parking_pages.append(i)

    if parking_pages:
        start = max(0, min(parking_pages) - 1)
        end = min(total_pages, max(parking_pages) + 2)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()

        print(f"\nOCRing pages {start}-{end}...")
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
            print(page["markdown"][:3000])
