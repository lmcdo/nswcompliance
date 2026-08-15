import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Marrickville TOC JOIN success rate
cur.execute("""
  SELECT
    count(*) as total,
    count(t.section_number) as joined,
    count(*) - count(t.section_number) as no_toc_match
  FROM regulatory_provisions p
  LEFT JOIN dcp_table_of_contents t
    ON p.document_id = t.document_id
    AND p.pdf_page BETWEEN t.page_start AND t.page_end
  WHERE p.document_id ILIKE '%marrickville%'
    AND p.is_current = TRUE
""")
print('Marrickville TOC JOIN rate:', cur.fetchone())

# Ashfield TOC JOIN success rate
cur.execute("""
  SELECT
    count(*) as total,
    count(t.section_number) as joined,
    count(*) - count(t.section_number) as no_toc_match
  FROM regulatory_provisions p
  LEFT JOIN dcp_table_of_contents t
    ON p.document_id = t.document_id
    AND p.pdf_page BETWEEN t.page_start AND t.page_end
  WHERE p.document_id ILIKE '%ashfield%'
    AND p.is_current = TRUE
""")
print('Ashfield TOC JOIN rate:', cur.fetchone())

# Leichhardt old-format document_ids vs TOC new-format
# Can the fuzzy JOIN actually match them?
cur.execute("""
  SELECT
    p.document_id as prov_doc,
    REPLACE(REPLACE(REPLACE(REPLACE(p.document_id, '__-__', '__'), '_-_', '_'), '__', '_'), '-', '_') as normalized,
    count(*) as n
  FROM regulatory_provisions p
  WHERE p.document_id LIKE 'Leichhardt DCP 2013%' AND p.is_current = TRUE
  GROUP BY p.document_id,
    REPLACE(REPLACE(REPLACE(REPLACE(p.document_id, '__-__', '__'), '_-_', '_'), '__', '_'), '-', '_')
  ORDER BY n DESC
""")
print('\nLeichhardt old-format doc_id normalized forms:')
for r in cur.fetchall(): print(' ', r)

# What do Marrickville provision document_ids look like?
cur.execute("""
  SELECT document_id, count(*) as n FROM regulatory_provisions
  WHERE document_id ILIKE '%marrickville%' AND is_current = TRUE
  GROUP BY document_id ORDER BY n DESC LIMIT 10
""")
print('\nMarrickville provision document_ids:')
for r in cur.fetchall(): print(' ', r)

# Marrickville TOC document_ids
cur.execute("""
  SELECT DISTINCT document_id FROM dcp_table_of_contents
  WHERE document_id ILIKE '%marrickville%'
  LIMIT 10
""")
print('\nMarrickville TOC document_ids:')
for r in cur.fetchall(): print(' ', r)

# Section count that WOULD exist if TOC JOIN worked for Leichhardt
# Use the TOC sections directly
cur.execute("""
  SELECT count(DISTINCT section_number) as unique_sections, count(*) as total_toc_rows
  FROM dcp_table_of_contents
  WHERE document_id ILIKE '%leichhardt_dcp_2013__%'
    AND document_id NOT ILIKE '%appendix%'
    AND document_id NOT ILIKE '%__15__%'
    AND document_id NOT ILIKE '%__13__%'
    AND document_id NOT ILIKE '%__17__%'
""")
print('\nLeichhardt unique TOC sections (post-migration, non-appendix):', cur.fetchone())

# Marrickville unique sections
cur.execute("""
  SELECT count(DISTINCT section_number) as unique_sections
  FROM dcp_table_of_contents
  WHERE document_id ILIKE '%marrickville%'
""")
print('Marrickville unique TOC sections:', cur.fetchone())

conn.close()
