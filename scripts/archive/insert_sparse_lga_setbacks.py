#!/usr/bin/env python3
"""
Manual insert of DCP setback controls for 5 sparse LGAs:
  hornsby, northern_beaches, campbelltown, liverpool, blacktown

Clears all existing rows for these LGAs first (they had no conditions,
some false positives), then inserts correct rows with proper conditions.

All extraction_method='manual' from direct PDF inspection.
"""
import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

TARGET_LGAS = ['hornsby', 'northern_beaches', 'campbelltown', 'liverpool', 'blacktown']

# ── Delete existing rows for these LGAs (known to have no conditions + some FPs) ──
cur.execute("DELETE FROM dcp_setback_controls WHERE lga = ANY(%s)", (TARGET_LGAS,))
deleted = cur.rowcount
print(f"Deleted {deleted} existing rows for {TARGET_LGAS}")

rows = [

    # ════════════════════════════════════════════════════════════════
    # HORNSBY — DCP 2024, Part 3 Residential (amended June 2025)
    # Table 3.1.2-a: Dwelling Houses and Dual Occupancies
    # No dedicated SD section — DH controls apply as universal_residential
    # ════════════════════════════════════════════════════════════════
    {
        'lga': 'hornsby', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'local road (standard)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3.1.2-a: Front boundary (local road) minimum 6m',
        'section_ref': 's3.1.2-table-a', 'dcp_version': 'v2024-jun2025',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'hornsby', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 9.0, 'value_max': None, 'unit': 'm',
        'condition': 'designated road (Council-identified)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3.1.2-a: Front boundary (designated road) minimum 9m',
        'section_ref': 's3.1.2-table-a', 'dcp_version': 'v2024-jun2025',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'hornsby', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary frontage on corner allotment',
        'applicability': 'universal_residential',
        'source_text': 'Table 3.1.2-a: Secondary boundary (corner lots) minimum 3m',
        'section_ref': 's3.1.2-table-a', 'dcp_version': 'v2024-jun2025',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'hornsby', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': '1 storey element (≤4.5m height)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3.1.2-a: Side boundary up to 1 storey = 0.9m',
        'section_ref': 's3.1.2-table-a', 'dcp_version': 'v2024-jun2025',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'hornsby', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 1.5, 'value_max': None, 'unit': 'm',
        'condition': '2 storey element (>4.5m height)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3.1.2-a: Side boundary 2 storey element = 1.5m',
        'section_ref': 's3.1.2-table-a', 'dcp_version': 'v2024-jun2025',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'hornsby', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': '1 storey element (≤4.5m height)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3.1.2-a: Rear boundary up to 1 storey = 3m',
        'section_ref': 's3.1.2-table-a', 'dcp_version': 'v2024-jun2025',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'hornsby', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 8.0, 'value_max': None, 'unit': 'm',
        'condition': '2 storey element (>4.5m height)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3.1.2-a: Rear boundary 2 storey element = 8m',
        'section_ref': 's3.1.2-table-a', 'dcp_version': 'v2024-jun2025',
        'is_current': True, 'extraction_method': 'manual',
    },

    # ════════════════════════════════════════════════════════════════
    # NORTHERN BEACHES — Warringah DCP 2011
    # Zone-organized, map-based. R2 Low Density Residential.
    # Side setbacks stored on DCP maps (not fixed text value).
    # SD controls not in DCP text — governed by SEPP H2021.
    # Note: existing max_height 8.5m row had no verifiable text source — excluded.
    # ════════════════════════════════════════════════════════════════
    {
        'lga': 'northern_beaches', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 6.5, 'value_max': None, 'unit': 'm',
        'condition': 'primary street, R2 zone (all other R2 land)',
        'applicability': 'universal_residential',
        'source_text': 'Front Boundary Setbacks R2: All other land in R2 zone 6.5m',
        'section_ref': 'B3-front-R2', 'dcp_version': 'v2011-2016',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'northern_beaches', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 3.5, 'value_max': None, 'unit': 'm',
        'condition': 'secondary/corner frontage, R2 zone (where primary is 6.5m to both)',
        'applicability': 'universal_residential',
        'source_text': 'Front Boundary Exceptions R2: corner lots secondary frontage may reduce to min 3.5m',
        'section_ref': 'B3-front-R2-corner', 'dcp_version': 'v2011-2016',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'northern_beaches', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'all other R2 land (not Madison Estate)',
        'applicability': 'universal_residential',
        'source_text': 'Rear Boundary Setbacks R2: All other land under R2 = 6m',
        'section_ref': 'B8-rear-R2', 'dcp_version': 'v2011-2016',
        'is_current': True, 'extraction_method': 'manual',
    },

    # ════════════════════════════════════════════════════════════════
    # CAMPBELLTOWN — Campbelltown (Sustainable City) DCP 2015
    # Updated 02/09/2024
    # Section 3.6.1.3 = DH setbacks; Section 3.6.2.2 = SD setbacks
    # ════════════════════════════════════════════════════════════════
    # DH setbacks
    {
        'lga': 'campbelltown', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 5.5, 'value_max': None, 'unit': 'm',
        'condition': 'primary street, dwelling (not garage)',
        'applicability': 'universal_residential',
        'source_text': 's3.6.1.3(i): 5.5m from primary street boundary for the dwelling',
        'section_ref': 's3.6.1.3-i', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'primary street, garage',
        'applicability': 'universal_residential',
        'source_text': 's3.6.1.3(ii): 6.0m from primary street boundary for the garage',
        'section_ref': 's3.6.1.3-ii', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 2.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary street (corner allotment)',
        'applicability': 'universal_residential',
        'source_text': 's3.6.1.3(iii): 2m from secondary street boundary',
        'section_ref': 's3.6.1.3-iii', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'all side boundaries',
        'applicability': 'universal_residential',
        'source_text': 's3.6.1.3(v): 0.9m from any side boundary',
        'section_ref': 's3.6.1.3-v', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'part of building ≤4.5m height from existing ground level',
        'applicability': 'universal_residential',
        'source_text': 's3.6.1.3(vi): 3m from rear boundary for parts ≤4.5m height',
        'section_ref': 's3.6.1.3-vi', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 8.0, 'value_max': None, 'unit': 'm',
        'condition': 'part of building >4.5m height from existing ground level',
        'applicability': 'universal_residential',
        'source_text': 's3.6.1.3(vii): 8m from rear boundary for parts >4.5m height',
        'section_ref': 's3.6.1.3-vii', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    # SD setbacks
    {
        'lga': 'campbelltown', 'dev_type': 'secondary_dwelling', 'control_type': 'front_setback',
        'value_min': 5.5, 'value_max': None, 'unit': 'm',
        'condition': 'primary street; must align with existing or predominant front building line',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's3.6.2.2(i): 5.5m from primary street, align with existing front building line',
        'section_ref': 's3.6.2.2-i', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'secondary_dwelling', 'control_type': 'front_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary/corner street',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's3.6.2.2(ii): 3m from secondary street boundary',
        'section_ref': 's3.6.2.2-ii', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'secondary_dwelling', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'all side boundaries',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's3.6.2.2(iii): 0.9m from any side boundary',
        'section_ref': 's3.6.2.2-iii', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'secondary_dwelling', 'control_type': 'rear_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'part of building ≤3.8m height from existing ground level',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's3.6.2.2(iv): 3m from rear boundary for parts ≤3.8m height',
        'section_ref': 's3.6.2.2-iv', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'campbelltown', 'dev_type': 'secondary_dwelling', 'control_type': 'rear_setback',
        'value_min': 8.0, 'value_max': None, 'unit': 'm',
        'condition': 'part of building >3.8m height from existing ground level',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's3.6.2.2(v): 8m from rear boundary for parts >3.8m height',
        'section_ref': 's3.6.2.2-v', 'dcp_version': 'v2015-2024',
        'is_current': True, 'extraction_method': 'manual',
    },

    # ════════════════════════════════════════════════════════════════
    # LIVERPOOL — Liverpool DCP 2008, Part 8 (Dwelling Houses)
    # Table 3 (s2.1): applies to DH on lots 300–900m², R1/R2/R3
    # Part 8 does not cover secondary dwellings — SD governed by SEPP H2021
    # ════════════════════════════════════════════════════════════════
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 4.5, 'value_max': None, 'unit': 'm',
        'condition': 'ground floor and balcony (standard local road)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Front setback ground floor/balcony minimum 4.5m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 5.5, 'value_max': None, 'unit': 'm',
        'condition': 'attached garage',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Attached garage front setback minimum 5.5m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 7.0, 'value_max': None, 'unit': 'm',
        'condition': 'classified road frontage',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Classified road front setback minimum 7.0m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 2.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary street (corner allotment)',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Secondary street setback minimum 2.0m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'ground floor, all lots',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Side setback ground floor minimum 0.9m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 1.2, 'value_max': None, 'unit': 'm',
        'condition': 'first floor, lots >450m²',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Side setback first floor >450m² lots = 1.2m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 4.0, 'value_max': None, 'unit': 'm',
        'condition': 'ground floor',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Rear setback ground floor minimum 4.0m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'liverpool', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'first floor',
        'applicability': 'universal_residential',
        'source_text': 'Table 3: Rear setback first floor minimum 6.0m',
        'section_ref': 's2.1-table3', 'dcp_version': 'v2008',
        'is_current': True, 'extraction_method': 'manual',
    },

    # ════════════════════════════════════════════════════════════════
    # BLACKTOWN — Blacktown DCP 2015, Part C
    # s3.11 checklist DH; s4.3.5/4.3.6 dual occupancy + secondary dwelling
    # ════════════════════════════════════════════════════════════════
    # DH setbacks (s3.11 checklist / s3.2.3, s3.2.4)
    {
        'lga': 'blacktown', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'primary street (standard)',
        'applicability': 'universal_residential',
        'source_text': 's3.2.3: Building line dwelling minimum 6m from primary street',
        'section_ref': 's3.2.3', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'dwelling_house', 'control_type': 'front_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary road (corner allotment)',
        'applicability': 'universal_residential',
        'source_text': 's3.4.1: Setback to secondary road minimum 3m on corner lots',
        'section_ref': 's3.4.1', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'ground and upper storey, ≤2 storeys',
        'applicability': 'universal_residential',
        'source_text': 's3.2.4: Side and rear ground/upper storey setback ≤2 storeys = 0.9m',
        'section_ref': 's3.2.4', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'upper storey rear, ≤2 storeys',
        'applicability': 'universal_residential',
        'source_text': 's3.2.4: Upper storey rear setback ≤2 storeys = 3m',
        'section_ref': 's3.2.4', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'dwelling_house', 'control_type': 'side_setback',
        'value_min': 1.5, 'value_max': None, 'unit': 'm',
        'condition': 'ground and upper storey, >2 storeys',
        'applicability': 'universal_residential',
        'source_text': 's3.2.5: Side and rear setback >2 storeys = 1.5m',
        'section_ref': 's3.2.5', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'dwelling_house', 'control_type': 'rear_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'upper storey rear, >2 storeys',
        'applicability': 'universal_residential',
        'source_text': 's3.2.5: Upper storey rear setback >2 storeys = 3m',
        'section_ref': 's3.2.5', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    # SD setbacks (s4.3.5/4.3.6)
    {
        'lga': 'blacktown', 'dev_type': 'secondary_dwelling', 'control_type': 'front_setback',
        'value_min': 6.0, 'value_max': None, 'unit': 'm',
        'condition': 'primary street (standard); Stanhope Gardens exception: 4.5m',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's4.3.5: Secondary dwelling building setback from street 6m (Stanhope 4.5m)',
        'section_ref': 's4.3.5', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'secondary_dwelling', 'control_type': 'front_setback',
        'value_min': 3.0, 'value_max': None, 'unit': 'm',
        'condition': 'secondary street (corner allotment)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's4.3.5: Secondary building setback for corner allotment secondary dwelling = 3m',
        'section_ref': 's4.3.5', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'secondary_dwelling', 'control_type': 'side_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'all side boundaries (general case)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's4.3.6: Walls minimum 900mm from side and rear boundaries',
        'section_ref': 's4.3.6', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
    {
        'lga': 'blacktown', 'dev_type': 'secondary_dwelling', 'control_type': 'rear_setback',
        'value_min': 0.9, 'value_max': None, 'unit': 'm',
        'condition': 'rear boundary (general case)',
        'applicability': 'secondary_dwelling_specific',
        'source_text': 's4.3.6: Walls minimum 900mm from side and rear boundaries',
        'section_ref': 's4.3.6', 'dcp_version': 'v2015',
        'is_current': True, 'extraction_method': 'manual',
    },
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

print(f"\nInserting {len(rows)} rows...")
inserted = 0
for row in rows:
    cur.execute(INSERT_SQL, row)
    row_id = cur.fetchone()[0]
    print(f"  [{row_id:3d}] {row['lga']:20} {row['dev_type']:20} {row['control_type']:18} "
          f"min={str(row.get('value_min') or ''):>5} max={str(row.get('value_max') or ''):>5} {row['unit']}")
    inserted += 1

conn.commit()
print(f"\nDone. Inserted {inserted} rows.")

# Summary by LGA
print("\n── Summary by LGA ──")
cur.execute("""
    SELECT lga, dev_type, count(*) as n
    FROM dcp_setback_controls
    WHERE lga = ANY(%s) AND is_current = TRUE
    GROUP BY lga, dev_type
    ORDER BY lga, dev_type
""", (TARGET_LGAS,))
for r in cur.fetchall():
    print(f"  {r[0]:20} {r[1]:22} {r[2]} rows")

conn.close()
