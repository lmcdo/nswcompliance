"""
Run ActionableClassifier on all provisions to properly set v2_is_actionable.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from enrichment.extractors.actionable_classifier import ActionableClassifier

load_dotenv()

def run_classifier():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor)
    cur = conn.cursor()

    cur.execute("SET statement_timeout = '600s'")

    print("\n" + "="*70)
    print("RUN ACTIONABLE CLASSIFIER")
    print("="*70)

    # Get all provisions
    print("\nFetching all provisions...")
    cur.execute("""
        SELECT id, document_id, provision_text
        FROM regulatory_provisions
        ORDER BY id
    """)
    provisions = cur.fetchall()
    print(f"Found {len(provisions):,} provisions")

    # Run classifier
    print("\nClassifying provisions...")
    classifier = ActionableClassifier()

    actionable_count = 0
    non_actionable_count = 0
    batch = []
    batch_size = 1000

    for i, prov in enumerate(provisions):
        if i > 0 and i % 5000 == 0:
            print(f"  Progress: {i:,} / {len(provisions):,}")

        is_actionable, reason = classifier.classify(
            prov['provision_text'] or '',
            prov['document_id'] or ''
        )

        if is_actionable:
            actionable_count += 1
        else:
            non_actionable_count += 1

        batch.append((is_actionable, prov['id']))

        # Commit in batches
        if len(batch) >= batch_size:
            cur.executemany(
                "UPDATE regulatory_provisions SET v2_is_actionable = %s WHERE id = %s",
                batch
            )
            conn.commit()
            batch = []

    # Commit remaining
    if batch:
        cur.executemany(
            "UPDATE regulatory_provisions SET v2_is_actionable = %s WHERE id = %s",
            batch
        )
        conn.commit()

    print(f"\nClassification complete:")
    print(f"  Actionable: {actionable_count:,}")
    print(f"  Non-actionable: {non_actionable_count:,}")

    # Verify
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable,
            COUNT(*) FILTER (WHERE v2_is_actionable = false) as non_actionable
        FROM regulatory_provisions
    """)
    row = cur.fetchone()

    print(f"\nDatabase verification:")
    print(f"  Total: {row['total']:,}")
    print(f"  Actionable (TRUE): {row['actionable']:,}")
    print(f"  Non-actionable (FALSE): {row['non_actionable']:,}")

    print("\n" + "="*70)
    print("[SUCCESS] Actionable classification complete")
    print("="*70 + "\n")

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_classifier()
