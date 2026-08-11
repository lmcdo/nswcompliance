#!/usr/bin/env python3
# prior-art-checked: reuse not viable because scripts/backfill_invalid_zone_codes.py
# repairs INVALID zone codes against lep_zone_coverage — a different defect, a
# different source of truth, and it only touches rows already known bad. This
# re-runs the TAGGER over a council's whole corpus after a matcher fix. Its safety
# shape (dry-run default, auto backup table, per-row optimistic-concurrency guard,
# printed rollback SQL, 30s timeout, never TRUNCATE/DROP) is copied deliberately
# rather than reinvented. enrichment/pipeline.py::run_applicability_tagging cannot
# be used: it only revisits rows WHERE v2_applicable_zones IS NULL, so it would
# skip every row this exists to correct.
"""Re-tag applicability after the DQ-33 document_id slug fix.

WHY
---
The Marrickville / Ashfield / Leichhardt matchers were written for a verbose
document_id convention ("Chapter E1", "4.1"). Production uses a slug
("chapter_e1_heritage", "part4_s1_low_density"). The council matched, the PART
never did, and 9,854 served rows fell through to ALL/ALL.

DIRECTION OF RISK — read before running
---------------------------------------
Unlike the 241-row zone repair, this NARROWS what a property is shown. Showing an
irrelevant control is noise; hiding a binding one is the liability. So:

  * a slug resolves ONLY to a key the council's config already declares — no key
    is invented and no part is guessed to improve the numbers;
  * anything unrecognised stays ALL with source `no_config`, deliberately, and
    that count is reported rather than minimised;
  * --dry-run is the default and prints the full plan.

Predicted before the first run (2026-08-01): 22,007 rows in scope, 1,928 values
change, 815 served rows narrow on zones, 882 on dev types, and `no_config` on
served rows falls 9,854 -> 1,278.

SAFETY
------
Backup table first, aborts if the backup is smaller than the plan, per-row UPDATE
guarded on the value read during planning (so a concurrent write is never
clobbered), 30s statement timeout, rollback SQL printed on completion.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

COUNCILS = ("marrickville", "ashfield", "leichhardt")


def _connect():
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is not a pass.",
              file=sys.stderr)
        sys.exit(2)
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    return conn, cur


# Declared beside the query that uses it. NOTE the scope is deliberately NOT
# restricted to is_current / v2_is_actionable rows: applicability should be correct
# on superseded provisions too, or the next time one is reinstated it comes back
# mis-tagged. The SELECT below carries those two columns so served rows can be
# counted separately in the plan, which is the number that matters for risk.
TABLE = "regulatory_provisions"


def build_plan(cur):
    """Rows whose tag VALUES change, plus the provenance for every row in scope."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from enrichment.extractors.applicability_tagger import ApplicabilityTagger

    cur.execute(
        f"""SELECT is_current AND v2_is_actionable AS served,
                   id, document_id, provision_text,
                   v2_applicable_zones, v2_applicable_dev_types
            FROM {TABLE} WHERE source_council = ANY(%s)""",
        (list(COUNCILS),),
    )
    tagger = ApplicabilityTagger()
    plan, prov_only = [], []
    stats = Counter()
    for served, pid, doc, txt, old_z, old_d in cur.fetchall():
        zones, devs, prov = tagger.tag_with_provenance(txt or "", doc)
        old_z, old_d = list(old_z or []), list(old_d or [])
        stats[(prov["zone_source"], "served" if served else "other")] += 1
        row = (pid, zones, devs, prov["zone_source"], prov["dev_type_source"],
               old_z, old_d)
        if zones != old_z or devs != old_d:
            plan.append(row)
            if zones != old_z and served:
                stats["served_zone_narrowed"] += 1
            if devs != old_d and served:
                stats["served_devtype_narrowed"] += 1
        else:
            prov_only.append(row)
    return plan, prov_only, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--backup-table", default="regulatory_provisions_dq33_backup_20260801")
    ap.add_argument("--limit-print", type=int, default=15)
    args = ap.parse_args()

    conn, cur = _connect()
    try:
        plan, prov_only, stats = build_plan(cur)
        print(f"\n=== DQ-33 re-tag plan ===")
        print(f"  rows in scope            : {len(plan) + len(prov_only):,}")
        print(f"  VALUES change            : {len(plan):,}")
        print(f"  provenance only          : {len(prov_only):,}")
        print(f"  served rows narrowed — zones {stats['served_zone_narrowed']:,}, "
              f"dev types {stats['served_devtype_narrowed']:,}")
        print("\n  predicted provenance after:")
        # `stats` mixes tuple keys (source, served-ness) with two plain string
        # counters, so filter by key SHAPE before unpacking rather than assuming.
        prov = {k: v for k, v in stats.items() if isinstance(k, tuple)}
        for (src, kind), n in sorted(prov.items(), key=lambda kv: -kv[1]):
            print(f"    {src:<16} {kind:<7} {n:>7,}")

        print(f"\n  sample of value changes (first {args.limit_print}):")
        for pid, z, d, zs, _ds, oz, od in plan[:args.limit_print]:
            print(f"    id={pid:<7} zones {oz} -> {z}   src={zs}")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0

        all_rows = plan + prov_only
        ids = [r[0] for r in all_rows]
        print(f"\nCreating backup table {args.backup_table} ...")
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
            f"SELECT id, v2_applicable_zones, v2_applicable_dev_types, "
            f"       v2_zone_source, v2_dev_type_source "
            f"FROM {TABLE} WHERE id = ANY(%s)",
            (ids,),
        )
        cur.execute(f"SELECT count(*) FROM {args.backup_table}")
        n_backup = cur.fetchone()[0]
        conn.commit()
        print(f"  backed up {n_backup:,} rows")
        if n_backup < len(all_rows):
            print("ERROR: backup smaller than plan — aborting before any UPDATE.",
                  file=sys.stderr)
            return 2

        written = 0
        for pid, zones, devs, zsrc, dsrc, old_z, old_d in all_rows:
            # Optimistic-concurrency guard: only write if the row still holds the
            # values planning saw. A concurrent edit is skipped, never clobbered.
            cur.execute(
                f"UPDATE {TABLE} SET v2_applicable_zones = %s, "
                f"v2_applicable_dev_types = %s, v2_zone_source = %s, "
                f"v2_dev_type_source = %s "
                # IS NOT DISTINCT FROM, not `=`: 62 rows in scope hold NULL, and
                # `NULL = '{}'` is NULL, so a plain equality guard would silently
                # skip every one of them. Planning coerces NULL to [], so the
                # comparison must treat the two as equal on the SQL side too.
                f"WHERE id = %s "
                f"AND coalesce(v2_applicable_zones, '{{}}') IS NOT DISTINCT FROM %s "
                f"AND coalesce(v2_applicable_dev_types, '{{}}') IS NOT DISTINCT FROM %s",
                (zones, devs, zsrc, dsrc, pid, old_z, old_d),
            )
            written += cur.rowcount
        conn.commit()
        print(f"  updated {written:,} rows ({len(all_rows) - written:,} skipped by the guard)")
        print(f"\nROLLBACK:\n  UPDATE {TABLE} t SET v2_applicable_zones = b.v2_applicable_zones, "
              f"v2_applicable_dev_types = b.v2_applicable_dev_types, "
              f"v2_zone_source = b.v2_zone_source, v2_dev_type_source = b.v2_dev_type_source "
              f"FROM {args.backup_table} b WHERE t.id = b.id;")
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
