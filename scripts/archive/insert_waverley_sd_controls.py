#!/usr/bin/env python3
"""Insert Waverley secondary dwelling DCP controls from C1.1.16."""
import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

DRY_RUN = '--dry-run' in sys.argv

ROWS = [
    {
        'lga': 'waverley',
        'dev_type': 'secondary_dwelling',
        'control_type': 'max_height',
        'value_min': None,
        'value_max': 3.0,
        'unit': 'm',
        'condition': 'not fronting a laneway',
        'applicability': 'secondary_dwelling_specific',
        'source_text': (
            '(f) Secondary dwellings that do not front a laneway are to be single storey only, '
            'with an overall maximum height of 3m.'
        ),
        'section_ref': 'waverley-dcp-2022/C1_1_16_controls',
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
        print(f"DRY-RUN: {row['control_type']} max={row['value_max']}{row['unit']} cond={row['condition']}")
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
        print(f"INSERTED: {row['control_type']} max={row['value_max']}{row['unit']} cond={row['condition']}")

if not DRY_RUN:
    conn.commit()
conn.close()
print("Done.")
