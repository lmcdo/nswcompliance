import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# C1 Low Density setbacks (id=101039)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 101039")
print("=== C1 Low Density Setbacks ===")
print(cur.fetchone()[0])

# C2 Other Residential setbacks (id=101084)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 101084")
print("\n\n=== C2 Other Residential Setbacks ===")
print(cur.fetchone()[0])

conn.close()
