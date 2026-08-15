#!/usr/bin/env python3
"""
Build the structural category map by analyzing actual (chapter_key, section_header) combinations.
Shows what needs to be mapped for each council.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# For intake exclusion, we only need categories that map to TRIGGER_TO_TOPICS:
# stormwater, drainage, trees, pool, fencing/fence, parking/vehicle_access/carport,
# signage, flooding, bushfire, acoustic/noise/anef, coastal, biodiversity,
# mine_subsidence, landslide, drinking_water, demolition
#
# Everything else stays in the active set (never excluded).

EXCLUDABLE_CATEGORIES = {
    'stormwater', 'drainage', 'trees', 'pool', 'fencing', 'parking',
    'signage', 'flooding', 'bushfire', 'acoustic', 'coastal',
    'biodiversity', 'demolition', 'contamination',
}

for council in ['marrickville', 'woollahra', 'waverley', 'ashfield', 'leichhardt']:
    cur.execute("""
        SELECT source_chapter_key, section_header, COUNT(*) as cnt,
               v2_topic
        FROM regulatory_provisions
        WHERE is_current = true AND source_council = %s
        GROUP BY source_chapter_key, section_header, v2_topic
        ORDER BY source_chapter_key, section_header
    """, (council,))
    rows = cur.fetchall()

    print(f"\n{'='*80}")
    print(f"  {council.upper()} — {len(rows)} (chapter_key, header, topic) combinations")
    print(f"{'='*80}")

    # Group by chapter_key
    from collections import defaultdict
    by_chapter = defaultdict(list)
    for r in rows:
        by_chapter[r[0]].append({'header': r[1], 'count': r[2], 'topic': r[3]})

    for chapter_key, items in sorted(by_chapter.items()):
        total = sum(it['count'] for it in items)
        topics = set(it['topic'] for it in items if it['topic'])

        # Check if any current topics are excludable
        excludable = topics & EXCLUDABLE_CATEGORIES
        has_excludable = "** NEEDS MAP **" if excludable else ""

        print(f"\n  {chapter_key} ({total} provisions) {has_excludable}")
        if excludable:
            print(f"    Excludable topics present: {excludable}")

        # Show unique headers (up to 10)
        unique_headers = sorted(set(it['header'] for it in items if it['header']))
        for h in unique_headers[:10]:
            matching_topics = set(it['topic'] for it in items if it['header'] == h and it['topic'])
            topic_str = f" [{', '.join(matching_topics)}]" if matching_topics else ""
            print(f"    - {h[:65]}{topic_str}")
        if len(unique_headers) > 10:
            print(f"    ... and {len(unique_headers) - 10} more")

cur.close()
conn.close()
