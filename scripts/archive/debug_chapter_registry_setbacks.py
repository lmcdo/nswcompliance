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

# Check distinct council values
cur.execute("SELECT DISTINCT council FROM dcp_chapter_registry ORDER BY council")
print("Councils in registry:", [r['council'] for r in cur.fetchall()])
print()

COUNCILS = ['ashfield', 'leichhardt', 'marrickville',
            'Inner West Ashfield', 'Inner West Leichhardt', 'Inner West Marrickville']

for council in COUNCILS:
    cur.execute("""
        SELECT chapter_key, chapter_label, r2_current_path, r2_public_pdf_url,
               page_start, page_end, is_inert, is_active
        FROM dcp_chapter_registry
        WHERE council ILIKE %s
        ORDER BY sort_order, chapter_key
    """, (f'%{council}%',))
    rows = cur.fetchall()
    if not rows:
        continue
    print(f"=== {council} ({len(rows)} chapters) ===")
    for r in rows:
        print(f"  {r['chapter_key']:50} | pages {r['page_start']}-{r['page_end']} | inert={r['is_inert']} | active={r['is_active']}")
        if r['r2_current_path']:
            print(f"    r2: {r['r2_current_path']}")
        if r['r2_public_pdf_url']:
            print(f"    pub: {r['r2_public_pdf_url']}")
    print()

conn.close()
