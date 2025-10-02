from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print("=== DEVELOPMENT_PERMISSIONS SCHEMA ===")
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='development_permissions' ORDER BY ordinal_position")
for col in cur.fetchall():
    print(f"{col[0]}: {col[1]}")

print("\n=== PERMISSIBILITY_ANALYSIS SCHEMA ===")
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='permissibility_analysis' ORDER BY ordinal_position")
for col in cur.fetchall():
    print(f"{col[0]}: {col[1]}")

print("\n=== DEVELOPMENT_PERMISSIONS SAMPLE ===")
cur.execute("SELECT * FROM development_permissions LIMIT 3")
rows = cur.fetchall()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='development_permissions' ORDER BY ordinal_position")
cols = [c[0] for c in cur.fetchall()]
for row in rows:
    print(dict(zip(cols, row)))

conn.close()