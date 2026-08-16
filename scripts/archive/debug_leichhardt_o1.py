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
    SELECT id, ref_number, source_chapter_key, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'leichhardt'
      AND is_current = TRUE
      AND source_chapter_key ILIKE '%part_c_s2%'
    ORDER BY ref_number
""")
rows = cur.fetchall()
print(f"Found {len(rows)} Leichhardt part_c_s2 provisions\n")
for r in rows:
    print(f"REF: {r['ref_number']}")
    print(f"TOPIC: {r['v2_topic']}")
    print(f"TEXT: {(r['provision_text'] or '')[:600]}")
    print('---')

conn.close()
