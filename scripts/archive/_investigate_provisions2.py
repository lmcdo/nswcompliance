import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check dcp_table_of_contents columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='dcp_table_of_contents' ORDER BY ordinal_position")
print('TOC columns:', [r[0] for r in cur.fetchall()])

# Sample TOC entries for Leichhardt
cur.execute("""
  SELECT * FROM dcp_table_of_contents
  WHERE document_id ILIKE '%leichhardt%'
  LIMIT 5
""")
rows = cur.fetchall()
print('\nTOC sample:', rows[:3] if rows else 'NONE')

# Provision structure: how many are objectives vs controls, and what's the section-level grouping?
# The key question: how many SECTIONS (not provisions) does a planner actually address?
print("\n=== Unique section headers (v2_dcp_part / v2_section) for Leichhardt controls ===")
cur.execute("""
  SELECT column_name FROM information_schema.columns
  WHERE table_name='regulatory_provisions'
    AND column_name IN ('v2_dcp_part','v2_section','section_header','v2_structural_category','v2_topic','pdf_page')
""")
print('Available columns:', [r[0] for r in cur.fetchall()])

# How many unique section_header values for Leichhardt controls?
cur.execute("""
  SELECT section_header, count(*) as n
  FROM regulatory_provisions
  WHERE document_id ILIKE '%leichhardt%'
    AND is_current = TRUE
    AND provision_type = 'control'
  GROUP BY section_header
  ORDER BY n DESC
  LIMIT 30
""")
rows = cur.fetchall()
print(f'\nUnique section_headers for controls ({len(rows)} shown):')
for r in rows: print(' ', r)

conn.close()
