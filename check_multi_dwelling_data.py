from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check E1 + residential_flat_building
cur.execute("""
    SELECT development_type, permission_status, source_type
    FROM development_permissions
    WHERE zone = 'E1' AND development_type = 'residential_flat_building'
""")

print("E1 + residential_flat_building:")
result = cur.fetchone()
if result:
    print(f"  {result[0]} = {result[1]} ({result[2]})")
else:
    print("  NOT FOUND")

# Check R2 + residential_flat_building  
cur.execute("""
    SELECT development_type, permission_status, source_type
    FROM development_permissions
    WHERE zone = 'R2' AND development_type = 'residential_flat_building'
""")

print("\nR2 + residential_flat_building:")
result = cur.fetchone()
if result:
    print(f"  {result[0]} = {result[1]} ({result[2]})")
else:
    print("  NOT FOUND")

# Check what R2 has
cur.execute("""
    SELECT development_type, permission_status, source_type
    FROM development_permissions
    WHERE zone = 'R2'
    AND source_type = 'nsw_standard'
    ORDER BY development_type
""")

print("\nR2 nsw_standard permissions:")
for row in cur.fetchall():
    print(f"  {row[0]:35} {row[1]:15} ({row[2]})")

conn.close()
