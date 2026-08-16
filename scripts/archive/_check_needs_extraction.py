import os, psycopg2
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()
cur.execute("""
    SELECT chapter_key, needs_extraction, is_active, council_url IS NOT NULL as has_url
    FROM dcp_chapter_registry
    WHERE council = 'leichhardt' AND needs_extraction = TRUE
""")
rows = cur.fetchall()
print(f"Chapters with needs_extraction=TRUE: {len(rows)}")
for r in rows:
    print(f"  {r[0]} | is_active={r[1]} | has_url={r[2]}")
conn.close()
