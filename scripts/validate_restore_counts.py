"""
Validate database restore by comparing current provision counts to expected counts.

Expected counts (from LEGAL_RATIONALE.md and DATA_QUALITY_TRACKER.md):
- Leichhardt: 2,989 provisions
- Marrickville: 2,838 provisions
- Ashfield: Unknown (need to verify)
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def validate_restore():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    print("\n" + "="*80)
    print("DATABASE RESTORE VALIDATION")
    print("="*80)

    # Total provisions
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
    total = cur.fetchone()[0]
    print(f"\nTotal provisions in database: {total:,}")

    # Actionable provisions
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true")
    actionable = cur.fetchone()[0]
    print(f"Actionable provisions: {actionable:,}")
    print(f"Non-actionable: {total - actionable:,}")

    # By former council (using document_id patterns)
    print("\n" + "="*80)
    print("PROVISIONS BY FORMER COUNCIL")
    print("="*80)

    councils = [
        ('Leichhardt', '%Leichhardt%', 2989),
        ('Marrickville', '%Marrickville%', 2838),
        ('Ashfield', '%Ashfield%', None)
    ]

    results = []

    for council_name, pattern, expected in councils:
        # Total provisions
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
        """, (pattern,))
        total_count = cur.fetchone()[0]

        # Actionable provisions
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s AND v2_is_actionable = true
        """, (pattern,))
        actionable_count = cur.fetchone()[0]

        # DCP provisions only
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND (document_id LIKE '%DCP%' OR document_id LIKE '%Development_Control_Plan%')
        """, (pattern,))
        dcp_count = cur.fetchone()[0]

        results.append({
            'council': council_name,
            'total': total_count,
            'actionable': actionable_count,
            'dcp_only': dcp_count,
            'expected': expected
        })

        print(f"\n{council_name}:")
        print(f"  Total provisions: {total_count:,}")
        print(f"  Actionable: {actionable_count:,}")
        print(f"  DCP only: {dcp_count:,}")

        if expected:
            diff = total_count - expected
            pct_diff = (diff / expected * 100) if expected > 0 else 0
            status = "OK" if abs(pct_diff) < 10 else "MISSING" if diff < 0 else "EXTRA"
            print(f"  Expected: {expected:,}")
            print(f"  Difference: {diff:+,} ({pct_diff:+.1f}%) [{status}]")

    # By document type
    print("\n" + "="*80)
    print("PROVISIONS BY DOCUMENT TYPE")
    print("="*80)

    cur.execute("""
        SELECT
            CASE
                WHEN document_id LIKE '%DCP%' OR document_id LIKE '%Development_Control_Plan%' THEN 'DCP'
                WHEN document_id LIKE '%SEPP%' OR document_id LIKE '%Environmental_Planning_Policy%' THEN 'SEPP'
                WHEN document_id LIKE '%LEP%' OR document_id LIKE '%Local_Environmental_Plan%' THEN 'LEP'
                ELSE 'Other'
            END as doc_type,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable
        FROM regulatory_provisions
        GROUP BY doc_type
        ORDER BY total DESC
    """)

    for row in cur.fetchall():
        doc_type, total_count, actionable_count = row
        print(f"\n{doc_type}:")
        print(f"  Total: {total_count:,}")
        print(f"  Actionable: {actionable_count:,}")

    # Sample provisions per council
    print("\n" + "="*80)
    print("SAMPLE PROVISIONS (First 3 per council)")
    print("="*80)

    for council_name, pattern, _ in councils:
        cur.execute("""
            SELECT id, document_id, LEFT(provision_text, 80)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            ORDER BY id
            LIMIT 3
        """, (pattern,))

        print(f"\n{council_name}:")
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  ID={row[0]}, doc={row[1][:50]}...")
                print(f"    text: {row[2]}...")
        else:
            print("  NO PROVISIONS FOUND")

    # Validation summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    issues = []

    for r in results:
        if r['expected'] and r['total'] < r['expected'] * 0.9:
            issues.append(f"  [CRITICAL] {r['council']}: Missing {r['expected'] - r['total']:,} provisions (have {r['total']:,}, expected {r['expected']:,})")

    if issues:
        print("\n[ISSUES FOUND]")
        for issue in issues:
            print(issue)
        print("\n[RECOMMENDATION] Database may be incomplete - restore from correct backup")
    else:
        print("\n[SUCCESS] All provision counts within expected ranges")

    cur.close()
    conn.close()

if __name__ == "__main__":
    validate_restore()
