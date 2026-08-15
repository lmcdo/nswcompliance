#!/usr/bin/env python3
"""Extract parking rate tables from Inner West DCP PDFs."""
import sys
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\593f985b-c543-4a9f-bc35-f6c3a38980c5\tool-results"

pdfs = {
    "marrickville": f"{BASE}\\webfetch-1778411045069-8v6e1r.pdf",
    "leichhardt": f"{BASE}\\webfetch-1778411050457-5o80tz.pdf",
    "ashfield": f"{BASE}\\webfetch-1778411053876-wui7nw.pdf",
}

for council, pdf_path in pdfs.items():
    print(f"\n{'#'*80}")
    print(f"### {council.upper()}")
    print(f"{'#'*80}")
    try:
        reader = PdfReader(pdf_path)
        print(f"Pages: {len(reader.pages)}")
        for i in range(len(reader.pages)):
            text = reader.pages[i].extract_text() or ""
            lower = text.lower()
            if any(kw in lower for kw in [
                "parking rate", "car parking", "spaces per",
                "dwelling house", "dual occupancy", "residential flat",
                "multi dwelling", "boarding house", "table c1.11",
                "table 2.10", "minimum rate", "parking schedule",
                "maximum rate", "car space"
            ]):
                print(f"\n{'='*60}")
                print(f"=== Page {i} ===")
                print(f"{'='*60}")
                print(text[:5000])
    except Exception as e:
        print(f"ERROR: {e}")
