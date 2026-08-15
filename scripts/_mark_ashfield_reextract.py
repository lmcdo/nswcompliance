#!/usr/bin/env python3
"""Mark all Ashfield chapters for re-extraction after adding Level 2 marker splitting."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Show current state
cur.execute("""
    SELECT id, chapter_key, chapter_label, needs_extraction, last_extracted_at
    FROM dcp_chapter_registry
    WHERE council = 'ashfield' AND is_active = TRUE
    ORDER BY chapter_key
""")
rows = cur.fetchall()
print(f"Ashfield chapters in registry: {len(rows)}")
for r in rows:
    print(f"  {r[0]:>5} | {r[1]:<20} | {r[2][:40]:<40} | extract={r[3]} | last={r[4]}")

# Mark for re-extraction
cur.execute("""
    UPDATE dcp_chapter_registry
    SET needs_extraction = TRUE
    WHERE council = 'ashfield' AND is_active = TRUE
    RETURNING id, chapter_key
""")
updated = cur.fetchall()
conn.commit()
print(f"\nMarked {len(updated)} chapters for re-extraction:")
for u in updated:
    print(f"  {u[0]} | {u[1]}")

cur.close()
conn.close()
