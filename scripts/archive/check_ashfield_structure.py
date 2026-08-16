"""Quick check of Ashfield provision structure."""

import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    port=os.getenv('PGPORT')
)
cur = conn.cursor()

# Get sample Ashfield provisions with relevant columns
cur.execute("""
    SELECT id, v2_dcp_part, provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_dcp_layer = 'precinct'
      AND v2_is_actionable = true
    LIMIT 20;
""")

print("Sample Ashfield precinct provisions:\n")
for id, part, text in cur.fetchall():
    text_preview = text[:150] if text else "None"
    print(f"ID: {id}")
    print(f"Part: {part}")
    print(f"Text: {text_preview}...")
    print()

cur.close()
conn.close()
