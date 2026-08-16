#!/usr/bin/env python3
"""Extract TOD-related page (accessible area definition) from SEPP Housing 2021."""

import pdfplumber
from pathlib import Path

# Find the SEPP Housing PDF
script_dir = Path(__file__).parent
pdf_path = script_dir / 'sepp_housing_2021.pdf'

# Alternative locations
if not pdf_path.exists():
    alt_path = script_dir.parent / 'extraction_outputs' / 'sepps' / 'State Environmental Planning Policy (Housing) 2021 - NSW Legislation' / 'auto' / 'sepp_housing_2021.pdf'
    if alt_path.exists():
        pdf_path = alt_path

print(f'Using PDF: {pdf_path}')

# Output directory
output_dir = script_dir.parent / 'frontend-nextjs' / 'public' / 'pdf-pages' / 'sepp-housing'
output_dir.mkdir(parents=True, exist_ok=True)

# Extract page 115 (index 114)
page_num = 115
output_path = output_dir / f'sepp-housing_page_{page_num}.png'

print(f'Extracting page {page_num}...')

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[page_num - 1]  # 0-indexed
    img = page.to_image(resolution=150)
    img.save(str(output_path))
    print(f'Saved: {output_path}')

print('Done!')
