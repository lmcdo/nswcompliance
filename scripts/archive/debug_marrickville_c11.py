#!/usr/bin/env python3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Check C11
cur.execute(
    "SELECT id, ref_number, provision_text FROM regulatory_provisions "
    "WHERE ref_number LIKE '%C11%' AND source_council='marrickville' LIMIT 5"
)
rows = cur.fetchall()
for r in rows:
    print('REF:', r['ref_number'])
    print('TEXT:', (r['provision_text'] or '')[:800])
    print('---')

# Also check C10
cur.execute(
    "SELECT id, ref_number, provision_text FROM regulatory_provisions "
    "WHERE ref_number LIKE '%C10%' AND source_council='marrickville' LIMIT 3"
)
rows = cur.fetchall()
for r in rows:
    print('REF:', r['ref_number'])
    print('TEXT:', (r['provision_text'] or '')[:800])
    print('---')

conn.close()
