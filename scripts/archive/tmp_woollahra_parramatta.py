import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Woollahra - setback provisions
cur.execute("""
SELECT id, LEFT(provision_text, 500), pdf_page, v2_topic, source_chapter_key
FROM regulatory_provisions
WHERE source_council = 'woollahra' AND is_current = true
AND (provision_text ILIKE '%%front setback%%' OR provision_text ILIKE '%%side setback%%'
     OR provision_text ILIKE '%%rear setback%%')
AND provision_text ~* '\d+\.?\d*\s*m'
ORDER BY id
LIMIT 10
""")
rows = cur.fetchall()
print(f"=== Woollahra setback+metre provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} topic={r[3]} chapter={r[4]}")
    print(r[1][:400])

# Parramatta - setback provisions from the full DCP
cur.execute("""
SELECT id, LEFT(provision_text, 500), pdf_page, v2_topic
FROM regulatory_provisions
WHERE source_council = 'parramatta' AND is_current = true
AND (provision_text ILIKE '%%front setback%%' OR provision_text ILIKE '%%side setback%%'
     OR provision_text ILIKE '%%rear setback%%')
AND provision_text ~* '\d+\.?\d*\s*m'
ORDER BY id
LIMIT 10
""")
rows = cur.fetchall()
print(f"\n\n=== Parramatta setback+metre provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} topic={r[3]}")
    print(r[1][:400])

conn.close()
