#!/usr/bin/env python3
"""Find TOD parking reduction clauses in SEPP Housing 2021."""

import pdfplumber
import re

pdf_path = 'sepp_housing_2021.pdf'

print('Searching for specific parking reduction clauses...\n')

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ''

        # Look for percentage reductions or specific clause patterns
        if re.search(r'(30|25|20|15|10)\s*%', text) and 'parking' in text.lower():
            print(f'=== PAGE {i+1} ===')
            print(text[:1500])
            print('\n---\n')

        # Also look for "accessible area" or "800m" patterns
        if '800m' in text or 'accessible area' in text.lower():
            if i+1 not in [115]:  # already printed
                print(f'=== PAGE {i+1} (accessible area) ===')
                print(text[:1500])
                print('\n---\n')
