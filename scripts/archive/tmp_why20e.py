import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("SELECT DISTINCT source_council, COUNT(*) FROM regulatory_provisions WHERE source_council IS NOT NULL GROUP BY source_council ORDER BY COUNT(*) DESC")
print("source_council in regulatory_provisions:")
for r in cur.fetchall():
    print(f"  {r[0]:40s} {r[1]:>6}")

conn.close()
