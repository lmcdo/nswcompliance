#!/usr/bin/env python3
"""Validate TOC JOIN rates for one or all councils.

Checks that regulatory_provisions rows successfully join to dcp_table_of_contents
via (document_id, pdf_page). A low join rate means provisions are invisible in
the section-grouped UI and indicates a document_id mismatch or page range gap.

Usage:
  python scripts/validate_toc_join.py                  # all councils
  python scripts/validate_toc_join.py --council leichhardt
  python scripts/validate_toc_join.py --gate            # exit 1 if any council below threshold
  python scripts/validate_toc_join.py --council ashfield --gate --threshold 90

Exit codes:
  0  all checks passed (or --gate not set)
  1  one or more councils below threshold (only when --gate is set)
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

# ── Thresholds ─────────────────────────────────────────────────────────────────
# Ashfield chapter_e2_haberfield (121 provisions) has no TOC — structural cap ~93.7%
# Marrickville: 92.8% is stable baseline
DEFAULT_THRESHOLD = 85.0

KNOWN_CAPS: dict = {
    # council: (cap_pct, reason)
    # Ashfield: was capped at 93.8% (e2_haberfield no TOC). Fixed in migration 018 — catch-all entry inserted.
    # If a future council has a structural cap, add it here with the reason.
}

# ── DB connection ──────────────────────────────────────────────────────────────

def _load_env() -> dict:
    """Load env vars from frontend-nextjs/.env.local (has DATABASE_URL)."""
    env = {}
    candidates = [
        Path(__file__).parent.parent / "frontend-nextjs" / ".env.local",
        Path(__file__).parent.parent / ".env.local",
    ]
    for path in candidates:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_connection():
    env = _load_env()
    db_url = env.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url, connect_timeout=15)
    raise RuntimeError(
        "DATABASE_URL not found in frontend-nextjs/.env.local. "
        "Cannot connect to Supabase."
    )


# ── Queries ────────────────────────────────────────────────────────────────────

JOIN_RATE_SQL = """
SELECT
    p.source_council,
    count(*)                                             AS total,
    count(t.section_number)                              AS joined,
    round(100.0 * count(t.section_number) / count(*), 1) AS join_pct
FROM regulatory_provisions p
LEFT JOIN dcp_table_of_contents t
    ON  p.document_id = t.document_id
    AND p.pdf_page    >= t.page_start
    AND (t.page_end IS NULL OR p.pdf_page <= t.page_end)
WHERE p.is_current = true
  AND p.source_council IS NOT NULL
  {council_filter}
GROUP BY p.source_council
ORDER BY p.source_council
"""

TOC_EXISTS_FOR_COUNCIL_SQL = """
SELECT count(*)
FROM dcp_table_of_contents t
WHERE EXISTS (
    SELECT 1 FROM regulatory_provisions p
    WHERE p.document_id = t.document_id
      AND p.source_council = %s
      AND p.is_current = true
)
"""

ORPHAN_TOC_SQL = """
SELECT t.document_id, count(*) AS toc_rows
FROM dcp_table_of_contents t
WHERE t.document_id LIKE %s
  AND NOT EXISTS (
      SELECT 1 FROM regulatory_provisions p
      WHERE p.document_id = t.document_id AND p.is_current = true
  )
GROUP BY t.document_id
ORDER BY t.document_id
LIMIT 20
"""

UNMATCHED_DOCIDS_SQL = """
SELECT DISTINCT p.document_id
FROM regulatory_provisions p
WHERE p.source_council = %s
  AND p.is_current = true
  AND NOT EXISTS (
      SELECT 1 FROM dcp_table_of_contents t
      WHERE t.document_id = p.document_id
  )
ORDER BY p.document_id
LIMIT 20
"""


# ── Reporting ──────────────────────────────────────────────────────────────────

def _toc_loaded(cur, council: str) -> bool:
    """Returns True if ANY dcp_table_of_contents rows share document_ids with this council's provisions.

    Uses the provisions' document_ids as the anchor — council slugs and TOC document_id
    prefixes may not match (e.g. source_council='ashfield' but document_id starts with
    'Inner_West_Ashfield_DCP_2016__').
    """
    cur.execute(TOC_EXISTS_FOR_COUNCIL_SQL, (council,))
    (cnt,) = cur.fetchone()
    return cnt > 0


def check_council(cur, council: str, threshold: float, verbose: bool) -> bool:
    """Returns True if the council passes all checks (or has no TOC — skip, not fail)."""

    # 1. Check if TOC has been loaded at all for this council
    if not _toc_loaded(cur, council):
        print(f"  {council}: NO TOC — dcp_table_of_contents not loaded yet (skip)")
        return True  # Not a failure — TOC hasn't been imported yet

    # 2. JOIN rate
    filter_clause = "AND p.source_council = %s"
    cur.execute(JOIN_RATE_SQL.format(council_filter=filter_clause), (council,))
    row = cur.fetchone()
    if not row:
        print(f"  {council}: NO DATA — no is_current provisions found")
        return False

    _, total, joined, join_pct = row
    cap, cap_reason = KNOWN_CAPS.get(council, (None, None))
    effective_threshold = min(threshold, cap) if cap else threshold

    status = "PASS" if float(join_pct) >= effective_threshold else "FAIL"
    cap_note = f"  [cap: {cap}% — {cap_reason}]" if cap else ""
    print(f"  {council}: {joined}/{total} joined ({join_pct}%)  [{status}]{cap_note}")

    passed = float(join_pct) >= effective_threshold
    if not passed and verbose:
        cur.execute(UNMATCHED_DOCIDS_SQL, (council,))
        unmatched = cur.fetchall()
        if unmatched:
            print(f"    Provision document_ids with NO TOC entry:")
            for (doc_id,) in unmatched:
                print(f"      {doc_id}")

    # 3. Orphaned TOC entries (TOC rows with no matching provisions)
    if verbose:
        # Use a wildcard that covers all known document_id formats for this council
        cur.execute(
            "SELECT DISTINCT document_id FROM regulatory_provisions "
            "WHERE source_council = %s AND is_current = true LIMIT 1",
            (council,)
        )
        sample = cur.fetchone()
        prefix = (sample[0].split("__")[0] + "%") if sample else (council + "%")
        cur.execute(ORPHAN_TOC_SQL, (prefix,))
        orphans = cur.fetchall()
        if orphans:
            print(f"    Orphaned TOC document_ids (TOC entries but no matching provisions):")
            for doc_id, cnt in orphans:
                print(f"      {doc_id}  ({cnt} TOC rows)")

    return passed


def run(args) -> int:
    try:
        conn = get_connection()
    except Exception as e:
        print(f"validate_toc_join: DB connection failed — {e}", file=sys.stderr)
        return 1

    cur = conn.cursor()
    threshold = args.threshold

    if args.council:
        councils = [args.council]
    else:
        cur.execute(
            "SELECT DISTINCT source_council FROM regulatory_provisions "
            "WHERE is_current = true AND source_council IS NOT NULL ORDER BY source_council"
        )
        councils = [r[0] for r in cur.fetchall()]

    print(f"\n=== TOC JOIN Rate Validation (threshold: >={threshold}%) ===\n")

    all_passed = True
    for council in councils:
        ok = check_council(cur, council, threshold, verbose=args.verbose or args.gate)
        if not ok:
            all_passed = False

    print()
    if all_passed:
        print("  PASS — all councils meet TOC JOIN threshold")
    else:
        print("  FAIL — one or more councils below threshold")
        if args.gate:
            print("         Run with --verbose to see unmatched document_ids")

    conn.close()

    if args.gate and not all_passed:
        return 1
    return 0


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate TOC JOIN rates per council")
    parser.add_argument("--council", "-c", help="Filter to a single council slug")
    parser.add_argument(
        "--gate", action="store_true",
        help="Exit 1 if any council is below threshold (for CI/pre-pr use)"
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=DEFAULT_THRESHOLD,
        help=f"Minimum acceptable JOIN rate %% (default: {DEFAULT_THRESHOLD})"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show unmatched document_ids and orphaned TOC entries on failure"
    )
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
