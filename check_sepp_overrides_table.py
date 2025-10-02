#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check sepp_lep_overrides structure
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'sepp_lep_overrides'
    ORDER BY ordinal_position
""")

print('=== sepp_lep_overrides schema ===')
for col, dtype in cur.fetchall():
    print(f'  {col:30} {dtype}')

# Get sample data
cur.execute("""
    SELECT id, lep_clause_reference, override_type,
           confidence_score, sepp_provision_id
    FROM sepp_lep_overrides
    LIMIT 10
""")

print('\n=== Sample SEPP overrides ===')
for row in cur.fetchall():
    print(f'  ID: {row[0]}, LEP Clause: {row[1]}, Type: {row[2]}, Confidence: {row[3]}, SEPP Prov: {row[4]}')

# Check if there's any zone/lga info
cur.execute("""
    SELECT COUNT(*)
    FROM sepp_lep_overrides
""")
total = cur.fetchone()[0]
print(f'\nTotal SEPP overrides: {total}')

conn.close()
