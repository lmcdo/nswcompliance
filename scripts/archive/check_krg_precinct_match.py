import psycopg2, os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute("""
  SELECT section_header, COUNT(*) as n
  FROM regulatory_provisions
  WHERE source_council = 'ku-ring-gai'
    AND v2_structural_category = 'precinct'
    AND v2_dcp_layer = 'precinct'
    AND section_header IS NOT NULL
  GROUP BY section_header
  ORDER BY n DESC
  LIMIT 20
""")
print('=== KRG section_headers (top 20) ===')
for r in cur.fetchall():
    print(f'  {r[1]:4d}  {r[0]!r}')

cur.execute("""
  SELECT precinct_id, precinct_name, lga
  FROM dcp_precinct_boundaries
  WHERE LOWER(lga) LIKE '%ku%'
  ORDER BY precinct_id
""")
print('\n=== dcp_precinct_boundaries for KRG ===')
for r in cur.fetchall():
    print(f'  id={r[0]!r}  name={r[1]!r}  lga={r[2]!r}')

conn.close()
