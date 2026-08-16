#!/usr/bin/env python3
"""Temp script to extract parking rates from downloaded DCP PDFs."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

try:
    import fitz
except ImportError:
    print("PyMuPDF not installed")
    sys.exit(1)

pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
if not pdf_path or not os.path.exists(pdf_path):
    print(f"Usage: python {sys.argv[0]} <pdf_path>")
    sys.exit(1)

doc = fitz.open(pdf_path)
print(f"Pages: {len(doc)}")

for i in range(len(doc)):
    t = doc[i].get_text()
    tl = t.lower()
    if any(kw in tl for kw in ['parking', 'dwelling', 'car space', 'bedroom', 'landscap', 'deep soil', 'site coverage']):
        print(f"\n--- PAGE {i+1} ---")
        print(t[:3000])
