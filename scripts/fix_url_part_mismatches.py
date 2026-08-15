#!/usr/bin/env python3
"""Fix URL/Part mismatches - these provisions have wrong v2_dcp_part, not wrong URL."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# These Part G provisions have Part C1 URLs - likely means they're actually Part C provisions
# Check what's in them
cur.execute('''
    SELECT id, v2_dcp_part, pdf_page_image_url, pdf_page, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND pdf_page_image_url LIKE '%part-c1%'
    AND v2_is_actionable = true
    ORDER BY pdf_page
''')

rows = cur.fetchall()
print(f"Part G provisions with Part C1 URLs: {len(rows)}")

# The URL tells us the truth - if URL is part-c1, the provision is from Part C Section 1
# Let's fix the v2_dcp_part

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute:
    # Fix Part G -> Part C Section 1 based on URL
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_dcp_part = 'Part C Section 1'
        WHERE v2_dcp_part = 'Part G'
        AND pdf_page_image_url LIKE '%part-c1%'
    ''')
    print(f"Fixed Part G -> Part C Section 1: {cur.rowcount}")

    # Check for any other mismatches
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_dcp_part = 'Part C Section 2'
        WHERE v2_dcp_part NOT LIKE 'Part C Section 2'
        AND pdf_page_image_url LIKE '%part-c2%'
    ''')
    print(f"Fixed -> Part C Section 2: {cur.rowcount}")

    conn.commit()
    print("Done!")

cur.close()
conn.close()
