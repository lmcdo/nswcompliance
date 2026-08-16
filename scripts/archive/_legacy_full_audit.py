import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

print("=== Current keyed provisions per chapter ===")
cur.execute("""
    SELECT source_chapter_key, COUNT(*)
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt' AND is_current = TRUE AND source_chapter_key IS NOT NULL
    GROUP BY source_chapter_key ORDER BY source_chapter_key
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n=== Soft-deleted keyed provisions per chapter ===")
cur.execute("""
    SELECT source_chapter_key, COUNT(*)
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt' AND is_current = FALSE AND source_chapter_key IS NOT NULL
    GROUP BY source_chapter_key ORDER BY source_chapter_key
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n=== Legacy NULL provisions by document_id (mapping to chapters) ===")
cur.execute("""
    SELECT
        CASE
            WHEN document_id ILIKE '%Part A%' THEN 'part-a-introduction'
            WHEN document_id ILIKE '%Part B%' THEN 'part-b-connections'
            WHEN document_id ILIKE '%Part C Place Section 1%' OR document_id ILIKE '%Part_C_Section_1%' THEN 'part-c-s1-general'
            WHEN document_id ILIKE '%Part C Place Section 2%' OR document_id ILIKE '%Part_C_Section_2%' THEN 'part-c-s2-urban-character'
            WHEN document_id ILIKE '%Part C%Section 3%' OR document_id ILIKE '%Part_C_Section_3%' THEN 'part-c-s3-residential'
            WHEN document_id ILIKE '%Part C%Section 4%' THEN 'part-c-s4-non-residential'
            WHEN document_id ILIKE '%Part C%Section 5%' THEN 'part-c-s5-entertainment-precincts'
            WHEN document_id ILIKE '%Part D%' THEN 'part-d-energy'
            WHEN document_id ILIKE '%Part E%' THEN 'part-e-water'
            WHEN document_id ILIKE '%Part F%' THEN 'part-f-food'
            WHEN document_id ILIKE '%Part G%' THEN 'part-g-s1-site-specific'
            ELSE 'unknown'
        END AS inferred_chapter,
        COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
      AND is_current = TRUE
    GROUP BY inferred_chapter
    ORDER BY n DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
