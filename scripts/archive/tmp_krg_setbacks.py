import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Ku-ring-gai dwelling house building envelope controls
cur.execute("""
SELECT id, provision_text, pdf_page, source_chapter_key
FROM regulatory_provisions
WHERE source_council = 'ku_ring_gai' AND is_current = true
AND source_chapter_key = 'section-a-part-4-dwelling-houses'
AND (provision_text ILIKE %s OR provision_text ILIKE %s)
ORDER BY id
""", ('%setback%', '%set back%'))
rows = cur.fetchall()
print(f"=== KRG dwelling house setback provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} chapter={r[3]}")
    print(r[1][:800])

# Also check dual occupancy and multi-dwelling
for chapter in ['section-a-part-5-dual-occupancy', 'section-a-part-6-multi-dwelling']:
    cur.execute("""
    SELECT id, provision_text, pdf_page, source_chapter_key
    FROM regulatory_provisions
    WHERE source_council = 'ku_ring_gai' AND is_current = true
    AND source_chapter_key = %s
    AND (provision_text ILIKE %s OR provision_text ILIKE %s)
    ORDER BY id
    """, (chapter, '%setback%', '%set back%'))
    rows = cur.fetchall()
    print(f"\n\n=== KRG {chapter} setback provisions ({len(rows)}) ===")
    for r in rows:
        print(f"\nid={r[0]} page={r[2]}")
        print(r[1][:800])

conn.close()
