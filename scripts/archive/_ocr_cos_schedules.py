#!/usr/bin/env python3
"""OCR City of Sydney DCP 2012 Schedules for parking rates."""
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
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking pages
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    if any(kw in text.lower() for kw in ["car parking", "parking rate", "luti"]):
        print(f"Page {i}: {text[:150].strip()}")

# Also search for "3.11" which is the transport section
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    if "3.11" in text or "transport" in text.lower():
        print(f"Page {i} (transport): {text[:150].strip()}")
