import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# What councils are in dcp_chapter_registry?
cur.execute("SELECT DISTINCT council FROM dcp_chapter_registry ORDER BY council")
chap_councils = [r[0] for r in cur.fetchall()]
print(f"Councils in dcp_chapter_registry: {len(chap_councils)}")
for c in chap_councils:
    print(f"  {c}")

# What councils are in regulatory_provisions (check former_council)?
cur.execute("SELECT DISTINCT former_council FROM regulatory_provisions WHERE former_council IS NOT NULL ORDER BY former_council")
fc = [r[0] for r in cur.fetchall()]
print(f"\nformer_council in regulatory_provisions: {len(fc)}")
for c in fc:
    print(f"  {c}")

# Check instrument_name for council names
cur.execute("SELECT DISTINCT instrument_name FROM regulatory_provisions ORDER BY instrument_name")
instruments = [r[0] for r in cur.fetchall()]
print(f"\nDistinct instruments: {len(instruments)}")
for i in instruments:
    print(f"  {i}")

conn.close()
