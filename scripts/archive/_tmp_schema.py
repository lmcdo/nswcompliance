import os, psycopg2
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor()

# documents table structure
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'documents' ORDER BY ordinal_position")
print("=== documents columns ===")
for r in cur.fetchall(): print(r)

# E&C documents row
cur.execute("SELECT id, pdf_name, dcp_name FROM documents WHERE pdf_name ILIKE '%exempt%' LIMIT 5")
print("\n=== E&C documents rows ===")
for r in cur.fetchall(): print(r)

conn.close()
