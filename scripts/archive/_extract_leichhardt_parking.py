#!/usr/bin/env python3
"""Extract parking rates from Leichhardt DCP 2013 Part C Section 1."""
import sys
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

pdf_path = r"C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\009d1a7a-47b3-4160-92cf-d0aa1f1b716b\tool-results\webfetch-1778408579766-dois06.pdf"
reader = PdfReader(pdf_path)
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking rate table
for i in range(total_pages):
    text = reader.pages[i].extract_text() or ""
    lower = text.lower()
    if "c1.11" in lower or ("parking" in lower and any(kw in lower for kw in ["dwelling", "rate", "table", "spaces per", "minimum"])):
        print(f"\n{'='*60}")
        print(f"=== Page {i} ===")
        print(f"{'='*60}")
        print(text[:3000])
