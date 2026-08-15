#!/usr/bin/env python3
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check what page data we have
cur.execute('''
    SELECT
        COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as has_page,
        COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as has_marker,
        COUNT(*) as total
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%' AND v2_is_actionable = true
''')
r = cur.fetchone()
print(f'Leichhardt: {r[0]} have page, {r[1]} have marker, {r[2]} total')

# Sample: provisions without markers
cur.execute('''
    SELECT pdf_page, v2_dcp_part, LEFT(provision_text, 150)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND (v2_marker IS NULL OR v2_marker = '')
    LIMIT 5
''')
print('\nProvisions WITHOUT markers:')
for row in cur.fetchall():
    print(f'  Page {row[0]} | {row[1]} | {row[2][:80]}...')

conn.close()
