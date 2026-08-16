#!/usr/bin/env python3
"""Find parking-related chapters in Inner West DCP registry."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor()

# First check schema
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='dcp_chapter_registry' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print("Columns:", cols)

# Check all councils that map to inner_west
for council in ['inner_west', 'leichhardt', 'ashfield', 'marrickville']:
    cur.execute("""
        SELECT *
        FROM dcp_chapter_registry
        WHERE council = %s
        ORDER BY chapter_key
    """, (council,))
    rows = cur.fetchall()
    if rows:
        print(f"\n=== {council} ({len(rows)} chapters) ===")
        for r in rows:
            # Print all columns
            row_dict = dict(zip(cols, r))
            key = row_dict.get('chapter_key', '')
            # Filter for parking-related
            all_text = ' '.join(str(v) for v in row_dict.values() if v).lower()
            if any(kw in all_text for kw in ['parking', 'transport', 'traffic', 'vehicle', 'access']):
                print(f"  PARKING-RELATED: {row_dict}")
            elif any(kw in key.lower() for kw in ['c1', 'part-c', '2.10', 'chapter-a']):
                print(f"  KEY-MATCH: {row_dict}")
    else:
        print(f"\n=== {council}: NO chapters in registry ===")

conn.close()
