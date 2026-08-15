"""
Georges River DCP 2021 - Setback controls extraction
Source: Part 6.1 Low Density Residential Controls (Amendment 6, 10 June 2024)
Section 6.1.2.3 Setbacks (pages 5-8), Section 6.1.3.3 Setbacks (pages 17-23)
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Georges River DCP 2021 Amendment 6 (June 2024)"
CHAPTER_KEY = "grdcp-part-6-1-low-density"

# First register the chapter
cur.execute("""
INSERT INTO dcp_chapter_registry (council, dcp_name, doc_type, chapter_key, chapter_label, sort_order,
    council_url, is_active, needs_extraction, created_at, updated_at, registration_status)
VALUES ('georges_river', 'Georges River DCP 2021', 'dcp', %s,
    'Part 6.1 Low Density Residential Controls', 10,
    'https://www.georgesriver.nsw.gov.au/Development/Planning-Controls/Development-Control-Plans',
    true, false, NOW(), NOW(), 'confirmed')
ON CONFLICT DO NOTHING
""", (CHAPTER_KEY,))
print(f"Chapter registered: {CHAPTER_KEY}")

rows = [
    # === SINGLE DWELLINGS ===
    # Front setback 4.5m
    {
        "lga": "georges_river", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 4.5, "value_max": None, "unit": "m",
        "condition": "to main building wall/facade",
        "applicability": "universal_residential",
        "source_text": "The minimum setback from the primary street boundary is: 4.5m to the main building wall / facade",
        "section_ref": "6.1.2.3 Control 1(i)", "pdf_page": 5,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Front setback 5.5m to garage
    {
        "lga": "georges_river", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 5.5, "value_max": None, "unit": "m",
        "condition": "to front facade of garage or carport; or 1m behind main wall whichever is greater",
        "applicability": "universal_residential",
        "source_text": "5.5m to the front facade of a garage or carport, or at least 1m behind the main building wall / facade, whichever is the greater",
        "section_ref": "6.1.2.3 Control 1(ii)", "pdf_page": 5,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Secondary street setback - lot <15m: 1.2m
    {
        "lga": "georges_river", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 1.2, "value_max": None, "unit": "m",
        "condition": "corner lot; secondary street; site less than 15m in width",
        "applicability": "universal_residential",
        "source_text": "For corner lots, the setback from the secondary street boundary is to be at least: 1.2m to the building line if the site is less than 15m in width",
        "section_ref": "6.1.2.3 Control 3(i)", "pdf_page": 5,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Secondary street setback - lot >=15m: 2.0m
    {
        "lga": "georges_river", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 2.0, "value_max": None, "unit": "m",
        "condition": "corner lot; secondary street; site 15m or greater in width",
        "applicability": "universal_residential",
        "source_text": "For corner lots, the setback from the secondary street boundary is to be at least: 2.0m to the building line if the site is 15m or greater in width",
        "section_ref": "6.1.2.3 Control 3(ii)", "pdf_page": 5,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Rear setback 15% or 6m
    {
        "lga": "georges_river", "control_type": "rear_setback", "dev_type": "dwelling_house",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "15% of average site length or 6m whichever is greater",
        "applicability": "universal_residential",
        "source_text": "Buildings are to have a minimum rear setback of 15% of the average site length, or 6m, whichever is the greater",
        "section_ref": "6.1.2.3 Control 4", "pdf_page": 6,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Side setback - lot <=12.5m: 0.9m
    {
        "lga": "georges_river", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": "lots up to 12.5m in width; ground and first floor",
        "applicability": "universal_residential",
        "source_text": "Minimum side setbacks: 900mm for lots up to 12.5m in width measured at the front building line for the length of the development",
        "section_ref": "6.1.2.3 Control 5(i)", "pdf_page": 6,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Side setback - lot >12.5m: 1.2m
    {
        "lga": "georges_river", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.2, "value_max": None, "unit": "m",
        "condition": "lots greater than 12.5m in width; ground and first floor",
        "applicability": "universal_residential",
        "source_text": "Minimum side setbacks: 1.2m for lots greater than 12.5m in width measured at the front building line for the length of the development",
        "section_ref": "6.1.2.3 Control 5(ii)", "pdf_page": 6,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Side setback - Foreshore: 1.5m
    {
        "lga": "georges_river", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "Foreshore Scenic Protection Area; ground and first floor",
        "applicability": "zone_specific",
        "source_text": "1.5m for all lots within the Foreshore Scenic Protection Area measured at the front building line",
        "section_ref": "6.1.2.3 Control 5(iii)", "pdf_page": 6,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Secondary dwelling - side/rear 1.5m
    {
        "lga": "georges_river", "control_type": "side_setback", "dev_type": "secondary_dwelling",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "side and rear boundaries; excluding laneways where nil setback permitted",
        "applicability": "universal_residential",
        "source_text": "The minimum setback to side and rear boundaries is 1500mm, (excluding laneways where a nil setback is permitted)",
        "section_ref": "6.1.2.12 Control 6", "pdf_page": 14,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },

    # === DUAL OCCUPANCY ===
    # Front setback 4.5m
    {
        "lga": "georges_river", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 4.5, "value_max": None, "unit": "m",
        "condition": "to main building wall/facade; primary street",
        "applicability": "universal_residential",
        "source_text": "Minimum setback from the primary street boundary for ground and first floor: 4.5m to the main building wall / facade",
        "section_ref": "6.1.3.3 Control 1", "pdf_page": 18,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Side setback dual occ side-by-side 1.2m
    {
        "lga": "georges_river", "control_type": "side_setback", "dev_type": "dual_occupancy",
        "value_min": 1.2, "value_max": None, "unit": "m",
        "condition": "detached side-by-side; external side boundaries and internal allotment boundary; outside Foreshore area",
        "applicability": "universal_residential",
        "source_text": "Minimum side setback (ground and first floor) to external side boundaries and internal allotment boundary is to be minimum 1.2m",
        "section_ref": "6.1.3.3 Control 3", "pdf_page": 18,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Rear setback dual occ side-by-side: 6m or 15%
    {
        "lga": "georges_river", "control_type": "rear_setback", "dev_type": "dual_occupancy",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "side-by-side; 15% of average site length or 6m whichever is greater",
        "applicability": "universal_residential",
        "source_text": "Each dwelling is to have minimum rear setback (ground and first floor) of 15% of the average site length, or 6.0m, whichever is greater",
        "section_ref": "6.1.3.3 Control 4", "pdf_page": 19,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # Secondary street setback 3m
    {
        "lga": "georges_river", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 3, "value_max": None, "unit": "m",
        "condition": "corner site; secondary street; ground and first floor",
        "applicability": "universal_residential",
        "source_text": "The minimum setback (ground and first floor) to a secondary street is 3m",
        "section_ref": "6.1.3.3 Control 9", "pdf_page": 21,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
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

print(f"Inserted {inserted} Georges River setback rows")

# Verify
cur.execute("""
SELECT control_type, dev_type, value_min, unit, LEFT(condition, 55), pdf_page
FROM dcp_setback_controls
WHERE lga = 'georges_river' AND control_type IN ('front_setback','side_setback','rear_setback')
ORDER BY control_type, dev_type, id
""")
print(f"\nVerification ({cur.rowcount} rows):")
for r in cur.fetchall():
    print(f"  {str(r[0]):16s} {str(r[1]):20s} min={r[2]} {r[3]} p{r[5]} {r[4]}")

conn.close()
