#!/usr/bin/env python3
"""
Insert SEPP override rules for Pattern Book pathway.

These are POLICY RULES based on NSW planning framework, NOT extracted from text.
Source: pd-pattern-book-sepp-framework.md (lines 199-205)

Override rules determine whether an exclusion can be bypassed with additional
assessments/certificates, or if DA is mandatory.

Usage:
    python scripts/insert_sepp_override_rules.py
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


# Override rules based on NSW planning framework
# Source: Resilience & Hazards SEPP (2021), Infrastructure SEPP (2008)
OVERRIDE_RULES = [
    # ====================================================================
    # OVERRIDABLE EXCLUSIONS (with required assessments/certificates)
    # ====================================================================
    {
        'requirement_category': 'override',
        'is_override': True,
        'exclusion_type': 'bushfire_prone',
        'override_condition': 'Bushfire Hazard Assessment (Planning for Bush Fire Protection 2019)',
        'applies_to': 'Pattern_Book',
        'notes': 'Pattern Book designs include BAL ratings. Approval by Council + Private Certifier. Excludes Blue Mountains/Wollondilly LGAs (no override).',
        'source_clause': 'Resilience & Hazards SEPP (2021) Part 4'
    },
    {
        'requirement_category': 'override',
        'is_override': True,
        'exclusion_type': 'flood_planning_area',
        'override_condition': 'Flood Impact Assessment + SES approval',
        'applies_to': 'Pattern_Book',
        'notes': 'Assessment must demonstrate development is suitable despite flood hazard.',
        'source_clause': 'Resilience & Hazards SEPP (2021) Part 3'
    },
    {
        'requirement_category': 'override',
        'is_override': True,
        'exclusion_type': 'acid_sulfate_soils',
        'override_condition': 'Acid Sulfate Soil Management Plan',
        'applies_to': 'Pattern_Book',
        'notes': 'Required for sites on ASS Map. Site compatibility certificate must be obtained BEFORE CDC application.',
        'source_clause': 'Infrastructure SEPP (2008) Clause 2.10'
    },
    {
        'requirement_category': 'override',
        'is_override': True,
        'exclusion_type': 'aircraft_noise',
        'override_condition': 'Site Compatibility Certificate (if within OLS or ANEF 25-35 contour)',
        'applies_to': 'Pattern_Book',
        'notes': 'Certificate verifies site compatible with Pattern Book design. ANEF >35 = no override.',
        'source_clause': 'Infrastructure SEPP (2008) Clause 2.9'
    },

    # ====================================================================
    # NON-OVERRIDABLE EXCLUSIONS (DA mandatory)
    # ====================================================================
    {
        'requirement_category': 'override',
        'is_override': False,
        'exclusion_type': 'heritage',
        'override_condition': None,
        'applies_to': 'Pattern_Book',
        'notes': 'Heritage items and HCAs cannot use Part 3BA CDC pathway. DA required under Housing SEPP standards.',
        'source_clause': 'Codes SEPP (2008) Part 3BA Clause 3BA.4 (exclusions)'
    },
    {
        'requirement_category': 'override',
        'is_override': False,
        'exclusion_type': 'unsewered',
        'override_condition': None,
        'applies_to': 'Pattern_Book',
        'notes': 'Land without sewer connection cannot use CDC pathway. DA required.',
        'source_clause': 'Codes SEPP (2008) Part 3BA Clause 3BA.4 (exclusions)'
    },
    {
        'requirement_category': 'override',
        'is_override': False,
        'exclusion_type': 'threatened_species',
        'override_condition': None,
        'applies_to': 'Pattern_Book',
        'notes': 'Sites with threatened species/critical habitat require DA with biodiversity assessment.',
        'source_clause': 'Biodiversity Conservation Act 2016'
    },
    {
        'requirement_category': 'override',
        'is_override': False,
        'exclusion_type': 'coastal_erosion',
        'override_condition': None,
        'applies_to': 'Pattern_Book',
        'notes': 'Coastal erosion zones require DA with coastal hazard assessment.',
        'source_clause': 'Coastal Management SEPP (2018)'
    },
    {
        'requirement_category': 'override',
        'is_override': False,
        'exclusion_type': 'protected_area',
        'override_condition': None,
        'applies_to': 'Pattern_Book',
        'notes': 'Conservation zones, national parks, and protected areas exclude CDC pathway.',
        'source_clause': 'Codes SEPP (2008) Part 3BA Clause 3BA.4 (exclusions)'
    },
]


def insert_override_rules():
    """Insert override rules to database."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Make provision_id nullable (override rules don't reference specific provisions)
    try:
        cur.execute("""
            ALTER TABLE sepp_structured_requirements
            ALTER COLUMN provision_id DROP NOT NULL
        """)
        conn.commit()
        print("Made provision_id nullable for policy-level override rules")
    except Exception as e:
        # Column might already be nullable
        conn.rollback()

    # Drop check_override constraint (doesn't make sense for policy-level rules)
    try:
        cur.execute("""
            ALTER TABLE sepp_structured_requirements
            DROP CONSTRAINT check_override
        """)
        conn.commit()
        print("Dropped check_override constraint")
    except Exception as e:
        # Constraint might already be dropped
        conn.rollback()

    # Check if override rules already exist
    cur.execute("SELECT COUNT(*) FROM sepp_structured_requirements WHERE requirement_category = 'override'")
    existing_count = cur.fetchone()[0]

    if existing_count > 0:
        print(f"WARNING: {existing_count} override rules already exist in database")
        response = input("Delete and re-insert? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            cur.close()
            conn.close()
            return

        # Delete existing override rules
        cur.execute("DELETE FROM sepp_structured_requirements WHERE requirement_category = 'override'")
        print(f"Deleted {existing_count} existing override rules")
        conn.commit()

    # Insert new override rules
    print("\nInserting override rules...")
    inserted = 0

    for rule in OVERRIDE_RULES:
        cur.execute("""
            INSERT INTO sepp_structured_requirements (
                requirement_category,
                is_override,
                exclusion_type,
                override_condition,
                applies_to,
                ambiguity_notes,
                source_clause,
                extraction_confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            rule['requirement_category'],
            rule['is_override'],
            rule['exclusion_type'],
            rule['override_condition'],
            rule['applies_to'],
            rule['notes'],
            rule['source_clause'],
            1.0  # Manual curation = 100% confidence
        ))

        override_status = "CAN override" if rule['is_override'] else "NO override"
        print(f"  [{inserted+1}] {rule['exclusion_type']}: {override_status}")
        if rule['override_condition']:
            print(f"      Condition: {rule['override_condition']}")

        inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nInserted {inserted} override rules")
    return inserted


def verify_insertion():
    """Verify override rules were inserted correctly."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Count by override status
    cur.execute("""
        SELECT is_override, COUNT(*)
        FROM sepp_structured_requirements
        WHERE requirement_category = 'override'
        GROUP BY is_override
    """)
    by_status = cur.fetchall()

    # Sample override rules
    cur.execute("""
        SELECT
            exclusion_type,
            is_override,
            override_condition,
            ambiguity_notes
        FROM sepp_structured_requirements
        WHERE requirement_category = 'override'
        ORDER BY is_override DESC, exclusion_type
    """)
    all_rules = cur.fetchall()

    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    print("\nBy override status:")
    for is_override, count in by_status:
        status = "CAN be overridden" if is_override else "NO override available"
        print(f"  {status}: {count}")

    print("\nAll override rules:")
    for exc_type, is_override, condition, notes in all_rules:
        override_status = "CAN OVERRIDE" if is_override else "NO OVERRIDE"
        print(f"\n  {exc_type}: {override_status}")
        if condition:
            print(f"    Condition: {condition}")
        if notes:
            print(f"    Notes: {notes}")

    cur.close()
    conn.close()


def main():
    print("=" * 70)
    print("SEPP OVERRIDE RULES INSERTION")
    print("=" * 70)
    print()
    print("Source: NSW Planning Framework (Resilience & Hazards SEPP, Infrastructure SEPP)")
    print("Method: Manual curation (policy rules, not extractable from text)")
    print()

    inserted = insert_override_rules()

    if inserted > 0:
        verify_insertion()


if __name__ == '__main__':
    main()
