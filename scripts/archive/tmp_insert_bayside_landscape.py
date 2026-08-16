"""
Bayside DCP 2022 - Landscaping controls extraction
Source: Section 3.7.1 Table 7 (page 87)
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Bayside DCP 2022 Amendment 2 (April 2026)"

rows = [
    # Low density landscaping 25%
    {
        "lga": "bayside", "control_type": "landscaping_min", "dev_type": "dwelling_house",
        "value_min": 25, "value_max": None, "unit": "%",
        "condition": "low density residential",
        "applicability": "universal_residential",
        "source_text": "The minimum amount of landscaped area within the site: Low and medium density residential 25%",
        "section_ref": "3.7.1 C12 Table 7", "pdf_page": 87,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part3",
    },
    {
        "lga": "bayside", "control_type": "landscaping_min", "dev_type": "dual_occupancy",
        "value_min": 25, "value_max": None, "unit": "%",
        "condition": "low density residential",
        "applicability": "universal_residential",
        "source_text": "The minimum amount of landscaped area within the site: Low and medium density residential 25%",
        "section_ref": "3.7.1 C12 Table 7", "pdf_page": 87,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part3",
    },
    # Medium density landscaping 25%
    {
        "lga": "bayside", "control_type": "landscaping_min", "dev_type": "multi_dwelling_housing",
        "value_min": 25, "value_max": None, "unit": "%",
        "condition": "medium density residential",
        "applicability": "universal_residential",
        "source_text": "The minimum amount of landscaped area within the site: Low and medium density residential 25%",
        "section_ref": "3.7.1 C12 Table 7", "pdf_page": 87,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part3",
    },
    # RFB landscaping 15%
    {
        "lga": "bayside", "control_type": "landscaping_min", "dev_type": "residential_flat_building",
        "value_min": 15, "value_max": None, "unit": "%",
        "condition": "residential flat buildings",
        "applicability": "universal_residential",
        "source_text": "The minimum amount of landscaped area within the site: Residential flat buildings 15%",
        "section_ref": "3.7.1 C12 Table 7", "pdf_page": 87,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part3",
    },
    # Site coverage - Warringah DCP B4 applies to Northern Beaches via map
    # Northern Beaches site coverage: 33.3% or 20-30% depending on DCP map
    {
        "lga": "northern_beaches", "control_type": "max_site_coverage", "dev_type": "dwelling_house",
        "value_min": None, "value_max": 33.3, "unit": "%",
        "condition": "per DCP Map Site Coverage; some areas 20% (lots >=3500sqm) or 30% (lots <3500sqm)",
        "applicability": "universal_residential",
        "source_text": "Development on land shown coloured on the DCP Map Site Coverage shall not exceed the maximum site coverage shown on the map: 33.3% or 20% for lots >=3,500sqm / 30% for lots <3,500sqm",
        "section_ref": "B4 Site Coverage", "pdf_page": 17,
        "dcp_version": "Warringah DCP 2011 (as amended May 2016)", "source_chapter_key": "warringah-dcp-2011-part-b",
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

print(f"Inserted {inserted} landscaping/coverage rows")

# Final coverage check
cur.execute('SELECT COUNT(*) FROM dcp_setback_controls WHERE is_current = true')
print(f"\nTotal rows: {cur.fetchone()[0]}")

conn.close()
