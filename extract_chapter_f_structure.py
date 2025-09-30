#!/usr/bin/env python3
"""
Extract Chapter F structure to find development type mapping
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

print("="*80)
print("CHAPTER F - DEVELOPMENT CATEGORY STRUCTURE")
print("="*80)

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Get Chapter F document
        cur.execute("""
            SELECT id, pdf_name, full_text
            FROM documents
            WHERE id LIKE '%Chapter_F%Development_Category%'
        """)

        doc = cur.fetchone()
        if not doc:
            print("Chapter F document not found")
            sys.exit(1)

        doc_id = doc[0]
        full_text = doc[2]

        print(f"Document: {doc[1]}")
        print(f"Full text length: {len(full_text):,} chars\n")

        # Look for section structure in full text
        import re

        # Find "Part" headings (e.g., "Part F.1", "Part F1", etc.)
        part_pattern = r'(?:Part\s+)?F\.?\d+[A-Z]?\s+[–-]\s+([^\n]+)'
        parts = re.findall(part_pattern, full_text, re.IGNORECASE)

        if parts:
            print("Found Part headings in full text:")
            for i, part in enumerate(parts[:20], 1):
                print(f"  Part F.{i}: {part.strip()}")

        # Also check regulatory_provisions for ref_numbers starting with F
        print("\n" + "="*80)
        print("CHAPTER F PROVISIONS BY REF NUMBER")
        print("="*80)

        cur.execute("""
            SELECT DISTINCT ref_number, section_header, LEFT(provision_text, 100)
            FROM regulatory_provisions
            WHERE document_id = %s
            AND ref_number ~ '^F\\.?\\d+'
            ORDER BY ref_number
            LIMIT 30
        """, (doc_id,))

        results = cur.fetchall()
        if results:
            print(f"\nFound {len(results)} F.x provisions:")
            for row in results:
                print(f"  {row[0]}: {row[1] or 'No header'}")
                if row[2]:
                    print(f"    {row[2]}...")

        # Look for table of contents in full text
        print("\n" + "="*80)
        print("SEARCHING FOR TABLE OF CONTENTS")
        print("="*80)

        # Find lines with "Part F" followed by page numbers
        toc_pattern = r'(Part F\.?\d+[A-Z]?.*?)\.{3,}\s*\d+'
        toc_entries = re.findall(toc_pattern, full_text)

        if toc_entries:
            print("\nTable of Contents entries:")
            for entry in toc_entries[:30]:
                print(f"  {entry.strip()}")

        # Look for development type keywords
        print("\n" + "="*80)
        print("DEVELOPMENT TYPES MENTIONED")
        print("="*80)

        dev_types = [
            'dwelling house',
            'dual occupancy',
            'multi dwelling',
            'residential flat',
            'manor house',
            'shop top housing',
            'boarding house',
            'child care',
            'place of public worship',
            'commercial',
            'retail',
            'industrial'
        ]

        for dev_type in dev_types:
            cur.execute("""
                SELECT COUNT(*)
                FROM regulatory_provisions
                WHERE document_id = %s
                AND provision_text ILIKE %s
            """, (doc_id, f'%{dev_type}%'))

            count = cur.fetchone()[0]
            if count > 0:
                print(f"  {dev_type}: {count} provisions")

        # Get first 5000 chars of full text to see TOC
        print("\n" + "="*80)
        print("FIRST 5000 CHARS OF CHAPTER F (Looking for TOC)")
        print("="*80)
        print(full_text[:5000])