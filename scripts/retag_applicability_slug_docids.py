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

THE COUNCIL LIST IS AN ARGUMENT, NOT A CONSTANT (2026-09-23)
------------------------------------------------------------
It was hardcoded to the three Inner West councils the slug fix was written for,
which made every number this script printed -- including "no_config served" --
silently scoped to those three while reading like a global measurement. Pass
--councils to run it anywhere a config was added.

AND "NARROWED" NOW MEANS NARROWED. The two counters named served_zone_narrowed
and served_devtype_narrowed tested `!=`, so they counted every change in either
direction. Widening to ALL is noise; narrowing hides a binding control, and that
is the only number worth gating on. They are now classified properly, printed
apart, and --apply refuses unless --expect-narrowings names the exact count, so
nobody applies a narrowing without having looked at one.

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
from datetime import datetime
from collections import Counter

#: Default scope: the three councils the 2026-08-01 slug fix was written for.
#: Override with --councils; see the docstring for why this is not a constant.
DEFAULT_COUNCILS = ("marrickville", "ashfield", "leichhardt")


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


def classify(old: list, new: list) -> str:
    """How a tag VALUE moved: the direction is the risk, not the fact of change.

    `narrowed` is the only outcome that can hide a binding control from a
    property it applies to, because both v2_applicable_zones and
    v2_applicable_dev_types are HARD filters on the served answer
    (frontend-nextjs/app/api/provisions/for-property/route.ts:1012 and :1222,
    and app/api/permissibility/check/route.ts:207). A row survives only if the
    column is NULL, holds 'ALL', or overlaps the query.

    `['ALL']` and `[]` are the same state here -- "applies to everything" -- so
    losing ALL for a named list is `narrowed_from_all`, not a swap.
    """
    o, n = set(old or []), set(new or [])
    if o == n:
        return "same"
    o_all = (not o) or o == {"ALL"}
    n_all = n == {"ALL"}
    if o_all and not n_all:
        return "narrowed_from_all"
    if n_all and not o_all:
        return "widened_to_all"
    if o_all and n_all:
        return "same"
    if n < o:
        return "narrowed"
    if n > o:
        return "widened"
    return "swapped"


#: Outcomes that remove a row from some property's answer. A `swapped` value
#: loses at least one member it used to carry, so it counts here too.
NARROWING = ("narrowed", "narrowed_from_all", "swapped")


def build_plan(cur, councils):
    """Rows whose tag VALUES change, plus the provenance for every row in scope."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from enrichment.extractors.applicability_tagger import ApplicabilityTagger

    cur.execute(
        f"""SELECT is_current AND v2_is_actionable AS served,
                   id, document_id, provision_text,
                   v2_applicable_zones, v2_applicable_dev_types
            FROM {TABLE} WHERE source_council = ANY(%s)""",
        (list(councils),),
    )
    tagger = ApplicabilityTagger()
    plan, prov_only, narrowings = [], [], []
    stats = Counter()
    for served, pid, doc, txt, old_z, old_d in cur.fetchall():
        zones, devs, prov = tagger.tag_with_provenance(txt or "", doc)
        old_z, old_d = list(old_z or []), list(old_d or [])
        # BOTH sources, keyed by which column they describe. This used to
        # record zone_source alone, so the "predicted provenance after"
        # block reported zones while the ratchet it exists to serve --
        # DQ-33 -- counts v2_dev_type_source. The two differ: 7 served
        # canterbury_bankstown rows resolve no_config on zones and
        # text_regex on dev types (2026-09-23), so the zone-only view
        # showed work outstanding that DQ-33 does not count, and would
        # equally have hidden the reverse.
        kind = "served" if served else "other"
        stats[("zone", prov["zone_source"], kind)] += 1
        stats[("devtype", prov["dev_type_source"], kind)] += 1
        row = (pid, zones, devs, prov["zone_source"], prov["dev_type_source"],
               old_z, old_d)
        if zones != old_z or devs != old_d:
            plan.append(row)
            if served:
                zk, dk = classify(old_z, zones), classify(old_d, devs)
                stats[f"served_zone_{zk}"] += 1
                stats[f"served_devtype_{dk}"] += 1
                if zk in NARROWING:
                    narrowings.append((pid, doc, "zones", old_z, zones, zk))
                if dk in NARROWING:
                    narrowings.append((pid, doc, "dev_types", old_d, devs, dk))
        else:
            prov_only.append(row)
    return plan, prov_only, stats, narrowings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--councils", nargs="+", default=list(DEFAULT_COUNCILS),
                    help="source_council slugs to re-tag (default: the three "
                         "Inner West councils the 2026-08-01 slug fix targeted).")
    ap.add_argument("--backup-table", default=None,
                    help="Defaults to a timestamped name. The table must NOT "
                         "already exist -- see the abort below.")
    ap.add_argument("--expect-narrowings", type=int, default=None,
                    help="Required with --apply when the plan narrows any served "
                         "row. Must equal the printed count exactly.")
    ap.add_argument("--limit-print", type=int, default=15)
    args = ap.parse_args()
    backup_table = args.backup_table or (
        "regulatory_provisions_dq33_backup_"
        + datetime.now().strftime("%Y%m%d_%H%M%S"))

    conn, cur = _connect()
    try:
        plan, prov_only, stats, narrowings = build_plan(cur, args.councils)
        print(f"\n=== DQ-33 re-tag plan ===")
        print(f"  councils                 : {', '.join(args.councils)}")
        print(f"  rows in scope            : {len(plan) + len(prov_only):,}")
        print(f"  VALUES change            : {len(plan):,}")
        print(f"  provenance only          : {len(prov_only):,}")
        for field in ("zone", "devtype"):
            pre = f"served_{field}_"
            # `stats` mixes tuple keys (source, served-ness) with these string
            # counters, and str/tuple do not compare -- filter before sorting.
            parts = [f"{k[len(pre):]} {v:,}" for k, v in
                     sorted((kv for kv in stats.items()
                             if isinstance(kv[0], str) and kv[0].startswith(pre)))]
            print(f"  served {field:<8} changes  : " + (", ".join(parts) or "none"))
        print(f"  SERVED ROWS NARROWED     : {len(narrowings):,}"
              "   <- the only direction that can hide a control")
        # Grouped, not listed. 201 narrowings on 2026-09-23 were 8 distinct
        # shapes repeated; printing them one per row buries the 8 decisions an
        # operator actually has to make under 200 identical lines.
        shapes = {}
        for pid, doc, field, before, after, kind in narrowings:
            shapes.setdefault(
                (doc, field, kind, tuple(before), tuple(after)), []).append(pid)
        print(f"  distinct narrowing shapes : {len(shapes):,}")
        for (doc, field, kind, before, after), pids in sorted(
                shapes.items(), key=lambda kv: -len(kv[1])):
            print(f"    {len(pids):>5,} row(s)  {field} {kind}: "
                  f"{list(before)} -> {list(after)}")
            print(f"            {doc}")
            print(f"            e.g. id={pids[0]}")
        print("\n  predicted provenance after:")
        # `stats` mixes tuple keys (source, served-ness) with two plain string
        # counters, so filter by key SHAPE before unpacking rather than assuming.
        prov = {k: v for k, v in stats.items() if isinstance(k, tuple)}
        for (col, src, kind), n in sorted(prov.items(), key=lambda kv: -kv[1]):
            flag = "  <- DQ-33 counts this" if (col, src, kind) == (
                "devtype", "no_config", "served") else ""
            print(f"    {col:<8} {src:<16} {kind:<7} {n:>7,}{flag}")

        print(f"\n  sample of value changes (first {args.limit_print}):")
        for pid, z, d, zs, _ds, oz, od in plan[:args.limit_print]:
            print(f"    id={pid:<7} zones {oz} -> {z}   src={zs}")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0

        if narrowings and args.expect_narrowings != len(narrowings):
            print(f"ERROR: the plan narrows {len(narrowings):,} served row(s) and "
                  f"--expect-narrowings is {args.expect_narrowings}. Read the list "
                  f"above, then pass the exact count. Nothing was written.",
                  file=sys.stderr)
            return 2

        all_rows = plan + prov_only
        ids = [r[0] for r in all_rows]
        # NOT "IF NOT EXISTS". A name that already holds a table makes that form
        # a no-op, and the row-count guard below then passes against the OLD
        # contents -- 22,007 rows from 2026-08-01 are still sitting under this
        # script's former default name, so every later run with the default was
        # one keystroke from writing with no usable rollback.
        cur.execute("SELECT to_regclass(%s)", (backup_table,))
        if cur.fetchone()[0] is not None:
            print(f"ERROR: backup table {backup_table} already exists. Pick "
                  f"another name; nothing was written.", file=sys.stderr)
            return 2
        print(f"\nCreating backup table {backup_table} ...")
        cur.execute(
            f"CREATE TABLE {backup_table} AS "
            f"SELECT id, v2_applicable_zones, v2_applicable_dev_types, "
            f"       v2_zone_source, v2_dev_type_source "
            f"FROM {TABLE} WHERE id = ANY(%s)",
            (ids,),
        )
        cur.execute(f"SELECT count(*) FROM {backup_table}")
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
              f"FROM {backup_table} b WHERE t.id = b.id;")
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
