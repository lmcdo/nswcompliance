import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()
cur.execute("""
    SELECT chapter_key, chapter_label, council_url
    FROM dcp_chapter_registry
    WHERE council = 'leichhardt'
      AND chapter_key IN ('part-c-s2-urban-character', 'part-e-water', 'part-g-s13-site-specific', 'appendix-a-glossary')
    ORDER BY sort_order
""")
for row in cur.fetchall():
    print(f"{row[0]}\n  {row[1]}\n  {row[2]}\n")
conn.close()
