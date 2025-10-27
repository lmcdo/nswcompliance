import psycopg2
conn = psycopg2.connect(host='127.0.0.1', database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'regulatory_provisions_canonical'
    ORDER BY ordinal_position
""")
canon_cols = [row[0] for row in cur.fetchall()]

cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
""")
base_cols = [row[0] for row in cur.fetchall()]

print("Canonical view columns:")
for col in canon_cols:
    print(f"  {col}")

print("\nBase table has but canonical doesn't:")
for col in base_cols:
    if col not in canon_cols:
        print(f"  {col}")

cur.close()
conn.close()
