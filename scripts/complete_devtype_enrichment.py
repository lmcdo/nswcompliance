#!/usr/bin/env python3
"""Complete dev-type enrichment by setting defaults"""
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("SET statement_timeout = '600s'")

print("Completing dev-type enrichment...")

# Set ALL for remaining provisions without dev_types
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_applicable_dev_types = ARRAY['ALL']
    WHERE v2_applicable_dev_types IS NULL OR v2_applicable_dev_types = '{}'
""")
updated = cur.rowcount
conn.commit()

print(f'Set dev_types to ALL for {updated} provisions')

# Verify
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_applicable_dev_types IS NOT NULL
""")
total = cur.fetchone()[0]
print(f'Total provisions with dev_types: {total} / 48374')

conn.close()
print("[OK] Dev-type enrichment complete")
