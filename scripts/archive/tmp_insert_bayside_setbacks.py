"""
Bayside DCP 2022 (Amendment 2) - Setback controls extraction
Source: Section 5.2.1 Low-density (pages 199-201), 5.2.3 Medium density (pages 210-211),
5.2.4 High density (pages 217-218)
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Bayside DCP 2022 Amendment 2 (April 2026)"

rows = [
    # === LOW DENSITY (5.2.1) - dwelling_house, dual_occupancy ===
    # Front setback 6m (or average of adjoining)
    {
        "lga": "bayside", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "or average of dwellings on adjoining lots whichever applies",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a primary road is either: a. the average of the dwellings on adjoining lots; b. otherwise, 6m.",
        "section_ref": "5.2.1 Setbacks C1", "pdf_page": 200,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Secondary road 1.5m
    {
        "lga": "bayside", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "secondary road",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a secondary road is 1.5m",
        "section_ref": "5.2.1 Setbacks C2", "pdf_page": 200,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Rear 5m
    {
        "lga": "bayside", "control_type": "rear_setback", "dev_type": "dwelling_house",
        "value_min": 5, "value_max": None, "unit": "m",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a rear boundary is 5m.",
        "section_ref": "5.2.1 Setbacks C5", "pdf_page": 200,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Side ground 0.9m
    {
        "lga": "bayside", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": "ground floor",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a side boundary is 0.9m (ground floor) and 1.5m (first storey and above).",
        "section_ref": "5.2.1 Setbacks C6", "pdf_page": 200,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Side first floor+ 1.5m
    {
        "lga": "bayside", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "first storey and above",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a side boundary is 0.9m (ground floor) and 1.5m (first storey and above).",
        "section_ref": "5.2.1 Setbacks C6", "pdf_page": 200,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Dual occupancy uses same setbacks as low density per 5.2.2
    {
        "lga": "bayside", "control_type": "front_setback", "dev_type": "dual_occupancy",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "or average of dwellings on adjoining lots; minimum lot width 15m",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a primary road is either: a. the average of the dwellings on adjoining lots; b. otherwise, 6m.",
        "section_ref": "5.2.1 Setbacks C1 (applies per 5.2.2)", "pdf_page": 200,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },

    # === MEDIUM DENSITY (5.2.3) - multi_dwelling_housing ===
    # Front 6m
    {
        "lga": "bayside", "control_type": "front_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "or compatible with predominant existing setback",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a road is either: a. compatible with the predominant existing setback b. where there is no predominant existing setback: 6m",
        "section_ref": "5.2.3 Setbacks C1", "pdf_page": 210,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Secondary road 1.5m
    {
        "lga": "bayside", "control_type": "front_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "secondary road",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a secondary road is 1.5m.",
        "section_ref": "5.2.3 Setbacks C3", "pdf_page": 210,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Side ground 0.9m (front 2/3 of site)
    {
        "lga": "bayside", "control_type": "side_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": "ground floor; front two-thirds of site",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a side boundary is: For the front two-thirds of site: a. 0.9m (ground floor) and 1.5m first floor and above.",
        "section_ref": "5.2.3 Setbacks C4", "pdf_page": 210,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Side first floor+ 1.5m (front 2/3)
    {
        "lga": "bayside", "control_type": "side_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": "first floor and above; front two-thirds of site",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a side boundary is: For the front two-thirds of site: a. 0.9m (ground floor) and 1.5m first floor and above.",
        "section_ref": "5.2.3 Setbacks C4", "pdf_page": 210,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Side rear 1/3: 4m
    {
        "lga": "bayside", "control_type": "side_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 4, "value_max": None, "unit": "m",
        "condition": "rear third of site",
        "applicability": "universal_residential",
        "source_text": "Minimum building setback to a side boundary is: For the rear third of the site: 4m",
        "section_ref": "5.2.3 Setbacks C4", "pdf_page": 210,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Rear ground 4m
    {
        "lga": "bayside", "control_type": "rear_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 4, "value_max": None, "unit": "m",
        "condition": "ground storey",
        "applicability": "universal_residential",
        "source_text": "Minimum building setbacks to a rear boundary are: a. For a ground storey: 4m",
        "section_ref": "5.2.3 Setbacks C5", "pdf_page": 210,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Rear above ground 6m
    {
        "lga": "bayside", "control_type": "rear_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "above ground storey",
        "applicability": "universal_residential",
        "source_text": "Minimum building setbacks to a rear boundary are: b. For above the ground storey: 6m",
        "section_ref": "5.2.3 Setbacks C5", "pdf_page": 211,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },

    # === HIGH DENSITY (5.2.4) - residential_flat_building ===
    # Side up to 4 storeys 3m
    {
        "lga": "bayside", "control_type": "side_setback", "dev_type": "residential_flat_building",
        "value_min": 3, "value_max": None, "unit": "m",
        "condition": "up to four storeys (approx 12m); habitable rooms/balconies; where ADG doesn't apply",
        "applicability": "universal_residential",
        "source_text": "Where the ADG doesn't apply: Minimum building setback to a side boundary: i. up to four storeys (approximately 12m): 3m between habitable rooms/balconies",
        "section_ref": "5.2.4 Setbacks C2(a)(i)", "pdf_page": 217,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Side 4+ storeys 4.5m
    {
        "lga": "bayside", "control_type": "side_setback", "dev_type": "residential_flat_building",
        "value_min": 4.5, "value_max": None, "unit": "m",
        "condition": "four storeys and above (approx 12m+); where ADG doesn't apply",
        "applicability": "universal_residential",
        "source_text": "Where the ADG doesn't apply: Minimum building setback to a side boundary: ii. four storeys (approximately 12m) and above: 4.5m",
        "section_ref": "5.2.4 Setbacks C2(a)(ii)", "pdf_page": 217,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
    },
    # Rear 6m or 15%
    {
        "lga": "bayside", "control_type": "rear_setback", "dev_type": "residential_flat_building",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "or 15% of site length whichever is greater; where ADG doesn't apply",
        "applicability": "universal_residential",
        "source_text": "Where the ADG doesn't apply: Minimum building setback to a rear boundary shall be, whichever is greater: i. 6m ii. 15% of the length of the site",
        "section_ref": "5.2.4 Setbacks C2(b)", "pdf_page": 217,
        "dcp_version": DCP_VERSION, "source_chapter_key": "bayside-dcp-2022-part5",
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

print(f"Inserted {inserted} Bayside setback rows")

# Verify
cur.execute("""
SELECT control_type, dev_type, value_min, unit, LEFT(condition, 55), pdf_page
FROM dcp_setback_controls
WHERE lga = 'bayside' AND control_type IN ('front_setback','side_setback','rear_setback')
ORDER BY control_type, dev_type, id
""")
print(f"\nVerification ({cur.rowcount} rows):")
for r in cur.fetchall():
    print(f"  {str(r[0]):16s} {str(r[1]):28s} min={r[2]} {r[3]} p{r[5]} {r[4]}")

conn.close()
