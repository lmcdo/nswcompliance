import psycopg2, os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

councils = {
    'ku_ring_gai':    'Ku-ring-gai',
    'waverley':       'Waverley',
    'woollahra':      'Woollahra',
    'city_of_sydney': 'City of Sydney',
}

for council_key, label in councils.items():
    print(f'\n{"="*70}')
    print(f'  {label}  (source_council={council_key!r})')
    print(f'{"="*70}')

    cur.execute("""
        SELECT v2_dcp_layer, COUNT(*) as n
        FROM regulatory_provisions
        WHERE source_council = %s
        GROUP BY 1 ORDER BY n DESC
    """, (council_key,))
    print('  Layer breakdown:')
    for r in cur.fetchall():
        print(f'    {r[1]:5d}  {r[0]!r}')

    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(v2_precinct_id) as has_id,
            COUNT(DISTINCT v2_precinct_id) as distinct_ids
        FROM regulatory_provisions
        WHERE source_council = %s AND v2_dcp_layer = 'precinct'
    """, (council_key,))
    r = cur.fetchone()
    print(f'  Precinct layer: {r[0]} total | {r[1]} have v2_precinct_id | {r[2]} distinct')

    cur.execute("""
        SELECT DISTINCT section_header, COUNT(*) as n
        FROM regulatory_provisions
        WHERE source_council = %s AND v2_dcp_layer = 'precinct'
          AND section_header IS NOT NULL
        GROUP BY 1 ORDER BY n DESC LIMIT 8
    """, (council_key,))
    rows = cur.fetchall()
    if rows:
        print(f'  section_header samples:')
        for r in rows:
            h = r[0]
            first_token = h.split(' \u2014 ')[0] if ' \u2014 ' in h else h[:60]
            print(f'    {r[1]:4d}  first_token={first_token!r}')

    # PostGIS boundaries — try different LGA name formats
    for lga_pat in [label, label.lower(), council_key.replace('_', '-'), council_key.replace('_', ' ')]:
        cur.execute("""
            SELECT precinct_id, precinct_name FROM dcp_precinct_boundaries
            WHERE LOWER(lga) ILIKE %s ORDER BY precinct_id LIMIT 8
        """, (f'%{lga_pat.lower()}%',))
        rows = cur.fetchall()
        if rows:
            print(f'  PostGIS boundaries (lga~{lga_pat!r}):')
            for r in rows:
                print(f'    id={r[0]!r}  name={r[1]!r}')
            break
    else:
        print(f'  PostGIS boundaries: (none)')

conn.close()
