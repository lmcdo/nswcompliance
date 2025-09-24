#!/usr/bin/env python3
"""
Check LEP and DCP clause coverage in corrected database
"""

import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning_corrected',
    user='postgres',
    password='postgres',
    port='5432'
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print('=== CHECKING LEP AND DCP CLAUSE COVERAGE ===')
print()

# 1. Check legal instrument distribution
print('1. LEGAL INSTRUMENT DISTRIBUTION:')
cursor.execute('''
    SELECT instrument_type, COUNT(*) as count
    FROM legal_instruments
    GROUP BY instrument_type
    ORDER BY count DESC
''')
instruments = cursor.fetchall()

for inst in instruments:
    print(f'  {inst["instrument_type"]}: {inst["count"]} instruments')

print()

# 2. Check provision distribution by instrument type
print('2. PROVISION DISTRIBUTION BY INSTRUMENT TYPE:')
cursor.execute('''
    SELECT li.instrument_type, COUNT(rp.id) as provision_count
    FROM legal_instruments li
    LEFT JOIN regulatory_provisions rp ON rp.instrument_id = li.id
    GROUP BY li.instrument_type
    ORDER BY provision_count DESC
''')
provision_dist = cursor.fetchall()

for dist in provision_dist:
    print(f'  {dist["instrument_type"]}: {dist["provision_count"]} provisions')

print()

# 3. Check document text availability for each type
print('3. DOCUMENT TEXT AVAILABILITY:')
cursor.execute('''
    SELECT
        li.instrument_type,
        COUNT(DISTINCT d.id) as docs_with_full_text,
        AVG(d.char_count) as avg_char_count,
        MIN(d.char_count) as min_chars,
        MAX(d.char_count) as max_chars
    FROM legal_instruments li
    JOIN regulatory_provisions rp ON rp.instrument_id = li.id
    JOIN documents d ON d.id = rp.document_id
    WHERE d.full_text IS NOT NULL AND d.char_count > 0
    GROUP BY li.instrument_type
    ORDER BY docs_with_full_text DESC
''')
text_coverage = cursor.fetchall()

for coverage in text_coverage:
    print(f'  {coverage["instrument_type"]}:')
    print(f'    Documents with full text: {coverage["docs_with_full_text"]}')
    print(f'    Avg document size: {int(coverage["avg_char_count"]):,} chars')
    print(f'    Range: {int(coverage["min_chars"]):,} - {int(coverage["max_chars"]):,} chars')
    print()

# 4. Sample LEP provisions
print('4. SAMPLE LEP PROVISIONS:')
cursor.execute('''
    SELECT rp.id, rp.ref_number, LEFT(rp.provision_text, 150) as text_sample,
           li.instrument_code, d.char_count
    FROM regulatory_provisions rp
    JOIN legal_instruments li ON rp.instrument_id = li.id
    JOIN documents d ON d.id = rp.document_id
    WHERE li.instrument_type = 'LEP'
    AND rp.provision_text IS NOT NULL
    ORDER BY d.char_count DESC
    LIMIT 3
''')
lep_samples = cursor.fetchall()

for sample in lep_samples:
    print(f'  LEP ID {sample["id"]}: {sample["ref_number"]}')
    print(f'    Instrument: {sample["instrument_code"]}')
    print(f'    Document size: {sample["char_count"]:,} chars')
    print(f'    Text: {sample["text_sample"]}...')
    print()

# 5. Sample DCP provisions
print('5. SAMPLE DCP PROVISIONS:')
cursor.execute('''
    SELECT rp.id, rp.ref_number, LEFT(rp.provision_text, 150) as text_sample,
           li.instrument_code, d.char_count
    FROM regulatory_provisions rp
    JOIN legal_instruments li ON rp.instrument_id = li.id
    JOIN documents d ON d.id = rp.document_id
    WHERE li.instrument_type = 'DCP'
    AND rp.provision_text IS NOT NULL
    ORDER BY d.char_count DESC
    LIMIT 3
''')
dcp_samples = cursor.fetchall()

for sample in dcp_samples:
    print(f'  DCP ID {sample["id"]}: {sample["ref_number"]}')
    print(f'    Instrument: {sample["instrument_code"]}')
    print(f'    Document size: {sample["char_count"]:,} chars')
    print(f'    Text: {sample["text_sample"]}...')
    print()

# 6. Test complete text extraction for LEP and DCP
print('6. TESTING COMPLETE TEXT EXTRACTION:')

# Test LEP
cursor.execute('''
    SELECT rp.id, rp.ref_number, d.full_text, li.instrument_type
    FROM regulatory_provisions rp
    JOIN legal_instruments li ON rp.instrument_id = li.id
    JOIN documents d ON d.id = rp.document_id
    WHERE li.instrument_type = 'LEP'
    AND d.full_text ILIKE '%setback%'
    LIMIT 1
''')
lep_test = cursor.fetchone()

if lep_test:
    print(f'  LEP Test - ID {lep_test["id"]}, Ref {lep_test["ref_number"]}:')
    # Try to extract clause from full text
    full_text = lep_test["full_text"]
    ref_number = lep_test["ref_number"]

    # Simple extraction test
    start_idx = full_text.lower().find(ref_number.lower())
    if start_idx != -1:
        extract = full_text[start_idx:start_idx+300]
        print(f'    Extraction possible: {extract[:100]}...')
    else:
        print(f'    Extraction challenging - clause {ref_number} not found in standard format')
else:
    print('    No LEP test case found')

print()

# Test DCP
cursor.execute('''
    SELECT rp.id, rp.ref_number, d.full_text, li.instrument_type
    FROM regulatory_provisions rp
    JOIN legal_instruments li ON rp.instrument_id = li.id
    JOIN documents d ON d.id = rp.document_id
    WHERE li.instrument_type = 'DCP'
    AND d.full_text ILIKE '%height%'
    LIMIT 1
''')
dcp_test = cursor.fetchone()

if dcp_test:
    print(f'  DCP Test - ID {dcp_test["id"]}, Ref {dcp_test["ref_number"]}:')
    # Try to extract clause from full text
    full_text = dcp_test["full_text"]
    ref_number = dcp_test["ref_number"]

    # Simple extraction test
    start_idx = full_text.lower().find(ref_number.lower())
    if start_idx != -1:
        extract = full_text[start_idx:start_idx+300]
        print(f'    Extraction possible: {extract[:100]}...')
    else:
        print(f'    Extraction challenging - clause {ref_number} not found in standard format')
else:
    print('    No DCP test case found')

cursor.close()
conn.close()

print()
print('=== COVERAGE ANALYSIS COMPLETE ===')