#!/usr/bin/env python3
"""Verify published coverage stats against the live database.

The marketing site publishes corpus/coverage figures from a single source of
truth: frontend-nextjs/lib/coverage.ts. Those numbers drift as coverage grows.
This script re-runs the canonical query behind each DB-backed figure and reports
any that no longer match, so a "never a guess" product never publishes a stale
number it can't trace.

Read-only. Safe to run any time:

    python scripts/verify_coverage_stats.py

Exit code 0 = all DB-backed figures current; 1 = drift found (or DB unreachable).
Editorial/config-derived fields in coverage.ts (dcpFullCouncils, floodLgas, etc.)
have no query here and are not checked.

prior-art-checked: reuse not viable because no coverage-stat drift-checker exists.
  /api/dcp/coverage returns the council list (not the marketing counts);
  api/db-verify is a connection health-check; sepp .../05_verify_completeness.py
  checks SEPP text extraction; drawdown_verify.py is an unrelated service. This
  script uniquely reconciles frontend-nextjs/lib/coverage.ts against the live DB.
"""
from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERAGE_TS = os.path.join(REPO_ROOT, "frontend-nextjs", "lib", "coverage.ts")

# key in COVERAGE  ->  (human label, SQL). Must mirror the header of coverage.ts.
QUERIES: dict[str, tuple[str, str]] = {
    "provisionsTotal": (
        "Total provisions",
        "SELECT COUNT(*) FROM regulatory_provisions",
    ),
    "dcpActionableProvisions": (
        "Actionable DCP provisions",
        "SELECT COUNT(*) FROM regulatory_provisions "
        "WHERE v2_is_actionable = TRUE AND v2_dcp_layer IS NOT NULL",
    ),
    "dcpNumericCouncils": (
        "Councils with DCP numeric controls",
        "SELECT COUNT(DISTINCT r.display_name) "
        "FROM dcp_setback_controls c JOIN lga_registry r ON r.slug = c.lga "
        "WHERE c.is_current = TRUE AND r.slug != 'nsw_statewide' "
        "AND r.parent_lga IS NULL",
    ),
    "dcpSetbackRows": (
        "DCP setback/control rows",
        "SELECT COUNT(*) FROM dcp_setback_controls",
    ),
    "heritageAreas": (
        "Heritage conservation areas",
        "SELECT COUNT(*) FROM heritage_conservation_areas",
    ),
    "regulatoryDefinitions": (
        "Regulatory definitions",
        "SELECT COUNT(*) FROM regulatory_definitions",
    ),
}

# Growing counts are published rounded DOWN (e.g. 53,716 -> "53,000+"). A live
# value ABOVE the stored integer is fine (the "+" still holds); only a live value
# BELOW the stored integer means the published claim is now overstated.
GROWING = {"provisionsTotal", "dcpActionableProvisions", "dcpSetbackRows",
           "regulatoryDefinitions"}


def parse_coverage_ts() -> dict[str, int]:
    """Extract the COVERAGE {...} integer block from coverage.ts."""
    with open(COVERAGE_TS, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"export const COVERAGE\s*=\s*\{(.*?)\}\s*as const", text, re.S)
    if not m:
        print("ERROR: could not find the COVERAGE object in coverage.ts", file=sys.stderr)
        sys.exit(1)
    body = m.group(1)
    return {k: int(v.replace(",", "")) for k, v in re.findall(r"(\w+):\s*([\d,]+)", body)}


def main() -> int:
    try:
        from dotenv import load_dotenv
        import psycopg2
    except ImportError as exc:  # pragma: no cover
        print(f"ERROR: missing dependency ({exc}). pip install psycopg2-binary python-dotenv", file=sys.stderr)
        return 1

    load_dotenv(os.path.join(REPO_ROOT, ".env"), override=True)
    published = parse_coverage_ts()

    # prior-art-checked: reuse IS viable and is what this now does. This script
    # demanded PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD, which nothing in the
    # repo sets -- every other consumer reads DATABASE_URL -- so it exited 1 on
    # "cannot reach the database: 'PGHOST'" wherever it ran. That is why it was
    # never wired into CI or a hook, and why the marketing site's published
    # coverage figures could drift from the database without one failing check.
    # scripts/dq_db.py already resolves DATABASE_URL from the main checkout's
    # .env and returns a read-only connection with a 30s statement timeout,
    # which is exactly this script's requirement, so it replaces the hand-built
    # connect rather than sitting beside it. The PG* path stays as a fallback
    # for anyone who does set those.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from dq_db import connect as _dq_connect
        conn = _dq_connect()
    except Exception as exc:  # noqa: BLE001
        try:
            conn = psycopg2.connect(
                host=os.environ["PGHOST"], port=os.environ["PGPORT"],
                dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"],
                password=os.environ["PGPASSWORD"], connect_timeout=15,
            )
            conn.set_session(readonly=True)
        except Exception:  # noqa: BLE001
            # Exit 2, not 1: unreachable is UNKNOWN, not "the figures disagree".
            # Collapsing those two turned main red on 2026-08-12 (#939).
            print(f"ERROR: cannot reach the database: {exc}", file=sys.stderr)
            return 2
    cur = conn.cursor()

    drift: list[str] = []
    print(f"Coverage stat verification  (source: {os.path.relpath(COVERAGE_TS, REPO_ROOT)})\n")
    print(f"  {'stat':<34}{'published':>11}{'live':>10}   status")
    print("  " + "-" * 66)
    for key, (label, sql) in QUERIES.items():
        want = published.get(key)
        if want is None:
            print(f"  {label:<34}{'—':>11}{'—':>10}   MISSING from coverage.ts")
            drift.append(f"{key}: absent from COVERAGE object")
            continue
        cur.execute(sql)
        live = cur.fetchone()[0]
        if key in GROWING:
            ok = live >= want                      # "+" claim: live may exceed, not fall below
            status = "OK" if ok else "OVERSTATED"
        else:
            ok = live == want                      # exact figure
            status = "OK" if ok else "DRIFT"
        if not ok:
            drift.append(f"{key}: published {want:,} vs live {live:,}")
        print(f"  {label:<34}{want:>11,}{live:>10,}   {status}")

    conn.close()
    print()
    if drift:
        print("DRIFT DETECTED — update frontend-nextjs/lib/coverage.ts:")
        for d in drift:
            print(f"  - {d}")
        return 1
    print("All DB-backed coverage stats are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
