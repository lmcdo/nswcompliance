#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

docs_dir = Path("docs")

if not docs_dir.exists():
    print("docs directory not found")
    sys.exit(1)

print("Searching for Inner West LEP PDFs:\n")

lep_files = list(docs_dir.rglob("*Inner*West*.pdf"))

for f in lep_files:
    if "local" in f.name.lower() and "environmental" in f.name.lower():
        size_mb = f.stat().st_size / 1_000_000
        print(f"Found: {f}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Full path: {f.absolute()}")
        print()

# Also check what we have in documents table
print("\n" + "="*80)
print("LEP documents in database:")

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, pdf_name, pdf_path, char_count
            FROM documents
            WHERE document_type = 'LEP'
            AND pdf_name LIKE '%Inner%West%'
            LIMIT 5
        """)

        for row in cur.fetchall():
            print(f"\nDoc ID: {row[0]}")
            print(f"  Name: {row[1]}")
            print(f"  Path: {row[2]}")
            print(f"  Size: {row[3]:,} chars")