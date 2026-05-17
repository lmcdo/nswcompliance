#!/usr/bin/env python3
"""
Insert Inner West landscaping controls into dcp_setback_controls.

Sources (3 former DCPs):
- Ashfield DCP 2016, Chapter F — Dwelling Houses (DS18.5)
- Leichhardt DCP 2013, Part C — Residential (C1 deep soil, landscaping)
- Marrickville DCP 2011, Section 4.1/4.2 — Residential + Section 2.18

Notes:
- Inner West is a merged council with 3 operative DCPs.
- Each former LGA has different landscaping controls.
- Ashfield: 35% landscaped area (DS18.5), max 65% site coverage
- Leichhardt: 10% deep soil (general residential), 20% landscaped area
- Marrickville: dwelling house 25% open space, MDH/RFB 45% site area landscaped,
  25% of open space as deep soil

Usage:
    python scripts/insert_inner_west_landscaping.py --dry-run
    python scripts/insert_inner_west_landscaping.py
"""
import argparse
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

LGA = "inner_west"

LANDSCAPING_ROWS = [
    # ── Former Ashfield LGA ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "former Ashfield LGA",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% of site area as landscaped area (Ashfield DCP 2016 DS18.5)",
        "section_ref": "f-dwelling-houses",
        "dcp_version": "v2016-iw-comprehensive",
        "extraction_method": "text_extraction",
        "source_chapter_key": "ashfield-chapter-a-miscellaneous",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 65,
        "unit": "%",
        "condition": "former Ashfield LGA",
        "applicability": "universal_residential",
        "source_text": "Site cover over 65% not supported (Ashfield DCP 2016 F-Dwelling Houses)",
        "section_ref": "f-dwelling-houses",
        "dcp_version": "v2016-iw-comprehensive",
        "extraction_method": "text_extraction",
        "source_chapter_key": "ashfield-chapter-a-miscellaneous",
    },
    # ── Former Leichhardt LGA ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 10,
        "value_max": None,
        "unit": "%",
        "condition": "former Leichhardt LGA",
        "applicability": "universal_residential",
        "source_text": "Minimum 10% of site area as deep soil planting (Leichhardt DCP 2013 C1)",
        "section_ref": "c-landscaping",
        "dcp_version": "v2013-leichhardt",
        "extraction_method": "text_extraction",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": "former Leichhardt LGA",
        "applicability": "universal_residential",
        "source_text": "Minimum 20% of site area as landscaped area (Leichhardt DCP 2013 Open Space and Landscape C1)",
        "section_ref": "c-open-space-landscape",
        "dcp_version": "v2013-leichhardt",
        "extraction_method": "text_extraction",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 10,
        "value_max": None,
        "unit": "%",
        "condition": "former Leichhardt LGA",
        "applicability": "universal_residential",
        "source_text": "Minimum 10% of site as deep soil planting (Leichhardt DCP 2013 Open Space and Landscape C2)",
        "section_ref": "c-open-space-landscape",
        "dcp_version": "v2013-leichhardt",
        "extraction_method": "text_extraction",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "tree_canopy_min",
        "value_min": 15,
        "value_max": None,
        "unit": "%",
        "condition": "former Leichhardt LGA",
        "applicability": "universal_residential",
        "source_text": "Landscaping and mature tree planting shall achieve 15% site canopy (Leichhardt DCP 2013 C2)",
        "section_ref": "c-open-space-landscape",
        "dcp_version": "v2013-leichhardt",
        "extraction_method": "text_extraction",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    # ── Former Marrickville LGA ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 25,
        "value_max": None,
        "unit": "%",
        "condition": "former Marrickville LGA; open space min",
        "applicability": "universal_residential",
        "source_text": "Minimum 25% of site area as open space (Marrickville DCP 2011 s4.1)",
        "section_ref": "4-1-low-density",
        "dcp_version": "v2011-marrickville",
        "extraction_method": "text_extraction",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 45,
        "value_max": None,
        "unit": "%",
        "condition": "former Marrickville LGA; in addition to front setback",
        "applicability": "universal_residential",
        "source_text": "Minimum 45% of total site area as landscaped area in addition to front setback (Marrickville DCP 2011 s4.2)",
        "section_ref": "4-2-mdh-rfb",
        "dcp_version": "v2011-marrickville",
        "extraction_method": "text_extraction",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 45,
        "value_max": None,
        "unit": "%",
        "condition": "former Marrickville LGA; in addition to front setback",
        "applicability": "universal_residential",
        "source_text": "Minimum 45% of total site area as landscaped area in addition to front setback (Marrickville DCP 2011 s4.2)",
        "section_ref": "4-2-mdh-rfb",
        "dcp_version": "v2011-marrickville",
        "extraction_method": "text_extraction",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 25,
        "value_max": None,
        "unit": "%",
        "condition": "former Marrickville LGA; 25% of open space area",
        "applicability": "universal_residential",
        "source_text": "Minimum 25% of open space area as deep soil (Marrickville DCP 2011 s4.1)",
        "section_ref": "4-1-low-density",
        "dcp_version": "v2011-marrickville",
        "extraction_method": "text_extraction",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    skipped = 0

    for row in LANDSCAPING_ROWS:
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition, '') = COALESCE(%s, '')
              AND is_current = TRUE
        """, (LGA, row["dev_type"], row["control_type"],
              row.get("condition")))
        if cur.fetchone():
            print(f"  SKIP dup: {row['dev_type']} {row['control_type']} "
                  f"cond={(row.get('condition') or '')[:50]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']} "
                  f"cond={(row.get('condition') or '')[:55]}")
        else:
            cur.execute("""
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref,
                   dcp_version, is_current, extraction_method, source_chapter_key)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s)
            """, (LGA, row["dev_type"], row["control_type"],
                  row.get("value_min"), row.get("value_max"), row["unit"],
                  row.get("condition"), row["applicability"],
                  row["source_text"], row["section_ref"],
                  row["dcp_version"], row["extraction_method"],
                  row["source_chapter_key"]))
            print(f"  INSERT: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']} "
                  f"[{row.get('condition','')[:30]}]")
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")
    conn.close()


if __name__ == "__main__":
    main()
