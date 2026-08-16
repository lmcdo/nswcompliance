import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

target_lgas = ['bayside', 'georges_river', 'inner_west', 'ku_ring_gai', 'parramatta',
               'randwick', 'sutherland_shire', 'waverley', 'woollahra']

for lga in target_lgas:
    cur.execute("""
    SELECT id, LEFT(provision_text, 200), v2_topic, pdf_page, source_chapter_key
    FROM regulatory_provisions
    WHERE source_council = %s AND is_current = true
    AND (provision_text ILIKE %s OR provision_text ILIKE %s)
    AND provision_text ILIKE %s
    ORDER BY id
    LIMIT 5
    """, (lga, '%setback%', '%set back%', '%metre%'))
    rows = cur.fetchall()
    if rows:
        print(f"\n=== {lga} ({len(rows)} setback provisions with metre) ===")
        for r in rows:
            print(f"  id={r[0]} topic={r[2]} page={r[3]} chapter={r[4]}")
            print(f"    {r[1][:180]}")
    else:
        # Try broader search
        cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE source_council = %s AND is_current = true
        AND (provision_text ILIKE %s OR provision_text ILIKE %s)
        """, (lga, '%setback%', '%set back%'))
        ct = cur.fetchone()[0]
        print(f"\n{lga}: 0 setback+metre matches, {ct} total setback mentions")

conn.close()
