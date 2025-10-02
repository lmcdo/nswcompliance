#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cur = conn.cursor()

print('=== DEVELOPMENT CONTROLS LINKED TO CLAUSES ===')
linked = cur.execute('''
SELECT dc.control_type, dc.value_numeric, dc.unit, dc.value_text, rp.ref_number, rp.document_id
FROM development_controls dc
JOIN regulatory_provisions rp ON dc.provision_id = rp.id
WHERE dc.control_type IN ('height', 'setback', 'fsr') AND dc.value_numeric IS NOT NULL
LIMIT 15
''').fetchall()

for row in linked:
    ctrl_type = row[0] or 'unknown'
    value = row[1] or 0
    unit = row[2] or ''
    ref_num = row[4] or 'no_ref'
    doc = row[5] or 'no_doc'
    print(f'{ctrl_type}: {value} {unit} from {ref_num} ({doc[:20]}...)')

print('\n=== QUANTITATIVE STANDARDS TABLE ===')
quant = cur.execute('SELECT * FROM quantitative_standards LIMIT 10').fetchall()
for i, row in enumerate(quant):
    print(f'Record {i+1}: {row}')

print('\n=== ZONE-SPECIFIC CONTROLS ===')
zone_controls = cur.execute('''
SELECT dc.control_type, dc.value_numeric, dc.unit, dc.zone_applicable, rp.ref_number
FROM development_controls dc
JOIN regulatory_provisions rp ON dc.provision_id = rp.id
WHERE dc.zone_applicable IS NOT NULL AND dc.zone_applicable != 'general'
LIMIT 10
''').fetchall()

print('Zone-specific development controls:')
for row in zone_controls:
    print(f'  {row[4]}: {row[0]} = {row[1]} {row[2]} (Zone: {row[3]})')

conn.close()