#!/usr/bin/env python3
"""Check PDF URL, page number, and image extraction status."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 60)
print("PDF LINK & IMAGE STATUS")
print("=" * 60)

# Get all columns
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
""")
columns = [row[0] for row in cur.fetchall()]

# Find relevant columns
url_cols = [c for c in columns if 'url' in c.lower() or 'link' in c.lower()]
page_cols = [c for c in columns if 'page' in c.lower()]
image_cols = [c for c in columns if 'image' in c.lower() or 'figure' in c.lower()]

print(f"\n1. Schema Analysis:")
print(f"   Total columns: {len(columns)}")
print(f"   URL columns: {url_cols}")
print(f"   Page columns: {page_cols}")
print(f"   Image columns: {image_cols}")

# Check URL coverage
if url_cols:
    for col in url_cols:
        cur.execute(f'SELECT COUNT(*) FROM regulatory_provisions WHERE {col} IS NOT NULL')
        count = cur.fetchone()[0]
        print(f"\n2. {col} coverage: {count}")

        # Sample
        cur.execute(f'SELECT DISTINCT {col} FROM regulatory_provisions WHERE {col} IS NOT NULL LIMIT 3')
        samples = cur.fetchall()
        for s in samples:
            if s[0]:
                print(f"   Sample: {s[0][:70]}...")

# Check page number coverage
if page_cols:
    for col in page_cols:
        cur.execute(f'SELECT COUNT(*) FROM regulatory_provisions WHERE {col} IS NOT NULL')
        count = cur.fetchone()[0]
        print(f"\n3. {col} coverage: {count}")

# Check for image tables
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    AND (table_name LIKE '%image%' OR table_name LIKE '%figure%' OR table_name LIKE '%asset%')
""")
image_tables = cur.fetchall()
print(f"\n4. Image-related tables: {[t[0] for t in image_tables] if image_tables else 'None'}")

# Check document_id format (this is how PDFs are referenced)
cur.execute('SELECT DISTINCT document_id FROM regulatory_provisions LIMIT 5')
doc_ids = cur.fetchall()
print(f"\n5. Document ID samples:")
for d in doc_ids:
    print(f"   {d[0]}")

# Check for provisions that reference figures
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_text ~* 'figure\\s*\\d|diagram|see\\s+map'
""")
figure_refs = cur.fetchone()[0]
print(f"\n6. Provisions referencing figures/diagrams: {figure_refs}")

conn.close()
