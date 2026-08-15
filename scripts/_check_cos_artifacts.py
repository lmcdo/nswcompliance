#!/usr/bin/env python3
"""Check spaced digit artifacts in City of Sydney provisions."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find provisions with spaced digit patterns
spaced_digit_re = re.compile(r'\d\s+\d\s+\d')

cur.execute("""
    SELECT id, source_chapter_key, LEFT(provision_text, 500)
    FROM regulatory_provisions
    WHERE source_council = 'city_of_sydney' AND is_current = true
    ORDER BY id
""")

affected = []
for row in cur.fetchall():
    pid, chkey, text = row
    matches = spaced_digit_re.findall(text)
    if matches:
        affected.append((pid, chkey, matches[:3], text[:200]))

print(f"Provisions with spaced digits: {len(affected)}")
print()

# Show samples grouped by chapter
by_chapter = {}
for pid, chkey, matches, sample in affected:
    by_chapter.setdefault(chkey, []).append((pid, matches, sample))

for chkey, items in sorted(by_chapter.items()):
    print(f"  {chkey}: {len(items)} provisions")
    for pid, matches, sample in items[:2]:
        print(f"    ID {pid}: {matches}")
        # Find the spaced digit in context
        full_matches = spaced_digit_re.finditer(sample)
        for m in full_matches:
            start = max(0, m.start() - 20)
            end = min(len(sample), m.end() + 20)
            print(f"      ...{sample[start:end]}...")
            break
    print()

cur.close()
conn.close()
