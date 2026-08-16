#!/usr/bin/env python3
"""Direct insert of Ashfield secondary dwelling setback controls from Chapter F DS5.x."""
import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

DRY_RUN = '--dry-run' in sys.argv

ROWS = [
    {
        'lga': 'ashfield',
        'dev_type': 'secondary_dwelling',
        'control_type': 'side_setback',
        'value_min': 0.9,
        'value_max': None,
        'unit': 'm',
        'condition': None,
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'DS5.2 Minimum side setback is 0.9 metres',
        'section_ref': 'chapter-f-dev-category/DS5.2',
    },
    {
        'lga': 'ashfield',
        'dev_type': 'secondary_dwelling',
        'control_type': 'rear_setback',
        'value_min': 1.0,
        'value_max': None,
        'unit': 'm',
        'condition': 'loft over garage with rear lane access',
        'applicability': 'secondary_dwelling_specific',
        'source_text': (
            'DS5.4 If the secondary dwelling is built as a loft structure over a garage with rear lane access '
            'it may be built: in line with an existing garage or a minimum of 1 metre from the rear boundary '
            'contained within an attic space'
        ),
        'section_ref': 'chapter-f-dev-category/DS5.4',
    },
]

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

for row in ROWS:
    cur.execute("""
        SELECT id FROM dcp_setback_controls
        WHERE lga = %s AND dev_type = %s AND control_type = %s
          AND COALESCE(condition, '') = COALESCE(%s, '')
    """, (row['lga'], row['dev_type'], row['control_type'], row['condition']))
    if cur.fetchone():
        print(f"SKIP (dup): {row['control_type']} cond={row['condition']}")
        continue

    if DRY_RUN:
        print(f"DRY-RUN: {row['control_type']} min={row['value_min']}m cond={row['condition']}")
        print(f"  text: {row['source_text']}")
    else:
        cur.execute("""
            INSERT INTO dcp_setback_controls
              (lga, dev_type, control_type, value_min, value_max, unit,
               condition, applicability, source_text, section_ref)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row['lga'], row['dev_type'], row['control_type'],
            row['value_min'], row['value_max'], row['unit'],
            row['condition'], row['applicability'],
            row['source_text'], row['section_ref'],
        ))
        print(f"INSERTED: {row['control_type']} {row['value_min']}m cond={row['condition']}")

if not DRY_RUN:
    conn.commit()
conn.close()
print("Done.")
