import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# 1. What provision types exist for Leichhardt?
print("=== v2_provision_type distribution ===")
cur.execute("""
  SELECT v2_provision_type, count(*) as n
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%' AND is_current = TRUE
  GROUP BY v2_provision_type ORDER BY n DESC
""")
for r in cur.fetchall(): print(' ', r)

# 2. What structural categories exist?
print("\n=== v2_structural_category distribution ===")
cur.execute("""
  SELECT v2_structural_category, count(*) as n
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%' AND is_current = TRUE
  GROUP BY v2_structural_category ORDER BY n DESC
""")
for r in cur.fetchall(): print(' ', r)

# 3. What v2_topic distribution looks like?
print("\n=== v2_topic distribution (top 20) ===")
cur.execute("""
  SELECT v2_topic, count(*) as n
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%' AND is_current = TRUE
  GROUP BY v2_topic ORDER BY n DESC LIMIT 20
""")
for r in cur.fetchall(): print(' ', r)

# 4. Of the ~1306 assessable provisions — what breakdown by type?
print("\n=== Actionable + control-type breakdown ===")
cur.execute("""
  SELECT
    v2_is_actionable,
    v2_provision_type,
    count(*) as n
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%' AND is_current = TRUE
  GROUP BY v2_is_actionable, v2_provision_type ORDER BY n DESC
""")
for r in cur.fetchall(): print(' ', r)

# 5. Sample of actual control provisions (the assessable ones)
print("\n=== Sample assessable control provisions (10) ===")
cur.execute("""
  SELECT id, v2_topic, v2_structural_category, substring(provision_text, 1, 120) as text
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%'
    AND is_current = TRUE
    AND v2_is_actionable = TRUE
    AND v2_provision_type = 'control'
  LIMIT 10
""")
for r in cur.fetchall(): print(' ', r)

# 6. How many provisions per document_id (chapter)?
print("\n=== Provisions per chapter (document_id) ===")
cur.execute("""
  SELECT document_id,
    count(*) as total,
    count(*) filter (where v2_provision_type = 'control') as controls,
    count(*) filter (where v2_provision_type = 'objective') as objectives
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%' AND is_current = TRUE
  GROUP BY document_id ORDER BY total DESC
""")
for r in cur.fetchall(): print(' ', r)

# 7. How many provisions per toc_section_number (after migration 015)?
print("\n=== Provisions per toc_section (joined) - top 20 ===")
cur.execute("""
  SELECT t.section_number, t.title, count(p.id) as n
  FROM regulatory_provisions p
  JOIN dcp_table_of_contents t
    ON p.document_id = t.document_id
    AND p.pdf_page BETWEEN t.page_start AND t.page_end
  WHERE p.document_id ILIKE '%leichhardt%' AND p.is_current = TRUE
  GROUP BY t.section_number, t.title
  ORDER BY n DESC LIMIT 20
""")
for r in cur.fetchall(): print(' ', r)

conn.close()
