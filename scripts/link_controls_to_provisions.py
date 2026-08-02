#!/usr/bin/env python3
# prior-art-checked: reuse not viable because nothing links dcp_setback_controls to
# regulatory_provisions. Checked: scripts/validate_controls_provenance.py (#866)
# classifies provenance but writes nothing; scripts/backfill_invalid_zone_codes.py
# and scripts/retag_applicability_slug_docids.py are the SAFETY shape copied here
# (dry-run default, backup table, per-row optimistic guard, printed rollback) but
# repair different columns from different sources; enrichment/ has no linker.
# The lga -> source_council resolution reuses the lga_registry approach from #854
# rather than a new mapping, because slug/display_name drift is exactly what that
# PR existed to fix.
"""Link a numeric control to the provision its value was read from.

WHY
---
scripts/validate_controls_provenance.py puts every control in one of three states.
State (b) `traceable` means "a human can re-check this against its clause" — 535
rows sit there, and re-checking them is manual. A `provision_id` turns that into
something a machine can do: the clause text is one join away, so the stored number
can be compared against its own source automatically.

THE CEILING — measured 2026-08-02, BEFORE writing anything
----------------------------------------------------------
Only 41 of 1,069 controls can be linked with confidence. The rest are blocked by
corpus coverage, not by matching:

    exactly one CURRENT provision contains the quote  41   <- linkable
    multiple provisions match (ambiguous)              2   <- left NULL deliberately
    no provision contains the quote                  545   <- chapter not ingested
    council has NO provisions at all                 450   <- 14 LGAs, never ingested
    quote too short to be distinctive                 31   <- under 30 chars

Restricting the candidate set to current, actionable provisions IMPROVED this: it
removes superseded duplicates of the same clause, so ambiguity fell from 23 to 2
and linkable rose from 35 to 41. Filtering for correctness made the numbers better,
not worse — worth noting, because the first version linked 3 rows to a superseded
Marrickville provision before the filter existed.

So this is not the fix for the other 1,034. Making them linkable means ingesting
those councils' DCP chapters, which is extraction work and out of scope per
docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md. It IS written to be
re-run: as corpus coverage grows, re-running links more rows with no code change,
which is why this exists as a repeatable script rather than a one-off backfill.

DIRECTION OF RISK
-----------------
A WRONG link is worse than no link, because it would let a later check compare a
number against someone else's clause and report a confident false verdict. So:

  * a link is written ONLY when exactly one provision in that council contains the
    control's quoted text — never the best or the nearest match;
  * ambiguous and unmatched rows stay NULL, and both counts are reported rather
    than minimised;
  * matching is substring containment over normalised text, not fuzzy similarity —
    there is no score to tune and no threshold to get subtly wrong;
  * --dry-run is the default.

SAFETY
------
Backup table first, aborts if the backup is smaller than the plan, per-row UPDATE
guarded on the value read during planning, 30s statement timeout, rollback SQL
printed on completion.

WHAT READS provision_id — corrected 2026-08-02
----------------------------------------------
An earlier version of this docstring said "nothing reads provision_id (verified by
grep)". Retracted: the grep it cited had not finished when its output was read.
Re-checked, three readers exist and none of them renders the column:

  * frontend-nextjs/app/api/internal/setback-review/[id]/route.ts — SELECTs it only
    to copy onto the superseding row when a reviewer corrects a value. NULL carries
    through as NULL and the column is never returned to the client.
  * scripts/validate_dcp_health.py — orphaned-backlink check. Clearing a stale link
    REMOVES a finding there; it cannot create one.
  * scripts/verify_setback_source_texts.py — LEFT JOIN, prints '' when NULL.

Not a reader despite appearances: the "Referenced Legislation" accordion
(components/compliance/ReferencedLegislationAccordion.tsx) takes its provision_id
from regulatory_provisions_clean / quantitative_standards via
lib/database/prp-k7-client.ts — a different table. It also guards NULL
(`{ref.provision_id && ...}`), so a missing id drops the "View Full Text" button
rather than erroring, and its only mount point (components/dashboard/AnalysisTabs.tsx)
is imported by nothing.

So a NULL provision_id degrades to "no link shown", which is already the state of
1,027 of the 1,069 rows. No served output changes either way.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict

# A quote shorter than this is not distinctive enough to identify a clause — it
# would match many provisions and the "exactly one" rule would quietly become a
# coin toss. Rows below it are reported, never linked.
MIN_QUOTE_CHARS = 30

# The extractors append a citation to source_text ("... (Ashfield DCP 2016 DS18.5)")
# which is NOT part of the provision text, so it must come off before matching or
# rows fail to match for the wrong reason and the ceiling reads as worse than it is.
_CITATION = re.compile(
    r"\s*\([^()]*(?:dcp|lep|sepp|part|table|clause|s\d)[^()]*\)\s*$", re.I)

# Every control lands in exactly one of these, so the counts always sum to the
# table size. `already_linked_correctly` is a subset of `linkable`, not an outcome.
OUTCOMES = ("linkable", "ambiguous_multiple_provisions",
            "no_provision_contains_the_quote", "council_has_no_provisions",
            "quote_too_short")

# An existing non-NULL provision_id is NEVER overwritten. Found while dry-running:
# the one pre-existing link (control 3 -> provision 98149) was made by a different
# method, and this matcher resolves the same control to 97850 — the same clause
# exists as more than one provision row, so "exactly one substring match" can
# legitimately land on a different duplicate than a human chose. There is no
# deterministic way to say which is right, so the human's link stands and the
# disagreement is reported.
PRESERVE_EXISTING_LINKS = True


def normalise(text: str | None) -> str:
    """Lowercase and collapse whitespace. Nothing else — no stemming, no fuzzing."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def quoted_clause(source_text: str | None) -> str:
    """The part of source_text that should appear in the provision itself."""
    return _CITATION.sub("", normalise(source_text)).strip()


def find_single_match(quote: str, provisions: list[tuple]) -> tuple[int | None, int]:
    """Return (provision_id, hit_count). The id is set only when exactly one hits.

    Pure and DB-free so both failure directions can be tested: a quote matching
    nothing, and a quote matching several provisions, must BOTH yield None.
    """
    if len(quote) < MIN_QUOTE_CHARS:
        return None, 0
    hits = [pid for pid, text in provisions if quote in text]
    return (hits[0] if len(hits) == 1 else None), len(hits)


def classify(quote: str, provisions: list[tuple]) -> str:
    """The outcome name for one control, given its council's provisions."""
    if not provisions:
        return "council_has_no_provisions"
    if len(quote) < MIN_QUOTE_CHARS:
        return "quote_too_short"
    _, count = find_single_match(quote, provisions)
    if count == 1:
        return "linkable"
    return ("ambiguous_multiple_provisions" if count > 1
            else "no_provision_contains_the_quote")


def build_plan(cur) -> tuple[list[tuple], Counter]:
    """Rows resolving to exactly one provision, plus the full outcome breakdown."""
    cur.execute(
        """SELECT id, lga, control_type, source_text, provision_id
           FROM dcp_setback_controls ORDER BY lga, id"""
    )
    columns = [d[0] for d in cur.description]
    by_lga: dict[str, list[dict]] = defaultdict(list)
    for record in cur.fetchall():
        row = dict(zip(columns, record))
        by_lga[row["lga"]].append(row)

    plan: list[tuple] = []
    stats: Counter = Counter()
    for lga, rows in by_lga.items():
        # lga is an lga_registry slug; provisions are keyed by source_council, which
        # holds either the slug or the display name depending on the ingestion (only
        # 16 of 30 match exactly). Resolved through the registry, never a hand map.
        cur.execute(
            # is_current AND v2_is_actionable is REQUIRED, not optional: linking to a
            # superseded clause would let a later check compare a live number against
            # withdrawn text and report a confident false verdict. Measured before
            # adding it — 3 of the first 35 links pointed at superseded provisions.
            # r.is_active guards the resolution side; all 30 control LGAs are active
            # today, so this narrows nothing now and fails visibly if one is retired.
            """SELECT p.id, p.provision_text
               FROM regulatory_provisions p
               LEFT JOIN lga_registry r ON r.slug = %s AND r.is_active
               WHERE p.is_current AND p.v2_is_actionable
                 AND (p.source_council = %s
                   OR lower(p.source_council) = lower(r.display_name)
                   OR lower(replace(p.source_council, ' ', '_')) = %s)""",
            (lga, lga, lga),
        )
        provisions = [(pid, normalise(text)) for pid, text in cur.fetchall()]
        current_ids = {pid for pid, _ in provisions}
        for row in rows:
            quote = quoted_clause(row["source_text"])
            outcome = classify(quote, provisions)
            stats[outcome] += 1
            provision_id, _ = find_single_match(quote, provisions)
            # A link pointing OUTSIDE the current set is stale, whatever the outcome.
            # Handled before the outcome branch because a stale link on a row that no
            # longer matches anything current would otherwise be silently retained —
            # the first version of this script did exactly that.
            stale = (row["provision_id"] is not None
                     and row["provision_id"] not in current_ids)
            if stale:
                # Cleared rather than kept when nothing current matches: pointing at
                # withdrawn text is worse than admitting there is no link.
                stats["stale_link_repointed" if provision_id
                      else "stale_link_cleared"] += 1
                plan.append((row["id"], provision_id, row["provision_id"]))
                continue
            if outcome != "linkable":
                continue
            if provision_id == row["provision_id"]:
                stats["already_linked_correctly"] += 1
            elif row["provision_id"] is not None and PRESERVE_EXISTING_LINKS:
                # Points into the current set but at a different row — a genuine
                # disagreement between a human's choice and this matcher. Reported,
                # never overwritten.
                stats["disagrees_with_existing_link"] += 1
            else:
                plan.append((row["id"], provision_id, row["provision_id"]))
    return plan, stats


def main() -> int:  # pragma: no cover - CLI entry point
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Execute. Without this nothing is written.")
    parser.add_argument("--backup-table",
                        default="dcp_setback_controls_provlink_backup_20260802")
    parser.add_argument("--limit-print", type=int, default=20)
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is not a "
              "pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    try:
        plan, stats = build_plan(cur)
        print("\n=== control -> provision link plan ===")
        print(f"  controls examined                  : "
              f"{sum(stats[k] for k in OUTCOMES):>5}")
        for key in OUTCOMES:
            print(f"  {key:<35}: {stats[key]:>5}")
        print(f"  of the linkable, already correct   : "
              f"{stats['already_linked_correctly']:>5}")
        print(f"  stale link re-pointed to a current row: "
              f"{stats['stale_link_repointed']:>5}")
        print(f"  stale link CLEARED (nothing current matches): "
              f"{stats['stale_link_cleared']:>5}")
        print(f"  of the linkable, existing link kept: "
              f"{stats['disagrees_with_existing_link']:>5}   "
              f"(a human's link is never overwritten)")
        print(f"  rows this run would WRITE          : {len(plan):>5}")
        print("\n  Not a defect list. Ambiguous and unmatched rows stay NULL on"
              "\n  purpose — a wrong link would let a later check compare a number"
              "\n  against someone else's clause and report a false verdict.")
        print(f"\n  sample (first {args.limit_print}):")
        for control_id, provision_id, previous in plan[:args.limit_print]:
            print(f"    control {control_id} -> provision {provision_id} "
                  f"(was {previous})")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0
        if not plan:
            print("\nNothing to write.")
            return 0

        ids = [row[0] for row in plan]
        print(f"\nCreating backup table {args.backup_table} ...")
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
            f"SELECT id, provision_id, is_current FROM dcp_setback_controls "
            f"WHERE id = ANY(%s)",
            (ids,),
        )
        # A row-COUNT check is not enough. CREATE TABLE IF NOT EXISTS silently
        # keeps a previous run's table, and an earlier backup of 34 different rows
        # would satisfy `count >= 13` while covering none of the rows about to
        # change. So assert every planned id is actually present.
        cur.execute(f"SELECT count(*) FROM {args.backup_table}")
        backed_up = cur.fetchone()[0]
        cur.execute(
            f"SELECT count(*) FROM unnest(%s::int[]) AS wanted(id) "
            f"WHERE NOT EXISTS (SELECT 1 FROM {args.backup_table} b "
            f"                  WHERE b.id = wanted.id)",
            (ids,),
        )
        missing = cur.fetchone()[0]
        conn.commit()
        print(f"  backed up {backed_up:,} rows ({missing} planned rows missing)")
        if missing:
            print(f"ERROR: {missing} of {len(plan)} rows about to change are NOT in "
                  f"{args.backup_table} — it is from an earlier run and cannot roll "
                  f"this one back. Pass --backup-table with a fresh name. Aborting "
                  f"before any UPDATE.", file=sys.stderr)
            return 2

        written = 0
        skipped: list[int] = []
        for control_id, provision_id, previous in plan:
            # Optimistic-concurrency guard. IS NOT DISTINCT FROM, not `=`: the
            # previous value is almost always NULL here and `NULL = NULL` is NULL,
            # so a plain equality guard would silently skip every single row — the
            # exact defect found in the DQ-33 re-tag before it ran.
            cur.execute(
                """UPDATE dcp_setback_controls SET provision_id = %s
                   WHERE id = %s AND provision_id IS NOT DISTINCT FROM %s""",
                (provision_id, control_id, previous),
            )
            if cur.rowcount:
                written += cur.rowcount
            else:
                skipped.append(control_id)
        conn.commit()
        print(f"  updated {written:,} rows ({len(skipped):,} skipped by the guard)")
        print(f"\nROLLBACK:\n  UPDATE dcp_setback_controls t SET provision_id = "
              f"b.provision_id FROM {args.backup_table} b WHERE t.id = b.id;")
        if skipped:
            # A partial apply used to print the skip count and still exit 0, so a
            # scheduled re-run would report success having done half the repair.
            # It exits 2 instead. The successful UPDATEs are NOT rolled back: each
            # one is independently correct, and discarding correct links to punish
            # an unrelated concurrent edit would lose real work. The plan is stale,
            # not wrong — re-running rebuilds it against current values.
            print(f"\nPARTIAL APPLY: {len(skipped)} of {len(plan)} planned rows were "
                  f"skipped because their provision_id changed after planning — "
                  f"controls {skipped}. The {written} writes that succeeded stand "
                  f"and are correct; re-run to rebuild the plan for the rest. "
                  f"Exiting 2 so this is not read as a clean run.", file=sys.stderr)
            return 2
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
