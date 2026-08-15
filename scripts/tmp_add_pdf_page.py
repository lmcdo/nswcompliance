import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Add pdf_page column
cur.execute("""
ALTER TABLE dcp_setback_controls 
ADD COLUMN IF NOT EXISTS pdf_page integer
""")
print("Added pdf_page column")

# Verify
cur.execute("""
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'dcp_setback_controls' AND column_name = 'pdf_page'
""")
r = cur.fetchone()
print(f"Verified: {r[0]} {r[1]}")

conn.close()
