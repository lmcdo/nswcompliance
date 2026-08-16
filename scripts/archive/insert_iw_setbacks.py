#!/usr/bin/env python3
"""
Insert/fix DCP setback controls for Marrickville and Leichhardt.

Marrickville DCP 2011 s4.1.6.2 C10-C11 (OCR-verified 2026-04-22):
  - DH front/rear: site_derived
  - DH side: 3 storey-based prescribed rows + 1 site_derived for <8m lots
  - SD: existing rows correct (separation 4m, side 1.5m) — not touched

Leichhardt DCP 2013 Part C (dcp_general_requirements confirmed, OCR-verified 2026-04-22):
  - All DH setbacks site_derived (BLZ/graph-based — no fixed numbers)
  - SD: no LGA-specific DCP controls — defers to SEPP H2021
"""
import os, sys, psycopg2
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

# ── Marrickville — fix DH rows ─────────────────────────────────────────────────
# Delete the incomplete existing DH side_setback row (no condition, val=1.5)
cur.execute("""
    DELETE FROM dcp_setback_controls
    WHERE lga = 'marrickville'
      AND dev_type = 'dwelling_house'
      AND control_type = 'side_setback'
""")
print(f"Deleted {cur.rowcount} marrickville DH side_setback rows (replacing with storey-specific)")

MVILLE_DH = [
    # Front — site_derived
    {
        'lga': 'marrickville', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': None, 'value_max': None, 'unit': 'm',
        'condition': None,
        'applicability': 'universal_residential',
        'source_text': 'Consistent with setback of adjoining development or dominant setback along the street. Council discretion on corner lots.',
        'section_ref': 's4.1.6.2-c10', 'dcp_version': 'v1.1-2026-04-06',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
    # Rear — site_derived
    {
        'lga': 'marrickville', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': None, 'value_max': None, 'unit': 'm',
        'condition': None,
        'applicability': 'universal_residential',
        'source_text': 'Where predominant rear building line exists: maintain it. Otherwise assessed on merit — adverse amenity impacts and adequate open space are primary considerations.',
        'section_ref': 's4.1.6.2-c10', 'dcp_version': 'v1.1-2026-04-06',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
    # Side — lot <8m — site_derived
    {
        'lga': 'marrickville', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': None, 'value_max': None, 'unit': 'm',
        'condition': 'lot width <8m — Council discretion',
        'applicability': 'universal_residential',
        'source_text': 'Visual impact, solar access to adjoining dwellings and street context determine setback. No fixed minimum.',
        'section_ref': 's4.1.6.2-c10', 'dcp_version': 'v1.1-2026-04-06',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
    # Side — 1 storey, lot ≥8m
    {
        'lga': 'marrickville', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': '1 storey, lot width ≥8m',
        'applicability': 'universal_residential',
        'source_text': 'Minimum side setback 900mm for single storey dwellings on lots 8m wide or over.',
        'section_ref': 's4.1.6.2-c10', 'dcp_version': 'v1.1-2026-04-06',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
    # Side — 2 storey, lot ≥8m
    {
        'lga': 'marrickville', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 1.5, 'value_max': None, 'unit': 'm',
        'condition': '2 storeys, lot width ≥8m',
        'applicability': 'universal_residential',
        'source_text': 'Minimum side setback 1.5m for two storey dwellings on lots 8m wide or over.',
        'section_ref': 's4.1.6.2-c10', 'dcp_version': 'v1.1-2026-04-06',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
    # Side — 3 storey, lot ≥8m
    {
        'lga': 'marrickville', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 2.5, 'value_max': None, 'unit': 'm',
        'condition': '3 storeys, lot width ≥8m',
        'applicability': 'universal_residential',
        'source_text': 'Minimum side setback 2.5m for three storey dwellings on lots 8m wide or over.',
        'section_ref': 's4.1.6.2-c10', 'dcp_version': 'v1.1-2026-04-06',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
]

INSERT = """
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

for r in MVILLE_DH:
    cur.execute(INSERT, r)
    row_id = cur.fetchone()[0]
    print(f"  [marrickville DH] id={row_id} {r['control_type']} val={r['value_min']}  cond={r['condition']}")

# ── Leichhardt — insert all DH (all site_derived) ────────────────────────────
# No existing rows to delete (already confirmed 0 rows)

LEICH_DH = [
    # Front — BLZ site_derived
    {
        'lga': 'leichhardt', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': None, 'value_max': None, 'unit': 'm',
        'condition': None,
        'applicability': 'universal_residential',
        'source_text': 'Building Line Zone (BLZ): determined by where buildings sit on adjoining properties. No fixed number — derived by planner from site visit.',
        'section_ref': 'part-c-c4-c7', 'dcp_version': 'v1.0-2026-03-01',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
    # Rear — BLZ site_derived
    {
        'lga': 'leichhardt', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': None, 'value_max': None, 'unit': 'm',
        'condition': None,
        'applicability': 'universal_residential',
        'source_text': 'Consistent with rear building line of adjoining properties. No fixed number — assessed on merit.',
        'section_ref': 'part-c-c4-c7', 'dcp_version': 'v1.0-2026-03-01',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
    # Side — graph-based site_derived
    {
        'lga': 'leichhardt', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': None, 'value_max': None, 'unit': 'm',
        'condition': None,
        'applicability': 'universal_residential',
        'source_text': 'Scales with wall height per Figure C129 (approx 1.0m at 4m wall height, 1.5m at 5.5m). Not a fixed minimum — derived from the DCP graph by a planner.',
        'section_ref': 'part-c-c4-c7', 'dcp_version': 'v1.0-2026-03-01',
        'is_current': True, 'extraction_method': 'mistral_ocr',
    },
]

for r in LEICH_DH:
    cur.execute(INSERT, r)
    row_id = cur.fetchone()[0]
    print(f"  [leichhardt DH] id={row_id} {r['control_type']} val={r['value_min']}  cond={r['condition']}")

conn.commit()
conn.close()
print("\nDone. Marrickville DH complete (6 rows). Leichhardt DH inserted (3 site_derived rows).")
print("SD rows for both LGAs unchanged.")
