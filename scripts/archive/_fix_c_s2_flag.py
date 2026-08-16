import os, psycopg2
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()
cur.execute("""
    UPDATE dcp_chapter_registry
    SET needs_extraction = FALSE,
        notes = 'URL updated to full-resolution PDF — text content identical to low-res, 80 provisions current'
    WHERE council = 'leichhardt' AND chapter_key = 'part-c-s2-urban-character'
""")
conn.commit()
conn.close()
print("Done.")
