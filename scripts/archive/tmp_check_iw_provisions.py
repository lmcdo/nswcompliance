import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Inner West has 0 setback provisions in regulatory_provisions
# Check dcp_chapter_registry columns
cur.execute("""SELECT column_name FROM information_schema.columns
WHERE table_name = 'dcp_chapter_registry' ORDER BY ordinal_position""")
print("dcp_chapter_registry columns:", [r[0] for r in cur.fetchall()])

# Check chapters
cur.execute("""SELECT council, chapter_key, chapter_label FROM dcp_chapter_registry
WHERE council IN ('inner_west','ashfield','leichhardt','marrickville')
ORDER BY council, chapter_key""")
print(f"\nIW-related chapters ({cur.rowcount}):")
for r in cur.fetchall():
    print(f"  {r[0]:15s} {r[1]}: {r[2]}")

# Check ashfield+leichhardt existing setbacks
for lga in ['ashfield', 'leichhardt', 'marrickville']:
    cur.execute("""
    SELECT control_type, dev_type, value_min, condition
    FROM dcp_setback_controls
    WHERE lga = %s AND control_type IN ('front_setback','side_setback','rear_setback')
    ORDER BY control_type
    """, (lga,))
    print(f"\n{lga} setbacks ({cur.rowcount}):")
    for r in cur.fetchall():
        print(f"  {r[0]:16s} {r[1]:20s} min={r[2]} {r[3]}")

# Check waverley front setbacks
cur.execute("""
SELECT control_type, dev_type, value_min, condition
FROM dcp_setback_controls
WHERE lga = 'waverley' AND control_type = 'front_setback'
""")
print(f"\nWaverley front setbacks ({cur.rowcount}):")
for r in cur.fetchall():
    print(f"  {r[0]:16s} {r[1]:20s} min={r[2]} {r[3]}")

# Northern beaches side setbacks
cur.execute("""
SELECT control_type, dev_type, value_min, condition
FROM dcp_setback_controls
WHERE lga = 'northern_beaches' AND control_type IN ('front_setback','side_setback','rear_setback')
ORDER BY control_type
""")
print(f"\nNorthern Beaches setbacks ({cur.rowcount}):")
for r in cur.fetchall():
    print(f"  {r[0]:16s} {r[1]:20s} min={r[2]} {r[3]}")

conn.close()
