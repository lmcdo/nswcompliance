#!/usr/bin/env python3
"""Fix Part D provisions with wrong topics."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Part D is structured as:
# D1 - Energy
# D2 - Waste (construction)
# D3 - Waste (residential)
# D4 - Waste (commercial/mixed use) - this is where the mixed use waste provision is

# Find all Part D provisions and check their topics
cur.execute('''
    SELECT id, pdf_page, v2_topic, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part D'
    AND v2_is_actionable = true
    ORDER BY pdf_page, id
''')

# Group by page to understand structure
from collections import defaultdict
by_page = defaultdict(list)
for r in cur.fetchall():
    by_page[r[1]].append((r[0], r[2], r[3]))

print("Part D provisions by page:")
for page in sorted(by_page.keys()):
    print(f"\nPage {page}:")
    for id, topic, text in by_page[page][:3]:  # Show first 3 per page
        print(f"  ID {id} [{topic}]: {text[:60]}...")

# Fix provisions that mention "waste" but are classified as energy
cur.execute('''
    SELECT id, provision_text
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part D'
    AND v2_topic = 'energy'
    AND v2_is_actionable = true
    AND (provision_text ILIKE '%waste%' OR provision_text ILIKE '%recycl%' OR provision_text ILIKE '%garbage%')
''')

waste_ids = [r[0] for r in cur.fetchall()]
print(f"\n\nEnergy provisions that should be waste: {len(waste_ids)}")

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute and waste_ids:
    cur.execute("UPDATE regulatory_provisions SET v2_topic = 'waste' WHERE id = ANY(%s)", (waste_ids,))
    conn.commit()
    print(f"Fixed {cur.rowcount} provisions")

cur.close()
conn.close()
