"""
Ashfield DCP 2016 — Parking controls extraction
Source: Table 3 — Car Parking Rates (Part A8 Parking, pages 57-62)
Also: Part F3 Residential Flat Buildings (page 37) DS9.1, DS9.2
DCP: Comprehensive Inner West DCP 2016 (Ashfield area)
"""
import os, psycopg2, json

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Comprehensive Inner West DCP 2016 (Ashfield)"
CHAPTER_KEY = "chapter-a-miscellaneous"  # Part A8 Parking is within this chapter
RFB_CHAPTER_KEY = "chapter-f-dev-category"  # Part F3

rows = [
    # Dwelling house — Table 3 page 57
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "dwelling_house",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Dwelling House 1 space per dwelling (preferably 2)",
        "section_ref": "Table 3",
        "pdf_page": 57,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Boarding house — Table 3 page 57
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "boarding_house",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/room",
        "condition": "plus 1 space per resident employee",
        "applicability": "universal_residential",
        "source_text": "Boarding Houses 1 parking space per resident employee and 0.5 parking spaces per boarding room",
        "section_ref": "Table 3",
        "pdf_page": 57,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Multi-dwelling housing (R3 zone) — Table 3 page 57
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "multi_dwelling_housing",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "R3 zone; plus 1 space per 5 x 2-bedroom units; plus 1 space per 2 x 3-bedroom units",
        "applicability": "zone_specific",
        "source_text": "Multi-unit housing in R3 1 car space per unit plus 1 additional space for every five 2-bedroom units, plus 1 additional space for every two 3-bedroom units",
        "section_ref": "Table 3",
        "pdf_page": 57,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Multi-dwelling housing visitor parking — Table 3 page 57
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "multi_dwelling_housing",
        "value_min": 0.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "visitor parking; plus 1 car wash bay",
        "applicability": "universal_residential",
        "source_text": "1 visitor space required per 5 units plus 1 car wash bay",
        "section_ref": "Table 3",
        "pdf_page": 57,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB — DS9.1 page 37 — minimum 1 space per dwelling
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "B1, B2, B4 zones; or as per ADG whichever is lesser",
        "applicability": "zone_specific",
        "source_text": "DS9.1 On site carparking is provided as follows, whichever is the lesser: at a minimum of 1 space per dwelling or in accordance with the Apartment Design Guide",
        "section_ref": "DS9.1",
        "pdf_page": 37,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": RFB_CHAPTER_KEY,
    },
    # RFB visitor — DS9.2 page 37
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "visitor parking; plus 1 car wash bay",
        "applicability": "universal_residential",
        "source_text": "DS9.2 Parking for visitors is provided at the rate of 1 space for every 4 dwellings including serviced apartments plus 1 car wash bay",
        "section_ref": "DS9.2",
        "pdf_page": 37,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": RFB_CHAPTER_KEY,
    },
    # Youth hostel — Table 3 page 57
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "boarding_house",
        "value_min": 0.2,
        "value_max": None,
        "unit": "spaces/occupant",
        "condition": "youth hostel/backpacker; plus 1 space for resident manager; plus 1 space per 2 employees",
        "applicability": "development_specific",
        "source_text": "Youth Hostel/Backpacker Hostel 1 space for each 5 occupants/lodgers, plus 1 space for any resident manager, plus 1 space for each 2 employees",
        "section_ref": "Table 3",
        "pdf_page": 57,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Seniors housing — Table 3 page 57
    {
        "lga": "ashfield",
        "control_type": "car_parking",
        "dev_type": "seniors_housing",
        "value_min": 0.67,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "funded developments: 2 spaces per 3 self-contained units; plus 1 visitor space per 5 units",
        "applicability": "development_specific",
        "source_text": "Housing for Aged Persons Resident funded developments- 2 spaces per 3 self-contained units plus 1 visitor space for every 5 units",
        "section_ref": "Table 3",
        "pdf_page": 57,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
]

# Insert
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

print(f"Inserted {inserted} Ashfield parking rows")

# Verify
cur.execute("""
SELECT control_type, dev_type, value_min, unit, LEFT(source_text, 80)
FROM dcp_setback_controls
WHERE lga = 'ashfield' AND control_type = 'car_parking'
ORDER BY id
""")
print("\nVerification:")
for r in cur.fetchall():
    print(f"  {r[1]:30s} min={r[2]:6s} unit={r[3]:20s} src={r[4]}")

conn.close()
