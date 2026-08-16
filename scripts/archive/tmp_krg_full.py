import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Get KRG dwelling house building setbacks (4A.2)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 98131")
print("=== KRG 4A.2 Building Setbacks (Dwelling Houses) ===")
print(cur.fetchone()[0])

# Get KRG dual occupancy building setbacks (5A.3)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 98162")
print("\n\n=== KRG 5A.3 Building Setbacks (Dual Occupancy) ===")
print(cur.fetchone()[0])

# Get KRG multi-dwelling setback/separation
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 98179")
print("\n\n=== KRG 6A.4 Building Separation (Multi-Dwelling) ===")
print(cur.fetchone()[0])

# Check for multi-dwelling building setback section
cur.execute("""
SELECT id, LEFT(provision_text, 300), pdf_page
FROM regulatory_provisions
WHERE source_council = 'ku_ring_gai' AND is_current = true
AND source_chapter_key = 'section-a-part-6-multi-dwelling'
AND provision_text ILIKE '%%setback%%'
ORDER BY id
""", ())
rows = cur.fetchall()
print(f"\n\n=== KRG multi-dwelling setback provisions ({len(rows)}) ===")
for r in rows:
    print(f"id={r[0]} page={r[2]}")
    print(r[1][:300])

conn.close()
