#!/usr/bin/env python3
"""One-off script to extract residential chapters from full DCP PDFs."""
import fitz
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'dcps')

# Burwood: Part 4.4-4.6 (p203-241, 0-based 202-240)
doc = fitz.open(r'C:\Users\lawre\Downloads\Burwood-development-control-plan-DCP.pdf')
out = fitz.open()
for i in range(202, 241):
    out.insert_pdf(doc, from_page=i, to_page=i)
outpath = os.path.join(DATA_DIR, 'burwood-part4-residential.pdf')
out.save(outpath)
print(f'Burwood: extracted {len(out)} pages (p203-241) -> {outpath}')
out.close()
doc.close()

# Fairfield 2024: Ch 5A+5B+5C (p145-204, 0-based 144-203)
doc = fitz.open(r'C:\Users\lawre\Downloads\fairfield-city-wide-development-control-plan-2024.pdf')
out = fitz.open()
for i in range(144, 204):
    out.insert_pdf(doc, from_page=i, to_page=i)
outpath = os.path.join(DATA_DIR, 'fairfield-ch5-dwelling-houses.pdf')
out.save(outpath)
print(f'Fairfield: extracted {len(out)} pages (p145-204) -> {outpath}')
out.close()
doc.close()
