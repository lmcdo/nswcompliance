import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Check columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'dcp_chapter_registry' ORDER BY ordinal_position")
print("Columns:", [r[0] for r in cur.fetchall()])

# Check existing entries for these LGAs
cur.execute("SELECT chapter_key, lga FROM dcp_chapter_registry WHERE lga IN ('campbelltown','blacktown','canterbury_bankstown') ORDER BY lga")
print("\nExisting entries:")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

conn.close()
