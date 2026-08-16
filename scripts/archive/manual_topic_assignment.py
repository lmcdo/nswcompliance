#!/usr/bin/env python3
"""
Manual topic assignment for remaining None topic provisions in Leichhardt DCP.

Based on manual review of provision content.

Usage:
    python scripts/manual_topic_assignment.py --dry-run  # Preview
    python scripts/manual_topic_assignment.py            # Apply
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Manual assignments based on content review
# Format: provision_id -> topic

MANUAL_ASSIGNMENTS = {
    # ========================================================================
    # Part C Section 1 (39 provisions)
    # ========================================================================

    # Urban design principles
    79536: 'building_design',  # Legible places, landmarks, paths

    # Structural/building reports
    79554: 'building_design',  # Structural condition report
    79561: 'building_design',  # Structural condition report for heritage item
    79591: 'building_design',  # Building typologies appendix reference
    79618: 'building_form',    # Corner sites - visual prominence
    79619: 'building_form',    # Corner sites - address street frontages
    79576: 'building_design',  # (Already assigned in earlier fix)

    # Development process/admin
    79569: 'general',          # Pre-DA advice
    79739: 'general',          # Plan of Management requirements
    79827: 'general',          # Monitoring and review
    79875: 'density',          # Floor space GFA calculation
    79934: 'general',          # Development application property
    79971: 'general',          # EPA s4.15 considerations
    79989: 'general',          # Procedural review
    79991: 'general',          # Appeal processes
    80004: 'general',          # Amenity definition (glossary)
    80035: 'general',          # Location list (amenities)

    # Subdivision/streets
    79634: 'access',           # Street patterns, grid, cul-de-sacs

    # Contamination/environmental
    79663: 'contamination',    # Site investigation stage 1
    79665: 'contamination',    # Site audit note
    79696: 'contamination',    # Site audit statement
    79712: 'contamination',    # Plant/machinery vibrations
    79717: 'contamination',    # Volatile emissions records
    79718: 'contamination',    # Soil vapour extraction
    79730: 'contamination',    # Fill material sampling

    # Safety/CPTED
    79742: 'safety',           # Police partnership
    79746: 'safety',           # Well-lit, safe spaces
    79973: 'safety',           # Danger assessment factors
    79981: 'safety',           # Termite infestation (building safety)

    # Accessibility/housing
    79770: 'access',           # Adaptable housing (accessibility)
    79797: 'access',           # Turning areas for vehicles

    # Landscaping
    79911: 'landscaping',      # Native plants
    80112: 'landscaping',      # Green/living walls

    # Commercial/mixed use zones
    79926: 'mixed_use',        # B1/B2 zone < 3000sqm
    79929: 'mixed_use',        # B1/B2 zone >= 3000sqm

    # Public domain/structures
    80058: 'building_design',  # Awnings, balconies in public domain
    80061: 'building_design',  # Maintenance/liability for structures
    80072: 'access',           # Encroachments on roads
    80073: 'access',           # Public domain structures reference
    80074: 'access',           # Laneway provisions

    # ========================================================================
    # Part G - Site Specific (67 provisions)
    # Most are site context/descriptions - assign 'site_specific'
    # ========================================================================

    # Introductory/administrative for Part G
    80370: 'general',          # Intro to site-specific provisions
    80371: 'general',          # Section structure explanation
    80372: 'general',          # Previous DCP sites heading
    80373: 'general',          # DCP repeal statement

    # Site location references (these are context, not controls)
    80375: 'site_specific',    # Area 2 map reference
    80384: 'site_specific',    # Area 3 map reference
    80396: 'site_specific',    # Area 1 map reference
    80412: 'site_specific',    # Area 4 map reference
    80476: 'site_specific',    # Area 5 map reference
    80564: 'site_specific',    # Area 7 map reference
    80635: 'site_specific',    # Area 7 map reference
    80696: 'site_specific',    # Area 8 map reference
    80749: 'site_specific',    # Area 9 map reference
    80791: 'site_specific',    # Area 10/Chester St reference
    80861: 'site_specific',    # Area 11 map reference

    # Site descriptions
    80389: 'landscaping',      # Trees/vegetation on site
    80401: 'environmental',    # Bent-Wing Bats (threatened species)
    80432: 'site_specific',    # Address list
    80477: 'site_specific',    # Site identification (Terry St)
    80478: 'site_specific',    # Site area description
    80481: 'site_specific',    # Urban study background
    80565: 'site_specific',    # Johnston St site identification
    80636: 'site_specific',    # Allen St site identification
    80697: 'site_specific',    # Norton St site identification
    80750: 'site_specific',    # Marion St site identification
    80752: 'site_specific',    # Council resolution background
    80756: 'site_specific',    # Distinctive neighbourhood reference
    80786: 'site_specific',    # Chester St intro
    80792: 'site_specific',    # Site area and location
    80859: 'site_specific',    # Lonsdale/Brenan St site ID
    80860: 'site_specific',    # Site area description
    80866: 'site_specific',    # Distinctive neighbourhood reference

    # Section headings
    80475: 'site_specific',    # Section 6 heading (Anka site)
    80630: 'site_specific',    # Section 8 heading (Allen St)
    80858: 'site_specific',    # Section 12 heading (Lonsdale St)

    # Escarpment/geological
    80448: 'environmental',    # Escarpment excavation restriction

    # Roads/infrastructure
    80491: 'access',           # New road construction
    80493: 'access',           # Intersection construction

    # Sustainability objectives
    80550: 'sustainability',   # High sustainability standard
    80621: 'sustainability',   # High sustainability standard
    80677: 'sustainability',   # Sustainability + Greenstar

    # Building/development considerations
    80558: 'building_design',  # Development considerations
    80574: 'building_design',  # Amenity/appearance of Johnston St
    80589: 'building_form',    # Building envelopes
    80590: 'building_form',    # Building envelopes
    80631: 'general',          # Site-specific controls intro
    80634: 'general',          # DCP inconsistency clause
    80660: 'building_design',  # Activate street with living spaces
    80693: 'general',          # Site-specific controls intro
    80695: 'general',          # DCP inconsistency clause
    80746: 'general',          # Site-specific controls intro
    80764: 'building_design',  # Facade articulation
    80772: 'building_design',  # Glazing, windows, balustrades
    80789: 'general',          # SEPP relationship
    80790: 'general',          # SEPP inconsistency clause
    80795: 'general',          # Section heading
    80797: 'general',          # DCP inconsistency clause
    80864: 'general',          # DCP inconsistency clause
    80869: 'site_specific',    # Lot amalgamation pattern

    # Residential/amenity (boarding house provisions)
    80809: 'residential',      # Bedroom GFA requirements
    80810: 'residential',      # Bedroom space breakdown
    80811: 'residential',      # Kitchenette requirements
    80813: 'residential',      # Communal kitchen area
    80815: 'residential',      # Communal kitchen provisions
    80816: 'residential',      # Storage requirements
    80827: 'residential',      # Laundry facilities

    # Noise
    80890: 'residential',      # Noise impacts for residents

    # ========================================================================
    # unknown part (17 provisions) - These are Part A introductory
    # ========================================================================
    79365: 'general',          # Figure reference (TOC)
    79366: 'general',          # Plan name heading
    79367: 'general',          # Plan adoption date
    79368: 'general',          # Plans repealed
    79371: 'general',          # Application of DCP
    79372: 'general',          # Transitional provisions
    79376: 'general',          # Standards reference
    79377: 'general',          # SEPP reference
    79379: 'general',          # Inner West LEP reference
    79381: 'general',          # LEP/SEPP reference
    79386: 'general',          # Structure heading
    79387: 'general',          # DCP complements LEP
    79388: 'general',          # Structure explanation
    79391: 'general',          # Assessment against DCP
    79395: 'general',          # DCP review requirements
    79400: 'general',          # Legislative amendments note
    79402: 'general',          # URL reference
}


def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def apply_manual_assignments(dry_run=True):
    """Apply manual topic assignments"""
    print("=" * 80)
    if dry_run:
        print("MANUAL TOPIC ASSIGNMENT - DRY RUN")
    else:
        print("MANUAL TOPIC ASSIGNMENT - APPLYING CHANGES")
    print("=" * 80)

    conn = get_db_connection()

    # First verify these IDs exist and have None topic
    with conn.cursor() as cur:
        ids_list = list(MANUAL_ASSIGNMENTS.keys())
        placeholders = ','.join(['%s'] * len(ids_list))
        cur.execute(f"""
            SELECT id, v2_topic, v2_dcp_part
            FROM regulatory_provisions
            WHERE id IN ({placeholders})
              AND document_id ILIKE '%%Leichhardt%%'
              AND is_current = TRUE
        """, ids_list)
        existing = {r['id']: r for r in cur.fetchall()}

    print(f"\nFound {len(existing)}/{len(MANUAL_ASSIGNMENTS)} provisions in database")

    # Check which already have topics
    already_assigned = []
    to_assign = []
    not_found = []

    for pid, topic in MANUAL_ASSIGNMENTS.items():
        if pid not in existing:
            not_found.append(pid)
        elif existing[pid]['v2_topic'] is not None:
            already_assigned.append((pid, existing[pid]['v2_topic'], topic))
        else:
            to_assign.append((pid, topic, existing[pid]['v2_dcp_part']))

    print(f"To assign: {len(to_assign)}")
    print(f"Already have topics: {len(already_assigned)}")
    print(f"Not found: {len(not_found)}")

    if not_found:
        print(f"\nWARNING: IDs not found: {not_found[:10]}...")

    if already_assigned:
        print(f"\nAlready assigned (will skip):")
        for pid, current, proposed in already_assigned[:5]:
            print(f"  ID {pid}: has '{current}', proposed '{proposed}'")

    # Group by topic for summary
    from collections import defaultdict
    by_topic = defaultdict(list)
    for pid, topic, part in to_assign:
        by_topic[topic].append((pid, part))

    print(f"\nAssignments by topic:")
    for topic, items in sorted(by_topic.items(), key=lambda x: -len(x[1])):
        print(f"  {topic}: {len(items)}")

    if not dry_run and to_assign:
        print("\nApplying changes...")

        with conn.cursor() as cur:
            for topic, items in by_topic.items():
                ids = [pid for pid, _ in items]
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id IN ({placeholders})
                      AND document_id ILIKE '%%Leichhardt%%'
                """, [topic] + ids)
                print(f"  Updated {cur.rowcount} provisions to '{topic}'")

        conn.commit()
        print("\n[OK] Changes applied")

        # Verify
        with conn.cursor() as cur:
            cur.execute("""
                SELECT v2_dcp_part, COUNT(*) as total,
                       COUNT(*) FILTER (WHERE v2_topic IS NULL) as none_count
                FROM regulatory_provisions
                WHERE document_id ILIKE '%%Leichhardt%%'
                  AND is_current = TRUE
                GROUP BY v2_dcp_part
                ORDER BY v2_dcp_part
            """)
            print("\nPost-fix None counts:")
            for r in cur.fetchall():
                pct = r['none_count'] / r['total'] * 100 if r['total'] > 0 else 0
                print(f"  {r['v2_dcp_part']}: {r['none_count']}/{r['total']} ({pct:.1f}%)")

    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    apply_manual_assignments(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
