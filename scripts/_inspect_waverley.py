"""Inspect Waverley provision titles to find junk (objectives, descriptions, index, etc.)."""
import os, psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")
db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

# Show all section_header values + first 200 chars of provision_text
cur.execute("""
    SELECT section_header, LEFT(provision_text, 250), ref_number
    FROM regulatory_provisions
    WHERE source_council = 'waverley'
      AND is_current = TRUE
      AND v2_is_actionable = TRUE
    ORDER BY ref_number
    LIMIT 80
""")
for row in cur.fetchall():
    print(f"\n=== {row[0]} ===")
    print(row[1][:200])

cur.close()
conn.close()
