import os, re
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

cur.execute("""
    SELECT ref_number, COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
      AND is_current = TRUE
    GROUP BY ref_number
    ORDER BY n DESC
    LIMIT 5
""")
print("Sample ref_numbers:")
for row in cur.fetchall():
    print(f"  {row[0]}  (x{row[1]})")

# Try to extract chapter slug from ref_number pattern:
# Leichhardt_DCP_2013__part_c_s3_residential__R3_1 -> part-c-s3-residential
cur.execute("""
    SELECT
        regexp_replace(
            regexp_replace(ref_number, '^[^_]+__([^_]+(?:_[^_]+)*)__.*$', '\\1'),
            '_', '-', 'g'
        ) AS inferred_chapter,
        COUNT(*) AS n
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
      AND is_current = TRUE
    GROUP BY inferred_chapter
    ORDER BY n DESC
""")
print("\nInferred chapter keys from ref_number:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
