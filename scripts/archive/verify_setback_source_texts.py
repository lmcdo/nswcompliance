#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Show all rows in dcp_setback_controls with their source provision text
cur.execute("""
    SELECT sc.id, sc.lga, sc.control_type, sc.value_min, sc.value_max, sc.unit,
           sc.applicability, sc.section_ref, sc.source_text,
           rp.provision_text as full_text
    FROM dcp_setback_controls sc
    LEFT JOIN regulatory_provisions rp ON rp.id = sc.provision_id
    ORDER BY sc.lga, sc.control_type
""")
rows = cur.fetchall()
print(f"Total rows: {len(rows)}\n")
for r in rows:
    print(f"LGA: {r['lga']} | {r['control_type']} | min={r['value_min']} max={r['value_max']} {r['unit']}")
    print(f"  Section: {r['section_ref']}")
    print(f"  Source text (stored): {r['source_text'][:200] if r['source_text'] else 'NULL'}")
    print(f"  Full text (first 400): {(r['full_text'] or '')[:400]}")
    print()

conn.close()
