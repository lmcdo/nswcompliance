import psycopg2

conn = psycopg2.connect(
    host='127.0.0.1',
    database='nsw_planning',
    user='postgres',
    port=5432
)

cursor = conn.cursor()

# Check what's in regulatory_provisions
cursor.execute("""
    SELECT
        provision_type,
        document_type,
        zone,
        development_type,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE zone IS NOT NULL
    GROUP BY provision_type, document_type, zone, development_type
    ORDER BY count DESC
    LIMIT 20
""")

print("Existing data in regulatory_provisions table:")
print("-" * 60)
for row in cursor.fetchall():
    print(f"Type: {row[0]}, Doc: {row[1]}, Zone: {row[2]}, Dev: {row[3]}, Count: {row[4]}")

# Check if data already maps to zones
cursor.execute("""
    SELECT DISTINCT zone
    FROM regulatory_provisions
    WHERE zone IS NOT NULL
    ORDER BY zone
""")

zones = [r[0] for r in cursor.fetchall()]
print(f"\nZones with data: {zones}")

# Check development types
cursor.execute("""
    SELECT DISTINCT development_type
    FROM regulatory_provisions
    WHERE development_type IS NOT NULL
    ORDER BY development_type
    LIMIT 10
""")

dev_types = [r[0] for r in cursor.fetchall()]
print(f"\nDevelopment types: {dev_types}")

conn.close()