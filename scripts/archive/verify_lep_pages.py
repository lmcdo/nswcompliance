#!/usr/bin/env python3
"""Verify LEP page numbers and extract missing site-specific pages."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import fitz
from pathlib import Path

LEP_PDF_PATH = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\extraction_outputs\leps\Inner West Local Environmental Plan 2022 - NSW Legislation\auto\Inner West Local Environmental Plan 2022 - NSW Legislation_origin.pdf")
OUTPUT_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\frontend-nextjs\public\pdf-pages")

doc = fitz.open(str(LEP_PDF_PATH))
print(f"Total pages: {len(doc)}")
print()

# Show first few lines of pages 72-89 to verify clause locations
print("=" * 80)
print("PAGE CONTENT VERIFICATION (pages 72-89)")
print("=" * 80)
for pg_num in range(72, 90):
    page = doc[pg_num - 1]
    text = page.get_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()][:4]
    preview = " | ".join(lines[:3])
    print(f"Page {pg_num}: {preview[:120]}")

print()
print("=" * 80)
print("EXTRACTING MISSING PAGES: 6.20 (page 77) and 6.26 (page 82)")
print("=" * 80)

MISSING_PAGES = [
    {'page': 77, 'clauses': ['6.20'], 'name': 'Heritage conservation areas'},
    {'page': 82, 'clauses': ['6.26'], 'name': 'Alice Street, Lilyfield'},
]

for info in MISSING_PAGES:
    pg_num = info['page']
    page = doc[pg_num - 1]
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    for clause in info['clauses']:
        filename = f"iwlep_clause_{clause.replace('.', '_')}_page_{pg_num}.png"
        path = OUTPUT_DIR / filename
        pix.save(str(path))
        size = path.stat().st_size
        print(f"  Saved: {filename} ({size / 1024:.0f} KB)")

doc.close()
print()
print("Done.")
