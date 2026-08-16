#!/usr/bin/env python3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

for ref in [
    'Marrickville_DCP_2011__part4_s1_low_density__O14_controls_C11',
    'Marrickville_DCP_2011__part4_s1_low_density__O14_controls_C10',
]:
    cur.execute(
        "SELECT id, ref_number, provision_text, is_current FROM regulatory_provisions WHERE ref_number = %s",
        (ref,)
    )
    r = cur.fetchone()
    if r:
        print('REF:', r['ref_number'])
        print('IS_CURRENT:', r['is_current'])
        print('TEXT:', r['provision_text'] or '(empty)')
        print('---')
    else:
        print(f'NOT FOUND: {ref}')
        print('---')

conn.close()
