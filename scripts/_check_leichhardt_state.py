import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

# Registry state
cur.execute("""
    SELECT chapter_key, needs_extraction, last_extracted_at, last_extracted_version, notes
    FROM dcp_chapter_registry
    WHERE council = 'leichhardt'
    ORDER BY sort_order
""")
print("=== Leichhardt Registry State ===")
for row in cur.fetchall():
    flag = "!! NEEDS EXTRACTION" if row[1] else "ok"
    extracted = row[2].strftime('%Y-%m-%d %H:%M') if row[2] else "never"
    print(f"{flag}  {row[0]}")
    print(f"    last_extracted: {extracted} | version: {row[3] or '-'}")
    if row[4]:
        print(f"    notes: {row[4]}")

# Provision counts per chapter
print("\n=== Provision Counts (current) ===")
cur.execute("""
    SELECT source_chapter_key, COUNT(*) as n
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt' AND is_current = TRUE
    GROUP BY source_chapter_key
    ORDER BY source_chapter_key NULLS FIRST
""")
for row in cur.fetchall():
    key = row[0] or "(NULL — legacy, no chapter key)"
    print(f"  {key}: {row[1]}")

conn.close()
