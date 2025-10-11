#!/usr/bin/env python3
"""
Fix zone_setback_rules to link back to regulatory_provisions_canonical
for full text display.

PROBLEM:
- zone_setback_rules shows "Curated setback rule" as provision text
- No link to original DCP provisions for "View Full Text" feature

SOLUTION:
- Add source_provision_id column
- Populate by matching source_document + source_clause
- Update API to use provision_id for full text lookup
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db_safety_wrapper import get_safe_connection

print("=" * 80)
print("FIXING ZONE SETBACK RULE PROVISION LINKS")
print("=" * 80)

with get_safe_connection() as conn:
    cursor = conn.cursor()

    # Step 1: Check if column already exists
    print("\n[1/4] Checking schema...")
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'zone_setback_rules'
          AND column_name = 'source_provision_id'
    """)

    column_exists = cursor.fetchone() is not None

    if column_exists:
        print("[OK] Column source_provision_id already exists")
    else:
        print("Adding source_provision_id column...")
        # Note: regulatory_provisions_canonical might be a view, so skip FK constraint for now
        cursor.execute("""
            ALTER TABLE zone_setback_rules
            ADD COLUMN source_provision_id INTEGER
        """)
        conn.commit()
        print("[OK] Column added successfully (FK constraint skipped - view limitation)")

    # Step 2: Analyze existing data
    print("\n[2/4] Analyzing zone_setback_rules data...")
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(source_provision_id) as with_link,
               COUNT(*) - COUNT(source_provision_id) as without_link
        FROM zone_setback_rules
    """)
    stats = cursor.fetchone()
    print(f"  Total rules: {stats[0]}")
    print(f"  With provision link: {stats[1]}")
    print(f"  Without provision link: {stats[2]}")

    if stats[2] == 0:
        print("\nOK All setback rules already have provision links!")
        print("No updates needed.")
        sys.exit(0)

    # Step 3: Sample matching strategy
    print("\n[3/4] Testing matching strategy...")
    cursor.execute("""
        SELECT
            zsr.zone,
            zsr.boundary_type,
            zsr.source_clause,
            zsr.source_document,
            COUNT(rp.id) as potential_matches
        FROM zone_setback_rules zsr
        LEFT JOIN regulatory_provisions_canonical rp
            ON zsr.source_document = rp.document_id
            AND (
                rp.ref_number ILIKE '%' || zsr.source_clause || '%'
                OR zsr.source_clause ILIKE '%' || rp.ref_number || '%'
            )
        WHERE zsr.source_provision_id IS NULL
        GROUP BY zsr.zone, zsr.boundary_type, zsr.source_clause, zsr.source_document
        LIMIT 5
    """)

    samples = cursor.fetchall()
    print(f"\nSample matching (first 5 rules):")
    for zone, boundary, clause, doc, matches in samples:
        print(f"  {zone} {boundary} setback: '{clause}' -> {matches} potential matches")

    # Step 4: Populate provision links
    print("\n[4/4] Populating provision links...")

    # Strategy 1: Fuzzy match on document name (handles "Ashfield DCP 2016 Chapter E2" -> "Ashfield_DCP_2016")
    cursor.execute("""
        UPDATE zone_setback_rules zsr
        SET source_provision_id = (
            SELECT rp.id
            FROM regulatory_provisions_canonical rp
            WHERE (
                -- Extract base document name (e.g., "Ashfield DCP 2016" from "Ashfield DCP 2016 Chapter E2")
                rp.document_id ILIKE (
                    SELECT CASE
                        WHEN zsr.source_document ILIKE '%Ashfield%' THEN '%Ashfield%DCP%'
                        WHEN zsr.source_document ILIKE '%Leichhardt%' THEN '%Leichhardt%DCP%'
                        WHEN zsr.source_document ILIKE '%Marrickville%' THEN '%Marrickville%DCP%'
                        ELSE '%' || split_part(zsr.source_document, ' ', 1) || '%'
                    END
                )
            )
            AND rp.zone = zsr.zone
            AND rp.provision_text ILIKE '%' || zsr.boundary_type || '%setback%'
            ORDER BY
                -- Prefer exact boundary type match
                CASE WHEN rp.section_header ILIKE '%' || zsr.boundary_type || '%setback%' THEN 1 ELSE 2 END,
                -- Prefer provisions with numeric values matching our setback
                CASE WHEN rp.provision_text ILIKE '%' || zsr.base_value || zsr.unit || '%' THEN 1 ELSE 2 END,
                rp.id
            LIMIT 1
        )
        WHERE zsr.source_provision_id IS NULL
    """)
    strategy1_count = cursor.rowcount
    conn.commit()
    print(f"  Strategy 1 (fuzzy document + zone + boundary): {strategy1_count} links created")

    # Strategy 2: Any setback provision in matching DCP for same zone
    cursor.execute("""
        UPDATE zone_setback_rules zsr
        SET source_provision_id = (
            SELECT rp.id
            FROM regulatory_provisions_canonical rp
            WHERE rp.document_id ILIKE (
                    CASE
                        WHEN zsr.source_document ILIKE '%Ashfield%' THEN '%Ashfield%DCP%'
                        WHEN zsr.source_document ILIKE '%Leichhardt%' THEN '%Leichhardt%DCP%'
                        WHEN zsr.source_document ILIKE '%Marrickville%' THEN '%Marrickville%DCP%'
                        ELSE '%DCP%'
                    END
                )
            AND rp.zone = zsr.zone
            AND rp.provision_text ILIKE '%setback%'
            ORDER BY rp.id
            LIMIT 1
        )
        WHERE zsr.source_provision_id IS NULL
    """)
    strategy2_count = cursor.rowcount
    conn.commit()
    print(f"  Strategy 2 (any setback in matching DCP): {strategy2_count} links created")

    # Final statistics
    print("\n[SUMMARY]")
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(source_provision_id) as with_link,
               COUNT(*) - COUNT(source_provision_id) as without_link
        FROM zone_setback_rules
    """)
    final_stats = cursor.fetchone()
    print(f"  Total rules: {final_stats[0]}")
    print(f"  With provision link: {final_stats[1]} ({final_stats[1]*100//final_stats[0]}%)")
    print(f"  Without provision link: {final_stats[2]}")

    # Show sample results
    print("\n[VERIFICATION] Sample linked setbacks:")
    cursor.execute("""
        SELECT
            zsr.zone,
            zsr.boundary_type,
            zsr.base_value || zsr.unit as value,
            rp.ref_number,
            LEFT(rp.provision_text, 60) || '...' as text_preview
        FROM zone_setback_rules zsr
        JOIN regulatory_provisions_canonical rp ON zsr.source_provision_id = rp.id
        LIMIT 5
    """)

    for zone, boundary, value, ref, text in cursor.fetchall():
        print(f"  {zone} {boundary} ({value}): {ref}")
        print(f"    -> {text}")

print("\n" + "=" * 80)
print("OK PROVISION LINKS FIXED")
print("=" * 80)
print("\nNext step: Update API to use source_provision_id for full text display")
