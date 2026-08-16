import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# 1. section_header fill rate for old-format Leichhardt provisions
cur.execute("""
  SELECT
    count(*) filter (where section_header is not null and section_header != '') as has_header,
    count(*) filter (where section_header is null or section_header = '') as no_header,
    count(*) as total
  FROM regulatory_provisions
  WHERE document_id LIKE 'Leichhardt DCP 2013%' AND is_current = TRUE
""")
print('section_header fill rate (old format provisions):', cur.fetchone())

# 2. Sample section_header values for old-format provisions
cur.execute("""
  SELECT section_header, count(*) as n
  FROM regulatory_provisions
  WHERE document_id LIKE 'Leichhardt DCP 2013%' AND is_current = TRUE
    AND section_header IS NOT NULL AND section_header != ''
  GROUP BY section_header ORDER BY n DESC LIMIT 20
""")
print('\nTop section_header values (old format):')
for r in cur.fetchall(): print(' ', r)

# 3. Marrickville and Ashfield TOC state
cur.execute("""
  SELECT count(*) FROM dcp_table_of_contents
  WHERE document_id ILIKE '%marrickville%'
""")
print('\nMarrickville TOC rows:', cur.fetchone())

cur.execute("""
  SELECT count(*) FROM dcp_table_of_contents
  WHERE document_id ILIKE '%ashfield%'
""")
print('Ashfield TOC rows:', cur.fetchone())

# 4. What are the section_header patterns? Does inferSectionNumberFromHeader work on them?
cur.execute("""
  SELECT section_header
  FROM regulatory_provisions
  WHERE document_id LIKE 'Leichhardt DCP 2013%' AND is_current = TRUE
    AND section_header IS NOT NULL AND section_header != ''
  LIMIT 15
""")
print('\nSample section_header raw values:')
for r in cur.fetchall(): print(' ', repr(r[0]))

# 5. Check globalProgress fields — does ProvisionsByTocStructure pass all required fields?
# The NaN source: DAModeCard uses autoChapterDismissed, questionnaireScoped, heritageElementScoped
# but globalProgress in ProvisionsByTocStructure only returns:
# { total, triaged, chapterDismissed, topicDismissed, suppressed, scopeTotal, assessed, remaining }
# MISSING: autoChapterDismissed, questionnaireScoped, heritageElementScoped
print('\n=== NaN analysis: DAModeCard fields vs globalProgress fields ===')
print('DAModeCard expects: total, triaged, suppressed, chapterDismissed, autoChapterDismissed, topicDismissed, questionnaireScoped, heritageElementScoped, scopeTotal, assessed, remaining')
print('ProvisionsByTocStructure globalProgress returns: total, triaged, chapterDismissed, topicDismissed, suppressed, scopeTotal, assessed, remaining')
print('MISSING from globalProgress: autoChapterDismissed, questionnaireScoped, heritageElementScoped')
print('Any undefined + number = NaN => inScope = NaN')

# 6. Marrickville and Ashfield provision counts for comparison
cur.execute("""
  SELECT
    CASE WHEN document_id ILIKE '%marrickville%' THEN 'marrickville'
         WHEN document_id ILIKE '%ashfield%' THEN 'ashfield' END as council,
    count(*) as total,
    count(*) filter (where provision_type = 'control') as controls,
    count(*) filter (where provision_type = 'objective') as objectives
  FROM regulatory_provisions
  WHERE (document_id ILIKE '%marrickville%' OR document_id ILIKE '%ashfield%')
    AND is_current = TRUE
  GROUP BY 1
""")
print('\nMarrickville/Ashfield provision counts:')
for r in cur.fetchall(): print(' ', r)

conn.close()
