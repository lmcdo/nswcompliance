import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Check existing
cur.execute("SELECT chapter_key, council FROM dcp_chapter_registry WHERE council IN ('campbelltown','blacktown','canterbury_bankstown') ORDER BY council")
print("Existing entries:")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

chapters = [
    ('campbelltown-scdcp-2015-part3', 'campbelltown', 'Campbelltown SCDCP 2015', 'dcp', 'Part 3 - Residential Development'),
    ('blacktown-dcp-2015-part-c', 'blacktown', 'Blacktown DCP 2015', 'dcp', 'Part C - Development in Residential Areas'),
    ('cb-dcp-2023-ch5-1', 'canterbury_bankstown', 'Canterbury-Bankstown DCP 2023', 'dcp', 'Chapter 5.1 - Former Bankstown LGA'),
]
for key, council, dcp_name, doc_type, label in chapters:
    cur.execute("""
    INSERT INTO dcp_chapter_registry (chapter_key, council, dcp_name, doc_type, chapter_label, is_active)
    VALUES (%s, %s, %s, %s, %s, true)
    ON CONFLICT (chapter_key) DO UPDATE SET updated_at = NOW()
    """, (key, council, dcp_name, doc_type, label))
    print(f"Registered: {key}")

# Total controls count
cur.execute('SELECT COUNT(*) FROM dcp_setback_controls WHERE is_current = true')
print(f"\nTotal dcp_setback_controls rows: {cur.fetchone()[0]}")

conn.close()
