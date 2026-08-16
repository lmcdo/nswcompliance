import psycopg2, os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

councils = ['ku-ring-gai', 'waverley', 'woollahra', 'city-of-sydney']

for council in councils:
    print(f'\n{"="*70}')
    print(f'  {council.upper()}')
    print(f'{"="*70}')

    # Total precinct provisions and v2_precinct_id coverage
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(v2_precinct_id) as has_precinct_id,
            COUNT(DISTINCT v2_precinct_id) as distinct_precinct_ids
        FROM regulatory_provisions
        WHERE source_council = %s
          AND v2_dcp_layer = 'precinct'
    """, (council,))
    r = cur.fetchone()
    print(f'  Precinct provisions: {r[0]} total | {r[1]} have v2_precinct_id | {r[2]} distinct IDs')

    # Sample section_headers to understand structure
    cur.execute("""
        SELECT DISTINCT section_header, COUNT(*) as n
        FROM regulatory_provisions
        WHERE source_council = %s
          AND v2_dcp_layer = 'precinct'
          AND section_header IS NOT NULL
        GROUP BY section_header
        ORDER BY n DESC
        LIMIT 8
    """, (council,))
    rows = cur.fetchall()
    if rows:
        print(f'  section_header samples:')
        for r in rows:
            print(f'    {r[1]:4d}  {r[0]!r}')
    else:
        print(f'  section_header: (none / all NULL)')

    # Distinct v2_precinct_id values already set
    cur.execute("""
        SELECT DISTINCT v2_precinct_id, COUNT(*) as n
        FROM regulatory_provisions
        WHERE source_council = %s
          AND v2_dcp_layer = 'precinct'
          AND v2_precinct_id IS NOT NULL
        GROUP BY v2_precinct_id
        ORDER BY n DESC
        LIMIT 10
    """, (council,))
    rows = cur.fetchall()
    if rows:
        print(f'  v2_precinct_id values already set:')
        for r in rows:
            print(f'    {r[1]:4d}  {r[0]!r}')

    # PostGIS boundaries for this council
    cur.execute("""
        SELECT precinct_id, precinct_name
        FROM dcp_precinct_boundaries
        WHERE LOWER(lga) LIKE %s
        ORDER BY precinct_id
        LIMIT 15
    """, (f'%{council.replace("-", "%")}%',))
    rows = cur.fetchall()
    if rows:
        print(f'  PostGIS boundaries ({len(rows)} rows):')
        for r in rows:
            print(f'    id={r[0]!r}  name={r[1]!r}')
    else:
        print(f'  PostGIS boundaries: (none)')

conn.close()
