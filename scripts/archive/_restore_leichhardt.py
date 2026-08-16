import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

# Restore legacy NULL provisions
cur.execute("""
    UPDATE regulatory_provisions
    SET is_current = TRUE
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
      AND is_current = FALSE
""")
restored = cur.rowcount
print(f"Restored: {restored} legacy NULL provisions")

# Soft-delete the 3 wrong part-e-water provisions (Part F Food content)
cur.execute("""
    UPDATE regulatory_provisions
    SET is_current = FALSE
    WHERE source_council = 'leichhardt'
      AND source_chapter_key = 'part-e-water'
      AND is_current = TRUE
""")
removed = cur.rowcount
print(f"Soft-deleted: {removed} wrong part-e-water provisions (Part F Food content)")

conn.commit()
conn.close()
print("Done.")
