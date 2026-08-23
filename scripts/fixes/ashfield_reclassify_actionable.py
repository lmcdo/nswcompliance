#!/usr/bin/env python3
"""
Phase 2: Reclassify Ashfield provisions with DS/PC markers as actionable

These were incorrectly marked as boilerplate due to PDF header pollution.
"""
import os
import psycopg2

LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"

def reclassify_actionable():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()

    print("=" * 80)
    print("Phase 2: Reclassifying Ashfield provisions as actionable")
    print("=" * 80)

    # Check current state
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE v2_is_actionable = false AND (provision_text ~ 'DS\d' OR provision_text ~ 'PC\d')) as boilerplate_with_controls,
            COUNT(*) FILTER (WHERE v2_is_actionable = false) as total_boilerplate
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
    """)
    row = cur.fetchone()
    print(f"Current: {row[0]} boilerplate with DS/PC markers (of {row[1]} total boilerplate)")

    # Reclassify provisions with DS/PC markers
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_is_actionable = true
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_is_actionable = false
          AND (provision_text ~ 'DS\d' OR provision_text ~ 'PC\d')
        RETURNING id
    """)

    updated_ids = cur.fetchall()
    print(f"Updated {len(updated_ids)} provisions to actionable")

    # Also clear their v2 columns so they get re-tagged
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_dcp_layer = NULL,
            v2_dcp_part = NULL,
            v2_topic = NULL
        WHERE id = ANY(%s)
    """, ([r[0] for r in updated_ids],))

    conn.commit()

    # Check new state
    cur.execute("""
        SELECT document_id, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_is_actionable = true
          AND v2_dcp_layer IS NULL
        GROUP BY document_id
        ORDER BY COUNT(*) DESC
    """)

    print("\nProvisions now actionable but need layer tagging:")
    for row in cur.fetchall():
        print(f"  {row[1]:4d} | {row[0][:60]}")

    conn.close()
    return len(updated_ids)

if __name__ == "__main__":
    reclassify_actionable()
