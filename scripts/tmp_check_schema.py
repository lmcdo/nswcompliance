import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Get dcp_setback_controls columns
cur.execute("""
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'dcp_setback_controls'
ORDER BY ordinal_position
""")
print("=== dcp_setback_controls schema ===")
for row in cur.fetchall():
    print(f"  {row[0]:30s} {row[1]:20s} nullable={row[2]}")

# Check existing parking rows for these 3 councils
cur.execute("""
SELECT lga, control_type, COUNT(*) 
FROM dcp_setback_controls 
WHERE lga IN ('ashfield', 'leichhardt', 'marrickville')
GROUP BY lga, control_type
ORDER BY lga, control_type
""")
print("\n=== Existing controls for target LGAs ===")
for row in cur.fetchall():
    print(f"  {row[0]:20s} {row[1]:30s} {row[2]}")

# Sample a few existing parking rows from another council to see the format
cur.execute("""
SELECT lga, control_type, dev_type, value_min, value_max, unit, condition, 
       source_text, section_ref, source_chapter_key, extraction_method
FROM dcp_setback_controls 
WHERE control_type = 'car_parking' AND lga = 'canterbury_bankstown'
LIMIT 5
""")
print("\n=== Sample parking rows (canterbury_bankstown) ===")
for row in cur.fetchall():
    print(f"  lga={row[0]} type={row[1]} dev={row[2]} min={row[3]} max={row[4]} unit={row[5]}")
    print(f"    cond={row[6]}")
    print(f"    source={row[7]}")
    print(f"    ref={row[8]} chapter={row[9]} method={row[10]}")

conn.close()
