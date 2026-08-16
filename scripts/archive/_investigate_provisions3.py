import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# 1. TOC entries for Leichhardt - what's actually in there after migration 015?
print("=== TOC entries for Leichhardt (normalised document_ids) ===")
cur.execute("""
  SELECT document_id, section_number, section_title, page_start, page_end
  FROM dcp_table_of_contents
  WHERE document_id ILIKE '%leichhardt_dcp_2013__%'
    AND document_id NOT ILIKE '%__17__%'
  ORDER BY document_id, page_start
  LIMIT 40
""")
for r in cur.fetchall(): print(' ', r)

# 2. How many provisions JOIN successfully after migration?
print("\n=== JOIN success rate after migration 015 ===")
cur.execute("""
  SELECT
    count(*) as total,
    count(t.section_number) as joined,
    count(*) - count(t.section_number) as no_toc_match
  FROM regulatory_provisions p
  LEFT JOIN dcp_table_of_contents t
    ON p.document_id = t.document_id
    AND p.pdf_page BETWEEN t.page_start AND t.page_end
  WHERE p.document_id ILIKE '%leichhardt%'
    AND p.is_current = TRUE
""")
for r in cur.fetchall(): print(' ', r)

# 3. v2_dcp_part distribution
print("\n=== v2_dcp_part distribution for Leichhardt ===")
cur.execute("""
  SELECT v2_dcp_part, count(*) as n
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%'
    AND is_current = TRUE
  GROUP BY v2_dcp_part ORDER BY n DESC LIMIT 20
""")
for r in cur.fetchall(): print(' ', r)

# 4. document_id formats in provisions
print("\n=== document_id formats in regulatory_provisions for Leichhardt ===")
cur.execute("""
  SELECT document_id, count(*) as n
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%' AND is_current = TRUE
  GROUP BY document_id ORDER BY n DESC LIMIT 15
""")
for r in cur.fetchall(): print(' ', r)

# 5. Section-level grouping after JOIN
print("\n=== Section-level grouping after TOC join ===")
cur.execute("""
  SELECT
    t.section_number,
    t.section_title,
    count(*) filter (where p.provision_type = 'control') as controls,
    count(*) filter (where p.provision_type = 'objective') as objectives
  FROM regulatory_provisions p
  JOIN dcp_table_of_contents t
    ON p.document_id = t.document_id
    AND p.pdf_page BETWEEN t.page_start AND t.page_end
  WHERE p.document_id ILIKE '%leichhardt%'
    AND p.is_current = TRUE
  GROUP BY t.section_number, t.section_title
  ORDER BY controls DESC
  LIMIT 20
""")
for r in cur.fetchall(): print(' ', r)

# 6. What does the API actually use for section_key? Check buildSectionKey logic
# The API joins on enrichWithTocSections and returns toc_section_number
# Let's verify what the old document_id rows look like
print("\n=== Old-format document_ids still in provisions? ===")
cur.execute("""
  SELECT count(*) FROM regulatory_provisions
  WHERE document_id ILIKE '%Leichhardt_DCP_2013__%3__%Part_A%' AND is_current = TRUE
""")
print('Old Part A format:', cur.fetchone())
cur.execute("""
  SELECT count(*) FROM regulatory_provisions
  WHERE document_id = 'Leichhardt_DCP_2013__part_a_introduction' AND is_current = TRUE
""")
print('New Part A format:', cur.fetchone())

conn.close()
