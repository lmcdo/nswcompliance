#!/usr/bin/env python3
"""
Register DCP chapters for new LGAs in dcp_chapter_registry.

These LGAs have control rows in dcp_setback_controls but no chapter_registry
entries, meaning their source PDFs are not monitored for changes.

Usage:
    python scripts/register_new_lga_chapters.py --dry-run   # preview
    python scripts/register_new_lga_chapters.py             # apply
"""
import argparse
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

# New chapter registrations: (council, chapter_key, chapter_label, dcp_name, council_page_url)
# council_page_url is the hub page where chapter PDFs are listed
NEW_CHAPTERS = [
    # Burwood
    ("burwood", "part-4-residential", "Part 4 - Residential Development",
     "Burwood DCP 2013",
     "https://www.burwood.nsw.gov.au/Planning-and-Development/Planning-Controls/Development-Control-Plans"),
    ("burwood", "s4-landscaping", "Part 4 - Landscaping",
     "Burwood DCP 2013",
     "https://www.burwood.nsw.gov.au/Planning-and-Development/Planning-Controls/Development-Control-Plans"),
    ("burwood", "s4-table-4-parking", "Part 4 - Parking Rates Table",
     "Burwood DCP 2013",
     "https://www.burwood.nsw.gov.au/Planning-and-Development/Planning-Controls/Development-Control-Plans"),

    # Camden
    ("camden", "part-4-residential", "Part 4 - Residential Dwelling Controls",
     "Camden DCP 2019",
     "https://www.camden.nsw.gov.au/planning-and-building/planning-controls/development-control-plan"),
    ("camden", "s4-2-6-landscaping", "Section 4.2.6 - Landscaping",
     "Camden DCP 2019",
     "https://www.camden.nsw.gov.au/planning-and-building/planning-controls/development-control-plan"),

    # Canada Bay
    ("canada_bay", "part-e-single-dwellings", "Part E - Single Dwellings",
     "Canada Bay DCP 2020",
     "https://www.canadabay.nsw.gov.au/planning-and-development/rules-for-development/development-control-plan"),
    ("canada_bay", "landscaping-controls", "Landscaping Controls",
     "Canada Bay DCP 2020",
     "https://www.canadabay.nsw.gov.au/planning-and-development/rules-for-development/development-control-plan"),
    ("canada_bay", "part-c-table-cb-parking", "Part C - Parking Rates Table",
     "Canada Bay DCP 2020",
     "https://www.canadabay.nsw.gov.au/planning-and-development/rules-for-development/development-control-plan"),

    # Fairfield
    ("fairfield", "chapter-5-dwelling-houses", "Chapter 5 - Dwelling Houses",
     "Fairfield DCP 2013",
     "https://www.fairfieldcity.nsw.gov.au/Development/Development-Controls/Development-Control-Plan"),
    ("fairfield", "landscaping-controls", "Landscaping Controls",
     "Fairfield DCP 2013",
     "https://www.fairfieldcity.nsw.gov.au/Development/Development-Controls/Development-Control-Plan"),
    ("fairfield", "parking-controls", "Parking Controls",
     "Fairfield DCP 2013",
     "https://www.fairfieldcity.nsw.gov.au/Development/Development-Controls/Development-Control-Plan"),

    # Ryde
    ("ryde", "part-3-3-dwelling-houses", "Part 3.3 - Dwelling Houses",
     "Ryde DCP 2014",
     "https://www.ryde.nsw.gov.au/development/planning-controls/development-control-plan"),
    ("ryde", "part-9.3-parking", "Part 9.3 - Parking",
     "Ryde DCP 2014",
     "https://www.ryde.nsw.gov.au/development/planning-controls/development-control-plan"),

    # Strathfield
    ("strathfield", "part-a-dwelling-houses", "Part A - Dwelling Houses",
     "Strathfield DCP 2005",
     "https://www.strathfield.nsw.gov.au/planning-and-development/planning-controls/development-control-plan"),
    ("strathfield", "landscaping-controls", "Landscaping Controls",
     "Strathfield DCP 2005",
     "https://www.strathfield.nsw.gov.au/planning-and-development/planning-controls/development-control-plan"),
    ("strathfield", "parking-controls", "Parking Controls",
     "Strathfield DCP 2005",
     "https://www.strathfield.nsw.gov.au/planning-and-development/planning-controls/development-control-plan"),

    # The Hills
    ("the_hills", "part-b-section-2-residential", "Part B Section 2 - Residential Development",
     "The Hills DCP 2012",
     "https://www.thehills.nsw.gov.au/Building-and-Development/Development-Controls/Development-Control-Plans"),
    ("the_hills_shire", "part-c-s1-parking", "Part C Section 1 - Parking",
     "The Hills DCP 2012",
     "https://www.thehills.nsw.gov.au/Building-and-Development/Development-Controls/Development-Control-Plans"),

    # Bayside
    ("bayside", "bayside-dcp-2022-part3", "Part 3 - Residential Development",
     "Bayside DCP 2022",
     "https://www.bayside.nsw.gov.au/planning-and-development/planning-our-city/controls"),
    ("bayside", "bayside-dcp-2022-part5", "Part 5 - General Controls",
     "Bayside DCP 2022",
     "https://www.bayside.nsw.gov.au/planning-and-development/planning-our-city/controls"),
    ("bayside", "s3-5-traffic-parking-access", "Section 3.5 - Traffic, Parking & Access",
     "Bayside DCP 2022",
     "https://www.bayside.nsw.gov.au/planning-and-development/planning-our-city/controls"),

    # Randwick
    ("randwick", "randwick-dcp-c1-low-density", "Part C1 - Low Density Residential",
     "Randwick DCP 2013",
     "https://www.randwick.nsw.gov.au/planning-and-building/planning-strategies-and-control/development-control-plan-dcp"),
    ("randwick", "b7-transport-traffic-parking-access", "Part B7 - Transport, Traffic, Parking & Access",
     "Randwick DCP 2013",
     "https://www.randwick.nsw.gov.au/planning-and-building/planning-strategies-and-control/development-control-plan-dcp"),

    # Sutherland Shire
    ("sutherland_shire", "ch36-vehicular-access-traffic-parking", "Chapter 36 - Vehicular Access, Traffic & Parking",
     "Sutherland Shire DCP 2015",
     "https://www.sutherlandshire.nsw.gov.au/plan-and-build/Planning-considerations/development-control-plan-dcp"),
    ("sutherland_shire", "landscaping-controls", "Landscaping Controls",
     "Sutherland Shire DCP 2015",
     "https://www.sutherlandshire.nsw.gov.au/plan-and-build/Planning-considerations/development-control-plan-dcp"),
    ("sutherland_shire", "sutherland-lep-2015-schedule-3", "LEP 2015 Schedule 3 Reference",
     "Sutherland Shire LEP 2015",
     "https://www.sutherlandshire.nsw.gov.au/plan-and-build/Planning-considerations/development-control-plan-dcp"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for council, chapter_key, chapter_label, dcp_name, hub_url in NEW_CHAPTERS:
        # Check if already exists
        cur.execute(
            "SELECT 1 FROM dcp_chapter_registry WHERE council = %s AND chapter_key = %s",
            (council, chapter_key),
        )
        if cur.fetchone():
            print(f"  SKIP (exists): [{council}] {chapter_key}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  WOULD INSERT: [{council}] {chapter_key} — {chapter_label}")
            inserted += 1
            continue

        cur.execute("""
            INSERT INTO dcp_chapter_registry
                (council, dcp_name, chapter_key, chapter_label, council_page_url,
                 is_active, needs_extraction, registration_status)
            VALUES (%s, %s, %s, %s, %s, TRUE, FALSE, 'registered')
        """, (council, dcp_name, chapter_key, chapter_label, hub_url))
        inserted += 1
        print(f"  INSERT: [{council}] {chapter_key} — {chapter_label}")

    if not args.dry_run and inserted > 0:
        conn.commit()

    print(f"\nInserted: {inserted}, Skipped: {skipped}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
