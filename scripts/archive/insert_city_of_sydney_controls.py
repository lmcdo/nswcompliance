"""Insert City of Sydney DCP 2012 structured controls into dcp_setback_controls.

Source: Sydney DCP 2012
- Section 3: General Provisions (amended 28 Jan 2026)
- Section 4: Development Types (amended Dec 2022)

Key findings:
- Setbacks are MAP-BASED (Building Setback and Alignment Map) — no universal numeric
- Car parking maximum rates are in Sydney LEP 2012, not DCP
- Deep soil, private open space, common open space have clear numerics
- Bike parking rates from Table 3.5
"""
import os
import psycopg2
from dotenv import load_dotenv
from datetime import date

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL'))
cur = conn.cursor()

controls = [
    # --- SETBACKS (map-based — explanation rows) ---
    {
        'dev_type': 'dwelling_house',
        'control_type': 'front_setback',
        'value_min': None, 'value_max': None, 'unit': None,
        'condition': 'Map-based: refer to Building Setbacks Map in Sydney LEP/DCP',
        'source_text': 'Front setbacks are to be consistent with the Building setbacks map. Where no front setback is shown on the map, the front setback is to be consistent with the predominant setting in the street.',
        'section_ref': '4.1.2(1)', 'pdf_page': 6,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'dwelling_house',
        'control_type': 'side_setback',
        'value_min': None, 'value_max': None, 'unit': None,
        'condition': 'Map-based + character: relate to established development pattern',
        'source_text': 'Within heritage conservation areas, new development is to relate to the established development pattern including the subdivision pattern, front, side and rear setbacks.',
        'section_ref': '4.1.2(2)', 'pdf_page': 6,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'dwelling_house',
        'control_type': 'rear_setback',
        'value_min': None, 'value_max': None, 'unit': None,
        'condition': 'Character-based: must respect predominant rear building line',
        'source_text': 'New development and alterations and additions must respect and be sympathetic to the predominant rear building line.',
        'section_ref': '4.1.2(4)', 'pdf_page': 7,
        'chapter': 'section-4-development-types',
    },
    # Multi-dwelling setbacks
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'front_setback',
        'value_min': None, 'value_max': None, 'unit': None,
        'condition': 'Map-based: refer to Building Setback and Alignment Map',
        'source_text': 'Setbacks are to be consistent with the setbacks shown in the Building setback and alignment map. Where no setback or alignment is shown on the map, the setback and alignment must be consistent with adjoining buildings.',
        'section_ref': '4.2.2.1(1)', 'pdf_page': 27,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'rear_setback',
        'value_min': None, 'value_max': None, 'unit': None,
        'condition': 'Character-based: consistent with adjoining buildings',
        'source_text': 'The rear setback and alignment is to be consistent with adjoining buildings. When the setback or alignment varies, either the adjacent or average rear setback or alignment is to be adopted.',
        'section_ref': '4.2.2.1(3)', 'pdf_page': 27,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'front_setback',
        'value_min': 3, 'value_max': None, 'unit': 'm',
        'condition': 'Above street frontage height only (upper level setback)',
        'source_text': 'A setback above the street frontage height is to be a minimum of 3m for residential above non-residential and for residential above residential.',
        'section_ref': '4.2.2.2(2)', 'pdf_page': 27,
        'chapter': 'section-4-development-types',
    },

    # --- DEEP SOIL ---
    {
        'dev_type': 'dwelling_house',
        'control_type': 'deep_soil_min',
        'value_min': 15, 'value_max': None, 'unit': '%',
        'condition': 'Lots greater than 150sqm',
        'source_text': 'For lots greater than 150sqm, the minimum amount of deep soil is to be 15% of the site area.',
        'section_ref': '4.1.3.4(1)', 'pdf_page': 9,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'deep_soil_min',
        'value_min': 10, 'value_max': None, 'unit': '%',
        'condition': 'Does not apply in Central Sydney; lots >1000sqm must consolidate with min 10m dimension',
        'source_text': 'The minimum amount of deep soil is to be 10% of the site area.',
        'section_ref': '4.2.3.6(1)', 'pdf_page': 29,
        'chapter': 'section-4-development-types',
    },

    # --- PRIVATE OPEN SPACE ---
    {
        'dev_type': 'dwelling_house',
        'control_type': 'communal_open_space_min',
        'value_min': 16, 'value_max': None, 'unit': 'm2',
        'condition': 'Minimum dimension 3m; directly accessible from living area',
        'source_text': 'Private open space at the ground level is to have a minimum area of 16sqm and minimum dimension of 3m.',
        'section_ref': '4.1.3.5(1)', 'pdf_page': 9,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'communal_open_space_min',
        'value_min': 25, 'value_max': None, 'unit': 'm2',
        'condition': 'Ground level dwellings; minimum dimension 4m',
        'source_text': 'Private open space: ground level dwellings: 25sqm with a minimum dimension of 4m.',
        'section_ref': '4.2.3.7(6)(a)', 'pdf_page': 30,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'residential_flat_building',
        'control_type': 'communal_open_space_min',
        'value_min': 10, 'value_max': None, 'unit': 'm2',
        'condition': 'Upper level units; minimum dimension 2m (balcony)',
        'source_text': 'Private open space: upper level units: 10sqm with a minimum dimension of 2m.',
        'section_ref': '4.2.3.7(6)(b)', 'pdf_page': 30,
        'chapter': 'section-4-development-types',
    },

    # --- COMMON OPEN SPACE / LANDSCAPING (multi-dwelling) ---
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'landscaping_min',
        'value_min': 25, 'value_max': None, 'unit': '%',
        'condition': 'Common open space under common title; min dimension 6m; excludes driveways/parking/fire escapes',
        'source_text': 'Provide an area of common open space under common title that is at least 25% of the total site area and has a minimum dimension of 6m.',
        'section_ref': '4.2.3.8(1)', 'pdf_page': 30,
        'chapter': 'section-4-development-types',
    },

    # --- BIKE PARKING ---
    {
        'dev_type': 'dwelling_house',
        'control_type': 'bicycle_parking',
        'value_min': 1, 'value_max': None, 'unit': 'spaces/dwelling',
        'condition': 'Resident parking; plus 1 per 10 dwellings visitor',
        'source_text': 'Residential accommodation: 1 per dwelling (residents/employees), 1 per 10 dwellings (customer/visitors).',
        'section_ref': '3.11.3 Table 3.5', 'pdf_page': None,
        'chapter': 'section-3-general-provisions',
    },
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'bicycle_parking',
        'value_min': 1, 'value_max': None, 'unit': 'spaces/dwelling',
        'condition': 'Resident parking; plus 1 per 10 dwellings visitor',
        'source_text': 'Residential accommodation: 1 per dwelling (residents/employees), 1 per 10 dwellings (customer/visitors).',
        'section_ref': '3.11.3 Table 3.5', 'pdf_page': None,
        'chapter': 'section-3-general-provisions',
    },
    {
        'dev_type': 'residential_flat_building',
        'control_type': 'bicycle_parking',
        'value_min': 1, 'value_max': None, 'unit': 'spaces/dwelling',
        'condition': 'Resident parking; plus 1 per 10 dwellings visitor',
        'source_text': 'Residential accommodation: 1 per dwelling (residents/employees), 1 per 10 dwellings (customer/visitors).',
        'section_ref': '3.11.3 Table 3.5', 'pdf_page': None,
        'chapter': 'section-3-general-provisions',
    },

    # --- CAR PARKING (LEP sets max rates, DCP has design controls) ---
    {
        'dev_type': 'dwelling_house',
        'control_type': 'car_parking',
        'value_min': None, 'value_max': None, 'unit': None,
        'condition': 'Maximum rates set by Sydney LEP 2012 Part 7 Div 1 (not DCP); max driveway width 2.7m',
        'source_text': 'Sydney LEP 2012 identifies the maximum number of car spaces permitted for dwelling houses, attached dwellings and semi-detached dwellings. The maximum width of a driveway is 2.7m.',
        'section_ref': '4.1.9(1)', 'pdf_page': 24,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'multi_dwelling',
        'control_type': 'car_parking',
        'value_min': None, 'value_max': None, 'unit': None,
        'condition': 'Maximum rates set by Sydney LEP 2012 Part 7 Div 1 (LUTI categories A/B/C)',
        'source_text': 'Applicants are to refer to Sydney LEP 2012 for maximum on-site car parking rates and for the associated Land Use and Transport Integration (LUTI) and Public Transport Accessibility Level (PTAL) Maps.',
        'section_ref': '3.11.1', 'pdf_page': None,
        'chapter': 'section-3-general-provisions',
    },

    # --- SECONDARY DWELLING ---
    {
        'dev_type': 'secondary_dwelling',
        'control_type': 'max_height',
        'value_min': None, 'value_max': 5.4, 'unit': 'm',
        'condition': 'One storey with attic; adjacent to rear lane; roof pitch max 40 degrees',
        'source_text': 'A one storey structure with an attic above is permissible adjacent to a rear lane, provided the height does not exceed 5.4m and amenity to adjacent sites is maintained.',
        'section_ref': '4.1.6.1(1)', 'pdf_page': 20,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'secondary_dwelling',
        'control_type': 'deep_soil_min',
        'value_min': 15, 'value_max': None, 'unit': '%',
        'condition': 'Lots greater than 150sqm (same as dwelling_house)',
        'source_text': 'For lots greater than 150sqm, the minimum amount of deep soil is to be 15% of the site area.',
        'section_ref': '4.1.3.4(1)', 'pdf_page': 9,
        'chapter': 'section-4-development-types',
    },
    {
        'dev_type': 'secondary_dwelling',
        'control_type': 'communal_open_space_min',
        'value_min': 16, 'value_max': None, 'unit': 'm2',
        'condition': 'For principal dwelling; min dimension 3m; lots <150sqm not permitted unless achieved',
        'source_text': 'On lots smaller than 150sqm, a secondary dwelling is not permitted unless it can achieve a minimum consolidated area of private open space for the principal dwelling of 16sqm with a minimum dimension of 3m.',
        'section_ref': '4.1.6.1(2)', 'pdf_page': 20,
        'chapter': 'section-4-development-types',
    },
]

inserted = 0
for c in controls:
    cur.execute("""
        INSERT INTO dcp_setback_controls (
            lga, dev_type, control_type, value_min, value_max, unit,
            condition, source_text, section_ref, pdf_page,
            applicability, dcp_version, is_current, extraction_method,
            source_chapter_key, effective_date, last_verified_at
        ) VALUES (
            'city_of_sydney', %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            'universal_residential', 'Sydney DCP 2012 (amended Jan 2026)', TRUE, 'text_extraction',
            %s, %s, %s
        )
    """, (
        c['dev_type'], c['control_type'], c['value_min'], c['value_max'], c['unit'],
        c['condition'], c['source_text'], c['section_ref'], c.get('pdf_page'),
        c['chapter'],
        date(2026, 1, 28),
        date(2026, 5, 18),
    ))
    inserted += 1

conn.commit()
print(f"Inserted {inserted} rows for city_of_sydney")

# Verify
cur.execute("""
    SELECT control_type, dev_type, value_min, value_max, unit, LEFT(condition, 70)
    FROM dcp_setback_controls
    WHERE lga = 'city_of_sydney' AND is_current = TRUE
    ORDER BY dev_type, control_type
""")
print("\nVerification:")
for r in cur.fetchall():
    val = f"{r[2] or ''}-{r[3] or ''}" if r[2] or r[3] else "N/A"
    print(f"  {r[1]:30s} | {r[0]:25s} | {val:8s} {r[4] or ''} | {r[5]}")

conn.close()
