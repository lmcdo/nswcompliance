#!/usr/bin/env python3
"""
Phase 1: Strip PDF headers from Ashfield Chapter F provisions

The provision_text has garbage PDF headers like:
  Chapter F – Development Category Guidelines
  Part 1– Residential – Low Density Zone
             Comprehensive Inner West DCP 2016
               page 5

This script removes these headers to clean the provision text.
"""
import re
import os
import psycopg2

# Connect to LOCAL database (frontend uses this)
LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"

def clean_pdf_headers():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()

    print("=" * 80)
    print("Phase 1: Cleaning PDF headers from Ashfield provisions")
    print("=" * 80)

    # Pattern to match PDF headers at start of provision_text
    # Matches: "Chapter F ... Comprehensive Inner West DCP 2016 ... page XX"
    header_pattern = r'^(Chapter [A-Z]\d?\s*[-–—]\s*[^\n]+\n[^\n]*\n\s*Comprehensive Inner West DCP 2016\s*\n\s*page \d+\s*\n?)'

    # Get provisions with PDF headers
    cur.execute("""
        SELECT id, provision_text
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND provision_text ~ '^Chapter [A-Z]'
          AND provision_text ILIKE '%Comprehensive Inner West DCP 2016%'
    """)

    provisions = cur.fetchall()
    print(f"Found {len(provisions)} provisions with PDF headers")

    updated = 0
    for prov_id, text in provisions:
        # Try to strip the header
        cleaned = re.sub(header_pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Also try a simpler pattern for variations
        if cleaned == text:
            # Try alternate pattern
            alt_pattern = r'^Chapter [A-Z].*?page \d+\s*\n?'
            cleaned = re.sub(alt_pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

        if cleaned != text and len(cleaned) > 50:  # Ensure we didn't strip too much
            cur.execute("""
                UPDATE regulatory_provisions
                SET provision_text = %s
                WHERE id = %s
            """, (cleaned.strip(), prov_id))
            updated += 1

    conn.commit()
    print(f"Updated {updated} provisions")

    # Show sample of cleaned text
    cur.execute("""
        SELECT LEFT(provision_text, 200)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%Chapter F%Development Category%'
        LIMIT 3
    """)

    print("\nSample cleaned provisions:")
    for row in cur.fetchall():
        print(f"  {row[0][:150]}...")

    conn.close()
    return updated

if __name__ == "__main__":
    clean_pdf_headers()
