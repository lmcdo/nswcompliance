"""
Northern Beaches (Warringah DCP 2011) - Side setback backfill
Source: B5 Side Boundary Setbacks (pages 17-21), B9 Rear Boundary Setbacks (pages 38-48)
Note: Front (6.5m R2) and Rear (6.0m R2) already in DB. Adding side setbacks.
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

DCP_VERSION = "Warringah DCP 2011 (as amended May 2016)"
CHAPTER_KEY = "warringah-dcp-2011-part-b"

rows = [
    # R2 side setback 0.9m
    {
        "lga": "northern_beaches", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": "R2 Low Density Residential zone",
        "applicability": "universal_residential",
        "source_text": "All land in R2 zone: 0.9m. Side boundary setback areas are to be landscaped and free of any above or below ground structures, car parking or site facilities other than driveways and fences.",
        "section_ref": "B5 Side Boundary Setbacks - R2", "pdf_page": 18,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # R3 side setback 4.5m (multi dwelling / RFB)
    {
        "lga": "northern_beaches", "control_type": "side_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 4.5, "value_max": None, "unit": "m",
        "condition": "R3 Medium Density Residential zone; above and below ground structures shall not encroach",
        "applicability": "universal_residential",
        "source_text": "All land in R3 zone: 4.5m. On land within the R3 Medium Density Residential zone, above and below ground structures and private open space, basement car parking, vehicle access ramps, balconies, terraces, and the like shall not encroach the side setback.",
        "section_ref": "B5 Side Boundary Setbacks - R3", "pdf_page": 19,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # R3 side setback for RFB
    {
        "lga": "northern_beaches", "control_type": "side_setback", "dev_type": "residential_flat_building",
        "value_min": 4.5, "value_max": None, "unit": "m",
        "condition": "R3 Medium Density Residential zone",
        "applicability": "universal_residential",
        "source_text": "All land in R3 zone: 4.5m",
        "section_ref": "B5 Side Boundary Setbacks - R3", "pdf_page": 19,
        "dcp_version": DCP_VERSION, "source_chapter_key": CHAPTER_KEY,
    },
    # R3 rear setback 6m
    {
        "lga": "northern_beaches", "control_type": "rear_setback", "dev_type": "multi_dwelling_housing",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "R3 Medium Density Residential zone; above and below ground structures shall not encroach",
        "applicability": "universal_residential",
        "source_text": "All other land within R3: 6m. On land zoned R3 Medium Density where there is a 6m rear boundary setback, above and below ground structures and private open space, including basement carparking, vehicle access ramps, balconies, terraces, and the like shall not encroach the rear building setback.",
        "section_ref": "B9 Rear Boundary Setbacks - R3", "pdf_page": 45,
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

print(f"Inserted {inserted} Northern Beaches setback rows")

# Verify
cur.execute("""
SELECT control_type, dev_type, value_min, unit, LEFT(condition, 55), pdf_page
FROM dcp_setback_controls
WHERE lga = 'northern_beaches' AND control_type IN ('front_setback','side_setback','rear_setback')
ORDER BY control_type, dev_type, id
""")
print(f"\nVerification ({cur.rowcount} rows):")
for r in cur.fetchall():
    print(f"  {str(r[0]):16s} {str(r[1]):28s} min={r[2]} {r[3]} p{r[5]} {r[4]}")

conn.close()
