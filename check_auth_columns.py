import psycopg2

conn = psycopg2.connect(host='127.0.0.1', database='nsw_planning', user='postgres', port=5432)
cursor = conn.cursor()

cursor.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'planning_provisions'
    AND table_schema = 'authoritative'
    ORDER BY ordinal_position
""")

columns = [r[0] for r in cursor.fetchall()]
print('Authoritative planning_provisions columns:')
for col in columns:
    print(f'  - {col}')

conn.close()