import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

# Compare extraction_method and provision text length between legacy and keyed
cur.execute("""
    SELECT
        CASE WHEN source_chapter_key IS NULL THEN 'legacy-null' ELSE 'march-2026-keyed' END as cohort,
        extraction_method,
        COUNT(*) as n,
        ROUND(AVG(LENGTH(provision_text))) as avg_text_len,
        MIN(LENGTH(provision_text)) as min_len,
        MAX(LENGTH(provision_text)) as max_len
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND (
        (source_chapter_key IS NULL AND is_current = TRUE)
        OR
        (source_chapter_key IS NOT NULL AND is_current = FALSE
         AND source_chapter_key NOT IN ('amendment-7-licensed-premises','part-c-s2-urban-character','part-g-s13-site-specific'))
      )
    GROUP BY cohort, extraction_method
    ORDER BY cohort, extraction_method
""")
print("=== Extraction method + text length comparison ===")
for r in cur.fetchall():
    print(f"  {r[0]} | method={r[1]} | n={r[2]} | avg_len={r[3]} | min={r[4]} | max={r[5]}")

# Sample 3 legacy vs 3 March-2026 provisions from same chapter (part-c-s1-general)
print("\n=== Sample: part-c-s1-general legacy NULL (first 3) ===")
cur.execute("""
    SELECT ref_number, section_header, LEFT(provision_text, 200)
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL AND is_current = TRUE
      AND document_id ILIKE '%Part C Place Section 1%'
    LIMIT 3
""")
for r in cur.fetchall():
    print(f"  ref={r[0]!r}\n  header={r[1]!r}\n  text={r[2]!r}\n")

print("=== Sample: part-c-s1-general March 2026 keyed (first 3) ===")
cur.execute("""
    SELECT ref_number, section_header, LEFT(provision_text, 200)
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key = 'part-c-s1-general' AND is_current = FALSE
    LIMIT 3
""")
for r in cur.fetchall():
    print(f"  ref={r[0]!r}\n  header={r[1]!r}\n  text={r[2]!r}\n")

conn.close()
