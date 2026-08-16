#!/usr/bin/env python3
"""Find TOD parking reduction clauses in SEPP Housing 2021."""

import pdfplumber

pdf_path = 'sepp_housing_2021.pdf'

print('Searching SEPP Housing 2021 for TOD parking clauses...\n')

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ''
        text_lower = text.lower()

        # Check for parking reduction content
        if 'parking' in text_lower and ('reduction' in text_lower or 'reduce' in text_lower or 'transit' in text_lower or 'rail' in text_lower):
            print(f'=== PAGE {i+1} ===')
            print(text[:1200])
            print('\n---\n')
