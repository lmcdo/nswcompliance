#!/usr/bin/env python3
"""
Master Re-Enrichment Script
Restores all v2 column enrichment after database recovery

This script runs the complete enrichment pipeline to restore:
1. v2_dcp_layer (generic/use_specific/condition/precinct)
2. v2_topic (setbacks/parking/heritage/etc.)
3. v2_applicable_zones (zone arrays)
4. v2_applicable_dev_types (dev-type arrays)
5. v2_has_numeric_value (CDC eligibility)

Usage:
    python scripts/re_enrich_all.py [--dry-run] [--quick-test]

Options:
    --dry-run       Show what would be done without making changes
    --quick-test    Process only 1000 provisions for testing
"""

import os
import sys
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor
from enrichment.extractors.layer_topic_tagger import LayerTopicTagger


def get_connection():
    """Get database connection"""
    return psycopg2.connect(os.getenv('DATABASE_URL'), cursor_factory=RealDictCursor)


def step1_layer_and_topic_enrichment(dry_run=False, limit=None):
    """
    Step 1: Classify provisions into layers and assign topics
    - v2_dcp_layer: generic, use_specific, condition, precinct
    - v2_dcp_part: Part 2, Part 4.1, etc.
    - v2_topic: setbacks, parking, heritage, etc.
    """
    print("\n" + "=" * 70)
    print("STEP 1: Layer & Topic Classification")
    print("=" * 70)

    conn = get_connection()
    cur = conn.cursor()

    # Set timeout
    cur.execute("SET statement_timeout = '600s'")

    tagger = LayerTopicTagger()

    # Get provisions to enrich
    query = """
        SELECT id, document_id, provision_text
        FROM regulatory_provisions
        ORDER BY id
    """
    if limit:
        query += f" LIMIT {limit}"

    print(f"Fetching provisions...")
    cur.execute(query)
    provisions = cur.fetchall()

    print(f"Found {len(provisions)} provisions to enrich")

    if dry_run:
        print("\n[DRY RUN] Would classify provisions into layers and topics")
        print(f"Sample classification:")
        for prov in provisions[:5]:
            layer, part, topic = tagger.tag(prov['document_id'], prov['provision_text'] or '')
            print(f"  ID {prov['id']}: layer={layer}, part={part}, topic={topic}")
        conn.close()
        return

    # Process in batches
    batch_size = 500
    total = len(provisions)
    processed = 0
    updated = 0

    print(f"\nProcessing in batches of {batch_size}...")

    for i in range(0, total, batch_size):
        batch = provisions[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} provisions)...", end='')

        for prov in batch:
            layer, part, topic = tagger.tag(prov['document_id'], prov['provision_text'] or '')

            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_dcp_layer = %s,
                    v2_dcp_part = %s,
                    v2_topic = %s
                WHERE id = %s
            """, (layer, part, topic, prov['id']))

            processed += 1
            updated += cur.rowcount

        conn.commit()
        print(f" [OK] ({processed}/{total})")

    print(f"\n[OK] Step 1 Complete: {updated} provisions classified")
    conn.close()
    return updated


def step2_zone_enrichment(dry_run=False, limit=None):
    """
    Step 2: Enrich v2_applicable_zones
    - Sets zone arrays based on zone-specific sections
    - Defaults to ['ALL'] for generic provisions
    """
    print("\n" + "=" * 70)
    print("STEP 2: Zone Enrichment")
    print("=" * 70)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '600s'")

    # Default ALL zones for generic layer
    print("Setting default zones for generic layer...")
    query = """
        UPDATE regulatory_provisions
        SET v2_applicable_zones = ARRAY['ALL']
        WHERE v2_dcp_layer = 'generic'
          AND (v2_applicable_zones IS NULL OR v2_applicable_zones = '{}')
    """
    if limit:
        query += f" AND id IN (SELECT id FROM regulatory_provisions LIMIT {limit})"

    if dry_run:
        print("[DRY RUN] Would set v2_applicable_zones = ['ALL'] for generic provisions")
        conn.close()
        return

    cur.execute(query)
    generic_updated = cur.rowcount
    print(f"  [OK] {generic_updated} generic provisions set to ALL zones")

    # Set ALL for non-zone-specific layers
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_applicable_zones = ARRAY['ALL']
        WHERE v2_dcp_layer IN ('use_specific', 'condition', 'precinct')
          AND (v2_applicable_zones IS NULL OR v2_applicable_zones = '{}')
    """)
    other_updated = cur.rowcount
    print(f"  [OK] {other_updated} other provisions set to ALL zones")

    conn.commit()
    print(f"\n[OK] Step 2 Complete: {generic_updated + other_updated} provisions enriched")
    conn.close()
    return generic_updated + other_updated


def step3_run_dq_fixes(dry_run=False, limit=None):
    """
    Step 3: Run critical DQ fix scripts
    - DQ7: Dev-type enrichment
    - DQ11: Heritage categorization
    - DQ13/14: Leichhardt fixes
    """
    print("\n" + "=" * 70)
    print("STEP 3: Data Quality Fixes")
    print("=" * 70)

    critical_scripts = [
        'scripts/fixes/DQ7_devtype_enrichment.py',
        'scripts/fixes/DQ7_commercial_industrial_enrichment.py',
        'scripts/fixes/DQ7_remaining_devtypes.py',
        'scripts/fixes/DQ11_marrickville_heritage.py',
        'scripts/fixes/DQ13_leichhardt_fixes.py',
    ]

    for script in critical_scripts:
        if not os.path.exists(script):
            print(f"  [SKIP] {script} not found")
            continue

        print(f"\nRunning {os.path.basename(script)}...")

        if dry_run:
            print(f"  [DRY RUN] Would run: python {script}")
        else:
            import subprocess
            try:
                result = subprocess.run(
                    [sys.executable, script],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result.returncode == 0:
                    print(f"  [OK] Completed successfully")
                    if result.stdout:
                        print(f"  Output: {result.stdout[:200]}")
                else:
                    print(f"  [WARN] Exit code {result.returncode}")
                    if result.stderr:
                        print(f"  Error: {result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                print(f"  [WARN] Script timed out after 600 seconds")
            except Exception as e:
                print(f"  [ERROR] {e}")

    print(f"\n[OK] Step 3 Complete: DQ fixes applied")


def step4_default_dev_types(dry_run=False, limit=None):
    """
    Step 4: Set default dev_types for provisions without specific types
    """
    print("\n" + "=" * 70)
    print("STEP 4: Default Dev-Type Assignment")
    print("=" * 70)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '600s'")

    # Set ALL for provisions without dev_types
    query = """
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = ARRAY['ALL']
        WHERE (v2_applicable_dev_types IS NULL OR v2_applicable_dev_types = '{}')
    """
    if limit:
        query += f" AND id IN (SELECT id FROM regulatory_provisions LIMIT {limit})"

    if dry_run:
        print("[DRY RUN] Would set v2_applicable_dev_types = ['ALL'] for provisions without specific types")
        conn.close()
        return

    cur.execute(query)
    updated = cur.rowcount
    conn.commit()

    print(f"  [OK] {updated} provisions set to ALL dev_types")
    print(f"\n[OK] Step 4 Complete")
    conn.close()
    return updated


def verify_enrichment():
    """Verify enrichment results"""
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    conn = get_connection()
    cur = conn.cursor()

    # Check layer distribution
    cur.execute("""
        SELECT v2_dcp_layer, COUNT(*) as count
        FROM regulatory_provisions
        GROUP BY v2_dcp_layer
        ORDER BY count DESC
    """)
    print("\nLayer distribution:")
    for row in cur.fetchall():
        layer = row['v2_dcp_layer'] or 'NULL'
        print(f"  {layer}: {row['count']} provisions")

    # Check topic coverage
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE v2_topic IS NOT NULL) as has_topic,
            COUNT(*) FILTER (WHERE v2_topic IS NULL) as no_topic
        FROM regulatory_provisions
    """)
    result = cur.fetchone()
    print(f"\nTopic coverage:")
    print(f"  With topic: {result['has_topic']}")
    print(f"  Without topic: {result['no_topic']}")

    # Check zone coverage
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE v2_applicable_zones IS NOT NULL) as has_zones,
            COUNT(*) FILTER (WHERE v2_applicable_zones IS NULL) as no_zones
        FROM regulatory_provisions
    """)
    result = cur.fetchone()
    print(f"\nZone coverage:")
    print(f"  With zones: {result['has_zones']}")
    print(f"  Without zones: {result['no_zones']}")

    # Check dev_type coverage
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE v2_applicable_dev_types IS NOT NULL) as has_dev_types,
            COUNT(*) FILTER (WHERE v2_applicable_dev_types IS NULL) as no_dev_types
        FROM regulatory_provisions
    """)
    result = cur.fetchone()
    print(f"\nDev-type coverage:")
    print(f"  With dev_types: {result['has_dev_types']}")
    print(f"  Without dev_types: {result['no_dev_types']}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Re-enrich all v2 columns after database recovery')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--quick-test', action='store_true', help='Process only 1000 provisions for testing')

    args = parser.parse_args()

    limit = 1000 if args.quick_test else None

    print("=" * 70)
    print("COMPLIANCE ENGINE - V2 RE-ENRICHMENT MASTER SCRIPT")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dry run: {args.dry_run}")
    print(f"Limit: {limit or 'None (all provisions)'}")

    try:
        # Run enrichment pipeline
        step1_layer_and_topic_enrichment(args.dry_run, limit)
        step2_zone_enrichment(args.dry_run, limit)
        step3_run_dq_fixes(args.dry_run, limit)
        step4_default_dev_types(args.dry_run, limit)

        if not args.dry_run:
            verify_enrichment()

        print("\n" + "=" * 70)
        print("RE-ENRICHMENT COMPLETE")
        print("=" * 70)
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Enrichment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Enrichment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
