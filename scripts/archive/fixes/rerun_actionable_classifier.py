#!/usr/bin/env python3
"""
Re-run the fixed actionable classifier on all provisions.

This script applies the following fixes:
1. Blank line regex bug fix (\\A[\\s\\.\\-_]+\\Z instead of ^[\\s\\.\\-_]+$)
2. Underscore pattern fix (Local[_ ]Environmental[_ ]Plan)
3. Boilerplate rescue logic (high actionable score overrides boilerplate match)
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

from enrichment.extractors.actionable_classifier import ActionableClassifier

def rerun_classifier():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    classifier = ActionableClassifier()

    print("=" * 70)
    print("RE-RUNNING ACTIONABLE CLASSIFIER WITH FIXES")
    print("=" * 70)

    # Get current counts
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true")
    before_actionable = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = false")
    before_excluded = cur.fetchone()[0]

    print(f"\nBefore: {before_actionable} actionable, {before_excluded} excluded")

    # Get all provisions
    cur.execute("""
        SELECT id, document_id, provision_text, v2_is_actionable
        FROM regulatory_provisions
        WHERE provision_text IS NOT NULL
    """)

    rows = cur.fetchall()
    total = len(rows)
    print(f"\nProcessing {total} provisions...")

    # Track changes
    changed_to_actionable = 0
    changed_to_excluded = 0
    unchanged = 0
    batch_updates = []

    for i, (id, doc_id, text, current_actionable) in enumerate(rows):
        new_actionable, reason = classifier.classify(text, doc_id)

        if new_actionable != current_actionable:
            batch_updates.append((new_actionable, id))
            if new_actionable:
                changed_to_actionable += 1
            else:
                changed_to_excluded += 1
        else:
            unchanged += 1

        # Progress update
        if (i + 1) % 5000 == 0:
            print(f"  Processed {i + 1}/{total}...")

    print(f"\nChanges to apply:")
    print(f"  Changed to ACTIONABLE: {changed_to_actionable}")
    print(f"  Changed to EXCLUDED:   {changed_to_excluded}")
    print(f"  Unchanged:             {unchanged}")

    # Apply updates in batches
    if batch_updates:
        print(f"\nApplying {len(batch_updates)} updates...")

        # Split into actionable=true and actionable=false batches
        to_actionable = [id for (val, id) in batch_updates if val]
        to_excluded = [id for (val, id) in batch_updates if not val]

        if to_actionable:
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_is_actionable = true
                WHERE id = ANY(%s)
            """, (to_actionable,))
            print(f"  Set {len(to_actionable)} provisions to actionable")

        if to_excluded:
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_is_actionable = false
                WHERE id = ANY(%s)
            """, (to_excluded,))
            print(f"  Set {len(to_excluded)} provisions to excluded")

        conn.commit()
        print("  Committed changes")

    # Get new counts
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true")
    after_actionable = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = false")
    after_excluded = cur.fetchone()[0]

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\nBefore: {before_actionable} actionable ({before_actionable/(before_actionable+before_excluded)*100:.1f}%)")
    print(f"After:  {after_actionable} actionable ({after_actionable/(after_actionable+after_excluded)*100:.1f}%)")
    print(f"\nNet change: +{after_actionable - before_actionable} actionable provisions")

    conn.close()

    return changed_to_actionable, changed_to_excluded

if __name__ == "__main__":
    rerun_classifier()
