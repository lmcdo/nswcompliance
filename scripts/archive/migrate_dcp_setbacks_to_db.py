#!/usr/bin/env python3
"""
Phase 2: Migrate DCP_SETBACKS hardcoded dict → dcp_general_requirements DB rows.

Idempotent: ON CONFLICT DO NOTHING — safe to re-run.
Use --dry-run to preview without writing.

14 rows total:
  marrickville  7  (front, side x3, rear, secondary x2)
  leichhardt    3  (front, side, rear)
  ashfield      4  (front, side, rear, garage)
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
import psycopg2

# ---------------------------------------------------------------------------
# Source data — must match DCP_SETBACKS exactly (including control_type field)
# ---------------------------------------------------------------------------

ROWS = [
    # ------------------------------------------------------------------
    # MARRICKVILLE — Marrickville DCP 2011, Part 4.1
    # ------------------------------------------------------------------
    {
        "former_council": "Marrickville",
        "category": "setback_front",
        "subcategory": "Front",
        "control_type": "site_derived",
        "requirement_text": "Match prevailing setback",
        "value_numeric": None,
        "unit": None,
        "conditional_text": "Consistent with adjoining development or the dominant setback found along the street. No fixed number — determined by site context.",
        "lep_clause": "C10(i)",
        "part_number": "Part 4.1",
        "part_name": "Marrickville DCP 2011",
        "section_reference": "O14, C10-C11",
        "applicable_zones": ["R1", "R2"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Marrickville",
        "category": "setback_side",
        "subcategory": "Side - 1 storey (lot >= 8 m wide)",
        "control_type": "prescribed",
        "requirement_text": "900 mm minimum",
        "value_numeric": 0.9,
        "unit": "m",
        "conditional_text": "Lots less than 8 m wide: at Council's discretion — visual impact and solar access determine setback.",
        "lep_clause": "C10(ii)",
        "part_number": "Part 4.1",
        "part_name": "Marrickville DCP 2011",
        "section_reference": "O14, C10-C11",
        "applicable_zones": ["R1", "R2"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Marrickville",
        "category": "setback_side",
        "subcategory": "Side - 2 storey (lot >= 8 m wide)",
        "control_type": "prescribed",
        "requirement_text": "1.5 m minimum",
        "value_numeric": 1.5,
        "unit": "m",
        "conditional_text": "",
        "lep_clause": "C10(ii)",
        "part_number": "Part 4.1",
        "part_name": "Marrickville DCP 2011",
        "section_reference": "O14, C10-C11",
        "applicable_zones": ["R1", "R2"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Marrickville",
        "category": "setback_side",
        "subcategory": "Side - 3 storey (lot >= 8 m wide)",
        "control_type": "prescribed",
        "requirement_text": "2.5 m minimum",
        "value_numeric": 2.5,
        "unit": "m",
        "conditional_text": "",
        "lep_clause": "C10(ii)",
        "part_number": "Part 4.1",
        "part_name": "Marrickville DCP 2011",
        "section_reference": "O14, C10-C11",
        "applicable_zones": ["R1", "R2"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Marrickville",
        "category": "setback_rear",
        "subcategory": "Rear",
        "control_type": "site_derived",
        "requirement_text": "Merit-based",
        "value_numeric": None,
        "unit": None,
        "conditional_text": "Assessed on merit — adverse amenity impacts and adequate open space are primary considerations. No fixed number.",
        "lep_clause": "C10(iii)",
        "part_number": "Part 4.1",
        "part_name": "Marrickville DCP 2011",
        "section_reference": "O14, C10-C11",
        "applicable_zones": ["R1", "R2"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Marrickville",
        "category": "setbacks",
        "subcategory": "Secondary dwelling - side (detached, rear)",
        "control_type": "prescribed",
        "requirement_text": "1.5 m minimum",
        "value_numeric": 1.5,
        "unit": "m",
        "conditional_text": "Detached secondary dwellings at rear of lot.",
        "lep_clause": "C11(iii)(b)",
        "part_number": "Part 4.1",
        "part_name": "Marrickville DCP 2011",
        "section_reference": "O14, C10-C11",
        "applicable_zones": ["R1", "R2"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Marrickville",
        "category": "setbacks",
        "subcategory": "Secondary dwelling - separation",
        "control_type": "prescribed",
        "requirement_text": "4.0 m minimum",
        "value_numeric": 4.0,
        "unit": "m",
        "conditional_text": "Minimum separation between principal and detached secondary dwelling.",
        "lep_clause": "C11",
        "part_number": "Part 4.1",
        "part_name": "Marrickville DCP 2011",
        "section_reference": "O14, C10-C11",
        "applicable_zones": ["R1", "R2"],
        "evidence_type": "manual",
    },
    # ------------------------------------------------------------------
    # LEICHHARDT — Leichhardt DCP 2013, Part C3.2
    # ------------------------------------------------------------------
    {
        "former_council": "Leichhardt",
        "category": "setback_front",
        "subcategory": "Front",
        "control_type": "site_derived",
        "requirement_text": "Building Location Zone - prevailing character",
        "value_numeric": None,
        "unit": None,
        "conditional_text": "BLZ is determined by where buildings sit on adjoining properties. No fixed number — derived by planner from site visit.",
        "lep_clause": "C4",
        "part_number": "Part C3.2",
        "part_name": "Leichhardt DCP 2013",
        "section_reference": "C4, C7",
        "applicable_zones": ["ALL"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Leichhardt",
        "category": "setback_side",
        "subcategory": "Side",
        "control_type": "site_derived",
        "requirement_text": "Height-dependent graph (60 degree angle from wall)",
        "value_numeric": None,
        "unit": None,
        "conditional_text": "Setback scales continuously with wall height per Figure C129. Approx 1.0 m at 4 m wall height, 1.5 m at 5.5 m. Not a fixed minimum — derived from the graph.",
        "lep_clause": "C7",
        "part_number": "Part C3.2",
        "part_name": "Leichhardt DCP 2013",
        "section_reference": "C4, C7",
        "applicable_zones": ["ALL"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Leichhardt",
        "category": "setback_rear",
        "subcategory": "Rear",
        "control_type": "site_derived",
        "requirement_text": "Building Location Zone - prevailing character",
        "value_numeric": None,
        "unit": None,
        "conditional_text": "Consistent with rear building line of adjoining properties. No fixed number.",
        "lep_clause": "C4",
        "part_number": "Part C3.2",
        "part_name": "Leichhardt DCP 2013",
        "section_reference": "C4, C7",
        "applicable_zones": ["ALL"],
        "evidence_type": "manual",
    },
    # ------------------------------------------------------------------
    # ASHFIELD — Inner West DCP 2016 (Ashfield precinct), Chapter F
    # ------------------------------------------------------------------
    {
        "former_council": "Ashfield",
        "category": "setback_front",
        "subcategory": "Front",
        "control_type": "site_derived",
        "requirement_text": "On merits - no fixed minimum",
        "value_numeric": None,
        "unit": None,
        "conditional_text": "Performance criteria based. Site analysis and streetscape character required. No pre-determined number.",
        "lep_clause": "DS1.1",
        "part_number": "Chapter F",
        "part_name": "Inner West DCP 2016 (Ashfield precinct)",
        "section_reference": "Chapter F DS",
        "applicable_zones": ["R1", "R2", "R3"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Ashfield",
        "category": "setback_side",
        "subcategory": "Side",
        "control_type": "prescribed",
        "requirement_text": "0.9 m minimum",
        "value_numeric": 0.9,
        "unit": "m",
        "conditional_text": "Minimum side setback for dwelling houses. Council may require greater setback under performance criteria.",
        "lep_clause": "Chapter F DS",
        "part_number": "Chapter F",
        "part_name": "Inner West DCP 2016 (Ashfield precinct)",
        "section_reference": "Chapter F DS",
        "applicable_zones": ["R1", "R2", "R3"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Ashfield",
        "category": "setback_rear",
        "subcategory": "Rear",
        "control_type": "site_derived",
        "requirement_text": "On merits",
        "value_numeric": None,
        "unit": None,
        "conditional_text": "Must include adequate green space between adjoining properties. Assessed on merit — no fixed number.",
        "lep_clause": "DS13.3",
        "part_number": "Chapter F",
        "part_name": "Inner West DCP 2016 (Ashfield precinct)",
        "section_reference": "Chapter F DS",
        "applicable_zones": ["R1", "R2", "R3"],
        "evidence_type": "manual",
    },
    {
        "former_council": "Ashfield",
        "category": "setbacks",
        "subcategory": "Garage / carport (rear lane access)",
        "control_type": "prescribed",
        "requirement_text": "1.0 m from rear boundary",
        "value_numeric": 1.0,
        "unit": "m",
        "conditional_text": "Minimum to allow sight lines for manoeuvring.",
        "lep_clause": "DS6.5",
        "part_number": "Chapter F",
        "part_name": "Inner West DCP 2016 (Ashfield precinct)",
        "section_reference": "Chapter F DS",
        "applicable_zones": ["R1", "R2", "R3"],
        "evidence_type": "manual",
    },
]


INSERT_SQL = """
    INSERT INTO dcp_general_requirements (
        lga, former_council, category, subcategory, control_type,
        requirement_text, value_numeric, unit, conditional_text,
        lep_clause, part_number, part_name, section_reference,
        applicable_zones, evidence_type
    ) VALUES (
        %(lga)s, %(former_council)s, %(category)s, %(subcategory)s, %(control_type)s,
        %(requirement_text)s, %(value_numeric)s, %(unit)s, %(conditional_text)s,
        %(lep_clause)s, %(part_number)s, %(part_name)s, %(section_reference)s,
        %(applicable_zones)s, %(evidence_type)s
    )
    ON CONFLICT (former_council, category, subcategory, evidence_type)
    WHERE evidence_type = 'manual'
    DO NOTHING
"""


def run(dry_run: bool = False) -> None:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    # Inner West amalgamated 2016 — all three former councils → same LGA
    _LGA_FOR_COUNCIL = {
        "Marrickville": "Inner West Council",
        "Leichhardt": "Inner West Council",
        "Ashfield": "Inner West Council",
    }

    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating {len(ROWS)} DCP setback rows...")
    inserted = 0
    skipped = 0

    for row in ROWS:
        row = {**row, "lga": _LGA_FOR_COUNCIL.get(row["former_council"], row["former_council"])}
        if dry_run:
            print(f"  WOULD INSERT: {row['former_council']} / {row['category']} / {row['subcategory']}")
            continue

        cur.execute(INSERT_SQL, row)
        if cur.rowcount:
            inserted += 1
            print(f"  inserted: {row['former_council']} / {row['category']} / {row['subcategory']}")
        else:
            skipped += 1
            print(f"  skipped (already exists): {row['former_council']} / {row['category']} / {row['subcategory']}")

    if not dry_run:
        conn.commit()
        print(f"\nDone. inserted={inserted} skipped={skipped}")

        # Verify
        cur.execute(
            "SELECT former_council, COUNT(*) FROM dcp_general_requirements "
            "WHERE evidence_type = 'manual' "
            "GROUP BY former_council ORDER BY former_council"
        )
        print("\nManual setback rows by council:")
        for fc, cnt in cur.fetchall():
            print(f"  {fc}: {cnt}")

        cur.execute(
            "SELECT COUNT(*) FROM dcp_general_requirements WHERE evidence_type = 'manual'"
        )
        total = cur.fetchone()[0]
        assert total >= 14, f"FAIL: expected >= 14 manual rows, got {total}"
        print(f"\nTotal manual rows: {total} (expected >= 14)")
    else:
        print(f"\n[DRY RUN] Would insert up to {len(ROWS)} rows. Re-run without --dry-run to apply.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
