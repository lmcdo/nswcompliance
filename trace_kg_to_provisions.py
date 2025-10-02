#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check if original_ref_id links back to regulatory_provisions
        print("Checking if KG relationships link to regulatory_provisions...\n")

        cur.execute("""
            SELECT
                r.original_ref_type,
                r.original_ref_id,
                r.subject_text,
                r.predicate,
                r.object_text
            FROM kg_relationships r
            WHERE r.original_ref_type IS NOT NULL
            AND r.original_ref_id IS NOT NULL
            LIMIT 5
        """)

        results = cur.fetchall()
        if results:
            print("Sample relationships with ref links:")
            for row in results:
                print(f"\nRef type: {row[0]}, Ref ID: {row[1]}")
                print(f"  {row[2]} --[{row[3]}]--> {row[4]}")

                # Try to find matching provision
                if row[0] == 'regulatory_provision':
                    cur.execute("""
                        SELECT ref_number, document_id, LEFT(provision_text, 100)
                        FROM regulatory_provisions
                        WHERE id = %s
                    """, (row[1],))

                    prov = cur.fetchone()
                    if prov:
                        print(f"  Links to: {prov[1]} clause {prov[0]}")
                        print(f"  Text: {prov[2]}")
        else:
            print("No relationships have original_ref links")

        # Check what original_ref_types exist
        print("\n" + "="*80)
        print("\nDistinct original_ref_types:")
        cur.execute("""
            SELECT DISTINCT original_ref_type, COUNT(*)
            FROM kg_relationships
            WHERE original_ref_type IS NOT NULL
            GROUP BY original_ref_type
        """)

        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]} relationships")