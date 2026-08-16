import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

# part-g-s13 specific count
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND source_chapter_key = 'part-g-s13-site-specific'
      AND is_current = TRUE
""")
print(f"part-g-s13-site-specific existing provisions: {cur.fetchone()[0]}")

# appendix-a-glossary: mark no extraction
cur.execute("""
    UPDATE dcp_chapter_registry
    SET needs_extraction = FALSE,
        notes = 'Glossary — flat alphabetical list, no numbered section structure, not extractable as provisions'
    WHERE council = 'leichhardt' AND chapter_key = 'appendix-a-glossary'
    RETURNING chapter_key, needs_extraction, notes
""")
row = cur.fetchone()
print(f"\nappendix-a-glossary updated: needs_extraction={row[1]}")

# part-e-water: clear needs_extraction, note URL is wrong
cur.execute("""
    UPDATE dcp_chapter_registry
    SET needs_extraction = FALSE,
        notes = 'Council hub URL mislabelled — points to Part F Food PDF, not Part E Water. Correct URL unknown. Monitor until council fixes.'
    WHERE council = 'leichhardt' AND chapter_key = 'part-e-water'
    RETURNING chapter_key, needs_extraction
""")
row = cur.fetchone()
print(f"part-e-water updated: needs_extraction={row[1]} (URL mislabelled by council)")

conn.commit()
conn.close()
print("\nDone.")
