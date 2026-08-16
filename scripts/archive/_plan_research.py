#!/usr/bin/env python3
"""Gather all data needed for the comprehensive plan."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# 1. PDF page numbers by council
print("=== PDF PAGE NUMBERS ===")
cur.execute("""
    SELECT source_council,
           COUNT(*) as total,
           SUM(CASE WHEN pdf_page IS NOT NULL THEN 1 ELSE 0 END) as has_page,
           SUM(CASE WHEN pdf_page IS NULL THEN 1 ELSE 0 END) as no_page
    FROM regulatory_provisions
    WHERE is_current = true
    GROUP BY source_council ORDER BY total DESC
""")
for row in cur.fetchall():
    print(f"  {row[0] or 'NULL'}: total={row[1]}, has_page={row[2]}, no_page={row[3]}")

# 2. LaTeX artifacts count
print("\n=== LATEX ARTIFACTS ===")
cur.execute("""
    SELECT source_council,
           COUNT(*) as latex_count
    FROM regulatory_provisions
    WHERE is_current = true
      AND (provision_text LIKE '%%\\mathrm%%'
           OR provision_text LIKE '%%\\mathsf%%'
           OR provision_text LIKE '%%$_{%%')
    GROUP BY source_council ORDER BY latex_count DESC
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0] or 'NULL'}: {row[1]} provisions with LaTeX")
else:
    print("  None found")

# 3. Registry state
print("\n=== DCP CHAPTER REGISTRY ===")
cur.execute("""
    SELECT council,
           COUNT(*) as chapters,
           SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
           SUM(CASE WHEN needs_extraction THEN 1 ELSE 0 END) as needs_extract,
           SUM(CASE WHEN r2_current_path IS NOT NULL THEN 1 ELSE 0 END) as has_r2,
           SUM(CASE WHEN page_start IS NOT NULL THEN 1 ELSE 0 END) as has_pages
    FROM dcp_chapter_registry
    GROUP BY council ORDER BY chapters DESC
""")
for row in cur.fetchall():
    print(f"  {row[0]}: chapters={row[1]}, active={row[2]}, needs_extract={row[3]}, has_r2={row[4]}, has_pages={row[5]}")

# 4. Extraction status breakdown
print("\n=== EXTRACTION STATUS ===")
cur.execute("""
    SELECT source_council, v2_extraction_status, COUNT(*)
    FROM regulatory_provisions
    WHERE is_current = true AND v2_extraction_status IS NOT NULL
    GROUP BY source_council, v2_extraction_status
    ORDER BY source_council, v2_extraction_status
""")
for row in cur.fetchall():
    print(f"  {row[0] or 'NULL'}: {row[1]} = {row[2]}")

# 5. Sample pdf_page values
print("\n=== SAMPLE PDF_PAGE VALUES ===")
cur.execute("""
    SELECT id, source_council, pdf_page, LEFT(provision_text, 80)
    FROM regulatory_provisions
    WHERE is_current = true AND pdf_page IS NOT NULL
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  id={row[0]} council={row[1]} page={row[2]} text={row[3]}")

# 6. Check document_id patterns
print("\n=== DOCUMENT_ID PATTERNS ===")
cur.execute("""
    SELECT document_id, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE is_current = true
    GROUP BY document_id
    ORDER BY cnt DESC
    LIMIT 15
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.close()
conn.close()
