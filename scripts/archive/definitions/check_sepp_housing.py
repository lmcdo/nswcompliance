#!/usr/bin/env python3
"""Quick check of SEPP Housing provisions in database."""

import psycopg2

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Check exact document_id format for SEPP Housing
print('SEPP document_ids with State and Housing:')
cur.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id ILIKE '%State%Environmental%Housing%'
    LIMIT 20;
""")
for row in cur.fetchall():
    print(f'  {row[0]}')

print()
print('Check query with LIKE:')
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE '%State_Environmental_Planning_Policy_(Housing)_2021%';
""")
print(f'  With underscores: {cur.fetchone()[0]}')

# Check with escaped parentheses
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE 'State_Environmental_Planning_Policy_(Housing)_2021%';
""")
print(f'  Starting with exact pattern: {cur.fetchone()[0]}')

# Check section headers for SEPP Housing
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE 'State_Environmental_Planning_Policy_(Housing)_2021%'
    AND section_header ILIKE '%Dictionary%';
""")
print(f'  With Dictionary section: {cur.fetchone()[0]}')

# Check provision_text with means
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE 'State_Environmental_Planning_Policy_(Housing)_2021%'
    AND provision_text ILIKE '% means %';
""")
print(f'  With "means" in text: {cur.fetchone()[0]}')

cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id LIKE '%State_Environmental_Planning_Policy_%Housing%2021%';
""")
print(f'  With percent wildcards: {cur.fetchone()[0]}')

print()
# Check what SEPP Housing documents exist
print('SEPP Housing document_ids (all with Housing):')
cur.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id ILIKE '%housing%'
    LIMIT 10;
""")
for row in cur.fetchall():
    print(f'  {row[0]}')

print()
print('Sample ref_numbers from Housing provisions:')
cur.execute("""
    SELECT DISTINCT ref_number
    FROM regulatory_provisions
    WHERE document_id ILIKE '%housing%'
    LIMIT 20;
""")
for row in cur.fetchall():
    print(f'  {row[0]}')

print()
print('Section headers:')
cur.execute("""
    SELECT DISTINCT section_header
    FROM regulatory_provisions
    WHERE document_id ILIKE '%housing%'
    LIMIT 20;
""")
for row in cur.fetchall():
    print(f'  {row[0]}')

print()
print('Sample provision texts with "means":')
cur.execute("""
    SELECT ref_number, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%housing%'
    AND provision_text ILIKE '%means%'
    LIMIT 10;
""")
for ref, text in cur.fetchall():
    print(f'  [{ref}] {text}...')

cur.close()
conn.close()
