#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing script repairs stored
# zone codes. scripts/validate_zone_code_validity.py (this PR) DETECTS the defect
# but is read-only by design; enrichment/pipeline.py::run_applicability_tagging
# only fills rows WHERE v2_applicable_zones IS NULL and re-deriving from text was
# measured to fix 0 of 241 rows (it re-runs the same regex that caused them).
# scripts/fixes/DQ*.py are one-off historical repairs for other columns. This is
# the targeted repair for this column, sharing validate_zone_code_validity.py's
# ground-truth resolution rather than reimplementing it.
"""Repair stored zone codes that do not exist in their LGA (DQ-30).

WHAT IT DOES
------------
For every row whose zone array contains a code absent from `lep_zone_coverage`
for that LGA, remove the offending codes. If nothing survives, store ``['ALL']``
— the honest "applicability undetermined" state, identical to what the tagger
produces when it finds no zone evidence at all.

WHY NOT JUST RE-RUN THE TAGGER
------------------------------
Measured against production: re-deriving these rows from text fixes **0 of 241**,
because they come from the blind text-regex fallback that produced them in the
first place ("Part B3" matching as zone B3). Re-running unchanged code reproduces
the same output — which is also why the old "0% drift" check reported success.
Intersecting the STORED value is both minimal and sufficient: valid codes are
kept, invalid ones dropped, and no other field is touched.

SAFETY
------
* --dry-run (default) writes nothing and prints the exact plan.
* --apply requires a backup table to exist; it is created automatically first.
* Per-row UPDATE guarded by optimistic concurrency on the pre-change value, so a
  concurrent writer cannot be silently clobbered.
* statement_timeout 30s. Never TRUNCATE/DROP. Always WHERE-scoped by id.
* Verify afterwards with: python scripts/validate_zone_code_validity.py
  (that check CAN fail, which is the point — see DQ-30 in the tracker).
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

WILDCARD = "ALL"
TARGET_TABLE = "regulatory_provisions"
ZONE_COL = "v2_applicable_zones"
LGA_COL = "source_council"

# NO is_current / v2_is_actionable FILTER — deliberate, not an oversight.
# The usual currency guard exists to stop STALE rows being SERVED. This script
# does the opposite job: it repairs stored data. Restricting it to is_current
# would knowingly leave 129 superseded rows holding zone codes that do not exist
# — wrong data that becomes live the moment a row is revived or re-read. Repair
# covers every row; the currency decision belongs to the read path, not here.


def _connect():
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    import psycopg2

    conn = psycopg2.connect(url)
    conn.autocommit = False  # explicit transactions for the write path
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    return conn, cur


def _ground_truth(cur):
    cur.execute(
        "SELECT lga, zone FROM lep_zone_coverage "
        "WHERE is_complete = TRUE AND lga IS NOT NULL AND zone IS NOT NULL"
    )
    truth = defaultdict(set)
    for lga, z in cur.fetchall():
        truth[lga.strip().casefold()].add(z.strip().upper())
    return truth


def _resolver(cur, truth):
    """Slug -> ground-truth key. Mirrors validate_zone_code_validity.py exactly;
    parent_lga holds a SLUG, and names differ in case ('Ku-ring-gai' vs
    'Ku-Ring-Gai') and in form ('City of Sydney' vs 'Sydney')."""
    cur.execute("SELECT slug, display_name, parent_lga FROM lga_registry")
    rows = cur.fetchall()
    disp = {s: (d or "").strip() for s, d, _ in rows}
    par = {s: p for s, _, p in rows}

    def resolve(slug):
        if not slug:
            return None
        cands = []
        if par.get(slug):
            cands.append(disp.get(par[slug], par[slug]))
        cands.append(disp.get(slug, slug))
        cands.append(slug)
        for c in cands:
            if c and c.strip().casefold() in truth:
                return c.strip().casefold()
        return None

    return resolve


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Actually write. Omit for a dry run (the default).")
    ap.add_argument("--backup-table", default="regulatory_provisions_zone_backup_20260801")
    args = ap.parse_args()

    conn, cur = _connect()
    try:
        truth = _ground_truth(cur)
        if not truth:
            print("ERROR: no complete lep_zone_coverage rows — refusing to run.",
                  file=sys.stderr)
            return 2
        resolve = _resolver(cur, truth)

        cur.execute(
            f"SELECT id, {LGA_COL}, {ZONE_COL} FROM {TARGET_TABLE} "
            f"WHERE {ZONE_COL} IS NOT NULL AND cardinality({ZONE_COL}) > 0 "
            f"AND {LGA_COL} IS NOT NULL"
        )
        plan = []
        for rid, slug, zones in cur.fetchall():
            key = resolve(slug)
            if key is None:
                continue  # unverifiable — never guessed at, never written
            before = list(zones)
            codes = [z for z in before if z and z.strip().upper() != WILDCARD]
            bad = [z for z in codes if z.strip().upper() not in truth[key]]
            if not bad:
                continue
            kept = sorted({z for z in codes if z.strip().upper() in truth[key]})
            after = kept if kept else [WILDCARD]
            plan.append((rid, slug, before, after, bad))

        if not plan:
            print("Nothing to repair — every resolvable row already valid.")
            return 0

        by_lga = defaultdict(lambda: {"n": 0, "to_all": 0})
        for _, slug, _, after, _ in plan:
            by_lga[slug]["n"] += 1
            if after == [WILDCARD]:
                by_lga[slug]["to_all"] += 1

        print(f"Rows to repair: {len(plan)}")
        print(f"{'council':<22}{'rows':>6}{'-> ALL (all codes bogus)':>28}")
        for slug, s in sorted(by_lga.items(), key=lambda kv: -kv[1]["n"]):
            print(f"{slug:<22}{s['n']:>6}{s['to_all']:>28}")
        print("\nSamples:")
        for rid, slug, before, after, bad in plan[:8]:
            print(f"  id={rid} {slug}: {before} -> {after}   (dropped {sorted(bad)})")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0

        # ---- write path ----
        print(f"\nCreating backup table {args.backup_table} ...")
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
            f"SELECT id, {ZONE_COL}, v2_applicable_dev_types, {LGA_COL} "
            f"FROM {TARGET_TABLE} WHERE id = ANY(%s)",
            ([r[0] for r in plan],),
        )
        cur.execute(f"SELECT count(*) FROM {args.backup_table}")
        n_backup = cur.fetchone()[0]
        conn.commit()
        print(f"  backed up {n_backup} rows")
        if n_backup < len(plan):
            print("ERROR: backup smaller than plan — aborting before any UPDATE.",
                  file=sys.stderr)
            return 2

        updated = skipped = 0
        for rid, _slug, before, after, _bad in plan:
            # Optimistic concurrency: only write if the row still holds the value
            # this plan was computed from.
            cur.execute(
                f"UPDATE {TARGET_TABLE} SET {ZONE_COL} = %s "
                f"WHERE id = %s AND {ZONE_COL} = %s",
                (after, rid, before),
            )
            if cur.rowcount == 1:
                updated += 1
            else:
                skipped += 1
        conn.commit()
        print(f"\nUpdated {updated} rows; {skipped} skipped (changed underneath).")
        print(f"Rollback: UPDATE {TARGET_TABLE} t SET {ZONE_COL} = b.{ZONE_COL} "
              f"FROM {args.backup_table} b WHERE t.id = b.id;")
        print("\nNow verify: python scripts/validate_zone_code_validity.py")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
