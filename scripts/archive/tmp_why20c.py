import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Get all distinct instrument_name values
cur.execute("SELECT DISTINCT instrument_name, COUNT(*) FROM regulatory_provisions GROUP BY instrument_name ORDER BY instrument_name")
for r in cur.fetchall():
    print(f"  {r[0]:60s} {r[1]:>5}")

# What's the total council count in spatial_overlays?
print("\n--- spatial_overlays councils ---")
cur.execute("SELECT DISTINCT council_name FROM spatial_overlays ORDER BY council_name LIMIT 50")
for r in cur.fetchall():
    print(f"  {r[0]}")

conn.close()
