#!/usr/bin/env python3
"""OCR City of Sydney parking rates update PDF."""
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

pdf_path = r"C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\009d1a7a-47b3-4160-92cf-d0aa1f1b716b\tool-results\webfetch-1778404648453-0zg52b.pdf"

with open(pdf_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

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
    print(f"--- Page {page['index']} ---")
    print(page["markdown"][:4000])
    print()
