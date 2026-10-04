#!/usr/bin/env python3
"""
Align orphan source_chapter_keys with existing dcp_chapter_registry entries,
and register genuinely new chapters.

Two operations:
  1. ALIAS: source_chapter_key in controls points to same PDF as an existing
     registry entry under a different key. Fix by updating the controls' key.
  2. REGISTER: source_chapter_key has no matching registry entry at all.
     Create a new registry entry (with URL where known, NULL where not).

Usage:
    python scripts/register_orphan_chapters.py --dry-run
    python scripts/register_orphan_chapters.py
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

# ── Alias mappings: orphan_key → existing_registry_key ──────────────────────
# These are the same PDF chapter under different names.
ALIASES = {
    # Canterbury-Bankstown
    ("canterbury_bankstown", "ch3-2-parking"): "chapter-3-2-parking",
    ("canterbury_bankstown", "chapter-5-1-bankstown-residential"): "cb-dcp-2023-ch5-1-bankstown",
    ("canterbury_bankstown", "chapter-5-2-canterbury-residential"): "cb-dcp-2023-ch5-2-canterbury",
    ("canterbury_bankstown", "cb-dcp-2023-ch5-1"): "cb-dcp-2023-ch5-1-bankstown",
    # Woollahra
    ("woollahra", "chapter-e1-parking-and-access"): "chapter-e1-parking-access",
    ("woollahra", "woollahra-dcp-2015-ch-b3"): "chapter-b3-general-development",
    # Penrith — part-d2-residential and d2-landscaping both reference the same Part D2 PDF
    ("penrith", "part-d2-residential"): "penrith-dcp-2014-part-d2",
    ("penrith", "d2-landscaping"): "penrith-dcp-2014-part-d2",
    # Campbelltown — multiple keys for the same Part 3
    ("campbelltown", "part-3-residential"): "campbelltown-dcp-part3-low-medium",
    ("campbelltown", "part-3-low-medium-density-residential"): "campbelltown-dcp-part3-low-medium",
    ("campbelltown", "campbelltown-scdcp-2015-part3"): "campbelltown-dcp-part3-low-medium",
    # Blacktown — part-3-residential is the same as part-c
    ("blacktown", "part-3-residential"): "blacktown-dcp-2015-part-c",
    # Waverley — sub-parts of the single DCP PDF
    ("waverley", "waverley-dcp-2022-part-c1"): "waverley-dcp-2022",
    ("waverley", "waverley-dcp-2022-part-c2"): "waverley-dcp-2022",
    # Cumberland — part-b-residential is same chapter
    ("cumberland", "part-b-residential"): "cumberland-dcp-part-b-residential",
    # Hornsby — part-3-residential is same chapter
    ("hornsby", "part-3-residential"): "hornsby-dcp-2024-part3-residential",
}

# ── New registrations: chapters that need new registry entries ───────────────
# Format: (council, chapter_key, dcp_name, chapter_label, council_url)
NEW_CHAPTERS = [
    # Blacktown
    ("blacktown", "part-4-secondary-dwellings", "Blacktown DCP 2015",
     "Part 4 — Secondary Dwellings",
     "https://www.blacktown.nsw.gov.au/files/assets/public/v/1/building-and-development/dcp/blacktown-development-control-plan-2015-part-d.pdf"),
    ("blacktown", "part-a-car-parking", "Blacktown DCP 2015",
     "Part A — Car Parking",
     "https://www.blacktown.nsw.gov.au/files/assets/public/v/1/building-and-development/dcp/blacktown-development-control-plan-2015-part-a.pdf"),
    # Campbelltown — Part 4 RFB/Mixed Use is a separate chapter
    ("campbelltown", "part-4-rfb-mixed-use", "Campbelltown (Sustainable City) DCP 2015",
     "Part 4 — RFB and Mixed Use",
     "https://www.campbelltown.nsw.gov.au/files/assets/public/v/2/building-and-planning/dcps/scdcp-2015/scdcp-2015-part-4.pdf"),
    # Penrith — C10 is a separate parking chapter
    ("penrith", "c10-transport-access-parking", "Penrith DCP 2014",
     "Part C10 — Transport, Access and Parking",
     "https://www.penrithcity.nsw.gov.au/images/documents/building-development/planning-zoning/planning-controls/Penrith_DCP_2014_Part_C10_Transport_Access_Parking.pdf"),
    # Georges River — Part 3 is a separate chapter
    ("georges_river", "part-3-general-planning-considerations", "Georges River DCP 2021",
     "Part 3 — General Planning Considerations",
     "https://www.georgesriver.nsw.gov.au/StGeorge/media/Documents/Development%20control%20plan/GRDCP-Part-3-General-Planning-Considerations.PDF"),
    # Hornsby — Part 1 General
    ("hornsby", "part-1-general", "Hornsby DCP 2024",
     "Part 1 — General Provisions",
     "https://www.hornsby.nsw.gov.au/__data/assets/pdf_file/0007/235519/Hornsby-DCP-2024-Part-1-General-Provisions.pdf"),
    # Liverpool
    ("liverpool", "part-1-car-parking-access", "Liverpool DCP 2008",
     "Part 1 — Car Parking and Access",
     "https://www.liverpool.nsw.gov.au/files/assets/public/v/1/hperm/planning/dcps/liverpool-dcp-2008-part-1.pdf"),
    ("liverpool", "part-2-residential", "Liverpool DCP 2008",
     "Part 2 — Residential",
     "https://www.liverpool.nsw.gov.au/files/assets/public/v/1/hperm/planning/dcps/liverpool-dcp-2008-part-2.pdf"),
    # Parramatta — Part 6
    ("parramatta", "part-6-traffic-and-transport", "Parramatta DCP 2023",
     "Part 6 — Traffic and Transport",
     None),  # Parramatta DCP is a single consolidated PDF
    # Waverley — landscaping and transport are sub-sections of the main DCP
    ("waverley", "landscaping-controls", "Waverley DCP 2012",
     "Landscaping Controls (Parts B2-B4)",
     None),  # Sub-section of waverley-dcp-2022
    ("waverley", "part-b7-transport", "Waverley DCP 2012",
     "Part B7 — Transport",
     None),  # Sub-section of waverley-dcp-2022
    # Northern Beaches
    ("northern_beaches", "warringah-appendix-1-car-parking", "Warringah DCP 2011",
     "Appendix 1 — Car Parking",
     None),
    ("northern_beaches", "part-b-development-controls", "Warringah DCP 2011",
     "Part B — Development Controls",
     None),
    ("northern_beaches", "warringah-dcp-2011-part-b", "Warringah DCP 2011",
     "Part B — Development Controls (alias)",
     None),
    # Inner West: the three former-council chapters once listed here (registered 2026-05-14 as
    # council='inner_west', ids 747-749) were removed 2026-10-04 (DQ-128). Each duplicated a chapter
    # already registered under its former council, and the registry council is copied into
    # regulatory_provisions.source_council, so 11 served rows were filed under the wrong slug.
    # A former council's plan is registered under the former council's own slug.
    # Bayside
    ("bayside", "bayside-dcp-2022-part3", "Bayside DCP 2022",
     "Part 3 — General Controls", None),
    ("bayside", "bayside-dcp-2022-part5", "Bayside DCP 2022",
     "Part 5 — Residential Controls", None),
    ("bayside", "s3-5-traffic-parking-access", "Bayside DCP 2022",
     "Section 3.5 — Traffic, Parking and Access", None),
    # Burwood
    ("burwood", "part-4-residential", "Burwood DCP",
     "Part 4 — Residential", None),
    ("burwood", "s4-landscaping", "Burwood DCP",
     "Section 4 — Landscaping", None),
    ("burwood", "s4-table-4-parking", "Burwood DCP",
     "Section 4 Table 4 — Parking", None),
    # Camden
    ("camden", "part-4-residential", "Camden DCP 2019",
     "Part 4 — Residential Dwelling Controls", None),
    ("camden", "s4-2-6-landscaping", "Camden DCP 2019",
     "Section 4.2.6 — Landscaping", None),
    # Canada Bay
    ("canada_bay", "landscaping-controls", "Canada Bay DCP 2025",
     "Landscaping Controls (Parts E & F)", None),
    ("canada_bay", "part-c-table-cb-parking", "Canada Bay DCP 2020",
     "Part C Table C-B — Parking", None),
    ("canada_bay", "part-e-single-dwellings", "Canada Bay DCP 2025",
     "Part E — Single Dwellings", None),
    # Fairfield
    ("fairfield", "chapter-5-dwelling-houses", "Fairfield City Wide DCP 2024",
     "Chapter 5 — Dwelling Houses", None),
    ("fairfield", "landscaping-controls", "Fairfield City Wide DCP 2024",
     "Landscaping Controls", None),
    ("fairfield", "parking-controls", "Fairfield City Wide DCP 2024",
     "Parking Controls", None),
    # Randwick
    ("randwick", "b7-transport-traffic-parking-access", "Randwick DCP 2013",
     "Section B7 — Transport, Traffic, Parking and Access", None),
    ("randwick", "randwick-dcp-c1-low-density", "Randwick DCP 2013",
     "Part C1 — Low Density Residential", None),
    # Ryde
    ("ryde", "part-3-3-dwelling-houses", "Ryde DCP 2014",
     "Part 3.3 — Dwelling Houses", None),
    ("ryde", "part-9.3-parking", "Ryde DCP 2014",
     "Part 9.3 — Parking", None),
    # Strathfield
    ("strathfield", "landscaping-controls", "Strathfield DCP 2005",
     "Landscaping Controls", None),
    ("strathfield", "parking-controls", "Strathfield DCP 2005",
     "Parking Controls", None),
    ("strathfield", "part-a-dwelling-houses", "Strathfield DCP 2005",
     "Part A — Dwelling Houses", None),
    # Sutherland Shire
    ("sutherland_shire", "ch36-vehicular-access-traffic-parking", "Sutherland Shire DCP 2015",
     "Chapter 36 — Vehicular Access, Traffic and Parking", None),
    ("sutherland_shire", "landscaping-controls", "Sutherland Shire DCP 2015",
     "Landscaping Controls", None),
    ("sutherland_shire", "sutherland-lep-2015-schedule-3", "Sutherland Shire LEP 2015",
     "Schedule 3 — Landscaped Area", None),
    # The Hills
    ("the_hills", "part-b-section-2-residential", "The Hills DCP 2012",
     "Part B Section 2 — Residential", None),
    ("the_hills_shire", "part-c-s1-parking", "The Hills DCP 2012",
     "Part C Section 1 — Parking", None),
    # Cumberland — missing entry
    ("cumberland", "part-g3-traffic-parking", "Cumberland DCP 2021",
     "Part G3 — Traffic and Parking", None),
]


def former_council_owner(cur, council: str, dcp_name: str):
    """The former council whose plan `dcp_name` is, when `council` is the merged council it rolled into.

    Rolls up through lga_registry.parent_lga (never `former_council`, which exists for Inner West
    only). Returns the former council's slug, or None when the plan is the council's own.
    """
    if not council or not dcp_name:
        return None
    cur.execute("""
        SELECT slug, display_name FROM lga_registry
        WHERE parent_lga = %s AND is_active = TRUE
    """, (council,))
    name = dcp_name.strip().lower()
    for row in cur.fetchall():
        slug, display = (row["slug"], row["display_name"]) if isinstance(row, dict) else row
        if display and name.startswith(display.strip().lower() + " "):
            return slug
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now(timezone.utc)

    # ── Step 1: Apply alias mappings ────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Alias alignment")
    print("=" * 60)

    alias_count = 0
    for (council, old_key), new_key in ALIASES.items():
        # Verify the target key exists in registry
        cur.execute("""
            SELECT id FROM dcp_chapter_registry
            WHERE council = %s AND chapter_key = %s AND registration_status = 'confirmed'
        """, (council, new_key))
        if not cur.fetchone():
            print(f"  SKIP (target not in registry): {council} | {old_key} -> {new_key}")
            continue

        if args.dry_run:
            cur.execute("""
                SELECT COUNT(*) FROM dcp_setback_controls
                WHERE lga = %s AND source_chapter_key = %s AND is_current = TRUE
            """, (council, old_key))
            count = cur.fetchone()["count"]
            print(f"  DRY-RUN: {council} | {old_key} -> {new_key} ({count} rows)")
        else:
            cur.execute("""
                UPDATE dcp_setback_controls
                SET source_chapter_key = %s
                WHERE lga = %s AND source_chapter_key = %s AND is_current = TRUE
            """, (new_key, council, old_key))
            updated = cur.rowcount
            print(f"  ALIAS: {council} | {old_key} -> {new_key} ({updated} rows updated)")
            alias_count += updated

    if not args.dry_run:
        conn.commit()

    # ── Step 2: Register new chapters ───────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("STEP 2: Register new chapters")
    print("=" * 60)

    registered = 0
    skipped = 0

    for council, key, dcp_name, label, url in NEW_CHAPTERS:
        # Check if already exists
        cur.execute("""
            SELECT id FROM dcp_chapter_registry
            WHERE council = %s AND chapter_key = %s
        """, (council, key))
        if cur.fetchone():
            print(f"  SKIP (exists): {council} | {key}")
            skipped += 1
            continue

        owner = former_council_owner(cur, council, dcp_name)
        if owner:
            print(f"  REFUSE: {council} | {key} -- '{dcp_name}' is {owner}'s plan; "
                  f"register it under '{owner}' (DQ-128)")
            skipped += 1
            continue

        # Check if this key was just aliased away (no longer orphaned)
        if (council, key) in ALIASES:
            print(f"  SKIP (aliased): {council} | {key}")
            skipped += 1
            continue

        if args.dry_run:
            url_status = "has URL" if url else "NO URL"
            print(f"  DRY-RUN: {council} | {key} ({url_status})")
        else:
            cur.execute("""
                INSERT INTO dcp_chapter_registry
                  (council, dcp_name, chapter_key, chapter_label, council_url,
                   registration_status, is_active, needs_extraction, created_at)
                VALUES (%s, %s, %s, %s, %s, 'confirmed', TRUE, FALSE, %s)
            """, (council, dcp_name, key, label, url, now))
            url_status = "has URL" if url else "NO URL — needs manual URL"
            print(f"  REGISTER: {council} | {key} ({url_status})")
            registered += 1

    if not args.dry_run:
        conn.commit()

    # ── Summary ─────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    if args.dry_run:
        print("  (dry run — no changes made)")
    else:
        print(f"  Aliases applied : {alias_count} control rows re-keyed")
        print(f"  Chapters registered : {registered}")
        print(f"  Skipped (existing/aliased) : {skipped}")

    # Show remaining NULL-URL chapters
    cur.execute("""
        SELECT council, chapter_key FROM dcp_chapter_registry
        WHERE council_url IS NULL AND registration_status = 'confirmed'
          AND is_active = TRUE
        ORDER BY council, chapter_key
    """)
    null_urls = cur.fetchall()
    if null_urls:
        print(f"\n  Chapters needing PDF URLs ({len(null_urls)}):")
        for r in null_urls:
            print(f"    {r['council']:25s} | {r['chapter_key']}")

    conn.close()


if __name__ == "__main__":
    main()
