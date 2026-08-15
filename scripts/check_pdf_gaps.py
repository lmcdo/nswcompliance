#!/usr/bin/env python3
"""Check gaps in PDF linking and image coverage."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 60)
print("PDF LINKING GAPS ANALYSIS")
print("=" * 60)

# Actionable provisions coverage
cur.execute('''
    SELECT
        COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as with_pdf_page,
        COUNT(*) FILTER (WHERE pdf_page IS NULL) as without_pdf_page,
        COUNT(*) FILTER (WHERE pdf_page_image_url IS NOT NULL) as with_image_url,
        COUNT(*) FILTER (WHERE pdf_page_image_url IS NULL) as without_image_url,
        COUNT(*) as total
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
''')
row = cur.fetchone()
print(f"\n1. ACTIONABLE PROVISIONS ({row[4]} total):")
print(f"   With pdf_page: {row[0]} ({row[0]/row[4]*100:.1f}%)")
print(f"   Without pdf_page: {row[1]} ({row[1]/row[4]*100:.1f}%)")
print(f"   With image_url: {row[2]} ({row[2]/row[4]*100:.1f}%)")
print(f"   Without image_url: {row[3]} ({row[3]/row[4]*100:.1f}%)")

# Which documents are missing pdf_page?
cur.execute('''
    SELECT document_id, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true AND pdf_page IS NULL
    GROUP BY document_id
    ORDER BY count DESC
    LIMIT 10
''')
rows = cur.fetchall()
print(f"\n2. Documents with actionable provisions MISSING pdf_page:")
for doc, count in rows:
    print(f"   {count:4d} | {doc[:60]}")

# Which documents are missing image URLs?
cur.execute('''
    SELECT document_id, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true AND pdf_page_image_url IS NULL
    GROUP BY document_id
    ORDER BY count DESC
    LIMIT 10
''')
rows = cur.fetchall()
print(f"\n3. Documents with actionable provisions MISSING image_url:")
for doc, count in rows:
    print(f"   {count:4d} | {doc[:60]}")

# Check if there's a pattern for what HAS image URLs
cur.execute('''
    SELECT document_id, COUNT(*) as count
    FROM regulatory_provisions
    WHERE pdf_page_image_url IS NOT NULL
    GROUP BY document_id
    ORDER BY count DESC
    LIMIT 10
''')
rows = cur.fetchall()
print(f"\n4. Documents WITH image_urls:")
for doc, count in rows:
    print(f"   {count:4d} | {doc[:60]}")

# Check figure references without images
cur.execute('''
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND provision_text ~* 'figure\\s*\\d|see\\s+figure|refer.*figure'
    AND pdf_page_image_url IS NULL
''')
figure_no_image = cur.fetchone()[0]
print(f"\n5. Actionable provisions referencing figures but NO image URL: {figure_no_image}")

conn.close()
