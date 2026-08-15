#!/usr/bin/env python3
"""Extract parking-related pages from DCP PDFs."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import fitz

pdf_path = sys.argv[1]
doc = fitz.open(pdf_path)
print(f"Pages: {len(doc)}")

keywords = ['car parking', 'parking space', 'spaces per', 'visitor parking',
            'landscap', 'deep soil', 'site coverage']

for i in range(len(doc)):
    t = doc[i].get_text()
    tl = t.lower()
    score = sum(1 for kw in keywords if kw in tl)
    if score >= 2 and ('dwelling' in tl or 'residential' in tl or 'bedroom' in tl):
        print(f"\n{'='*60}")
        print(f"PAGE {i+1} (score={score})")
        print('='*60)
        print(t[:5000])
