#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT DISTINCT source_chapter_key, v2_topic, count(*) as cnt
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt' AND is_current = TRUE
    GROUP BY source_chapter_key, v2_topic
    ORDER BY source_chapter_key, cnt DESC
""")
for r in cur.fetchall():
    print(f"  {r['source_chapter_key']:45} | {(r['v2_topic'] or 'NULL'):20} | {r['cnt']}")

conn.close()
