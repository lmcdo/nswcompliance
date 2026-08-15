import psycopg2, os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Find actual source_council values that look like KRG
cur.execute("""
    SELECT DISTINCT source_council, COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council ILIKE '%ku%'
       OR source_council ILIKE '%ring%'
    GROUP BY 1 ORDER BY n DESC
""")
print('=== Matching source_council values ===')
for r in cur.fetchall():
    print(f'  {r[1]:6d}  {r[0]!r}')

# Also check all councils for context
cur.execute("""
    SELECT DISTINCT source_council, COUNT(*) as n
    FROM regulatory_provisions
    GROUP BY 1 ORDER BY n DESC
""")
print('\n=== All source_council values ===')
for r in cur.fetchall():
    print(f'  {r[1]:6d}  {r[0]!r}')

conn.close()
