import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

# Check for LEP Clause 5.x provisions
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE ref_number LIKE '5.%'
""")
count = cur.fetchone()[0]
print(f"LEP Clause 5.x provisions in database: {count}")

# Check for secondary dwelling provisions
cur.execute("""
    SELECT ref_number, provision_text
    FROM regulatory_provisions
    WHERE ref_number LIKE '5.%'
      AND provision_text ILIKE '%secondary%dwelling%'
    LIMIT 2
""")

rows = cur.fetchall()
if rows:
    print("\nSample LEP Clause 5.x (secondary dwellings):")
    for row in rows:
        print(f"  Clause {row[0]}: {row[1][:150]}...")
else:
    print("\nNo LEP Clause 5.x provisions found for secondary dwellings")

# Check what types of provisions we have
cur.execute("""
    SELECT provision_type, COUNT(*)
    FROM regulatory_provisions
    WHERE ref_number LIKE '5.%'
    GROUP BY provision_type
    ORDER BY COUNT(*) DESC
    LIMIT 5
""")

print("\nProvision types for Clause 5.x:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} provisions")

conn.close()
