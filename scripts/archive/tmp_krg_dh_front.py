import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# KRG dwelling house - building setbacks full text (4A.2) - already got battle-axe
# Need to find the front/side/rear setback for normal lots
# The provision 98131 had battle-axe only. Let me check if there are more provisions in this section
cur.execute("""
SELECT id, LEFT(provision_text, 500), pdf_page
FROM regulatory_provisions
WHERE source_council = 'ku_ring_gai' AND is_current = true
AND source_chapter_key = 'section-a-part-4-dwelling-houses'
AND (provision_text ILIKE '%%front setback%%' OR provision_text ILIKE '%%side setback%%'
     OR provision_text ILIKE '%%rear setback%%')
ORDER BY id
""")
rows = cur.fetchall()
print(f"=== KRG DH setback provisions ({len(rows)}) ===")
for r in rows:
    print(f"\nid={r[0]} page={r[2]}")
    print(r[1][:500])

# Also get the building envelope (4C.1) which often has setback dimensions
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 98137")
text = cur.fetchone()[0]
# Find sections with metre values
import re
lines = text.split('\n')
for i, line in enumerate(lines):
    if any(w in line.lower() for w in ['setback', 'metre', 'minimum', '1.5m', '2m', '3m', '6m', '9m', '12m']):
        context = lines[max(0,i-1):min(len(lines),i+3)]
        print(f"\n  Line {i}: {'|'.join(context)}")

conn.close()
