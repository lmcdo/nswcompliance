import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Marrickville full parking rate table
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 104406")
r = cur.fetchone()
print("=== Marrickville Table 1 (id=104406) ===")
print(r[0])

# Ashfield - look for the actual rate table (Table 3 referenced)
cur.execute("""
SELECT id, provision_text, pdf_page
FROM regulatory_provisions
WHERE source_council = 'ashfield' AND v2_topic = 'parking'
AND is_current = true
AND provision_text ILIKE '%table 3%'
ORDER BY id
""")
rows = cur.fetchall()
print(f"\n\n=== Ashfield provisions mentioning Table 3 ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]}")
    print(r[1][:600])

# Also check Ashfield RFB parking (id=100718, 100719)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id IN (100718, 100719) ORDER BY id")
rows = cur.fetchall()
print("\n\n=== Ashfield RFB parking provisions ===")
for r in rows:
    print(r[0])
    print("---")

# Get DCP versions for each council
cur.execute("""
SELECT DISTINCT source_council, document_id 
FROM regulatory_provisions 
WHERE source_council IN ('ashfield','leichhardt','marrickville')
AND is_current = true
LIMIT 10
""")
print("\n\n=== Document IDs per council ===")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
