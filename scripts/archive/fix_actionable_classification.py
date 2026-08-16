"""
Fix v2_is_actionable classification.

Based on the Nov 24 backup which had 11,835 actionable DCP provisions,
we set v2_is_actionable = TRUE for all DCP provisions.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def fix_actionable():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    cur.execute("SET statement_timeout = '600s'")

    print("\n" + "="*70)
    print("FIX v2_is_actionable CLASSIFICATION")
    print("="*70)

    # Check current state
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable_true,
            COUNT(*) FILTER (WHERE v2_is_actionable = false) as actionable_false
        FROM regulatory_provisions
    """)
    row = cur.fetchone()
    print(f"\nCurrent state:")
    print(f"  Total provisions: {row[0]:,}")
    print(f"  v2_is_actionable = TRUE: {row[1]:,}")
    print(f"  v2_is_actionable = FALSE: {row[2]:,}")

    # Count DCP provisions
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%DCP%'
           OR document_id LIKE '%Development_Control_Plan%'
    """)
    dcp_count = cur.fetchone()[0]
    print(f"\nDCP provisions found: {dcp_count:,}")

    # Set DCP provisions to actionable = TRUE
    print("\nSetting DCP provisions to v2_is_actionable = TRUE...")
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_is_actionable = TRUE
        WHERE document_id LIKE '%DCP%'
           OR document_id LIKE '%Development_Control_Plan%'
    """)

    conn.commit()
    updated = cur.rowcount
    print(f"Updated {updated:,} provisions to actionable = TRUE")

    # Verify final state
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable_true,
            COUNT(*) FILTER (WHERE v2_is_actionable = false) as actionable_false
        FROM regulatory_provisions
    """)
    row = cur.fetchone()
    print(f"\nFinal state:")
    print(f"  Total provisions: {row[0]:,}")
    print(f"  v2_is_actionable = TRUE: {row[1]:,}")
    print(f"  v2_is_actionable = FALSE: {row[2]:,}")

    print("\n" + "="*70)
    print("[SUCCESS] v2_is_actionable classification fixed")
    print("="*70 + "\n")

    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_actionable()
