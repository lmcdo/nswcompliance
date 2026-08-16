#!/usr/bin/env python3
"""
Direct insert of Canterbury-Bankstown DCP setback controls.
Ch 5.1 = Former Bankstown LGA (DH + SD controls)
Ch 5.2 = Former Canterbury LGA (DH controls; SD defers to SEPP H2021 — no rows)
All extraction_method='manual' from PDF inspection.
"""
import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

DCP_VERSION = 'v1.0-2026-03-12'
LGA = 'canterbury_bankstown'

rows = [
    # ── Ch 5.1 Former Bankstown — DWELLING HOUSE (Section 2) ──────────────────
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 5.5, 'value_max': None, 'unit': 'm',
        'condition': 'ground floor, primary street',
        'applicability': 'universal_residential',
        'source_text': 'Ground floor: minimum 5.5m from primary street boundary',
        'section_ref': 'ch5-1-s2-front',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 6.5, 'value_max': None, 'unit': 'm',
        'condition': '2nd storey, primary street',
        'applicability': 'universal_residential',
        'source_text': '2nd storey: minimum 6.5m from primary street boundary',
        'section_ref': 'ch5-1-s2-front',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary street or corner allotment',
        'applicability': 'universal_residential',
        'source_text': 'Secondary street/corner: minimum 3.0m setback',
        'section_ref': 'ch5-1-s2-front',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'wall height ≤7m, former Bankstown LGA (Ch 5.1)',
        'applicability': 'universal_residential',
        'source_text': 'Side setback: minimum 0.9m where wall height does not exceed 7m',
        'section_ref': 'ch5-1-s2-side',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 1.5, 'value_max': None, 'unit': 'm',
        'condition': 'wall height >7m, former Bankstown LGA (Ch 5.1)',
        'applicability': 'universal_residential',
        'source_text': 'Side setback: minimum 1.5m where wall height exceeds 7m',
        'section_ref': 'ch5-1-s2-side',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },

    # ── Ch 5.1 Former Bankstown — SECONDARY DWELLING (Section 3) ──────────────
    {
        'lga': LGA, 'dev_type': 'secondary_dwelling', 'control_type': 'front_setback',
        'value_min': 5.5, 'value_max': None, 'unit': 'm',
        'condition': 'ground floor, primary street, former Bankstown LGA (Ch 5.1)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'Secondary dwelling: minimum 5.5m from primary street (ground floor)',
        'section_ref': 'ch5-1-s3-front',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'secondary_dwelling', 'control_type': 'front_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary or corner street, former Bankstown LGA (Ch 5.1)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'Secondary dwelling: minimum 3.0m from secondary/corner street',
        'section_ref': 'ch5-1-s3-front',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'secondary_dwelling', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'wall height ≤7m, former Bankstown LGA (Ch 5.1)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'Secondary dwelling side setback: 0.9m minimum where wall height ≤7m',
        'section_ref': 'ch5-1-s3-11',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'secondary_dwelling', 'control_type': 'rear_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'wall height ≤7m, former Bankstown LGA (Ch 5.1)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'Secondary dwelling rear setback: 0.9m minimum where wall height ≤7m',
        'section_ref': 'ch5-1-s3-11',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'secondary_dwelling', 'control_type': 'side_setback',
        'value_min': 1.5, 'value_max': None, 'unit': 'm',
        'condition': 'wall height >7m, former Bankstown LGA (Ch 5.1)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'Secondary dwelling side setback: 1.5m minimum where wall height >7m',
        'section_ref': 'ch5-1-s3-12',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'secondary_dwelling', 'control_type': 'rear_setback',
        'value_min': 1.5, 'value_max': None, 'unit': 'm',
        'condition': 'wall height >7m, former Bankstown LGA (Ch 5.1)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'Secondary dwelling rear setback: 1.5m minimum where wall height >7m',
        'section_ref': 'ch5-1-s3-12',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'secondary_dwelling', 'control_type': 'max_height',
        'value_min': None, 'value_max': 3.0, 'unit': 'm',
        'condition': 'detached secondary dwelling, wall height limit, single storey only',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 'Detached secondary dwelling: maximum wall height 3.0m, must be single storey',
        'section_ref': 'ch5-1-s3-height',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },

    # ── Ch 5.2 Former Canterbury — DWELLING HOUSE (Section 2.6) ───────────────
    # Table 3: lot frontage ≤12.5m
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 5.5, 'value_max': None, 'unit': 'm',
        'condition': 'lot frontage ≤12.5m (Table 3), former Canterbury LGA (Ch 5.2)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3 (frontage ≤12.5m): front setback minimum 5.5m',
        'section_ref': 'ch5-2-s2.6-table3',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'lot frontage ≤12.5m (Table 3), former Canterbury LGA (Ch 5.2)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3 (frontage ≤12.5m): side setback minimum 0.9m',
        'section_ref': 'ch5-2-s2.6-table3',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'all lots (Table 3 and 4), former Canterbury LGA (Ch 5.2)',
        'applicability': 'universal_residential',
        'source_text': 'Rear setback minimum 6.0m (applies to all lot frontages)',
        'section_ref': 'ch5-2-s2.6-rear',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    # Table 4: lot frontage >12.5m
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'lot frontage >12.5m (Table 4), or average of neighbours, former Canterbury LGA (Ch 5.2)',
        'applicability': 'universal_residential',
        'source_text': 'Table 4 (frontage >12.5m): front setback 6.0m or average of adjoining dwellings',
        'section_ref': 'ch5-2-s2.6-table4',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 2.0, 'value_max': None, 'unit': 'm',
        'condition': 'corner allotment secondary street, lot frontage >12.5m (Table 4), former Canterbury LGA (Ch 5.2)',
        'applicability': 'universal_residential',
        'source_text': 'Table 4: corner allotment secondary street setback minimum 2.0m',
        'section_ref': 'ch5-2-s2.6-table4',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 1.0, 'value_max': None, 'unit': 'm',
        'condition': 'lot frontage >12.5m (Table 4), former Canterbury LGA (Ch 5.2)',
        'applicability': 'universal_residential',
        'source_text': 'Table 4 (frontage >12.5m): side setback minimum 1.0m',
        'section_ref': 'ch5-2-s2.6-table4',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    # Major road front setback
    {
        'lga': LGA, 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 9.0, 'value_max': None, 'unit': 'm',
        'condition': 'major road frontage (C1), former Canterbury LGA (Ch 5.2)',
        'applicability': 'universal_residential',
        'source_text': 'C1: Where lot fronts a major road, minimum front setback is 9.0m',
        'section_ref': 'ch5-2-s2.6-C1',
        'dcp_version': DCP_VERSION, 'is_current': True, 'extraction_method': 'manual',
    },
    # Ch 5.2 SD: DEFERS to SEPP H2021 — no rows inserted
    # (Section 7 states SD must comply with SEPP Housing 2021, no additional numeric DCP controls)
]

INSERT_SQL = """
    INSERT INTO dcp_setback_controls
        (lga, dev_type, control_type, value_min, value_max, unit,
         condition, applicability, source_text, section_ref,
         dcp_version, is_current, extraction_method)
    VALUES
        (%(lga)s, %(dev_type)s, %(control_type)s, %(value_min)s, %(value_max)s, %(unit)s,
         %(condition)s, %(applicability)s, %(source_text)s, %(section_ref)s,
         %(dcp_version)s, %(is_current)s, %(extraction_method)s)
    RETURNING id
"""

print(f"Inserting {len(rows)} Canterbury-Bankstown setback controls...")
inserted = 0
for row in rows:
    cur.execute(INSERT_SQL, row)
    row_id = cur.fetchone()[0]
    print(f"  [{row_id}] {row['dev_type']:20} {row['control_type']:18} "
          f"{row.get('value_min') or '':>5} / {row.get('value_max') or '':>5} {row['unit']}  "
          f"— {row['condition'][:60]}")
    inserted += 1

conn.commit()
print(f"\nDone. Inserted {inserted} rows for lga='{LGA}'.")

# Verify
cur.execute(
    "SELECT dev_type, control_type, value_min, value_max, unit, condition "
    "FROM dcp_setback_controls WHERE lga = %s AND is_current = TRUE "
    "ORDER BY dev_type, control_type, section_ref",
    (LGA,)
)
print(f"\nAll current {LGA} rows:")
for r in cur.fetchall():
    print(f"  {r[0]:20} {r[1]:18} min={r[2]} max={r[3]} {r[4]}  [{r[5][:50]}]")

conn.close()
