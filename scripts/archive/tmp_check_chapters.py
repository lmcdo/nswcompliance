import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Schema first
cur.execute("""
SELECT column_name FROM information_schema.columns
WHERE table_name = 'dcp_chapter_registry'
ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print("Columns:", cols)

# Check existing parking chapters
cur.execute(f"""
SELECT * FROM dcp_chapter_registry
WHERE council IN ('ashfield', 'leichhardt', 'marrickville')
AND (chapter_key ILIKE '%parking%' OR chapter_key ILIKE '%part8%' OR chapter_key ILIKE '%part-8%')
LIMIT 10
""")
rows = cur.fetchall()
print(f"\nExisting parking chapters ({len(rows)}):")
for r in rows:
    print(f"  {r}")

conn.close()
