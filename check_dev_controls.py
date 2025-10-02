#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cur = conn.cursor()

print('=== DEVELOPMENT_CONTROLS TABLE STRUCTURE ===')
cols = cur.execute('PRAGMA table_info(development_controls)').fetchall()
for col in cols:
    print(f'{col[1]} ({col[2]})')

print('\n=== SAMPLE DEVELOPMENT_CONTROLS RECORDS ===')
sample = cur.execute('SELECT * FROM development_controls LIMIT 10').fetchall()
for i, row in enumerate(sample):
    print(f'Record {i+1}: {row}')

print('\n=== CONTROL_TYPE BREAKDOWN ===')
types = cur.execute('SELECT control_type, COUNT(*) FROM development_controls GROUP BY control_type ORDER BY COUNT(*) DESC').fetchall()
for control_type, count in types:
    print(f'{control_type}: {count} records')

print('\n=== SAMPLE BY CONTROL_TYPE ===')
for control_type, count in types[:5]:  # Top 5 types
    print(f'\n{control_type.upper()} EXAMPLES:')
    examples = cur.execute('SELECT provision_id, value_numeric, value_text, unit FROM development_controls WHERE control_type = ? LIMIT 3', (control_type,)).fetchall()
    for ex in examples:
        print(f'  Provision {ex[0]}: {ex[1]} {ex[3]} | Text: {ex[2]}')

print('\n=== LINKING TO PROVISIONS ===')
linked = cur.execute('''
SELECT dc.control_type, dc.value_numeric, dc.unit, rp.ref_number, rp.document_id
FROM development_controls dc
JOIN regulatory_provisions rp ON dc.provision_id = rp.id
WHERE dc.control_type IN ('height', 'setback', 'fsr')
LIMIT 10
''').fetchall()

print('Control Type | Value | Unit | Clause | Document')
print('-' * 60)
for row in linked:
    print(f'{row[0]:<12} | {row[1]:<5} | {row[2]:<4} | {row[3]:<8} | {row[4][:30]}...')

conn.close()