#!/usr/bin/env python3
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check for dcp_toc table
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name LIKE '%toc%'
""")
print('TOC tables:', [r[0] for r in cur.fetchall()])

# Check dcp_toc structure
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'dcp_toc' ORDER BY ordinal_position
""")
print('\ndcp_toc columns:', [r[0] for r in cur.fetchall()])

# Sample entries
cur.execute("""
    SELECT council_area, section_id, title, page_start, page_end
    FROM dcp_toc
    WHERE council_area ILIKE '%leichhardt%'
    ORDER BY page_start
    LIMIT 20
""")
print('\nLeichhardt TOC entries (page_start -> section):')
for r in cur.fetchall():
    print(f'  p{r[3]:3}-{r[4]:3} | {r[1]:15} | {r[2][:50]}')
conn.close()
