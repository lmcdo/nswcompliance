#!/usr/bin/env python3
"""Examine remaining None topic provisions for manual assignment"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib
from collections import defaultdict

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)
cur = conn.cursor()

# Get all None topic provisions
cur.execute('''
    SELECT id, provision_text, v2_dcp_part, pdf_page, document_id
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_topic IS NULL
      AND is_current = TRUE
    ORDER BY v2_dcp_part, pdf_page, id
''')
provisions = cur.fetchall()

print(f'Total None topics: {len(provisions)}')

# Group by part
by_part = defaultdict(list)
for p in provisions:
    by_part[p['v2_dcp_part']].append(p)

for part, items in sorted(by_part.items()):
    print(f'\n{"="*80}')
    print(f'{part}: {len(items)} provisions')
    print('='*80)
    for p in items:
        text = (p['provision_text'] or '')[:200].replace('\n', ' ').strip()
        print(f"\nID {p['id']} (page {p['pdf_page']})")
        print(f'  {text}...')

conn.close()
