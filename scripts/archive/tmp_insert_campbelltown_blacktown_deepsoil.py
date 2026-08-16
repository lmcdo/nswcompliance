"""
Campbelltown SCDCP 2015 + Blacktown BDCP 2015 — deep soil controls extraction
Sources:
  Campbelltown: Part 3, Sections 3.6.1.2, 3.6.3.6, 3.6.4.6, 3.6.5.8, 3.7.1.9, 3.7.2.9, 3.7.3.9
  Blacktown: Part C, Table 6.4 (page 58) — ADG reference
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

rows = [
    # === CAMPBELLTOWN deep soil 20% across all residential types ===
    {
        "lga": "campbelltown", "control_type": "deep_soil_min", "dev_type": "dwelling_house",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "minimum 20% of total site area for deep soil planting",
        "applicability": "universal_residential",
        "source_text": "A dwelling house shall satisfy the following provisions relating to deep soil planting: a minimum of 20% of the total site area shall be available for deep soil planting.",
        "section_ref": "3.6.1.2", "pdf_page": 20,
        "dcp_version": "Campbelltown SCDCP 2015 (updated 02/09/2024)",
        "source_chapter_key": "campbelltown-scdcp-2015-part3",
    },
    {
        "lga": "campbelltown", "control_type": "deep_soil_min", "dev_type": "dual_occupancy",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "minimum 20% of total site area for deep soil planting",
        "applicability": "universal_residential",
        "source_text": "A dual occupancy shall satisfy the following provisions relating to deep soil planting: a minimum of 20% of the total site area shall be available for deep soil planting.",
        "section_ref": "3.6.3.6", "pdf_page": 26,
        "dcp_version": "Campbelltown SCDCP 2015 (updated 02/09/2024)",
        "source_chapter_key": "campbelltown-scdcp-2015-part3",
    },
    {
        "lga": "campbelltown", "control_type": "deep_soil_min", "dev_type": "semi_detached",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "minimum 20% of total site area for deep soil planting",
        "applicability": "universal_residential",
        "source_text": "A semi detached dwelling shall satisfy the following provisions relating to deep soil planting: a minimum of 20% of the total site area shall be available for deep soil planting.",
        "section_ref": "3.6.4.6", "pdf_page": 29,
        "dcp_version": "Campbelltown SCDCP 2015 (updated 02/09/2024)",
        "source_chapter_key": "campbelltown-scdcp-2015-part3",
    },
    {
        "lga": "campbelltown", "control_type": "deep_soil_min", "dev_type": "attached_dwelling",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "minimum 20% of total site area for deep soil planting; applies R2 (3.6.5.8) and R3 (3.7.1.9)",
        "applicability": "universal_residential",
        "source_text": "Attached dwellings shall satisfy the following provisions relating to deep soil planting: a minimum of 20% of the total site area shall be available for deep soil planting.",
        "section_ref": "3.6.5.8 / 3.7.1.9", "pdf_page": 35,
        "dcp_version": "Campbelltown SCDCP 2015 (updated 02/09/2024)",
        "source_chapter_key": "campbelltown-scdcp-2015-part3",
    },
    {
        "lga": "campbelltown", "control_type": "deep_soil_min", "dev_type": "multi_dwelling_housing",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "minimum 20% of total site area for deep soil planting",
        "applicability": "universal_residential",
        "source_text": "a minimum of 20% of the total site area shall be available for deep soil planting",
        "section_ref": "3.7.2.9", "pdf_page": 51,
        "dcp_version": "Campbelltown SCDCP 2015 (updated 02/09/2024)",
        "source_chapter_key": "campbelltown-scdcp-2015-part3",
    },
    {
        "lga": "campbelltown", "control_type": "deep_soil_min", "dev_type": "manor_house",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "minimum 20% of total site area for deep soil planting",
        "applicability": "universal_residential",
        "source_text": "All manor house proposals shall satisfy the following requirements relating to landscape: a minimum of 20% of the total site area shall be available for deep soil planting",
        "section_ref": "3.7.3.9", "pdf_page": 61,
        "dcp_version": "Campbelltown SCDCP 2015 (updated 02/09/2024)",
        "source_chapter_key": "campbelltown-scdcp-2015-part3",
    },

    # === BLACKTOWN deep soil for RFBs (ADG reference via Table 6.4) ===
    {
        "lga": "blacktown", "control_type": "deep_soil_min", "dev_type": "residential_flat_building",
        "value_min": 7, "value_max": None, "unit": "%",
        "condition": "sites <650sqm; per ADG Table 6.4. Larger sites: 3m min dimension (650-1500sqm), 6m min dimension (>1500sqm)",
        "applicability": "universal_residential",
        "source_text": "Deep soil zones must comply with the requirements of the NSW Apartment Design Guide. Table 6.4 Minimum deep soil zone sizes: less than 650sq.m - 7%",
        "section_ref": "6.9.1 Table 6.4", "pdf_page": 58,
        "dcp_version": "Blacktown DCP 2015 (revised November 2025)",
        "source_chapter_key": "blacktown-dcp-2015-part-c",
    },

    # === BLACKTOWN common open space 25% for RFBs ===
    {
        "lga": "blacktown", "control_type": "communal_open_space_min", "dev_type": "residential_flat_building",
        "value_min": 25, "value_max": None, "unit": "%",
        "condition": "minimum total area equal to 25% of the site; 3m minimum dimension; 50% direct sunlight 2hrs 9am-3pm 21 June",
        "applicability": "universal_residential",
        "source_text": "Common open space must comply with the requirements of the NSW Apartment Design Guide: Minimum total area equal to 25% of the site",
        "section_ref": "6.7.2", "pdf_page": 54,
        "dcp_version": "Blacktown DCP 2015 (revised November 2025)",
        "source_chapter_key": "blacktown-dcp-2015-part-c",
    },

    # === CANTERBURY-BANKSTOWN front setback landscaping 45% ===
    # Note: this is 45% of the FRONT SETBACK AREA, not total site area
    {
        "lga": "canterbury_bankstown", "control_type": "landscaping_min", "dev_type": "dwelling_house",
        "value_min": 45, "value_max": None, "unit": "%",
        "condition": "of area between building and primary street frontage (not total site area); also 45% of secondary street frontage area",
        "applicability": "universal_residential",
        "source_text": "Development must landscape the following areas on the site: a minimum 45% of the area between the dwelling house and the primary street frontage; and a minimum 45% of the area between the dwelling house and the secondary street frontage",
        "section_ref": "2.29", "pdf_page": 10,
        "dcp_version": "Canterbury-Bankstown DCP 2023 Chapter 5.1 (Amended March 2026)",
        "source_chapter_key": "cb-dcp-2023-ch5-1",
    },
    {
        "lga": "canterbury_bankstown", "control_type": "landscaping_min", "dev_type": "dual_occupancy",
        "value_min": 45, "value_max": None, "unit": "%",
        "condition": "of area between building and primary street frontage (not total site area); also 45% of secondary street frontage area",
        "applicability": "universal_residential",
        "source_text": "Development must landscape the following areas on the site: a minimum 45% of the area between the dual occupancy and the primary street frontage; and a minimum 45% of the area between the dual occupancy and the secondary street frontage",
        "section_ref": "4.31", "pdf_page": 19,
        "dcp_version": "Canterbury-Bankstown DCP 2023 Chapter 5.1 (Amended March 2026)",
        "source_chapter_key": "cb-dcp-2023-ch5-1",
    },
    {
        "lga": "canterbury_bankstown", "control_type": "landscaping_min", "dev_type": "semi_detached",
        "value_min": 45, "value_max": None, "unit": "%",
        "condition": "of area between building and primary street frontage (not total site area); also 45% of secondary street frontage area",
        "applicability": "universal_residential",
        "source_text": "Development must landscape the following areas on the site: a minimum 45% of the area between the semi-detached dwellings and the primary street frontage; and a minimum 45% of the area between the semi-detached dwellings and the secondary street frontage",
        "section_ref": "5.31", "pdf_page": 24,
        "dcp_version": "Canterbury-Bankstown DCP 2023 Chapter 5.1 (Amended March 2026)",
        "source_chapter_key": "cb-dcp-2023-ch5-1",
    },
    {
        "lga": "canterbury_bankstown", "control_type": "landscaping_min", "dev_type": "attached_dwelling",
        "value_min": 45, "value_max": None, "unit": "%",
        "condition": "of area between building and primary street frontage (not total site area); also 45% of secondary street frontage area",
        "applicability": "universal_residential",
        "source_text": "Development must landscape the following areas on the site: a minimum 45% of the area between the attached dwellings and the primary street frontage; and a minimum 45% of the area between the attached dwellings and the secondary street frontage",
        "section_ref": "6.27", "pdf_page": 28,
        "dcp_version": "Canterbury-Bankstown DCP 2023 Chapter 5.1 (Amended March 2026)",
        "source_chapter_key": "cb-dcp-2023-ch5-1",
    },
    {
        "lga": "canterbury_bankstown", "control_type": "landscaping_min", "dev_type": "multi_dwelling_housing",
        "value_min": 45, "value_max": None, "unit": "%",
        "condition": "of area between building and primary street frontage (not total site area); also 45% of secondary street frontage area",
        "applicability": "universal_residential",
        "source_text": "Development must landscape the following areas on the site: a minimum 45% of the area between the multi dwelling housing and the primary street frontage",
        "section_ref": "7.16", "pdf_page": 32,
        "dcp_version": "Canterbury-Bankstown DCP 2023 Chapter 5.1 (Amended March 2026)",
        "source_chapter_key": "cb-dcp-2023-ch5-1",
    },
    {
        "lga": "canterbury_bankstown", "control_type": "landscaping_min", "dev_type": "residential_flat_building",
        "value_min": 45, "value_max": None, "unit": "%",
        "condition": "of area between building and primary street frontage (not total site area); also 45% of secondary street frontage area",
        "applicability": "universal_residential",
        "source_text": "Development must landscape the following areas on the site: a minimum 45% of the area between the building and the primary street frontage; and a minimum 45% of the area between the building and the secondary street frontage",
        "section_ref": "8.31", "pdf_page": 38,
        "dcp_version": "Canterbury-Bankstown DCP 2023 Chapter 5.1 (Amended March 2026)",
        "source_chapter_key": "cb-dcp-2023-ch5-1",
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

print(f"Inserted {inserted} rows (Campbelltown deep soil: 6, Blacktown deep soil+COS: 2, CB landscaping: 6)")

# Register chapter keys
chapters = [
    ('campbelltown-scdcp-2015-part3', 'Campbelltown SCDCP 2015 Part 3 - Residential Development', 'campbelltown'),
    ('blacktown-dcp-2015-part-c', 'Blacktown DCP 2015 Part C - Development in Residential Areas', 'blacktown'),
    ('cb-dcp-2023-ch5-1', 'Canterbury-Bankstown DCP 2023 Chapter 5.1 - Former Bankstown LGA', 'canterbury_bankstown'),
]
for key, title, lga in chapters:
    cur.execute("""
    INSERT INTO dcp_chapters (chapter_key, dcp_title, lga, is_monitored, last_checked)
    VALUES (%s, %s, %s, true, NOW())
    ON CONFLICT (chapter_key) DO UPDATE SET last_checked = NOW()
    """, (key, title, lga))

print("Chapter keys registered")

# Final count
cur.execute('SELECT COUNT(*) FROM dcp_setback_controls WHERE is_current = true')
print(f"\nTotal rows: {cur.fetchone()[0]}")

conn.close()
