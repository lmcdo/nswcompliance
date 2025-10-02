from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check what permission statuses exist
cur.execute("""
    SELECT DISTINCT permission_status, COUNT(*) 
    FROM development_permissions 
    GROUP BY permission_status 
    ORDER BY COUNT(*) DESC
""")

print("Permission statuses in database:")
for status, count in cur.fetchall():
    print(f"  {status:20} {count:,} records")

# Check R2 + dwelling_house
cur.execute("""
    SELECT zone, development_type, permission_status, source_type
    FROM development_permissions
    WHERE zone = 'R2' AND development_type = 'dwelling_house'
    LIMIT 5
""")

print("\nR2 + dwelling_house records:")
for row in cur.fetchall():
    print(f"  {row[0]} + {row[1]} = {row[2]} (source: {row[3]})")

# Check our new exempt/complying records
cur.execute("""
    SELECT zone, development_type, permission_status, source_type
    FROM development_permissions
    WHERE source_type ILIKE '%exempt%'
    ORDER BY zone, development_type
    LIMIT 10
""")

print("\nOur exempt/complying records:")
for row in cur.fetchall():
    print(f"  {row[0]} + {row[1]} = {row[2]} (source: {row[3]})")

conn.close()
