#!/usr/bin/env python3
"""
Backfill v2_structural_category on all provisions using the structural category map.

Usage:
  python scripts/backfill_structural_categories.py --dry-run   # preview only
  python scripts/backfill_structural_categories.py              # apply updates
"""
import os, sys, argparse
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

from enrichment.config.structural_categories import get_structural_category, EXCLUDABLE

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without updating')
    parser.add_argument('--council', '-c', help='Filter to single council')
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    # Ensure column exists
    if not args.dry_run:
        cur.execute("""
            DO $$ BEGIN
                ALTER TABLE regulatory_provisions ADD COLUMN v2_structural_category TEXT;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """)
        conn.commit()

    # Fetch all provisions
    where = "WHERE is_current = true AND source_council IS NOT NULL"
    params = []
    if args.council:
        where += " AND source_council = %s"
        params.append(args.council)

    cur.execute(f"""
        SELECT id, source_council, source_chapter_key, section_header, v2_topic
        FROM regulatory_provisions
        {where}
        ORDER BY source_council, id
    """, params)

    rows = cur.fetchall()
    print(f"Processing {len(rows)} provisions...\n")

    updates = []  # (id, category)
    stats_by_council = {}  # council -> Counter

    for row in rows:
        prov_id, council, chapter_key, header, current_topic = row
        category = get_structural_category(council, chapter_key or "", header)

        if council not in stats_by_council:
            stats_by_council[council] = {"total": 0, "mapped": 0, "by_cat": Counter()}

        stats_by_council[council]["total"] += 1
        if category:
            stats_by_council[council]["mapped"] += 1
            stats_by_council[council]["by_cat"][category] += 1
            updates.append((prov_id, category))

    # Report
    print("=== STRUCTURAL CATEGORY ASSIGNMENT ===\n")
    for council in sorted(stats_by_council.keys()):
        s = stats_by_council[council]
        mapped_pct = s["mapped"] / s["total"] * 100 if s["total"] else 0
        unmapped = s["total"] - s["mapped"]
        print(f"  {council:15s} {s['mapped']:4d}/{s['total']:4d} mapped ({mapped_pct:.0f}%) | "
              f"{unmapped} unmapped (always in active set)")
        for cat, count in s["by_cat"].most_common():
            print(f"  {'':15s}  {cat}: {count}")
        print()

    # Compare: how many provisions would change exclusion behavior?
    print("=== IMPACT: v2_topic vs v2_structural_category ===\n")
    print("  Shows provisions that are currently excluded by v2_topic")
    print("  but would NOT be excluded by structural category (over-exclusions prevented).\n")

    topic_excluded_but_not_structural = Counter()
    for row in rows:
        prov_id, council, chapter_key, header, current_topic = row
        category = get_structural_category(council, chapter_key or "", header)
        if current_topic and current_topic.lower() in EXCLUDABLE:
            if category != current_topic.lower():
                topic_excluded_but_not_structural[
                    f"{council}:{current_topic}"
                ] += 1

    if topic_excluded_but_not_structural:
        for key, count in topic_excluded_but_not_structural.most_common(20):
            print(f"  {key:40s} {count:4d} provisions no longer auto-excludable")
    else:
        print("  (none)")

    print(f"\n  Total: {sum(topic_excluded_but_not_structural.values())} provisions "
          f"protected from false exclusion")

    # Apply
    if not args.dry_run and updates:
        print(f"\nApplying {len(updates)} updates...")
        for prov_id, category in updates:
            cur.execute(
                "UPDATE regulatory_provisions SET v2_structural_category = %s WHERE id = %s",
                (category, prov_id),
            )
        # Clear structural category for provisions not in update list
        update_ids = {u[0] for u in updates}
        all_ids = {r[0] for r in rows}
        clear_ids = all_ids - update_ids
        if clear_ids:
            cur.execute(
                "UPDATE regulatory_provisions SET v2_structural_category = NULL WHERE id = ANY(%s)",
                (list(clear_ids),),
            )
        conn.commit()
        print("Done.")
    elif args.dry_run:
        print(f"\n[DRY RUN] Would update {len(updates)} provisions. Run without --dry-run to apply.")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
