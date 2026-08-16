"""
Marrickville DCP 2011 - Parking controls extraction
Source: Table 1 Onsite car parking requirements (Section 2.10 Parking, pages 8-10)
DCP: Marrickville DCP 2011
Note: Marrickville uses 3 Parking Areas (zones) - Area 1 (lowest), Area 2 (mid), Area 3 (highest rate)
"""
import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Marrickville DCP 2011"
CHAPTER_KEY = "part2-s10-parking"

rows = [
    # Dwelling house - 1 per dwelling in all areas
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "dwelling_house",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "including attached, semi-detached and secondary dwellings combined",
        "applicability": "universal_residential",
        "source_text": "Dwelling houses (incl. attached, semi-detached and secondary dwellings) 1 per dwelling house or 1 per principal dwelling and secondary dwelling combined",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Secondary dwelling - combined with principal
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "secondary_dwelling",
        "value_min": 0,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "combined with principal dwelling; no additional spaces required",
        "applicability": "universal_residential",
        "source_text": "1 per principal dwelling and secondary dwelling combined",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Boarding house
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "boarding_house",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/room",
        "condition": "plus 1 space per resident employee",
        "applicability": "universal_residential",
        "source_text": "Boarding houses: 1 parking space per resident employee and 0.5 parking spaces per boarding room",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - studio - Area 1
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; Parking Area 1; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs and shoptop housing with 7 or more units non-adaptable: 0.2 per studio for residents (Parking Area 1)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - studio - Area 2
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.4,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; Parking Area 2; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 0.4 per studio for residents (Parking Area 2)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - studio - Area 3
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.6,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; Parking Area 3; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 0.6 per studio for residents (Parking Area 3)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 1br - Area 1
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.4,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; Parking Area 1; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 0.4 per 1br unit for residents (Parking Area 1)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 1br - Area 2
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; Parking Area 2; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 0.5 per 1br unit for residents (Parking Area 2)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 1br - Area 3
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.8,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; Parking Area 3; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 0.8 per 1br unit for residents (Parking Area 3)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 2br - Area 1
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.8,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedroom; Parking Area 1; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 0.8 per 2br unit for residents (Parking Area 1)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 2br - Area 2
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1.0,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedroom; Parking Area 2; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 1.0 per 2br unit for residents (Parking Area 2)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 2br - Area 3
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedroom; Parking Area 3; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 1.2 per 2br unit for residents (Parking Area 3)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 3+br - Area 1
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1.1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3+ bedroom; Parking Area 1; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 1.1 per 3+br unit for residents (Parking Area 1)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 3+br - Area 2
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3+ bedroom; Parking Area 2; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 1.2 per 3+br unit for residents (Parking Area 2)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - 3+br - Area 3
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3+ bedroom; Parking Area 3; 7+ units non-adaptable",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units non-adaptable: 1.2 per 3+br unit for residents (Parking Area 3)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # RFB 7+ units - visitor parking Area 2/3
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "visitor parking; Parking Area 2 and 3; 7+ units",
        "applicability": "zone_specific",
        "source_text": "All RFBs 7+ units: 0.1 per unit for visitors (Parking Area 2 and 3)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Shoptop housing 6 or less - studio/1br - Area 1
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "shop_top_housing",
        "value_min": 0.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio or 1br; Parking Area 1; 6 or less units",
        "applicability": "zone_specific",
        "source_text": "Shoptop housing 6 or less units: 0.2 per studio or 1br unit for residents (Parking Area 1)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Shoptop housing 6 or less - 2+br - Area 1
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "shop_top_housing",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 or 3+ bedroom; Parking Area 1; 6 or less units",
        "applicability": "zone_specific",
        "source_text": "Shoptop housing 6 or less units: 0.5 per 2 or 3+br unit for residents (Parking Area 1)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Seniors housing - Area 1
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "seniors_housing",
        "value_min": 0.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "Parking Area 1; plus 1 per 5 units for visitors and carers",
        "applicability": "zone_specific",
        "source_text": "Seniors housing: 0.2 per unit for residents + 1 per 5 units for visitors and carers (Parking Area 1)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Seniors housing - Area 2
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "seniors_housing",
        "value_min": 0.33,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "Parking Area 2; plus 0.33 per unit for visitors and carers",
        "applicability": "zone_specific",
        "source_text": "Seniors housing: 0.33 per unit for residents + 0.33 per unit for visitors and carers (Parking Area 2)",
        "section_ref": "Table 1",
        "pdf_page": 8,
        "dcp_version": DCP_VERSION,
        "source_chapter_key": CHAPTER_KEY,
    },
    # Seniors housing - Area 3
    {
        "lga": "marrickville",
        "control_type": "car_parking",
        "dev_type": "seniors_housing",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "Parking Area 3; plus 0.33 per unit for visitors and carers",
        "applicability": "zone_specific",
        "source_text": "Seniors housing: 0.5 per unit for residents + 0.33 per unit for visitors and carers (Parking Area 3)",
        "section_ref": "Table 1",
        "pdf_page": 8,
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

print(f"Inserted {inserted} Marrickville parking rows")

# Verify
cur.execute("""
SELECT control_type, dev_type, value_min, unit, pdf_page
FROM dcp_setback_controls
WHERE lga = 'marrickville' AND control_type = 'car_parking'
ORDER BY id
""")
print(f"\nVerification ({cur.rowcount} rows):")
for r in cur.fetchall():
    print(f"  {str(r[1]):30s} min={r[2]} unit={r[3]} p{r[4]}")

conn.close()
