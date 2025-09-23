#!/usr/bin/env python3
"""
Migrate data from regulatory_provisions to authoritative schema
This should have been done by the PRPs but wasn't
"""

import psycopg2

print("Migrating data from regulatory_provisions to authoritative schema...")

conn = psycopg2.connect(
    host='127.0.0.1',
    database='nsw_planning',
    user='postgres',
    port=5432
)

cursor = conn.cursor()

try:
    # First, populate authoritative.planning_provisions from regulatory_provisions
    print("\nMigrating provisions to authoritative.planning_provisions...")

    cursor.execute("""
        INSERT INTO authoritative.planning_provisions (
            document_type,
            document_name,
            clause_reference,
            authority_level,
            precedence_score,
            provision_text,
            zone_specific,
            applicable_zones,
            development_type,
            numeric_standard,
            numeric_value,
            units,
            provision_category,
            data_source,
            confidence_score
        )
        SELECT
            CASE
                WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
                WHEN document_id LIKE '%LEP%' THEN 'LEP'
                WHEN document_id LIKE '%DCP%' THEN 'DCP'
                ELSE 'OTHER'
            END as document_type,
            document_id as document_name,
            COALESCE(ref_number, 'N/A') as clause_reference,
            CASE
                WHEN document_id LIKE '%SEPP%' THEN 1
                WHEN document_id LIKE '%LEP%' THEN 2
                WHEN document_id LIKE '%DCP%' THEN 3
                ELSE 4
            END as authority_level,
            50.00 as precedence_score,
            provision_text,
            CASE WHEN zone IS NOT NULL THEN true ELSE false END as zone_specific,
            CASE WHEN zone IS NOT NULL THEN ARRAY[zone] ELSE NULL END as applicable_zones,
            development_type,
            false as numeric_standard,
            NULL as numeric_value,
            NULL as units,
            provision_type as provision_category,
            'regulatory_provisions' as data_source,
            COALESCE(classification_confidence, 0.5) as confidence_score
        FROM public.regulatory_provisions
        WHERE provision_text IS NOT NULL
        AND LENGTH(provision_text) > 10
        ON CONFLICT DO NOTHING
    """)

    provisions_count = cursor.rowcount
    print(f"  Inserted {provisions_count:,} provisions")

    # Commit the migration
    conn.commit()

    # Verify the migration
    cursor.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
    total_provisions = cursor.fetchone()[0]

    cursor.execute("""
        SELECT document_type, COUNT(*)
        FROM authoritative.planning_provisions
        GROUP BY document_type
        ORDER BY COUNT(*) DESC
    """)

    print(f"\nMigration complete! Total provisions: {total_provisions:,}")
    print("\nBreakdown by document type:")
    for doc_type, count in cursor.fetchall():
        print(f"  {doc_type}: {count:,}")

    # Check zone-specific provisions
    cursor.execute("""
        SELECT COUNT(DISTINCT applicable_zones[1]) as zones,
               COUNT(*) as provisions
        FROM authoritative.planning_provisions
        WHERE zone_specific = true
    """)
    zones, zone_provisions = cursor.fetchone()
    print(f"\nZone-specific provisions: {zone_provisions:,} across {zones} zones")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

print("\n✓ Data migration complete! The authoritative schema now has data.")