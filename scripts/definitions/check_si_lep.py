#!/usr/bin/env python3
"""Check if Standard Instrument LEP definitions exist in database."""

import os
import psycopg2

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': os.environ['DB_PASSWORD'],
    'host': 'localhost'
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Check for Standard Instrument LEP documents
print('Checking for Standard Instrument LEP documents...')
cur.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id ILIKE '%standard%instrument%'
       OR document_id ILIKE '%LEP%order%'
       OR document_id ILIKE '%inner%west%LEP%'
    LIMIT 20;
""")
rows = cur.fetchall()
print(f'Found {len(rows)} matching document_ids:')
for row in rows:
    print(f'  {row[0]}')

print()
print('Checking for Inner West LEP documents...')
cur.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id ILIKE '%inner%west%LEP%'
       OR document_id ILIKE '%IWLEP%'
    LIMIT 20;
""")
rows = cur.fetchall()
print(f'Found {len(rows)} Inner West LEP documents:')
for row in rows:
    print(f'  {row[0]}')

print()
print('Sample provisions with "means" from LEP documents:')
cur.execute("""
    SELECT document_id, ref_number, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%LEP%' OR document_id ILIKE '%local%environmental%plan%')
    AND provision_text ILIKE '% means %'
    LIMIT 10;
""")
for doc_id, ref, text in cur.fetchall():
    print(f'  [{doc_id[:40]}...] {text[:60]}...')

cur.close()
conn.close()
