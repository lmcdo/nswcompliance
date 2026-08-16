import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'dcp_setback_controls_applicability_check'
""")
r = cur.fetchone()
print(f"Constraint: {r[0]}")
print(f"Definition: {r[1]}")

# Also check valid applicability values
cur.execute("SELECT DISTINCT applicability FROM dcp_setback_controls ORDER BY 1")
print("\nExisting applicability values:")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

conn.close()
