#!/usr/bin/env python3
"""Fix Part D provisions that have wrong Part G URLs."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find Part D provisions with Part G URLs
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part D'
    AND pdf_page_image_url ILIKE '%part-g%'
    AND v2_is_actionable = true
''')

rows = cur.fetchall()
print(f"Part D provisions with Part G URLs: {len(rows)}")

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute and rows:
    print("\nFixing URLs...")
    for r in rows:
        id, page, old_url = r
        # Replace part-g with part-d in URL
        new_url = old_url.replace('part-g', 'part-d')
        cur.execute("UPDATE regulatory_provisions SET pdf_page_image_url = %s WHERE id = %s", (new_url, id))
        print(f"  ID {id}: {old_url} -> {new_url}")
    conn.commit()
    print(f"\nDone! Fixed {len(rows)} URLs")

cur.close()
conn.close()
