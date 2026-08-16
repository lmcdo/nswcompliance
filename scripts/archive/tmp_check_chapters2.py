import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Check Ashfield and Leichhardt parking chapters
cur.execute("""
SELECT council, chapter_key, chapter_label
FROM dcp_chapter_registry
WHERE council IN ('ashfield', 'leichhardt')
AND (chapter_key ILIKE '%parking%' OR chapter_label ILIKE '%parking%' 
     OR chapter_key ILIKE '%miscellaneous%' OR chapter_key ILIKE '%general%')
ORDER BY council, chapter_key
""")
rows = cur.fetchall()
print(f"Ashfield/Leichhardt parking-related chapters ({len(rows)}):")
for r in rows:
    print(f"  {r[0]}: key={r[1]} label={r[2]}")

# What chapter_keys do Ashfield provisions use?
cur.execute("""
SELECT DISTINCT source_chapter_key 
FROM regulatory_provisions 
WHERE source_council = 'ashfield' AND v2_topic = 'parking' AND is_current = true
""")
print("\nAshfield parking source_chapter_keys:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# What chapter_keys do Leichhardt provisions use?
cur.execute("""
SELECT DISTINCT source_chapter_key 
FROM regulatory_provisions 
WHERE source_council = 'leichhardt' AND v2_topic = 'parking' AND is_current = true
""")
print("\nLeichhardt parking source_chapter_keys:")
for r in cur.fetchall():
    print(f"  {r[0]}")

# Check if chapter-a-miscellaneous and part-c-s1-general exist in registry
cur.execute("""
SELECT council, chapter_key, chapter_label
FROM dcp_chapter_registry
WHERE chapter_key IN ('chapter-a-miscellaneous', 'part-c-s1-general', 'chapter-f-dev-category')
""")
print("\nThese chapter_keys in registry:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} — {r[2]}")

conn.close()
