#!/usr/bin/env python3
"""Backfill v2_structural_category for City of Sydney only."""
import os, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from enrichment.config.structural_categories import get_structural_category

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT id, source_council, source_chapter_key, section_header
    FROM regulatory_provisions
    WHERE source_council = 'city_of_sydney' AND is_current = true
""")
rows = cur.fetchall()

updates = []
from collections import Counter
by_cat = Counter()

for pid, council, chapter_key, header in rows:
    cat = get_structural_category(council, chapter_key or "", header)
    if cat:
        updates.append((pid, cat))
        by_cat[cat] += 1

print(f"Mapped {len(updates)}/{len(rows)} provisions:")
for cat, count in by_cat.most_common():
    print(f"  {cat}: {count}")

for pid, cat in updates:
    cur.execute("UPDATE regulatory_provisions SET v2_structural_category = %s WHERE id = %s", (cat, pid))
conn.commit()
print(f"\nApplied {len(updates)} updates.")

cur.close()
conn.close()
