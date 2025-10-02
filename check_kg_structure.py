import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

print("\n=== All Tables ===\n")
cur.execute("""
  SELECT table_name
  FROM information_schema.tables
  WHERE table_schema = 'public'
  ORDER BY table_name;
""")

for row in cur.fetchall():
    print(f"  - {row[0]}")

print("\n\n=== Entities/Relationships Tables ===\n")
cur.execute("""
  SELECT table_name
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND (
      table_name LIKE '%entit%'
      OR table_name LIKE '%relationship%'
      OR table_name LIKE '%graph%'
      OR table_name LIKE '%kg%'
    )
  ORDER BY table_name;
""")

kg_tables = cur.fetchall()
for row in kg_tables:
    print(f"  - {row[0]}")

if kg_tables:
    print("\n\n=== Sample from Knowledge Graph Tables ===\n")
    for table in kg_tables[:3]:
        table_name = table[0]
        print(f"\n{table_name}:")
        cur.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        rows = cur.fetchall()
        if rows:
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position;")
            columns = [r[0] for r in cur.fetchall()]
            print(f"  Columns: {', '.join(columns)}")
            print(f"  Sample rows: {len(rows)}")
        else:
            print(f"  (empty)")

print("\n\n=== Provision Type Distribution ===\n")
cur.execute("""
  SELECT
    document_category,
    COUNT(DISTINCT provision_type) as unique_types,
    COUNT(*) as total_provisions
  FROM provisions_with_category
  WHERE provision_type IS NOT NULL
  GROUP BY document_category
  ORDER BY document_category;
""")

print(f"{'Category':<15} | {'Unique Types':<15} | Total Provisions")
print("-" * 60)
for row in cur.fetchall():
    print(f"{row[0]:<15} | {row[1]:<15} | {row[2]}")

print("\n\n=== Sample Provision Types for Each Category ===\n")
for category in ['SEPP', 'LEP', 'DCP']:
    cur.execute(f"""
      SELECT DISTINCT provision_type
      FROM provisions_with_category
      WHERE document_category = '{category}'
        AND provision_type IS NOT NULL
      ORDER BY provision_type
      LIMIT 10;
    """)

    print(f"\n{category}:")
    for row in cur.fetchall():
        print(f"  - {row[0]}")

cur.close()
conn.close()