#!/usr/bin/env python3
"""Quick check of dcp_setback_controls counts per LGA."""
import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT lga, COUNT(*)
    FROM dcp_setback_controls
    WHERE is_current IS NULL OR is_current = true
    GROUP BY lga ORDER BY lga
""")
rows = cur.fetchall()
total = 0
for row in rows:
    print(f'  {row[0]:25s} {row[1]:>3} controls')
    total += row[1]
print(f'\n  TOTAL: {total} controls across {len(rows)} LGAs')
conn.close()
