"""
Waverley DCP 2022 + Parramatta DCP 2023 - Setback controls extraction
Waverley: C1.2 Setbacks (page 189), C2.3 Setbacks (page 223)
Parramatta: 3.3.1.2 Building Envelope (page 60), 3.4.1.2 Building Envelope (page 80)
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

rows = [
    # === WAVERLEY C1 LOW DENSITY ===
    # Side setback - ground/first floor 0.9m
    {
        "lga": "waverley", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": "ground floor and first floor",
        "applicability": "universal_residential",
        "source_text": "Comply with the minimum setbacks: Ground Floor 0.9m, First Floor 0.9m",
        "section_ref": "C1.2(a) Table 1", "pdf_page": 189,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },
    # Side setback - second floor 1.5m
    {
        "lga": "waverley", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "second floor",
        "applicability": "universal_residential",
        "source_text": "Comply with the minimum setbacks: Second Floor 1.5m",
        "section_ref": "C1.2(a) Table 1", "pdf_page": 189,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },
    # Side setback - new 3-storey 1.5m all floors
    {
        "lga": "waverley", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "new three storey structure; all floors must be setback 1.5m",
        "applicability": "universal_residential",
        "source_text": "Where a brand new three storey structure is proposed, all floors must be setback by 1.5m",
        "section_ref": "C1.2(f)", "pdf_page": 190,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },

    # === WAVERLEY C2 OTHER RESIDENTIAL ===
    # Rear setback 6m
    {
        "lga": "waverley", "control_type": "rear_setback", "dev_type": "residential_flat_building",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "or predominant rear building line whichever is greater",
        "applicability": "universal_residential",
        "source_text": "New buildings are to provide a minimum 6m rear setback, or extend no further to the rear than the predominant rear building line, whichever is the greater setback",
        "section_ref": "C2.3(a)", "pdf_page": 223,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },
    # Side setback - up to 4.5m height: 0.9m
    {
        "lga": "waverley", "control_type": "side_setback", "dev_type": "residential_flat_building",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": "building height up to 4.5m",
        "applicability": "universal_residential",
        "source_text": "Height up to 4.5m: Side setback to whole building (min.) 0.9m",
        "section_ref": "C2.3(b) Table 3", "pdf_page": 223,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },
    # Side setback - up to 12.5m height: 1.5m
    {
        "lga": "waverley", "control_type": "side_setback", "dev_type": "residential_flat_building",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "building height up to 12.5m",
        "applicability": "universal_residential",
        "source_text": "Height up to 12.5m: Side setback to whole building (min.) 1.5m",
        "section_ref": "C2.3(b) Table 3", "pdf_page": 223,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },
    # Side setback - above 12.5m: 1.5-2.5m
    {
        "lga": "waverley", "control_type": "side_setback", "dev_type": "residential_flat_building",
        "value_min": 1.5, "value_max": 2.5, "unit": "m",
        "condition": "building height above 12.5m",
        "applicability": "universal_residential",
        "source_text": "Height above 12.5m: Side setback to whole building (min.) 1.5 - 2.5m",
        "section_ref": "C2.3(b) Table 3", "pdf_page": 223,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },
    # Rear setback for multi-dwelling (same as RFB)
    {
        "lga": "waverley", "control_type": "rear_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "or predominant rear building line whichever is greater",
        "applicability": "universal_residential",
        "source_text": "New buildings are to provide a minimum 6m rear setback, or extend no further to the rear than the predominant rear building line, whichever is the greater setback",
        "section_ref": "C2.3(a)", "pdf_page": 223,
        "dcp_version": "Waverley DCP 2022 Amendment 5", "source_chapter_key": "waverley-dcp-2022",
    },

    # === PARRAMATTA DCP 2023 - DWELLING HOUSES ===
    # Front setback 6m
    {
        "lga": "parramatta", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "consistent with prevailing setback along the street",
        "applicability": "universal_residential",
        "source_text": "C.05 Buildings must be setback a minimum of 6 metres and be consistent with the prevailing setback along the street",
        "section_ref": "3.3.1.2 C.05", "pdf_page": 60,
        "dcp_version": "Parramatta DCP 2023 Amendment 4", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    # Secondary street setback 3m
    {
        "lga": "parramatta", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 3, "value_max": None, "unit": "m",
        "condition": "corner lot; secondary street setback",
        "applicability": "universal_residential",
        "source_text": "C.06 On corner lots, the secondary street setback must be a minimum of 3 metres",
        "section_ref": "3.3.1.2 C.06", "pdf_page": 60,
        "dcp_version": "Parramatta DCP 2023 Amendment 4", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    # State/regional road 10m
    {
        "lga": "parramatta", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 10, "value_max": None, "unit": "m",
        "condition": "state and regional roads",
        "applicability": "development_specific",
        "source_text": "C.07 Notwithstanding the above, the minimum setback to state and regional roads is 10 metres",
        "section_ref": "3.3.1.2 C.07", "pdf_page": 60,
        "dcp_version": "Parramatta DCP 2023 Amendment 4", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    # Side setback 900mm
    {
        "lga": "parramatta", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "C.08 Buildings must be setback a minimum of 900mm from side boundaries",
        "section_ref": "3.3.1.2 C.08", "pdf_page": 60,
        "dcp_version": "Parramatta DCP 2023 Amendment 4", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    # Rear setback 30% of site length
    {
        "lga": "parramatta", "control_type": "rear_setback", "dev_type": "dwelling_house",
        "value_min": 30, "value_max": None, "unit": "%",
        "condition": "of site length measured perpendicular to centre of rear boundary",
        "applicability": "universal_residential",
        "source_text": "C.10 A rear setback equal to 30% of the site length, as measured perpendicular to the centre of the rear boundary, must be provided",
        "section_ref": "3.3.1.2 C.10", "pdf_page": 60,
        "dcp_version": "Parramatta DCP 2023 Amendment 4", "source_chapter_key": "parramatta-dcp-2023-full",
    },

    # === PARRAMATTA - MULTI-DWELLING ===
    # Front setback 6m (4m minimum with character assessment)
    {
        "lga": "parramatta", "control_type": "front_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 4, "value_max": 6, "unit": "m",
        "condition": "6m required; lesser to 4m with local street character assessment",
        "applicability": "universal_residential",
        "source_text": "C.07 A minimum front setback of 6 metres is required however, a lesser front setback, to a minimum of 4 metres may be considered subject to a local street character assessment",
        "section_ref": "3.4.1.2 C.07", "pdf_page": 80,
        "dcp_version": "Parramatta DCP 2023 Amendment 4", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    # Secondary street 4m
    {
        "lga": "parramatta", "control_type": "front_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 4, "value_max": None, "unit": "m",
        "condition": "corner lot; secondary street setback",
        "applicability": "universal_residential",
        "source_text": "C.08 On corner lots, the secondary street setback must be a minimum of 4 metres",
        "section_ref": "3.4.1.2 C.08", "pdf_page": 80,
        "dcp_version": "Parramatta DCP 2023 Amendment 4", "source_chapter_key": "parramatta-dcp-2023-full",
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

print(f"Inserted {inserted} Waverley+Parramatta setback rows")

# Verify
for lga in ['waverley', 'parramatta']:
    cur.execute("""
    SELECT control_type, dev_type, value_min, value_max, unit, section_ref, pdf_page
    FROM dcp_setback_controls
    WHERE lga = %s AND control_type IN ('front_setback','side_setback','rear_setback')
    ORDER BY control_type, dev_type, id
    """, (lga,))
    print(f"\n{lga} setbacks ({cur.rowcount} rows):")
    for r in cur.fetchall():
        print(f"  {str(r[0]):16s} {str(r[1]):28s} min={r[2]} max={r[3]} {r[4]} ref={r[5]} p{r[6]}")

conn.close()
