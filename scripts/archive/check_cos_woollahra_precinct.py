import psycopg2, os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# What columns exist?
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print('Columns:', cols)

# CoS: precinct sample with available columns
print('\n=== City of Sydney: precinct provisions sample ===')
cur.execute("""
    SELECT ref_number, section_header, v2_precinct_id, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE source_council = 'city_of_sydney' AND v2_dcp_layer = 'precinct'
    LIMIT 10
""")
for r in cur.fetchall():
    print(f'  ref={r[0]!r}  precinct_id={r[2]!r}')
    print(f'    section_header={r[1]!r}')
    print(f'    text={r[3]!r}')
    print()

# Woollahra: breakdown
print('=== Woollahra: all layers ===')
cur.execute("""
    SELECT v2_dcp_layer, COUNT(*) as n,
           COUNT(DISTINCT section_header) as distinct_headers
    FROM regulatory_provisions
    WHERE source_council = 'woollahra'
    GROUP BY 1 ORDER BY n DESC
""")
for r in cur.fetchall():
    print(f'  layer={r[0]!r}  n={r[1]}  distinct_headers={r[2]}')

# Woollahra: what does section_header look like?
print('\n=== Woollahra: section_header samples ===')
cur.execute("""
    SELECT DISTINCT section_header, v2_dcp_layer, COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND section_header IS NOT NULL
    GROUP BY 1, 2 ORDER BY n DESC LIMIT 15
""")
for r in cur.fetchall():
    print(f'  {r[2]:4d}  layer={r[1]!r}  {r[0]!r}')

conn.close()
