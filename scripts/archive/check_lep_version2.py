#!/usr/bin/env python3
"""Extract all Part 6 clause headings from LEP PDF."""
import sys, re
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import fitz
from pathlib import Path

LEP_PDF_PATH = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\extraction_outputs\leps\Inner West Local Environmental Plan 2022 - NSW Legislation\auto\Inner West Local Environmental Plan 2022 - NSW Legislation_origin.pdf")

doc = fitz.open(str(LEP_PDF_PATH))

# Search pages 40-95 for Part 6 clause headings
# Pattern: "6.XX" followed by text (clause title)
clause_pattern = re.compile(r'^(6\.\d+)\s+(.+?)$', re.MULTILINE)

print("=== ALL PART 6 CLAUSES FOUND ===")
found_clauses = {}
for pg_num in range(40, min(95, len(doc))):
    page = doc[pg_num - 1]
    text = page.get_text()
    matches = clause_pattern.findall(text)
    for clause_num, title in matches:
        title = title.strip()
        if len(title) > 5 and clause_num not in found_clauses:
            # Skip if it looks like body text not a heading
            if not title.startswith('(') and not title.startswith('the '):
                found_clauses[clause_num] = (pg_num, title[:80])

for clause_num in sorted(found_clauses.keys(), key=lambda x: float(x)):
    pg, title = found_clauses[clause_num]
    print(f"  Clause {clause_num} | Page {pg} | {title}")

doc.close()
