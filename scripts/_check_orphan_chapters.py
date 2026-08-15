#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    SELECT DISTINCT s.lga, s.source_chapter_key
    FROM dcp_setback_controls s
    LEFT JOIN dcp_chapter_registry r ON r.chapter_key = s.source_chapter_key
    WHERE s.control_type = 'car_parking' AND s.is_current = TRUE
      AND r.id IS NULL AND s.source_chapter_key IS NOT NULL
    ORDER BY s.lga, s.source_chapter_key
""")
rows = cur.fetchall()
if rows:
    print("Orphan source_chapter_keys (no registry entry):")
    for r in rows:
        print(f"  {r[0]:25s} {r[1]}")
else:
    print("All source_chapter_keys have registry entries")
conn.close()
