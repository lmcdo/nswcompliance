#!/usr/bin/env python3
"""Mark TOC provisions as not actionable."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find TOC provisions - they have section numbers with page references like "E1.1.1 ... 5"
# Pattern: ". . 5" or ".. 5" at end of lines
cur.execute('''
    SELECT id, v2_dcp_part, pdf_page, LEFT(provision_text, 200)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND provision_text ~ '\\.\\s*\\.\\s+\\d+\\s*$'
    ORDER BY v2_dcp_part, pdf_page
    LIMIT 50
''')

toc_ids = []
print("TOC provisions found:")
for r in cur.fetchall():
    print(f"ID {r[0]}: {r[1]} page {r[2]}")
    print(f"  {r[3]}...")
    toc_ids.append(r[0])
    print()

print(f"\nTotal: {len(toc_ids)}")

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute and toc_ids:
    print("\nMarking as not actionable...")
    cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = ANY(%s)", (toc_ids,))
    conn.commit()
    print(f"Done! Updated {cur.rowcount} rows")

cur.close()
conn.close()
