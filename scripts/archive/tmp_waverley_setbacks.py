import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Get Waverley residential setback provisions
cur.execute("""
SELECT id, provision_text, pdf_page, source_chapter_key, v2_topic
FROM regulatory_provisions
WHERE source_council = 'waverley' AND is_current = true
AND v2_topic = 'residential'
AND (provision_text ILIKE '%%setback%%' OR provision_text ILIKE '%%set back%%')
ORDER BY id
LIMIT 10
""")
rows = cur.fetchall()
print(f"=== Waverley residential setback provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} topic={r[4]} chapter={r[3]}")
    print(r[1][:600])

# Also check for specific dwelling house/multi-dwelling chapters
cur.execute("""
SELECT id, LEFT(provision_text, 500), pdf_page, v2_topic
FROM regulatory_provisions
WHERE source_council = 'waverley' AND is_current = true
AND (provision_text ILIKE '%%front setback%%' OR provision_text ILIKE '%%side setback%%' 
     OR provision_text ILIKE '%%rear setback%%')
AND provision_text ~* '\d+\.?\d*\s*m(etre)?'
ORDER BY id
LIMIT 10
""")
rows = cur.fetchall()
print(f"\n\n=== Waverley setback + metre provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} topic={r[3]}")
    print(r[1][:500])

conn.close()
