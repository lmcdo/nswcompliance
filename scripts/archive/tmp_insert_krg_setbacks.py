"""
Ku-ring-gai DCP - Setback controls extraction
Source: Section A Part 5 - Dual Occupancy (5A.3 Building Setbacks), pages 8-16
Also: Section A Part 4 - Dwelling Houses (4A.2 Building Setbacks, battle-axe), page 11
DCP: Ku-ring-gai Development Control Plan
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Ku-ring-gai Development Control Plan"
DH_CHAPTER = "section-a-part-4-dwelling-houses"
DO_CHAPTER = "section-a-part-5-dual-occupancy"

rows = [
    # === DUAL OCCUPANCY - Side-Side Layout ===
    {
        "lga": "ku_ring_gai", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 12, "value_max": None, "unit": "m",
        "condition": "side-side layout",
        "applicability": "universal_residential",
        "source_text": "The front setback at the building line for each dual occupancy dwelling is to be a minimum of 12m",
        "section_ref": "5A.3 Control 6", "pdf_page": 8,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "rear_setback", "dev_type": "dual_occupancy",
        "value_min": 12, "value_max": None, "unit": "m",
        "condition": "side-side layout",
        "applicability": "universal_residential",
        "source_text": "The rear setback for each dual occupancy dwelling is to be a minimum of 12m",
        "section_ref": "5A.3 Control 7", "pdf_page": 8,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "side_setback", "dev_type": "dual_occupancy",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "side-side layout; lot width <25m; single storey",
        "applicability": "universal_residential",
        "source_text": "Parent Lot width less than 25m: Minimum side setback single storey 1.5m",
        "section_ref": "5A.3 Control 8 Table", "pdf_page": 8,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "side_setback", "dev_type": "dual_occupancy",
        "value_min": 2, "value_max": None, "unit": "m",
        "condition": "side-side layout; lot width <25m; double storey",
        "applicability": "universal_residential",
        "source_text": "Parent Lot width less than 25m: Minimum side setback double storey 2m",
        "section_ref": "5A.3 Control 8 Table", "pdf_page": 8,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "side_setback", "dev_type": "dual_occupancy",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "side-side layout; lot width 25-36m; single storey",
        "applicability": "universal_residential",
        "source_text": "Parent Lot width 25-36m: Minimum side setback single storey 1.5m",
        "section_ref": "5A.3 Control 8 Table", "pdf_page": 8,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "side_setback", "dev_type": "dual_occupancy",
        "value_min": 2.5, "value_max": None, "unit": "m",
        "condition": "side-side layout; lot width 25-36m; double storey",
        "applicability": "universal_residential",
        "source_text": "Parent Lot width 25-36m: Minimum side setback double storey 2.5m",
        "section_ref": "5A.3 Control 8 Table", "pdf_page": 8,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },

    # === DUAL OCCUPANCY - Front-Back Layout ===
    {
        "lga": "ku_ring_gai", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 9, "value_max": None, "unit": "m",
        "condition": "front-back layout; low side of street",
        "applicability": "universal_residential",
        "source_text": "Front-Back Layout: Low Side minimum front setback 9m, average 11m",
        "section_ref": "5A.3 Control 12 Table", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 12, "value_max": None, "unit": "m",
        "condition": "front-back layout; high side of street",
        "applicability": "universal_residential",
        "source_text": "Front-Back Layout: High Side minimum front setback 12m, average 14m",
        "section_ref": "5A.3 Control 12 Table", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "rear_setback", "dev_type": "dual_occupancy",
        "value_min": 8, "value_max": None, "unit": "m",
        "condition": "front-back layout; lot depth 48m or less",
        "applicability": "universal_residential",
        "source_text": "Parent Lot depth 48m or less: Minimum required rear setback 8m",
        "section_ref": "5A.3 Control 14 Table", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "rear_setback", "dev_type": "dual_occupancy",
        "value_min": 12, "value_max": None, "unit": "m",
        "condition": "front-back layout; lot depth greater than 48m",
        "applicability": "universal_residential",
        "source_text": "Parent Lot depth greater than 48m: Minimum required rear setback 12m",
        "section_ref": "5A.3 Control 14 Table", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "side_setback", "dev_type": "dual_occupancy",
        "value_min": 1, "value_max": None, "unit": "m",
        "condition": "front-back layout; lot width <25m; single storey",
        "applicability": "universal_residential",
        "source_text": "Front-Back Layout: Lot width less than 25m: minimum side setback single storey 1m",
        "section_ref": "5A.3 Control 15 Table", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "side_setback", "dev_type": "dual_occupancy",
        "value_min": 2, "value_max": None, "unit": "m",
        "condition": "front-back layout; lot width <25m; double storey",
        "applicability": "universal_residential",
        "source_text": "Front-Back Layout: Lot width less than 25m: minimum side setback double storey 2m",
        "section_ref": "5A.3 Control 15 Table", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },

    # === CORNER LAYOUT ===
    {
        "lga": "ku_ring_gai", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 12, "value_max": None, "unit": "m",
        "condition": "corner layout; primary street frontage",
        "applicability": "universal_residential",
        "source_text": "Corner Layout: front setback at the building line for the dwelling facing the primary street frontage is to be 12m",
        "section_ref": "5A.3 Control 25", "pdf_page": 14,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "corner layout; secondary road frontage",
        "applicability": "universal_residential",
        "source_text": "Corner Layout: front setback for the dwelling facing the secondary road is to be a minimum of 6m",
        "section_ref": "5A.3 Control 26", "pdf_page": 14,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "rear_setback", "dev_type": "dual_occupancy",
        "value_min": 8, "value_max": None, "unit": "m",
        "condition": "corner layout; secondary street facing dwelling",
        "applicability": "universal_residential",
        "source_text": "Corner Layout: rear setback for dual occupancy facing the secondary street is to be 8m minimum",
        "section_ref": "5A.3 Control 27", "pdf_page": 14,
        "dcp_version": DCP_VERSION, "source_chapter_key": DO_CHAPTER,
    },

    # === DWELLING HOUSE - Battle-Axe Lots ===
    {
        "lga": "ku_ring_gai", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 3, "value_max": None, "unit": "m",
        "condition": "battle-axe lot; 15% of site width or 3m whichever is greater",
        "applicability": "development_specific",
        "source_text": "Battle-axe blocks: setbacks from the two long boundaries minimum of 15% of site width or 3m, whichever is the greater",
        "section_ref": "4A.2 Control 16(i)", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DH_CHAPTER,
    },
    {
        "lga": "ku_ring_gai", "control_type": "rear_setback", "dev_type": "dwelling_house",
        "value_min": 12, "value_max": None, "unit": "m",
        "condition": "battle-axe lot; lot depth greater than 48m",
        "applicability": "development_specific",
        "source_text": "Battle-axe blocks: setback from boundary excluding long boundaries minimum 12m for sites with depth greater than 48m",
        "section_ref": "4A.2 Control 16(ii)", "pdf_page": 11,
        "dcp_version": DCP_VERSION, "source_chapter_key": DH_CHAPTER,
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

print(f"Inserted {inserted} Ku-ring-gai setback rows")

# Verify
cur.execute("""
SELECT control_type, dev_type, value_min, unit, LEFT(condition, 55), pdf_page
FROM dcp_setback_controls
WHERE lga = 'ku_ring_gai' AND control_type IN ('front_setback','side_setback','rear_setback')
ORDER BY control_type, dev_type, id
""")
print(f"\nVerification ({cur.rowcount} rows):")
for r in cur.fetchall():
    print(f"  {str(r[0]):16s} {str(r[1]):20s} min={r[2]} {r[3]} p{r[5]} {r[4]}")

conn.close()
