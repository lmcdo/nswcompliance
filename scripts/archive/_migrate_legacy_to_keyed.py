import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

# Chapters covered by March 2026 keyed provisions (exclude part-c-s2 — April 2026 is active)
RESTORE_CHAPTERS = [
    'appendix-b-building-typologies',
    'part-a-introduction',
    'part-b-connections',
    'part-c-s1-general',
    'part-c-s3-residential',
    'part-c-s4-non-residential',
    'part-c-s5-entertainment-precincts',
    'part-d-energy',
    'part-e-water',
    'part-f-food',
    'part-g-s1-site-specific',
    'part-g-s13-pyrmont-bridge-rd',
]

# Step 1: restore March 2026 keyed provisions
cur.execute("""
    UPDATE regulatory_provisions
    SET is_current = TRUE
    WHERE source_council = 'leichhardt'
      AND is_current = FALSE
      AND source_chapter_key = ANY(%s)
      AND extraction_method = 'pdfplumber-ci'
""", (RESTORE_CHAPTERS,))
restored_keyed = cur.rowcount
print(f"Restored {restored_keyed} March 2026 keyed provisions")

# Step 2: soft-delete all legacy NULL provisions
cur.execute("""
    UPDATE regulatory_provisions
    SET is_current = FALSE
    WHERE source_council = 'leichhardt'
      AND source_chapter_key IS NULL
      AND is_current = TRUE
""")
deleted_legacy = cur.rowcount
print(f"Soft-deleted {deleted_legacy} legacy NULL provisions")

# Step 3: verify final state
cur.execute("""
    SELECT
        source_chapter_key,
        COUNT(*) FILTER (WHERE is_current = TRUE) AS current,
        COUNT(*) FILTER (WHERE is_current = FALSE) AS soft_deleted
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
    GROUP BY source_chapter_key
    ORDER BY source_chapter_key NULLS FIRST
""")
print("\n=== Final state ===")
for r in cur.fetchall():
    key = r[0] or "(NULL)"
    print(f"  {key}: current={r[1]} | deleted={r[2]}")

conn.commit()
conn.close()
print("\nDone.")
