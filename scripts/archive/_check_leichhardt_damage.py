import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

# How many leichhardt provisions are now is_current=FALSE (soft-deleted)?
cur.execute("""
    SELECT
        COUNT(*) FILTER (WHERE is_current = TRUE)  AS current,
        COUNT(*) FILTER (WHERE is_current = FALSE) AS soft_deleted
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
""")
row = cur.fetchone()
print(f"Leichhardt provisions — current: {row[0]} | soft-deleted: {row[1]}")

# Show the NULL-sourced ones specifically
cur.execute("""
    SELECT
        COUNT(*) FILTER (WHERE is_current = TRUE)  AS current,
        COUNT(*) FILTER (WHERE is_current = FALSE) AS soft_deleted
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
""")
row = cur.fetchone()
print(f"  of which NULL source_chapter_key — current: {row[0]} | soft-deleted: {row[1]}")

conn.close()
