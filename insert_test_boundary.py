import psycopg2

conn = psycopg2.connect(
    dbname='nsw_planning',
    user='postgres',
    password='Duffysql1!',
    host='localhost',
    port='5432'
)
cur = conn.cursor()

# Insert approximate boundary for Dulwich Hill North (Precinct 10_)
# Using a simple polygon around the Dulwich Hill area (covers 20 Pile St)
boundary_wkt = 'POLYGON((151.135 -33.910, 151.145 -33.910, 151.145 -33.900, 151.135 -33.900, 151.135 -33.910))'

cur.execute('''
    INSERT INTO dcp_precinct_boundaries
    (precinct_id, precinct_name, lga, former_council, boundary, confidence_score, extraction_method)
    VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s, %s)
    ON CONFLICT (precinct_id, lga) DO UPDATE
    SET boundary = ST_GeomFromText(%s, 4326),
        confidence_score = %s,
        extraction_method = %s
''', (
    '10_', 'Dulwich Hill North', 'INNER WEST', 'Marrickville',
    boundary_wkt, 0.5, 'manual_approximate',
    boundary_wkt, 0.5, 'manual_approximate'
))
conn.commit()
print('SUCCESS: Manually inserted boundary for Precinct 10_ (Dulwich Hill North)')
print('This covers approximately: 20 Pile St, Dulwich Hill 2203')
cur.close()
conn.close()
