"""
Randwick DCP 2013 + Sutherland Shire LEP 2015 Schedule 3 - Setback controls extraction
Randwick: Section 3.3.1 Front Setback, 3.3.2 Side Setbacks (from planning panel docs)
Sutherland: LEP 2015 Schedule 3 (statutory setback standards)
"""
import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

rows = [
    # === RANDWICK DCP 2013 ===
    # Front setback 6m (or average of adjoining)
    {
        "lga": "randwick", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": "or average setbacks of adjoining properties whichever applies",
        "applicability": "universal_residential",
        "source_text": "The average setbacks of adjoining properties, or if none, no less than 6m",
        "section_ref": "C1 3.3.1 Front Setback", "pdf_page": None,
        "dcp_version": "Randwick Comprehensive DCP 2013", "source_chapter_key": "randwick-dcp-c1-low-density",
    },
    # Side setback ground/first 1.2m (lots >12m frontage)
    {
        "lga": "randwick", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.2, "value_max": None, "unit": "m",
        "condition": "ground and first storey; lots with frontage greater than 12m",
        "applicability": "universal_residential",
        "source_text": "Comply with the minimum side setbacks: Ground storey 1.2m, First storey 1.2m",
        "section_ref": "C1 3.3.2 Side Setback", "pdf_page": None,
        "dcp_version": "Randwick Comprehensive DCP 2013", "source_chapter_key": "randwick-dcp-c1-low-density",
    },
    # Side setback second+ 1.8m
    {
        "lga": "randwick", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.8, "value_max": None, "unit": "m",
        "condition": "second storey and above; lots with frontage greater than 12m",
        "applicability": "universal_residential",
        "source_text": "Comply with the minimum side setbacks: Second storey and above 1.8m",
        "section_ref": "C1 3.3.2 Side Setback", "pdf_page": None,
        "dcp_version": "Randwick Comprehensive DCP 2013", "source_chapter_key": "randwick-dcp-c1-low-density",
    },
    # Side setback narrow lots 0.9m
    {
        "lga": "randwick", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 0.9, "value_max": None, "unit": "m",
        "condition": "all levels; lots with frontage less than 9m",
        "applicability": "universal_residential",
        "source_text": "For dwelling houses with frontage less than 9m: side setback 900mm",
        "section_ref": "C1 3.3.2 Side Setback", "pdf_page": None,
        "dcp_version": "Randwick Comprehensive DCP 2013", "source_chapter_key": "randwick-dcp-c1-low-density",
    },

    # === SUTHERLAND SHIRE LEP 2015 Schedule 3 ===
    # Front setback - average of 2 nearest or 5.5m minimum
    {
        "lga": "sutherland_shire", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 5.5, "value_max": None, "unit": "m",
        "condition": "or average distance of setbacks of nearest 2 dwelling houses within 40m whichever is greater",
        "applicability": "universal_residential",
        "source_text": "A setback from the primary street frontage determined by either a specified minimum distance or the average distance of the setbacks of the nearest 2 dwelling houses within 40m",
        "section_ref": "LEP 2015 Schedule 3", "pdf_page": None,
        "dcp_version": "Sutherland Shire LEP 2015", "source_chapter_key": "sutherland-lep-2015-schedule-3",
    },
    # Secondary street 3m
    {
        "lga": "sutherland_shire", "control_type": "front_setback", "dev_type": "dwelling_house",
        "value_min": 3, "value_max": None, "unit": "m",
        "condition": "secondary frontage",
        "applicability": "universal_residential",
        "source_text": "A setback from any secondary frontage of at least 3m",
        "section_ref": "LEP 2015 Schedule 3", "pdf_page": None,
        "dcp_version": "Sutherland Shire LEP 2015", "source_chapter_key": "sutherland-lep-2015-schedule-3",
    },
    # Side 1.5m
    {
        "lga": "sutherland_shire", "control_type": "side_setback", "dev_type": "dwelling_house",
        "value_min": 1.5, "value_max": None, "unit": "m",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "A setback from side boundaries of at least 1.5m",
        "section_ref": "LEP 2015 Schedule 3", "pdf_page": None,
        "dcp_version": "Sutherland Shire LEP 2015", "source_chapter_key": "sutherland-lep-2015-schedule-3",
    },
    # Rear 6m
    {
        "lga": "sutherland_shire", "control_type": "rear_setback", "dev_type": "dwelling_house",
        "value_min": 6, "value_max": None, "unit": "m",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "A setback from the rear boundary of at least 6m",
        "section_ref": "LEP 2015 Schedule 3", "pdf_page": None,
        "dcp_version": "Sutherland Shire LEP 2015", "source_chapter_key": "sutherland-lep-2015-schedule-3",
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

print(f"Inserted {inserted} Randwick + Sutherland Shire setback rows")

# Verify
for lga in ['randwick', 'sutherland_shire']:
    cur.execute("""
    SELECT control_type, dev_type, value_min, unit, LEFT(condition, 60), pdf_page
    FROM dcp_setback_controls
    WHERE lga = %s AND control_type IN ('front_setback','side_setback','rear_setback')
    ORDER BY control_type, dev_type, id
    """, (lga,))
    print(f"\n{lga} setbacks ({cur.rowcount} rows):")
    for r in cur.fetchall():
        print(f"  {str(r[0]):16s} {str(r[1]):20s} min={r[2]} {r[3]} p{r[5]} {r[4]}")

conn.close()
