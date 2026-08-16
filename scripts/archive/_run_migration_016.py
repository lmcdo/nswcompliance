import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.autocommit = False
cur = conn.cursor()

# Read and execute migration 016
with open('migrations/016_toc_add_leichhardt_old_format_docids.sql', 'r') as f:
    sql = f.read()

try:
    cur.execute(sql)
    conn.commit()
    print("Migration 016 committed successfully.")
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
    raise

# Verify: overall Leichhardt JOIN rate post-migration
cur.execute("""
    SELECT
        count(*) as total,
        count(t.section_number) as joined,
        round(100.0 * count(t.section_number) / count(*), 1) as pct
    FROM regulatory_provisions p
    LEFT JOIN dcp_table_of_contents t
        ON p.document_id = t.document_id
        AND p.pdf_page BETWEEN t.page_start AND t.page_end
    WHERE p.document_id ILIKE '%leichhardt%'
        AND p.is_current = TRUE
""")
r = cur.fetchone()
print(f"\nPost-migration Leichhardt TOC JOIN rate: {r[1]}/{r[0]} ({r[2]}%)")

# Per-chapter breakdown
cur.execute("""
    SELECT
        p.document_id,
        count(*) as total,
        count(t.section_number) as joined
    FROM regulatory_provisions p
    LEFT JOIN dcp_table_of_contents t
        ON p.document_id = t.document_id
        AND p.pdf_page BETWEEN t.page_start AND t.page_end
    WHERE p.document_id ILIKE '%leichhardt%'
        AND p.is_current = TRUE
    GROUP BY p.document_id
    ORDER BY total DESC
""")
print("\nPer-chapter:")
for r in cur.fetchall():
    pct = 100 * r[2] / r[1] if r[1] else 0
    label = r[0][:60]
    print(f"  {pct:5.0f}%  {r[2]:4}/{r[1]:4}  {label}")

# Count old-format TOC rows now in the table
cur.execute("""
    SELECT document_id, count(*)
    FROM dcp_table_of_contents
    WHERE document_id LIKE 'Leichhardt DCP 2013%'
    GROUP BY document_id ORDER BY count(*) DESC
""")
print("\nNew old-format TOC rows inserted:")
for r in cur.fetchall():
    print(f"  {r[1]:3} rows  {r[0]}")

conn.close()
