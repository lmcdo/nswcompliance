import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

for council in ['ashfield', 'leichhardt', 'marrickville']:
    cur.execute("""
    SELECT id, LEFT(provision_text, 200), v2_marker, pdf_page, source_chapter_key, 
           v2_applicable_dev_types, v2_has_numeric_value, section_header
    FROM regulatory_provisions
    WHERE source_council = %s AND v2_topic = 'parking'
    AND is_current = true
    ORDER BY id
    LIMIT 15
    """, (council,))
    rows = cur.fetchall()
    print(f"\n=== {council} parking provisions (first 15) ===")
    for r in rows:
        print(f"  id={r[0]} marker={r[2]} page={r[3]} chapter={r[4]} numeric={r[6]}")
        print(f"    header: {r[7]}")
        print(f"    dev_types: {r[5]}")
        print(f"    text: {r[1]}")
        print()

# Count
cur.execute("""
SELECT source_council, COUNT(*), 
       COUNT(*) FILTER (WHERE v2_has_numeric_value = true)
FROM regulatory_provisions 
WHERE source_council IN ('ashfield','leichhardt','marrickville') 
AND v2_topic = 'parking' AND is_current = true
GROUP BY source_council
""")
print("\n=== Counts (total / numeric) ===")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} total, {r[2]} numeric")

conn.close()
