import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Look for tables that might track searches/usage
cur.execute("""SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND (
    table_name LIKE '%search%' OR table_name LIKE '%log%'
    OR table_name LIKE '%analytic%' OR table_name LIKE '%usage%'
    OR table_name LIKE '%history%' OR table_name LIKE '%request%'
    OR table_name LIKE '%audit%' OR table_name LIKE '%event%'
) ORDER BY table_name""")
print("Potential usage tracking tables:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Check spatial_overlays for what addresses are stored
cur.execute("""SELECT DISTINCT council_name, COUNT(*)
FROM spatial_overlays GROUP BY council_name ORDER BY COUNT(*) DESC""")
print("\nCouncils in spatial_overlays (addresses looked up):")
for r in cur.fetchall():
    print(f"  {r[0]:40s} {r[1]:>5}")

conn.close()
