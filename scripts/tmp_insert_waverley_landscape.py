"""
Waverley DCP 2022 — landscaping, deep soil, and open space controls
Sources:
  Part C1.9 (page 21/198) — Low Density Residential
  Part C2.9 (page 50/227) — Other Residential Development
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP = "Waverley DCP 2022"

rows = [
    # === C1 Low Density: landscaped area 20%, deep soil 50% of landscaped (=10% of site) ===
    {
        "lga": "waverley", "control_type": "landscaping_min", "dev_type": "dwelling_house",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "20% of total site area as landscaped area; also 40% open space required",
        "applicability": "universal_residential",
        "source_text": "A minimum of 20% of the total site area is to be provided as landscaped area.",
        "section_ref": "C1.9(c)", "pdf_page": 21,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c1",
    },
    {
        "lga": "waverley", "control_type": "landscaping_min", "dev_type": "dual_occupancy",
        "value_min": 20, "value_max": None, "unit": "%",
        "condition": "20% of total site area as landscaped area; also 40% open space required",
        "applicability": "universal_residential",
        "source_text": "A minimum of 20% of the total site area is to be provided as landscaped area.",
        "section_ref": "C1.9(c)", "pdf_page": 21,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c1",
    },
    {
        "lga": "waverley", "control_type": "deep_soil_min", "dev_type": "dwelling_house",
        "value_min": 10, "value_max": None, "unit": "%",
        "condition": "50% of landscaped area (20%) must be deep soil zone = 10% of total site area",
        "applicability": "universal_residential",
        "source_text": "A minimum 50% of the landscaped area must be deep soil zone.",
        "section_ref": "C1.9(d)", "pdf_page": 21,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c1",
    },
    {
        "lga": "waverley", "control_type": "deep_soil_min", "dev_type": "dual_occupancy",
        "value_min": 10, "value_max": None, "unit": "%",
        "condition": "50% of landscaped area (20%) must be deep soil zone = 10% of total site area",
        "applicability": "universal_residential",
        "source_text": "A minimum 50% of the landscaped area must be deep soil zone.",
        "section_ref": "C1.9(d)", "pdf_page": 21,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c1",
    },

    # === C2 Other Residential: landscaped area 30%, deep soil 50% of landscaped (=15% of site) ===
    {
        "lga": "waverley", "control_type": "landscaping_min", "dev_type": "multi_dwelling_housing",
        "value_min": 30, "value_max": None, "unit": "%",
        "condition": "30% of site area as landscaped area",
        "applicability": "universal_residential",
        "source_text": "30% of the site area is to be provided as landscaped area.",
        "section_ref": "C2.9(b)", "pdf_page": 50,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c2",
    },
    {
        "lga": "waverley", "control_type": "landscaping_min", "dev_type": "residential_flat_building",
        "value_min": 30, "value_max": None, "unit": "%",
        "condition": "30% of site area as landscaped area",
        "applicability": "universal_residential",
        "source_text": "30% of the site area is to be provided as landscaped area.",
        "section_ref": "C2.9(b)", "pdf_page": 50,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c2",
    },
    {
        "lga": "waverley", "control_type": "deep_soil_min", "dev_type": "multi_dwelling_housing",
        "value_min": 15, "value_max": None, "unit": "%",
        "condition": "50% of landscaped area (30%) must be deep soil zone = 15% of total site area",
        "applicability": "universal_residential",
        "source_text": "50% of the landscaped area must be deep soil zone.",
        "section_ref": "C2.9(c)", "pdf_page": 50,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c2",
    },
    {
        "lga": "waverley", "control_type": "deep_soil_min", "dev_type": "residential_flat_building",
        "value_min": 15, "value_max": None, "unit": "%",
        "condition": "50% of landscaped area (30%) must be deep soil zone = 15% of total site area",
        "applicability": "universal_residential",
        "source_text": "50% of the landscaped area must be deep soil zone.",
        "section_ref": "C2.9(c)", "pdf_page": 50,
        "dcp_version": DCP, "source_chapter_key": "waverley-dcp-2022-part-c2",
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

print(f"Inserted {inserted} Waverley landscaping/deep soil rows")

cur.execute('SELECT COUNT(*) FROM dcp_setback_controls WHERE is_current = true')
print(f"Total active rows: {cur.fetchone()[0]}")

conn.close()
