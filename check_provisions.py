import sys, os
from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check current URLs in dcp_general_requirements
print("=== dcp_general_requirements URLs (Ashfield E1/B1/B2) ===")
cur.execute("""
    SELECT id, part_name, pdf_page, pdf_page_image_url
    FROM dcp_general_requirements
    WHERE former_council = 'Ashfield'
    AND applicable_zones && ARRAY['E1', 'B1', 'B2']::text[]
    ORDER BY id
    LIMIT 10
""")
for r in cur.fetchall():
    url = r[3][:60] + "..." if r[3] and len(r[3]) > 60 else r[3]
    print(f'  ID: {r[0]}, Part: {r[1][:20] if r[1] else "N"}, Page: {r[2]}, URL: {url}')

cur.close()
conn.close()
