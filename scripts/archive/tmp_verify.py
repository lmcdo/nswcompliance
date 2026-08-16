import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
SELECT dev_type, value_min, unit, section_ref, pdf_page, LEFT(source_text, 80)
FROM dcp_setback_controls
WHERE lga = 'ashfield' AND control_type = 'car_parking'
ORDER BY id
""")
print("=== Ashfield car_parking (verified) ===")
for r in cur.fetchall():
    print(f"  {str(r[0]):30s} min={r[1]} unit={r[2]} ref={r[3]} p{r[4]}")

conn.close()
