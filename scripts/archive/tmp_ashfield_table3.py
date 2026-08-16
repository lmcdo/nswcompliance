import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Get full text of provision 99297 which references Table 3
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 99297")
print("=== Ashfield id=99297 (full) ===")
print(cur.fetchone()[0])

# Look for provisions that contain the actual table data (dwelling rates)
cur.execute("""
SELECT id, LEFT(provision_text, 500), pdf_page
FROM regulatory_provisions
WHERE source_council = 'ashfield' AND is_current = true
AND (provision_text ILIKE '%1 space per dwelling%' 
     OR provision_text ILIKE '%spaces per dwelling%'
     OR provision_text ILIKE '%per bedroom%')
ORDER BY id
""")
rows = cur.fetchall()
print(f"\n\n=== Ashfield provisions with 'per dwelling' or 'per bedroom' ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]}")
    print(r[1])

# Look for Ashfield Table 3 text - search for common table patterns
cur.execute("""
SELECT id, LEFT(provision_text, 600), pdf_page, source_chapter_key
FROM regulatory_provisions
WHERE source_council = 'ashfield' AND is_current = true
AND v2_topic = 'parking'
AND (provision_text ILIKE '%dwelling house%' AND provision_text ILIKE '%space%')
ORDER BY id
""")
rows = cur.fetchall()
print(f"\n\n=== Ashfield parking + dwelling house ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} chapter={r[3]}")
    print(r[1])

conn.close()
