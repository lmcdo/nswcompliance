#!/usr/bin/env python3
import os, sys, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

for council in ('waverley', 'woollahra'):
    cur.execute("""
        SELECT DISTINCT source_chapter_key, v2_topic, count(*) as cnt
        FROM regulatory_provisions
        WHERE source_council = %s AND is_current = TRUE
        GROUP BY source_chapter_key, v2_topic
        ORDER BY source_chapter_key, cnt DESC
    """, (council,))
    rows = cur.fetchall()
    print(f"\n=== {council} ({len(rows)} chapter/topic combos) ===")
    for r in rows:
        print(f"  {(r['source_chapter_key'] or 'NULL'):50} | {(r['v2_topic'] or 'NULL'):25} | {r['cnt']}")

conn.close()
