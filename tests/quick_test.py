"""Check dcp_general_provisions structure"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres@127.0.0.1:5432/nsw_planning')
cur = conn.cursor()

print("=" * 70)
print("DCP_GENERAL_PROVISIONS DATA CHECK")
print("=" * 70)

# Check LGA values
cur.execute("""
    SELECT DISTINCT lga, COUNT(*)
    FROM dcp_general_provisions
    GROUP BY lga
""")
print("\nLGA values in dcp_general_provisions:")
for row in cur.fetchall():
    print(f"  '{row[0]}': {row[1]}")

# Check what development_types look like
cur.execute("""
    SELECT development_types, COUNT(*)
    FROM dcp_general_provisions
    GROUP BY development_types
    ORDER BY 2 DESC
    LIMIT 10
""")
print("\nDevelopment_types arrays:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Sample some actual records
cur.execute("""
    SELECT id, lga, part_number, LEFT(provision_text, 80), development_types
    FROM dcp_general_provisions
    LIMIT 5
""")
print("\nSample records:")
for row in cur.fetchall():
    print(f"  id={row[0]}, lga='{row[1]}', part={row[2]}")
    print(f"    text: {row[3]}...")
    print(f"    dev_types: {row[4]}")

# Check applicable_zones
cur.execute("""
    SELECT applicable_zones, COUNT(*)
    FROM dcp_general_provisions
    GROUP BY applicable_zones
    ORDER BY 2 DESC
    LIMIT 10
""")
print("\nApplicable_zones arrays:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
