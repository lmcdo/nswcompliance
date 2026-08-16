#!/usr/bin/env python3
"""
DQ-2 Fix: Re-run topic classification for misclassified provisions.

This script fixes topic misclassification by:
1. Using section number from document_id for Marrickville Part 2 provisions
2. Using earliest keyword match position for fallback

Run this script to update v2_topic for all affected provisions.
"""
import os
import sys
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

from enrichment.extractors.layer_topic_tagger import LayerTopicTagger


def main():
    """Re-run topic classification on all provisions with v2_topic set."""
    print("=" * 70)
    print("DQ-2 FIX: Re-running topic classification")
    print("=" * 70)
    print()

    conn = psycopg2.connect('dbname=nsw_planning')
    cur = conn.cursor()
    tagger = LayerTopicTagger()

    # Get all provisions that have a document_id (needed for tagging)
    print("Fetching provisions to re-classify...")
    cur.execute('''
        SELECT id, document_id, provision_text, v2_topic
        FROM regulatory_provisions
        WHERE document_id IS NOT NULL
          AND document_id != ''
    ''')
    provisions = cur.fetchall()
    print(f"Found {len(provisions)} provisions to process")
    print()

    # Track changes
    changes = 0
    unchanged = 0
    errors = 0
    change_details = []

    print("Processing provisions...")
    for i, (prov_id, doc_id, text, old_topic) in enumerate(provisions):
        if i % 5000 == 0:
            print(f"  Processed {i}/{len(provisions)}...")

        try:
            # Re-tag the provision
            layer, part, new_topic = tagger.tag(doc_id, text or '')

            if new_topic != old_topic:
                # Update the provision
                cur.execute('''
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                ''', (new_topic, prov_id))
                changes += 1

                # Track the change for reporting
                if len(change_details) < 50:  # Keep first 50 for display
                    change_details.append({
                        'id': prov_id,
                        'old': old_topic,
                        'new': new_topic,
                        'doc_id': doc_id[:60] if doc_id else None
                    })
            else:
                unchanged += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error processing ID {prov_id}: {e}")

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total provisions: {len(provisions)}")
    print(f"Changed: {changes}")
    print(f"Unchanged: {unchanged}")
    print(f"Errors: {errors}")
    print()

    if change_details:
        print("Sample changes:")
        for detail in change_details[:20]:
            print(f"  ID {detail['id']}: {detail['old']} -> {detail['new']}")
        if len(change_details) > 20:
            print(f"  ... and {len(change_details) - 20} more")
    print()

    # Verify the specific case mentioned in DQ-2
    print("Verifying ID 78329 (Car parking design controls)...")
    cur.execute("SELECT v2_topic FROM regulatory_provisions WHERE id = 78329")
    result = cur.fetchone()
    if result:
        print(f"  v2_topic = '{result[0]}'")
        if result[0] == 'parking':
            print("  SUCCESS: Now correctly tagged as 'parking'")
        else:
            print(f"  WARNING: Expected 'parking', got '{result[0]}'")
    else:
        print("  Provision not found")

    # Commit changes
    print()
    confirm = input("Commit changes? (y/n): ")
    if confirm.lower() == 'y':
        conn.commit()
        print("Changes committed successfully!")
    else:
        conn.rollback()
        print("Changes rolled back.")

    conn.close()


if __name__ == "__main__":
    main()
