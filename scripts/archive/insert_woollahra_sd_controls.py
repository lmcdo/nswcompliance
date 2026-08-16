#!/usr/bin/env python3
"""Insert Woollahra secondary dwelling DCP controls from B3.2 Figure 5B.

Secondary dwellings fall under C4 of B3.2.3 (any other land use not addressed
in C1-C3), so Figure 5B applies. Minimum side setback is 1.5m for sites < 18m wide.
Rear setback is formula-based (25% of average side boundary depth) — not inserted.
"""
import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

DRY_RUN = '--dry-run' in sys.argv

ROWS = [
    {
        'lga': 'woollahra',
        'dev_type': 'secondary_dwelling',
        'control_type': 'side_setback',
        'value_min': 1.5,
        'value_max': None,
        'unit': 'm',
        'condition': 'site width < 18m (Figure 5B; varies by lot width)',
        'applicability': 'universal_residential',
        'source_text': (
            'B3.2.3 Side setbacks C4: The minimum side setback for any other land use not '
            'addressed in controls C1 to C3 above is determined by the table in Figure 5B. '
            'Figure 5B: Site width < 18.0m = 1.5m; 18.0-<21.0m = 2.0m; 21.0-<28.0m = 2.5m; '
            '28.0-<35.0m = 3.0m; 35.0m+ = 3.5m'
        ),
        'section_ref': 'chapter-b3-general-development/B3.2.3_Figure5B',
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
        print(f"SKIP (dup): {row['control_type']}")
        continue

    if DRY_RUN:
        print(f"DRY-RUN: {row['control_type']} min={row['value_min']}m cond={row['condition']}")
        print(f"  text: {row['source_text'][:120]}")
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
        print(f"INSERTED: {row['control_type']} min={row['value_min']}m")

if not DRY_RUN:
    conn.commit()
conn.close()
print("Done.")
