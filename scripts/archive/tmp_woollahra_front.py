import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Woollahra front setback control
cur.execute("""
SELECT id, provision_text, pdf_page, v2_topic, source_chapter_key
FROM regulatory_provisions
WHERE source_council = 'woollahra' AND is_current = true
AND provision_text ILIKE '%%front setback%%'
AND provision_text ~* '\d+\.?\d*\s*m'
ORDER BY id
LIMIT 5
""")
rows = cur.fetchall()
print(f"=== Woollahra front setback provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]} topic={r[3]} chapter={r[4]}")
    print(r[1][:1000])

# Check existing Woollahra setbacks in dcp_setback_controls
cur.execute("""
SELECT control_type, dev_type, value_min, unit, condition, source_text
FROM dcp_setback_controls
WHERE lga = 'woollahra' AND control_type IN ('front_setback','side_setback','rear_setback')
ORDER BY control_type, id
""")
print(f"\n\n=== Existing Woollahra setbacks ===")
for r in cur.fetchall():
    print(f"  {r[0]:16s} {r[1]:30s} min={r[2]} {r[3]} cond={r[4]}")
    print(f"    src: {r[5][:100] if r[5] else 'None'}")

conn.close()
