#!/usr/bin/env python3
"""Re-parse specific Dulwich Hill tables"""
import sys
sys.path.insert(0, 'scripts')
from reparse_table_structure import (
    find_pdf_file, reparse_table, update_provision_table
)

# Dulwich Hill tables
tables_to_fix = [
    {
        'id': 73432,
        'pdf_file': 'Marrickville DCP 2011 - 9 38 Dulwich Hill Commercial Precinct 38 - with IWLEP 2022 amendments.pdf',
        'page': 8
    },
    {
        'id': 73433,
        'pdf_file': 'Marrickville DCP 2011 - 9 38 Dulwich Hill Commercial Precinct 38 - with IWLEP 2022 amendments.pdf',
        'page': 9
    }
]

pdf_file = tables_to_fix[0]['pdf_file']
pdf_path = find_pdf_file(pdf_file)

if not pdf_path:
    print(f"ERROR: Could not find {pdf_file}")
    sys.exit(1)

print(f"Found PDF: {pdf_path}")
print()

for table in tables_to_fix:
    prov_id = table['id']
    page = table['page']

    print(f"Re-parsing provision {prov_id} (page {page})...")

    new_html, parser = reparse_table(pdf_path, page)

    if new_html:
        update_provision_table(prov_id, new_html, parser)
        print(f"  SUCCESS: Updated with {parser}")
    else:
        print(f"  FAILED: All parsers failed")

print("\nDone!")
