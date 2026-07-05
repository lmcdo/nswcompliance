#!/usr/bin/env python3
# prior-art-checked: no existing end-to-end DCP health validator. scripts/verify_dcp_formatting.py
# checks TEXT FORMATTING artifacts (headers, bullets, topic distribution) for a single council;
# this checks the LIVE-DATA integrity a commit can break (enrichment gaps, orphaned numeric
# backlinks, duplicate is_current) across councils. Different concern, no overlap.
"""
DCP health validator — run after committing a council (or over everything at the end).

Confirms the end-user UI will show correct provisions after an AI baseline swap. Checks,
per council:

  1. ENRICHMENT GAP  — live provisions with v2_is_actionable IS NULL. The UI filters and
     groups by the v2_* tags, so an unenriched provision is invisible. Should be 0.
  2. ORPHANED BACKLINK — dcp_setback_controls.provision_id pointing at a missing or
     superseded provision. The number is safe (stored on the control) but the "source
     clause" link is broken. --fix-backlinks re-points it to the current provision that
     shares the same section_ref.
  3. DUPLICATE is_current — the same (council, chapter_key, ref_number) live more than once.
     A commit should leave exactly one current version per code.
  4. REGISTRY FANOUT — duplicate active (council, chapter_key) rows in
     dcp_chapter_registry. A duplicated key multiplies every joined control row in
     the structured-controls API output. Must be 0.
  5. MIXED DCP NAMES — an LGA whose live numeric controls resolve to >1 distinct
     dcp_name through the council-scoped registry join (the join the API uses).
     Contamination or inconsistent registry naming; users see mixed citations.

Read-only by default. --fix-backlinks performs ONLY the backlink re-point (bounded, logged).

Exit codes: 0 = healthy, 1 = one or more issues found.

Usage:
    python scripts/validate_dcp_health.py                 # all AI-reviewed councils
    python scripts/validate_dcp_health.py --council ashfield
    python scripts/validate_dcp_health.py --fix-backlinks # re-point orphaned numeric links
"""

import argparse
import os
import sys

import psycopg2


def _connect():
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        print("ERROR: set DATABASE_URL (or SUPABASE_DB_URL).", file=sys.stderr)
        sys.exit(2)
    return psycopg2.connect(dsn)


def _councils(cur, council: str | None) -> list[str]:
    if council:
        return [council]
    cur.execute(
        "SELECT DISTINCT source_council FROM regulatory_provisions "
        "WHERE is_current = TRUE AND extraction_method = 'ai-reviewed' "
        "ORDER BY source_council"
    )
    return [r[0] for r in cur.fetchall()]


def enrichment_gap(cur, council: str) -> int:
    """Live provisions with no actionability tag — invisible to the UI."""
    cur.execute(
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE source_council = %s AND is_current = TRUE AND v2_is_actionable IS NULL",
        (council,),
    )
    return cur.fetchone()[0]


def duplicate_current(cur, council: str) -> int:
    """A code that is live more than once — a commit should supersede the old version."""
    cur.execute(
        """
        SELECT count(*) FROM (
            SELECT source_chapter_key, ref_number
            FROM regulatory_provisions
            WHERE source_council = %s AND is_current = TRUE
            GROUP BY source_chapter_key, ref_number
            HAVING count(*) > 1
        ) d
        """,
        (council,),
    )
    return cur.fetchone()[0]


def orphaned_backlinks(cur) -> list[int]:
    """Numeric-control provision_id links (any LGA) pointing at a missing/superseded
    provision. Global check — only a handful of controls hard-link a provision at all."""
    cur.execute(
        """
        SELECT s.id
        FROM dcp_setback_controls s
        LEFT JOIN regulatory_provisions p ON p.id = s.provision_id
        WHERE s.provision_id IS NOT NULL
          AND (p.id IS NULL OR p.is_current = FALSE)
        """
    )
    return [r[0] for r in cur.fetchall()]


def registry_fanout_duplicates(cur) -> list[tuple[str, str, int]]:
    """Active registry rows sharing the same (council, chapter_key). This is the
    mechanism of the cross-council contamination bug at the within-council level:
    a duplicated key multiplies every joined control row in the API output.
    Must always be 0."""
    cur.execute(
        """
        SELECT council, chapter_key, count(*)
        FROM dcp_chapter_registry
        WHERE is_active = TRUE
        GROUP BY council, chapter_key
        HAVING count(*) > 1
        ORDER BY council, chapter_key
        """
    )
    return [(r[0], r[1], r[2]) for r in cur.fetchall()]


def dcp_name_variance(cur) -> list[tuple[str, list[str]]]:
    """LGAs whose live numeric controls resolve to more than one registry DCP name
    through the council-scoped join the API uses. One LGA slug = one former-council
    DCP, so >1 name means either contamination (bad ingest / migration writing the
    wrong lga) or inconsistent registry naming across a council's chapters — both
    surface to end users as mixed citations. DB-layer version of the API sweep
    that caught the cross-council leak."""
    cur.execute(
        """
        SELECT sc.lga, array_agg(DISTINCT cr.dcp_name ORDER BY cr.dcp_name)
        FROM dcp_setback_controls sc
        JOIN dcp_chapter_registry cr
          ON cr.chapter_key = sc.source_chapter_key
         AND cr.council = sc.lga
         AND cr.is_active = TRUE
        WHERE (sc.is_current IS NULL OR sc.is_current = TRUE)
        GROUP BY sc.lga
        HAVING count(DISTINCT cr.dcp_name) > 1
        ORDER BY sc.lga
        """
    )
    return [(r[0], r[1]) for r in cur.fetchall()]


def fix_backlink(cur, control_id: int) -> bool:
    """Re-point one orphaned control to the current provision sharing its section_ref."""
    cur.execute(
        """
        UPDATE dcp_setback_controls s
        SET provision_id = p.id
        FROM regulatory_provisions p
        WHERE s.id = %s
          AND s.section_ref IS NOT NULL
          AND p.is_current = TRUE
          AND p.ref_number = s.section_ref
        """,
        (control_id,),
    )
    return cur.rowcount > 0


def main() -> int:
    ap = argparse.ArgumentParser(description="DCP live-data health validator.")
    ap.add_argument("--council", help="Limit to one council (default: all ai-reviewed).")
    ap.add_argument("--fix-backlinks", action="store_true",
                    help="Re-point orphaned numeric-control provision_id links via section_ref.")
    args = ap.parse_args()

    conn = _connect()
    cur = conn.cursor()
    councils = _councils(cur, args.council)
    if not councils:
        print("No ai-reviewed councils found.")
        return 0

    # prior-art-checked: reuse not viable — the flagged files are frontend provision-DISPLAY
    # routes/components (for-property, dcp/provisions, ProvisionsByTocStructure); this is a
    # backend live-DATA integrity check (enrichment/dup/orphan) with no frontend equivalent.
    issues = 0
    fixed = 0
    print(f"{'council':<16} {'live':>6} {'unenriched':>11} {'dup_current':>12}")
    for c in councils:
        cur.execute(
            "SELECT count(*) FROM regulatory_provisions WHERE source_council=%s AND is_current=TRUE",
            (c,),
        )
        live = cur.fetchone()[0]
        gap = enrichment_gap(cur, c)
        dup = duplicate_current(cur, c)
        issues += (1 if gap else 0) + (1 if dup else 0)
        print(f"{c:<16} {live:>6} {gap:>11} {dup:>12}")

    # Orphaned numeric backlinks — a global check (only a few controls hard-link a provision).
    orphans = orphaned_backlinks(cur)
    if args.fix_backlinks and orphans:
        for oid in orphans:
            if fix_backlink(cur, oid):
                fixed += 1
        conn.commit()
        orphans = orphaned_backlinks(cur)  # re-check what remains

    print("-" * 52)
    print(f"orphaned numeric backlinks (all LGAs): {len(orphans)}")
    issues += 1 if orphans else 0
    if args.fix_backlinks:
        print(f"backlinks re-pointed: {fixed}")

    # Contamination canary — global, mirrors the API's registry join.
    fanout = registry_fanout_duplicates(cur)
    print(f"duplicate active (council, chapter_key) registry rows: {len(fanout)}")
    for council_key in fanout:
        print(f"  FANOUT {council_key[0]} / {council_key[1]}: {council_key[2]} active rows")
    issues += 1 if fanout else 0

    variance = dcp_name_variance(cur)
    print(f"LGAs serving >1 DCP name through the registry join: {len(variance)}")
    for lga, names in variance:
        print(f"  MIXED-NAME {lga}: {names}")
    issues += 1 if variance else 0
    if issues:
        print(f"RESULT: {issues} issue group(s) found. Unenriched provisions won't show in the "
              f"UI; run enrichment. Orphan links: re-run with --fix-backlinks. Dup current: "
              f"investigate the commit. FANOUT/MIXED-NAME: fix the registry rows — the "
              f"structured-controls API serves these.")
    else:
        print("RESULT: healthy — every live provision is enriched, one current version per "
              "code, no orphaned numeric links, no registry fanout or mixed DCP names. "
              "The end-user UI will reflect these correctly.")
    cur.close()
    conn.close()
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
