import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

target_lgas = ['bayside', 'georges_river', 'inner_west', 'ku_ring_gai', 'parramatta',
               'randwick', 'sutherland_shire', 'waverley', 'woollahra']

for lga in target_lgas:
    cur.execute("""
    SELECT chapter_key, chapter_label
    FROM dcp_chapter_registry
    WHERE council = %s AND is_active = true
    AND (chapter_label ILIKE %s OR chapter_label ILIKE %s
         OR chapter_label ILIKE %s OR chapter_label ILIKE %s
         OR chapter_label ILIKE %s OR chapter_label ILIKE %s)
    ORDER BY chapter_key
    LIMIT 5
    """, (lga, '%residential%', '%dwelling%', '%setback%', '%building%', '%site%', '%general%'))
    rows = cur.fetchall()
    if rows:
        print(f"\n{lga}: {len(rows)} matches")
        for r in rows:
            print(f"  {r[0]:40s} {r[1]}")
    else:
        cur.execute("SELECT COUNT(*) FROM dcp_chapter_registry WHERE council = %s", (lga,))
        ct = cur.fetchone()[0]
        print(f"\n{lga}: 0 matches ({ct} total chapters)")
        if ct > 0:
            cur.execute("""
            SELECT chapter_key, chapter_label FROM dcp_chapter_registry
            WHERE council = %s AND is_active = true ORDER BY sort_order LIMIT 8
            """, (lga,))
            for r in cur.fetchall():
                print(f"  {r[0]:40s} {r[1]}")

conn.close()
