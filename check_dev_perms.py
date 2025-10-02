from db_config import get_connection
conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM development_permissions")
total = cur.fetchone()[0]
print(f"Total records in development_permissions: {total}")

cur.execute("""
    SELECT zone, development_type, permission_status, source_type
    FROM development_permissions
    LIMIT 10
""")
print("\nFirst 10 records:")
for row in cur.fetchall():
    print(f"  {row[0]:10} {row[1]:30} {row[2]:20} {row[3]}")

cur.execute("SELECT MAX(id) FROM development_permissions")
max_id = cur.fetchone()[0]
print(f"\nMax ID in table: {max_id}")

conn.close()
