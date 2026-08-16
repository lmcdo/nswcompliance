import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

cur.execute("""
    SELECT document_id, pdf_source_file, COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
      AND is_current = TRUE
    GROUP BY document_id, pdf_source_file
    ORDER BY n DESC
    LIMIT 20
""")
print("document_id / pdf_source_file breakdown:")
for row in cur.fetchall():
    print(f"  doc={row[0]!r}  src={row[1]!r}  n={row[2]}")

conn.close()
