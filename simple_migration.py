#!/usr/bin/env python3
"""
Simple migration from regulatory_provisions to authoritative.planning_provisions
"""

import psycopg2

print("Migrating data to authoritative schema...")

conn = psycopg2.connect(
    host='127.0.0.1',
    database='nsw_planning',
    user='postgres',
    port=5432
)

cursor = conn.cursor()

try:
    # Simple migration with only matching columns
    cursor.execute("""
        INSERT INTO authoritative.planning_provisions (
            document_type,
            document_name,
            clause_reference,
            authority_level,
            precedence_score,
            provision_text,
            provision_type,
            applicable_zones,
            applicable_dev_types,
            extraction_method,
            extraction_confidence,
            verification_status,
            is_current
        )
        SELECT
            CASE
                WHEN document_id ILIKE '%sepp%' THEN 'SEPP'
                WHEN document_id ILIKE '%lep%' THEN 'LEP'
                WHEN document_id ILIKE '%dcp%' THEN 'DCP'
                ELSE 'OTHER'
            END,
            LEFT(document_id, 200),
            LEFT(COALESCE(ref_number, 'N/A'), 100),
            CASE
                WHEN document_id ILIKE '%sepp%' THEN 1
                WHEN document_id ILIKE '%lep%' THEN 2
                WHEN document_id ILIKE '%dcp%' THEN 3
                ELSE 4
            END,
            50.0,
            provision_text,
            provision_type,
            CASE WHEN zone IS NOT NULL THEN ARRAY[zone] ELSE NULL END,
            CASE WHEN development_type IS NOT NULL THEN ARRAY[development_type] ELSE NULL END,
            'migration',
            COALESCE(classification_confidence, 0.5),
            'unverified',
            is_current
        FROM public.regulatory_provisions
        WHERE provision_text IS NOT NULL
        AND LENGTH(provision_text) > 10
        LIMIT 5000  -- Start with subset
    """)

    count = cursor.rowcount
    print(f"Migrated {count} provisions")

    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
    total = cursor.fetchone()[0]
    print(f"Total in authoritative: {total}")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

print("Migration complete!")