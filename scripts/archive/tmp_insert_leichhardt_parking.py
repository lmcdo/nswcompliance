"""
Leichhardt DCP 2013 — Parking controls extraction
Source: Table C4 General Vehicle Parking Rates (Part C1.11 Parking, pages 64-66)
DCP: Leichhardt DCP 2013
"""
import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Leichhardt DCP 2013"
CHAPTER_KEY = "part-c-s1-general"

rows = [
    # Single dwelling house — 2 spaces max, nil min
    {
        "lga": "leichhardt",
        "control_type": "car_parking",
        "dev_type": "dwelling_house",
        "value_min": None,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Single dwelling house: Minimum Nil, Maximum 2 spaces per dwelling house",
        "section_ref": "Table C4",
        "pdf_page": 64,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Bed-sit/Studio — resident min nil, max 0.5
    {
        "lga": "leichhardt",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "bed-sit or studio",
        "applicability": "universal_residential",
        "source_text": "Bed-sit / Studio: Residents Minimum Nil, Maximum 0.5 space per dwelling; Visitors 1 space per 11 dwellings",
        "section_ref": "Table C4",
        "pdf_page": 64,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # 1-bedroom — resident min 0.33, max 0.5
    {
        "lga": "leichhardt",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.33,
        "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 bedroom unit: Residents Minimum 1 space per 3 dwellings, Maximum 0.5 space per dwelling",
        "section_ref": "Table C4",
        "pdf_page": 64,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # 2-bedroom — resident min 0.5, max 1
    {
        "lga": "leichhardt",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.5,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "2 bedroom",
        "applicability": "universal_residential",
        "source_text": "2 bedroom unit: Residents Minimum 1 space per 2 dwellings, Maximum 1 space per dwelling",
        "section_ref": "Table C4",
        "pdf_page": 64,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # 3+ bedroom — resident min 1, max 1.2
    {
        "lga": "leichhardt",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "value_max": 1.2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "3+ bedrooms unit: Residents Minimum 1 space per dwelling, Maximum 1.2 spaces per dwelling",
        "section_ref": "Table C4",
        "pdf_page": 64,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Visitor parking for all residential units
    {
        "lga": "leichhardt",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.091,
        "value_max": 0.125,
        "unit": "spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "Visitors: Minimum 1 space per 11 dwellings, Maximum 0.125 spaces per dwelling",
        "section_ref": "Table C4",
        "pdf_page": 64,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Boarding house — 0.5 per room + 1 per resident employee
    {
        "lga": "leichhardt",
        "control_type": "car_parking",
        "dev_type": "boarding_house",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/room",
        "condition": "plus 1 space per resident employee",
        "applicability": "universal_residential",
        "source_text": "Boarding Houses: 1 space per resident employee and 0.5 space per boarding room",
        "section_ref": "Table C4",
        "pdf_page": 64,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Bicycle parking — RFB (from Table C6, page 68)
    {
        "lga": "leichhardt",
        "control_type": "bicycle_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "residents/staff; 1 space per 10 dwellings for visitors",
        "applicability": "universal_residential",
        "source_text": "Apartments 1 space per dwelling for residents; 1 per 10 dwellings for visitors",
        "section_ref": "Table C6",
        "pdf_page": 68,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
]

cols = list(rows[0].keys())
placeholders = ", ".join(["%s"] * len(cols))
col_str = ", ".join(cols)

inserted = 0
for row in rows:
    vals = [row[c] for c in cols]
    cur.execute(f"""
    INSERT INTO dcp_setback_controls ({col_str}, is_current, needs_review, extraction_method)
    VALUES ({placeholders}, true, false, 'text_extraction')
    """, vals)
    inserted += 1

print(f"Inserted {inserted} Leichhardt parking rows")

# Verify
cur.execute("""
SELECT control_type, dev_type, value_min, value_max, unit, section_ref, pdf_page
FROM dcp_setback_controls
WHERE lga = 'leichhardt' AND control_type IN ('car_parking', 'bicycle_parking')
ORDER BY id
""")
print("\nVerification:")
for r in cur.fetchall():
    print(f"  {r[0]:16s} {str(r[1]):30s} min={r[2]} max={r[3]} unit={r[4]} ref={r[5]} p{r[6]}")

conn.close()
