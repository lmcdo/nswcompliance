#!/usr/bin/env python3
"""Check LEP PDF version and verify Part 6 clause structure."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import fitz
from pathlib import Path

LEP_PDF_PATH = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\extraction_outputs\leps\Inner West Local Environmental Plan 2022 - NSW Legislation\auto\Inner West Local Environmental Plan 2022 - NSW Legislation_origin.pdf")

doc = fitz.open(str(LEP_PDF_PATH))
print(f"Total pages: {len(doc)}")
print()

# Check first few pages for version/amendment info
print("=== FIRST PAGE (version info) ===")
page0 = doc[0]
print(page0.get_text()[:1000])

print("\n=== PART 6 STRUCTURE (pages 44-90) ===")
print("Looking for clause headings (lines starting with 6.)...")
for pg_num in range(44, min(90, len(doc))):
    page = doc[pg_num - 1]
    text = page.get_text()
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        # Match clause headings like "6.1" or "6.14" or "6.1 Development..."
        if line and (line.startswith('6.') or line.startswith('| 6.')):
            # Only show lines that look like clause headings
            if len(line) < 150 and any(c.isalpha() for c in line[3:20] if len(line) > 3):
                print(f"  Page {pg_num}: {line[:100]}")
                break

doc.close()
