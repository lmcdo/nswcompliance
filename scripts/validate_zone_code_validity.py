#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing check validates a stored
# zone code against the live per-LGA zone list. The near neighbours were each
# examined: scripts/validate_dcp_setbacks.py is a semantic validator scoped to one
# table (dcp_setback_controls) asking "is this NUMBER a real setback"; its CONFLICT
# check treats "a condition exists" as disambiguated and so cannot see this class.
# services/extracted_data_integrity.py::conflicting_values has the same blind spot.
# scripts/lint_hardcoded_zone_codes.py (DQ-30 PR4) scans SOURCE CODE, never data.
# This is the data-side gate none of them provide, and it is deliberately written
# table-agnostic so dcp_setback_controls.applies_to_zones becomes one more --target
# when that column lands, rather than a second copy of this logic.
"""Validate that every stored NSW zone code actually exists in its LGA.

WHY THIS EXISTS
---------------
DQ-30 was marked "Fixed" on the strength of a "0% drift" check, which re-ran the
tagger and compared its output to the stored value. That is a SELF-CONSISTENCY
check: if the code itself still emits a retired zone code, drift is 0% and the
data is still wrong. It cannot fail when the bug is present, so it is not a
verification. 286 rows carrying retired B/IN codes — 14 of them live and served —
survived it.

This check can fail. It compares stored codes against `lep_zone_coverage`, the
live-scraped per-LGA land-use table, by exact set membership. No regex, so none
of the `B3`-zone-vs-`Part B3`-chapter ambiguity that makes text scanning
unreliable applies here: these columns hold already-parsed codes.

THE RULE IT ENFORCES
--------------------
For every row: every code in the zone column must appear in `lep_zone_coverage`
for that row's LGA, among rows where `is_complete = TRUE`.

THREE-STATE, NOT PASS/FAIL
--------------------------
Absence of ground truth must never read as a pass — that is how the original
defect hid. Every row lands in exactly one bucket:

  VALID        every code exists for that LGA
  INVALID      at least one code does not exist for that LGA  -> the defect
  UNVERIFIABLE no complete ground truth for that LGA, or no LGA on the row

and separately, as its own reported defect rather than an absorbed silence:

  UNRESOLVED   the row has an LGA slug but it could not be joined to ground
               truth at all. Verified join hazards this catches:
                 * lga_registry.parent_lga stores a SLUG ('inner_west'), not a
                   display name — a naive COALESCE misses 22,007 Inner West rows
                 * 'Ku-ring-gai' (registry) vs 'Ku-Ring-Gai' (ground truth) — case
                 * 'City of Sydney' (registry) vs 'Sydney' (ground truth) — name
               Reporting these loudly turns a registry defect into a finding
               instead of silently skipping a quarter of the corpus.

Read-only. Never writes. Exit 1 when any INVALID row exists (so it can gate).
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

# The wildcard sentinel stored alongside real codes; not a zone, never validated.
WILDCARD = "ALL"

# (table, zone array column, lga column). dcp_setback_controls.applies_to_zones
# joins this list when migration 062 lands — see
# ~/.claude/plans/ce-dcp-condition-structuring-2026-08.md
TARGETS = {
    "regulatory_provisions": ("v2_applicable_zones", "source_council"),
}

# DELIBERATELY NOT A TARGET: `dcp_all_provisions`. It is a VIEW over
# `zz_legacy_dcp_general_provisions` (listed under "NEVER READ — frozen legacy"
# in DB_SCHEMA.md) UNION `dcp_precinct_provisions` (empty). It holds 32 rows with
# invalid zone codes, but a repo-wide grep finds ZERO code reading it, so those
# rows reach no user. Gating on permanently-failing dead data trains people to
# ignore a red check, which costs more than it catches.
# RE-ADD IT the moment anything reads this view or its underlying tables.
_EXCLUDED = {"dcp_all_provisions": "legacy view, no consumers (DB_SCHEMA.md never-read list)"}


def _connect():
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    import psycopg2

    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    return conn, cur


def load_ground_truth(cur) -> dict[str, set[str]]:
    """Complete per-LGA zone lists, keyed case-folded for tolerant joining."""
    cur.execute(
        "SELECT lga, zone FROM lep_zone_coverage "
        "WHERE is_complete = TRUE AND lga IS NOT NULL AND zone IS NOT NULL"
    )
    truth: dict[str, set[str]] = defaultdict(set)
    for lga, zone in cur.fetchall():
        truth[lga.strip().casefold()].add(zone.strip().upper())
    return truth


def load_slug_resolution(cur, truth: dict[str, set[str]]) -> dict[str, str | None]:
    """Map each LGA slug to a ground-truth key, or None if unresolvable.

    Resolution order, widest-first, because a former council's zones are those of
    its CURRENT amalgamated LGA (Marrickville provisions are assessed against
    Inner West's land-use table, not a defunct Marrickville one):
      1. the row's own display_name
      2. its parent's display_name, resolving parent_lga as the slug it is
    Matching is case-folded so 'Ku-ring-gai' reaches 'Ku-Ring-Gai'.
    """
    # prior-art-checked: not a new capability — adds one WHERE predicate to a
    # query already in this same function (added earlier in this branch). The
    # guard's suggestions are unrelated satellite/report modules matched on
    # generic words; is_active=TRUE is the convention already used by every
    # other lga_registry consumer, which is what this adopts rather than invents.
    #
    # An inactive registry entry may carry a stale display_name and would join to
    # the wrong ground truth. Rows whose LGA stops resolving are reported
    # UNRESOLVED, never silently passed.
    cur.execute("SELECT slug, display_name, parent_lga FROM lga_registry "
                "WHERE is_active = TRUE")
    rows = cur.fetchall()
    display_by_slug = {s: (d or "").strip() for s, d, _ in rows}
    parent_by_slug = {s: p for s, _, p in rows}

    resolved: dict[str, str | None] = {}
    for slug in display_by_slug:
        candidates = []
        parent_slug = parent_by_slug.get(slug)
        if parent_slug:
            # parent_lga holds a SLUG; translate it before use.
            candidates.append(display_by_slug.get(parent_slug, parent_slug))
        candidates.append(display_by_slug.get(slug, slug))
        resolved[slug] = next(
            (c.casefold() for c in candidates if c and c.casefold() in truth), None
        )
    return resolved


def validate(cur, table: str, zone_col: str, lga_col: str,
             truth: dict[str, set[str]], resolved: dict[str, str | None]) -> dict:
    cur.execute(
        f"SELECT id, {lga_col}, {zone_col} FROM {table} "
        f"WHERE {zone_col} IS NOT NULL AND cardinality({zone_col}) > 0"
    )
    buckets = {"VALID": 0, "INVALID": 0, "UNVERIFIABLE": 0, "UNRESOLVED": 0}
    invalid_by_lga: dict[str, dict] = defaultdict(
        lambda: {"rows": 0, "codes": set(), "sample_ids": []}
    )
    unresolved_slugs: set[str] = set()
    no_lga_rows = 0

    for row_id, slug, zones in cur.fetchall():
        codes = {z.strip().upper() for z in zones if z and z.strip().upper() != WILDCARD}
        if not codes:
            buckets["VALID"] += 1  # wildcard-only row: nothing to validate
            continue
        if not slug:
            buckets["UNVERIFIABLE"] += 1
            no_lga_rows += 1
            continue
        key = resolved.get(slug)
        if key is None:
            # The LGA column may hold a display name rather than a registry slug
            # (verified: dcp_all_provisions.lga holds 'Inner West'). Try it as a
            # ground-truth key directly before declaring the row unresolvable.
            direct = slug.strip().casefold()
            key = direct if direct in truth else None
        if key is None:
            buckets["UNRESOLVED"] += 1
            unresolved_slugs.add(slug)
            continue
        valid_for_lga = truth[key]
        bad = codes - valid_for_lga
        if bad:
            buckets["INVALID"] += 1
            e = invalid_by_lga[slug]
            e["rows"] += 1
            e["codes"] |= bad
            if len(e["sample_ids"]) < 5:
                e["sample_ids"].append(row_id)
        else:
            buckets["VALID"] += 1

    return {
        "buckets": buckets,
        "invalid_by_lga": invalid_by_lga,
        "unresolved_slugs": unresolved_slugs,
        "no_lga_rows": no_lga_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", action="append", choices=sorted(TARGETS),
                    help="Table to validate (repeatable; default: all).")
    ap.add_argument("--quiet", action="store_true", help="Summary lines only.")
    args = ap.parse_args()

    conn, cur = _connect()
    try:
        truth = load_ground_truth(cur)
        resolved = load_slug_resolution(cur, truth)
        if not truth:
            print("ERROR: lep_zone_coverage has no complete rows — cannot verify "
                  "anything. This is a blocker, not a pass.", file=sys.stderr)
            return 2

        any_invalid = False
        for table in (args.target or sorted(TARGETS)):
            zone_col, lga_col = TARGETS[table]
            r = validate(cur, table, zone_col, lga_col, truth, resolved)
            b = r["buckets"]
            total = sum(b.values())
            print(f"\n=== {table}.{zone_col} ({total} rows with zone codes) ===")
            print(f"  VALID        {b['VALID']}")
            print(f"  INVALID      {b['INVALID']}   <- codes not in this LGA's land-use table")
            print(f"  UNVERIFIABLE {b['UNVERIFIABLE']}   ({r['no_lga_rows']} have no LGA on the row)")
            print(f"  UNRESOLVED   {b['UNRESOLVED']}   <- LGA present but not joinable to ground truth")

            if b["INVALID"]:
                any_invalid = True
                if not args.quiet:
                    print("  invalid detail (lga -> offending codes, sample ids):")
                    for slug, e in sorted(r["invalid_by_lga"].items(),
                                          key=lambda kv: -kv[1]["rows"]):
                        print(f"    {slug}: {e['rows']} rows, codes "
                              f"{sorted(e['codes'])}, ids {e['sample_ids']}")
            if r["unresolved_slugs"]:
                print(f"  UNRESOLVED slugs (fix lga_registry / lep_zone_coverage naming): "
                      f"{sorted(r['unresolved_slugs'])}")

        print("\nNote: UNVERIFIABLE and UNRESOLVED are NOT passes. A row is only "
              "verified when its LGA has complete ground-truth coverage.")
        if any_invalid:
            print("\nFAILED: stored zone codes do not exist in their LGA's land-use table.")
            return 1
        print("\nPASSED: every verifiable stored zone code exists in its LGA.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
