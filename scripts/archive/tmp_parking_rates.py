import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Get the actual parking rate provisions - look for rate tables
# Ashfield Part 8
cur.execute("""
SELECT id, provision_text, pdf_page, source_chapter_key
FROM regulatory_provisions
WHERE source_council = 'ashfield' AND v2_topic = 'parking'
AND is_current = true
AND (provision_text ILIKE '%per dwelling%' OR provision_text ILIKE '%spaces per%' 
     OR provision_text ILIKE '%parking rate%' OR provision_text ILIKE '%1 space%'
     OR provision_text ILIKE '%car space%')
ORDER BY id
""")
rows = cur.fetchall()
print(f"=== Ashfield parking rate provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} chapter={r[3]}")
    print(r[1][:500])
    print("---")

# Leichhardt - the actual rate table is id=87820
cur.execute("""
SELECT id, provision_text, pdf_page, source_chapter_key
FROM regulatory_provisions
WHERE id = 87820
""")
r = cur.fetchone()
print(f"\n\n=== Leichhardt General Vehicle Parking Rates (id={r[0]}) ===")
print(r[1])

# Marrickville - look for parking rate table
cur.execute("""
SELECT id, provision_text, pdf_page, source_chapter_key
FROM regulatory_provisions
WHERE source_council = 'marrickville' AND v2_topic = 'parking'
AND is_current = true
AND (provision_text ILIKE '%per dwelling%' OR provision_text ILIKE '%spaces per%' 
     OR provision_text ILIKE '%parking rate%' OR provision_text ILIKE '%1 space%'
     OR provision_text ILIKE '%car space%' OR provision_text ILIKE '%parking schedule%')
ORDER BY id
""")
rows = cur.fetchall()
print(f"\n\n=== Marrickville parking rate provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} chapter={r[3]}")
    print(r[1][:500])
    print("---")

conn.close()
