import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Check if any partial rows were inserted
cur.execute("""
SELECT id, dev_type, value_min, source_text 
FROM dcp_setback_controls 
WHERE lga = 'ashfield' AND control_type = 'car_parking'
""")
rows = cur.fetchall()
print(f"Existing ashfield car_parking rows: {len(rows)}")
for r in rows:
    print(f"  id={r[0]} dev={r[1]} min={r[2]} src={r[3][:60]}")

# Clean them up if they exist (they were from a failed transaction, but autocommit was on)
if rows:
    ids = [r[0] for r in rows]
    cur.execute("DELETE FROM dcp_setback_controls WHERE id = ANY(%s)", (ids,))
    print(f"Cleaned up {len(ids)} partial rows")

conn.close()
