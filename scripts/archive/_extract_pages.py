#!/usr/bin/env python3
"""Extract specific page ranges from DCP PDFs."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import fitz

pdf_path = sys.argv[1]
start = int(sys.argv[2]) - 1  # 1-indexed to 0-indexed
end = int(sys.argv[3]) if len(sys.argv) > 3 else start + 1

doc = fitz.open(pdf_path)
for i in range(start, min(end, len(doc))):
    t = doc[i].get_text()
    print(f"\n--- PAGE {i+1} ---")
    print(t)
