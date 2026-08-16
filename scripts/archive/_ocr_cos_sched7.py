#!/usr/bin/env python3
"""OCR City of Sydney DCP Schedule 7 Transport pages."""
import base64, os, sys, io
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader, PdfWriter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

pdf_path = r"C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\009d1a7a-47b3-4160-92cf-d0aa1f1b716b\tool-results\webfetch-1778404727896-chl4re.pdf"

reader = PdfReader(pdf_path)
writer = PdfWriter()
for i in range(37, 47):
    writer.add_page(reader.pages[i])

buf = io.BytesIO()
writer.write(buf)
pdf_bytes = buf.getvalue()

b64 = base64.b64encode(pdf_bytes).decode()
print(f"OCRing Schedule 7 ({len(pdf_bytes)} bytes, 10 pages)...")
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
