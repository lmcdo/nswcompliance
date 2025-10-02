#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check what clause references are in the controls we return
cur.execute("""
    SELECT DISTINCT rp.ref_number, rp.document_id
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE rp.zone = 'R2'
    LIMIT 10
""")

print('Sample LEP clause references for R2 zone:')
for ref, doc in cur.fetchall():
    print(f'  {ref:15} - {doc[:60]}')

# Check what parent clauses might match
print('\nSample SEPP overrides and their clause references:')
cur.execute("""
    SELECT lep_clause_reference, override_type, sepp_provision_id
    FROM sepp_lep_overrides
    WHERE lep_clause_reference IN ('4', '4.3', '4.4', '3', '3B')
""")

for clause, override_type, sepp_id in cur.fetchall():
    print(f'  Clause {clause:10} - {override_type:15} - SEPP {sepp_id}')

conn.close()
