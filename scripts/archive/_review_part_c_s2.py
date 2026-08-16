import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

# All current part-c-s2 provisions: section header, page, ref_number
cur.execute("""
    SELECT ref_number, section_header, pdf_page, page_range
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key = 'part-c-s2-urban-character'
      AND is_current = TRUE
    ORDER BY pdf_page, ref_number
""")
rows = cur.fetchall()
print(f"Total provisions: {len(rows)}")
print()
for r in rows:
    pages = r[3] if r[3] else [r[2]]
    print(f"  [{r[0]}] p{r[2]}  {r[1]}")

# What page range do we cover?
cur.execute("""
    SELECT MIN(pdf_page), MAX(pdf_page)
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key = 'part-c-s2-urban-character'
      AND is_current = TRUE
""")
mn, mx = cur.fetchone()
print(f"\nPage range covered: {mn} – {mx}")

# Legacy NULL provisions that look like they might be part-c-s2 (by ref_number pattern)
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
      AND is_current = TRUE
      AND (ref_number ILIKE '%C.2%' OR ref_number ILIKE '%urban%' OR section_header ILIKE '%urban character%')
""")
print(f"\nLegacy NULL provisions that look like part-c-s2: {cur.fetchone()[0]}")

conn.close()
