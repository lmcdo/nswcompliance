import psycopg2, os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute('SELECT DISTINCT council FROM dcp_precinct_localities')
print('councils in dcp_precinct_localities:', [r[0] for r in cur.fetchall()])

addr = '20 LACKEY STREET, SUMMER HILL NSW 2130'
for council in ['ashfield', 'Ashfield', 'inner_west', 'Inner West']:
    cur.execute("""
        SELECT precinct_id FROM dcp_precinct_localities
        WHERE LOWER(council) = LOWER(%s)
          AND UPPER(%s) LIKE ('%%' || locality || '%%')
        ORDER BY LENGTH(locality) DESC
    """, (council, addr))
    rows = cur.fetchall()
    print(f'  council={council!r} -> {[r[0] for r in rows]}')

conn.close()
