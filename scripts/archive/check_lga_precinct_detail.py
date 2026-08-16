import psycopg2, os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Waverley: what does the section_header separator actually look like?
# (the terminal showed mojibake — check raw bytes)
cur.execute("""
    SELECT section_header
    FROM regulatory_provisions
    WHERE source_council = 'waverley'
      AND v2_dcp_layer = 'precinct'
      AND section_header IS NOT NULL
    LIMIT 3
""")
print('=== Waverley section_header raw ===')
for r in cur.fetchall():
    h = r[0]
    print(f'  repr: {h!r}')
    parts = h.split(' \u2014 ')   # em-dash
    print(f'  split on em-dash: {parts}')
    parts2 = h.split(' - ')
    print(f'  split on hyphen:  {parts2}')

# Waverley: how many distinct first-tokens would we get?
cur.execute("""
    SELECT
        SPLIT_PART(section_header, ' — ', 1) as precinct_token,
        COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'waverley'
      AND v2_dcp_layer = 'precinct'
      AND section_header IS NOT NULL
    GROUP BY 1
    ORDER BY n DESC
""")
print('\n=== Waverley: SPLIT_PART on em-dash ===')
for r in cur.fetchall():
    print(f'  {r[1]:4d}  {r[0]!r}')

# KRG: check ALL layers, not just precinct
cur.execute("""
    SELECT v2_dcp_layer, v2_structural_category, COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'ku-ring-gai'
    GROUP BY 1, 2
    ORDER BY n DESC
    LIMIT 15
""")
print('\n=== KRG: layer/category breakdown ===')
for r in cur.fetchall():
    print(f'  layer={r[0]!r}  cat={r[1]!r}  n={r[2]}')

# KRG: what are the section_headers (any layer)?
cur.execute("""
    SELECT DISTINCT section_header, v2_dcp_layer, COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'ku-ring-gai'
      AND section_header IS NOT NULL
      AND section_header LIKE '%14%'
    GROUP BY 1, 2
    ORDER BY n DESC
    LIMIT 15
""")
print('\n=== KRG: section_headers containing "14" ===')
for r in cur.fetchall():
    print(f'  {r[2]:4d}  layer={r[1]!r}  {r[0]!r}')

conn.close()
