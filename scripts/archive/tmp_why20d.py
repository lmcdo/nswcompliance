import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# What columns does regulatory_provisions have?
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name LIKE '%lga%' OR table_name = 'regulatory_provisions' AND column_name LIKE '%council%' OR table_name = 'regulatory_provisions' AND column_name LIKE '%instrument%' ORDER BY column_name")
print("LGA/council/instrument columns in regulatory_provisions:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Check v2_instrument
cur.execute("SELECT DISTINCT v2_instrument, COUNT(*) FROM regulatory_provisions WHERE v2_instrument IS NOT NULL GROUP BY v2_instrument ORDER BY v2_instrument")
print("\nv2_instrument values:")
for r in cur.fetchall():
    print(f"  {r[0]:60s} {r[1]:>5}")

conn.close()
